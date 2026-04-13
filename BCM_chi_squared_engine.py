# -*- coding: utf-8 -*-
"""
BCM Paper A — Chi-Squared Comparison Engine
=============================================
Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC
GIBUSH Systems

Three-way reduced chi-squared comparison:
  BCM (4 frozen global params, 0 per-galaxy)
  MOND (fixed a0=1.2e-10, 0 per-galaxy)
  NFW (2 per-galaxy fitted params: c, M_vir)

All three models use identical SPARC baryonic components
(Vgas, Vdisk, Vbul) from Lelli et al. 2016.

Frozen BCM constants:
  lambda  = 0.1
  kappa   = 2.0 (calibrated)
  grid    = 256
  layers  = 8

Galaxy selection: 30 galaxies across five velocity brackets,
covering Classes I, II, III, IV, V-A, V-B, VI where available.

Usage:
    python BCM_chi_squared_engine.py
    python BCM_chi_squared_engine.py --data-dir data/sparc_raw
    python BCM_chi_squared_engine.py --quick   (grid=128 for fast test)

Output: JSON file with per-galaxy chi-squared table.
Foreman runs, provides JSON. Agent reads results.
"""

import numpy as np
import os
import sys
import json
import time
import argparse

# ── Ensure root directory is on path ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "core"))

from sparc_ingest import load_galaxy, build_newtonian_curve
from substrate_solver import SubstrateSolver
from rotation_compare import compare_rotation

# BCM injection
try:
    from Burdick_Crag_Mass import inject_crag_mass, KAPPA_BH_CALIBRATED
    _BCM_AVAILABLE = True
except ImportError:
    _BCM_AVAILABLE = False
    KAPPA_BH_CALIBRATED = 2.0

# Overrides
try:
    from BCM_Substrate_overrides import apply_galaxy_override
    _OVERRIDES_AVAILABLE = True
except ImportError:
    _OVERRIDES_AVAILABLE = False


# ═══════════════════════════════════════
# FROZEN CONSTANTS — DO NOT MODIFY
# ═══════════════════════════════════════
LAMBDA    = 0.1
KAPPA     = 2.0
GRID      = 256
LAYERS    = 8
SETTLE    = 20000
MEASURE   = 5000

# MOND
A0_SI     = 1.2e-10       # m/s^2
KPC_TO_M  = 3.0857e19
KMS_TO_MS = 1000.0


# ═══════════════════════════════════════
# GALAXY SELECTION — 30 REPRESENTATIVES
# ═══════════════════════════════════════
# Criteria: high-quality data, distributed across
# velocity brackets and substrate classes.
# Format: (filename, bracket, notes)

GALAXY_LIST = [
    # ── Dwarf (V < 50) ──
    "DDO154_rotmod.dat",
    "DDO064_rotmod.dat",
    "UGC07577_rotmod.dat",
    "NGC6789_rotmod.dat",
    "UGC04305_rotmod.dat",
    "D564-8_rotmod.dat",

    # ── Low (50-100) ──
    "NGC2976_rotmod.dat",     # Class V-A override
    "NGC0055_rotmod.dat",
    "IC2574_rotmod.dat",
    "NGC2366_rotmod.dat",
    "NGC3741_rotmod.dat",
    "UGC06667_rotmod.dat",

    # ── Mid (100-150) ──
    "NGC2403_rotmod.dat",
    "NGC7793_rotmod.dat",     # Class V-B override
    "NGC6503_rotmod.dat",
    "NGC4559_rotmod.dat",
    "UGC06614_rotmod.dat",
    "NGC3726_rotmod.dat",

    # ── High (150-200) ──
    "NGC5055_rotmod.dat",
    "NGC3198_rotmod.dat",
    "NGC2903_rotmod.dat",
    "NGC5033_rotmod.dat",
    "NGC6946_rotmod.dat",
    "NGC4013_rotmod.dat",

    # ── Massive (V > 200) ──
    "NGC2841_rotmod.dat",     # Class I flagship
    "NGC7331_rotmod.dat",     # Calibration galaxy
    "NGC3521_rotmod.dat",     # Calibration galaxy
    "NGC3953_rotmod.dat",     # Class VI barred
    "NGC5907_rotmod.dat",
    "NGC0891_rotmod.dat",
]


# ═══════════════════════════════════════
# MOND VELOCITY
# ═══════════════════════════════════════

def compute_mond(v_baryonic, r_kpc):
    """MOND velocity. mu(x) = x/(1+x), a0 = 1.2e-10 m/s^2."""
    v_mond = np.zeros_like(v_baryonic)
    for i in range(len(v_baryonic)):
        v_n = v_baryonic[i] * KMS_TO_MS
        r = r_kpc[i] * KPC_TO_M
        if r <= 0 or v_n <= 0:
            v_mond[i] = v_baryonic[i]
            continue
        g_n = (v_n ** 2) / r
        x = g_n / A0_SI
        if x > 100:
            mu = 1.0
        elif x < 0.01:
            mu = x
        else:
            mu = x / (1.0 + x)
        g_mond = g_n / mu if mu > 0 else g_n
        v_mond[i] = np.sqrt(g_mond * r) / KMS_TO_MS
    return v_mond


# ═══════════════════════════════════════
# NFW HALO VELOCITY
# ═══════════════════════════════════════

def nfw_velocity(r_kpc, M_vir, c, H0=70.0):
    """
    NFW halo circular velocity.

    V_halo^2(r) = G * M_vir * g(c) * [ln(1+x) - x/(1+x)] / r
    where x = r/r_s, r_s = r_vir/c, g(c) = 1/[ln(1+c) - c/(1+c)]

    M_vir in solar masses, r_kpc in kpc.
    Returns V_halo in km/s.
    """
    G_ASTRO = 4.30091e-6   # kpc (km/s)^2 / M_sun

    # Virial radius from M_vir (Bryan & Norman 1998)
    # r_vir = (3 * M_vir / (4 * pi * 200 * rho_crit))^(1/3)
    rho_crit = 3.0 * (H0 / 3.0857e19) ** 2 / (8.0 * np.pi * 6.674e-11)
    # In solar masses per kpc^3:
    rho_crit_solar = rho_crit * (3.0857e19) ** 3 / 1.989e30
    r_vir = (3.0 * M_vir / (4.0 * np.pi * 200.0 * rho_crit_solar)) ** (1.0 / 3.0)

    r_s = r_vir / c
    g_c = 1.0 / (np.log(1.0 + c) - c / (1.0 + c))

    v_halo = np.zeros_like(r_kpc)
    for i in range(len(r_kpc)):
        r = r_kpc[i]
        if r <= 0:
            continue
        x = r / r_s
        if x < 1e-6:
            continue
        bracket = np.log(1.0 + x) - x / (1.0 + x)
        v_sq = G_ASTRO * M_vir * g_c * bracket / r
        if v_sq > 0:
            v_halo[i] = np.sqrt(v_sq)

    return v_halo


def fit_nfw(r_kpc, v_obs, v_newton, errv):
    """
    Fit NFW halo to residual rotation curve.
    Grid search over (c, M_vir) to minimize chi-squared.

    Returns best (c, M_vir, chi2_red, v_nfw_total).
    """
    # Search grid
    c_vals = np.array([3, 5, 7, 10, 12, 15, 18, 20, 25, 30])
    logM_vals = np.arange(9.0, 13.5, 0.25)  # log10(M_vir / M_sun)

    best_chi2 = 1e30
    best_c = 10.0
    best_logM = 11.0

    safe_err = np.maximum(errv, 1.0)  # floor at 1 km/s
    n = len(r_kpc)

    for c in c_vals:
        for logM in logM_vals:
            M_vir = 10.0 ** logM
            v_halo = nfw_velocity(r_kpc, M_vir, c)
            v_total = np.sqrt(v_newton ** 2 + v_halo ** 2)
            chi2 = np.sum(((v_obs - v_total) / safe_err) ** 2) / max(n - 2, 1)
            if chi2 < best_chi2:
                best_chi2 = chi2
                best_c = c
                best_logM = logM

    # Refine around best
    c_fine = np.linspace(max(best_c - 3, 1), best_c + 3, 25)
    logM_fine = np.linspace(best_logM - 0.5, best_logM + 0.5, 25)
    for c in c_fine:
        for logM in logM_fine:
            M_vir = 10.0 ** logM
            v_halo = nfw_velocity(r_kpc, M_vir, c)
            v_total = np.sqrt(v_newton ** 2 + v_halo ** 2)
            chi2 = np.sum(((v_obs - v_total) / safe_err) ** 2) / max(n - 2, 1)
            if chi2 < best_chi2:
                best_chi2 = chi2
                best_c = c
                best_logM = logM

    M_vir_best = 10.0 ** best_logM
    v_halo_best = nfw_velocity(r_kpc, M_vir_best, best_c)
    v_nfw_total = np.sqrt(v_newton ** 2 + v_halo_best ** 2)

    return best_c, M_vir_best, best_chi2, v_nfw_total


# ═══════════════════════════════════════
# REDUCED CHI-SQUARED
# ═══════════════════════════════════════

def reduced_chi2(v_model, v_obs, errv, n_params=0):
    """
    Reduced chi-squared.
    chi2_red = (1 / (N - p)) * sum( (V_model - V_obs)^2 / errV^2 )

    n_params: number of per-galaxy free parameters.
      BCM  = 0  (frozen global)
      MOND = 0  (fixed a0, same M/L as SPARC)
      NFW  = 2  (c, M_vir fitted per galaxy)
    """
    n = len(v_obs)
    dof = max(n - n_params, 1)
    safe_err = np.maximum(errv, 1.0)  # floor 1 km/s
    return float(np.sum(((v_model - v_obs) / safe_err) ** 2) / dof)


# ═══════════════════════════════════════
# FIND GALAXY FILE
# ═══════════════════════════════════════

def find_dat_file(filename, data_dir):
    """Search data_dir and subdirectories for the .dat file."""
    # Direct path
    direct = os.path.join(data_dir, filename)
    if os.path.exists(direct):
        return direct
    # Search subdirs
    for root, dirs, files in os.walk(data_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


# ═══════════════════════════════════════
# PROCESS ONE GALAXY
# ═══════════════════════════════════════

def process_galaxy(dat_path, grid, layers, verbose=True):
    """
    Full pipeline for one galaxy:
    1. Load SPARC data
    2. Apply override if applicable
    3. Run BCM solver
    4. Compute BCM, MOND, NFW rotation curves
    5. Compute reduced chi-squared for all three
    6. Return results dict
    """
    galaxy_name = os.path.basename(dat_path).replace("_rotmod.dat", "").replace(".dat", "")
    if verbose:
        print(f"\n{'='*60}")
        print(f"  GALAXY: {galaxy_name}")
        print(f"{'='*60}")

    # ── 1. Load ──
    galaxy = load_galaxy(dat_path, grid=grid, scale_factor=1.0,
                         source_mode="classic", lam=LAMBDA)
    r_kpc = galaxy["radii_kpc"]
    v_obs = galaxy["vobs"]
    v_newton = galaxy["newtonian_curve"]
    errv = galaxy["rotation_curve"]["errV"]

    if len(r_kpc) < 5:
        if verbose:
            print(f"  SKIP: only {len(r_kpc)} data points")
        return None

    vmax = float(np.max(v_obs))

    # ── 2. Apply override if applicable ──
    J_source = galaxy["source_field"]
    override_class = "standard"

    if _OVERRIDES_AVAILABLE:
        try:
            J_override, override_params = apply_galaxy_override(
                galaxy_name, J_source, grid, vmax)
            if J_override is not None:
                J_source = J_override
                override_class = override_params.get("class", "override")
                if verbose:
                    print(f"  Override applied: Class {override_class}")
        except Exception as e:
            if verbose:
                print(f"  Override skipped: {e}")

    # ── 3. Run BCM solver ──
    solver = SubstrateSolver(
        grid=grid, layers=layers, dx=1.0, dt=0.005,
        c_wave=1.0, gamma=0.05, lam=LAMBDA,
        epsilon=0.001, entangle=0.02,
        settle=SETTLE, measure=MEASURE, edge=10
    )

    result = solver.run(
        J_source, verbose=verbose,
        galaxy_name=galaxy_name, vmax_kms=vmax,
        use_crag=True, crag_kappa=KAPPA
    )

    # ── 4. Extract BCM rotation curve ──
    comp = compare_rotation(result, galaxy)
    v_bcm = comp["v_substrate"]

    # ── 5. Compute MOND ──
    v_mond = compute_mond(v_newton, r_kpc)

    # ── 6. Fit NFW ──
    nfw_c, nfw_Mvir, nfw_chi2_fitted, v_nfw = fit_nfw(
        r_kpc, v_obs, v_newton, errv)

    # ── 7. Chi-squared for all three ──
    chi2_newton = reduced_chi2(v_newton, v_obs, errv, n_params=0)
    chi2_mond   = reduced_chi2(v_mond,   v_obs, errv, n_params=0)
    chi2_bcm    = reduced_chi2(v_bcm,    v_obs, errv, n_params=0)
    chi2_nfw    = reduced_chi2(v_nfw,    v_obs, errv, n_params=2)

    # ── 8. RMS errors ──
    rms_newton = float(np.sqrt(np.mean((v_newton - v_obs) ** 2)))
    rms_mond   = float(np.sqrt(np.mean((v_mond   - v_obs) ** 2)))
    rms_bcm    = float(np.sqrt(np.mean((v_bcm    - v_obs) ** 2)))
    rms_nfw    = float(np.sqrt(np.mean((v_nfw    - v_obs) ** 2)))

    # ── 9. Determine winner ──
    chi2_dict = {"NEWTON": chi2_newton, "MOND": chi2_mond,
                 "BCM": chi2_bcm, "NFW": chi2_nfw}
    winner = min(chi2_dict, key=chi2_dict.get)

    # ── 10. Phase diagnostics from solver ──
    cos_dphi = result.get("cos_delta_phi", None)
    decoupling = result.get("decoupling_ratio", None)

    if verbose:
        print(f"\n  {'Model':<10} {'chi2_red':>10} {'RMS':>8}")
        print(f"  {'─'*10} {'─'*10} {'─'*8}")
        print(f"  {'Newton':<10} {chi2_newton:>10.3f} {rms_newton:>8.2f}")
        print(f"  {'MOND':<10} {chi2_mond:>10.3f} {rms_mond:>8.2f}")
        print(f"  {'BCM':<10} {chi2_bcm:>10.3f} {rms_bcm:>8.2f}")
        print(f"  {'NFW':<10} {chi2_nfw:>10.3f} {rms_nfw:>8.2f}")
        print(f"  Winner: {winner}")

    return {
        "galaxy":         galaxy_name,
        "n_points":       len(r_kpc),
        "r_max_kpc":      float(r_kpc[-1]),
        "v_max_kms":      vmax,
        "override_class": override_class,

        "chi2_newton":    chi2_newton,
        "chi2_mond":      chi2_mond,
        "chi2_bcm":       chi2_bcm,
        "chi2_nfw":       chi2_nfw,

        "rms_newton":     rms_newton,
        "rms_mond":       rms_mond,
        "rms_bcm":        rms_bcm,
        "rms_nfw":        rms_nfw,

        "nfw_c":          float(nfw_c),
        "nfw_logMvir":    float(np.log10(nfw_Mvir)),

        "winner_chi2":    winner,
        "bcm_vs_mond":    chi2_mond - chi2_bcm,
        "bcm_vs_nfw":     chi2_nfw - chi2_bcm,

        "cos_delta_phi":    float(cos_dphi) if cos_dphi is not None else None,
        "decoupling_ratio": float(decoupling) if decoupling is not None else None,

        # Per-point data for paper plots
        "r_kpc":      r_kpc.tolist(),
        "v_obs":      v_obs.tolist(),
        "errv":       errv.tolist(),
        "v_newton":   v_newton.tolist(),
        "v_mond":     v_mond.tolist(),
        "v_bcm":      v_bcm.tolist(),
        "v_nfw":      v_nfw.tolist(),
    }


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM Paper A — Chi-Squared Comparison Engine")
    parser.add_argument("--data-dir", type=str,
                        default=os.path.join(SCRIPT_DIR, "data", "sparc_raw"),
                        help="SPARC data directory")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON path")
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: grid=128 for fast test")
    args = parser.parse_args()

    grid = 128 if args.quick else GRID
    layers = LAYERS

    print("=" * 60)
    print("  BCM PAPER A — CHI-SQUARED COMPARISON ENGINE")
    print("  Stephen Justin Burdick Sr. — Emerald Entities LLC")
    print("  GIBUSH Systems — 2026")
    print("=" * 60)
    print(f"\n  Frozen constants:")
    print(f"    lambda  = {LAMBDA}")
    print(f"    kappa   = {KAPPA}")
    print(f"    grid    = {grid}")
    print(f"    layers  = {layers}")
    print(f"    settle  = {SETTLE}")
    print(f"    measure = {MEASURE}")
    print(f"\n  MOND: a0 = {A0_SI:.1e} m/s^2")
    print(f"  NFW: fitted per galaxy (c, M_vir)")
    print(f"\n  BCM available: {_BCM_AVAILABLE}")
    print(f"  Overrides available: {_OVERRIDES_AVAILABLE}")
    print(f"\n  Data dir: {args.data_dir}")
    print(f"  Galaxies: {len(GALAXY_LIST)}")

    if not os.path.exists(args.data_dir):
        print(f"\n  ERROR: Data directory not found: {args.data_dir}")
        print(f"  Place SPARC _rotmod.dat files in: {args.data_dir}")
        sys.exit(1)

    # ── Run batch ──
    t_start = time.time()
    results = []
    skipped = []

    for filename in GALAXY_LIST:
        dat_path = find_dat_file(filename, args.data_dir)
        if dat_path is None:
            print(f"\n  NOT FOUND: {filename}")
            skipped.append(filename)
            continue

        try:
            r = process_galaxy(dat_path, grid, layers, verbose=True)
            if r is not None:
                results.append(r)
        except Exception as e:
            print(f"\n  FAILED: {filename}: {e}")
            skipped.append(filename)

    t_total = time.time() - t_start

    # ═══════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════

    print(f"\n{'='*60}")
    print(f"  SUMMARY — {len(results)} galaxies in {t_total:.1f}s")
    print(f"{'='*60}")

    if skipped:
        print(f"\n  Skipped: {', '.join(skipped)}")

    if results:
        # Winner counts
        winners = {}
        for r in results:
            w = r["winner_chi2"]
            winners[w] = winners.get(w, 0) + 1

        print(f"\n  CHI-SQUARED WINNERS:")
        for model in ["BCM", "MOND", "NFW", "NEWTON"]:
            print(f"    {model:<10} {winners.get(model, 0):>3} / {len(results)}")

        # Average chi-squared
        avg_chi2_n = np.mean([r["chi2_newton"] for r in results])
        avg_chi2_m = np.mean([r["chi2_mond"]   for r in results])
        avg_chi2_b = np.mean([r["chi2_bcm"]    for r in results])
        avg_chi2_f = np.mean([r["chi2_nfw"]    for r in results])

        # Median chi-squared (more robust to outliers)
        med_chi2_n = np.median([r["chi2_newton"] for r in results])
        med_chi2_m = np.median([r["chi2_mond"]   for r in results])
        med_chi2_b = np.median([r["chi2_bcm"]    for r in results])
        med_chi2_f = np.median([r["chi2_nfw"]    for r in results])

        print(f"\n  {'Model':<10} {'Avg chi2':>10} {'Med chi2':>10} {'Avg RMS':>10}")
        print(f"  {'─'*10} {'─'*10} {'─'*10} {'─'*10}")
        print(f"  {'Newton':<10} {avg_chi2_n:>10.3f} {med_chi2_n:>10.3f}"
              f" {np.mean([r['rms_newton'] for r in results]):>10.2f}")
        print(f"  {'MOND':<10} {avg_chi2_m:>10.3f} {med_chi2_m:>10.3f}"
              f" {np.mean([r['rms_mond'] for r in results]):>10.2f}")
        print(f"  {'BCM':<10} {avg_chi2_b:>10.3f} {med_chi2_b:>10.3f}"
              f" {np.mean([r['rms_bcm'] for r in results]):>10.2f}")
        print(f"  {'NFW':<10} {avg_chi2_f:>10.3f} {med_chi2_f:>10.3f}"
              f" {np.mean([r['rms_nfw'] for r in results]):>10.2f}")

        # Per-galaxy table
        print(f"\n  {'Galaxy':<16} {'N':>4} {'chi2_N':>8} {'chi2_M':>8}"
              f" {'chi2_B':>8} {'chi2_F':>8} {'Winner':>8}")
        print(f"  {'─'*16} {'─'*4} {'─'*8} {'─'*8}"
              f" {'─'*8} {'─'*8} {'─'*8}")
        for r in sorted(results, key=lambda x: x["v_max_kms"]):
            print(f"  {r['galaxy']:<16} {r['n_points']:>4}"
                  f" {r['chi2_newton']:>8.2f} {r['chi2_mond']:>8.2f}"
                  f" {r['chi2_bcm']:>8.2f} {r['chi2_nfw']:>8.2f}"
                  f" {r['winner_chi2']:>8}")

    # ═══════════════════════════════════════
    # SAVE JSON
    # ═══════════════════════════════════════

    out_path = args.output
    if out_path is None:
        out_dir = os.path.join(SCRIPT_DIR, "data", "results")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir,
            f"BCM_chi2_engine_{time.strftime('%Y%m%d_%H%M%S')}.json")

    output = {
        "engine":     "BCM_chi_squared_engine",
        "version":    "Paper_A_v1",
        "timestamp":  time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_s":  t_total,
        "config": {
            "lambda":  LAMBDA,
            "kappa":   KAPPA,
            "grid":    grid,
            "layers":  layers,
            "settle":  SETTLE,
            "measure": MEASURE,
            "a0_mond": A0_SI,
            "bcm_available":       _BCM_AVAILABLE,
            "overrides_available": _OVERRIDES_AVAILABLE,
        },
        "n_galaxies":   len(results),
        "n_skipped":    len(skipped),
        "skipped":      skipped,
        "summary": {
            "winners": winners if results else {},
            "avg_chi2_newton": float(avg_chi2_n) if results else 0,
            "avg_chi2_mond":   float(avg_chi2_m) if results else 0,
            "avg_chi2_bcm":    float(avg_chi2_b) if results else 0,
            "avg_chi2_nfw":    float(avg_chi2_f) if results else 0,
            "med_chi2_newton": float(med_chi2_n) if results else 0,
            "med_chi2_mond":   float(med_chi2_m) if results else 0,
            "med_chi2_bcm":    float(med_chi2_b) if results else 0,
            "med_chi2_nfw":    float(med_chi2_f) if results else 0,
        },
        "galaxies": results,
    }

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n  Saved: {out_path}")
    print(f"\n  Done. {len(results)} galaxies processed in {t_total:.1f}s.")
    print(f"\n  Stephen Justin Burdick Sr. — Emerald Entities LLC")
    print(f"  GIBUSH Systems — 2026")
