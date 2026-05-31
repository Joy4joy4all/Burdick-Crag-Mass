# -*- coding: utf-8 -*-
"""
BCM v30 — ANCHOR PARTITION REGIME PERFORMANCE AUDIT
=====================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Code execution: The code builder.

Purpose:
    Join the SPARC175 Anchor Partition Regime Map with existing
    BCM solver win/loss records from the results directory.
    Ask: which APR regime explains BCM wins vs failures?

Regime map chain:
    Test 1: SPARC175 — APR_median=0.693, 152/175 substrate-side
    Test 2: Bracket Audit — 3/4 gates, 125 km/s snap delta=+0.193
    Test 3: High-Mass Split — 4/4 gates, bifurcation confirmed
    Test 4: Regime Map — 6-regime structure, valley-and-return

This test (Test 5):
    Load existing solver run records (load_all_records from run_record.py)
    Join by galaxy name to regime labels from Regime Map JSON
    Compute per-regime: BCM win rate, Newton win rate, mean RMS

Gates:
    G1: SUBSTRATE_PLATEAU has highest BCM win rate
    G2: SUPPRESSION_VALLEY has highest Newton win rate
    G3: ROOT_REENTRY BCM win rate higher than SUPPRESSION_VALLEY
        (re-entry is not just a Newton regime)
    G4: MASS_FLOOR has Newton win rate > 0.70

Hypothesis being tested:
    H_V30_ANCHOR_REGIME_MAP_SPARC175 — does the regime map
    predict which galaxies BCM wins on?
"""

from __future__ import annotations

import json
import sys
import os
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict

try:
    import cupy as cp
    import numpy as np
    xp = cp
    _BACKEND = "cupy"
except (ImportError, AttributeError):
    import numpy as np
    cp = np
    xp = np
    _BACKEND = "numpy"

_THIS_DIR      = Path(os.path.abspath(__file__)).parent
_SOLVER_ROOT   = _THIS_DIR.parent.parent
_GENESIS_BRAIN = _SOLVER_ROOT / "TITS_EPICt_BCM" / "genesis_brain"
_RESULTS_DIR   = _SOLVER_ROOT / "data" / "results"
_CORE_DIR      = _SOLVER_ROOT / "core"

for _p in [str(_SOLVER_ROOT), str(_GENESIS_BRAIN), str(_CORE_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from BCM_test_renderer import launch_renderer, write_frame, close_renderer
    _RENDERER_AVAILABLE = True
except ImportError:
    _RENDERER_AVAILABLE = False
    def launch_renderer(*a, **kw): return None
    def write_frame(*a, **kw):     pass
    def close_renderer(*a, **kw):  pass

EPS = 1e-9

REGIME_LABELS = [
    "MASS_FLOOR",
    "DWARF_INTERMEDIATE",
    "SUBSTRATE_PLATEAU",
    "MIXED_TRANSITION",
    "SUPPRESSION_VALLEY",
    "ROOT_REENTRY",
]


def load_regime_map() -> Dict[str, str]:
    """
    Load the most recent Regime Map JSON and return
    {galaxy_name: regime_label} mapping.
    """
    jsons = sorted(
        [f for f in _RESULTS_DIR.glob("BCM_v30_ANCHOR_PARTITION_REGIME_MAP_*.json")],
        key=os.path.getmtime
    )
    if not jsons:
        return {}
    with open(jsons[-1], encoding="utf-8") as fh:
        data = json.load(fh)
    regime_map = {}
    for g in data.get("galaxy_map", []):
        name = g.get("name", "")
        regime = g.get("regime", "UNKNOWN")
        if name:
            regime_map[name] = regime
    return regime_map


def load_bcm_records() -> List[Dict]:
    """
    Load all BCM solver run records from results directory.
    Uses run_record.load_all_records if available, otherwise
    scans for BCM_v27_SPARC_M_sigma_*.json files directly.
    """
    # Try load_all_records first
    try:
        from run_record import load_all_records
        records = load_all_records(str(_RESULTS_DIR))
        if records:
            return records
    except Exception:
        pass

    # Fallback: scan v27 SPARC M_sigma JSONs directly
    records = []
    for jf in sorted(_RESULTS_DIR.glob("BCM_v27_SPARC_M_sigma_*.json")):
        try:
            with open(jf, encoding="utf-8") as fh:
                d = json.load(fh)
            records.append(d)
        except Exception:
            pass
    return records


def extract_galaxy_result(record: Dict) -> Optional[Dict]:
    """
    Extract galaxy name, vmax, winner, rms values from a run record.
    Handles both load_all_records format and raw JSON format.
    """
    # load_all_records format
    if "galaxy" in record and "results" in record:
        gal  = record.get("galaxy", {})
        res  = record.get("results", {})
        # galaxy may be a string (name) or a dict
        if isinstance(gal, str):
            name = gal
            vmax = float(record.get("galaxy_properties", {}).get("v_max", 0))
        else:
            name = gal.get("name", "")
            vmax = float(gal.get("v_max", 0))
        winner   = res.get("winner", None)
        rms_n    = res.get("rms_newton", None)
        rms_s    = res.get("rms_substrate", None)
        if name and winner:
            return {"name": name, "vmax": vmax,
                    "winner": winner, "rms_newton": rms_n,
                    "rms_substrate": rms_s}

    # Raw v27 SPARC M_sigma JSON format
    # These may store results differently — try common fields
    for name_key in ["galaxy_name", "name", "galaxy"]:
        if name_key in record:
            name = record[name_key]
            if isinstance(name, str):
                break
    else:
        return None

    # Try various result structures
    res = record.get("results", record.get("comparison", {}))
    winner   = res.get("winner", record.get("winner", None))
    rms_n    = res.get("rms_newton", record.get("rms_newton", None))
    rms_s    = res.get("rms_substrate", record.get("rms_substrate", None))
    vmax     = float(record.get("v_max", record.get("vmax", 0)))

    if name and winner:
        return {"name": name, "vmax": vmax,
                "winner": winner, "rms_newton": rms_n,
                "rms_substrate": rms_s}
    return None


def regime_performance(joined: List[Dict]) -> Dict[str, Any]:
    """Compute win rates and RMS stats by regime."""
    by_regime = defaultdict(list)
    for g in joined:
        by_regime[g["regime"]].append(g)

    stats = {}
    for label in REGIME_LABELS:
        sub = by_regime.get(label, [])
        if not sub:
            stats[label] = {"n_matched": 0}
            continue
        winners  = [g["winner"] for g in sub]
        rms_n    = [g["rms_newton"] for g in sub if g["rms_newton"] is not None]
        rms_s    = [g["rms_substrate"] for g in sub if g["rms_substrate"] is not None]
        n        = len(sub)
        bcm_wins = sum(1 for w in winners if w == "SUBSTRATE")
        nwt_wins = sum(1 for w in winners if w == "NEWTON")
        stats[label] = {
            "n_matched":      n,
            "bcm_win_rate":   round(bcm_wins/n, 3) if n > 0 else 0,
            "newton_win_rate":round(nwt_wins/n, 3) if n > 0 else 0,
            "rms_newton_mean":round(float(np.mean(rms_n)), 2) if rms_n else None,
            "rms_sub_mean":   round(float(np.mean(rms_s)), 2) if rms_s else None,
            "galaxies":       sorted([g["name"] for g in sub]),
        }
    return stats


def run_test():
    print("BCM v30 — ANCHOR PARTITION REGIME PERFORMANCE AUDIT")
    print(f"Backend:  {_BACKEND}")
    print(f"Renderer: {'ACTIVE' if _RENDERER_AVAILABLE else 'NOT FOUND'}")
    print()

    # Load regime map
    regime_map = load_regime_map()
    if not regime_map:
        print("ERROR: No Regime Map JSON found in results directory.")
        print("Run BCM_v30_ANCHOR_PARTITION_REGIME_MAP.py first.")
        return 1
    print(f"Regime map loaded: {len(regime_map)} galaxies")

    # Load BCM run records
    all_records = load_bcm_records()
    print(f"BCM run records found: {len(all_records)}")

    # Extract and deduplicate — keep most recent per galaxy
    extracted: Dict[str, Dict] = {}
    for rec in all_records:
        g = extract_galaxy_result(rec)
        if g and g["name"] in regime_map:
            name = g["name"]
            # Keep if not seen yet (records sorted oldest-first typically)
            if name not in extracted:
                extracted[name] = g

    # Join with regime labels
    joined = []
    for name, g in extracted.items():
        regime = regime_map.get(name, "UNKNOWN")
        joined.append({**g, "regime": regime})

    n_joined    = len(joined)
    n_regime    = len(regime_map)
    n_unmatched = n_regime - n_joined

    print(f"Joined (regime ∩ BCM records): {n_joined}")
    print(f"Regime galaxies without BCM record: {n_unmatched}")
    print()

    if n_joined < 10:
        print("WARNING: Fewer than 10 matched galaxies.")
        print("BCM solver records may be in a different format.")
        print("Attempting direct JSON scan of v27 SPARC files...")
        # Direct scan fallback
        joined = []
        for jf in sorted(_RESULTS_DIR.glob("BCM_v27_SPARC_M_sigma_*.json")):
            try:
                with open(jf, encoding="utf-8") as fh:
                    d = json.load(fh)
                # Extract galaxy name from filename
                stem = jf.stem  # BCM_v27_SPARC_M_sigma_NGC2403_20260502_090040
                parts = stem.split("_M_sigma_")
                if len(parts) == 2:
                    gname = parts[1].rsplit("_", 2)[0]  # remove timestamp
                    regime = regime_map.get(gname)
                    if regime:
                        # Try to get winner from JSON
                        winner = (d.get("winner") or
                                  d.get("results", {}).get("winner") or
                                  d.get("comparison", {}).get("winner"))
                        rms_n = (d.get("rms_newton") or
                                 d.get("results", {}).get("rms_newton"))
                        rms_s = (d.get("rms_substrate") or
                                 d.get("results", {}).get("rms_substrate"))
                        vmax  = regime_map.get(gname + "_vmax",
                                               float(d.get("v_max", 0)))
                        if winner:
                            joined.append({"name": gname, "vmax": vmax,
                                          "winner": winner, "rms_newton": rms_n,
                                          "rms_substrate": rms_s,
                                          "regime": regime})
            except Exception:
                pass
        print(f"  Direct scan matched: {len(joined)}")

    rend = launch_renderer("BCM_v30_REGIME_PERFORMANCE",
                            n_steps=len(REGIME_LABELS), downsample=1)

    perf = regime_performance(joined)

    # Print performance table
    print("=" * 70)
    print("REGIME PERFORMANCE — BCM vs Newton by Anchor Partition Regime")
    print("=" * 70)
    print(f"\n{'Regime':22s} {'N':>5}  {'BCM_win%':>9}  {'NWT_win%':>9}  "
          f"{'RMS_N_mean':>11}  {'RMS_S_mean':>11}")
    print("-" * 72)
    for label in REGIME_LABELS:
        s = perf.get(label, {})
        n = s.get("n_matched", 0)
        if n == 0:
            print(f"{label:22s} {'0':>5}  {'(no match)':>9}")
            continue
        rms_n_str = f"{s['rms_newton_mean']:>11.2f}" if s['rms_newton_mean'] else "         N/A"
        rms_s_str = f"{s['rms_sub_mean']:>11.2f}" if s['rms_sub_mean'] else "         N/A"
        print(f"{label:22s} {n:>5}  "
              f"{s['bcm_win_rate']*100:>8.1f}%  "
              f"{s['newton_win_rate']*100:>8.1f}%  "
              f"{rms_n_str}  {rms_s_str}")

        if rend is not None:
            hist = np.zeros((1, 6))
            for i, lbl in enumerate(REGIME_LABELS):
                hist[0, i] = perf.get(lbl, {}).get("bcm_win_rate", 0)
            write_frame(rend, hist, step=REGIME_LABELS.index(label)+1,
                        n_steps=len(REGIME_LABELS),
                        state=f"Regime: {label}",
                        metrics={"bcm_win": s["bcm_win_rate"],
                                 "n_matched": n}, downsample=1)

    # Gates
    print()
    sp   = perf.get("SUBSTRATE_PLATEAU", {})
    sv   = perf.get("SUPPRESSION_VALLEY", {})
    rr   = perf.get("ROOT_REENTRY", {})
    mf   = perf.get("MASS_FLOOR", {})

    bcm_rates = {k: perf.get(k, {}).get("bcm_win_rate", 0) for k in REGIME_LABELS
                 if perf.get(k, {}).get("n_matched", 0) > 0}
    nwt_rates = {k: perf.get(k, {}).get("newton_win_rate", 0) for k in REGIME_LABELS
                 if perf.get(k, {}).get("n_matched", 0) > 0}

    g1 = (sp.get("n_matched", 0) > 0 and sp.get("bcm_win_rate", 0) ==
          max(bcm_rates.values()))
    g2 = (sv.get("n_matched", 0) > 0 and sv.get("newton_win_rate", 0) ==
          max(nwt_rates.values()))
    g3 = (rr.get("n_matched", 0) > 0 and
          rr.get("bcm_win_rate", 0) > sv.get("bcm_win_rate", 0))
    g4 = (mf.get("n_matched", 0) > 0 and mf.get("newton_win_rate", 0) >= 0.70)

    gates_pass = sum([g1, g2, g3, g4])

    print("Gates:")
    print(f"  G1 SUBSTRATE_PLATEAU highest BCM win rate: "
          f"{'PASS' if g1 else 'FAIL'}  "
          f"(rate={sp.get('bcm_win_rate',0):.3f})")
    print(f"  G2 SUPPRESSION_VALLEY highest Newton win:  "
          f"{'PASS' if g2 else 'FAIL'}  "
          f"(rate={sv.get('newton_win_rate',0):.3f})")
    print(f"  G3 ROOT_REENTRY BCM > SUPPRESSION_VALLEY:  "
          f"{'PASS' if g3 else 'FAIL'}  "
          f"(RR={rr.get('bcm_win_rate',0):.3f} vs SV={sv.get('bcm_win_rate',0):.3f})")
    print(f"  G4 MASS_FLOOR Newton win >= 0.70:          "
          f"{'PASS' if g4 else 'FAIL'}  "
          f"(rate={mf.get('newton_win_rate',0):.3f})")
    print(f"  Gates passed: {gates_pass}/4")

    if n_joined < 10:
        verdict  = "INSUFFICIENT_MATCHED_RECORDS_REGIME_JOIN_FAILED"
        hyp_keys = ["H_V30_ANCHOR_REGIME_MAP_SPARC175"]
    elif gates_pass == 4:
        verdict  = "REGIME_MAP_PREDICTIVE_CONFIRMED_4_OF_4"
        hyp_keys = ["H_V30_ANCHOR_REGIME_MAP_SPARC175",
                    "H_V30_APR_TRACKS_BTFR_BRACKET",
                    "H_V30_REGIME_PREDICTS_BCM_WIN"]
    elif gates_pass >= 2:
        verdict  = f"REGIME_MAP_PARTIAL_PREDICTIVE_{gates_pass}_OF_4"
        hyp_keys = ["H_V30_ANCHOR_REGIME_MAP_SPARC175"]
    else:
        verdict  = "REGIME_MAP_NOT_PREDICTIVE_OF_BCM_WINS"
        hyp_keys = ["H_V30_ANCHOR_REGIME_MAP_SPARC175"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v30_ANCHOR_REGIME_PERFORMANCE_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
            "test_id":   "BCM_v30_ANCHOR_REGIME_PERFORMANCE_AUDIT",
            "test_name": "SPARC175_REGIME_BCM_WIN_RATE_AUDIT",
            "timestamp": ts,
            "foreman":   "Stephen Justin Burdick Sr.",
            "n_regime_map":   n_regime,
            "n_bcm_records":  len(all_records),
            "n_joined":       n_joined,
            "n_unmatched":    n_unmatched,
            "regime_performance": perf,
            "gate_results":   {"G1": g1, "G2": g2, "G3": g3, "G4": g4},
            "gates_passed":   gates_pass,
            "verdict":        verdict,
            "hypothesis_keys": hyp_keys,
            "framework_note": (
                "Join of APR regime labels with existing BCM solver run records. "
                "Win = BCM RMS < Newton RMS per existing run_record schema. "
                "Does not re-run solver — reads archived results only."
            ),
        }, fh, indent=2)

    close_renderer(rend, final_state=verdict,
                   metrics={"gates_passed": gates_pass,
                            "n_joined": n_joined})

    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
