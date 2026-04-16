# -*- coding: utf-8 -*-
"""
BCM v24 — EDGE PERTURBATION TEST (SNAP-BACK)
=============================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

The transient snap-back test. Zero σ in a ring at 80% r_max
mid-settle, then measure whether the field recovers during
the measurement window.

Two runs:
  Run 1: BASELINE — normal settle + measure, no shear
  Run 2: SHEARED — σ zeroed in ring at step 15000,
          3000 steps to recover before measurement begins

Recovery ratio = σ_ring(sheared) / σ_ring(baseline)
  = 1.0 → full recovery (strong snap-back)
  = 0.0 → no recovery (dead zone)

Uses synthetic binary J (HR 1099 — dirty system with
high activity factor). The grind is the test bed.

Output JSON → data/results/BCM_v24_perturbation_YYYYMMDD_HHMMSS.json
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
SETTLE     = 18000
MEASURE    = 3000


class ShearCallback:
    """
    Mid-stream substrate shear. Zeros σ and ρ in a ring
    mask at the trigger step. Fires once.
    Signature: (step, total, rho, sigma)
    """
    def __init__(self, trigger_step, perturb_mask):
        self.trigger_step = trigger_step
        self.mask = perturb_mask
        self.applied = False

    def __call__(self, step, total, rho, sigma):
        if not self.applied and step >= self.trigger_step:
            for i in range(sigma.shape[0]):
                sigma[i][self.mask] = 0.0
                rho[i][self.mask] = 0.0
            self.applied = True


def build_binary_J(grid, m1=1.0, m2=1.3, sep=1.0,
                   activity=15.0):
    """Binary source field with baryonic grind noise (HR 1099)."""
    x = np.linspace(-5, 5, grid)
    y = np.linspace(-5, 5, grid)
    X, Y = np.meshgrid(x, y)
    r1 = np.sqrt((X + sep/2)**2 + Y**2)
    r2 = np.sqrt((X - sep/2)**2 + Y**2)
    J_base = (m1 / (r1 + 0.2)) + (m2 / (r2 + 0.2))
    throat = np.exp(-(X**2 + Y**2) / 1.0)
    grind = np.random.normal(0, 1.2, (grid, grid)) * activity
    J_net = J_base + grind * 0.05 * throat
    R = np.sqrt(X**2 + Y**2)
    return J_net, R


def run_perturbation_test(grid, verbose=True):
    if verbose:
        print(f"\n{'═'*60}")
        print(f"  HR 1099 — EDGE PERTURBATION (SNAP-BACK)")
        print(f"{'═'*60}")

    J_net, R = build_binary_J(grid)
    r_max = np.max(R)
    ring_mask = (R > 0.75 * r_max) & (R < 0.85 * r_max)

    if verbose:
        print(f"  Ring: 75-85% of r_max  |  {int(np.sum(ring_mask))} pixels")

    # ── BASELINE (no shear) ──
    if verbose:
        print(f"\n  ── BASELINE ──")
    t0 = time.time()
    solver = SubstrateSolver(grid=grid, layers=LAYERS, lam=LAMBDA,
                             settle=SETTLE, measure=MEASURE)
    base_res = solver.run(J_net, verbose=False)
    t_base = time.time() - t0

    sig_base = base_res["sigma_avg"]
    if sig_base.ndim == 3:
        sig_base = np.mean(sig_base, axis=0)
    ring_base = float(np.mean(np.abs(sig_base[ring_mask])))
    core_base = float(np.mean(np.abs(sig_base[R < 0.33 * r_max])))

    if verbose:
        print(f"    σ_ring: {ring_base:.4f}  |  σ_core: {core_base:.4f}")
        print(f"    Elapsed: {t_base:.1f}s")

    # ── SHEARED (ring zeroed at step 15000) ──
    shear_step = SETTLE - 3000
    if verbose:
        print(f"\n  ── SHEARED (step {shear_step}) ──")
    cb = ShearCallback(shear_step, ring_mask)
    t0 = time.time()
    solver2 = SubstrateSolver(grid=grid, layers=LAYERS, lam=LAMBDA,
                              settle=SETTLE, measure=MEASURE)
    shear_res = solver2.run(J_net, verbose=False, callback=cb)
    t_shear = time.time() - t0

    sig_shear = shear_res["sigma_avg"]
    if sig_shear.ndim == 3:
        sig_shear = np.mean(sig_shear, axis=0)
    ring_shear = float(np.mean(np.abs(sig_shear[ring_mask])))
    core_shear = float(np.mean(np.abs(sig_shear[R < 0.33 * r_max])))

    # ── Metrics ──
    recovery = ring_shear / ring_base if ring_base > 0 else 0.0
    core_stable = core_shear / core_base if core_base > 0 else 0.0
    torque = float(np.std(sig_shear[ring_mask]))

    if recovery > 0.90:
        verdict = "FULL SNAP-BACK"
    elif recovery > 0.50:
        verdict = "PARTIAL SNAP-BACK"
    elif recovery > 0.10:
        verdict = "WEAK RECOVERY"
    else:
        verdict = "NO SNAP-BACK"

    if verbose:
        print(f"    σ_ring: {ring_shear:.4f}  |  σ_core: {core_shear:.4f}")
        print(f"    Elapsed: {t_shear:.1f}s")
        print(f"\n  ── RECOVERY ──")
        print(f"    Ring: {recovery:.4f} ({recovery*100:.1f}%)")
        print(f"    Core: {core_stable:.4f} ({core_stable*100:.1f}%)")
        print(f"    Torque: {torque:.6f}")
        print(f"    VERDICT: {verdict}")

    return {
        "system": "HR 1099", "grid": grid,
        "shear_step": shear_step,
        "ring_baseline": ring_base, "ring_sheared": ring_shear,
        "core_baseline": core_base, "core_sheared": core_shear,
        "recovery_ratio": float(recovery),
        "core_stability": float(core_stable),
        "torque_signal": torque,
        "snap_detected": recovery > 0.50,
        "verdict": verdict,
        "shear_applied": cb.applied,
        "elapsed_baseline": float(t_base),
        "elapsed_sheared": float(t_shear),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v24 Edge Perturbation (Snap-Back)")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()
    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)

    print("=" * 60)
    print("  BCM v24 — EDGE PERTURBATION TEST (SNAP-BACK)")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)

    result = run_perturbation_test(grid)

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(results_dir,
                            f"BCM_v24_perturbation_{timestamp}.json")
    output = {
        "test": "edge_perturbation_snapback",
        "version": "v24", "grid": grid,
        "timestamp": timestamp,
        "elapsed_total": result["elapsed_baseline"]
                         + result["elapsed_sheared"],
        "results": result,
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")

if __name__ == "__main__":
    main()
