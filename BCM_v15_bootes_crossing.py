# -*- coding: utf-8 -*-
"""
BCM v15 — Bootes Void Maximum Feasibility Transit
====================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The Bootes Void is 330 million light-years across.
It contains approximately 60 known galaxies where
~2,000 would be expected. Those 60 are the survivors.
Everything else died.

This test runs a ship from our helion (Sun) across
the entire void to a target galaxy on the far side.
Sixty dead galaxies of random size and memory depth
are scattered through the transit corridor. Random
spacing, random substrate spread, random death scale.

The ship runs the full phase-cycling governor with
core-drop. The question:

  WHAT DOES THE SHIP LOOK LIKE WHEN IT EXITS?

  - Is it still a ship?
  - How much mass did it accumulate?
  - Did the governor keep it alive?
  - Did coherence survive?
  - What is the contrail behind it?

This is maximum feasibility. The What If scenario.
A reproductive journey. Generations on board.

The grid is scaled: 512 px wide = 330 Mly.
Each pixel = ~645,000 light-years.
Ship starts at px 10 (Sun). Target at px 502.

Usage:
    python BCM_v15_bootes_crossing.py
    python BCM_v15_bootes_crossing.py --steps 8000 --grid-x 512
"""

import numpy as np
import json
import os
import time
import argparse


def compute_com(field):
    total = np.sum(field)
    if total < 1e-15:
        return None
    nx, ny = field.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    return np.array([np.sum(X * field) / total,
                     np.sum(Y * field) / total])


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


def measure_ship_envelope(sigma, com, radius=12):
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    r2 = (X - com[0])**2 + (Y - com[1])**2
    return float(np.sum(sigma[r2 < radius**2]))


def build_bootes_void(nx, ny, void_lambda, n_graves, seed=42):
    """
    Build the Bootes Void transit corridor.

    60 dead galaxies scattered randomly. Each has:
    - Random position along the x-axis (transit path)
    - Random y-offset (not all centered)
    - Random memory depth (0.01 to 0.08)
    - Random radius (5 to 40 px)
    - Classification: dwarf, standard, or massive remnant

    Returns lambda field and grave catalog.
    """
    rng = np.random.RandomState(seed)

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    lam_field = np.full((nx, ny), void_lambda, dtype=float)
    graves = []

    for i in range(n_graves):
        # Position: scattered across the void
        # Avoid first 20 px (departure) and last 20 px (arrival)
        gx = rng.randint(25, nx - 25)
        gy = ny // 2 + rng.randint(-ny // 4, ny // 4)

        # Size classification
        roll = rng.random()
        if roll < 0.50:
            # Dwarf remnant (50%)
            depth = rng.uniform(0.01, 0.03)
            radius = rng.uniform(5, 12)
            gtype = "DWARF"
        elif roll < 0.85:
            # Standard remnant (35%)
            depth = rng.uniform(0.03, 0.06)
            radius = rng.uniform(12, 25)
            gtype = "STANDARD"
        else:
            # Massive remnant (15%)
            depth = rng.uniform(0.06, 0.09)
            radius = rng.uniform(25, 45)
            gtype = "MASSIVE"

        # Apply memory to lambda field
        r2 = (X - gx)**2 + (Y - gy)**2
        memory = depth * np.exp(-r2 / (2 * radius**2))
        lam_field = lam_field - memory

        graves.append({
            "id": i,
            "x": int(gx),
            "y": int(gy),
            "depth": round(depth, 4),
            "radius": round(radius, 2),
            "type": gtype,
        })

    lam_field = np.maximum(lam_field, 0.001)

    return lam_field, graves


def main():
    parser = argparse.ArgumentParser(
        description="BCM v15 Bootes Void Maximum Feasibility")
    parser.add_argument("--steps", type=int, default=8000)
    parser.add_argument("--grid-x", type=int, default=512)
    parser.add_argument("--grid-y", type=int, default=64)
    parser.add_argument("--graves", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    nx = args.grid_x
    ny = args.grid_y

    print(f"\n{'='*70}")
    print(f"  BCM v15 — BOOTES VOID MAXIMUM FEASIBILITY TRANSIT")
    print(f"  330 million light-years. 60 dead galaxies. One ship.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*70}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"  Scale: 1 px = {330_000_000 / nx:,.0f} light-years")
    print(f"  Dead galaxies: {args.graves}")
    print(f"  Seed: {args.seed}")

    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    ratio = 0.25
    alpha = 0.80
    separation = 15.0
    exhaust_coupling = 0.002

    # Phase cycling parameters
    drive_len = 375    # 3 parts drive
    shift_len = 125    # 1 part shift
    dump_len = 125     # 1 part dump
    collect_len = 125  # 1 part collect
    full_cycle = drive_len + shift_len + dump_len + collect_len

    # ── Build the Void ──
    print(f"\n  Building Bootes Void...")
    lam_field, graves = build_bootes_void(
        nx, ny, void_lambda, args.graves, args.seed)

    # Grave census
    dwarf_count = sum(1 for g in graves if g["type"] == "DWARF")
    std_count = sum(1 for g in graves if g["type"] == "STANDARD")
    massive_count = sum(1 for g in graves if g["type"] == "MASSIVE")

    print(f"  Grave census: {dwarf_count} dwarf, "
          f"{std_count} standard, {massive_count} massive")
    print(f"  Lambda range: {float(np.min(lam_field)):.4f} "
          f"to {float(np.max(lam_field)):.4f}")

    # Map the transit corridor
    corridor_lam = np.mean(lam_field[:, ny//2-5:ny//2+5], axis=1)
    hotspots = sum(1 for v in corridor_lam if v < 0.07)
    print(f"  Corridor hotspots (lambda < 0.07): {hotspots} px")

    # ── Initialize Ship ──
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    start_x = 10
    start_y = ny // 2
    target_x = nx - 10

    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    initial_com = compute_com(sigma)
    initial_mass = measure_ship_envelope(sigma, initial_com)

    lam_working = lam_field.copy()
    lam_orig = lam_field.copy()
    prev_com = initial_com.copy()

    print(f"\n  Departure: px {start_x} (Sun / helion)")
    print(f"  Target:    px {target_x} (far-side galaxy)")
    print(f"  Distance:  {target_x - start_x} px "
          f"= {(target_x - start_x) * 330_000_000 / nx:,.0f} ly")
    print(f"  Initial ship mass: {initial_mass:.4f}")

    # ── Transit ──
    print(f"\n  {'─'*65}")
    print(f"  TRANSIT LOG")
    print(f"  {'─'*65}")
    print(f"  {'Step':>6} {'Phase':>8} {'X':>8} {'Drift':>8} "
          f"{'Mass':>10} {'Pickup':>8} {'Coh':>6} "
          f"{'LocalLam':>9} {'Graves':>7}")
    print(f"  {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*10} "
          f"{'─'*8} {'─'*6} {'─'*9} {'─'*7}")

    timeline = []
    alive = True
    cores_dropped = 0
    core_mass_absorbed = 0.0
    graves_crossed = set()
    peak_mass_ratio = 1.0
    min_coherence = 1.0
    arrived = False

    for step in range(args.steps):
        com = compute_com(sigma)
        if com is None:
            alive = False
            print(f"  ** DISSOLVED at step {step} **")
            break

        velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])
        speed = float(np.linalg.norm(velocity_vec))

        # Check arrival
        if com[0] >= target_x:
            arrived = True
            print(f"  ** ARRIVED at step {step}, x={com[0]:.2f} **")

        # Track graves crossed
        for g in graves:
            dist_to_grave = np.sqrt((com[0] - g["x"])**2 +
                                    (com[1] - g["y"])**2)
            if dist_to_grave < g["radius"] * 1.5:
                graves_crossed.add(g["id"])

        # ── Phase cycling ──
        cycle_pos = step % full_cycle
        if cycle_pos < drive_len:
            phase = "DRIVE"
            current_pA = pump_A
            current_ratio = ratio
        elif cycle_pos < drive_len + shift_len:
            phase = "SHIFT"
            current_pA = pump_A * 0.5
            current_ratio = 1.0
        elif cycle_pos < drive_len + shift_len + dump_len:
            phase = "DUMP"
            current_pA = pump_A * 0.8
            current_ratio = 0.0
        else:
            phase = "COLLECT"
            current_pA = pump_A * 0.2
            current_ratio = 1.0

        # ── Apply pumps ──
        if current_pA > 0:
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = current_pA * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            if current_ratio > 0:
                bx = com[0] + separation
                r2_B = (X - bx)**2 + (Y - com[1])**2
                actual_B = current_pA * current_ratio
                pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
                sigma += pB * dt

        # Exhaust coupling (DRIVE phase only)
        if phase == "DRIVE":
            aft_weight = np.ones((nx, ny))
            for col in range(nx):
                if col < int(com[0]):
                    aft_weight[col, :] = 1.0
                elif col < int(com[0]) + 5:
                    aft_weight[col, :] = 0.3
                else:
                    aft_weight[col, :] = 0.05
            exhaust = exhaust_coupling * sigma * aft_weight * dt
            lam_working = lam_working - exhaust
            lam_working = np.maximum(lam_working, 0.001)

        # Dump: flush + relax
        if phase == "DUMP":
            relax = 0.02 * (lam_orig - lam_working) * dt
            lam_working = lam_working + relax

        # Shift: mild relax
        if phase == "SHIFT":
            relax = 0.01 * (lam_orig - lam_working) * dt
            lam_working = lam_working + relax

        # Core-drop (COLLECT phase)
        if phase == "COLLECT":
            core_x = com[0] - 20
            core_y = com[1]
            r2_core = (X - core_x)**2 + (Y - core_y)**2
            core_envelope = r2_core < 15.0**2

            absorption_rate = 0.1
            absorbed = sigma[core_envelope] * absorption_rate * dt
            sigma[core_envelope] -= absorbed
            sigma = np.maximum(sigma, 0)
            core_mass_absorbed += float(np.sum(absorbed))

            cycle_pos_in_collect = cycle_pos - (drive_len + shift_len + dump_len)
            if cycle_pos_in_collect == 0:
                cores_dropped += 1

        # ── Evolve PDE ──
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma_new = sigma + D * laplacian * dt - lam_working * sigma * dt

        if alpha > 0:
            sigma_new = sigma_new + alpha * (sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)

        if float(np.max(sigma_new)) > 1e10:
            alive = False
            print(f"  ** BLOWUP at step {step} **")
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Track extremes
        new_com = compute_com(sigma)
        if new_com is not None:
            current_mass = measure_ship_envelope(sigma, new_com)
            mr = current_mass / initial_mass
            if mr > peak_mass_ratio:
                peak_mass_ratio = mr
            coh = compute_coherence(sigma, new_com)
            if coh < min_coherence:
                min_coherence = coh

        # Log every 200 steps
        if step % 200 == 0 or step == args.steps - 1 or arrived:
            if new_com is not None:
                drift = float(np.linalg.norm(new_com - initial_com))
                ship_mass = measure_ship_envelope(sigma, new_com)
                pickup = ship_mass / initial_mass
                coh = compute_coherence(sigma, new_com)

                ix = min(max(int(new_com[0]), 0), nx - 1)
                iy = min(max(int(new_com[1]), 0), ny - 1)
                local_lam = float(lam_working[ix, iy])

                entry = {
                    "step": step,
                    "phase": phase,
                    "x": round(float(new_com[0]), 2),
                    "drift": round(drift, 2),
                    "mass": round(ship_mass, 4),
                    "pickup": round(pickup, 4),
                    "coherence": round(coh, 4),
                    "local_lambda": round(local_lam, 6),
                    "graves_crossed": len(graves_crossed),
                }
                timeline.append(entry)

                print(f"  {step:>6} {phase:>8} {new_com[0]:>8.1f} "
                      f"{drift:>8.1f} {ship_mass:>10.2f} "
                      f"{pickup:>8.2f}x {coh:>6.3f} "
                      f"{local_lam:>9.5f} {len(graves_crossed):>7}")

            if arrived:
                break

        prev_com = com

    # ── EXIT REPORT ──
    print(f"\n{'='*70}")
    print(f"  EXIT REPORT — BOOTES VOID CROSSING")
    print(f"{'='*70}")

    final_com = compute_com(sigma)
    if final_com is not None:
        final_drift = float(np.linalg.norm(final_com - initial_com))
        final_mass = measure_ship_envelope(sigma, final_com)
        final_coh = compute_coherence(sigma, final_com)
        final_pickup = final_mass / initial_mass
    else:
        final_drift = 0
        final_mass = 0
        final_coh = 0
        final_pickup = 0

    pct_crossed = (final_drift / (target_x - start_x)) * 100

    print(f"\n  STATUS: {'ARRIVED' if arrived else 'DISSOLVED' if not alive else 'IN TRANSIT'}")
    print(f"  Distance covered: {final_drift:.1f} px "
          f"({pct_crossed:.1f}% of void)")
    print(f"  Distance in ly: "
          f"{final_drift * 330_000_000 / nx:,.0f} light-years")
    print(f"")
    print(f"  SHIP CONDITION AT EXIT:")
    print(f"  {'─'*50}")
    print(f"  Alive:              {'YES' if alive else 'NO'}")
    print(f"  Initial mass:       {initial_mass:.4f}")
    print(f"  Final mass:         {final_mass:.4f}")
    print(f"  Mass pickup:        {final_pickup:.2f}x "
          f"({(final_pickup-1)*100:+.1f}%)")
    print(f"  Peak mass ratio:    {peak_mass_ratio:.2f}x")
    print(f"  Final coherence:    {final_coh:.4f}")
    print(f"  Minimum coherence:  {min_coherence:.4f}")
    print(f"  Cores dropped:      {cores_dropped}")
    print(f"  Core mass absorbed: {core_mass_absorbed:.2f}")
    print(f"  Graves crossed:     {len(graves_crossed)} of {args.graves}")
    print(f"")

    # Risk assessment
    if final_pickup > 50:
        risk = "NO-GO — Ship became a source"
    elif final_pickup > 10:
        risk = "STELLAR RISK — Ship approaching source-scale"
    elif final_pickup > 5:
        risk = "DANGER — Significant mass accumulation"
    elif final_pickup > 2:
        risk = "CAUTION — Elevated mass, governor compensating"
    else:
        risk = "SAFE — Ship within operational parameters"

    print(f"  RISK ASSESSMENT: {risk}")

    if final_coh < 0.15:
        print(f"  ** COHERENCE CRITICAL — structural dissolution imminent **")
    elif final_coh < 0.30:
        print(f"  ** COHERENCE LOW — structural integrity compromised **")
    elif final_coh < 0.50:
        print(f"  ** COHERENCE REDUCED — hull stress elevated **")

    # Grave encounter log
    print(f"\n  GRAVE ENCOUNTERS ({len(graves_crossed)} total):")
    print(f"  {'─'*50}")
    for gid in sorted(graves_crossed):
        g = graves[gid]
        print(f"    Grave {g['id']:>2}: x={g['x']:>4} "
              f"type={g['type']:>8} depth={g['depth']:.4f} "
              f"radius={g['radius']:>5.1f}")

    print(f"\n{'='*70}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v15_bootes_crossing_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v15 Bootes Void Maximum Feasibility Transit",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "330 Mly crossing with 60 dead galaxies",
        "grid": f"{nx}x{ny}",
        "steps": args.steps,
        "scale_ly_per_px": round(330_000_000 / nx),
        "parameters": {
            "dt": dt, "D": D, "void_lambda": void_lambda,
            "pump_A": pump_A, "ratio": ratio,
            "alpha": alpha, "separation": separation,
            "exhaust_coupling": exhaust_coupling,
        },
        "departure": {"x": start_x, "label": "Sun / Helion"},
        "target": {"x": target_x, "label": "Far-side galaxy"},
        "graves": graves,
        "grave_census": {
            "total": args.graves,
            "dwarf": dwarf_count,
            "standard": std_count,
            "massive": massive_count,
        },
        "result": {
            "arrived": arrived,
            "alive": alive,
            "distance_px": round(final_drift, 2),
            "distance_ly": round(final_drift * 330_000_000 / nx),
            "pct_crossed": round(pct_crossed, 1),
            "initial_mass": round(initial_mass, 4),
            "final_mass": round(final_mass, 4),
            "mass_pickup": round(final_pickup, 4),
            "peak_mass_ratio": round(peak_mass_ratio, 4),
            "final_coherence": round(final_coh, 4),
            "min_coherence": round(min_coherence, 4),
            "cores_dropped": cores_dropped,
            "core_mass_absorbed": round(core_mass_absorbed, 2),
            "graves_crossed": len(graves_crossed),
            "risk": risk,
        },
        "timeline": timeline,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
