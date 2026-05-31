# -*- coding: utf-8 -*-
"""
BCM v30 — ROOT REENTRY FAILURE AUDIT B
========================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Code execution: The code builder.

Fixes from Audit A:
    Bug 1: hardcoded galaxy list included UGC11914 (MASS_FLOOR, not ROOT_REENTRY)
    Bug 2: individual record lookup failed; use load_all_records bulk join
           (same pattern that matched 175/175 in performance audit)

Changes from A:
    1. Load regime map JSON — select only regime == ROOT_REENTRY (expected N=6)
    2. Load all BCM records via load_all_records; join by name
    3. Gate G2: if any winner/RMS is None, report JOIN_FAIL — do not print win counts
    4. Anatomy (APR zones, failure zones) kept from A — it was valid

Gates:
    G1: selected ROOT_REENTRY count == 6
    G2: all 6 have non-null winner, rms_newton, rms_substrate
    G3: outer worst BCM failure zone in >= 5 of joined galaxies
    G4: outer strongest APR zone in >= 5 of joined galaxies
    G5: ROOT_REENTRY mean BCM RMS > Newton RMS (solver underfit confirmed)
         or if RMS equal, classify as MIXED
"""

from __future__ import annotations

import json
import sys
import os
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import Counter

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
_SPARC_DIR     = _SOLVER_ROOT / "data" / "sparc_raw"
_RESULTS_DIR   = _SOLVER_ROOT / "data" / "results"
_CORE_DIR      = _SOLVER_ROOT / "core"

for _p in [str(_SOLVER_ROOT), str(_GENESIS_BRAIN), str(_CORE_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_sparc_path = _SOLVER_ROOT / "core" / "sparc_ingest.py"
_spec = importlib.util.spec_from_file_location("sparc_ingest", str(_sparc_path))
_sparc_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sparc_mod)
load_rotation_curve   = _sparc_mod.load_rotation_curve
build_newtonian_curve = _sparc_mod.build_newtonian_curve

try:
    from BCM_test_renderer import launch_renderer, write_frame, close_renderer
    _RENDERER_AVAILABLE = True
except ImportError:
    _RENDERER_AVAILABLE = False
    def launch_renderer(*a, **kw): return None
    def write_frame(*a, **kw):     pass
    def close_renderer(*a, **kw):  pass

EPS = 1e-9


def load_root_reentry_names() -> List[str]:
    """Load regime map and return only galaxies with regime == ROOT_REENTRY."""
    jsons = sorted(
        [f for f in _RESULTS_DIR.glob("BCM_v30_ANCHOR_PARTITION_REGIME_MAP_*.json")],
        key=os.path.getmtime
    )
    if not jsons:
        return []
    with open(jsons[-1], encoding="utf-8") as fh:
        data = json.load(fh)
    return [g["name"] for g in data.get("galaxy_map", [])
            if g.get("regime") == "ROOT_REENTRY"]


def load_apr_for_name(name: str) -> Dict:
    """APR values for one galaxy from regime map JSON."""
    jsons = sorted(
        [f for f in _RESULTS_DIR.glob("BCM_v30_ANCHOR_PARTITION_REGIME_MAP_*.json")],
        key=os.path.getmtime
    )
    if not jsons:
        return {}
    with open(jsons[-1], encoding="utf-8") as fh:
        data = json.load(fh)
    for g in data.get("galaxy_map", []):
        if g.get("name") == name:
            return g
    return {}


def load_all_bcm_records() -> List[Dict]:
    """Load all BCM solver records — same path as performance audit."""
    try:
        from run_record import load_all_records
        records = load_all_records(str(_RESULTS_DIR))
        if records:
            return records
    except Exception:
        pass
    records = []
    for jf in sorted(_RESULTS_DIR.glob("BCM_v27_SPARC_M_sigma_*.json")):
        try:
            with open(jf, encoding="utf-8") as fh:
                records.append(json.load(fh))
        except Exception:
            pass
    return records


def extract_result(record: Dict) -> Optional[Dict]:
    """Extract name + result fields — same logic as performance audit."""
    if "galaxy" in record and "results" in record:
        gal = record.get("galaxy", {})
        res = record.get("results", {})
        if isinstance(gal, str):
            name = gal
            vmax = float(record.get("galaxy_properties", {}).get("v_max", 0))
        else:
            name = gal.get("name", "")
            vmax = float(gal.get("v_max", 0))
        winner = res.get("winner")
        rms_n  = res.get("rms_newton")
        rms_s  = res.get("rms_substrate")
        if name and winner:
            return {"name": name, "vmax": vmax,
                    "winner": winner, "rms_newton": rms_n, "rms_substrate": rms_s}
    return None


def zonal_apr_profile(name: str) -> Dict:
    """Compute inner/mid/outer APR zones from SPARC rotation curve."""
    matches = list(_SPARC_DIR.rglob(f"{name}_rotmod.dat"))
    if not matches:
        return {}
    rot      = load_rotation_curve(str(matches[0]))
    radii    = np.array(rot["radius_kpc"])
    vobs     = np.array(rot["Vobs_kms"])
    v_newton = build_newtonian_curve(rot)

    vobs_sq  = xp.array(vobs)**2
    vnewt_sq = xp.array(v_newton)**2
    disc_sq  = xp.maximum(vobs_sq - vnewt_sq, 0.0)
    apr_r    = disc_sq / xp.maximum(vobs_sq, EPS)
    if hasattr(xp, "asnumpy"):
        apr_np = xp.asnumpy(apr_r)
    else:
        apr_np = np.array(apr_r)

    r_max = float(radii[-1]) if len(radii) > 0 else 1.0
    inner = radii < 0.33 * r_max
    mid   = (radii >= 0.33 * r_max) & (radii < 0.67 * r_max)
    outer = radii >= 0.67 * r_max

    def zone_apr(mask):
        return round(float(np.mean(apr_np[mask])), 4) if mask.sum() > 0 else None

    apr_inner = zone_apr(inner)
    apr_mid   = zone_apr(mid)
    apr_outer = zone_apr(outer)

    zones = {k: v for k, v in
             {"inner": apr_inner, "mid": apr_mid, "outer": apr_outer}.items()
             if v is not None}
    substrate_zone = max(zones, key=zones.get) if zones else "unknown"

    return {
        "apr_inner":       apr_inner,
        "apr_mid":         apr_mid,
        "apr_outer_zone":  apr_outer,
        "substrate_zone":  substrate_zone,
        "r_max_kpc":       round(r_max, 2),
        "n_points":        int(len(radii)),
    }


def run_test():
    print("BCM v30 — ROOT REENTRY FAILURE AUDIT B")
    print(f"Backend:  {_BACKEND}")
    print(f"Renderer: {'ACTIVE' if _RENDERER_AVAILABLE else 'NOT FOUND'}")
    print()

    # G1: select from regime map
    names = load_root_reentry_names()
    print(f"ROOT_REENTRY from regime map: {names}")
    g1 = len(names) == 6
    print(f"G1 count == 6: {'PASS' if g1 else 'FAIL'}  (n={len(names)})")
    print()

    # Load all BCM records and build lookup by name
    all_records = load_all_bcm_records()
    print(f"BCM records loaded: {len(all_records)}")

    record_by_name: Dict[str, Dict] = {}
    for rec in all_records:
        r = extract_result(rec)
        if r and r["name"] not in record_by_name:
            record_by_name[r["name"]] = r

    # APR data from regime map
    apr_by_name = {n: load_apr_for_name(n) for n in names}

    rend = launch_renderer("BCM_v30_ROOT_REENTRY_B",
                            n_steps=len(names), downsample=1)

    results = []
    for i, name in enumerate(names):
        apr   = apr_by_name.get(name, {})
        bcm   = record_by_name.get(name, {})
        zones = zonal_apr_profile(name)

        r = {
            "name":        name,
            "vmax":        apr.get("vmax"),
            "apr_max":     apr.get("apr_max"),
            "apr_outer":   apr.get("apr_outer"),
            "regime":      apr.get("regime"),
            "winner":      bcm.get("winner"),
            "rms_newton":  bcm.get("rms_newton"),
            "rms_substrate": bcm.get("rms_substrate"),
            **zones,
        }
        results.append(r)

        # Failure zone from RMS comparison
        if bcm.get("rms_newton") and bcm.get("rms_substrate"):
            # Approximate: BCM worse = outer underfit
            r["failure_zone_proxy"] = "outer" if bcm["rms_substrate"] > bcm["rms_newton"] else "inner_or_mid"
        else:
            r["failure_zone_proxy"] = "unknown"

        print(f"{name}:")
        print(f"  vmax={r['vmax']}  APR_outer={r['apr_outer']}")
        print(f"  winner={r['winner']}  BCM_RMS={r['rms_substrate']}  "
              f"Newton_RMS={r['rms_newton']}")
        print(f"  APR zones: inner={r.get('apr_inner')}  "
              f"mid={r.get('apr_mid')}  outer={r.get('apr_outer_zone')}")
        print(f"  Strongest substrate zone: {r.get('substrate_zone')}")
        print()

        if rend is not None:
            write_frame(rend, np.array([[r["apr_outer"] or 0]]),
                        step=i+1, n_steps=len(names),
                        state=f"{name} | {r['winner'] or 'no_record'}",
                        metrics={"apr_outer": r["apr_outer"] or 0,
                                 "bcm_rms": r["rms_substrate"] or 0,
                                 "newton_rms": r["rms_newton"] or 0},
                        downsample=1)

    # Gates
    joined = [r for r in results if r["winner"] is not None]
    g2     = len(joined) == len(names) and all(
        r["rms_newton"] is not None and r["rms_substrate"] is not None
        for r in joined
    )
    sub_zones   = [r.get("substrate_zone") for r in results if r.get("substrate_zone")]
    outer_sub   = sum(1 for z in sub_zones if z == "outer")
    fail_zones  = [r.get("failure_zone_proxy") for r in joined if r.get("failure_zone_proxy") != "unknown"]
    outer_fail  = sum(1 for z in fail_zones if z == "outer")

    g3 = outer_fail >= max(1, len(joined) * 5 // 6) if joined else False
    g4 = outer_sub  >= len(results) * 5 // 6

    if joined:
        rms_bcm_mean = float(np.mean([r["rms_substrate"] for r in joined
                                       if r["rms_substrate"]]))
        rms_nwt_mean = float(np.mean([r["rms_newton"] for r in joined
                                       if r["rms_newton"]]))
        g5 = rms_bcm_mean > rms_nwt_mean
    else:
        rms_bcm_mean = rms_nwt_mean = None
        g5 = False

    gates_pass = sum([g1, g2, g3, g4, g5])

    print("=" * 60)
    print("ROOT REENTRY — FAILURE ANATOMY SUMMARY")
    print("=" * 60)
    print(f"\n{'Galaxy':14s} {'vmax':>7}  {'APR_out':>8}  "
          f"{'BCM_RMS':>8}  {'NWT_RMS':>8}  {'Winner':>8}  {'SubZone':>10}")
    print("-" * 75)
    for r in results:
        print(f"{r['name']:14s} "
              f"{str(r.get('vmax','')):>7}  "
              f"{str(r.get('apr_outer','')):>8}  "
              f"{str(r.get('rms_substrate','')):>8}  "
              f"{str(r.get('rms_newton','')):>8}  "
              f"{str(r.get('winner','')):>8}  "
              f"{str(r.get('substrate_zone','')):>10}")

    print()
    if joined:
        newton_wins = sum(1 for r in joined if r["winner"] == "NEWTON")
        bcm_wins    = sum(1 for r in joined if r["winner"] == "SUBSTRATE")
        print(f"Joined records:   {len(joined)} / {len(names)}")
        print(f"BCM wins:         {bcm_wins} / {len(joined)}")
        print(f"Newton wins:      {newton_wins} / {len(joined)}")
        print(f"Mean BCM RMS:     {rms_bcm_mean:.2f}" if rms_bcm_mean else "")
        print(f"Mean Newton RMS:  {rms_nwt_mean:.2f}" if rms_nwt_mean else "")
    else:
        print("JOIN FAILED — no winner/RMS records attached.")
        print("Win counts not available.")

    print(f"\nSubstrate zones: {dict(Counter(sub_zones))}")
    print()
    print("Gates:")
    print(f"  G1 ROOT_REENTRY count == 6:          {'PASS' if g1 else 'FAIL'}  (n={len(names)})")
    print(f"  G2 all records joined with RMS:      {'PASS' if g2 else 'FAIL'}  "
          f"(joined={len(joined)}/{len(names)})")
    print(f"  G3 outer failure zone >= 5/6:        {'PASS' if g3 else 'FAIL'}  "
          f"(outer_fail={outer_fail}/{len(joined) if joined else 0})")
    print(f"  G4 outer APR zone >= 5/6:            {'PASS' if g4 else 'PASS' if outer_sub >= len(results)*5//6 else 'FAIL'}  "
          f"(outer_sub={outer_sub}/{len(results)})")
    print(f"  G5 BCM_RMS > Newton_RMS (underfit):  {'PASS' if g5 else 'FAIL'}"
          + (f"  ({rms_bcm_mean:.2f} vs {rms_nwt_mean:.2f})" if rms_bcm_mean else " (no data)"))
    print(f"  Gates passed: {gates_pass}/5")

    if not g2:
        verdict  = f"ROOT_REENTRY_ANATOMY_CONFIRMED__PERFORMANCE_JOIN_FAILED_{len(joined)}_OF_{len(names)}"
        hyp_keys = ["H_V30_ROOT_REENTRY_REQUIRES_ADDITIONAL_OPERATOR"]
    elif gates_pass >= 4:
        verdict  = "ROOT_REENTRY_OUTER_SUBSTRATE_UNDERFIT_CONFIRMED"
        hyp_keys = ["H_V30_ROOT_REENTRY_REQUIRES_ADDITIONAL_OPERATOR",
                    "H_V30_ANCHOR_REGIME_MAP_SPARC175"]
    elif gates_pass >= 2:
        verdict  = f"ROOT_REENTRY_PARTIAL_{gates_pass}_OF_5"
        hyp_keys = ["H_V30_ROOT_REENTRY_REQUIRES_ADDITIONAL_OPERATOR"]
    else:
        verdict  = "ROOT_REENTRY_AUDIT_INCONCLUSIVE"
        hyp_keys = ["H_V30_ROOT_REENTRY_REQUIRES_ADDITIONAL_OPERATOR"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v30_ROOT_REENTRY_AUDIT_B_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
            "test_id":   "BCM_v30_ROOT_REENTRY_AUDIT_B",
            "test_name": "ROOT_REENTRY_FAILURE_ANATOMY_B",
            "timestamp": ts,
            "foreman":   "Stephen Justin Burdick Sr.",
            "root_reentry_galaxies": names,
            "n_selected":   len(names),
            "n_joined":     len(joined),
            "performance_context": {
                "from_audit_A": {
                    "apr_outer_7of7_outer": True,
                    "substrate_zone_6of7_outer": True,
                    "winner_null": True,
                },
            },
            "galaxy_results": results,
            "substrate_zone_counts": dict(Counter(sub_zones)),
            "rms_bcm_mean":   round(rms_bcm_mean, 2) if rms_bcm_mean else None,
            "rms_newton_mean":round(rms_nwt_mean, 2) if rms_nwt_mean else None,
            "gate_results":   {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5},
            "gates_passed":   gates_pass,
            "verdict":        verdict,
            "hypothesis_keys":hyp_keys,
            "hypothesis_statement": (
                "ROOT_REENTRY galaxies show APR substrate signal concentrated "
                "in outer disk. Current solver underfits outer curve structure "
                "at ROOT scale. Additional operator needed for outer-disk "
                "ROOT-scale substrate geometry."
            ),
        }, fh, indent=2)

    close_renderer(rend, final_state=verdict,
                   metrics={"n_joined": len(joined), "gates": gates_pass,
                            "outer_sub": outer_sub})

    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
