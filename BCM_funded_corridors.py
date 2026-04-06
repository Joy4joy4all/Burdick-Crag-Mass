# -*- coding: utf-8 -*-
"""
BCM v13 — Self-Funded Interstellar Corridor Comparison
========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The passive packet failed the Sirius corridor (6%).
The self-funded ship survives any void.
Now: does downstream Sirius beat upstream Alpha Cen
when the ship carries its own pump?

Usage:
    python BCM_funded_corridors.py
    python BCM_funded_corridors.py --steps 3000 --grid 256
"""

import numpy as np
import json
import os
import time
import argparse


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
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    r_smbh = (X - smbh_pos[0])**2 + (Y - smbh_pos[1])**2
    lam = base_lam - smbh_depth * np.exp(-r_smbh / (2 * smbh_width))
    for sx, sy, depth in stars:
        r = (X - sx)**2 + (Y - sy)**2
        lam -= depth * np.exp(-r / (2 * star_width**2))
    return np.maximum(lam, 0.01)


def run_funded_corridor(lam_field, nx, ny, start, target,
                         steps, dt, D, pump_strength=0.5,
                         drive_delta=0.025, label="TRANSIT"):
    """Self-funded ship with continuous pump + drive."""
    direction = (target[0] - start[0], target[1] - start[1])
    ship_pos = np.array(start, dtype=float)
    initial_pos = ship_pos.copy()

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    r2_init = (X - start[0])**2 + (Y - start[1])**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))

    d = np.array(direction, dtype=float)
    d /= (np.linalg.norm(d) + 1e-12)

    trajectory = []
    speeds = []
    coherences = []
    peaks = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            print(f"    [{label}] DISSOLVED step {step}")
            break

        # Self-funding pump at ship location
        r2_ship = (X - com[0])**2 + (Y - com[1])**2
        pump = pump_strength * np.exp(-r2_ship / (2 * 4.0**2))
        sigma += pump * dt

        # Drive dipole
        proj = (X - com[0]) * d[0] + (Y - com[1]) * d[1]
        drive = -drive_delta * np.tanh(proj / 6.0)
        lam_step = np.maximum(lam_field + drive, 0.005)

        # Evolve
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt
        sigma -= lam_step * sigma * dt
        sigma = np.maximum(sigma, 0)

        coh = compute_coherence(sigma, com)
        peak = float(np.max(sigma))
        coherences.append(coh)
        peaks.append(peak)

        if len(trajectory) > 0:
            vel = com - trajectory[-1]
            speeds.append(float(np.linalg.norm(vel)))

        trajectory.append(com.copy())

        if step % 500 == 0:
            disp = com - initial_pos
            print(f"    [{label}] step={step:>5}  "
                  f"pos=({com[0]:.1f},{com[1]:.1f})  "
                  f"peak={peak:.3f}  coh={coh:.4f}  "
                  f"drift={np.linalg.norm(disp):.2f}")

    traj = np.array(trajectory) if trajectory else np.zeros((1, 2))
    disp = traj[-1] - traj[0] if len(traj) > 1 else np.zeros(2)
    total_drift = float(np.linalg.norm(disp))
    dist_to_target = float(np.linalg.norm(
        traj[-1] - np.array(target))) if len(traj) > 0 else 999
    gap_total = float(np.linalg.norm(
        np.array(target) - np.array(start)))

    return {
        "label": label,
        "pump": pump_strength,
        "total_drift": round(total_drift, 4),
        "dist_to_target": round(dist_to_target, 4),
        "gap_crossed_pct": round(total_drift / max(1, gap_total) * 100, 1),
        "mean_speed": round(float(np.mean(speeds)), 8) if speeds else 0,
        "peak_end": round(peaks[-1], 4) if peaks else 0,
        "coherence_end": round(coherences[-1], 4) if coherences else 0,
        "min_coherence": round(min(coherences), 4) if coherences else 0,
        "survived": len(trajectory) >= steps,
        "steps": len(trajectory),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 Funded Corridor Comparison")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    parser.add_argument("--pump", type=float, default=0.5)
    args = parser.parse_args()

    nx = args.grid
    ny = nx // 2

    print(f"\n{'='*65}")
    print(f"  BCM v13 SELF-FUNDED CORRIDOR COMPARISON")
    print(f"  Passive failed. Funded ship carries its own pump.")
    print(f"  Does downstream Sirius beat upstream Alpha Cen?")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}  Pump: {args.pump}")
    print(f"{'='*65}")

    smbh = (0, ny // 2)
    sol = (nx // 2, ny // 2)
    ac = (sol[0] - 35, sol[1] + 35)
    sirius = (sol[0] + 80, sol[1] - 20)

    stars = [
        (sol[0], sol[1], 0.08),
        (ac[0], ac[1], 0.06),
        (sirius[0], sirius[1], 0.09),
    ]

    lam_field = build_field(nx, ny, smbh, stars)

    dist_ac = np.linalg.norm(np.array(ac) - np.array(sol))
    dist_sir = np.linalg.norm(np.array(sirius) - np.array(sol))

    print(f"\n  Sol: {sol}  AC: {ac} ({dist_ac:.0f}px upstream)")
    print(f"  Sirius: {sirius} ({dist_sir:.0f}px downstream)")

    # Run both corridors with self-funded ship
    print(f"\n  {'='*60}")
    print(f"  Sol → Alpha Centauri (UPSTREAM, self-funded)")
    print(f"  {'─'*60}")
    start_ac = (sol[0] - 15, sol[1] + 15)
    r_ac = run_funded_corridor(lam_field, nx, ny, start_ac, ac,
                                args.steps, 0.05, 0.5,
                                pump_strength=args.pump,
                                label="AC-FUNDED")

    print(f"\n  {'='*60}")
    print(f"  Sol → Sirius (DOWNSTREAM, self-funded)")
    print(f"  {'─'*60}")
    start_sir = (sol[0] + 15, sol[1] - 5)
    r_sir = run_funded_corridor(lam_field, nx, ny, start_sir, sirius,
                                 args.steps, 0.05, 0.5,
                                 pump_strength=args.pump,
                                 label="SIR-FUNDED")

    # Comparison
    print(f"\n  {'='*65}")
    print(f"  FUNDED CORRIDOR COMPARISON")
    print(f"  {'='*65}")
    print(f"  {'':>22} {'Alpha Cen':>14} {'Sirius':>14}")
    print(f"  {'─'*22} {'─'*14} {'─'*14}")
    print(f"  {'Distance (px)':>22} {dist_ac:>14.0f} {dist_sir:>14.0f}")
    print(f"  {'Direction':>22} {'UPSTREAM':>14} {'DOWNSTREAM':>14}")
    print(f"  {'Drift (px)':>22} {r_ac['total_drift']:>14.2f} {r_sir['total_drift']:>14.2f}")
    print(f"  {'Gap crossed':>22} {r_ac['gap_crossed_pct']:>13.1f}% {r_sir['gap_crossed_pct']:>13.1f}%")
    print(f"  {'Mean speed':>22} {r_ac['mean_speed']:>14.6f} {r_sir['mean_speed']:>14.6f}")
    print(f"  {'Peak sigma':>22} {r_ac['peak_end']:>14.4f} {r_sir['peak_end']:>14.4f}")
    print(f"  {'Coherence':>22} {r_ac['coherence_end']:>14.4f} {r_sir['coherence_end']:>14.4f}")
    print(f"  {'Dist to target':>22} {r_ac['dist_to_target']:>14.2f} {r_sir['dist_to_target']:>14.2f}")
    print(f"  {'Survived':>22} {'YES' if r_ac['survived'] else 'NO':>14} {'YES' if r_sir['survived'] else 'NO':>14}")

    # Velocity comparison
    if r_ac['mean_speed'] > 0 and r_sir['mean_speed'] > 0:
        ratio = r_sir['mean_speed'] / r_ac['mean_speed']
        print(f"\n  Speed ratio Sirius/AC: {ratio:.4f}")

    # Verdict
    print(f"\n  {'='*65}")
    if r_sir['mean_speed'] > r_ac['mean_speed']:
        print(f"  VERDICT: SIRIUS IS FASTER (self-funded)")
        print(f"  Downstream + self-funding overcomes distance.")
        print(f"  The current carries the funded ship.")
    elif r_ac['mean_speed'] > r_sir['mean_speed']:
        ratio = r_ac['mean_speed'] / r_sir['mean_speed']
        print(f"  VERDICT: ALPHA CEN IS FASTER ({ratio:.2f}x)")
        if r_ac['gap_crossed_pct'] > 50:
            print(f"  AND {r_ac['gap_crossed_pct']:.0f}% of the way there.")
    else:
        print(f"  VERDICT: EQUIVALENT")

    if r_ac['survived'] and r_sir['survived']:
        print(f"  BOTH SURVIVED — self-funding works for either route.")
    print(f"  {'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_funded_corridors_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 Self-Funded Corridor Comparison",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "grid_nx": nx, "grid_ny": ny,
        "steps": args.steps,
        "pump": args.pump,
        "results": {
            "alpha_centauri": r_ac,
            "sirius": r_sir,
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
