# -*- coding: utf-8 -*-
"""
BCM v13 SPINE — Sirius Downstream Corridor
=============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Sirius lags behind us in the galactic current. It is
DOWNSTREAM. Alpha Centauri may be cross-current or
upstream. This test compares:

  1. Sol → Alpha Centauri (4.37 ly, against/cross current)
  2. Sol → Sirius (8.6 ly, WITH current)

The nearest star is not the easiest star. The easiest
star is the one the river carries you to.

Usage:
    python BCM_sirius_corridor.py
    python BCM_sirius_corridor.py --steps 3000 --grid 256
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


def build_field(nx, ny, smbh_pos, stars, base_lam=0.12,
                 smbh_depth=0.05, smbh_width=800.0,
                 star_depth=0.08, star_width=12.0):
    """
    Build lambda field with SMBH gradient and multiple stars.
    stars = list of (x, y, depth) tuples.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # SMBH gradient
    r_smbh = (X - smbh_pos[0])**2 + (Y - smbh_pos[1])**2
    lam = base_lam - smbh_depth * np.exp(-r_smbh / (2 * smbh_width))

    # Star wells
    for sx, sy, depth in stars:
        r_star = (X - sx)**2 + (Y - sy)**2
        lam -= depth * np.exp(-r_star / (2 * star_width**2))

    return np.maximum(lam, 0.01)


def build_drive(nx, ny, pos, direction, delta_lam=0.025,
                 spread=6.0):
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    d = np.array(direction, dtype=float)
    d /= (np.linalg.norm(d) + 1e-12)
    proj = (X - pos[0]) * d[0] + (Y - pos[1]) * d[1]
    return -delta_lam * np.tanh(proj / spread)


def run_corridor(lam_field, nx, ny, start, target,
                  steps, dt, D, drive_delta=0.025,
                  label="TRANSIT"):
    """Run a ship from start toward target. Return results."""
    direction = (target[0] - start[0], target[1] - start[1])
    ship_pos = np.array(start, dtype=float)
    initial_pos = ship_pos.copy()
    sigma = init_sigma_packet(nx, ny, ship_pos)

    trajectory = []
    speeds = []
    coherences = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        drive = build_drive(nx, ny, com, direction,
                             delta_lam=drive_delta)
        lam_total = np.maximum(lam_field + drive, 0.005)

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
            disp = com - initial_pos
            print(f"    [{label}] step={step:>5}  "
                  f"pos=({com[0]:.1f},{com[1]:.1f})  "
                  f"coh={coh:.4f}  "
                  f"drift={np.linalg.norm(disp):.2f}")

    traj = np.array(trajectory)
    if len(traj) > 1:
        disp = traj[-1] - traj[0]
        total_drift = float(np.linalg.norm(disp))
        dist_to_target = float(np.linalg.norm(
            traj[-1] - np.array(target)))
    else:
        total_drift = 0
        dist_to_target = 999

    return {
        "label": label,
        "start": list(start),
        "target": list(target),
        "total_drift": round(total_drift, 4),
        "dist_to_target": round(dist_to_target, 4),
        "mean_speed": round(float(np.mean(speeds)), 8) if speeds else 0,
        "final_coherence": round(coherences[-1], 4) if coherences else 0,
        "min_coherence": round(min(coherences), 4) if coherences else 0,
        "alive": len(traj) >= steps,
        "steps_completed": len(traj),
        "gap_crossed_pct": round(
            total_drift / max(1, np.linalg.norm(
                np.array(target) - np.array(start))) * 100, 1),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 Sirius Downstream Corridor")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = args.grid
    ny = nx // 2

    print(f"\n{'='*65}")
    print(f"  BCM v13 SIRIUS DOWNSTREAM CORRIDOR")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"{'='*65}")

    # Layout:
    # SMBH at far left (galactic center)
    # Sol at center
    # Alpha Centauri: upstream/cross (toward SMBH, offset)
    # Sirius: downstream (away from SMBH, with current)
    smbh = (0, ny // 2)
    sol = (nx // 2, ny // 2)

    # Alpha Cen: 4.37 ly ≈ 50 px, slightly upstream
    ac = (sol[0] - 35, sol[1] + 35)  # upstream + offset

    # Sirius: 8.6 ly ≈ 100 px, downstream
    sirius = (sol[0] + 80, sol[1] - 20)  # downstream + slight offset

    stars = [
        (sol[0], sol[1], 0.08),      # Sol
        (ac[0], ac[1], 0.06),         # Alpha Centauri
        (sirius[0], sirius[1], 0.09), # Sirius (brighter = deeper well)
    ]

    lam_field = build_field(nx, ny, smbh, stars)

    # Distances
    dist_ac = np.linalg.norm(np.array(ac) - np.array(sol))
    dist_sir = np.linalg.norm(np.array(sirius) - np.array(sol))

    print(f"\n  STELLAR POSITIONS (galactic frame):")
    print(f"    SMBH:          ({smbh[0]}, {smbh[1]})")
    print(f"    Sol:           ({sol[0]}, {sol[1]})")
    print(f"    Alpha Cen:     ({ac[0]}, {ac[1]}) — "
          f"dist={dist_ac:.0f}px — UPSTREAM")
    print(f"    Sirius:        ({sirius[0]}, {sirius[1]}) — "
          f"dist={dist_sir:.0f}px — DOWNSTREAM")

    # Lambda at midpoint of each corridor
    mid_ac = ((sol[0] + ac[0]) // 2, (sol[1] + ac[1]) // 2)
    mid_sir = ((sol[0] + sirius[0]) // 2,
               (sol[1] + sirius[1]) // 2)

    lam_mid_ac = float(lam_field[mid_ac[0], mid_ac[1]])
    lam_mid_sir = float(lam_field[mid_sir[0], mid_sir[1]])

    print(f"\n  CORRIDOR MIDPOINT LAMBDA:")
    print(f"    Sol→AC midpoint:     lambda = {lam_mid_ac:.6f}")
    print(f"    Sol→Sirius midpoint: lambda = {lam_mid_sir:.6f}")
    print(f"    {'Sol→AC is more funded' if lam_mid_ac < lam_mid_sir else 'Sol→Sirius is more funded'}")

    # Ship starts just outside Sol's well
    results = {}

    # Transit 1: Sol → Alpha Centauri (upstream)
    print(f"\n  {'='*60}")
    print(f"  TRANSIT 1: Sol → Alpha Centauri (UPSTREAM)")
    print(f"  Distance: {dist_ac:.0f} px | Direction: toward SMBH")
    print(f"  {'─'*60}")
    ship_start_ac = (sol[0] - 15, sol[1] + 15)
    r1 = run_corridor(lam_field, nx, ny, ship_start_ac, ac,
                       args.steps, 0.05, 0.5, label="→AC")
    results["sol_to_ac"] = r1

    # Transit 2: Sol → Sirius (downstream)
    print(f"\n  {'='*60}")
    print(f"  TRANSIT 2: Sol → Sirius (DOWNSTREAM)")
    print(f"  Distance: {dist_sir:.0f} px | Direction: with current")
    print(f"  {'─'*60}")
    ship_start_sir = (sol[0] + 15, sol[1] - 5)
    r2 = run_corridor(lam_field, nx, ny, ship_start_sir, sirius,
                       args.steps, 0.05, 0.5, label="→SIR")
    results["sol_to_sirius"] = r2

    # Comparison
    print(f"\n  {'='*65}")
    print(f"  CORRIDOR COMPARISON")
    print(f"  {'='*65}")
    print(f"  {'':>20} {'Alpha Cen':>14} {'Sirius':>14}")
    print(f"  {'─'*20} {'─'*14} {'─'*14}")
    print(f"  {'Distance (px)':>20} {dist_ac:>14.0f} {dist_sir:>14.0f}")
    print(f"  {'Direction':>20} {'UPSTREAM':>14} {'DOWNSTREAM':>14}")
    print(f"  {'Mid lambda':>20} {lam_mid_ac:>14.4f} {lam_mid_sir:>14.4f}")
    print(f"  {'Drift (px)':>20} {r1['total_drift']:>14.2f} {r2['total_drift']:>14.2f}")
    print(f"  {'Mean speed':>20} {r1['mean_speed']:>14.6f} {r2['mean_speed']:>14.6f}")
    print(f"  {'Gap crossed':>20} {r1['gap_crossed_pct']:>13.1f}% {r2['gap_crossed_pct']:>13.1f}%")
    print(f"  {'Final coherence':>20} {r1['final_coherence']:>14.4f} {r2['final_coherence']:>14.4f}")
    print(f"  {'Alive':>20} {'YES' if r1['alive'] else 'NO':>14} {'YES' if r2['alive'] else 'NO':>14}")

    # Verdict
    print(f"\n  {'='*65}")
    if r2['mean_speed'] > r1['mean_speed']:
        ratio = r2['mean_speed'] / (r1['mean_speed'] + 1e-15)
        print(f"  VERDICT: SIRIUS IS FASTER ({ratio:.2f}x)")
        print(f"  Downstream advantage overcomes 2x distance.")
        print(f"  The nearest star is NOT the easiest star.")
        print(f"  The easiest star is the one the current")
        print(f"  carries you to.")
    elif r1['mean_speed'] > r2['mean_speed']:
        ratio = r1['mean_speed'] / (r2['mean_speed'] + 1e-15)
        print(f"  VERDICT: ALPHA CEN IS FASTER ({ratio:.2f}x)")
        print(f"  Proximity advantage overcomes current.")
    else:
        print(f"  VERDICT: EQUIVALENT — distance and current cancel")
    print(f"  {'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_sirius_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 Sirius Downstream Corridor",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "grid_nx": nx, "grid_ny": ny,
        "steps": args.steps,
        "positions": {
            "smbh": list(smbh), "sol": list(sol),
            "alpha_cen": list(ac), "sirius": list(sirius),
        },
        "distances": {
            "sol_ac_px": round(dist_ac, 2),
            "sol_sirius_px": round(dist_sir, 2),
        },
        "midpoint_lambda": {
            "ac": lam_mid_ac, "sirius": lam_mid_sir,
        },
        "results": results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
