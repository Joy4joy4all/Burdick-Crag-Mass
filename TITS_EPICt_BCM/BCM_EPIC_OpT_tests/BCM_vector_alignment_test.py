# -*- coding: utf-8 -*-
"""
BCM v12 Vector Alignment Test — Collinearity Diagnostic
=========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Test design: ChatGPT + Gemini advisory

PURPOSE: Determine if drift is strictly aligned with the
lambda gradient or has orthogonal components.

If cos(theta) < 1.0, the craft drifts off course during
long-haul transit. This is a crew safety diagnostic.

Tests:
  1) +x gradient → measure alignment
  2) 45-degree gradient → verify drift follows TRUE gradient,
     not grid axes (rules out lattice bias)
  3) +y gradient → verify axis independence

Usage:
    python BCM_vector_alignment_test.py
    python BCM_vector_alignment_test.py --steps 2000 --grid 128
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


def run_alignment_test(steps=2000, nx=128, ny=128, dt=0.05,
                        D=0.5, base_lam=0.1, delta_lam=0.05,
                        spread=10.0, direction=(1, 0),
                        label="TEST"):
    """
    Run drift test and measure alignment between velocity
    and gradient direction at every step.
    """
    ship_pos = np.array([nx // 2, ny // 2], dtype=float)
    initial_pos = ship_pos.copy()
    sigma = initialize_sigma_packet(nx, ny, ship_pos)

    # Normalize direction
    d = np.array(direction, dtype=float)
    d /= (np.linalg.norm(d) + 1e-12)

    trajectory = []
    alignments = []  # cos(theta) at each step
    speeds = []

    for step in range(steps):
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

        if len(trajectory) > 0:
            vel = com - trajectory[-1]
            speed = np.linalg.norm(vel)
            speeds.append(speed)

            if speed > 1e-12:
                # cos(theta) between velocity and gradient direction
                cos_theta = np.dot(vel, d) / (speed + 1e-15)
                alignments.append(float(cos_theta))

        trajectory.append(com.copy())
        ship_pos = com

        if step % 500 == 0:
            disp = com - initial_pos
            cos_avg = np.mean(alignments) if alignments else 0
            print(f"    [{label}] step={step:>5}  "
                  f"pos=({com[0]:.2f},{com[1]:.2f})  "
                  f"disp=({disp[0]:+.3f},{disp[1]:+.3f})  "
                  f"cos_avg={cos_avg:.6f}")

    trajectory = np.array(trajectory)
    disp = trajectory[-1] - initial_pos if len(trajectory) > 0 else np.zeros(2)

    # Overall alignment: angle between net displacement and gradient
    disp_mag = np.linalg.norm(disp)
    if disp_mag > 1e-10:
        cos_overall = np.dot(disp, d) / disp_mag
        angle_deg = np.degrees(np.arccos(np.clip(cos_overall, -1, 1)))
    else:
        cos_overall = 0
        angle_deg = 90

    return {
        "direction": [float(d[0]), float(d[1])],
        "displacement": [float(disp[0]), float(disp[1])],
        "total_distance": float(disp_mag),
        "cos_overall": float(cos_overall),
        "angle_deg": float(angle_deg),
        "cos_mean": float(np.mean(alignments)) if alignments else 0,
        "cos_min": float(np.min(alignments)) if alignments else 0,
        "cos_max": float(np.max(alignments)) if alignments else 0,
        "cos_std": float(np.std(alignments)) if alignments else 0,
        "mean_speed": float(np.mean(speeds)) if speeds else 0,
        "steps": len(trajectory),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v12 Vector Alignment Test")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--dt", type=float, default=0.05)
    parser.add_argument("--D", type=float, default=0.5)
    parser.add_argument("--delta-lam", type=float, default=0.05)
    parser.add_argument("--spread", type=float, default=10.0)
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"  BCM v12 VECTOR ALIGNMENT TEST — COLLINEARITY")
    print(f"  Grid: {args.grid}x{args.grid}  Steps: {args.steps}")
    print(f"  delta_lam={args.delta_lam}  spread={args.spread}")
    print(f"{'='*65}")

    test_directions = [
        ((1, 0),  "+x (baseline)"),
        ((0, 1),  "+y (axis independence)"),
        ((1, 1),  "45 deg (lattice bias check)"),
        ((-1, 1), "135 deg (anti-diagonal)"),
    ]

    results = []

    for direction, label in test_directions:
        print(f"\n  DIRECTION: {label}")
        print(f"  {'─'*50}")
        r = run_alignment_test(
            steps=args.steps, nx=args.grid, ny=args.grid,
            dt=args.dt, D=args.D, delta_lam=args.delta_lam,
            spread=args.spread, direction=direction,
            label=label[:6])
        r["label"] = label
        results.append(r)

    # Summary table
    print(f"\n  {'='*65}")
    print(f"  ALIGNMENT SUMMARY")
    print(f"  {'='*65}")
    print(f"  {'Direction':>20} {'Drift(px)':>10} {'cos_θ':>8} "
          f"{'Angle°':>8} {'cos_mean':>10} {'cos_std':>10}")
    print(f"  {'─'*20} {'─'*10} {'─'*8} {'─'*8} {'─'*10} {'─'*10}")

    all_aligned = True
    for r in results:
        aligned = "✓" if r["cos_overall"] > 0.999 else "✗"
        if r["cos_overall"] <= 0.999:
            all_aligned = False
        print(f"  {r['label']:>20} {r['total_distance']:>10.4f} "
              f"{r['cos_overall']:>8.6f} {r['angle_deg']:>8.4f} "
              f"{r['cos_mean']:>10.6f} {r['cos_std']:>10.6f}  {aligned}")

    print(f"\n  {'='*65}")
    if all_aligned:
        print(f"  VERDICT: ALL DIRECTIONS ALIGNED (cos_θ > 0.999)")
        print(f"  The lambda drive follows the TRUE gradient.")
        print(f"  No lattice bias. No orthogonal drift.")
        print(f"  CREW SAFETY: trajectory is on-vector.")
    else:
        print(f"  VERDICT: ALIGNMENT DEVIATION DETECTED")
        print(f"  Some directions show cos_θ < 0.999")
        print(f"  Orthogonal drift exists — investigate before")
        print(f"  committing to long-duration transits.")
    print(f"  {'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_alignment_test_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v12 Vector Alignment Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "test_design": "ChatGPT + Gemini advisory",
        "grid": args.grid,
        "steps": args.steps,
        "delta_lam": args.delta_lam,
        "spread": args.spread,
        "results": results,
        "all_aligned": all_aligned,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
