# -*- coding: utf-8 -*-
"""
BCM v30 — ANCHOR PARTITION SPARC 175 BRACKET AUDIT
====================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Code execution: The code builder.

Purpose:
    Extend the Anchor Partition SPARC175 result by auditing whether
    APR tracks the Paper A bracket-stratified performance pattern.

Paper A v6 established (bracket-stratified):
    Dwarf  (V<50):   55% BCM wins,  chi2 mean low
    Low    (50-100): 88% BCM wins   <- strongest bracket
    Mid    (100-150):82% BCM wins
    High   (150-200):67% BCM wins
    Massive (V>200): 61% BCM wins,  TF exponent alpha=-0.29 (breaks)

    The massive bracket is where substrate-velocity coupling weakens.
    Paper A notes this as "scale-dependent phase transition."

Test question:
    Does APR track this bracket performance pattern?
    Specifically:
    - Do Low/Mid brackets show higher APR at outer disk
      (where BCM wins most)?
    - Does the Massive bracket show lower or inverted APR
      (where TF exponent collapses)?
    - Is INVERSION_TRANSITION concentrated in dwarf/low
      (deepest substrate dominance)?

Output per bracket:
    n_galaxies
    APR_max mean, median
    APR_outer mean, median
    fraction INVERSION_TRANSITION
    fraction MASS_DOMINANT
    Newton win rate
    correlation(vmax, APR_max) within bracket

Full-sample:
    correlation(vmax, APR_max)
    correlation(vmax, APR_outer)
    APR snap analysis: does APR transition sharply near V=125 km/s
    (the mid/high boundary where Paper A shows peak TF alpha)?

Gates:
    G1: Low/Mid APR_outer > Massive APR_outer
        (substrate excess higher where BCM wins most)
    G2: Massive bracket has lowest fraction INVERSION_TRANSITION
        (deepest substrate dominance NOT in massive systems)
    G3: INVERSION_TRANSITION concentrated in dwarf/low brackets
    G4: APR_max negatively correlates with vmax across full sample
        (higher velocity = less substrate-dominant)
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

# ── Path resolution ───────────────────────────────────────────────────────────
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

# ── BTFR brackets — match Paper A v6 exactly ─────────────────────────────────
BRACKETS = [
    ("DWARF",   0,   50),
    ("LOW",     50,  100),
    ("MID",     100, 150),
    ("HIGH",    150, 200),
    ("MASSIVE", 200, 9999),
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


def pearson_r(x: List[float], y: List[float]) -> float:
    if len(x) < 3:
        return 0.0
    xa = np.array(x, dtype=float)
    ya = np.array(y, dtype=float)
    mx, my = xa.mean(), ya.mean()
    num = ((xa - mx) * (ya - my)).sum()
    den = (np.sqrt(((xa-mx)**2).sum()) * np.sqrt(((ya-my)**2).sum()))
    return float(num / (den + EPS))


def process_galaxy(dat_path: str) -> Dict[str, Any]:
    name    = Path(dat_path).stem.split("_")[0]
    rot     = load_rotation_curve(dat_path)
    radii   = rot["radius_kpc"]
    vobs    = rot["Vobs_kms"]
    if len(radii) == 0:
        return {"name": name, "error": "empty"}

    v_newton  = build_newtonian_curve(rot)
    vobs_sq   = vobs**2
    vnewt_sq  = v_newton**2
    disc_sq   = xp.maximum(xp.array(vobs_sq) - xp.array(vnewt_sq), 0.0)
    apr       = disc_sq / xp.maximum(xp.array(vobs_sq), EPS)

    vmax_obs  = float(np.max(vobs))
    outer_start = int(len(radii) * 0.80)
    apr_outer = float(xp.mean(xp.array(apr[outer_start:]))) if outer_start < len(apr) else float(xp.mean(xp.array(apr)))

    return {
        "name":        name,
        "vmax":        round(vmax_obs, 1),
        "apr_max":     round(float(xp.max(xp.array(apr))), 4),
        "apr_mean":    round(float(xp.mean(xp.array(apr))), 4),
        "apr_outer":   round(apr_outer, 4),
        "bcm_class":   classify_apr(float(xp.max(xp.array(apr)))),
        "bracket":     get_bracket(vmax_obs),
        "newton_win":  float(xp.max(xp.array(apr))) < APR_MASS_DOMINANT_MAX,
    }


def bracket_stats(galaxies: List[Dict]) -> Dict[str, Any]:
    stats = {}
    for bname, blo, bhi in BRACKETS:
        sub = [g for g in galaxies
               if blo <= g["vmax"] < bhi and "error" not in g]
        if not sub:
            stats[bname] = {"n": 0}
            continue
        aprs       = [g["apr_max"] for g in sub]
        aprs_outer = [g["apr_outer"] for g in sub]
        vmaxs      = [g["vmax"] for g in sub]
        n_inv      = sum(1 for g in sub if g["bcm_class"] == "INVERSION_TRANSITION")
        n_mass     = sum(1 for g in sub if g["bcm_class"] == "MASS_DOMINANT")
        n_newton   = sum(1 for g in sub if g["newton_win"])
        r_vmax_apr = pearson_r(vmaxs, aprs)

        stats[bname] = {
            "n":                    len(sub),
            "vmax_range":           f"{blo}-{bhi}",
            "apr_max_mean":         round(float(np.mean(aprs)), 4),
            "apr_max_median":       round(float(np.median(aprs)), 4),
            "apr_outer_mean":       round(float(np.mean(aprs_outer)), 4),
            "apr_outer_median":     round(float(np.median(aprs_outer)), 4),
            "frac_inversion":       round(n_inv / max(len(sub), 1), 3),
            "frac_mass_dominant":   round(n_mass / max(len(sub), 1), 3),
            "newton_win_rate":      round(n_newton / max(len(sub), 1), 3),
            "r_vmax_apr_max":       round(r_vmax_apr, 4),
            "paper_a_bcm_win_rate": {
                "DWARF":   0.55, "LOW": 0.88, "MID": 0.82,
                "HIGH": 0.67, "MASSIVE": 0.61
            }.get(bname, None),
        }
    return stats


def run_test():
    print("BCM v30 — ANCHOR PARTITION SPARC 175 BRACKET AUDIT")
    print(f"Backend:  {_BACKEND}")
    print(f"Renderer: {'ACTIVE' if _RENDERER_AVAILABLE else 'NOT FOUND'}")
    print()

    dat_files = sorted([str(p) for p in _SPARC_DIR.rglob("*.dat")])
    if not dat_files:
        print(f"No .dat files found in {_SPARC_DIR}")
        return 1

    print(f"Found {len(dat_files)} galaxy files")
    print()

    rend = launch_renderer("BCM_v30_BRACKET_AUDIT",
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
                        state=f"galaxy {i+1}/{len(dat_files)}",
                        metrics={"processed": i+1}, downsample=1)

    ok = [g for g in galaxies if "error" not in g]

    # ── Bracket statistics ────────────────────────────────────────────────────
    bstats = bracket_stats(ok)

    # ── Full-sample correlations ──────────────────────────────────────────────
    all_vmax       = [g["vmax"] for g in ok]
    all_apr_max    = [g["apr_max"] for g in ok]
    all_apr_outer  = [g["apr_outer"] for g in ok]

    r_vmax_aprmax   = pearson_r(all_vmax, all_apr_max)
    r_vmax_aprouter = pearson_r(all_vmax, all_apr_outer)

    # ── Snap analysis: V=125 (mid/high boundary) ──────────────────────────────
    below_125 = [g for g in ok if g["vmax"] < 125]
    above_125 = [g for g in ok if g["vmax"] >= 125]
    apr_below = float(np.mean([g["apr_outer"] for g in below_125])) if below_125 else 0
    apr_above = float(np.mean([g["apr_outer"] for g in above_125])) if above_125 else 0
    snap_delta = apr_below - apr_above

    # ── Gates ─────────────────────────────────────────────────────────────────
    low_outer    = bstats.get("LOW", {}).get("apr_outer_mean", 0)
    mid_outer    = bstats.get("MID", {}).get("apr_outer_mean", 0)
    massive_outer = bstats.get("MASSIVE", {}).get("apr_outer_mean", 0)

    g1 = (low_outer > massive_outer) and (mid_outer > massive_outer)

    massive_inv = bstats.get("MASSIVE", {}).get("frac_inversion", 1.0)
    other_inv   = [bstats.get(b, {}).get("frac_inversion", 0)
                   for b in ["DWARF","LOW","MID","HIGH"]]
    g2 = all(massive_inv <= v for v in other_inv)

    dwarf_inv = bstats.get("DWARF", {}).get("frac_inversion", 0)
    low_inv   = bstats.get("LOW",   {}).get("frac_inversion", 0)
    g3 = (dwarf_inv > massive_inv) or (low_inv > massive_inv)

    g4 = r_vmax_aprmax < -0.10   # negative correlation vmax vs APR

    gates_pass = sum([g1, g2, g3, g4])

    # ── Print ─────────────────────────────────────────────────────────────────
    print("=" * 70)
    print("BRACKET AUDIT — APR vs Paper A performance pattern")
    print("=" * 70)
    print(f"\n{'Bracket':10s} {'N':>4}  {'APR_max_med':>12}  {'APR_out_med':>12}  "
          f"{'frac_inv':>9}  {'frac_mass':>9}  {'PaperA_win':>10}")
    print("-" * 70)
    for bname, _, __ in BRACKETS:
        s = bstats.get(bname, {})
        if s.get("n", 0) == 0:
            continue
        print(f"{bname:10s} {s['n']:>4}  "
              f"{s['apr_max_median']:>12.4f}  "
              f"{s['apr_outer_median']:>12.4f}  "
              f"{s['frac_inversion']:>9.3f}  "
              f"{s['frac_mass_dominant']:>9.3f}  "
              f"{str(s['paper_a_bcm_win_rate']):>10}")

    print()
    print(f"Full-sample correlations:")
    print(f"  r(vmax, APR_max):   {r_vmax_aprmax:+.4f}")
    print(f"  r(vmax, APR_outer): {r_vmax_aprouter:+.4f}")
    print()
    print(f"Snap analysis at V=125 km/s (mid/high boundary):")
    print(f"  APR_outer below 125: {apr_below:.4f}  (n={len(below_125)})")
    print(f"  APR_outer above 125: {apr_above:.4f}  (n={len(above_125)})")
    print(f"  Delta (below-above): {snap_delta:+.4f}"
          f"  {'snap confirmed' if snap_delta > 0.05 else 'no clear snap'}")
    print()
    print("Gates:")
    print(f"  G1 Low/Mid APR_outer > Massive: {'PASS' if g1 else 'FAIL'}")
    print(f"  G2 Massive lowest frac_inversion: {'PASS' if g2 else 'FAIL'}")
    print(f"  G3 INVERSION concentrated dwarf/low: {'PASS' if g3 else 'FAIL'}")
    print(f"  G4 r(vmax,APR_max) < -0.10: {'PASS' if g4 else 'FAIL'}  "
          f"(r={r_vmax_aprmax:+.4f})")
    print(f"  Gates passed: {gates_pass}/4")

    if gates_pass == 4:
        verdict   = "APR_TRACKS_PAPER_A_BRACKET_PATTERN_CONFIRMED"
        hyp_keys  = ["H_V30_APR_TRACKS_BTFR_BRACKET",
                     "H_V30_SUBSTRATE_DOMINANT_OUTER_DISK",
                     "H_V30_MASSIVE_BRACKET_APR_SUPPRESSED"]
    elif gates_pass >= 2:
        verdict   = f"APR_PARTIAL_BRACKET_TRACKING_{gates_pass}_OF_4"
        hyp_keys  = ["H_V30_APR_TRACKS_BTFR_BRACKET"]
    else:
        verdict   = "APR_BRACKET_TRACKING_NOT_CONFIRMED"
        hyp_keys  = ["H_V30_APR_BRACKET_AUDIT_INCONCLUSIVE"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v30_ANCHOR_PARTITION_BRACKET_AUDIT_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
            "test_id":   "BCM_v30_ANCHOR_PARTITION_BRACKET_AUDIT",
            "test_name": "SPARC175_APR_BRACKET_TRACKING_AUDIT",
            "timestamp": ts,
            "foreman":   "Stephen Justin Burdick Sr.",
            "paper_a_context": {
                "bracket_win_rates":    {"DWARF":0.55,"LOW":0.88,"MID":0.82,
                                         "HIGH":0.67,"MASSIVE":0.61},
                "tf_exponent_massive":  -0.29,
                "tf_exponent_full":     3.42,
                "paper_a_snap_region":  "V~125 km/s (mid/high boundary, peak alpha)",
            },
            "bracket_stats":         bstats,
            "full_sample": {
                "r_vmax_apr_max":    round(r_vmax_aprmax, 4),
                "r_vmax_apr_outer":  round(r_vmax_aprouter, 4),
                "snap_apr_below_125": round(apr_below, 4),
                "snap_apr_above_125": round(apr_above, 4),
                "snap_delta":         round(snap_delta, 4),
            },
            "gate_results":  {"G1": g1, "G2": g2, "G3": g3, "G4": g4},
            "gates_passed":  gates_pass,
            "verdict":       verdict,
            "hypothesis_keys": hyp_keys,
            "framework_note": (
                "APR is a decomposition of observed SPARC rotation curves "
                "against Newtonian baryonic prediction. Not a BCM solver fit. "
                "Paper A win rates are from BCM solver chi-squared comparison. "
                "APR-bracket correlation does not prove BCM mechanism — "
                "it shows where non-baryonic term is largest vs smallest."
            ),
        }, fh, indent=2)

    close_renderer(rend, final_state=verdict,
                   metrics={"gates_passed": gates_pass,
                            "snap_delta": round(snap_delta, 4),
                            "r_vmax_apr": round(r_vmax_aprmax, 4)})

    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
