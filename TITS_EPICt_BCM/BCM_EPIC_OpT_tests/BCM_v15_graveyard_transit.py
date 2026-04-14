# -*- coding: utf-8 -*-
"""
BCM v15 — Graveyard Transit (Dead Galaxy Wake Test)
=====================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The Bootes Void is not empty. It is a graveyard with
the headstones still warm. When an entire galaxy dies,
the substrate retains residual memory — dormant lambda
patterns from billions of years of funded events.

A ship enters this graveyard with pumps running. The
pumps agitate the substrate. The substrate has memory.
If the residual memory is deep enough, the pumps could
re-excite dormant modes — the ship wakes up what was
sleeping in the field.

Three questions:

  1. Can we OUTRUN the re-agitation? Does the excitation
     wave propagate faster than the ship moves?

  2. Does the CONTRAIL arrive with us? Does accumulated
     mass trail the ship and enter its orbit?

  3. How much MASS does the ship drag? At what velocity
     does accumulated sigma exceed ship-scale and risk
     entering stellar-scale?

METHOD:
  Grid = Bootes Void section. Pre-load with residual
  lambda memory from a dead dwarf galaxy (~10^9 solar
  masses worth of substrate memory, scaled to grid).

  Lambda field has structure: deeper memory near the
  dead galactic center, fading to baseline void at edges.
  This is the fossil — the footprint in the snow after
  the walker dissolved.

  Run the ship at multiple velocities (pump ratios).
  At each ratio, measure:
  - Ship sigma at start vs end (mass pickup)
  - Sigma within 20px trailing envelope (contrail mass)
  - Excitation wavefront speed vs ship speed
  - Total field energy before and after transit
  - Does the ship reach stellar-scale sigma? (danger zone)

Usage:
    python BCM_v15_graveyard_transit.py
    python BCM_v15_graveyard_transit.py --steps 3000 --grid 256
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


def build_graveyard(nx, ny, void_lambda, memory_depth,
                    memory_radius):
    """
    Build a dead galaxy lambda field.

    The graveyard has residual memory: lambda is lower
    (more funded) near where the galactic center was,
    fading to baseline void at the edges.

    Lower lambda = more memory = more dormant energy
    available for re-excitation.

    memory_depth: how much lower than void_lambda at center
                  (0.0 = fully funded ghost, void_lambda = no memory)
    memory_radius: how far the memory extends (in grid units)
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Dead galactic center at grid center
    cx, cy = nx // 2, ny // 2
    r2 = (X - cx)**2 + (Y - cy)**2

    # Gaussian memory profile: deep at center, fading out
    memory = memory_depth * np.exp(-r2 / (2 * memory_radius**2))

    # Lambda = void baseline minus memory
    # Lower lambda = more residual funding = more ghost energy
    lam_field = void_lambda - memory
    lam_field = np.maximum(lam_field, 0.001)  # floor

    return lam_field


def measure_ship_envelope(sigma, com, radius):
    """Measure total sigma within radius of COM."""
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    r2 = (X - com[0])**2 + (Y - com[1])**2
    return float(np.sum(sigma[r2 < radius**2]))


def measure_contrail(sigma, com, trail_length, trail_width):
    """Measure sigma in the trailing wake behind the ship."""
    nx, ny = sigma.shape
    ix = int(round(com[0]))
    iy = int(round(com[1]))

    # Trail: behind the ship (x < COM), within width of centerline
    total = 0.0
    count = 0
    for col in range(max(0, ix - trail_length), ix):
        for row in range(max(0, iy - trail_width),
                         min(ny, iy + trail_width + 1)):
            total += sigma[col, row]
            count += 1

    return total, count


def measure_excitation_front(sigma, sigma_baseline, com, nx, ny):
    """
    Measure how far ahead of the ship the substrate is
    excited above baseline. Returns the furthest x-position
    ahead of COM where sigma > 1.5x baseline peak.
    """
    ix = int(round(com[0]))
    iy = int(round(com[1]))

    # Check along the centerline ahead of ship
    baseline_peak = float(np.max(sigma_baseline)) if np.max(sigma_baseline) > 0 else 0.01
    threshold = baseline_peak * 0.1  # 10% of initial peak

    furthest = ix
    band = range(max(0, iy - 3), min(ny, iy + 4))

    for col in range(min(ix + 1, nx), nx):
        col_max = max(float(sigma[col, r]) for r in band)
        if col_max > threshold:
            furthest = col

    excitation_reach = furthest - ix
    return max(0, excitation_reach)


def run_transit(steps, nx, ny, dt, D, lam_field,
                pump_A, ratio, separation, alpha,
                exhaust_coupling, label="TRANSIT"):
    """
    Run one transit through the graveyard at a given ratio.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Ship starts at left edge, row center
    start_x = nx // 6
    start_y = ny // 2

    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    sigma_initial = sigma.copy()

    # Measure initial ship mass
    initial_com = compute_com(sigma)
    initial_ship_mass = measure_ship_envelope(sigma, initial_com, 12)
    initial_field_energy = float(np.sum(sigma**2))

    lam_working = lam_field.copy()
    lam_baseline = lam_field.copy()

    prev_com = initial_com.copy()

    timeline = []
    alive = True

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            alive = False
            break

        velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])
        speed = float(np.linalg.norm(velocity_vec))

        # Raw pumps — no governor (we want to see the
        # naked interaction with the graveyard)
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        actual_B = pump_A * ratio
        pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        # Exhaust coupling — ship deposits into lambda
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

        # Evolve PDE — using the graveyard lambda field
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma_new = sigma + D * laplacian * dt - lam_working * sigma * dt

        # Memory
        if alpha > 0:
            sigma_new = sigma_new + alpha * (sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)

        if float(np.max(sigma_new)) > 1e10:
            alive = False
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Measurements every 100 steps
        if step % 100 == 0 or step == steps - 1:
            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(new_com - initial_com))
                ship_mass = measure_ship_envelope(sigma, new_com, 12)
                mass_ratio = ship_mass / initial_ship_mass if initial_ship_mass > 0 else 0

                contrail_mass, contrail_px = measure_contrail(
                    sigma, new_com, trail_length=30, trail_width=8)

                excitation_reach = measure_excitation_front(
                    sigma, sigma_initial, new_com, nx, ny)

                field_energy = float(np.sum(sigma**2))
                energy_ratio = field_energy / initial_field_energy if initial_field_energy > 0 else 0

                coh = compute_coherence(sigma, new_com)

                timeline.append({
                    "step": step,
                    "x": round(float(new_com[0]), 4),
                    "drift": round(drift, 4),
                    "speed": round(speed, 8),
                    "ship_mass": round(ship_mass, 6),
                    "mass_ratio": round(mass_ratio, 6),
                    "contrail_mass": round(contrail_mass, 6),
                    "excitation_reach": excitation_reach,
                    "field_energy": round(field_energy, 4),
                    "energy_ratio": round(energy_ratio, 6),
                    "coherence": round(coh, 4),
                })

        prev_com = com

    # Final measurements
    final_com = compute_com(sigma)
    if final_com is not None:
        total_drift = float(np.linalg.norm(final_com - initial_com))
        final_ship_mass = measure_ship_envelope(sigma, final_com, 12)
        final_contrail, _ = measure_contrail(
            sigma, final_com, trail_length=30, trail_width=8)
        final_coh = compute_coherence(sigma, final_com)
        final_energy = float(np.sum(sigma**2))
    else:
        total_drift = 0
        final_ship_mass = 0
        final_contrail = 0
        final_coh = 0
        final_energy = 0

    mass_pickup = final_ship_mass / initial_ship_mass if initial_ship_mass > 0 else 0

    return {
        "label": label,
        "ratio": ratio,
        "alive": alive,
        "drift": round(total_drift, 6),
        "initial_ship_mass": round(initial_ship_mass, 6),
        "final_ship_mass": round(final_ship_mass, 6),
        "mass_pickup_ratio": round(mass_pickup, 6),
        "final_contrail_mass": round(final_contrail, 6),
        "final_coherence": round(final_coh, 4),
        "initial_field_energy": round(initial_field_energy, 4),
        "final_field_energy": round(final_energy, 4),
        "energy_ratio": round(final_energy / initial_field_energy, 6) if initial_field_energy > 0 else 0,
        "timeline": timeline,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v15 Graveyard Transit")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v15 — GRAVEYARD TRANSIT")
    print(f"  Dead galaxy wake test.")
    print(f"  Can we outrun the ghosts?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    alpha = 0.80
    separation = 15.0
    exhaust_coupling = 0.002

    # ── Build the graveyard ──
    # Dwarf galaxy: memory_depth = how much lambda is
    # reduced at the dead center. 0.08 means lambda goes
    # from 0.10 (void) down to 0.02 (heavily funded ghost).
    # memory_radius = how far the memory extends.

    memory_configs = [
        {"name": "SHALLOW_GRAVE", "depth": 0.03, "radius": 20,
         "desc": "Small dwarf remnant, weak memory"},
        {"name": "DEEP_GRAVE", "depth": 0.07, "radius": 30,
         "desc": "Large dwarf remnant, strong memory"},
        {"name": "MASS_GRAVE", "depth": 0.09, "radius": 45,
         "desc": "Full galaxy remnant, near-funded ghost field"},
    ]

    # Velocity sweep via pump ratio
    ratios = [0.10, 0.25, 0.50, 0.75]

    all_results = {}

    for config in memory_configs:
        print(f"\n{'='*65}")
        print(f"  GRAVEYARD: {config['name']}")
        print(f"  {config['desc']}")
        print(f"  Memory depth: {config['depth']}  "
              f"Radius: {config['radius']}")
        print(f"{'='*65}")

        lam_field = build_graveyard(nx, ny, void_lambda,
                                    config["depth"],
                                    config["radius"])

        # Report lambda stats
        print(f"  Lambda range: {float(np.min(lam_field)):.4f} "
              f"to {float(np.max(lam_field)):.4f}")
        print(f"  Lambda at center: "
              f"{float(lam_field[nx//2, ny//2]):.4f}")

        config_results = []

        print(f"\n  {'Ratio':>6} {'Drift':>8} {'Mass In':>10} "
              f"{'Mass Out':>10} {'Pickup':>8} "
              f"{'Contrail':>10} {'E_ratio':>8} {'Coh':>6}")
        print(f"  {'─'*6} {'─'*8} {'─'*10} {'─'*10} "
              f"{'─'*8} {'─'*10} {'─'*8} {'─'*6}")

        for ratio in ratios:
            result = run_transit(
                args.steps, nx, ny, dt, D, lam_field,
                pump_A, ratio, separation, alpha,
                exhaust_coupling,
                label=f"{config['name']}_R{ratio}")

            config_results.append(result)

            status = "ALIVE" if result["alive"] else "DEAD"
            print(f"  {ratio:>6.2f} {result['drift']:>8.2f} "
                  f"{result['initial_ship_mass']:>10.4f} "
                  f"{result['final_ship_mass']:>10.4f} "
                  f"{result['mass_pickup_ratio']:>8.4f} "
                  f"{result['final_contrail_mass']:>10.4f} "
                  f"{result['energy_ratio']:>8.4f} "
                  f"{result['final_coherence']:>6.3f} "
                  f" {status}")

        all_results[config["name"]] = {
            "config": config,
            "results": config_results,
        }

        # ── Can we outrun it? ──
        print(f"\n  EXCITATION ANALYSIS:")
        for r in config_results:
            if r["timeline"]:
                last = r["timeline"][-1]
                reach = last.get("excitation_reach", 0)
                speed = last.get("speed", 0)
                print(f"    Ratio {r['ratio']:.2f}: "
                      f"excitation reach = {reach} px ahead, "
                      f"ship speed = {speed:.6f}")

    # ── Final Summary ──
    print(f"\n{'='*65}")
    print(f"  GRAVEYARD TRANSIT SUMMARY")
    print(f"{'='*65}")

    for config_name, data in all_results.items():
        config = data["config"]
        results = data["results"]

        print(f"\n  {config_name} (depth={config['depth']}, "
              f"radius={config['radius']}):")
        print(f"  {'─'*55}")

        for r in results:
            pickup_pct = (r["mass_pickup_ratio"] - 1.0) * 100
            danger = ""
            if r["mass_pickup_ratio"] > 5.0:
                danger = " *** STELLAR RISK ***"
            elif r["mass_pickup_ratio"] > 2.0:
                danger = " ** HIGH ACCUMULATION **"
            elif r["mass_pickup_ratio"] > 1.5:
                danger = " * ELEVATED *"

            print(f"    R={r['ratio']:.2f}: "
                  f"drift={r['drift']:>7.2f} px  "
                  f"mass pickup={pickup_pct:>+7.1f}%  "
                  f"contrail={r['final_contrail_mass']:>8.3f}"
                  f"{danger}")

    # Outrun analysis
    print(f"\n  Q1: CAN WE OUTRUN THE RE-AGITATION?")
    print(f"  {'─'*55}")
    # Compare excitation reach vs ship speed across configs
    for config_name, data in all_results.items():
        for r in data["results"]:
            if r["timeline"]:
                speeds = [t["speed"] for t in r["timeline"] if t["speed"] > 0]
                reaches = [t["excitation_reach"] for t in r["timeline"]]
                avg_speed = np.mean(speeds) if speeds else 0
                max_reach = max(reaches) if reaches else 0
                print(f"    {config_name} R={r['ratio']:.2f}: "
                      f"avg_speed={avg_speed:.6f} px/step  "
                      f"max_excitation_reach={max_reach} px")

    print(f"\n  Q2: DOES THE CONTRAIL ARRIVE WITH US?")
    print(f"  {'─'*55}")
    for config_name, data in all_results.items():
        for r in data["results"]:
            if r["final_contrail_mass"] > 0.1:
                print(f"    {config_name} R={r['ratio']:.2f}: "
                      f"contrail mass = {r['final_contrail_mass']:.4f}  "
                      f"YES — trailing mass detected")
            else:
                print(f"    {config_name} R={r['ratio']:.2f}: "
                      f"contrail mass = {r['final_contrail_mass']:.4f}  "
                      f"minimal trailing mass")

    print(f"\n  Q3: HOW MUCH MASS DO WE BRING?")
    print(f"  {'─'*55}")
    max_pickup = 0
    worst_case = None
    for config_name, data in all_results.items():
        for r in data["results"]:
            if r["mass_pickup_ratio"] > max_pickup:
                max_pickup = r["mass_pickup_ratio"]
                worst_case = (config_name, r["ratio"])

    if worst_case:
        pickup_pct = (max_pickup - 1.0) * 100
        print(f"    Worst case: {worst_case[0]} at ratio "
              f"{worst_case[1]:.2f}")
        print(f"    Mass pickup: {pickup_pct:+.1f}% of initial")
        if max_pickup > 5.0:
            print(f"    *** DANGER: Ship risks entering stellar-scale ***")
        elif max_pickup > 2.0:
            print(f"    ** WARNING: Significant mass accumulation **")
        else:
            print(f"    Within safe operating margin.")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v15_graveyard_{time.strftime('%Y%m%d_%H%M%S')}.json")

    # Strip timelines for compact JSON
    save_results = {}
    for config_name, data in all_results.items():
        compact = []
        for r in data["results"]:
            rc = {k: v for k, v in r.items() if k != "timeline"}
            # Keep first/last/sampled timeline entries
            if r["timeline"]:
                rc["timeline_sample"] = (
                    [r["timeline"][0]] +
                    r["timeline"][len(r["timeline"])//4::len(r["timeline"])//4][:3] +
                    [r["timeline"][-1]]
                )
            compact.append(rc)
        save_results[config_name] = {
            "config": data["config"],
            "results": compact,
        }

    out_data = {
        "title": "BCM v15 Graveyard Transit — Dead Galaxy Wake Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Can we outrun the ghosts? Mass pickup from dead substrate.",
        "grid": nx,
        "steps": args.steps,
        "parameters": {
            "dt": dt, "D": D, "void_lambda": void_lambda,
            "pump_A": pump_A, "alpha": alpha,
            "separation": separation,
            "exhaust_coupling": exhaust_coupling,
        },
        "graveyard_configs": [c for c in memory_configs],
        "results": save_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
