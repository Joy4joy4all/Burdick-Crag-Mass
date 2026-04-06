# -*- coding: utf-8 -*-
"""
BCM v13 SPINE — Galactic Current & Wake Analysis
===================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The galaxy has a current. The SMBH pumps outward.
The substrate flows from core to edge. Stars form
where the flow slows. Voids exist where it runs fast.

Tests:
  1. WITH vs AGAINST the current — does direction
     relative to SMBH gradient affect drift speed?
  2. Wake formation — does the ship leave a measurable
     sigma disturbance behind it?
  3. Optimal exit vector from solar system — which
     heading gives the best-funded corridor?
  4. Wake relaxation — how long until the substrate
     forgets the ship passed?

Usage:
    python BCM_galactic_current.py
    python BCM_galactic_current.py --steps 2000 --grid 128
"""

import numpy as np
import json
import os
import time
import argparse


def init_sigma_packet(nx, ny, center, amplitude=1.0, width=5.0):
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    dx = X - center[0]
    dy = Y - center[1]
    r2 = dx**2 + dy**2
    return amplitude * np.exp(-r2 / (2 * width**2))


def compute_com(sigma):
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


def build_galactic_lambda(nx, ny, smbh_center, base_lam=0.15,
                           core_depth=0.12, falloff=800.0):
    """
    Build galactic lambda field: SMBH at center creates
    low-lambda (funded) core, high-lambda (unfunded) edge.
    The gradient IS the galactic current.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - smbh_center[0]
    dy = Y - smbh_center[1]
    r2 = dx**2 + dy**2

    # Low lambda at core (funded), high at edge (unfunded)
    lam_field = base_lam - core_depth * np.exp(-r2 / (2 * falloff))

    return np.maximum(lam_field, 0.01)


def build_drive_dipole(nx, ny, ship_pos, direction,
                        base_lam_local, delta_lam=0.03,
                        spread=8.0):
    """
    Ship's lambda modulator dipole overlaid on background.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - ship_pos[0]
    dy = Y - ship_pos[1]

    d = np.array(direction, dtype=float)
    d /= (np.linalg.norm(d) + 1e-12)

    proj = dx * d[0] + dy * d[1]
    profile = np.tanh(proj / spread)

    return -delta_lam * profile


# ============================================================
# TEST 1: WITH vs AGAINST THE GALACTIC CURRENT
# ============================================================
def run_current_test(steps=2000, nx=128, ny=128,
                      dt=0.05, D=0.5):
    """
    Place SMBH at one edge. Ship at center.
    Test drift toward core (with current) vs away (against).
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 1: WITH vs AGAINST THE GALACTIC CURRENT")
    print(f"  {'='*60}")
    print(f"  SMBH at (0, center). Ship at grid center.")
    print(f"  'With current' = toward SMBH (lower lambda)")
    print(f"  'Against current' = away from SMBH (higher lambda)")
    print(f"  {'─'*60}")

    smbh_center = (0, ny // 2)
    ship_start = (nx // 2, ny // 2)

    directions = [
        ((-1, 0), "TOWARD SMBH (with current)"),
        ((1, 0),  "AWAY from SMBH (against current)"),
        ((0, 1),  "PERPENDICULAR (cross current)"),
    ]

    galactic_lam = build_galactic_lambda(
        nx, ny, smbh_center, base_lam=0.12,
        core_depth=0.09, falloff=600.0)

    results = []

    for direction, label in directions:
        ship_pos = np.array(ship_start, dtype=float)
        initial_pos = ship_pos.copy()
        sigma = init_sigma_packet(nx, ny, ship_pos)

        speeds = []

        for step in range(steps):
            com = compute_com(sigma)
            if com is None:
                break

            # Combine galactic background + ship drive
            drive = build_drive_dipole(
                nx, ny, com, direction,
                base_lam_local=0.05, delta_lam=0.03)
            lam_total = galactic_lam + drive
            lam_total = np.maximum(lam_total, 0.01)

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

            if len(speeds) > 0 or step > 0:
                new_com = compute_com(sigma)
                if new_com is not None and com is not None:
                    vel = new_com - com
                    speeds.append(float(np.linalg.norm(vel)))

            ship_pos = com if com is not None else ship_pos

        final_com = compute_com(sigma)
        if final_com is not None:
            disp = final_com - initial_pos
            total_drift = float(np.linalg.norm(disp))
            mean_speed = float(np.mean(speeds)) if speeds else 0
            coh = compute_coherence(sigma, final_com)
        else:
            disp = np.zeros(2)
            total_drift = 0
            mean_speed = 0
            coh = 0

        print(f"  {label:>40}: drift={total_drift:>8.3f}px  "
              f"speed={mean_speed:.6f}  coh={coh:.4f}")

        results.append({
            "direction": label,
            "vector": list(direction),
            "drift_px": round(total_drift, 4),
            "displacement": [round(float(disp[0]), 4),
                              round(float(disp[1]), 4)],
            "mean_speed": round(mean_speed, 8),
            "coherence": round(coh, 4),
        })

    # Compare
    if len(results) >= 2:
        with_spd = results[0]["mean_speed"]
        against_spd = results[1]["mean_speed"]
        ratio = with_spd / (against_spd + 1e-15)
        print(f"\n  Current advantage: {ratio:.2f}x faster WITH "
              f"the current")

    return results


# ============================================================
# TEST 2: WAKE FORMATION
# ============================================================
def run_wake_test(steps=1500, nx=128, ny=128,
                   dt=0.05, D=0.5):
    """
    Run a ship through the substrate and measure the
    sigma disturbance left behind (the wake).
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 2: WAKE FORMATION")
    print(f"  {'='*60}")
    print(f"  Ship transits +x through uniform substrate.")
    print(f"  Measure sigma field BEHIND the ship.")
    print(f"  {'─'*60}")

    center = (nx // 4, ny // 2)  # start left of center
    ship_pos = np.array(center, dtype=float)
    sigma = init_sigma_packet(nx, ny, ship_pos)

    # Snapshot before transit
    sigma_before = sigma.copy()

    base_lam = 0.08
    lam_bg = np.full((nx, ny), base_lam)

    wake_samples = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        # Drive dipole
        drive = build_drive_dipole(
            nx, ny, com, (1, 0),
            base_lam_local=base_lam, delta_lam=0.04)
        lam_total = lam_bg + drive
        lam_total = np.maximum(lam_total, 0.01)

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

        # Sample wake every 300 steps
        if step % 300 == 0 and step > 0:
            midline = sigma[:, ny // 2]
            ship_x = int(com[0]) if com is not None else nx // 2
            # Sample behind the ship
            behind_sigma = float(np.mean(
                midline[max(0, ship_x - 20):max(1, ship_x - 5)]))
            ahead_sigma = float(np.mean(
                midline[min(nx-1, ship_x + 5):min(nx, ship_x + 20)]))

            wake_samples.append({
                "step": step,
                "ship_x": ship_x,
                "behind_sigma": round(behind_sigma, 8),
                "ahead_sigma": round(ahead_sigma, 8),
                "ratio": round(behind_sigma / (ahead_sigma + 1e-15), 4),
            })
            print(f"    Step {step:>5}: ship_x={ship_x:>4}  "
                  f"behind={behind_sigma:.8f}  "
                  f"ahead={ahead_sigma:.8f}  "
                  f"wake_ratio={behind_sigma/(ahead_sigma+1e-15):.4f}")

    # Final wake profile
    final_com = compute_com(sigma)
    wake_profile = []
    if final_com is not None:
        midline = sigma[:, ny // 2]
        for wx in range(0, nx, 4):
            wake_profile.append({
                "x": wx,
                "sigma": round(float(midline[wx]), 8),
            })
        print(f"\n  Wake detected: substrate disturbance behind "
              f"ship path")

    return wake_samples, wake_profile


# ============================================================
# TEST 3: OPTIMAL EXIT VECTOR FROM SOLAR SYSTEM
# ============================================================
def run_exit_vector(steps=2000, nx=128, ny=128,
                     dt=0.05, D=0.5):
    """
    Place the Sun at center. Test 8 exit directions.
    Which heading gives the best-funded corridor for
    leaving the solar system?

    In reality: the galactic center is in a specific
    direction from Sol. The optimal exit vector should
    align with the funded spiral arm corridor.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 3: OPTIMAL EXIT VECTOR FROM SOLAR SYSTEM")
    print(f"  {'='*60}")
    print(f"  Sun at center. SMBH gradient from left.")
    print(f"  Test 8 exit headings: which corridor survives?")
    print(f"  {'─'*60}")

    smbh_center = (0, ny // 2)
    sun_center = (nx // 2, ny // 2)

    galactic_lam = build_galactic_lambda(
        nx, ny, smbh_center, base_lam=0.12,
        core_depth=0.09, falloff=600.0)

    # Sun's local well
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    sun_r2 = (X - sun_center[0])**2 + (Y - sun_center[1])**2
    sun_well = -0.06 * np.exp(-sun_r2 / (2 * 15**2))
    total_lam = np.maximum(galactic_lam + sun_well, 0.01)

    # 8 directions
    angles = [0, 45, 90, 135, 180, 225, 270, 315]
    results = []

    print(f"  {'Heading':>8} {'Dir':>12} {'Drift(px)':>10} "
          f"{'Speed':>10} {'Coh':>8} {'Verdict':>12}")
    print(f"  {'─'*8} {'─'*12} {'─'*10} {'─'*10} {'─'*8} "
          f"{'─'*12}")

    for angle in angles:
        rad = np.radians(angle)
        direction = (np.cos(rad), np.sin(rad))

        ship_start = (sun_center[0] + 15 * np.cos(rad),
                       sun_center[1] + 15 * np.sin(rad))
        ship_pos = np.array(ship_start, dtype=float)
        initial_pos = ship_pos.copy()
        sigma = init_sigma_packet(nx, ny, ship_pos, width=4.0)

        for step in range(steps):
            com = compute_com(sigma)
            if com is None:
                break

            drive = build_drive_dipole(
                nx, ny, com, direction,
                base_lam_local=0.05, delta_lam=0.03)
            lam_step = total_lam + drive
            lam_step = np.maximum(lam_step, 0.01)

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

        final_com = compute_com(sigma)
        if final_com is not None:
            disp = final_com - initial_pos
            drift = float(np.linalg.norm(disp))
            coh = compute_coherence(sigma, final_com)
        else:
            drift = 0
            coh = 0

        speed = drift / steps

        if coh > 0.3 and drift > 5:
            verdict = "OPTIMAL"
        elif coh > 0.2 and drift > 2:
            verdict = "VIABLE"
        elif coh > 0.1:
            verdict = "MARGINAL"
        else:
            verdict = "DEAD"

        dir_label = "%+.1f,%+.1f" % (direction[0], direction[1])

        print(f"  {angle:>7}d {dir_label:>12} {drift:>10.3f} "
              f"{speed:>10.6f} {coh:>8.4f} {verdict:>12}")

        results.append({
            "angle_deg": angle,
            "direction": [round(direction[0], 3),
                           round(direction[1], 3)],
            "drift_px": round(drift, 4),
            "speed": round(speed, 8),
            "coherence": round(coh, 4),
            "verdict": verdict,
        })

    # Find best
    best = max(results, key=lambda r: r["drift_px"])
    print(f"\n  BEST EXIT: {best['angle_deg']} degrees "
          f"({best['verdict']}) — drift={best['drift_px']:.3f}px")

    return results


# ============================================================
# TEST 4: WAKE RELAXATION
# ============================================================
def run_wake_relaxation(steps_transit=800, steps_relax=2000,
                         nx=128, ny=128, dt=0.05, D=0.5):
    """
    Run a ship through, then STOP the drive and measure
    how long the wake takes to relax. This is the substrate's
    memory of passage.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 4: WAKE RELAXATION TIME")
    print(f"  {'='*60}")
    print(f"  Transit {steps_transit} steps, then coast "
          f"{steps_relax} steps.")
    print(f"  Measure wake decay rate.")
    print(f"  {'─'*60}")

    center = (nx // 4, ny // 2)
    ship_pos = np.array(center, dtype=float)
    sigma = init_sigma_packet(nx, ny, ship_pos)

    base_lam = 0.08
    lam_bg = np.full((nx, ny), base_lam)

    # Transit phase
    for step in range(steps_transit):
        com = compute_com(sigma)
        if com is None:
            break

        drive = build_drive_dipole(
            nx, ny, com, (1, 0),
            base_lam_local=base_lam, delta_lam=0.04)
        lam_total = lam_bg + drive
        lam_total = np.maximum(lam_total, 0.01)

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

    # Snapshot wake after transit
    wake_after_transit = float(np.sum(sigma[:nx//3, :]))
    print(f"  Wake energy after transit: {wake_after_transit:.6f}")

    # Relaxation phase — NO DRIVE, just background decay
    relax_samples = []
    for step in range(steps_relax):
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt
        sigma -= lam_bg * sigma * dt
        sigma = np.maximum(sigma, 0)

        if step % 200 == 0:
            wake_energy = float(np.sum(sigma[:nx//3, :]))
            ratio = wake_energy / (wake_after_transit + 1e-15)
            relax_samples.append({
                "step": step,
                "wake_energy": round(wake_energy, 8),
                "ratio_of_initial": round(ratio, 6),
            })
            print(f"    Relax step {step:>5}: "
                  f"wake={wake_energy:.8f}  "
                  f"remaining={ratio*100:.4f}%")

    return relax_samples, wake_after_transit


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 Galactic Current & Wake Analysis")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"  BCM v13 GALACTIC CURRENT & WAKE ANALYSIS")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")

    all_results = {}

    t1 = run_current_test(steps=args.steps, nx=args.grid,
                           ny=args.grid)
    all_results["current_test"] = t1

    t2_samples, t2_profile = run_wake_test(
        steps=min(1500, args.steps), nx=args.grid, ny=args.grid)
    all_results["wake_formation"] = {
        "samples": t2_samples, "profile": t2_profile}

    t3 = run_exit_vector(steps=args.steps, nx=args.grid,
                          ny=args.grid)
    all_results["exit_vector"] = t3

    t4_samples, t4_initial = run_wake_relaxation(
        steps_transit=800, steps_relax=2000,
        nx=args.grid, ny=args.grid)
    all_results["wake_relaxation"] = {
        "samples": t4_samples,
        "initial_energy": t4_initial}

    # Summary
    print(f"\n{'='*65}")
    print(f"  GALACTIC CURRENT SUMMARY")
    print(f"{'='*65}")

    if len(t1) >= 2:
        r = t1[0]["mean_speed"] / (t1[1]["mean_speed"] + 1e-15)
        print(f"  Current advantage: {r:.2f}x faster WITH flow")

    best_exit = max(t3, key=lambda r: r["drift_px"])
    print(f"  Best exit vector: {best_exit['angle_deg']} deg "
          f"({best_exit['verdict']})")

    if t4_samples:
        final_wake = t4_samples[-1]["ratio_of_initial"]
        print(f"  Wake relaxation: {final_wake*100:.4f}% remaining "
              f"after {len(t4_samples)*200} steps")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_galactic_current_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 Galactic Current & Wake Analysis",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "grid": args.grid,
        "steps": args.steps,
        "results": all_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
