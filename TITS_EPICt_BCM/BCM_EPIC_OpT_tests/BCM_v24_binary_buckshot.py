# -*- coding: utf-8 -*-
"""
BCM v24 — BINARY BUCKSHOT DIFFUSER (SWISS CHEESE)
===================================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

Winchester T-400 logic applied to binary substrate:
Neutrino buckshot hits the binary torus, perforating it
like a shotgun pattern through a target. The torus acts
as a diffuser — the perforation pattern determines whether
the coherent substrate wave survives or scatters to noise.

Swiss Cheese effect: stochastic holes in the source field
create local dead zones where J is weakened. The substrate
must heal these holes through diffusion or lose coherence.

Two solver runs:
  LAMINAR: clean J (smooth wave, no perforations)
  PERFORATED: J × buckshot_mask (Swiss Cheese)

Metrics:
  Coherence = correlation between laminar and perforated σ
  Dissipation = 1 - coherence
  Spike ratio = perforated bill / laminar bill

Target: Alpha Centauri A+B (clean baseline binary).
Output JSON → data/results/BCM_v24_buckshot_YYYYMMDD_HHMMSS.json
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

LAMBDA     = 0.1
GRID_PROD  = 256
GRID_QUICK = 128
LAYERS     = 8
SETTLE     = 15000
MEASURE    = 5000

ALPHA_CEN = {
    "name": "Alpha Centauri",
    "m1": 1.1, "m2": 0.9,
    "sep": 4.0,
}

HR_1099 = {
    "name": "HR 1099",
    "m1": 1.0, "m2": 1.3,
    "sep": 1.0,
}


def run_buckshot_test(system, grid, verbose=True):
    """Laminar vs perforated: does Swiss Cheese kill coherence?"""
    if verbose:
        print(f"\n{'═'*60}")
        print(f"  {system['name']} — BINARY BUCKSHOT (SWISS CHEESE)")
        print(f"{'═'*60}")

    x = np.linspace(-10, 10, grid)
    y = np.linspace(-10, 10, grid)
    X, Y = np.meshgrid(x, y)

    r1 = np.sqrt((X + system['sep']/2)**2 + Y**2)
    r2 = np.sqrt((X - system['sep']/2)**2 + Y**2)
    J_base = (system['m1'] / (r1 + 0.5)) + (system['m2'] / (r2 + 0.5))

    # Throat zone (bombardment concentrated here)
    throat = np.exp(-(X**2 + Y**2) / 2.0)

    # ── LAMINAR RUN ──
    if verbose:
        print(f"  Running LAMINAR (smooth wave)...")
    t0 = time.time()
    solver = SubstrateSolver(grid=grid, layers=LAYERS, lam=LAMBDA,
                             settle=SETTLE, measure=MEASURE)
    lam_res = solver.run(J_base, verbose=False)
    t_lam = time.time() - t0

    sig_lam = lam_res["sigma_avg"]
    if sig_lam.ndim == 3:
        sig_lam_2d = np.mean(sig_lam, axis=0)
    else:
        sig_lam_2d = sig_lam

    # ── BUCKSHOT MASK (Swiss Cheese) ──
    # Stochastic perforation: each pixel gets random attenuation
    buckshot = np.random.normal(1.0, 0.4, (grid, grid))
    buckshot = np.clip(buckshot, 0.1, 2.0)

    # Apply in throat only (outer regions unaffected)
    J_perforated = J_base * (1.0 + (buckshot - 1.0) * throat)

    # ── PERFORATED RUN ──
    if verbose:
        print(f"  Running PERFORATED (Swiss Cheese)...")
    t0 = time.time()
    perf_res = solver.run(J_perforated, verbose=False)
    t_perf = time.time() - t0

    sig_perf = perf_res["sigma_avg"]
    if sig_perf.ndim == 3:
        sig_perf_2d = np.mean(sig_perf, axis=0)
    else:
        sig_perf_2d = sig_perf

    # ── Metrics ──
    coherence = float(np.corrcoef(
        sig_lam_2d.flatten(), sig_perf_2d.flatten())[0, 1])
    dissipation = 1.0 - coherence

    bill_lam = float(LAMBDA * np.sum(np.abs(sig_lam_2d)))
    bill_perf = float(LAMBDA * np.sum(np.abs(sig_perf_2d)))
    spike = bill_perf / bill_lam if bill_lam > 0 else 1.0

    # Throat-specific coherence
    throat_mask = throat > 0.5
    if np.any(throat_mask):
        throat_coh = float(np.corrcoef(
            sig_lam_2d[throat_mask],
            sig_perf_2d[throat_mask])[0, 1])
    else:
        throat_coh = coherence

    # Perforation survival: how much σ is preserved in throat
    throat_lam = float(np.mean(np.abs(sig_lam_2d[throat_mask])))
    throat_perf = float(np.mean(np.abs(sig_perf_2d[throat_mask])))
    throat_ratio = throat_perf / throat_lam if throat_lam > 0 else 0.0

    if verbose:
        print(f"\n  ── RESULTS ──")
        print(f"    Coherence (full):    {coherence:.6f}")
        print(f"    Coherence (throat):  {throat_coh:.6f}")
        print(f"    Dissipation:         {dissipation:.6f}")
        print(f"    Bill laminar:        {bill_lam:.2e}")
        print(f"    Bill perforated:     {bill_perf:.2e}")
        print(f"    Spike ratio:         {spike:.4f}×")
        print(f"    Throat survival:     {throat_ratio:.4f} "
              f"({throat_ratio*100:.1f}%)")
        print(f"    Elapsed: lam={t_lam:.1f}s  perf={t_perf:.1f}s")

        if coherence > 0.99:
            print(f"    VERDICT: LAMINAR MAINTAINED — "
                  f"Swiss Cheese healed by diffusion")
        elif coherence > 0.95:
            print(f"    VERDICT: MINOR SCATTER — "
                  f"buckshot dented but didn't break")
        else:
            print(f"    VERDICT: HIGH DISSIPATION — "
                  f"Swiss Cheese pattern survived")

    return {
        "system": system["name"], "grid": grid,
        "coherence": float(coherence),
        "throat_coherence": float(throat_coh),
        "dissipation": float(dissipation),
        "spike_ratio": float(spike),
        "throat_survival": float(throat_ratio),
        "bill_laminar": bill_lam,
        "bill_perforated": bill_perf,
        "elapsed_laminar": float(t_lam),
        "elapsed_perforated": float(t_perf),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v24 Binary Buckshot Diffuser")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()
    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)

    print("=" * 60)
    print("  BCM v24 — BINARY BUCKSHOT (SWISS CHEESE)")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)

    all_results = []
    t_total = time.time()

    for system in [ALPHA_CEN, HR_1099]:
        result = run_buckshot_test(system, grid)
        all_results.append(result)

    elapsed_total = time.time() - t_total

    # Summary
    print(f"\n{'═'*60}")
    print(f"  BUCKSHOT SUMMARY")
    print(f"{'═'*60}")
    print(f"  {'System':<18} {'Coh':>7} {'Throat':>7} "
          f"{'Spike':>7} {'Surv':>7}")
    print(f"  {'─'*18} {'─'*7} {'─'*7} {'─'*7} {'─'*7}")
    for r in all_results:
        print(f"  {r['system']:<18} {r['coherence']:>7.4f} "
              f"{r['throat_coherence']:>7.4f} "
              f"{r['spike_ratio']:>7.4f} "
              f"{r['throat_survival']:>7.4f}")

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(results_dir,
                            f"BCM_v24_buckshot_{timestamp}.json")
    output = {
        "test": "binary_buckshot_swiss_cheese",
        "version": "v24", "grid": grid,
        "systems_tested": len(all_results),
        "timestamp": timestamp,
        "elapsed_total": float(elapsed_total),
        "results": all_results,
        "foreman_note": "The torus acts as a grinder. "
                        "Neutrinos are the buckshot.",
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")

if __name__ == "__main__":
    main()
