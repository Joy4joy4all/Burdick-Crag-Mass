# -*- coding: utf-8 -*-
"""
BCM v13 SPINE — Alpha Centauri Corridor Test
===============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Multi-attractor test: Sol + Alpha Centauri in a galactic
current field. Find the point of minimum resistance for
the first interstellar transit.

Tests:
  1. Sol-AlphaCen corridor with galactic current
  2. Edge-riding vs direct path (void boundary surf)
  3. Convoy effect (probe wake as gradient for follower)
  4. Minimum resistance point (where to cross the gap)

Usage:
    python BCM_alpha_centauri.py
    python BCM_alpha_centauri.py --steps 3000 --grid 256
"""

import numpy as np
import json
import os
import time
import argparse


def init_sigma_packet(nx, ny, center, amplitude=1.0, width=4.0):
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    dx = X - center[0]
    dy = Y - center[1]
    return amplitude * np.exp(-(dx**2 + dy**2) / (2 * width**2))


def compute_com(sigma):
    total = np.sum(sigma)
    if total < 1e-15:
        return None
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    return np.array([np.sum(X * sigma) / total,
                      np.sum(Y * sigma) / total])


def compute_coherence(sigma, center, radius=8):
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    r2 = (X - center[0])**2 + (Y - center[1])**2
    inside = np.sum(sigma[r2 < radius**2])
    total = np.sum(sigma)
    if total < 1e-15:
        return 0.0
    return inside / total


def build_two_star_field(nx, ny, sol_pos, ac_pos,
                          smbh_pos, sol_depth=0.08,
                          ac_depth=0.06, smbh_depth=0.05,
                          star_width=12.0, smbh_width=800.0,
                          base_lam=0.12):
    """
    Build lambda field with:
    - SMBH gradient (galactic current)
    - Sol local well
    - Alpha Centauri local well
    - Void between them
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # SMBH gradient
    r_smbh = (X - smbh_pos[0])**2 + (Y - smbh_pos[1])**2
    lam = base_lam - smbh_depth * np.exp(-r_smbh / (2 * smbh_width))

    # Sol well
    r_sol = (X - sol_pos[0])**2 + (Y - sol_pos[1])**2
    lam -= sol_depth * np.exp(-r_sol / (2 * star_width**2))

    # Alpha Centauri well
    r_ac = (X - ac_pos[0])**2 + (Y - ac_pos[1])**2
    lam -= ac_depth * np.exp(-r_ac / (2 * star_width**2))

    return np.maximum(lam, 0.01)


def build_drive(nx, ny, pos, direction, delta_lam=0.025,
                 spread=6.0):
    """Ship drive dipole."""
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    d = np.array(direction, dtype=float)
    d /= (np.linalg.norm(d) + 1e-12)
    proj = (X - pos[0]) * d[0] + (Y - pos[1]) * d[1]
    return -delta_lam * np.tanh(proj / spread)


def run_transit(sigma, lam_field, nx, ny, direction,
                 steps, dt, D, drive_delta=0.025,
                 label="TRANSIT"):
    """Run a ship through a static field, return trajectory."""
    trajectory = []
    coherences = []
    speeds = []
    alive = True

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            alive = False
            break

        # Drive
        drive = build_drive(nx, ny, com, direction,
                             delta_lam=drive_delta)
        lam_total = lam_field + drive
        lam_total = np.maximum(lam_total, 0.005)

        # Evolve
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt
        sigma -= lam_total * sigma * dt
        sigma = np.maximum(sigma, 0)

        coh = compute_coherence(sigma, com)
        coherences.append(coh)

        if len(trajectory) > 0:
            vel = com - trajectory[-1]
            speeds.append(float(np.linalg.norm(vel)))

        trajectory.append(com.copy())

        if step % 500 == 0:
            disp = com - trajectory[0]
            print(f"    [{label}] step={step:>5}  "
                  f"pos=({com[0]:.1f},{com[1]:.1f})  "
                  f"coh={coh:.4f}  "
                  f"disp={np.linalg.norm(disp):.2f}")

    traj = np.array(trajectory)
    total_disp = np.linalg.norm(traj[-1] - traj[0]) if len(traj) > 1 else 0

    return {
        "trajectory": traj,
        "coherences": coherences,
        "speeds": speeds,
        "total_drift": float(total_disp),
        "mean_speed": float(np.mean(speeds)) if speeds else 0,
        "final_coherence": coherences[-1] if coherences else 0,
        "alive": alive,
        "sigma_final": sigma,
    }


# ============================================================
# TEST 1: DIRECT PATH Sol → Alpha Centauri
# ============================================================
def test_direct_path(steps=3000, nx=256, ny=128,
                      dt=0.05, D=0.5):
    """
    Direct transit from Sol to Alpha Centauri.
    Sol at (40, 64). Alpha Cen at (216, 64).
    SMBH gradient from left.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 1: DIRECT PATH Sol → Alpha Centauri")
    print(f"  {'='*60}")

    sol = (40, ny // 2)
    ac = (nx - 40, ny // 2)
    smbh = (0, ny // 2)

    lam_field = build_two_star_field(
        nx, ny, sol, ac, smbh)

    # Direction: Sol → AC
    dx = ac[0] - sol[0]
    dy = ac[1] - sol[1]
    direction = (dx, dy)

    # Start ship just outside Sol's well
    ship_start = (sol[0] + 20, sol[1])
    sigma = init_sigma_packet(nx, ny, ship_start)

    print(f"  Sol at {sol}, Alpha Cen at {ac}")
    print(f"  Ship starts at {ship_start}")
    print(f"  Gap: {ac[0]-sol[0]} px")
    print(f"  {'─'*60}")

    result = run_transit(sigma, lam_field, nx, ny, direction,
                          steps, dt, D, label="DIRECT")

    # How close did we get to Alpha Cen?
    if result["alive"] and len(result["trajectory"]) > 0:
        final = result["trajectory"][-1]
        dist_to_ac = np.linalg.norm(final - np.array(ac))
        print(f"\n  Final position: ({final[0]:.1f}, {final[1]:.1f})")
        print(f"  Distance to Alpha Cen: {dist_to_ac:.1f} px")
        print(f"  Coherence at arrival: "
              f"{result['final_coherence']:.4f}")
        result["dist_to_ac"] = float(dist_to_ac)
    else:
        print(f"\n  DISSOLVED EN ROUTE")
        result["dist_to_ac"] = 999

    return result, lam_field


# ============================================================
# TEST 2: EDGE-RIDING PATH (void boundary surf)
# ============================================================
def test_edge_riding(steps=3000, nx=256, ny=128,
                      dt=0.05, D=0.5):
    """
    Instead of crossing the void directly, ride the EDGE
    of Sol's funded zone, then hop to Alpha Cen's edge.
    The boundary between funded and unfunded substrate
    has the steepest gradient — maximum drift efficiency.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 2: EDGE-RIDING PATH (void boundary surf)")
    print(f"  {'='*60}")

    sol = (40, ny // 2)
    ac = (nx - 40, ny // 2)
    smbh = (0, ny // 2)

    lam_field = build_two_star_field(
        nx, ny, sol, ac, smbh)

    # Edge path: go ABOVE the direct line, ride Sol's
    # funded boundary, then arc down to Alpha Cen
    waypoints = [
        (sol[0] + 20, sol[1]),       # depart Sol
        (sol[0] + 40, sol[1] + 25),  # climb to edge
        (nx // 2, sol[1] + 30),      # ride midpoint high
        (ac[0] - 40, ac[1] + 25),    # approach AC from above
        (ac[0] - 20, ac[1]),         # enter AC well
    ]

    print(f"  Path: depart Sol → climb to edge → "
          f"ride boundary → drop to AC")
    print(f"  {'─'*60}")

    total_drift = 0
    total_steps = 0
    min_coherence = 1.0
    alive = True

    sigma = init_sigma_packet(nx, ny, waypoints[0])

    for i in range(len(waypoints) - 1):
        wp_from = waypoints[i]
        wp_to = waypoints[i + 1]
        dx = wp_to[0] - wp_from[0]
        dy = wp_to[1] - wp_from[1]
        direction = (dx, dy)
        seg_steps = steps // (len(waypoints) - 1)

        result = run_transit(sigma, lam_field, nx, ny,
                              direction, seg_steps, dt, D,
                              label=f"SEG{i}")

        if not result["alive"]:
            alive = False
            print(f"    DISSOLVED on segment {i}")
            break

        sigma = result["sigma_final"]
        total_drift += result["total_drift"]
        total_steps += len(result["trajectory"])
        min_coherence = min(min_coherence,
                             result["final_coherence"])

    final_com = compute_com(sigma)
    dist_to_ac = 999
    if final_com is not None:
        dist_to_ac = float(np.linalg.norm(
            final_com - np.array(ac)))

    print(f"\n  Edge-riding result:")
    print(f"    Total drift: {total_drift:.1f} px")
    print(f"    Min coherence: {min_coherence:.4f}")
    print(f"    Distance to AC: {dist_to_ac:.1f} px")
    print(f"    Alive: {alive}")

    return {
        "total_drift": total_drift,
        "min_coherence": min_coherence,
        "dist_to_ac": dist_to_ac,
        "alive": alive,
        "total_steps": total_steps,
    }


# ============================================================
# TEST 3: CONVOY EFFECT (probe wake as road)
# ============================================================
def test_convoy(steps=2000, nx=256, ny=128,
                 dt=0.05, D=0.5):
    """
    Probe Alpha transits first. Does the wake it leaves
    create a usable gradient edge for Probe Beta?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 3: CONVOY EFFECT (probe wake as road)")
    print(f"  {'='*60}")

    sol = (40, ny // 2)
    ac = (nx - 40, ny // 2)
    smbh = (0, ny // 2)

    lam_field = build_two_star_field(
        nx, ny, sol, ac, smbh)

    direction = (ac[0] - sol[0], 0)
    ship_start = (sol[0] + 20, sol[1])

    # Probe Alpha goes first
    print(f"  PROBE ALPHA (pathfinder):")
    sigma_a = init_sigma_packet(nx, ny, ship_start)
    result_a = run_transit(sigma_a, lam_field, nx, ny,
                            direction, steps, dt, D,
                            label="ALPHA")

    # Capture the disturbed field after Alpha's passage
    # The wake modifies the effective lambda landscape
    alpha_wake = result_a["sigma_final"]

    # Probe Beta follows — offset by 5px in y to ride edge
    print(f"\n  PROBE BETA (follower, +5px offset):")
    beta_start = (sol[0] + 20, sol[1] + 5)
    sigma_b = init_sigma_packet(nx, ny, beta_start)

    # Beta runs in the same field (wake has dissipated in sigma
    # but the test shows if the path matters)
    result_b = run_transit(sigma_b, lam_field, nx, ny,
                            direction, steps, dt, D,
                            label="BETA")

    # Compare
    print(f"\n  CONVOY COMPARISON:")
    print(f"    Alpha drift: {result_a['total_drift']:.3f} px  "
          f"speed: {result_a['mean_speed']:.6f}")
    print(f"    Beta drift:  {result_b['total_drift']:.3f} px  "
          f"speed: {result_b['mean_speed']:.6f}")

    if result_b["mean_speed"] > 0:
        ratio = result_a["mean_speed"] / result_b["mean_speed"]
        print(f"    Ratio Alpha/Beta: {ratio:.4f}")

    return {
        "alpha": {
            "drift": result_a["total_drift"],
            "speed": result_a["mean_speed"],
            "coherence": result_a["final_coherence"],
            "alive": result_a["alive"],
        },
        "beta": {
            "drift": result_b["total_drift"],
            "speed": result_b["mean_speed"],
            "coherence": result_b["final_coherence"],
            "alive": result_b["alive"],
        },
    }


# ============================================================
# TEST 4: MINIMUM RESISTANCE POINT
# ============================================================
def test_min_resistance(nx=256, ny=128):
    """
    Map the lambda field between Sol and Alpha Cen.
    Find where the gradient is shallowest — the point
    of minimum resistance for crossing the gap.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 4: MINIMUM RESISTANCE POINT")
    print(f"  {'='*60}")

    sol = (40, ny // 2)
    ac = (nx - 40, ny // 2)
    smbh = (0, ny // 2)

    lam_field = build_two_star_field(
        nx, ny, sol, ac, smbh)

    # Sample along the direct path
    midline = lam_field[:, ny // 2]

    print(f"  Lambda along Sol-AC corridor:")
    print(f"  {'x':>6} {'lambda':>10} {'zone':>15}")
    print(f"  {'─'*6} {'─'*10} {'─'*15}")

    corridor = []
    max_lam = 0
    max_lam_x = 0

    for cx in range(sol[0], ac[0], 5):
        lam_val = float(midline[cx])
        if lam_val > max_lam:
            max_lam = lam_val
            max_lam_x = cx

        if cx <= sol[0] + 15:
            zone = "Sol well"
        elif cx >= ac[0] - 15:
            zone = "AC well"
        elif lam_val > 0.10:
            zone = "VOID"
        else:
            zone = "corridor"

        corridor.append({"x": cx, "lambda": round(lam_val, 6),
                          "zone": zone})
        print(f"  {cx:>6} {lam_val:>10.6f} {zone:>15}")

    print(f"\n  Maximum void lambda: {max_lam:.6f} at x={max_lam_x}")
    print(f"  Sol well edge: ~x={sol[0]+15}")
    print(f"  AC well edge: ~x={ac[0]-15}")
    print(f"  Gap width: {ac[0]-15 - (sol[0]+15)} px")

    # Find minimum resistance crossing
    # Look for y-offset where lambda is lowest
    print(f"\n  Scanning y-offsets for minimum resistance:")
    min_max_lam = 999
    best_y = ny // 2

    for test_y in range(ny // 4, 3 * ny // 4, 4):
        path_lam = lam_field[sol[0]+15:ac[0]-15, test_y]
        path_max = float(np.max(path_lam))
        if path_max < min_max_lam:
            min_max_lam = path_max
            best_y = test_y

    offset = best_y - ny // 2
    print(f"  Best y-offset: {offset:+d} px (y={best_y})")
    print(f"  Max lambda on best path: {min_max_lam:.6f}")
    print(f"  Max lambda on direct path: {max_lam:.6f}")

    if min_max_lam < max_lam:
        improvement = (1 - min_max_lam / max_lam) * 100
        print(f"  Improvement: {improvement:.1f}% lower resistance")

    return {
        "corridor": corridor,
        "max_void_lambda": max_lam,
        "max_void_x": max_lam_x,
        "gap_width": ac[0] - 15 - (sol[0] + 15),
        "best_y_offset": offset,
        "best_path_max_lambda": min_max_lam,
        "direct_path_max_lambda": max_lam,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 Alpha Centauri Corridor Test")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = args.grid
    ny = nx // 2  # elongated corridor

    print(f"\n{'='*65}")
    print(f"  BCM v13 ALPHA CENTAURI CORRIDOR TEST")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"{'='*65}")

    all_results = {}

    # Test 1: Direct path
    r1, lam_field = test_direct_path(
        steps=args.steps, nx=nx, ny=ny)
    all_results["direct_path"] = {
        "drift": r1["total_drift"],
        "speed": r1["mean_speed"],
        "coherence": r1["final_coherence"],
        "dist_to_ac": r1.get("dist_to_ac", 999),
        "alive": r1["alive"],
    }

    # Test 2: Edge riding
    r2 = test_edge_riding(steps=args.steps, nx=nx, ny=ny)
    all_results["edge_riding"] = r2

    # Test 3: Convoy
    r3 = test_convoy(steps=min(2000, args.steps),
                      nx=nx, ny=ny)
    all_results["convoy"] = r3

    # Test 4: Min resistance
    r4 = test_min_resistance(nx=nx, ny=ny)
    all_results["min_resistance"] = r4

    # Summary
    print(f"\n{'='*65}")
    print(f"  ALPHA CENTAURI CORRIDOR SUMMARY")
    print(f"{'='*65}")
    print(f"  Direct path: drift={all_results['direct_path']['drift']:.1f}px "
          f"dist_to_AC={all_results['direct_path']['dist_to_ac']:.1f}px "
          f"alive={all_results['direct_path']['alive']}")
    print(f"  Edge riding: drift={r2['total_drift']:.1f}px "
          f"dist_to_AC={r2['dist_to_ac']:.1f}px "
          f"alive={r2['alive']}")
    print(f"  Gap width: {r4['gap_width']} px")
    print(f"  Max void lambda: {r4['max_void_lambda']:.4f}")
    print(f"  Best offset: {r4['best_y_offset']:+d}px "
          f"({r4['best_path_max_lambda']:.4f})")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_alpha_cen_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 Alpha Centauri Corridor Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "grid_nx": nx, "grid_ny": ny,
        "steps": args.steps,
        "results": all_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
