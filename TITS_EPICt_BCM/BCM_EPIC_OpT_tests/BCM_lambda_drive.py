# -*- coding: utf-8 -*-
"""
BCM v12 Lambda Drive Simulator — Substrate Navigation Prototype
================================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

SPECULATIVE — Theoretical extrapolation from BCM solver behavior.
No claims of engineering feasibility.

Simulates a small "ship" perturbation moving between two sigma
wells (origin and destination) with fore/aft lambda modulation.
Measures coherence maintenance, sigma gradient response, and
wake formation.

Usage:
    python BCM_lambda_drive.py
    python BCM_lambda_drive.py --grid 128 --lam-fore 0.05 --lam-aft 0.20
"""

import numpy as np
import json
import os
import time
import argparse


def build_solar_field(grid, well_positions, well_strengths):
    """
    Build a static sigma well map representing the solar system
    substrate topology. Wells are Gaussian sigma sources.
    Returns J_bg (background source field, 2D).
    """
    J_bg = np.zeros((grid, grid))
    yy, xx = np.mgrid[0:grid, 0:grid]
    center_y = grid // 2

    for (wx, wy), strength in zip(well_positions, well_strengths):
        r = np.sqrt((xx - wx)**2 + (yy - wy)**2)
        width = max(3, grid // 25)
        J_bg += strength * np.exp(-r**2 / (2 * width**2))

    return J_bg


def build_lambda_field(grid, ship_x, ship_y, lam_base,
                        lam_fore, lam_aft, heading_x=1,
                        mod_radius=None):
    """
    Build spatially varying lambda field with fore/aft modulation
    around the ship position.

    lam_fore: lambda value ahead of ship (lower = deeper memory)
    lam_aft:  lambda value behind ship (higher = faster decay)
    heading_x: +1 = moving right, -1 = moving left
    """
    lam_field = np.full((grid, grid), lam_base)

    if mod_radius is None:
        mod_radius = max(4, grid // 16)

    yy, xx = np.mgrid[0:grid, 0:grid]
    r = np.sqrt((xx - ship_x)**2 + (yy - ship_y)**2)

    # Directional weighting: cos(angle) relative to heading
    dx = (xx - ship_x) * heading_x
    angle_weight = dx / (r + 1e-8)  # -1 to +1

    # Fore region: angle_weight > 0 (ahead)
    # Aft region: angle_weight < 0 (behind)
    mask = r < mod_radius * 2

    fore_mask = mask & (angle_weight > 0.2)
    aft_mask = mask & (angle_weight < -0.2)

    # Smooth modulation with Gaussian rolloff
    rolloff = np.exp(-r**2 / (2 * mod_radius**2))

    lam_field[fore_mask] = (lam_base +
        (lam_fore - lam_base) * rolloff[fore_mask])
    lam_field[aft_mask] = (lam_base +
        (lam_aft - lam_base) * rolloff[aft_mask])

    return lam_field


def run_lambda_drive(grid=128, lam_base=0.1,
                      lam_fore=0.05, lam_aft=0.20,
                      n_transit_steps=20,
                      settle=10000, measure=3000):
    """
    Simulate a ship transit between two sigma wells with
    lambda modulation.

    The simulation runs the solver at each ship position
    (static snapshots along the transit path) and measures
    substrate response.
    """
    from core.substrate_solver import SubstrateSolver

    print(f"\n{'='*65}")
    print(f"  BCM v12 LAMBDA DRIVE SIMULATOR")
    print(f"  Grid: {grid}  lam_base={lam_base}")
    print(f"  lam_fore={lam_fore}  lam_aft={lam_aft}")
    print(f"  Transit steps: {n_transit_steps}")
    print(f"{'='*65}")

    center_y = grid // 2

    # Solar system layout (simplified)
    # Sun at left, target planet at right
    sun_x = grid // 6
    planet_x = grid * 5 // 6

    # Well strengths
    sun_strength = 50.0
    planet_strength = 8.0

    # Ship parameters
    ship_strength = 0.5  # tiny perturbation
    ship_start = sun_x + grid // 8
    ship_end = planet_x - grid // 8

    # Transit positions (linear for now)
    ship_positions = np.linspace(ship_start, ship_end,
                                  n_transit_steps).astype(int)

    print(f"  Sun well: x={sun_x} (strength={sun_strength})")
    print(f"  Planet well: x={planet_x} "
          f"(strength={planet_strength})")
    print(f"  Ship transit: x={ship_start} → x={ship_end}")

    # Background field (static)
    wells = [(sun_x, center_y), (planet_x, center_y)]
    strengths = [sun_strength, planet_strength]
    J_bg = build_solar_field(grid, wells, strengths)

    print(f"\n  {'step':>4} {'ship_x':>6} {'cos_dphi':>10} "
          f"{'sig_ship':>10} {'sig_fore':>10} {'sig_aft':>10} "
          f"{'gradient':>10} {'phi_reach':>10}")
    print(f"  {'-'*4} {'-'*6} {'-'*10} {'-'*10} {'-'*10} "
          f"{'-'*10} {'-'*10} {'-'*10}")

    results = []

    for si, ship_x in enumerate(ship_positions):
        # Build source: background + ship
        yy, xx = np.mgrid[0:grid, 0:grid]
        r_ship = np.sqrt((xx - ship_x)**2 +
                          (yy - center_y)**2)
        ship_width = max(2, grid // 40)
        J_ship = ship_strength * np.exp(
            -r_ship**2 / (2 * ship_width**2))
        J_total = J_bg + J_ship

        # Build lambda field with modulation
        lam_field = build_lambda_field(
            grid, ship_x, center_y, lam_base,
            lam_fore, lam_aft, heading_x=1)

        # Run solver with spatially varying lambda
        # Note: current solver uses scalar lambda.
        # For v12 prototype, we use the mean lambda
        # in the ship's vicinity as the effective lambda.
        # Full spatial lambda requires solver modification.
        ship_region = lam_field[
            max(0, center_y - 10):center_y + 10,
            max(0, ship_x - 10):min(grid, ship_x + 10)]
        lam_effective = float(np.mean(ship_region))

        solver = SubstrateSolver(
            grid=grid, layers=6,
            lam=lam_effective, gamma=0.05,
            entangle=0.02, c_wave=1.0,
            settle=settle, measure=measure)

        result = solver.run(J_total, verbose=False)

        # Sample sigma field at ship, fore, and aft
        sigma_avg = result.get("sigma_avg")
        sig_field = sigma_avg.sum(axis=0)
        cos_dphi = result.get("cos_delta_phi", 0)

        r = max(3, grid // 32)

        def _s(f, cx, cy):
            return float(np.max(np.abs(
                f[max(0, cy - r):cy + r,
                  max(0, cx - r):min(grid, cx + r)])))

        # Measure points
        fore_x = min(grid - 1, ship_x + grid // 12)
        aft_x = max(0, ship_x - grid // 12)

        sig_ship = _s(sig_field, ship_x, center_y)
        sig_fore = _s(sig_field, fore_x, center_y)
        sig_aft = _s(sig_field, aft_x, center_y)
        gradient = sig_fore - sig_aft

        # Phi_reach around ship (simplified)
        cpf = result.get("cos_delta_phi_field")
        phi_reach = 0.0
        if cpf is not None:
            ship_region_cpf = cpf[
                max(0, center_y - 15):center_y + 15,
                max(0, ship_x - 15):min(grid, ship_x + 15)]
            above = np.sum(ship_region_cpf > 0.999999)
            total = ship_region_cpf.size
            phi_reach = 100.0 * above / total if total > 0 else 0

        print(f"  {si:>4} {ship_x:>6} {cos_dphi:>+10.6f} "
              f"{sig_ship:>10.1f} {sig_fore:>10.1f} "
              f"{sig_aft:>10.1f} {gradient:>+10.1f} "
              f"{phi_reach:>9.1f}%")

        results.append({
            "step":       si,
            "ship_x":     int(ship_x),
            "lam_eff":    round(lam_effective, 4),
            "cos_delta_phi": cos_dphi,
            "sig_ship":   round(sig_ship, 2),
            "sig_fore":   round(sig_fore, 2),
            "sig_aft":    round(sig_aft, 2),
            "gradient":   round(gradient, 2),
            "phi_reach":  round(phi_reach, 2),
        })

    # --- Summary ---
    print(f"\n  {'='*65}")
    print(f"  LAMBDA DRIVE TRANSIT SUMMARY")
    print(f"  {'='*65}")

    gradients = [r["gradient"] for r in results]
    reaches = [r["phi_reach"] for r in results]
    print(f"  Gradient range: {min(gradients):+.1f} → "
          f"{max(gradients):+.1f}")
    print(f"  Phi_reach range: {min(reaches):.1f}% → "
          f"{max(reaches):.1f}%")

    coherent = all(r["phi_reach"] > 5.0 for r in results)
    print(f"  Coherence maintained: "
          f"{'YES' if coherent else 'LOST AT SOME POINTS'}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_lambda_drive_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title":     "BCM v12 Lambda Drive Transit Simulation",
        "author":    "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "status":    "SPECULATIVE — theoretical extrapolation",
        "grid":      grid,
        "lam_base":  lam_base,
        "lam_fore":  lam_fore,
        "lam_aft":   lam_aft,
        "sun_strength": sun_strength,
        "planet_strength": planet_strength,
        "n_steps":   len(results),
        "coherent":  coherent,
        "results":   results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")

    return out_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v12 Lambda Drive Simulator")
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--lam-base", type=float, default=0.1,
                        help="Baseline lambda")
    parser.add_argument("--lam-fore", type=float, default=0.05,
                        help="Lambda ahead of ship (lower=deeper)")
    parser.add_argument("--lam-aft", type=float, default=0.20,
                        help="Lambda behind ship (higher=shallower)")
    parser.add_argument("--steps", type=int, default=20,
                        help="Number of transit positions")
    parser.add_argument("--settle", type=int, default=10000)
    parser.add_argument("--measure", type=int, default=3000)
    args = parser.parse_args()

    run_lambda_drive(grid=args.grid,
                      lam_base=args.lam_base,
                      lam_fore=args.lam_fore,
                      lam_aft=args.lam_aft,
                      n_transit_steps=args.steps,
                      settle=args.settle,
                      measure=args.measure)
