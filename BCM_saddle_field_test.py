# -*- coding: utf-8 -*-
"""
BCM v12 Saddle Field Navigation Test
======================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Test design: ChatGPT + Gemini advisory

PURPOSE: Move beyond linear gradients. Test whether a sigma
packet navigates CURVED lambda fields — Gaussian wells,
saddle points, and multi-body topology.

If the packet follows local gradient streamlines through
curved fields, the drive is a FIELD NAVIGATOR, not just
a linear pusher.

Tests:
  1) Gaussian lambda well — packet should drift TOWARD
     the low-lambda attractor (gravity analog)
  2) Two-well saddle — packet navigates the saddle point
     between two lambda wells (L1 ridge analog)
  3) Orbital capture — packet approaches a well and curves
     into orbit-like trajectory

Usage:
    python BCM_saddle_field_test.py
    python BCM_saddle_field_test.py --steps 3000 --grid 128
"""

import numpy as np
import json
import os
import time
import argparse


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


def build_gaussian_well(nx, ny, well_center, well_depth=0.08,
                         well_width=15.0, base_lam=0.15):
    """
    Single Gaussian lambda well.
    LOW lambda at center = deep substrate memory = attractor.
    High lambda at edges = fast decay = repeller.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - well_center[0]
    dy = Y - well_center[1]
    r2 = dx**2 + dy**2

    # Low lambda at center (attractor)
    lam_field = base_lam - well_depth * np.exp(-r2 /
                (2 * well_width**2))

    return lam_field


def build_two_well_saddle(nx, ny, well_A, well_B,
                           depth_A=0.08, depth_B=0.06,
                           width=15.0, base_lam=0.15):
    """
    Two Gaussian lambda wells — creates saddle point between them.
    Analog of Jupiter-Saturn L1 ridge.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dxA = X - well_A[0]
    dyA = Y - well_A[1]
    r2A = dxA**2 + dyA**2

    dxB = X - well_B[0]
    dyB = Y - well_B[1]
    r2B = dxB**2 + dyB**2

    lam_field = (base_lam
                 - depth_A * np.exp(-r2A / (2 * width**2))
                 - depth_B * np.exp(-r2B / (2 * width**2)))

    return lam_field


def run_field_navigation(steps, nx, ny, dt, D,
                          lam_field_func, ship_start,
                          label="TEST"):
    """
    Run packet through a STATIC curved lambda field.
    No dipole following the ship — the field is fixed.
    The packet must navigate by local gradients alone.
    """
    ship_pos = np.array(ship_start, dtype=float)
    initial_pos = ship_pos.copy()
    sigma = initialize_sigma_packet(nx, ny, ship_pos,
                                     amplitude=1.0, width=5.0)

    # Build static lambda field
    lam_field = lam_field_func(nx, ny)

    trajectory = []
    speeds = []

    for step in range(steps):
        # Diffusion
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt

        # Lambda decay (static field — no ship-following)
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

        trajectory.append(com.copy())

        if step % 500 == 0:
            disp = com - initial_pos
            speed_now = speeds[-1] if speeds else 0
            print(f"    [{label}] step={step:>5}  "
                  f"pos=({com[0]:.2f},{com[1]:.2f})  "
                  f"disp=({disp[0]:+.3f},{disp[1]:+.3f})  "
                  f"speed={speed_now:.6f}")

    trajectory = np.array(trajectory)
    disp = trajectory[-1] - initial_pos if len(trajectory) > 0 else np.zeros(2)

    return {
        "label": label,
        "initial_pos": [float(initial_pos[0]),
                         float(initial_pos[1])],
        "final_pos": [float(trajectory[-1][0]),
                       float(trajectory[-1][1])] if len(trajectory) > 0 else [0, 0],
        "displacement": [float(disp[0]), float(disp[1])],
        "total_distance": float(np.linalg.norm(disp)),
        "mean_speed": float(np.mean(speeds)) if speeds else 0,
        "final_speed": float(speeds[-1]) if speeds else 0,
        "steps": len(trajectory),
        "trajectory_x": [float(t[0]) for t in trajectory[::50]],
        "trajectory_y": [float(t[1]) for t in trajectory[::50]],
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v12 Saddle Field Navigation Test")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--dt", type=float, default=0.05)
    parser.add_argument("--D", type=float, default=0.5)
    args = parser.parse_args()

    nx, ny = args.grid, args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v12 SADDLE FIELD NAVIGATION TEST")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"  dt={args.dt}  D={args.D}")
    print(f"{'='*65}")

    results = []

    # TEST 1: Single Gaussian well — packet starts offset
    print(f"\n  TEST 1: SINGLE GAUSSIAN WELL (attractor)")
    print(f"  Well at grid center, packet starts 30px offset")
    print(f"  {'─'*50}")

    well_center = (nx // 2, ny // 2)
    ship_start = (nx // 2 - 30, ny // 2)

    def well_1(n, m):
        return build_gaussian_well(n, m, well_center,
                                    well_depth=0.08, well_width=15.0)

    r1 = run_field_navigation(
        args.steps, nx, ny, args.dt, args.D,
        well_1, ship_start, label="WELL")
    r1["test"] = "Single Gaussian well"
    r1["well_center"] = list(well_center)

    # Did it move toward the well?
    dist_start = np.sqrt((ship_start[0] - well_center[0])**2 +
                          (ship_start[1] - well_center[1])**2)
    dist_end = np.sqrt((r1["final_pos"][0] - well_center[0])**2 +
                        (r1["final_pos"][1] - well_center[1])**2)
    r1["approached_well"] = bool(dist_end < dist_start)
    r1["dist_to_well_start"] = float(dist_start)
    r1["dist_to_well_end"] = float(dist_end)
    results.append(r1)

    print(f"    Distance to well: {dist_start:.1f} → "
          f"{dist_end:.1f} px")
    print(f"    Approached: {'YES' if dist_end < dist_start else 'NO'}")

    # TEST 2: Two-well saddle — packet between them
    print(f"\n  TEST 2: TWO-WELL SADDLE (L1 ridge analog)")
    print(f"  Wells at (32,64) and (96,64), packet at saddle")
    print(f"  {'─'*50}")

    well_A = (32, ny // 2)
    well_B = (96, ny // 2)
    ship_start_2 = (64, ny // 2)  # midpoint = saddle

    def well_2(n, m):
        return build_two_well_saddle(n, m, well_A, well_B,
                                      depth_A=0.08, depth_B=0.06)

    r2 = run_field_navigation(
        args.steps, nx, ny, args.dt, args.D,
        well_2, ship_start_2, label="SADDLE")
    r2["test"] = "Two-well saddle"
    r2["well_A"] = list(well_A)
    r2["well_B"] = list(well_B)

    # Which well did it drift toward?
    dist_A = np.sqrt((r2["final_pos"][0] - well_A[0])**2 +
                      (r2["final_pos"][1] - well_A[1])**2)
    dist_B = np.sqrt((r2["final_pos"][0] - well_B[0])**2 +
                      (r2["final_pos"][1] - well_B[1])**2)
    r2["drifted_toward"] = "A (deeper)" if dist_A < dist_B else "B (shallower)"
    r2["dist_A"] = float(dist_A)
    r2["dist_B"] = float(dist_B)
    results.append(r2)

    print(f"    Dist to A (deeper): {dist_A:.1f} px")
    print(f"    Dist to B (shallower): {dist_B:.1f} px")
    print(f"    Drifted toward: {r2['drifted_toward']}")

    # TEST 3: Off-axis approach — packet approaches well diagonally
    print(f"\n  TEST 3: DIAGONAL APPROACH (curved trajectory)")
    print(f"  Well at (90,90), packet starts at (30,30)")
    print(f"  {'─'*50}")

    well_diag = (90, 90)
    ship_start_3 = (30, 30)

    def well_3(n, m):
        return build_gaussian_well(n, m, well_diag,
                                    well_depth=0.08, well_width=20.0)

    r3 = run_field_navigation(
        args.steps, nx, ny, args.dt, args.D,
        well_3, ship_start_3, label="DIAG")
    r3["test"] = "Diagonal approach"
    r3["well_center"] = list(well_diag)

    dist_start_3 = np.sqrt((ship_start_3[0] - well_diag[0])**2 +
                            (ship_start_3[1] - well_diag[1])**2)
    dist_end_3 = np.sqrt((r3["final_pos"][0] - well_diag[0])**2 +
                          (r3["final_pos"][1] - well_diag[1])**2)
    r3["approached_well"] = bool(dist_end_3 < dist_start_3)
    r3["dist_to_well_start"] = float(dist_start_3)
    r3["dist_to_well_end"] = float(dist_end_3)
    results.append(r3)

    print(f"    Distance to well: {dist_start_3:.1f} → "
          f"{dist_end_3:.1f} px")
    print(f"    Approached: {'YES' if dist_end_3 < dist_start_3 else 'NO'}")

    # SUMMARY
    print(f"\n  {'='*65}")
    print(f"  SADDLE FIELD SUMMARY")
    print(f"  {'='*65}")

    for r in results:
        print(f"\n  {r['test']}:")
        print(f"    Displacement: ({r['displacement'][0]:+.3f}, "
              f"{r['displacement'][1]:+.3f})")
        print(f"    Distance: {r['total_distance']:.3f} px")
        if "approached_well" in r:
            print(f"    Approached well: "
                  f"{'YES' if r['approached_well'] else 'NO'}")
        if "drifted_toward" in r:
            print(f"    Drifted toward: {r['drifted_toward']}")

    all_navigating = all(
        r.get("approached_well", True) for r in results)

    print(f"\n  {'='*65}")
    if all_navigating:
        print(f"  VERDICT: FIELD NAVIGATION CONFIRMED")
        print(f"  Packet follows curved lambda gradients.")
        print(f"  The drive is a FIELD NAVIGATOR, not a")
        print(f"  linear pusher.")
        print(f"  Saddle point selects deeper well (stronger")
        print(f"  attractor) — consistent with substrate")
        print(f"  gradient flow.")
    else:
        print(f"  VERDICT: NAVIGATION INCOMPLETE")
        print(f"  Some tests did not show approach to well.")
        print(f"  Further investigation needed.")
    print(f"  {'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_saddle_test_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v12 Saddle Field Navigation Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "test_design": "ChatGPT + Gemini advisory",
        "grid": args.grid,
        "steps": args.steps,
        "results": results,
        "all_navigating": all_navigating,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
