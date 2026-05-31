# -*- coding: utf-8 -*-
"""
BCM v30 — ANCHOR PARTITION REGIME MAP (FINAL)
==============================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Code execution: The code builder.

Purpose:
    Consolidate the three-test Anchor Partition chain into a
    publishable regime map for all 175 SPARC galaxies.

Chain summary:
    Test 1 (SPARC175):       APR_median=0.693, 152/175 substrate-side
    Test 2 (Bracket Audit):  3/4 gates, 125 km/s snap delta=+0.193 confirmed
    Test 3 (High-Mass Split):4/4 gates, bifurcation confirmed in 200+ bracket

Five-regime structure identified:
    REGIME 1 — SUBSTRATE_PLATEAU
        LOW/MID (50-150 km/s)
        APR_outer typically > 0.65
        BCM strongest (88%/82% Paper A wins)
        Outer disk substrate fraction highest

    REGIME 2 — DWARF_INTERMEDIATE
        DWARF (0-50 km/s)
        APR_outer ~0.53 — substrate present but not maximal
        BCM competitive (55% Paper A wins)
        Low absolute chi-squared for all models

    REGIME 3 — SUPPRESSION_VALLEY
        HIGH_A + HIGH_B + HIGH_C (150-300 km/s)
        APR_outer drops to 0.39-0.47
        Mass-stiff / Newton-competitive regime
        frac_mass_dominant highest (0.167-0.333)
        BCM weakest per Paper A (61-67% wins)

    REGIME 4 — ROOT_REENTRY
        HIGH_D (300+ km/s)
        APR_outer rises back to 0.59
        7 galaxies: ESO563-G021, NGC2841, NGC5985, UGC02487,
                    UGC02885, UGC02953, UGC11914
        Substrate fraction re-emerges at ROOT scale

    REGIME 5 — MASS_FLOOR
        APR_max < 0.30 regardless of velocity
        Newton explains most of the curve
        23 galaxies across all brackets

Regime assignment per galaxy:
    MASS_FLOOR first (APR_max < 0.30)
    Then velocity + APR_outer for remaining:
        vmax < 50:                DWARF_INTERMEDIATE
        50 <= vmax < 150:
            APR_outer >= 0.65:    SUBSTRATE_PLATEAU
            APR_outer <  0.65:    MIXED_TRANSITION (edge cases)
        150 <= vmax < 300:        SUPPRESSION_VALLEY
        vmax >= 300:              ROOT_REENTRY

Output:
    Per galaxy: name, vmax, APR_max, APR_outer, regime label
    Per regime: n, vmax range, APR stats, galaxy list
    Snap analysis at 125 km/s
    Full 175-galaxy regime table
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

REGIME_LABELS = [
    "MASS_FLOOR",
    "DWARF_INTERMEDIATE",
    "SUBSTRATE_PLATEAU",
    "MIXED_TRANSITION",
    "SUPPRESSION_VALLEY",
    "ROOT_REENTRY",
]

REGIME_DESC = {
    "MASS_FLOOR":          "APR_max<0.30, Newton explains curve",
    "DWARF_INTERMEDIATE":  "vmax<50, substrate present, low absolute scale",
    "SUBSTRATE_PLATEAU":   "50-150 km/s, strongest substrate fraction",
    "MIXED_TRANSITION":    "50-150 km/s edge case, APR_outer<0.65",
    "SUPPRESSION_VALLEY":  "150-300 km/s, mass-stiff, substrate suppressed",
    "ROOT_REENTRY":        "300+ km/s, substrate fraction recovers at ROOT scale",
}


def assign_regime(vmax: float, apr_max: float, apr_outer: float) -> str:
    if apr_max < 0.30:
        return "MASS_FLOOR"
    if vmax < 50:
        return "DWARF_INTERMEDIATE"
    if vmax < 150:
        return "SUBSTRATE_PLATEAU" if apr_outer >= 0.65 else "MIXED_TRANSITION"
    if vmax < 300:
        return "SUPPRESSION_VALLEY"
    return "ROOT_REENTRY"


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
    apr_max     = float(xp.max(apr))
    outer_start = int(len(radii) * 0.80)
    apr_outer   = float(xp.mean(apr[outer_start:])) if outer_start < len(apr) else float(xp.mean(apr))
    apr_mean    = float(xp.mean(apr))

    regime = assign_regime(vmax_obs, apr_max, apr_outer)

    return {
        "name":      name,
        "vmax":      round(vmax_obs, 1),
        "apr_max":   round(apr_max, 4),
        "apr_mean":  round(apr_mean, 4),
        "apr_outer": round(apr_outer, 4),
        "regime":    regime,
    }


def regime_stats(galaxies: List[Dict]) -> Dict[str, Any]:
    stats = {}
    for label in REGIME_LABELS:
        sub = [g for g in galaxies if g.get("regime") == label]
        if not sub:
            stats[label] = {"n": 0, "description": REGIME_DESC[label]}
            continue
        aprs   = [g["apr_max"] for g in sub]
        outers = [g["apr_outer"] for g in sub]
        vmaxs  = [g["vmax"] for g in sub]
        stats[label] = {
            "n":               len(sub),
            "description":     REGIME_DESC[label],
            "vmax_range":      f"{min(vmaxs):.0f}–{max(vmaxs):.0f}",
            "apr_max_mean":    round(float(np.mean(aprs)), 4),
            "apr_max_median":  round(float(np.median(aprs)), 4),
            "apr_outer_mean":  round(float(np.mean(outers)), 4),
            "apr_outer_median":round(float(np.median(outers)), 4),
            "galaxies":        sorted([g["name"] for g in sub]),
        }
    return stats


def run_test():
    print("BCM v30 — ANCHOR PARTITION REGIME MAP (FINAL)")
    print(f"Backend:  {_BACKEND}")
    print(f"Renderer: {'ACTIVE' if _RENDERER_AVAILABLE else 'NOT FOUND'}")
    print()

    dat_files = sorted([str(p) for p in _SPARC_DIR.rglob("*.dat")])
    if not dat_files:
        print(f"No .dat files in {_SPARC_DIR}")
        return 1
    print(f"Found {len(dat_files)} galaxy files")
    print()

    rend = launch_renderer("BCM_v30_REGIME_MAP_FINAL",
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
                        state=f"Galaxy {i+1}/{len(dat_files)}: {Path(dat_path).stem[:20]}",
                        metrics={"processed": i+1,
                                 "regime": galaxies[-1].get("regime","?") if galaxies else "?"},
                        downsample=1)

    ok = [g for g in galaxies if "error" not in g]
    rstats = regime_stats(ok)

    # ── Regime summary ────────────────────────────────────────────────────────
    print("=" * 70)
    print("ANCHOR PARTITION REGIME MAP — 175 SPARC GALAXIES")
    print("=" * 70)
    print()
    print(f"{'Regime':22s} {'N':>4}  {'vmax':>12}  "
          f"{'APR_max_med':>12}  {'APR_out_med':>12}")
    print("-" * 68)
    for label in REGIME_LABELS:
        s = rstats.get(label, {})
        if s.get("n", 0) == 0:
            print(f"{label:22s} {'0':>4}  {'(empty)':>12}")
            continue
        print(f"{label:22s} {s['n']:>4}  {s['vmax_range']:>12}  "
              f"{s['apr_max_median']:>12.4f}  "
              f"{s['apr_outer_median']:>12.4f}")

    # ── Full 175-galaxy table ─────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("FULL GALAXY REGIME TABLE (sorted by vmax)")
    print("=" * 70)
    print(f"{'Galaxy':20s} {'vmax':>7}  {'APR_max':>8}  {'APR_outer':>10}  {'Regime'}")
    print("-" * 70)
    for g in sorted(ok, key=lambda x: x["vmax"]):
        print(f"{g['name']:20s} {g['vmax']:>7.1f}  "
              f"{g['apr_max']:>8.4f}  "
              f"{g['apr_outer']:>10.4f}  {g['regime']}")

    # ── Snap analysis ─────────────────────────────────────────────────────────
    below = [g for g in ok if g["vmax"] < 125]
    above = [g for g in ok if g["vmax"] >= 125]
    snap_below = float(np.mean([g["apr_outer"] for g in below])) if below else 0
    snap_above = float(np.mean([g["apr_outer"] for g in above])) if above else 0

    print()
    print("=" * 70)
    print("SNAP ANALYSIS — 125 km/s boundary")
    print("=" * 70)
    print(f"  Below 125 km/s: APR_outer_mean={snap_below:.4f}  (n={len(below)})")
    print(f"  Above 125 km/s: APR_outer_mean={snap_above:.4f}  (n={len(above)})")
    print(f"  Delta:          {snap_below-snap_above:+.4f}"
          f"  {'snap confirmed' if snap_below-snap_above > 0.05 else 'weak'}")

    # ── Structure summary ─────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("VALLEY-AND-RETURN STRUCTURE")
    print("=" * 70)
    for label in ["SUBSTRATE_PLATEAU","DWARF_INTERMEDIATE",
                  "SUPPRESSION_VALLEY","ROOT_REENTRY","MASS_FLOOR","MIXED_TRANSITION"]:
        s = rstats.get(label, {})
        if s.get("n", 0) == 0:
            continue
        print(f"  {label:22s}: n={s['n']:3d}  "
              f"APR_outer_med={s.get('apr_outer_median',0):.4f}  "
              f"vmax={s.get('vmax_range','—')}")

    verdict  = "ANCHOR_PARTITION_REGIME_MAP_COMPLETE"
    hyp_keys = [
        "H_V30_ANCHOR_PARTITION_SUBSTRATE_DOMINANT",
        "H_V30_APR_TRACKS_BTFR_BRACKET",
        "H_V30_HIGH_MASS_APR_BIFURCATION",
        "H_V30_ANCHOR_REGIME_MAP_SPARC175",
    ]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v30_ANCHOR_PARTITION_REGIME_MAP_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
            "test_id":   "BCM_v30_ANCHOR_PARTITION_REGIME_MAP",
            "test_name": "SPARC175_ANCHOR_PARTITION_REGIME_MAP_FINAL",
            "timestamp": ts,
            "foreman":   "Stephen Justin Burdick Sr.",
            "chain_summary": {
                "test1_sparc175":    "APR_median=0.693, 152/175 substrate-side",
                "test2_bracket":     "3/4 gates, 125 km/s snap delta=+0.193",
                "test3_high_mass":   "4/4 gates, bifurcation confirmed in 200+ bracket",
            },
            "five_regime_structure": {
                "SUBSTRATE_PLATEAU":  "50-150 km/s, strongest substrate coupling",
                "DWARF_INTERMEDIATE": "0-50 km/s, intermediate",
                "SUPPRESSION_VALLEY": "150-300 km/s, mass-stiff, Newton-competitive",
                "ROOT_REENTRY":       "300+ km/s, substrate recovers at ROOT scale",
                "MASS_FLOOR":         "APR_max<0.30, Newton explains curve, any velocity",
            },
            "snap_analysis": {
                "boundary_kms":    125,
                "apr_outer_below": round(snap_below, 4),
                "apr_outer_above": round(snap_above, 4),
                "snap_delta":      round(snap_below - snap_above, 4),
            },
            "regime_stats":  rstats,
            "galaxy_map":    sorted(ok, key=lambda x: x["vmax"]),
            "verdict":       verdict,
            "hypothesis_keys": hyp_keys,
            "framework_note": (
                "APR = (Vobs² - V_newton²) / Vobs². "
                "Decomposition of observed SPARC rotation curves. "
                "Not a BCM solver fit. "
                "Does not prove substrate mechanism. "
                "Maps where non-baryonic term is largest / smallest "
                "if Anchor Equation decomposition is applied."
            ),
        }, fh, indent=2)

    close_renderer(rend, final_state=verdict,
                   metrics={"n_regimes": len([r for r in REGIME_LABELS
                                              if rstats.get(r,{}).get("n",0)>0]),
                            "snap_delta": round(snap_below-snap_above, 4)})

    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
