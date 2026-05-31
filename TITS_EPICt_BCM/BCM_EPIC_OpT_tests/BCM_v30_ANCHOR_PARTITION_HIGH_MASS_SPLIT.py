# -*- coding: utf-8 -*-
"""
BCM v30 — ANCHOR PARTITION HIGH-MASS FINE SPLIT
================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Code execution: The code builder.

Bracket audit finding:
    HIGH (150-200): frac_inv=0.000, frac_mass=0.333  <- lowest inversion
    MASSIVE (200+): frac_inv=0.053, frac_mass=0.184

    G2 failed because MASSIVE was not the lowest inversion bracket.
    HIGH was. That is a structural signal.

Question:
    Is MASSIVE one class, or does it bifurcate?
    Does the substrate-dominant population split inside 200+ km/s?

Fine split at upper end (replacing HIGH and MASSIVE Paper A brackets):
    HIGH_A:  150-200  (original HIGH — confirmed low inversion)
    HIGH_B:  200-250
    HIGH_C:  250-300
    HIGH_D:  300+

Ask:
    - Where does frac_inversion bottom out?
    - Where does frac_mass_dominant peak?
    - Is there a second substrate-dominant population inside MASSIVE?
    - Does APR_outer recover above 250 or 300?

Gates:
    G1: HIGH_A (150-200) has lowest frac_inversion of all high brackets
        (confirms bracket audit finding)
    G2: At least one sub-bracket above 200 has higher APR_outer
        than HIGH_A (substrate recovery in massive systems)
    G3: frac_mass peaks in one specific sub-bracket, not monotonic
        (bifurcation signal)
    G4: HIGH_B or HIGH_C has different APR_outer from HIGH_D by > 0.10
        (mass split is real, not smooth gradient)
"""

from __future__ import annotations

import json
import sys
import os
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

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

for _p in [str(_SOLVER_ROOT), str(_GENESIS_BRAIN)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_sparc_path = _SOLVER_ROOT / "core" / "sparc_ingest.py"
_spec = importlib.util.spec_from_file_location("sparc_ingest", str(_sparc_path))
_sparc_mod = importlib.util.module_from_spec(_spec)
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

# ── Full bracket set: Paper A low brackets + fine high split ─────────────────
BRACKETS = [
    ("DWARF",   0,   50),
    ("LOW",     50,  100),
    ("MID",     100, 150),
    ("HIGH_A",  150, 200),   # original HIGH — confirmed low inversion
    ("HIGH_B",  200, 250),   # fine split 1
    ("HIGH_C",  250, 300),   # fine split 2
    ("HIGH_D",  300, 9999),  # extreme massive
]

APR_MASS_DOMINANT_MAX      = 0.30
APR_MIXED_MAX              = 0.55
APR_SUBSTRATE_DOMINANT_MAX = 0.80


def get_bracket(vmax: float) -> str:
    for name, lo, hi in BRACKETS:
        if lo <= vmax < hi:
            return name
    return "UNKNOWN"


def classify_apr(apr_max: float) -> str:
    if apr_max < APR_MASS_DOMINANT_MAX:
        return "MASS_DOMINANT"
    elif apr_max < APR_MIXED_MAX:
        return "MIXED_ANCHOR"
    elif apr_max < APR_SUBSTRATE_DOMINANT_MAX:
        return "SUBSTRATE_DOMINANT"
    else:
        return "INVERSION_TRANSITION"


def process_galaxy(dat_path: str) -> Dict[str, Any]:
    name     = Path(dat_path).stem.split("_")[0]
    rot      = load_rotation_curve(dat_path)
    radii    = rot["radius_kpc"]
    vobs     = rot["Vobs_kms"]
    if len(radii) == 0:
        return {"name": name, "error": "empty"}

    v_newton = build_newtonian_curve(rot)
    vobs_sq  = xp.array(vobs)**2
    vnewt_sq = xp.array(v_newton)**2
    disc_sq  = xp.maximum(vobs_sq - vnewt_sq, 0.0)
    apr      = disc_sq / xp.maximum(vobs_sq, EPS)

    vmax_obs    = float(xp.max(xp.array(vobs)))
    outer_start = int(len(radii) * 0.80)
    apr_outer   = float(xp.mean(apr[outer_start:])) if outer_start < len(apr) else float(xp.mean(apr))

    return {
        "name":      name,
        "vmax":      round(vmax_obs, 1),
        "apr_max":   round(float(xp.max(apr)), 4),
        "apr_outer": round(apr_outer, 4),
        "bcm_class": classify_apr(float(xp.max(apr))),
        "bracket":   get_bracket(vmax_obs),
        "newton_win": float(xp.max(apr)) < APR_MASS_DOMINANT_MAX,
    }


def bracket_stats(galaxies: List[Dict]) -> Dict[str, Any]:
    stats = {}
    for bname, blo, bhi in BRACKETS:
        sub = [g for g in galaxies
               if blo <= g["vmax"] < bhi and "error" not in g]
        if not sub:
            stats[bname] = {"n": 0, "vmax_range": f"{blo}-{bhi}"}
            continue
        aprs       = [g["apr_max"] for g in sub]
        aprs_outer = [g["apr_outer"] for g in sub]
        vmaxs      = [g["vmax"] for g in sub]
        n_inv   = sum(1 for g in sub if g["bcm_class"] == "INVERSION_TRANSITION")
        n_mass  = sum(1 for g in sub if g["bcm_class"] == "MASS_DOMINANT")
        n_newt  = sum(1 for g in sub if g["newton_win"])

        stats[bname] = {
            "n":                  len(sub),
            "vmax_range":         f"{blo}-{bhi}",
            "vmax_mean":          round(float(np.mean(vmaxs)), 1),
            "apr_max_mean":       round(float(np.mean(aprs)), 4),
            "apr_max_median":     round(float(np.median(aprs)), 4),
            "apr_outer_mean":     round(float(np.mean(aprs_outer)), 4),
            "apr_outer_median":   round(float(np.median(aprs_outer)), 4),
            "frac_inversion":     round(n_inv / max(len(sub), 1), 3),
            "frac_mass_dominant": round(n_mass / max(len(sub), 1), 3),
            "newton_win_rate":    round(n_newt / max(len(sub), 1), 3),
            "galaxies":           sorted([g["name"] for g in sub]),
        }
    return stats


def run_test():
    print("BCM v30 — ANCHOR PARTITION HIGH-MASS FINE SPLIT")
    print(f"Backend:  {_BACKEND}")
    print(f"Renderer: {'ACTIVE' if _RENDERER_AVAILABLE else 'NOT FOUND'}")
    print()

    dat_files = sorted([str(p) for p in _SPARC_DIR.rglob("*.dat")])
    if not dat_files:
        print(f"No .dat files found in {_SPARC_DIR}")
        return 1
    print(f"Found {len(dat_files)} galaxy files")
    print()

    rend = launch_renderer("BCM_v30_HIGH_MASS_SPLIT",
                            n_steps=len(dat_files), downsample=1)

    galaxies = []
    for i, dat_path in enumerate(dat_files):
        try:
            r = process_galaxy(dat_path)
            galaxies.append(r)
        except Exception as e:
            galaxies.append({"name": Path(dat_path).stem, "error": str(e)})

        if rend is not None and i % 10 == 0:
            done = [g for g in galaxies if "error" not in g]
            hist = np.zeros((1, 64))
            for g in done:
                idx = min(int(g["apr_max"]*64), 63)
                hist[0, idx] += 1
            if hist.max() > 0:
                hist /= hist.max()
            write_frame(rend, hist, step=i+1, n_steps=len(dat_files),
                        state=f"{i+1}/{len(dat_files)}",
                        metrics={"processed": i+1}, downsample=1)

    ok = [g for g in galaxies if "error" not in g]
    bstats = bracket_stats(ok)

    # ── Print table ───────────────────────────────────────────────────────────
    print("=" * 72)
    print("HIGH-MASS FINE SPLIT — APR by sub-bracket")
    print("=" * 72)
    print(f"\n{'Bracket':10s} {'N':>4}  {'vmax_rng':>10}  "
          f"{'APR_max_med':>12}  {'APR_out_med':>12}  "
          f"{'frac_inv':>9}  {'frac_mass':>9}")
    print("-" * 72)
    for bname, _, __ in BRACKETS:
        s = bstats.get(bname, {})
        if s.get("n", 0) == 0:
            print(f"{bname:10s} {'0':>4}  {'(empty)':>10}")
            continue
        print(f"{bname:10s} {s['n']:>4}  {s['vmax_range']:>10}  "
              f"{s['apr_max_median']:>12.4f}  "
              f"{s['apr_outer_median']:>12.4f}  "
              f"{s['frac_inversion']:>9.3f}  "
              f"{s['frac_mass_dominant']:>9.3f}")

    # ── Gates ─────────────────────────────────────────────────────────────────
    ha = bstats.get("HIGH_A", {})
    hb = bstats.get("HIGH_B", {})
    hc = bstats.get("HIGH_C", {})
    hd = bstats.get("HIGH_D", {})

    # G1: HIGH_A has lowest frac_inversion among high brackets
    high_invs = {k: bstats.get(k, {}).get("frac_inversion", 1.0)
                 for k in ["HIGH_A","HIGH_B","HIGH_C","HIGH_D"]}
    g1 = ha.get("frac_inversion", 1.0) == min(high_invs.values())

    # G2: at least one sub-bracket above 200 has APR_outer > HIGH_A
    ha_outer = ha.get("apr_outer_median", 0)
    upper_outers = [bstats.get(k, {}).get("apr_outer_median", 0)
                    for k in ["HIGH_B","HIGH_C","HIGH_D"]
                    if bstats.get(k, {}).get("n", 0) > 0]
    g2 = any(v > ha_outer for v in upper_outers)

    # G3: frac_mass does not increase monotonically across high brackets
    mass_fracs = [bstats.get(k, {}).get("frac_mass_dominant", 0)
                  for k in ["HIGH_A","HIGH_B","HIGH_C","HIGH_D"]
                  if bstats.get(k, {}).get("n", 0) > 0]
    g3 = not all(mass_fracs[i] <= mass_fracs[i+1]
                 for i in range(len(mass_fracs)-1))

    # G4: APR_outer spread > 0.10 across HIGH_B through HIGH_D
    upper_all = [bstats.get(k, {}).get("apr_outer_median", None)
                 for k in ["HIGH_B","HIGH_C","HIGH_D"]
                 if bstats.get(k, {}).get("n", 0) > 0]
    g4 = (max(upper_all) - min(upper_all)) > 0.10 if len(upper_all) >= 2 else False

    gates_pass = sum([g1, g2, g3, g4])

    print()
    print("Gates:")
    print(f"  G1 HIGH_A lowest frac_inv in high brackets: {'PASS' if g1 else 'FAIL'}")
    print(f"     invs by bracket: {high_invs}")
    print(f"  G2 Any 200+ bracket APR_outer > HIGH_A ({ha_outer:.4f}): "
          f"{'PASS' if g2 else 'FAIL'}  upper={upper_outers}")
    print(f"  G3 frac_mass non-monotonic across high: {'PASS' if g3 else 'FAIL'}"
          f"  fracs={mass_fracs}")
    print(f"  G4 APR_outer spread >0.10 in 200+ brackets: "
          f"{'PASS' if g4 else 'FAIL'}"
          f"  spread={round(max(upper_all)-min(upper_all),4) if len(upper_all)>=2 else 'n/a'}")
    print(f"  Gates passed: {gates_pass}/4")

    # ── List galaxies in each high sub-bracket ────────────────────────────────
    print()
    for bname in ["HIGH_A","HIGH_B","HIGH_C","HIGH_D"]:
        s = bstats.get(bname, {})
        if s.get("n", 0) > 0:
            print(f"{bname} ({s['vmax_range']} km/s, n={s['n']}): "
                  f"{', '.join(s['galaxies'])}")

    if gates_pass == 4:
        verdict  = "MASSIVE_BRACKET_BIFURCATION_CONFIRMED"
        hyp_keys = ["H_V30_HIGH_MASS_APR_BIFURCATION",
                    "H_V30_APR_TRACKS_BTFR_BRACKET"]
    elif gates_pass >= 2:
        verdict  = f"MASSIVE_BRACKET_SPLIT_PARTIAL_{gates_pass}_OF_4"
        hyp_keys = ["H_V30_HIGH_MASS_APR_BIFURCATION"]
    else:
        verdict  = "MASSIVE_BRACKET_APPEARS_UNIFORM"
        hyp_keys = ["H_V30_HIGH_MASS_NO_BIFURCATION"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v30_ANCHOR_PARTITION_HIGH_MASS_SPLIT_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
            "test_id":   "BCM_v30_ANCHOR_PARTITION_HIGH_MASS_SPLIT",
            "test_name": "SPARC175_HIGH_MASS_APR_FINE_SPLIT",
            "timestamp": ts,
            "foreman":   "Stephen Justin Burdick Sr.",
            "bracket_audit_context": {
                "HIGH_A_frac_inv_bracket_audit": 0.000,
                "MASSIVE_frac_inv_bracket_audit": 0.053,
                "bracket_audit_finding": "HIGH (150-200) lowest inversion, not MASSIVE",
            },
            "bracket_stats": bstats,
            "gate_results":  {"G1": g1, "G2": g2, "G3": g3, "G4": g4},
            "gates_passed":  gates_pass,
            "verdict":       verdict,
            "hypothesis_keys": hyp_keys,
            "framework_note": (
                "APR decomposition of observed SPARC rotation curves. "
                "Not a BCM solver fit. Fine split tests whether 200+ km/s "
                "systems are one class or bifurcate in substrate coupling."
            ),
        }, fh, indent=2)

    close_renderer(rend, final_state=verdict,
                   metrics={"gates_passed": gates_pass, "g1": int(g1),
                            "g2": int(g2), "g3": int(g3), "g4": int(g4)})

    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
