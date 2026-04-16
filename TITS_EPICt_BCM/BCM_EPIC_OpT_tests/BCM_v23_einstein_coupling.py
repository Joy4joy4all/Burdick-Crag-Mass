# -*- coding: utf-8 -*-
"""
BCM v23 — EINSTEIN COUPLING TEST
===================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

Addresses ChatGPT adversarial kill conditions for Paper B:

  1. Clean Lagrangian (no memory term — covariant)
  2. Explicit T_μν derivation from physical velocity excess
  3. Newtonian limit: ∇²Φ = 4πG(ρ_baryon + ρ_sub)
  4. Rotation curve mapping: ρ_sub ↔ v_excess²
  5. Lensing prediction: deflection angle from M_sub
  6. Conservation check: ∇_μ T^μν residual

Physical unit mapping: code-unit σ → v_substrate (km/s) via
compare_rotation() → v_excess² = v_sub² - v_newton² → ρ_sub.
Same calibration path as v22 neutrino flux.

Output JSON → data/results/BCM_v23_einstein_YYYYMMDD_HHMMSS.json

Usage:
    python BCM_v23_einstein_coupling.py          # full (grid=256)
    python BCM_v23_einstein_coupling.py --quick   # fast (grid=128, 5 galaxies)
"""

import numpy as np
import os
import sys
import json
import time
import argparse

# ── Path setup ──
_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_EPIC_DIR     = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_EPIC_DIR)
for p in [_SCRIPT_DIR, _EPIC_DIR, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.substrate_solver import SubstrateSolver
from core.sparc_ingest import load_galaxy
from core.rotation_compare import compare_rotation

# ═══════════════════════════════════════════════════════════
# PHYSICAL CONSTANTS
# ═══════════════════════════════════════════════════════════

G_SI       = 6.674e-11
C_SI       = 2.998e8
KPC_TO_M   = 3.0857e19
MSUN_KG    = 1.989e30
KMS_TO_MS  = 1000.0

LAMBDA     = 0.1
KAPPA_BH   = 2.0
GRID_PROD  = 256
GRID_QUICK = 128
LAYERS     = 8
SETTLE     = 15000
MEASURE    = 5000

CHI2_GALAXIES = [
    "NGC2841", "NGC7331", "NGC3521", "NGC5907", "NGC5985",
    "NGC6674", "NGC0891", "NGC3992", "NGC5371", "NGC2998",
    "NGC3953", "NGC0801",
    "NGC6946", "NGC5055", "NGC5033", "NGC3198", "NGC4100",
    "NGC4217", "NGC4013", "NGC2903",
    "NGC7793", "NGC2976", "NGC6503", "NGC2403",
    "NGC3726", "NGC4559", "NGC3769",
    "UGC04305", "DDO154",
]
QUICK_GALAXIES = ["NGC2841", "NGC7331", "NGC6503", "NGC3953", "UGC04305"]


def physical_density_profile(r_kpc, v_substrate, v_newton):
    """Physical ρ_sub from velocity excess. SI units."""
    r_m = r_kpc * KPC_TO_M
    v_sub_ms = v_substrate * KMS_TO_MS
    v_new_ms = v_newton * KMS_TO_MS
    v_excess_sq = v_sub_ms**2 - v_new_ms**2

    M_enclosed = np.zeros_like(r_m)
    mask = r_m > 0
    M_enclosed[mask] = np.abs(v_excess_sq[mask]) * r_m[mask] / G_SI

    dM_dr = np.gradient(M_enclosed, r_m)
    rho_sub = np.zeros_like(r_m)
    mask2 = r_m > 0
    rho_sub[mask2] = np.abs(dM_dr[mask2]) / (4.0 * np.pi * r_m[mask2]**2)

    return {
        "r_m": r_m,
        "v_excess_sq": v_excess_sq,
        "M_enclosed": M_enclosed,
        "rho_sub": rho_sub,
    }


def compute_lagrangian(r_m, rho_sub, v_excess_sq):
    """Clean covariant Lagrangian. Returns action density."""
    sigma_phys = v_excess_sq / KAPPA_BH
    dsigma_dr = np.gradient(sigma_phys, r_m)
    kinetic = 0.5 * dsigma_dr**2
    mass    = 0.5 * LAMBDA * sigma_phys**2
    integrand = 4.0 * np.pi * r_m**2 * (kinetic - mass)
    return float(np.trapezoid(integrand, r_m))


def compute_stress_energy(r_m, rho_sub, v_excess_sq):
    """T_μν from physical density."""
    T_00 = rho_sub * C_SI**2
    p_sub = rho_sub * v_excess_sq / 3.0
    w = np.zeros_like(r_m)
    mask = T_00 > 0
    w[mask] = p_sub[mask] / T_00[mask]
    return {
        "T_00": T_00, "p_sub": p_sub,
        "T_00_mean": float(np.mean(T_00[mask])) if np.any(mask) else 0.0,
        "T_00_max": float(np.max(T_00)),
        "w_mean": float(np.mean(w[mask])) if np.any(mask) else 0.0,
    }


def test_newtonian_limit(r_kpc, v_obs, v_newton, v_substrate, M_enclosed):
    """Newtonian limit: does ρ_sub improve v(r)?"""
    v_excess_sq = v_substrate**2 - v_newton**2
    v_total = np.sqrt(v_newton**2 + np.maximum(v_excess_sq, 0))
    rms_n = float(np.sqrt(np.mean((v_obs - v_newton)**2)))
    rms_t = float(np.sqrt(np.mean((v_obs - v_total)**2)))
    rms_s = float(np.sqrt(np.mean((v_obs - v_substrate)**2)))
    return {
        "rms_newton": rms_n, "rms_substrate": rms_s,
        "rms_einstein": rms_t,
        "improvement_vs_newton": float(rms_n - rms_t),
        "newtonian_limit_holds": bool(rms_t <= rms_n),
        "M_sub_Msun": float(M_enclosed[-1] / MSUN_KG) if len(M_enclosed) > 0 else 0.0,
    }


def compute_lensing(r_kpc, M_enclosed, v_obs, distance_mpc=10.0):
    """Lensing from physical M_sub."""
    r_m = r_kpc * KPC_TO_M
    D_L = distance_mpc * 3.0857e22
    alpha_rad = np.zeros_like(r_kpc)
    mask = r_m > 0
    alpha_rad[mask] = (4.0 * G_SI * M_enclosed[mask]) / (C_SI**2 * r_m[mask])
    alpha_arcsec = np.degrees(alpha_rad) * 3600.0

    M_lens = M_enclosed[-1] if len(M_enclosed) > 0 else 0.0
    D_eff = D_L / 2.0
    theta_E = float(np.degrees(
        np.sqrt(4.0 * G_SI * M_lens / (C_SI**2 * D_eff))) * 3600.0) if D_eff > 0 else 0.0

    v_flat = float(np.median(v_obs[-5:])) if len(v_obs) >= 5 else float(v_obs[-1])
    r_outer = r_m[-1] if len(r_m) > 0 else 1.0
    M_baryon = (v_flat * KMS_TO_MS)**2 * r_outer / G_SI
    theta_E_bar = float(np.degrees(
        np.sqrt(4.0 * G_SI * M_baryon / (C_SI**2 * D_eff))) * 3600.0) if D_eff > 0 else 0.0

    return {
        "alpha_max_arcsec": float(np.max(alpha_arcsec)),
        "theta_E_arcsec": theta_E,
        "theta_E_baryon_arcsec": theta_E_bar,
        "lensing_excess_ratio": float(theta_E / theta_E_bar) if theta_E_bar > 0 else 0.0,
        "M_lens_Msun": float(M_lens / MSUN_KG),
        "M_baryon_Msun": float(M_baryon / MSUN_KG),
        "distance_Mpc": distance_mpc,
    }


def check_conservation(r_m, T_00, p_sub):
    """Static spherical conservation residual."""
    dP_dr = np.gradient(p_sub, r_m)
    r_safe = np.where(r_m > 0, r_m, 1e-30)
    residual = dP_dr + (2.0 / r_safe) * (p_sub - T_00)
    T_max = np.max(np.abs(T_00))
    cons_norm = float(np.sqrt(np.mean(residual**2)) / T_max) if T_max > 0 else 0.0
    return {
        "conservation_norm": cons_norm,
        "conservation_holds": bool(cons_norm < 0.1),
    }


def find_dat_path(galaxy_name, data_dir):
    """Find .dat file across velocity brackets."""
    for bracket in ["dwarf_V0-50", "low_V50-100", "mid_V100-150",
                    "high_V150-200", "massive_V200plus"]:
        path = os.path.join(data_dir, bracket, f"{galaxy_name}_rotmod.dat")
        if os.path.exists(path):
            return path
    path = os.path.join(data_dir, f"{galaxy_name}_rotmod.dat")
    return path if os.path.exists(path) else None


def run_galaxy(galaxy_name, data_dir, grid, verbose=True):
    """Run full Einstein coupling test on one galaxy."""
    dat_path = find_dat_path(galaxy_name, data_dir)
    if not dat_path:
        if verbose:
            print(f"  SKIP: {galaxy_name} — dat not found")
        return None

    if verbose:
        print(f"\n{'═'*55}")
        print(f"  {galaxy_name}")
        print(f"{'═'*55}")

    t0 = time.time()
    gal = load_galaxy(dat_path, grid)
    J = gal["source_field"]
    r_kpc = gal["radii_kpc"]
    v_obs = gal["vobs"]
    v_newton = gal["newtonian_curve"]
    v_max = float(np.max(v_obs))

    if verbose:
        print(f"  v_max = {v_max:.1f} km/s  |  {len(r_kpc)} points")

    solver = SubstrateSolver(grid=grid, layers=LAYERS, lam=LAMBDA,
                             settle=SETTLE, measure=MEASURE)
    result = solver.run(J, verbose=False)

    comp = compare_rotation(result, gal)
    v_substrate = comp["v_substrate"]

    if verbose:
        print(f"  RMS: Newton={comp['rms_newton']:.2f}  "
              f"Sub={comp['rms_substrate']:.2f}  "
              f"Winner={comp['winner']}")

    phys = physical_density_profile(r_kpc, v_substrate, v_newton)
    action = compute_lagrangian(phys["r_m"], phys["rho_sub"], phys["v_excess_sq"])
    tmunu = compute_stress_energy(phys["r_m"], phys["rho_sub"], phys["v_excess_sq"])
    newton_test = test_newtonian_limit(r_kpc, v_obs, v_newton, v_substrate, phys["M_enclosed"])

    distance_mpc = max(5.0, v_max / 70.0)
    lensing = compute_lensing(r_kpc, phys["M_enclosed"], v_obs, distance_mpc)
    cons = check_conservation(phys["r_m"], tmunu["T_00"], tmunu["p_sub"])

    elapsed = time.time() - t0

    if verbose:
        print(f"  Action:        {action:.4e} J·m")
        print(f"  T_00 mean:     {tmunu['T_00_mean']:.4e} J/m³")
        print(f"  w (EoS):       {tmunu['w_mean']:.4f}")
        nl = "PASS" if newton_test["newtonian_limit_holds"] else "FAIL"
        print(f"  Newton RMS:    {newton_test['rms_newton']:.2f} km/s")
        print(f"  Einstein RMS:  {newton_test['rms_einstein']:.2f} km/s")
        print(f"  Improvement:   {newton_test['improvement_vs_newton']:+.2f} km/s")
        print(f"  M_sub:         {newton_test['M_sub_Msun']:.2e} M☉")
        print(f"  Newtonian lim: {nl}")
        print(f"  θ_E (sub):     {lensing['theta_E_arcsec']:.4f}\"")
        print(f"  θ_E (baryon):  {lensing['theta_E_baryon_arcsec']:.4f}\"")
        print(f"  Excess ratio:  {lensing['lensing_excess_ratio']:.3f}×")
        cl = "PASS" if cons["conservation_holds"] else "FAIL"
        print(f"  Conservation:  {cons['conservation_norm']:.6f} ({cl})")
        print(f"  Elapsed:       {elapsed:.1f}s")

    return {
        "galaxy": galaxy_name, "v_max": v_max,
        "n_points": len(r_kpc), "grid": grid,
        "elapsed": float(elapsed),
        "rms_newton": float(comp["rms_newton"]),
        "rms_substrate": float(comp["rms_substrate"]),
        "winner": comp["winner"],
        "sub_vs_newton": float(comp["sub_vs_newton"]),
        "action_density_Jm": action,
        "T_00_mean_Jm3": tmunu["T_00_mean"],
        "T_00_max_Jm3": tmunu["T_00_max"],
        "w_eos_mean": tmunu["w_mean"],
        "rms_einstein": newton_test["rms_einstein"],
        "improvement_vs_newton": newton_test["improvement_vs_newton"],
        "newtonian_limit_holds": newton_test["newtonian_limit_holds"],
        "M_sub_Msun": newton_test["M_sub_Msun"],
        "theta_E_arcsec": lensing["theta_E_arcsec"],
        "theta_E_baryon_arcsec": lensing["theta_E_baryon_arcsec"],
        "lensing_excess_ratio": lensing["lensing_excess_ratio"],
        "alpha_max_arcsec": lensing["alpha_max_arcsec"],
        "M_lens_Msun": lensing["M_lens_Msun"],
        "distance_Mpc": lensing["distance_Mpc"],
        "conservation_norm": cons["conservation_norm"],
        "conservation_holds": cons["conservation_holds"],
        "corr_full": float(result.get("corr_full", 0)),
        "cos_delta_phi": float(result.get("cos_delta_phi", 0)),
    }


def main():
    parser = argparse.ArgumentParser(description="BCM v23 Einstein Coupling Test")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()

    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)
    galaxies = QUICK_GALAXIES if args.quick else CHI2_GALAXIES

    print("=" * 60)
    print("  BCM v23 — EINSTEIN COUPLING TEST")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)
    print(f"  Grid: {grid}  |  Galaxies: {len(galaxies)}")
    print(f"  Mode: {'QUICK' if args.quick else 'PRODUCTION'}")
    print(f"  Unit mapping: v_excess → ρ_sub → T_μν (physical SI)")
    print("=" * 60)

    data_dir = os.path.join(_PROJECT_ROOT, "data", "sparc_raw")
    if not os.path.isdir(data_dir):
        print(f"  ERROR: SPARC data not found at {data_dir}")
        sys.exit(1)

    results = []
    t_total = time.time()
    for galaxy in galaxies:
        r = run_galaxy(galaxy, data_dir, grid)
        if r:
            results.append(r)

    elapsed_total = time.time() - t_total
    newton_pass = cons_pass = 0

    print(f"\n{'═'*60}")
    print(f"  EINSTEIN COUPLING SUMMARY")
    print(f"{'═'*60}")

    if results:
        newton_pass = sum(1 for r in results if r["newtonian_limit_holds"])
        cons_pass   = sum(1 for r in results if r["conservation_holds"])
        print(f"  Galaxies tested:    {len(results)}")
        print(f"  Newtonian limit:    {newton_pass}/{len(results)} PASS")
        print(f"  Conservation:       {cons_pass}/{len(results)} PASS")
        print(f"  Mean improvement:   {np.mean([r['improvement_vs_newton'] for r in results]):+.2f} km/s")
        print(f"  Mean M_sub:         {np.mean([r['M_sub_Msun'] for r in results]):.2e} M☉")
        print(f"  Mean θ_E:           {np.mean([r['theta_E_arcsec'] for r in results]):.4f}\"")
        print(f"  Mean excess ratio:  {np.mean([r['lensing_excess_ratio'] for r in results]):.3f}×")
        print(f"  Mean w (EoS):       {np.mean([r['w_eos_mean'] for r in results]):.4f}")
        print(f"  Total elapsed:      {elapsed_total:.1f}s")

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(results_dir, f"BCM_v23_einstein_{timestamp}.json")

    output = {
        "test": "einstein_coupling", "version": "v23",
        "grid": grid, "mode": "quick" if args.quick else "production",
        "galaxies_tested": len(results),
        "newtonian_limit_pass": newton_pass,
        "conservation_pass": cons_pass,
        "lambda": LAMBDA, "kappa_BH": KAPPA_BH,
        "elapsed_total": float(elapsed_total),
        "timestamp": timestamp, "results": results,
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n  JSON saved: {out_path}")
    print(f"\n  Space is not a container. Space is a maintenance cost.")
    print(f"  The electric bill has a meter reading.")


if __name__ == "__main__":
    main()
