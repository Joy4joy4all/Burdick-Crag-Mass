# -*- coding: utf-8 -*-
"""
BCM v12 Phase-Lag Coherence Test — Substrate Slew Rate
========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Test design: Gemini advisory

PURPOSE: Flip the lambda gradient 180 degrees mid-transit
and measure how many steps until velocity crosses zero
and reverses. This is the substrate's reorganization rate.

The slew rate determines:
  - How fast the pilot can change course
  - The minimum turn radius at speed
  - Whether coherence survives a hard redirect

Tests:
  1) Cruise 1000 steps +x, flip to -x, run 2000 more
  2) Measure: steps to v=0, steps to full reversal
  3) Track coherence through the flip — does it survive?
  4) Compare flip response at different delta_lam values

Usage:
    python BCM_phase_lag_test.py
    python BCM_phase_lag_test.py --steps 3000 --grid 128
"""

import numpy as np
import json
import os
import time
import argparse


def build_lambda_field(nx, ny, base_lam=0.1, delta_lam=0.05,
                        ship_pos=None, direction=(1, 0),
                        spread=10.0):
    """Smooth lambda dipole centered on ship position."""
    if ship_pos is None:
        ship_pos = (nx // 2, ny // 2)

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - ship_pos[0]
    dy = Y - ship_pos[1]

    d = np.array(direction, dtype=float)
    d /= (np.linalg.norm(d) + 1e-12)

    proj = dx * d[0] + dy * d[1]
    profile = np.tanh(proj / spread)
    lam_field = base_lam - delta_lam * profile

    return lam_field


def initialize_sigma_packet(nx, ny, center, amplitude=1.0,
                             width=5.0):
    """Create a Gaussian sigma packet."""
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    dx = X - center[0]
    dy = Y - center[1]
    r2 = dx**2 + dy**2
    return amplitude * np.exp(-r2 / (2 * width**2))


def compute_center_of_mass(sigma):
    """Track center of mass."""
    total = np.sum(sigma)
    if total < 1e-15:
        return None
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    cx = np.sum(X * sigma) / total
    cy = np.sum(Y * sigma) / total
    return np.array([cx, cy])


def compute_coherence(sigma, center, radius=10):
    """Measure packet coherence."""
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    dx = X - center[0]
    dy = Y - center[1]
    r2 = dx**2 + dy**2
    inside = np.sum(sigma[r2 < radius**2])
    total = np.sum(sigma)
    if total < 1e-15:
        return 0.0
    return inside / total


def run_phase_lag_test(steps_before=1000, steps_after=2000,
                        nx=128, ny=128, dt=0.05, D=0.5,
                        base_lam=0.1, delta_lam=0.05,
                        spread=10.0, label="LAG"):
    """
    Run cruise in +x, flip to -x at flip_step, measure response.
    """
    ship_pos = np.array([nx // 2, ny // 2], dtype=float)
    initial_pos = ship_pos.copy()
    sigma = initialize_sigma_packet(nx, ny, ship_pos)

    total_steps = steps_before + steps_after
    flip_step = steps_before

    # Data tracking
    positions_x = []
    velocities_x = []
    coherences = []
    directions = []
    energies = []

    prev_com = None

    for step in range(total_steps):
        # Direction: +x before flip, -x after flip
        if step < flip_step:
            direction = (1, 0)
            dir_label = "+x"
        else:
            direction = (-1, 0)
            dir_label = "-x"

        lam_field = build_lambda_field(
            nx, ny, base_lam=base_lam,
            delta_lam=delta_lam,
            ship_pos=ship_pos,
            direction=direction,
            spread=spread)

        # Diffusion
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt

        # Lambda decay
        sigma -= lam_field * sigma * dt
        sigma = np.maximum(sigma, 0)

        # Measure
        com = compute_center_of_mass(sigma)
        if com is None:
            print(f"    [{label}] Collapsed at step {step}")
            break

        positions_x.append(float(com[0]))
        coh = compute_coherence(sigma, com, radius=10)
        coherences.append(float(coh))
        energy = float(np.sum(sigma**2))
        energies.append(energy)
        directions.append(dir_label)

        if prev_com is not None:
            vx = float(com[0] - prev_com[0])
            velocities_x.append(vx)
        else:
            velocities_x.append(0.0)

        prev_com = com.copy()
        ship_pos = com

        if step % 500 == 0 or step == flip_step:
            marker = " ◄ FLIP" if step == flip_step else ""
            print(f"    [{label}] step={step:>5} dir={dir_label} "
                  f"x={com[0]:.2f} vx={velocities_x[-1]:+.6f} "
                  f"coh={coh:.4f}{marker}")

    # Analysis: find zero crossing and reversal
    zero_crossing_step = None
    full_reversal_step = None
    pre_flip_speed = abs(np.mean(velocities_x[max(0, flip_step-100):flip_step]))

    for i in range(flip_step, len(velocities_x)):
        vx = velocities_x[i]
        # Zero crossing: velocity changes sign
        if zero_crossing_step is None and vx < 0:
            zero_crossing_step = i
        # Full reversal: speed reaches pre-flip magnitude in opposite dir
        if zero_crossing_step is not None and abs(vx) >= pre_flip_speed * 0.5:
            full_reversal_step = i
            break

    lag_to_zero = (zero_crossing_step - flip_step
                    if zero_crossing_step else None)
    lag_to_reversal = (full_reversal_step - flip_step
                        if full_reversal_step else None)

    # Coherence at flip point
    coh_at_flip = coherences[flip_step] if flip_step < len(coherences) else 0
    coh_min_after = min(coherences[flip_step:]) if flip_step < len(coherences) else 0
    coh_at_end = coherences[-1] if coherences else 0

    # Peak displacement before flip
    peak_x = max(positions_x[:flip_step]) - initial_pos[0]

    return {
        "label": label,
        "flip_step": flip_step,
        "total_steps": len(velocities_x),
        "delta_lam": delta_lam,
        "pre_flip_speed": float(pre_flip_speed),
        "peak_displacement_before_flip": float(peak_x),
        "lag_to_zero_crossing": lag_to_zero,
        "lag_to_half_reversal": lag_to_reversal,
        "coherence_at_flip": float(coh_at_flip),
        "coherence_min_after_flip": float(coh_min_after),
        "coherence_at_end": float(coh_at_end),
        "coherence_survived": bool(coh_at_end > 0.05),
        "final_position_x": float(positions_x[-1]),
        "initial_position_x": float(initial_pos[0]),
        "final_displacement": float(positions_x[-1] - initial_pos[0]),
        "velocity_at_flip": float(velocities_x[flip_step]
                                   if flip_step < len(velocities_x) else 0),
        "velocity_at_end": float(velocities_x[-1]
                                  if velocities_x else 0),
        # Sampled data for plotting
        "sample_steps": list(range(0, len(velocities_x), 50)),
        "sample_vx": [velocities_x[i]
                       for i in range(0, len(velocities_x), 50)],
        "sample_coh": [coherences[i]
                        for i in range(0, len(coherences), 50)],
        "sample_x": [positions_x[i]
                      for i in range(0, len(positions_x), 50)],
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v12 Phase-Lag Coherence Test")
    parser.add_argument("--steps-before", type=int, default=1000,
                        help="Steps before gradient flip")
    parser.add_argument("--steps-after", type=int, default=2000,
                        help="Steps after gradient flip")
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--dt", type=float, default=0.05)
    parser.add_argument("--D", type=float, default=0.5)
    parser.add_argument("--spread", type=float, default=10.0)
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"  BCM v12 PHASE-LAG COHERENCE TEST")
    print(f"  Grid: {args.grid}x{args.grid}")
    print(f"  Cruise: {args.steps_before} steps +x")
    print(f"  After flip: {args.steps_after} steps -x")
    print(f"  dt={args.dt}  D={args.D}  spread={args.spread}")
    print(f"{'='*65}")

    # Run at multiple delta_lam values
    test_deltas = [0.03, 0.05, 0.08]
    results = []

    for dl in test_deltas:
        print(f"\n  DELTA_LAM = {dl}")
        print(f"  {'─'*50}")
        r = run_phase_lag_test(
            steps_before=args.steps_before,
            steps_after=args.steps_after,
            nx=args.grid, ny=args.grid,
            dt=args.dt, D=args.D,
            base_lam=0.1, delta_lam=dl,
            spread=args.spread,
            label=f"dL={dl}")
        results.append(r)

    # Summary
    print(f"\n  {'='*65}")
    print(f"  PHASE-LAG SUMMARY")
    print(f"  {'='*65}")
    print(f"  {'delta_lam':>10} {'Lag→0':>8} {'Lag→rev':>8} "
          f"{'Pre-v':>10} {'Coh@flip':>10} {'Coh_min':>10} "
          f"{'Survived':>10}")
    print(f"  {'─'*10} {'─'*8} {'─'*8} {'─'*10} {'─'*10} "
          f"{'─'*10} {'─'*10}")

    for r in results:
        lag0 = f"{r['lag_to_zero_crossing']}" if r['lag_to_zero_crossing'] else "N/A"
        lagr = f"{r['lag_to_half_reversal']}" if r['lag_to_half_reversal'] else "N/A"
        surv = "YES" if r['coherence_survived'] else "NO"
        print(f"  {r['delta_lam']:>10.2f} {lag0:>8} {lagr:>8} "
              f"{r['pre_flip_speed']:>10.6f} "
              f"{r['coherence_at_flip']:>10.4f} "
              f"{r['coherence_min_after_flip']:>10.4f} "
              f"{surv:>10}")

    # Verdict
    all_survived = all(r['coherence_survived'] for r in results)
    any_reversed = any(r['lag_to_zero_crossing'] is not None
                        for r in results)

    print(f"\n  {'='*65}")
    if any_reversed and all_survived:
        avg_lag = np.mean([r['lag_to_zero_crossing']
                           for r in results
                           if r['lag_to_zero_crossing'] is not None])
        print(f"  VERDICT: SUBSTRATE RESPONDS TO GRADIENT FLIP")
        print(f"  Average lag to zero crossing: {avg_lag:.0f} steps")
        print(f"  Coherence SURVIVED all flips.")
        print(f"  The substrate has a measurable slew rate.")
        print(f"  Course corrections are viable — crew can steer.")
    elif any_reversed and not all_survived:
        print(f"  VERDICT: RESPONSE EXISTS BUT COHERENCE DEGRADES")
        print(f"  The flip works but damages the packet.")
        print(f"  Course corrections require coherence management.")
    elif not any_reversed:
        print(f"  VERDICT: NO REVERSAL DETECTED AFTER FLIP")
        print(f"  Substrate does not respond to direction change.")
        print(f"  Steering may require full stop and restart.")
    print(f"  {'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_phase_lag_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v12 Phase-Lag Coherence Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "test_design": "Gemini advisory",
        "grid": args.grid,
        "steps_before": args.steps_before,
        "steps_after": args.steps_after,
        "results": results,
        "all_survived": all_survived,
        "any_reversed": any_reversed,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
