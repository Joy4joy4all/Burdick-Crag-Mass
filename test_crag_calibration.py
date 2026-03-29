"""
Crag Mass Calibration — Find kappa_BH
======================================
Stephen Justin Burdick, 2026 — Emerald Entities LLC

Sweeps kappa_BH on 3 calibration galaxies with known M_BH.
Finds the single global coupling constant that minimizes
mean RMS across calibration set without overfitting.

Calibration galaxies (known M_BH, Kormendy & Ho 2013):
    NGC2841  V=283  log(M_BH)=8.11
    NGC7331  V=240  log(M_BH)=7.86
    NGC3521  V=229  log(M_BH)=7.70

Run: python test_crag_calibration.py
"""

import numpy as np
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.substrate_solver import SubstrateSolver
from core.sparc_ingest import load_galaxy
from core.rotation_compare import compare_rotation
from Burdick_Crag_Mass import inject_crag_mass as inject_bh, energy_spread_diagnostic, CALIBRATION_GALAXIES

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

GRID    = 128
LAYERS  = 6
LAM     = 0.1
SETTLE  = 20000
MEASURE = 3000

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "sparc_raw", "massive_V200plus")

# Known V_max for calibration galaxies
VMAX = {"NGC2841": 283.0, "NGC7331": 240.0, "NGC3521": 229.0}

# Newton baselines from v7 batch (reference point)
NEWTON_BASELINE = {
    "NGC2841": {"rms_newton": 87.9, "rms_v7": 89.7},
    "NGC7331": {"rms_newton": 70.7, "rms_v7": 55.4},
    "NGC3521": {"rms_newton": 52.5, "rms_v7": 73.8},
}

# Kappa sweep values
KAPPA_SWEEP = [0.0, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]


# ─────────────────────────────────────────
# RUN ONE GALAXY AT ONE KAPPA
# ─────────────────────────────────────────

def run_one(galaxy_name, kappa, rho_baryon_only=None):
    """Run solver with BH injection at given kappa. Returns comp dict."""
    dat_path = os.path.join(DATA_DIR, f"{galaxy_name}_rotmod.dat")
    if not os.path.exists(dat_path):
        # Try root sparc_raw
        dat_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "sparc_raw", f"{galaxy_name}_rotmod.dat"
        )
    if not os.path.exists(dat_path):
        print(f"  NOT FOUND: {galaxy_name}")
        return None, None

    gal    = load_galaxy(dat_path, GRID)
    vmax   = VMAX.get(galaxy_name, gal["vobs"].max())
    J_bar  = gal["source_field"]

    if kappa > 0:
        J_total, bh_info = inject_bh(J_bar, galaxy_name, vmax,
                                      kappa=kappa, verbose=False)
    else:
        J_total  = J_bar
        bh_info  = {"nu_fraction": 0.0}

    solver = SubstrateSolver(
        grid=GRID, layers=LAYERS, lam=LAM,
        settle=SETTLE, measure=MEASURE
    )
    result = solver.run(J_total, verbose=False)
    comp   = compare_rotation(result, gal)

    # Energy spread diagnostic
    rho_eff = result["rho_eff"]
    if rho_baryon_only is not None:
        r_ax, delta, outer_lift, inner_lift = energy_spread_diagnostic(
            rho_baryon_only, rho_eff, GRID
        )
    else:
        outer_lift = None

    return {
        "galaxy":       galaxy_name,
        "kappa":        kappa,
        "rms_newton":   comp["rms_newton"],
        "rms_sub":      comp["rms_substrate"],
        "winner":       comp["winner"],
        "shape":        comp["corr_substrate"],
        "outer_rms":    comp["outer_rms_substrate"],
        "bh_fraction":  bh_info.get("nu_fraction", bh_info.get("bh_fraction", 0.0)),
        "outer_lift":   outer_lift,
        "rho_eff":      rho_eff,
    }, gal


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  CRAG MASS CALIBRATION — kappa_BH sweep")
    print(f"  Grid={GRID}  Layers={LAYERS}  λ={LAM}")
    print(f"  Calibration galaxies: {CALIBRATION_GALAXIES}")
    import math
    r_c = 1.0 / math.sqrt(LAM)
    print(f"  Compton radius: {r_c:.2f} grid units  (injection ring at this radius)")
    print("=" * 65)

    all_results = {g: {} for g in CALIBRATION_GALAXIES}
    rho_baryon  = {g: None for g in CALIBRATION_GALAXIES}

    # First pass: kappa=0 to get baryon-only baseline and rho_eff
    print("\n  Pass 1: Baryon-only baseline (kappa=0)...")
    for gal_name in CALIBRATION_GALAXIES:
        print(f"\n  {gal_name}...")
        r, _ = run_one(gal_name, kappa=0.0)
        if r:
            rho_baryon[gal_name] = r["rho_eff"]
            all_results[gal_name][0.0] = r
            nb = NEWTON_BASELINE[gal_name]
            print(f"    Newton={r['rms_newton']:.2f}  Sub(kappa=0)={r['rms_sub']:.2f}"
                  f"  [v7 ref: {nb['rms_v7']:.2f}]")

    # Sweep kappa > 0
    print("\n  Pass 2: kappa sweep...")
    for kappa in [k for k in KAPPA_SWEEP if k > 0]:
        print(f"\n  ── kappa={kappa} ──")
        kappa_rms = []
        for gal_name in CALIBRATION_GALAXIES:
            r, _ = run_one(gal_name, kappa, rho_baryon[gal_name])
            if r:
                all_results[gal_name][kappa] = r
                kappa_rms.append(r["rms_sub"])
                lift_str = f"  outer_lift={r['outer_lift']:+.4f}" if r["outer_lift"] is not None else ""
                print(f"    {gal_name:<12} Sub={r['rms_sub']:6.2f}  N={r['rms_newton']:6.2f}"
                      f"  BH_frac={r['bh_fraction']:.3f}{lift_str}")
        if kappa_rms:
            print(f"    Mean Sub RMS: {np.mean(kappa_rms):.2f}")

    # ── Summary table ──
    print(f"\n\n{'='*65}")
    print(f"  CALIBRATION SUMMARY")
    print(f"{'='*65}")
    print(f"\n  {'kappa':>8}", end="")
    for g in CALIBRATION_GALAXIES:
        print(f"  {g:>12}", end="")
    print(f"  {'Mean':>8}  {'vs Newton':>10}")
    print(f"  {'─'*8}", end="")
    for _ in CALIBRATION_GALAXIES:
        print(f"  {'─'*12}", end="")
    print(f"  {'─'*8}  {'─'*10}")

    newton_means = np.mean([NEWTON_BASELINE[g]["rms_newton"] for g in CALIBRATION_GALAXIES])
    best_kappa = None
    best_mean = 999

    for kappa in KAPPA_SWEEP:
        row_rms = []
        print(f"  {kappa:>8.4f}", end="")
        for g in CALIBRATION_GALAXIES:
            r = all_results[g].get(kappa)
            if r:
                row_rms.append(r["rms_sub"])
                won = "✓" if r["winner"] == "SUBSTRATE" else " "
                print(f"  {r['rms_sub']:>10.2f}{won} ", end="")
            else:
                print(f"  {'---':>12}", end="")
        mean_rms = np.mean(row_rms) if row_rms else 999
        vs_newton = newton_means - mean_rms
        print(f"  {mean_rms:>8.2f}  {vs_newton:>+10.2f}")
        # Only consider kappa where BH fraction is physically reasonable
        # If BH_frac > 0.5 the baryon structure is drowned out
        max_bh_frac = max(
            all_results[g].get(kappa, {}).get("bh_fraction", 0.0)
            for g in CALIBRATION_GALAXIES
        )
        frac_flag = "  [BH>50% — unphysical]" if max_bh_frac > 0.5 else ""
        if frac_flag:
            print(f"  {frac_flag.strip()}")
        if mean_rms < best_mean and max_bh_frac <= 0.5:
            best_mean = mean_rms
            best_kappa = kappa

    print(f"\n  Newton mean RMS (reference): {newton_means:.2f}")
    print(f"\n  BEST kappa: {best_kappa}  →  mean RMS = {best_mean:.2f}")

    if best_mean < newton_means:
        improvement = newton_means - best_mean
        print(f"\n  >>> CRAG MASS WORKS on calibration set")
        print(f"  >>> Improvement: {improvement:+.2f} km/s over Newton")
        print(f"  >>> Set KAPPA_BH_CALIBRATED = {best_kappa} in Burdick_Crag_Mass.py")
    else:
        print(f"\n  >>> No kappa beats Newton on calibration set")
        print(f"  >>> Check energy_spread diagnostic — is outer_lift > 0?")

    # ── Energy spread summary ──
    print(f"\n  ENERGY SPREAD (outer_lift at best kappa={best_kappa}):")
    for g in CALIBRATION_GALAXIES:
        r = all_results[g].get(best_kappa)
        if r and r["outer_lift"] is not None:
            verdict = "TRANSPORT OK" if r["outer_lift"] > 0 else "NO TRANSPORT"
            print(f"    {g}: outer_lift={r['outer_lift']:+.6f}  [{verdict}]")
