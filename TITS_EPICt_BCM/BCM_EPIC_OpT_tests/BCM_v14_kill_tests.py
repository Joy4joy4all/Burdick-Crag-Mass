# -*- coding: utf-8 -*-
"""
BCM v14 — ChatGPT Kill Tests (Round 2)
=========================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

ChatGPT's four kill conditions for the binary drive:

  1. PUMPS OFF: Initialize with pumps, then turn them off.
     Does drift continue without injection? If no, transport
     is injected, not intrinsic.

  2. MASS NORMALIZE: Remove growth bias by normalizing total
     mass (sum of sigma) every step. If drift vanishes,
     it was growth-driven, not transport-driven.

  3. FREEZE COM: Don't let pumps follow the COM. Fixed
     pump positions. If drift vanishes, transport requires
     nonlinear feedback — it's self-reinforcing, not passive.

  4. CONTINUOUS LIMIT: Grid 64/128/256/512. Does drift
     converge or diverge? If it diverges, it's a grid
     artifact. If it converges, it's real.

Usage:
    python BCM_v14_kill_tests.py
    python BCM_v14_kill_tests.py --steps 1500 --grid 128
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


# ============================================================
# TEST 1: PUMPS OFF AFTER INITIALIZATION
# ============================================================
def test_pumps_off(steps=1500, nx=128, ny=128,
                    dt=0.05, D=0.5, pump_A=0.5,
                    ratio=0.125, separation=15,
                    void_lambda=0.10,
                    pump_on_steps=200):
    """
    Run pumps for pump_on_steps to establish the packet.
    Then turn pumps OFF. Does drift continue?

    Three phases:
    A) Pumps ON (0 to pump_on_steps): establish structure
    B) Pumps OFF (pump_on_steps to end): intrinsic transport?
    C) Comparison: drift rate A vs drift rate B
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 1: PUMPS OFF AFTER INITIALIZATION")
    print(f"  {'='*60}")
    print(f"  Pumps ON for {pump_on_steps} steps, then OFF.")
    print(f"  Does drift continue without injection?")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    lam_field = np.full((nx, ny), void_lambda)
    pump_B = pump_A * ratio

    initial_com = compute_com(sigma)
    prev_com = initial_com.copy()

    phase_a_drifts = []
    phase_b_drifts = []
    com_at_switch = None
    E_at_switch = None

    print(f"  {'Step':>6} {'Phase':>6} {'COM_x':>8} {'Drift':>10} "
          f"{'E_total':>10} {'Speed':>10}")
    print(f"  {'─'*6} {'─'*6} {'─'*8} {'─'*10} {'─'*10} {'─'*10}")

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            print(f"  DISSOLVED at step {step}")
            break

        pumps_active = step < pump_on_steps

        if pumps_active:
            # Pump A at COM
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            # Pump B forward
            bx = com[0] + separation
            r2_B = (X - bx)**2 + (Y - com[1])**2
            pB = pump_B * np.exp(-r2_B / (2 * 3.0**2))
            sigma += pB * dt

        # Record switch point
        if step == pump_on_steps:
            com_at_switch = com.copy()
            E_at_switch = float(np.sum(sigma**2))
            print(f"  >>> PUMPS OFF at step {step} <<<")

        # Evolve
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt
        sigma -= lam_field * sigma * dt
        sigma = np.maximum(sigma, 0)

        new_com = compute_com(sigma)
        if new_com is not None and prev_com is not None:
            speed = float(np.linalg.norm(new_com - prev_com))
            if pumps_active:
                phase_a_drifts.append(speed)
            else:
                phase_b_drifts.append(speed)

            if step % 100 == 0:
                drift = float(np.linalg.norm(new_com - initial_com))
                E = float(np.sum(sigma**2))
                phase = "ON" if pumps_active else "OFF"
                print(f"  {step:>6} {phase:>6} {new_com[0]:>8.2f} "
                      f"{drift:>10.4f} {E:>10.4f} {speed:>10.6f}")

        prev_com = new_com

    # Analysis
    avg_a = float(np.mean(phase_a_drifts)) if phase_a_drifts else 0
    avg_b = float(np.mean(phase_b_drifts)) if phase_b_drifts else 0

    total_drift_a = sum(phase_a_drifts)
    total_drift_b = sum(phase_b_drifts)

    print(f"\n  RESULTS:")
    print(f"    Phase A (pumps ON):  avg speed={avg_a:.8f}  "
          f"total drift={total_drift_a:.4f}")
    print(f"    Phase B (pumps OFF): avg speed={avg_b:.8f}  "
          f"total drift={total_drift_b:.4f}")

    if avg_a > 0:
        retention = avg_b / avg_a
        print(f"    Speed retention: {retention*100:.1f}%")
    else:
        retention = 0

    if avg_b > avg_a * 0.1:
        print(f"\n    DRIFT CONTINUES after pumps off.")
        print(f"    Transport has intrinsic component.")
    elif avg_b > 0.0001:
        print(f"\n    RESIDUAL drift after pumps off.")
        print(f"    Decaying but not zero.")
    else:
        print(f"\n    DRIFT STOPS when pumps stop.")
        print(f"    Transport is purely injected.")

    return {
        "avg_speed_on": round(avg_a, 10),
        "avg_speed_off": round(avg_b, 10),
        "total_drift_on": round(total_drift_a, 6),
        "total_drift_off": round(total_drift_b, 6),
        "speed_retention": round(retention, 6),
        "pump_on_steps": pump_on_steps,
    }


# ============================================================
# TEST 2: MASS NORMALIZATION (remove growth bias)
# ============================================================
def test_mass_normalize(steps=1500, nx=128, ny=128,
                          dt=0.05, D=0.5, pump_A=0.5,
                          ratio=0.125, separation=15,
                          void_lambda=0.10):
    """
    Normalize TOTAL MASS (sum of sigma, not sigma^2)
    every step. Removes growth bias.
    If drift vanishes: transport was growth-driven.
    If drift persists: transport survives mass conservation.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 2: MASS NORMALIZATION (growth bias removed)")
    print(f"  {'='*60}")
    print(f"  sum(sigma) held constant. Pumps still shape field.")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    lam_field = np.full((nx, ny), void_lambda)
    pump_B = pump_A * ratio
    M_ref = float(np.sum(sigma))

    initial_com = compute_com(sigma)
    speeds = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        # Pump A
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        # Pump B
        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        # Evolve
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt
        sigma -= lam_field * sigma * dt
        sigma = np.maximum(sigma, 0)

        # MASS NORMALIZE — remove growth bias
        M_current = float(np.sum(sigma))
        if M_current > 1e-15:
            sigma *= (M_ref / M_current)

        new_com = compute_com(sigma)
        if new_com is not None and com is not None:
            speeds.append(float(np.linalg.norm(new_com - com)))

    final_com = compute_com(sigma)
    if final_com is not None:
        drift = float(np.linalg.norm(final_com - initial_com))
    else:
        drift = 0

    mean_speed = float(np.mean(speeds)) if speeds else 0

    # Run WITHOUT normalization for comparison
    sigma2 = 1.0 * np.exp(-r2 / (2 * 5.0**2))
    initial_com2 = compute_com(sigma2)
    speeds2 = []

    for step in range(steps):
        com = compute_com(sigma2)
        if com is None:
            break

        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma2 += pA * dt
        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma2 += pB * dt

        laplacian = (
            np.roll(sigma2, 1, axis=0) +
            np.roll(sigma2, -1, axis=0) +
            np.roll(sigma2, 1, axis=1) +
            np.roll(sigma2, -1, axis=1) -
            4 * sigma2
        )
        sigma2 += D * laplacian * dt
        sigma2 -= lam_field * sigma2 * dt
        sigma2 = np.maximum(sigma2, 0)

        new_com = compute_com(sigma2)
        if new_com is not None and com is not None:
            speeds2.append(float(np.linalg.norm(new_com - com)))

    final_com2 = compute_com(sigma2)
    drift2 = float(np.linalg.norm(
        final_com2 - initial_com2)) if final_com2 is not None else 0

    print(f"  With mass normalization:    drift={drift:.4f}  "
          f"speed={mean_speed:.8f}")
    print(f"  Without normalization:      drift={drift2:.4f}  "
          f"speed={np.mean(speeds2) if speeds2 else 0:.8f}")

    if drift > drift2 * 0.5:
        print(f"\n  DRIFT SURVIVES mass normalization.")
        print(f"  Transport is NOT growth-driven.")
    elif drift > 0.1:
        print(f"\n  DRIFT REDUCED but present.")
        print(f"  Growth contributes but is not sole driver.")
    else:
        print(f"\n  DRIFT VANISHES under mass normalization.")
        print(f"  Transport was growth-driven.")

    return {
        "drift_normalized": round(drift, 6),
        "drift_free": round(drift2, 6),
        "speed_normalized": round(mean_speed, 10),
        "speed_free": round(float(np.mean(speeds2)) if speeds2 else 0, 10),
        "ratio": round(drift / drift2, 4) if drift2 > 0 else 0,
    }


# ============================================================
# TEST 3: FREEZE COM (no feedback)
# ============================================================
def test_freeze_com(steps=1500, nx=128, ny=128,
                      dt=0.05, D=0.5, pump_A=0.5,
                      ratio=0.125, separation=15,
                      void_lambda=0.10):
    """
    Pumps stay at FIXED positions. They do NOT follow
    the COM. If drift vanishes: self-reinforcing feedback
    is required. If drift persists: transport is passive.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 3: FREEZE COM (no pump feedback)")
    print(f"  {'='*60}")
    print(f"  Pumps stay at initial position. No tracking.")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    lam_field = np.full((nx, ny), void_lambda)
    pump_B_val = pump_A * ratio

    initial_com = compute_com(sigma)

    # Fixed pump positions (never move)
    fixed_A = np.array(center, dtype=float)
    fixed_B = np.array([center[0] + separation, center[1]],
                        dtype=float)

    speeds_fixed = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        # Pumps at FIXED positions
        r2_A = (X - fixed_A[0])**2 + (Y - fixed_A[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        r2_B = (X - fixed_B[0])**2 + (Y - fixed_B[1])**2
        pB = pump_B_val * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt
        sigma -= lam_field * sigma * dt
        sigma = np.maximum(sigma, 0)

        new_com = compute_com(sigma)
        if new_com is not None and com is not None:
            speeds_fixed.append(float(np.linalg.norm(new_com - com)))

    final_com = compute_com(sigma)
    drift_fixed = 0
    if final_com is not None:
        drift_fixed = float(np.linalg.norm(final_com - initial_com))

    # Run WITH feedback for comparison
    sigma2 = 1.0 * np.exp(-r2 / (2 * 5.0**2))
    initial_com2 = compute_com(sigma2)
    speeds_track = []

    for step in range(steps):
        com = compute_com(sigma2)
        if com is None:
            break

        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma2 += pA * dt
        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_B_val * np.exp(-r2_B / (2 * 3.0**2))
        sigma2 += pB * dt

        laplacian = (
            np.roll(sigma2, 1, axis=0) +
            np.roll(sigma2, -1, axis=0) +
            np.roll(sigma2, 1, axis=1) +
            np.roll(sigma2, -1, axis=1) -
            4 * sigma2
        )
        sigma2 += D * laplacian * dt
        sigma2 -= lam_field * sigma2 * dt
        sigma2 = np.maximum(sigma2, 0)

        new_com = compute_com(sigma2)
        if new_com is not None and com is not None:
            speeds_track.append(float(np.linalg.norm(new_com - com)))

    final_com2 = compute_com(sigma2)
    drift_track = float(np.linalg.norm(
        final_com2 - initial_com2)) if final_com2 is not None else 0

    print(f"  Fixed pumps (no feedback): drift={drift_fixed:.4f}")
    print(f"  Tracking pumps (feedback): drift={drift_track:.4f}")

    if drift_fixed > drift_track * 0.5:
        print(f"\n  DRIFT SURVIVES without feedback.")
        print(f"  Transport does not require self-reinforcement.")
    elif drift_fixed > 0.1:
        print(f"\n  DRIFT REDUCED without feedback.")
        print(f"  Feedback amplifies but is not sole driver.")
    else:
        print(f"\n  DRIFT REQUIRES FEEDBACK.")
        print(f"  Transport is self-reinforcing.")

    return {
        "drift_fixed": round(drift_fixed, 6),
        "drift_tracking": round(drift_track, 6),
        "ratio": round(drift_fixed / drift_track, 4) if drift_track > 0 else 0,
    }


# ============================================================
# TEST 4: CONTINUOUS LIMIT (grid convergence)
# ============================================================
def test_continuous_limit(steps_time=75.0, dt=0.05, D=0.5,
                            pump_A=0.5, ratio=0.125,
                            void_lambda=0.10):
    """
    Same scenario at grid 64, 128, 256, 512.
    Same total simulation time. Separation scales with grid.
    Does drift CONVERGE to a value (real) or DIVERGE (artifact)?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 4: CONTINUOUS LIMIT (grid convergence)")
    print(f"  {'='*60}")
    print(f"  Same physics, different resolution.")
    print(f"  Drift must converge, not diverge.")
    print(f"  {'─'*60}")

    grids = [64, 128, 256]
    results = []
    steps = int(steps_time / dt)

    print(f"  {'Grid':>6} {'Sep':>6} {'Steps':>8} {'Drift':>10} "
          f"{'Speed':>12} {'Coh':>8} {'Peak':>8}")
    print(f"  {'─'*6} {'─'*6} {'─'*8} {'─'*10} {'─'*12} "
          f"{'─'*8} {'─'*8}")

    for nx in grids:
        ny = nx
        # Scale separation proportionally
        sep = int(15 * nx / 128)

        x = np.arange(nx)
        y = np.arange(ny)
        X, Y = np.meshgrid(x, y, indexing='ij')

        center = (nx // 3, ny // 2)
        r2 = (X - center[0])**2 + (Y - center[1])**2
        # Scale packet width
        pw = 5.0 * nx / 128
        sigma = 1.0 * np.exp(-r2 / (2 * pw**2))

        lam_field = np.full((nx, ny), void_lambda)
        pump_B = pump_A * ratio

        initial_com = compute_com(sigma)
        speeds = []
        prev_com = initial_com.copy()

        for step in range(steps):
            com = compute_com(sigma)
            if com is None:
                break

            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA_w = 4.0 * nx / 128
            pA = pump_A * np.exp(-r2_A / (2 * pA_w**2))
            sigma += pA * dt

            bx = com[0] + sep
            r2_B = (X - bx)**2 + (Y - com[1])**2
            pB_w = 3.0 * nx / 128
            pB = pump_B * np.exp(-r2_B / (2 * pB_w**2))
            sigma += pB * dt

            laplacian = (
                np.roll(sigma, 1, axis=0) +
                np.roll(sigma, -1, axis=0) +
                np.roll(sigma, 1, axis=1) +
                np.roll(sigma, -1, axis=1) -
                4 * sigma
            )
            sigma += D * laplacian * dt
            sigma -= lam_field * sigma * dt
            sigma = np.maximum(sigma, 0)

            new_com = compute_com(sigma)
            if new_com is not None and prev_com is not None:
                speeds.append(float(np.linalg.norm(new_com - prev_com)))
            prev_com = new_com

        final_com = compute_com(sigma)
        if final_com is not None:
            # Normalize drift to grid units (fraction of grid)
            drift_px = float(np.linalg.norm(final_com - initial_com))
            drift_frac = drift_px / nx  # fraction of grid size
            coh = compute_coherence(sigma, final_com)
            peak = float(np.max(sigma))
        else:
            drift_px = 0
            drift_frac = 0
            coh = 0
            peak = 0

        mean_speed = float(np.mean(speeds)) if speeds else 0
        speed_frac = mean_speed / nx

        print(f"  {nx:>6} {sep:>6} {steps:>8} "
              f"{drift_frac:>10.6f} {speed_frac:>12.10f} "
              f"{coh:>8.4f} {peak:>8.4f}")

        results.append({
            "grid": nx,
            "separation": sep,
            "drift_px": round(drift_px, 4),
            "drift_frac": round(drift_frac, 8),
            "speed_frac": round(speed_frac, 12),
            "coherence": round(coh, 4),
            "peak": round(peak, 4),
        })

    # Convergence check
    fracs = [r["drift_frac"] for r in results]
    if len(fracs) >= 2:
        changes = []
        for i in range(len(fracs) - 1):
            if fracs[i] > 0:
                change = abs(fracs[i+1] - fracs[i]) / fracs[i]
                changes.append(change)

        print(f"\n  CONVERGENCE CHECK (drift as fraction of grid):")
        for i, r in enumerate(results):
            print(f"    Grid {r['grid']:>4}: {r['drift_frac']:.8f}")

        if changes:
            last_change = changes[-1]
            print(f"  Last change: {last_change*100:.2f}%")

            if last_change < 0.10:
                print(f"  CONVERGING — drift stabilizes with resolution")
            elif last_change < 0.25:
                print(f"  MARGINAL — approaching convergence")
            else:
                print(f"  NOT CONVERGING — possible grid artifact")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="BCM v14 ChatGPT Kill Tests Round 2")
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v14 — CHATGPT KILL TESTS (ROUND 2)")
    print(f"  Four conditions for the binary drive")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")

    all_results = {}

    r1 = test_pumps_off(steps=args.steps, nx=nx, ny=ny)
    all_results["pumps_off"] = r1

    r2 = test_mass_normalize(steps=args.steps, nx=nx, ny=ny)
    all_results["mass_normalize"] = r2

    r3 = test_freeze_com(steps=args.steps, nx=nx, ny=ny)
    all_results["freeze_com"] = r3

    r4 = test_continuous_limit()
    all_results["continuous_limit"] = r4

    # Summary
    print(f"\n{'='*65}")
    print(f"  KILL TEST SUMMARY")
    print(f"{'='*65}")
    print(f"  Pumps off retention:  "
          f"{r1['speed_retention']*100:.1f}%")
    print(f"  Mass norm drift ratio: "
          f"{r2['ratio']:.4f} "
          f"(1.0 = no effect)")
    print(f"  Freeze COM drift ratio: "
          f"{r3['ratio']:.4f} "
          f"(1.0 = no feedback needed)")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v14_kill_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v14 ChatGPT Kill Tests Round 2",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Four adversarial conditions for binary drive",
        "grid": nx,
        "steps": args.steps,
        "results": all_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
