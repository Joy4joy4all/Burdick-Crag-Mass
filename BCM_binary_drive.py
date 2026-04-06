# -*- coding: utf-8 -*-
"""
BCM v13 — Binary Pump Drive Test
===================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Everything in BCM is binary. The rigid body test failed
because it used a SINGLE pump. The ship is a binary
system: main pump A (reactor) + weak forward pump B
(fore ring exhaust) at 1:8 ratio.

B lowers local lambda AHEAD of the ship. A maintains
the ship. The bridge between them IS the drive corridor.

Tests:
  1. Single pump vs binary pump (deformable)
  2. Binary pump rigid body translation
  3. Pump ratio sweep (1:2 through 1:16)
  4. Separation sweep (how far ahead is pump B?)

Usage:
    python BCM_binary_drive.py
    python BCM_binary_drive.py --steps 2000 --grid 128
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
# TEST 1: SINGLE vs BINARY PUMP (deformable)
# ============================================================
def test_single_vs_binary(steps=2000, nx=128, ny=128,
                            dt=0.05, D=0.5,
                            pump_A=0.5, pump_B_ratio=0.125,
                            separation=15,
                            void_lambda=0.10):
    """
    Compare single pump (centered on ship) vs binary pump
    (A at ship + B projected forward at 1:8 ratio).
    Both in uniform void lambda. No external gradient.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 1: SINGLE vs BINARY PUMP")
    print(f"  {'='*60}")
    print(f"  Pump A = {pump_A}  Pump B = {pump_A * pump_B_ratio:.4f}")
    print(f"  B separation: {separation} px ahead")
    print(f"  Void lambda: {void_lambda}  NO external gradient")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    lam_field = np.full((nx, ny), void_lambda)
    pump_B = pump_A * pump_B_ratio

    configs = [
        ("SINGLE", False),
        ("BINARY", True),
    ]

    results = []

    for label, use_binary in configs:
        center = (nx // 3, ny // 2)
        r2 = (X - center[0])**2 + (Y - center[1])**2
        sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

        initial_com = compute_com(sigma)
        prev_com = initial_com.copy()
        speeds = []

        for step in range(steps):
            com = compute_com(sigma)
            if com is None:
                break

            # Pump A: at ship COM
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            # Pump B: projected ahead in +x direction
            if use_binary:
                bx = com[0] + separation
                by = com[1]
                r2_B = (X - bx)**2 + (Y - by)**2
                pB = pump_B * np.exp(-r2_B / (2 * 3.0**2))
                sigma += pB * dt

            # Evolve: diffusion + decay
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
            drift = float(np.linalg.norm(final_com - initial_com))
            coh = compute_coherence(sigma, final_com)
            peak = float(np.max(sigma))
        else:
            drift = 0
            coh = 0
            peak = 0

        mean_speed = float(np.mean(speeds)) if speeds else 0

        print(f"  {label:>8}: drift={drift:.4f}px  "
              f"speed={mean_speed:.8f}  peak={peak:.4f}  "
              f"coh={coh:.4f}")

        results.append({
            "label": label,
            "drift": round(drift, 6),
            "mean_speed": round(mean_speed, 10),
            "peak": round(peak, 4),
            "coherence": round(coh, 4),
        })

    if len(results) == 2:
        s_drift = results[0]["drift"]
        b_drift = results[1]["drift"]
        if s_drift > 0:
            ratio = b_drift / s_drift
            print(f"\n  Binary/Single drift ratio: {ratio:.2f}x")
        if b_drift > s_drift:
            print(f"  BINARY PUMP CREATES DIRECTIONAL TRANSPORT")
        elif b_drift < 0.01 and s_drift < 0.01:
            print(f"  Neither produced drift (expected in uniform field)")

    return results


# ============================================================
# TEST 2: BINARY PUMP WITH GRADIENT
# ============================================================
def test_binary_gradient(steps=2000, nx=128, ny=128,
                           dt=0.05, D=0.5,
                           pump_A=0.5, pump_B_ratio=0.125,
                           separation=15,
                           delta_lam=0.025,
                           void_lambda=0.10):
    """
    Binary pump in a lambda gradient field.
    Does the forward pump B amplify drift beyond what
    the gradient alone provides?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 2: BINARY PUMP + GRADIENT")
    print(f"  {'='*60}")
    print(f"  Pump A={pump_A}  B={pump_A*pump_B_ratio:.4f}")
    print(f"  Separation: {separation}px  Gradient: dl={delta_lam}")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    pump_B = pump_A * pump_B_ratio

    configs = [
        ("NO PUMP", 0, 0, False),
        ("SINGLE A", pump_A, 0, False),
        ("BINARY A+B", pump_A, pump_B, True),
    ]

    results = []

    for label, pA_str, pB_str, use_binary in configs:
        center = (nx // 3, ny // 2)
        r2 = (X - center[0])**2 + (Y - center[1])**2
        sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

        # Static gradient field
        lam_bg = np.full((nx, ny), void_lambda)
        proj = (X - center[0]) * 1.0
        drive = -delta_lam * np.tanh(proj / 6.0)
        lam_field = np.maximum(lam_bg + drive, 0.005)

        initial_com = compute_com(sigma)
        prev_com = initial_com.copy()
        speeds = []

        for step in range(steps):
            com = compute_com(sigma)
            if com is None:
                break

            # Pump A
            if pA_str > 0:
                r2_A = (X - com[0])**2 + (Y - com[1])**2
                pA = pA_str * np.exp(-r2_A / (2 * 4.0**2))
                sigma += pA * dt

            # Pump B (forward)
            if use_binary:
                bx = com[0] + separation
                by = com[1]
                r2_B = (X - bx)**2 + (Y - by)**2
                pB = pB_str * np.exp(-r2_B / (2 * 3.0**2))
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
            drift = float(np.linalg.norm(final_com - initial_com))
            peak = float(np.max(sigma))
        else:
            drift = 0
            peak = 0

        mean_speed = float(np.mean(speeds)) if speeds else 0

        print(f"  {label:>12}: drift={drift:.4f}px  "
              f"speed={mean_speed:.8f}  peak={peak:.4f}")

        results.append({
            "label": label,
            "drift": round(drift, 6),
            "mean_speed": round(mean_speed, 10),
            "peak": round(peak, 4),
        })

    return results


# ============================================================
# TEST 3: PUMP RATIO SWEEP
# ============================================================
def test_ratio_sweep(steps=1500, nx=128, ny=128,
                       dt=0.05, D=0.5,
                       pump_A=0.5, separation=15,
                       void_lambda=0.10):
    """
    Sweep B/A ratio from 1:2 to 1:16.
    No external gradient — only the binary pump asymmetry.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 3: PUMP RATIO SWEEP (no external gradient)")
    print(f"  {'='*60}")
    print(f"  Pump A={pump_A}  Separation={separation}px")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    lam_field = np.full((nx, ny), void_lambda)

    ratios = [0.5, 0.25, 0.125, 0.0625, 0.03125, 0.0]
    results = []

    print(f"  {'B/A':>8} {'B_power':>10} {'Drift':>10} "
          f"{'Speed':>12} {'Peak':>8}")
    print(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*12} {'─'*8}")

    for ratio in ratios:
        center = (nx // 3, ny // 2)
        r2 = (X - center[0])**2 + (Y - center[1])**2
        sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

        initial_com = compute_com(sigma)
        pump_B = pump_A * ratio
        speeds = []

        for step in range(steps):
            com = compute_com(sigma)
            if com is None:
                break

            # Pump A
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            # Pump B (forward)
            if ratio > 0:
                bx = com[0] + separation
                by = com[1]
                r2_B = (X - bx)**2 + (Y - by)**2
                pB = pump_B * np.exp(-r2_B / (2 * 3.0**2))
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
                speeds.append(float(np.linalg.norm(new_com - com)))

        final_com = compute_com(sigma)
        drift = 0
        peak = 0
        if final_com is not None and initial_com is not None:
            drift = float(np.linalg.norm(final_com - initial_com))
            peak = float(np.max(sigma))

        mean_speed = float(np.mean(speeds)) if speeds else 0

        print(f"  {ratio:>8.4f} {pump_B:>10.4f} {drift:>10.4f} "
              f"{mean_speed:>12.8f} {peak:>8.4f}")

        results.append({
            "ratio": ratio,
            "pump_B": round(pump_B, 4),
            "drift": round(drift, 6),
            "mean_speed": round(mean_speed, 10),
            "peak": round(peak, 4),
        })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 Binary Pump Drive Test")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v13 BINARY PUMP DRIVE TEST")
    print(f"  Everything in BCM is binary.")
    print(f"  Main pump A + forward pump B at 1:8 ratio.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")

    all_results = {}

    # Test 1: Single vs binary (no gradient)
    r1 = test_single_vs_binary(steps=args.steps, nx=nx, ny=ny)
    all_results["single_vs_binary"] = r1

    # Test 2: Binary + gradient
    r2 = test_binary_gradient(steps=args.steps, nx=nx, ny=ny)
    all_results["binary_gradient"] = r2

    # Test 3: Ratio sweep
    r3 = test_ratio_sweep(steps=min(1500, args.steps),
                           nx=nx, ny=ny)
    all_results["ratio_sweep"] = r3

    # Summary
    print(f"\n{'='*65}")
    print(f"  BINARY PUMP SUMMARY")
    print(f"{'='*65}")

    if len(r1) == 2:
        print(f"  Single pump drift:  {r1[0]['drift']:.4f} px")
        print(f"  Binary pump drift:  {r1[1]['drift']:.4f} px")

    if len(r2) == 3:
        print(f"  No pump + gradient: {r2[0]['drift']:.4f} px")
        print(f"  Single + gradient:  {r2[1]['drift']:.4f} px")
        print(f"  Binary + gradient:  {r2[2]['drift']:.4f} px")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_binary_drive_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 Binary Pump Drive Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Binary pump topology — everything in BCM is binary",
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
