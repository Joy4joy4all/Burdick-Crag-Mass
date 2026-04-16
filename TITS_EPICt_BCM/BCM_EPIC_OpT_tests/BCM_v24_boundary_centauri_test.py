# -*- coding: utf-8 -*-
"""
BCM v24 — ALPHA CENTAURI BOUNDARY STABILITY (PHASE-DEPENDENT)
==============================================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

The binary torus is NOT symmetric. The A pump (dominant) and
B pump (secondary) create different σ profiles on each side.
Arriving on the A-side means hitting high σ. Arriving on the
B-side means hitting low σ. The orbital phase (swirl) determines
which face the craft encounters.

This test runs the clamp boundary stability sweep on Alpha
Centauri at four arrival angles:

  0°   = A-side (dominant pump face)
  90°  = perpendicular (throat corridor)
  180° = B-side (secondary pump face)
  270° = perpendicular (opposite throat)

For each angle, measures:
  - Baseline σ at the approach ring
  - Clamp effectiveness (σ_crit=10, σ_crit=5)
  - Whether the boundary is thinner/thicker on each side

This determines arrival protocol by approach vector.
The 3D renders from v7-v11 showed this asymmetry visually.
Now we measure it.

Output JSON → data/results/BCM_v24_boundary_centauri_YYYYMMDD_HHMMSS.json
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
MEASURE    = 6000

ALPHA_CEN = {
    "name": "Alpha Centauri",
    "m1": 1.1,   # A (dominant)
    "m2": 0.9,   # B (secondary)
    "sep": 4.0,  # wider binary
}

# Arrival angles (degrees from A-pump axis)
APPROACH_ANGLES = [0, 90, 180, 270]

# Boundary treatment: clamp only (proven stable in HR 1099 sweep)
SIGMA_CRITS = [10.0, 5.0]


class DirectionalBoundaryCallback:
    """
    Shears an angular wedge of the boundary ring, then
    applies σ clamp. Measures recovery by angle.
    """
    def __init__(self, trigger_step, wedge_mask, sigma_crit=10.0):
        self.trigger_step = trigger_step
        self.wedge_mask = wedge_mask
        self.sigma_crit = sigma_crit
        self.sheared = False
        self.steps = []
        self.wedge_sigma = []

    def __call__(self, step, total, rho, sigma):
        if not self.sheared and step >= self.trigger_step:
            for i in range(sigma.shape[0]):
                sigma[i][self.wedge_mask] = 0.0
                rho[i][self.wedge_mask] = 0.0
            self.sheared = True

        # Apply clamp after shear
        if self.sheared:
            for i in range(sigma.shape[0]):
                mask = sigma[i] > self.sigma_crit
                combined = mask & self.wedge_mask
                sigma[i][combined] = self.sigma_crit

        # Record
        if step >= self.trigger_step - 2000:
            sig_2d = np.mean(sigma, axis=0) if sigma.ndim == 3 \
                else sigma
            val = float(np.mean(np.abs(sig_2d[self.wedge_mask])))
            self.steps.append(int(step))
            self.wedge_sigma.append(val)


def build_binary_J(grid, system):
    """Binary source field for Alpha Centauri."""
    x = np.linspace(-10, 10, grid)
    y = np.linspace(-10, 10, grid)
    X, Y = np.meshgrid(x, y)

    sep = system['sep']
    r1 = np.sqrt((X + sep/2)**2 + Y**2)
    r2 = np.sqrt((X - sep/2)**2 + Y**2)
    J = (system['m1'] / (r1 + 0.3)) + (system['m2'] / (r2 + 0.3))

    R = np.sqrt(X**2 + Y**2)
    THETA = np.arctan2(Y, X)  # angle from +x axis (A-pump direction)
    return J, X, Y, R, THETA


def make_wedge_mask(R, THETA, r_max, angle_deg, wedge_width=45):
    """
    Create a wedge-shaped ring mask at a specific approach angle.
    Ring: 75-85% of r_max
    Wedge: ±wedge_width degrees around approach angle
    """
    ring = (R > 0.75 * r_max) & (R < 0.85 * r_max)
    angle_rad = np.radians(angle_deg)
    half_w = np.radians(wedge_width)

    # Handle angle wrapping
    angle_diff = np.abs(np.arctan2(
        np.sin(THETA - angle_rad),
        np.cos(THETA - angle_rad)))
    wedge = angle_diff < half_w

    return ring & wedge


def run_angle_test(system, grid, angle_deg, sigma_crit,
                   J, R, THETA, verbose=True):
    """Run one angle + one σ_crit config."""
    r_max = np.max(R)
    wedge = make_wedge_mask(R, THETA, r_max, angle_deg)
    n_pixels = int(np.sum(wedge))

    if n_pixels < 5:
        return None

    # Side label
    if angle_deg == 0:
        side = "A-SIDE (dominant)"
    elif angle_deg == 180:
        side = "B-SIDE (secondary)"
    elif angle_deg == 90:
        side = "THROAT (perpendicular)"
    else:
        side = "ANTI-THROAT (270°)"

    if verbose:
        print(f"    {side}  |  σ_crit={sigma_crit}  |  "
              f"{n_pixels} px")

    shear_step = SETTLE - 3000
    cb = DirectionalBoundaryCallback(
        trigger_step=shear_step,
        wedge_mask=wedge,
        sigma_crit=sigma_crit)

    solver = SubstrateSolver(grid=grid, layers=LAYERS, lam=LAMBDA,
                             settle=SETTLE, measure=MEASURE)
    t0 = time.time()
    res = solver.run(J, verbose=False, callback=cb)
    elapsed = time.time() - t0

    # Baseline and final
    pre = [s for s, st in zip(cb.wedge_sigma, cb.steps)
           if st < shear_step]
    baseline = float(np.mean(pre)) if pre else 0.0
    final = float(cb.wedge_sigma[-1]) if cb.wedge_sigma else 0.0

    ratio = final / baseline if baseline > 0 else 0.0
    stable = ratio <= 2.0

    if verbose:
        print(f"      Baseline: {baseline:.4f}  →  Final: {final:.4f}"
              f"  ({ratio:.2f}×)  "
              f"{'STABLE' if stable else 'FLOOD'}")

    return {
        "angle_deg": angle_deg,
        "side": side,
        "sigma_crit": float(sigma_crit),
        "n_pixels": n_pixels,
        "baseline": baseline,
        "final": final,
        "ratio": float(ratio),
        "stable": stable,
        "elapsed": float(elapsed),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v24 Alpha Centauri Boundary (Phase)")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()
    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)

    print("=" * 60)
    print("  BCM v24 — ALPHA CENTAURI BOUNDARY STABILITY")
    print("  Phase-Dependent Arrival (Swirl Rate)")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)
    print(f"  Grid: {grid}")
    print(f"  Arrival angles: {APPROACH_ANGLES}°")
    print(f"  σ_crit values: {SIGMA_CRITS}")
    print(f"  A-pump (dominant): m={ALPHA_CEN['m1']}")
    print(f"  B-pump (secondary): m={ALPHA_CEN['m2']}")
    print("=" * 60)

    J, X, Y, R, THETA = build_binary_J(grid, ALPHA_CEN)

    all_results = []
    t_total = time.time()

    for sigma_crit in SIGMA_CRITS:
        print(f"\n  ── σ_crit = {sigma_crit} ──")
        for angle in APPROACH_ANGLES:
            r = run_angle_test(ALPHA_CEN, grid, angle, sigma_crit,
                               J, R, THETA)
            if r:
                all_results.append(r)

    elapsed_total = time.time() - t_total

    # Summary
    print(f"\n{'═'*60}")
    print(f"  PHASE-DEPENDENT BOUNDARY SUMMARY")
    print(f"{'═'*60}")
    print(f"  {'Side':<22} {'σ_crit':>6} {'Base':>8} "
          f"{'Final':>8} {'Ratio':>6} {'Status'}")
    print(f"  {'─'*22} {'─'*6} {'─'*8} {'─'*8} {'─'*6} {'─'*8}")
    for r in all_results:
        st = "STABLE" if r["stable"] else "FLOOD"
        print(f"  {r['side']:<22} {r['sigma_crit']:>6.0f} "
              f"{r['baseline']:>8.2f} {r['final']:>8.2f} "
              f"{r['ratio']:>6.2f} {st}")

    # Key finding: A-side vs B-side asymmetry
    a_sides = [r for r in all_results if r["angle_deg"] == 0]
    b_sides = [r for r in all_results if r["angle_deg"] == 180]
    if a_sides and b_sides:
        print(f"\n  A-SIDE vs B-SIDE ASYMMETRY:")
        for a, b in zip(a_sides, b_sides):
            print(f"    σ_crit={a['sigma_crit']:.0f}: "
                  f"A baseline={a['baseline']:.2f}  "
                  f"B baseline={b['baseline']:.2f}  "
                  f"ratio={a['baseline']/b['baseline']:.2f}×")

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(results_dir,
                            f"BCM_v24_boundary_centauri_{timestamp}.json")
    output = {
        "test": "boundary_centauri_phase",
        "version": "v24",
        "grid": grid,
        "system": ALPHA_CEN["name"],
        "angles_tested": APPROACH_ANGLES,
        "sigma_crits": SIGMA_CRITS,
        "configs_tested": len(all_results),
        "stable_count": sum(1 for r in all_results if r["stable"]),
        "timestamp": timestamp,
        "elapsed_total": float(elapsed_total),
        "results": all_results,
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")

if __name__ == "__main__":
    main()
