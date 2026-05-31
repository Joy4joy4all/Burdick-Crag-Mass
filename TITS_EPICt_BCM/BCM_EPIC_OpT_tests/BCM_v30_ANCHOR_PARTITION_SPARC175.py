# -*- coding: utf-8 -*-
"""
BCM v30 — ANCHOR PARTITION SPARC 175
=====================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Code execution: The code builder.

Purpose:
    Apply the Anchor Equation partition decomposition to all 175 SPARC
    galaxies. Compute the Anchor Partition Ratio (APR) per galaxy.
    Classify each galaxy by which term dominates the rotation curve.

Anchor Equation partition:
    Total velocity² = mass_term + substrate_term

    mass_term      = V_newton² = Vgas² + Vdisk² + Vbul²
                     (baryonic/Newtonian visible mass side)

    substrate_term = discrepancy² = Vobs² - V_newton²
                     (substrate excess / velocity-excess side)
                     This is what dark matter conventionally "explains."
                     BCM says it is substrate screening.

    APR = substrate_term / (mass_term + substrate_term)
        = discrepancy² / Vobs²

    APR → 0: mass-dominant (Newton explains most of the curve)
    APR → 1: substrate-dominant (substrate explains most)
    APR ~ 0.5: mixed-anchor

Classification:
    MASS_DOMINANT:         APR_max < 0.30
    MIXED_ANCHOR:          0.30 <= APR_max < 0.55
    SUBSTRATE_DOMINANT:    0.55 <= APR_max < 0.80
    INVERSION_TRANSITION:  APR_max >= 0.80

Per galaxy output:
    galaxy, n_points, r_max_kpc, vmax_obs, vmax_newton,
    newton_residual_mean, apr_mean, apr_max, apr_at_outer_disk,
    btfr_bracket, bcm_class, newton_win

Renderer: ACTIVE — live histogram of APR distribution as galaxies process.
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

import importlib.util

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
# Use os.path.abspath(__file__) — reliable on Windows regardless of cwd
_THIS_DIR      = Path(os.path.abspath(__file__)).parent
_SOLVER_ROOT   = _THIS_DIR.parent.parent
_GENESIS_BRAIN = _SOLVER_ROOT / "TITS_EPICt_BCM" / "genesis_brain"
_SPARC_DIR     = _SOLVER_ROOT / "data" / "sparc_raw"
_RESULTS_DIR   = _SOLVER_ROOT / "data" / "results"

for _p in [str(_SOLVER_ROOT), str(_GENESIS_BRAIN)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Load sparc_ingest by explicit file path — bypasses sys.path issues on Windows
_sparc_path = _SOLVER_ROOT / "core" / "sparc_ingest.py"
_spec = importlib.util.spec_from_file_location("sparc_ingest", str(_sparc_path))
_sparc_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sparc_mod)
load_rotation_curve  = _sparc_mod.load_rotation_curve
build_newtonian_curve = _sparc_mod.build_newtonian_curve
compute_discrepancy  = _sparc_mod.compute_discrepancy

# Renderer
try:
    from BCM_test_renderer import launch_renderer, write_frame, close_renderer
    _RENDERER_AVAILABLE = True
except ImportError:
    _RENDERER_AVAILABLE = False
    def launch_renderer(*a, **kw): return None
    def write_frame(*a, **kw):     pass
    def close_renderer(*a, **kw):  pass

EPS = 1e-9

# ── APR thresholds ────────────────────────────────────────────────────────────
APR_MASS_DOMINANT_MAX       = 0.30
APR_MIXED_MAX               = 0.55
APR_SUBSTRATE_DOMINANT_MAX  = 0.80
# >= 0.80: INVERSION_TRANSITION

# BTFR Vmax brackets (km/s)
BTFR_BRACKETS = [
    (0,   50,   "DWARF_LOW"),
    (50,  100,  "DWARF_HIGH"),
    (100, 150,  "INTERMEDIATE"),
    (150, 220,  "MILKY_WAY_CLASS"),
    (220, 9999, "MASSIVE"),
]


def classify_apr(apr_max: float) -> str:
    if apr_max < APR_MASS_DOMINANT_MAX:
        return "MASS_DOMINANT"
    elif apr_max < APR_MIXED_MAX:
        return "MIXED_ANCHOR"
    elif apr_max < APR_SUBSTRATE_DOMINANT_MAX:
        return "SUBSTRATE_DOMINANT"
    else:
        return "INVERSION_TRANSITION"


def btfr_bracket(vmax: float) -> str:
    for vlo, vhi, label in BTFR_BRACKETS:
        if vlo <= vmax < vhi:
            return label
    return "UNKNOWN"


def process_galaxy(dat_path: str) -> Dict[str, Any]:
    """
    Compute APR decomposition for one SPARC galaxy.
    Returns dict of per-galaxy results.
    """
    name = Path(dat_path).stem.split("_")[0]

    rot       = load_rotation_curve(dat_path)
    radii     = rot["radius_kpc"]
    vobs      = rot["Vobs_kms"]

    if len(radii) == 0 or len(vobs) == 0:
        return {"name": name, "error": "empty_data"}

    v_newton  = build_newtonian_curve(rot)
    disc      = compute_discrepancy(rot)

    # Move to xp (cupy if available) for bulk operations
    vobs_sq     = xp.array(vobs)**2
    vnewton_sq  = xp.array(v_newton)**2
    disc_sq     = xp.maximum(vobs_sq - vnewton_sq, 0.0)  # clamp negative

    # APR per data point
    apr = disc_sq / xp.maximum(vobs_sq, EPS)

    apr_mean      = float(xp.mean(apr))
    apr_max       = float(xp.max(apr))
    apr_min       = float(xp.min(apr))

    # APR at outer disk (last 20% of radial range)
    outer_start = int(len(radii) * 0.80)
    apr_outer   = float(xp.mean(apr[outer_start:])) if outer_start < len(apr) else apr_mean

    vmax_obs     = float(np.max(vobs))
    vmax_newton  = float(np.max(v_newton))
    r_max        = float(radii[-1])

    # Newton residual: mean |Vobs - V_newton| / Vobs
    newton_resid = float(xp.mean(
        xp.abs(xp.array(vobs) - xp.array(v_newton)) / xp.maximum(xp.array(vobs), EPS)
    ))

    # Newton win: Newton explains > 70% of curve (APR_max < 0.30)
    newton_win = apr_max < APR_MASS_DOMINANT_MAX

    bcm_class  = classify_apr(apr_max)
    bracket    = btfr_bracket(vmax_obs)

    return {
        "name":              name,
        "n_points":          int(len(radii)),
        "r_max_kpc":         round(r_max, 2),
        "vmax_obs":          round(vmax_obs, 1),
        "vmax_newton":       round(vmax_newton, 1),
        "newton_residual_mean": round(newton_resid, 4),
        "apr_mean":          round(apr_mean, 4),
        "apr_max":           round(apr_max, 4),
        "apr_min":           round(apr_min, 4),
        "apr_outer_disk":    round(apr_outer, 4),
        "btfr_bracket":      bracket,
        "bcm_class":         bcm_class,
        "newton_win":        newton_win,
        "apr_profile":       [round(float(v), 4) for v in (xp.asnumpy(apr) if hasattr(xp, "asnumpy") else np.array(apr))],
        "radii_kpc":         [round(float(v), 3) for v in radii],
    }


def render_histogram(rend, results: List[Dict], step: int, total: int):
    """Render APR distribution as a 1D histogram for the renderer."""
    if rend is None:
        return
    if not results:
        return

    aprs    = [r["apr_max"] for r in results if "error" not in r]
    classes = {
        "MASS_DOMINANT":        sum(1 for r in results if r.get("bcm_class")=="MASS_DOMINANT"),
        "MIXED_ANCHOR":         sum(1 for r in results if r.get("bcm_class")=="MIXED_ANCHOR"),
        "SUBSTRATE_DOMINANT":   sum(1 for r in results if r.get("bcm_class")=="SUBSTRATE_DOMINANT"),
        "INVERSION_TRANSITION": sum(1 for r in results if r.get("bcm_class")=="INVERSION_TRANSITION"),
    }

    # Build histogram as 1-row field (64 bins, APR 0→1)
    n_bins = 64
    hist   = np.zeros((1, n_bins))
    for apr in aprs:
        bin_idx = min(int(apr * n_bins), n_bins - 1)
        hist[0, bin_idx] += 1
    if hist.max() > 0:
        hist /= hist.max()  # normalize

    last = results[-1]
    write_frame(
        rend, hist,
        step=step, n_steps=total,
        state=f"Galaxy {step}/{total}: {last.get('name','?')} [{last.get('bcm_class','?')}]",
        metrics={
            "processed":       step,
            "mass_dominant":   classes["MASS_DOMINANT"],
            "mixed_anchor":    classes["MIXED_ANCHOR"],
            "substrate_dom":   classes["SUBSTRATE_DOMINANT"],
            "inversion":       classes["INVERSION_TRANSITION"],
            "apr_last":        last.get("apr_max", 0),
            "newton_wins":     sum(1 for r in results if r.get("newton_win", False)),
        },
        downsample=1,
    )


def run_test():
    print("BCM v30 — ANCHOR PARTITION SPARC 175")
    print(f"Backend:  {_BACKEND}")
    print(f"Renderer: {'ACTIVE' if _RENDERER_AVAILABLE else 'NOT FOUND'}")
    print()

    # Find all SPARC dat files
    if not _SPARC_DIR.exists():
        print(f"SPARC data directory not found: {_SPARC_DIR}")
        print("Place _rotmod.dat files there and re-run.")
        return 1

    dat_files = sorted([
        str(p) for p in _SPARC_DIR.rglob("*.dat")
    ])

    if not dat_files:
        print(f"No .dat files found in {_SPARC_DIR}")
        return 1

    print(f"Found {len(dat_files)} galaxy files")
    print()

    total = len(dat_files)
    rend  = launch_renderer("BCM_v30_ANCHOR_PARTITION_SPARC175",
                             n_steps=total, downsample=1)

    results = []
    errors  = []

    for i, dat_path in enumerate(dat_files):
        try:
            r = process_galaxy(dat_path)
            if "error" in r:
                errors.append(r)
                print(f"  SKIP {r['name']}: {r['error']}")
            else:
                results.append(r)
                if i % 10 == 0 or i < 5:
                    print(f"  [{i+1:3d}/{total}] {r['name']:20s} "
                          f"vmax={r['vmax_obs']:6.1f}  "
                          f"APR_max={r['apr_max']:.3f}  "
                          f"class={r['bcm_class']}")
        except Exception as e:
            errors.append({"name": Path(dat_path).stem, "error": str(e)})

        render_histogram(rend, results, i+1, total)

    # ── Summary ───────────────────────────────────────────────────────────────
    n_ok = len(results)

    class_counts = {
        "MASS_DOMINANT":        [r for r in results if r["bcm_class"]=="MASS_DOMINANT"],
        "MIXED_ANCHOR":         [r for r in results if r["bcm_class"]=="MIXED_ANCHOR"],
        "SUBSTRATE_DOMINANT":   [r for r in results if r["bcm_class"]=="SUBSTRATE_DOMINANT"],
        "INVERSION_TRANSITION": [r for r in results if r["bcm_class"]=="INVERSION_TRANSITION"],
    }

    bracket_counts = {}
    for r in results:
        b = r["btfr_bracket"]
        bracket_counts[b] = bracket_counts.get(b, 0) + 1

    newton_wins     = sum(1 for r in results if r["newton_win"])
    substrate_wins  = n_ok - newton_wins

    apr_all = [r["apr_max"] for r in results]
    apr_mean_global = float(xp.mean(xp.array(apr_all))) if apr_all else 0.0
    apr_median      = float(xp.median(xp.array(apr_all))) if apr_all else 0.0

    print()
    print("=" * 60)
    print("ANCHOR PARTITION SUMMARY")
    print("=" * 60)
    print(f"Galaxies processed: {n_ok} / {total}")
    print(f"Errors:             {len(errors)}")
    print()
    print(f"APR_max global mean:   {apr_mean_global:.4f}")
    print(f"APR_max global median: {apr_median:.4f}")
    print()
    print("BCM Classification:")
    for cls, items in class_counts.items():
        pct = 100*len(items)/max(n_ok,1)
        print(f"  {cls:25s}: {len(items):3d}  ({pct:5.1f}%)")
    print()
    print("BTFR Bracket:")
    for b, cnt in sorted(bracket_counts.items()):
        print(f"  {b:20s}: {cnt:3d}")
    print()
    print(f"Newton explains curve (APR_max<0.30): {newton_wins} / {n_ok}  "
          f"({100*newton_wins/max(n_ok,1):.1f}%)")
    print(f"Substrate dominant  (APR_max>=0.30): {substrate_wins} / {n_ok}  "
          f"({100*substrate_wins/max(n_ok,1):.1f}%)")

    # Top 10 substrate-dominant
    top_sub = sorted(results, key=lambda r: -r["apr_max"])[:10]
    print()
    print("Top 10 by APR_max (most substrate-dominant):")
    for r in top_sub:
        print(f"  {r['name']:20s} APR_max={r['apr_max']:.4f}  "
              f"vmax={r['vmax_obs']:6.1f}  class={r['bcm_class']}")

    # Where BCM gains over Newton (highest substrate excess at outer disk)
    top_outer = sorted(results, key=lambda r: -r["apr_outer_disk"])[:10]
    print()
    print("Top 10 by APR at outer disk (substrate excess at large radius):")
    for r in top_outer:
        print(f"  {r['name']:20s} APR_outer={r['apr_outer_disk']:.4f}  "
              f"vmax={r['vmax_obs']:6.1f}  bracket={r['btfr_bracket']}")

    # Verdict
    if apr_median >= 0.55:
        verdict   = "SUBSTRATE_DOMINANT_ACROSS_SPARC175"
        hyp_keys  = ["H_V30_ANCHOR_PARTITION_SUBSTRATE_DOMINANT",
                     "H_V30_APR_TRACKS_BTFR_BRACKET"]
    elif apr_median >= 0.30:
        verdict   = "MIXED_ANCHOR_REGIME_SPARC175"
        hyp_keys  = ["H_V30_ANCHOR_PARTITION_MIXED_REGIME",
                     "H_V30_APR_TRACKS_BTFR_BRACKET"]
    else:
        verdict   = "MASS_DOMINANT_SPARC175_UNEXPECTED"
        hyp_keys  = ["H_V30_ANCHOR_PARTITION_MASS_DOMINANT"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v30_ANCHOR_PARTITION_SPARC175_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
            "test_id":   "BCM_v30_ANCHOR_PARTITION_SPARC175",
            "test_name": "SPARC175_ANCHOR_PARTITION_RATIO",
            "timestamp": ts,
            "foreman":   "Stephen Justin Burdick Sr.",

            "apr_thresholds": {
                "MASS_DOMINANT_max":      APR_MASS_DOMINANT_MAX,
                "MIXED_ANCHOR_max":       APR_MIXED_MAX,
                "SUBSTRATE_DOMINANT_max": APR_SUBSTRATE_DOMINANT_MAX,
            },

            "summary": {
                "n_galaxies":        n_ok,
                "n_errors":          len(errors),
                "apr_mean":          round(apr_mean_global, 4),
                "apr_median":        round(apr_median, 4),
                "newton_wins":       newton_wins,
                "substrate_wins":    substrate_wins,
                "class_counts":      {k: len(v) for k, v in class_counts.items()},
                "bracket_counts":    bracket_counts,
            },

            "results":   results,
            "errors":    errors,
            "verdict":   verdict,
            "hypothesis_keys": hyp_keys,

            "framework_note": (
                "APR = Vobs_disc² / Vobs². "
                "substrate_term = Vobs² - V_newton². "
                "Real SPARC data. Not proxy values. "
                "APR is a decomposition metric, not a BCM solver output. "
                "Does not claim substrate is the correct mechanism — "
                "classifies where it would need to be largest."
            ),
        }, fh, indent=2)

    close_renderer(rend, final_state=verdict,
                   metrics={"apr_median": round(apr_median, 4),
                            "substrate_wins": substrate_wins,
                            "n_galaxies": n_ok})

    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
