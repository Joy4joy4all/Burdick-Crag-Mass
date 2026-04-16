# -*- coding: utf-8 -*-
"""
BCM v23 — NULL PUMP TEST (J = 0)
==================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

The cleanest fork in the project:

  RUN 1: Normal J (baryonic source field from SPARC data)
  RUN 2: J = 0 (no SMBH pump, no injection)

If rotation curve fits COLLAPSE without J:
  → The pump is essential. The substrate exists BECAUSE of
    the SMBH injection, not despite it. The pump works
    through diffusion, not local surplus.

If rotation curve fits HOLD without J:
  → The pump is decorative. The field structure comes from
    initial conditions or solver artifacts. The "maintenance
    cost" narrative needs revision.

Runs on the 5 snap-back galaxies.
Output JSON → data/results/BCM_v23_null_pump_YYYYMMDD_HHMMSS.json
"""

import numpy as np
import os
import sys
import json
import time
import argparse

_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_EPIC_DIR     = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_EPIC_DIR)
for p in [_SCRIPT_DIR, _EPIC_DIR, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.substrate_solver import SubstrateSolver
from core.sparc_ingest import load_galaxy
from core.rotation_compare import compare_rotation

LAMBDA     = 0.1
KAPPA_BH   = 2.0
GRID_PROD  = 256
GRID_QUICK = 128
LAYERS     = 8
SETTLE     = 15000
MEASURE    = 5000

TEST_GALAXIES = ["NGC6946", "NGC7331", "NGC3521", "NGC3953", "NGC0891"]


def find_dat_path(galaxy_name, data_dir):
    for bracket in ["dwarf_V0-50", "low_V50-100", "mid_V100-150",
                    "high_V150-200", "massive_V200plus"]:
        path = os.path.join(data_dir, bracket,
                            f"{galaxy_name}_rotmod.dat")
        if os.path.exists(path):
            return path
    path = os.path.join(data_dir, f"{galaxy_name}_rotmod.dat")
    return path if os.path.exists(path) else None


def run_pair(galaxy_name, data_dir, grid, verbose=True):
    """Run normal J and J=0, compare rotation curves."""
    dat_path = find_dat_path(galaxy_name, data_dir)
    if not dat_path:
        if verbose:
            print(f"  SKIP: {galaxy_name}")
        return None

    if verbose:
        print(f"\n{'═'*60}")
        print(f"  {galaxy_name} — NULL PUMP TEST")
        print(f"{'═'*60}")

    gal = load_galaxy(dat_path, grid)
    J_normal = gal["source_field"]
    J_zero = np.zeros_like(J_normal)
    v_max = float(np.max(gal["vobs"]))

    if verbose:
        print(f"  v_max = {v_max:.1f} km/s  |  "
              f"J_max = {np.max(J_normal):.2f}")

    results = {}

    for label, J_input in [("NORMAL", J_normal), ("NULL_J0", J_zero)]:
        if verbose:
            print(f"\n  ── {label} ──")

        t0 = time.time()
        solver = SubstrateSolver(
            grid=grid, layers=LAYERS, lam=LAMBDA,
            settle=SETTLE, measure=MEASURE)
        result = solver.run(J_input, verbose=False)
        elapsed = time.time() - t0

        comp = compare_rotation(result, gal)

        sigma_max = float(np.max(np.abs(result["sigma_avg"])))
        rho_max = float(np.max(np.abs(result["rho_avg"])))
        psi_max = float(result.get("psi_max", 0))

        if verbose:
            print(f"    σ_max:  {sigma_max:.6f}")
            print(f"    ρ_max:  {rho_max:.6f}")
            print(f"    Ψ_max:  {psi_max:.6f}")
            print(f"    RMS Newton:    {comp['rms_newton']:.2f} km/s")
            print(f"    RMS Substrate: {comp['rms_substrate']:.2f} km/s")
            print(f"    Winner: {comp['winner']}")
            print(f"    Elapsed: {elapsed:.1f}s")

        results[label] = {
            "sigma_max": sigma_max,
            "rho_max": rho_max,
            "psi_max": psi_max,
            "rms_newton": float(comp["rms_newton"]),
            "rms_substrate": float(comp["rms_substrate"]),
            "rms_mond": float(comp["rms_mond"]),
            "winner": comp["winner"],
            "sub_vs_newton": float(comp["sub_vs_newton"]),
            "corr_full": float(result.get("corr_full", 0)),
            "cos_delta_phi": float(result.get("cos_delta_phi", 0)),
            "elapsed": float(elapsed),
        }

    # ── Comparison ──
    normal = results["NORMAL"]
    null = results["NULL_J0"]

    sigma_ratio = null["sigma_max"] / normal["sigma_max"] \
        if normal["sigma_max"] > 0 else 0.0
    rms_change = null["rms_substrate"] - normal["rms_substrate"]
    field_collapsed = sigma_ratio < 0.01
    fit_degraded = null["rms_substrate"] > normal["rms_substrate"] * 1.5
    pump_essential = field_collapsed or fit_degraded

    if verbose:
        print(f"\n  ── COMPARISON ──")
        print(f"    σ ratio (null/normal): {sigma_ratio:.6f}")
        print(f"    Field collapsed:   {field_collapsed}")
        print(f"    RMS change:        {rms_change:+.2f} km/s")
        print(f"    Fit degraded:      {fit_degraded}")
        print(f"    PUMP ESSENTIAL:    {pump_essential}")

    return {
        "galaxy": galaxy_name,
        "v_max": v_max,
        "grid": grid,
        "normal": normal,
        "null_j0": null,
        "sigma_ratio": float(sigma_ratio),
        "rms_change": float(rms_change),
        "field_collapsed": field_collapsed,
        "fit_degraded": fit_degraded,
        "pump_essential": pump_essential,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v23 Null Pump Test (J=0)")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()

    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)

    print("=" * 60)
    print("  BCM v23 — NULL PUMP TEST (J = 0)")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)
    print(f"  Grid: {grid}  |  Galaxies: {len(TEST_GALAXIES)}")
    print(f"  Run 1: Normal J (baryonic source)")
    print(f"  Run 2: J = 0 (no pump)")
    print(f"  Question: does the pump matter?")
    print("=" * 60)

    data_dir = os.path.join(_PROJECT_ROOT, "data", "sparc_raw")
    if not os.path.isdir(data_dir):
        print(f"  ERROR: SPARC data not found")
        sys.exit(1)

    results = []
    t_total = time.time()

    for galaxy in TEST_GALAXIES:
        r = run_pair(galaxy, data_dir, grid)
        if r:
            results.append(r)

    elapsed_total = time.time() - t_total

    print(f"\n{'═'*60}")
    print(f"  NULL PUMP SUMMARY")
    print(f"{'═'*60}")

    if results:
        n_essential = sum(1 for r in results if r["pump_essential"])
        n_collapsed = sum(1 for r in results if r["field_collapsed"])
        n_degraded = sum(1 for r in results if r["fit_degraded"])

        print(f"  Galaxies tested:     {len(results)}")
        print(f"  Field collapsed:     {n_collapsed}/{len(results)}")
        print(f"  Fit degraded:        {n_degraded}/{len(results)}")
        print(f"  PUMP ESSENTIAL:      {n_essential}/{len(results)}")
        print(f"  Total elapsed:       {elapsed_total:.1f}s")

        print(f"\n  {'Galaxy':<12} {'σ ratio':>8} "
              f"{'RMS norm':>9} {'RMS null':>9} "
              f"{'Δ RMS':>7} {'Pump?':<8}")
        print(f"  {'─'*12} {'─'*8} {'─'*9} {'─'*9} "
              f"{'─'*7} {'─'*8}")
        for r in results:
            pump = "YES" if r["pump_essential"] else "no"
            print(f"  {r['galaxy']:<12} "
                  f"{r['sigma_ratio']:>8.6f} "
                  f"{r['normal']['rms_substrate']:>9.2f} "
                  f"{r['null_j0']['rms_substrate']:>9.2f} "
                  f"{r['rms_change']:>+7.2f} "
                  f"{pump:<8}")

        if n_essential == len(results):
            print(f"\n  VERDICT: The pump is ESSENTIAL for all "
                  f"{len(results)} galaxies.")
            print(f"  Without SMBH injection, the substrate")
            print(f"  field collapses and rotation fits degrade.")
            print(f"  The pump works through diffusion, not")
            print(f"  local surplus. Q < 0 everywhere is the")
            print(f"  signature of a regulated equilibrium,")
            print(f"  not a broken system.")
        elif n_essential == 0:
            print(f"\n  VERDICT: The pump is DECORATIVE.")
            print(f"  Field structure persists without J.")
            print(f"  The maintenance narrative needs revision.")
        else:
            print(f"\n  VERDICT: Mixed — pump essential for "
                  f"{n_essential}/{len(results)} galaxies.")

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(results_dir,
                            f"BCM_v23_null_pump_{timestamp}.json")

    output = {
        "test": "null_pump_j0",
        "version": "v23",
        "grid": grid,
        "question": "Does removing SMBH injection (J=0) collapse "
                    "the substrate field and degrade rotation fits?",
        "galaxies_tested": len(results),
        "pump_essential": n_essential if results else 0,
        "field_collapsed": n_collapsed if results else 0,
        "fit_degraded": n_degraded if results else 0,
        "lambda": LAMBDA,
        "kappa_BH": KAPPA_BH,
        "elapsed_total": float(elapsed_total),
        "timestamp": timestamp,
        "results": results,
    }

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n  JSON saved: {out_path}")
    print(f"\n  The Foreman asked: does the pump matter?")
    print(f"  The meter answers.")


if __name__ == "__main__":
    main()
