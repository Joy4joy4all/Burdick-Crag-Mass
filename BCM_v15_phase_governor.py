# -*- coding: utf-8 -*-
"""
BCM v15 — Phase-Cycling Governor & Core-Drop
===============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The graveyard transit showed +5,901% mass pickup at the
worst case. The ship becomes a star. That is a no-go.

This test implements Stephen's pump-cycling idea and
Gemini's core-drop strategy to find the BOUNDARY between
navigable and exclusion zones.

FOUR-PHASE CYCLE (Stephen / Gemini):
  1. DRIVE:   Binary pump, asymmetric ratio. Transport.
  2. SHIFT:   Equal pumps, neutralize drift. Stabilize.
  3. DUMP:    Pump B off, high A. Flush forward field.
  4. COLLECT: Drop heavy core. Core absorbs trailing wake.
              Ship decouples from core and moves on lighter.

SWEEP: Memory depth from 0.01 to 0.09 in 0.01 increments.
At each depth, run three configs:
  A) RAW (no cycling, no core-drop) — baseline danger
  B) CYCLING (4-phase governor, no core-drop)
  C) CYCLING + CORE-DROP (full countermeasure)

Find the depth where mass pickup crosses:
  - 2x initial (CAUTION)
  - 5x initial (DANGER)
  - 10x initial (STELLAR RISK)
  - 50x initial (NO-GO)

Usage:
    python BCM_v15_phase_governor.py
    python BCM_v15_phase_governor.py --steps 3000 --grid 128
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


def build_graveyard(nx, ny, void_lambda, depth, radius=30):
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    cx, cy = nx // 2, ny // 2
    r2 = (X - cx)**2 + (Y - cy)**2
    memory = depth * np.exp(-r2 / (2 * radius**2))
    lam = void_lambda - memory
    return np.maximum(lam, 0.001)


def run_transit(steps, nx, ny, dt, D, lam_field_orig,
                pump_A, ratio, separation, alpha,
                exhaust_coupling, mode="RAW",
                cycle_length=250):
    """
    Run transit in one of three modes:
      RAW:       No cycling, no core-drop. Continuous drive.
      CYCLING:   4-phase pump cycling, no core-drop.
      FULL:      4-phase cycling + core-drop in COLLECT phase.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    start_x = nx // 6
    start_y = ny // 2

    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    initial_com = compute_com(sigma)
    initial_ship_mass = measure_ship_envelope(sigma, initial_com)

    lam_field = lam_field_orig.copy()
    prev_com = initial_com.copy()

    # Core-drop tracking
    cores_dropped = 0
    core_mass_absorbed = 0.0

    # Phase timing
    phase_length = cycle_length  # steps per phase
    # 3:1:1:1 ratio as Gemini recommended
    drive_len = phase_length * 3
    shift_len = phase_length
    dump_len = phase_length
    collect_len = phase_length
    full_cycle = drive_len + shift_len + dump_len + collect_len

    alive = True
    peak_mass_ratio = 1.0

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            alive = False
            break

        velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])
        speed = float(np.linalg.norm(velocity_vec))

        # ── DETERMINE PHASE ──
        if mode == "RAW":
            phase = "DRIVE"
            current_pA = pump_A
            current_ratio = ratio
            current_sep = separation
        else:
            cycle_pos = step % full_cycle
            if cycle_pos < drive_len:
                phase = "DRIVE"
                current_pA = pump_A
                current_ratio = ratio
                current_sep = separation
            elif cycle_pos < drive_len + shift_len:
                phase = "SHIFT"
                current_pA = pump_A * 0.5
                current_ratio = 1.0  # equal pumps, neutralize
                current_sep = separation
            elif cycle_pos < drive_len + shift_len + dump_len:
                phase = "DUMP"
                current_pA = pump_A * 0.8  # high A, no B
                current_ratio = 0.0
                current_sep = separation
            else:
                phase = "COLLECT"
                current_pA = pump_A * 0.2  # low power soak
                current_ratio = 1.0
                current_sep = separation

        # ── APPLY PUMPS ──
        if current_pA > 0:
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = current_pA * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            if current_ratio > 0:
                bx = com[0] + current_sep
                r2_B = (X - bx)**2 + (Y - com[1])**2
                actual_B = current_pA * current_ratio
                pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
                sigma += pB * dt

        # ── EXHAUST COUPLING ──
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
            lam_field = lam_field - exhaust
            lam_field = np.maximum(lam_field, 0.001)

        # ── DUMP PHASE: flush forward field ──
        if phase == "DUMP":
            # High-power forward agitation clears ahead
            # Substrate relaxation boosted during dump
            relax = 0.02 * (lam_field_orig - lam_field) * dt
            lam_field = lam_field + relax
            lam_field = np.maximum(lam_field, 0.001)

        # ── CORE-DROP (COLLECT phase, FULL mode only) ──
        if phase == "COLLECT" and mode == "FULL":
            # Drop a heavy core behind the ship to absorb wake
            # The core sits at a fixed position behind current COM
            # and acts as a sigma sink — it pulls trailing mass
            # away from the ship envelope

            core_x = com[0] - 20  # 20 px behind ship
            core_y = com[1]

            # Define core absorption radius
            r2_core = (X - core_x)**2 + (Y - core_y)**2
            core_envelope = r2_core < 15.0**2

            # Mass in the core zone
            core_zone_mass = float(np.sum(sigma[core_envelope]))

            # Transfer: reduce sigma in core zone, track absorbed
            # The core "eats" the wake — sigma drops in that zone
            absorption_rate = 0.1
            absorbed = sigma[core_envelope] * absorption_rate * dt
            sigma[core_envelope] -= absorbed
            sigma = np.maximum(sigma, 0)

            mass_removed = float(np.sum(absorbed))
            core_mass_absorbed += mass_removed

            # Count cores
            cycle_pos_in_collect = step % full_cycle - (drive_len + shift_len + dump_len)
            if cycle_pos_in_collect == 0:
                cores_dropped += 1

        # ── SHIFT PHASE: lambda relaxation ──
        if phase == "SHIFT":
            relax = 0.01 * (lam_field_orig - lam_field) * dt
            lam_field = lam_field + relax

        # ── EVOLVE PDE ──
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma_new = sigma + D * laplacian * dt - lam_field * sigma * dt

        if alpha > 0:
            sigma_new = sigma_new + alpha * (sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)

        if float(np.max(sigma_new)) > 1e10:
            alive = False
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Track peak mass ratio
        new_com = compute_com(sigma)
        if new_com is not None:
            current_mass = measure_ship_envelope(sigma, new_com)
            current_ratio_m = current_mass / initial_ship_mass
            if current_ratio_m > peak_mass_ratio:
                peak_mass_ratio = current_ratio_m

        prev_com = com

    # ── Final Measurements ──
    final_com = compute_com(sigma)
    if final_com is not None:
        total_drift = float(np.linalg.norm(final_com - initial_com))
        final_mass = measure_ship_envelope(sigma, final_com)
        final_coh = compute_coherence(sigma, final_com)
    else:
        total_drift = 0
        final_mass = 0
        final_coh = 0

    mass_pickup = final_mass / initial_ship_mass

    return {
        "mode": mode,
        "alive": alive,
        "drift": round(total_drift, 4),
        "initial_mass": round(initial_ship_mass, 4),
        "final_mass": round(final_mass, 4),
        "mass_pickup_ratio": round(mass_pickup, 4),
        "peak_mass_ratio": round(peak_mass_ratio, 4),
        "mass_pickup_pct": round((mass_pickup - 1) * 100, 1),
        "final_coherence": round(final_coh, 4),
        "cores_dropped": cores_dropped,
        "core_mass_absorbed": round(core_mass_absorbed, 4),
    }


def classify_risk(mass_ratio):
    if mass_ratio < 2.0:
        return "SAFE"
    elif mass_ratio < 5.0:
        return "CAUTION"
    elif mass_ratio < 10.0:
        return "DANGER"
    elif mass_ratio < 50.0:
        return "STELLAR RISK"
    else:
        return "NO-GO"


def main():
    parser = argparse.ArgumentParser(
        description="BCM v15 Phase-Cycling Governor")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v15 — PHASE-CYCLING GOVERNOR & CORE-DROP")
    print(f"  Finding the boundary between navigable and no-go.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    ratio = 0.25
    alpha = 0.80
    separation = 15.0
    exhaust_coupling = 0.002

    # Sweep memory depths
    depths = [0.01, 0.02, 0.03, 0.04, 0.05,
              0.06, 0.07, 0.08, 0.09]
    memory_radius = 30

    all_results = []

    print(f"\n  {'Depth':>6} {'Mode':>10} {'Drift':>8} "
          f"{'Pickup':>8} {'Peak':>8} {'Coh':>6} "
          f"{'Cores':>6} {'Absorbed':>10} {'Risk':>14}")
    print(f"  {'─'*6} {'─'*10} {'─'*8} {'─'*8} {'─'*8} "
          f"{'─'*6} {'─'*6} {'─'*10} {'─'*14}")

    for depth in depths:
        lam_field = build_graveyard(nx, ny, void_lambda,
                                    depth, memory_radius)

        depth_results = {}

        for mode in ["RAW", "CYCLING", "FULL"]:
            result = run_transit(
                args.steps, nx, ny, dt, D, lam_field,
                pump_A, ratio, separation, alpha,
                exhaust_coupling, mode=mode,
                cycle_length=125)

            risk = classify_risk(result["mass_pickup_ratio"])
            result["risk"] = risk

            cores_str = str(result["cores_dropped"]) if mode == "FULL" else "—"
            absorbed_str = f"{result['core_mass_absorbed']:.2f}" if mode == "FULL" else "—"

            print(f"  {depth:>6.2f} {mode:>10} "
                  f"{result['drift']:>8.2f} "
                  f"{result['mass_pickup_ratio']:>8.2f}x "
                  f"{result['peak_mass_ratio']:>8.2f}x "
                  f"{result['final_coherence']:>6.3f} "
                  f"{cores_str:>6} {absorbed_str:>10} "
                  f"{risk:>14}")

            depth_results[mode] = result

        all_results.append({
            "depth": depth,
            "lambda_at_center": round(void_lambda - depth, 4),
            "results": depth_results,
        })

        # Separator between depths
        if depth in [0.03, 0.06]:
            print(f"  {'─'*90}")

    # ── Boundary Analysis ──
    print(f"\n{'='*65}")
    print(f"  BOUNDARY ANALYSIS")
    print(f"{'='*65}")

    print(f"\n  SAFE boundary (mass pickup < 2x):")
    for entry in all_results:
        for mode in ["RAW", "CYCLING", "FULL"]:
            r = entry["results"][mode]
            if r["mass_pickup_ratio"] < 2.0:
                print(f"    depth={entry['depth']:.2f}  mode={mode:>10}  "
                      f"pickup={r['mass_pickup_ratio']:.2f}x  SAFE")

    print(f"\n  CAUTION boundary (2x-5x):")
    for entry in all_results:
        for mode in ["RAW", "CYCLING", "FULL"]:
            r = entry["results"][mode]
            if 2.0 <= r["mass_pickup_ratio"] < 5.0:
                print(f"    depth={entry['depth']:.2f}  mode={mode:>10}  "
                      f"pickup={r['mass_pickup_ratio']:.2f}x  CAUTION")

    print(f"\n  DANGER boundary (5x-10x):")
    for entry in all_results:
        for mode in ["RAW", "CYCLING", "FULL"]:
            r = entry["results"][mode]
            if 5.0 <= r["mass_pickup_ratio"] < 10.0:
                print(f"    depth={entry['depth']:.2f}  mode={mode:>10}  "
                      f"pickup={r['mass_pickup_ratio']:.2f}x  DANGER")

    print(f"\n  NO-GO boundary (>50x):")
    for entry in all_results:
        for mode in ["RAW", "CYCLING", "FULL"]:
            r = entry["results"][mode]
            if r["mass_pickup_ratio"] >= 50.0:
                print(f"    depth={entry['depth']:.2f}  mode={mode:>10}  "
                      f"pickup={r['mass_pickup_ratio']:.2f}x  NO-GO")

    # ── Countermeasure Effectiveness ──
    print(f"\n{'='*65}")
    print(f"  COUNTERMEASURE EFFECTIVENESS")
    print(f"{'='*65}")

    print(f"\n  {'Depth':>6} {'RAW':>10} {'CYCLING':>10} "
          f"{'FULL':>10} {'Cycling %':>10} {'Full %':>10}")
    print(f"  {'─'*6} {'─'*10} {'─'*10} {'─'*10} "
          f"{'─'*10} {'─'*10}")

    for entry in all_results:
        raw = entry["results"]["RAW"]["mass_pickup_ratio"]
        cyc = entry["results"]["CYCLING"]["mass_pickup_ratio"]
        full = entry["results"]["FULL"]["mass_pickup_ratio"]

        cyc_reduction = ((raw - cyc) / raw * 100) if raw > 0 else 0
        full_reduction = ((raw - full) / raw * 100) if raw > 0 else 0

        print(f"  {entry['depth']:>6.2f} {raw:>10.2f}x "
              f"{cyc:>10.2f}x {full:>10.2f}x "
              f"{cyc_reduction:>+9.1f}% {full_reduction:>+9.1f}%")

    # ── Final Verdict ──
    print(f"\n{'='*65}")
    print(f"  TRANSIT CLASSIFICATION")
    print(f"{'='*65}")

    for entry in all_results:
        depth = entry["depth"]
        full = entry["results"]["FULL"]
        risk = full["risk"]

        if risk == "SAFE":
            symbol = "GREEN"
        elif risk == "CAUTION":
            symbol = "YELLOW"
        elif risk == "DANGER":
            symbol = "ORANGE"
        elif risk == "STELLAR RISK":
            symbol = "RED"
        else:
            symbol = "BLACK"

        print(f"  depth={depth:.2f}  lambda_center={entry['lambda_at_center']:.4f}  "
              f"best_pickup={full['mass_pickup_ratio']:.2f}x  "
              f"[{symbol}] {risk}")

    print(f"\n  LEGEND:")
    print(f"    GREEN  = Navigable with standard governor")
    print(f"    YELLOW = Navigable with phase cycling")
    print(f"    ORANGE = Navigable with cycling + core-drop")
    print(f"    RED    = Hazardous — risk of structural loss")
    print(f"    BLACK  = Exclusion zone — ship becomes source")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v15_phase_governor_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v15 Phase-Cycling Governor & Core-Drop",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Find navigable/no-go boundary with countermeasures",
        "grid": nx,
        "steps": args.steps,
        "parameters": {
            "dt": dt, "D": D, "void_lambda": void_lambda,
            "pump_A": pump_A, "ratio": ratio,
            "alpha": alpha, "separation": separation,
            "exhaust_coupling": exhaust_coupling,
            "memory_radius": memory_radius,
            "cycle_length": 125,
        },
        "depths_tested": depths,
        "results": all_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
