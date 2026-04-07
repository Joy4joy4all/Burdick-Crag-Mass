# -*- coding: utf-8 -*-
"""
BCM v14 — Lagrange Equilibrium Scanner
=========================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

ChatGPT designed the gate (Kill Test 1: no memory).
ChatGPT designed the lockpick (Lagrange scan + memory).

Find zero-velocity structures in the sigma field.
Test their stability. Test persistence after pumps stop.
Introduce lagged response (memory term) and re-test.

If ONE stable equilibrium persists without pumps,
Kill Test 1 is broken.

Usage:
    python BCM_lagrange_scan.py
    python BCM_lagrange_scan.py --steps 1500 --grid 128
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


def compute_velocity_field(sigma, lam_field, D, dt):
    """
    Extract the instantaneous velocity field from the PDE.
    V(x,y) = where would sigma move if it were concentrated
    at each point? This is the effective drift tendency.
    """
    nx, ny = sigma.shape

    # Gradient of sigma (flow tendency from diffusion)
    grad_sig_x = (np.roll(sigma, -1, axis=0) -
                   np.roll(sigma, 1, axis=0)) / 2.0
    grad_sig_y = (np.roll(sigma, -1, axis=1) -
                   np.roll(sigma, 1, axis=1)) / 2.0

    # Gradient of lambda (decay asymmetry)
    grad_lam_x = (np.roll(lam_field, -1, axis=0) -
                   np.roll(lam_field, 1, axis=0)) / 2.0
    grad_lam_y = (np.roll(lam_field, -1, axis=1) -
                   np.roll(lam_field, 1, axis=1)) / 2.0

    # Effective velocity: combination of diffusive flow
    # and decay-gradient bias
    # V ~ -D * grad(sigma)/sigma - sigma * grad(lambda)
    safe_sigma = np.maximum(sigma, 1e-15)

    Vx = -D * grad_sig_x / safe_sigma - sigma * grad_lam_x
    Vy = -D * grad_sig_y / safe_sigma - sigma * grad_lam_y

    return Vx, Vy


def find_equilibria(Vx, Vy, sigma, epsilon=1e-4,
                      min_sigma=1e-6):
    """
    Find grid cells where |V| < epsilon AND sigma > min_sigma.
    These are candidate equilibrium points.
    """
    speed = np.sqrt(Vx**2 + Vy**2)
    candidates = []

    nx, ny = sigma.shape
    for i in range(2, nx - 2):
        for j in range(2, ny - 2):
            if speed[i, j] < epsilon and sigma[i, j] > min_sigma:
                candidates.append({
                    "x": i, "y": j,
                    "speed": float(speed[i, j]),
                    "sigma": float(sigma[i, j]),
                })

    return candidates


def test_stability(sigma, lam_field, point, D, dt,
                    n_steps=200, nudge=0.5):
    """
    Perturb sigma near the candidate point and evolve.
    If COM returns toward point: STABLE.
    If COM diverges: UNSTABLE.
    """
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Create a small perturbation packet near the point
    px, py = point["x"], point["y"]
    r2 = (X - (px + nudge))**2 + (Y - py)**2
    test_sigma = sigma.copy()
    test_sigma += 0.1 * np.exp(-r2 / (2 * 2.0**2))

    initial_dist = nudge
    distances = [initial_dist]

    for step in range(n_steps):
        laplacian = (
            np.roll(test_sigma, 1, axis=0) +
            np.roll(test_sigma, -1, axis=0) +
            np.roll(test_sigma, 1, axis=1) +
            np.roll(test_sigma, -1, axis=1) -
            4 * test_sigma
        )
        test_sigma += D * laplacian * dt
        test_sigma -= lam_field * test_sigma * dt
        test_sigma = np.maximum(test_sigma, 0)

        com = compute_com(test_sigma)
        if com is None:
            return "DISSOLVED", distances

        dist = np.sqrt((com[0] - px)**2 + (com[1] - py)**2)
        distances.append(float(dist))

    # Classify
    final_dist = distances[-1]
    if final_dist < initial_dist * 0.5:
        return "STABLE", distances
    elif final_dist > initial_dist * 2.0:
        return "UNSTABLE", distances
    else:
        return "NEUTRAL", distances


# ============================================================
# TEST 1: BASELINE LAGRANGE SCAN (with pumps)
# ============================================================
def test_baseline_scan(steps=1000, nx=128, ny=128,
                        dt=0.05, D=0.5, pump_A=0.5,
                        ratio=0.125, separation=15,
                        void_lambda=0.10):
    """
    Run binary pump to steady state. Scan for equilibria.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 1: BASELINE LAGRANGE SCAN (pumps ON)")
    print(f"  {'='*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    lam_field = np.full((nx, ny), void_lambda)
    pump_B = pump_A * ratio

    # Run to steady state
    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
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

    # Extract velocity field
    Vx, Vy = compute_velocity_field(sigma, lam_field, D, dt)

    # Find equilibria
    candidates = find_equilibria(Vx, Vy, sigma, epsilon=1e-3)

    print(f"  Found {len(candidates)} equilibrium candidates")
    for i, c in enumerate(candidates[:10]):
        print(f"    [{i}] ({c['x']},{c['y']}) "
              f"speed={c['speed']:.6f} sigma={c['sigma']:.6f}")

    # Test stability of top candidates
    stable_count = 0
    for c in candidates[:5]:
        stability, dists = test_stability(
            sigma, lam_field, c, D, dt)
        print(f"    ({c['x']},{c['y']}): {stability}")
        if stability == "STABLE":
            stable_count += 1

    print(f"\n  Stable equilibria: {stable_count}/{min(5, len(candidates))}")

    return {
        "n_candidates": len(candidates),
        "stable_count": stable_count,
        "candidates": candidates[:10],
        "sigma_state": sigma,
        "lam_field": lam_field,
    }


# ============================================================
# TEST 2: PUMPS OFF — DO EQUILIBRIA PERSIST?
# ============================================================
def test_pumps_off_scan(sigma, lam_field, steps=500,
                          nx=128, ny=128, dt=0.05, D=0.5):
    """
    Take the steady-state sigma from Test 1.
    Turn pumps off. Let evolve. Re-scan for equilibria.
    Do any persist?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 2: PUMPS OFF — DO EQUILIBRIA PERSIST?")
    print(f"  {'='*60}")

    sigma_off = sigma.copy()

    # Evolve WITHOUT pumps
    for step in range(steps):
        laplacian = (
            np.roll(sigma_off, 1, axis=0) +
            np.roll(sigma_off, -1, axis=0) +
            np.roll(sigma_off, 1, axis=1) +
            np.roll(sigma_off, -1, axis=1) -
            4 * sigma_off
        )
        sigma_off += D * laplacian * dt
        sigma_off -= lam_field * sigma_off * dt
        sigma_off = np.maximum(sigma_off, 0)

    # Re-scan
    Vx, Vy = compute_velocity_field(sigma_off, lam_field, D, dt)
    candidates = find_equilibria(Vx, Vy, sigma_off,
                                   epsilon=1e-3, min_sigma=1e-8)

    E_remaining = float(np.sum(sigma_off**2))
    print(f"  After {steps} steps without pumps:")
    print(f"    E remaining: {E_remaining:.8f}")
    print(f"    Equilibria found: {len(candidates)}")

    if candidates:
        print(f"    EQUILIBRIA PERSIST WITHOUT PUMPS")
        for c in candidates[:5]:
            print(f"      ({c['x']},{c['y']}) "
                  f"speed={c['speed']:.8f} "
                  f"sigma={c['sigma']:.8f}")
    else:
        print(f"    No equilibria found — field dissolved")

    return {
        "n_candidates": len(candidates),
        "E_remaining": round(E_remaining, 10),
        "candidates": candidates[:10],
        "persisted": len(candidates) > 0,
    }


# ============================================================
# TEST 3: MEMORY TERM — BREAK KILL TEST 1
# ============================================================
def test_memory_term(steps=1500, nx=128, ny=128,
                       dt=0.05, D=0.5, pump_A=0.5,
                       ratio=0.125, separation=15,
                       void_lambda=0.10,
                       alpha=0.3, pump_on_steps=300):
    """
    ChatGPT's lockpick: add a lagged response term.

    sigma_new = f(sigma_t) + alpha * f(sigma_{t-1})

    This gives the substrate MEMORY. The field remembers
    where it was, not just where it is. After pumps stop,
    the memory term maintains structure.

    Run with pumps ON for pump_on_steps, then OFF.
    Compare drift retention WITH and WITHOUT memory.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 3: MEMORY TERM (alpha={alpha})")
    print(f"  {'='*60}")
    print(f"  Pumps ON for {pump_on_steps}, then OFF.")
    print(f"  Does memory term retain drift?")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    lam_field = np.full((nx, ny), void_lambda)
    pump_B = pump_A * ratio

    # Run WITH memory
    center = (nx // 3, ny // 2)
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    initial_com = compute_com(sigma)
    speeds_on_mem = []
    speeds_off_mem = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        pumps_active = step < pump_on_steps

        if pumps_active:
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt
            bx = com[0] + separation
            r2_B = (X - bx)**2 + (Y - com[1])**2
            pB = pump_B * np.exp(-r2_B / (2 * 3.0**2))
            sigma += pB * dt

        # Standard evolution
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma_new = (sigma + D * laplacian * dt
                      - lam_field * sigma * dt)

        # MEMORY TERM: blend with previous state
        sigma_new = sigma_new + alpha * (sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)
        sigma_prev = sigma.copy()
        sigma = sigma_new

        new_com = compute_com(sigma)
        if new_com is not None and com is not None:
            speed = float(np.linalg.norm(new_com - com))
            if pumps_active:
                speeds_on_mem.append(speed)
            else:
                speeds_off_mem.append(speed)

    drift_mem = 0
    final_com = compute_com(sigma)
    if final_com is not None and initial_com is not None:
        drift_mem = float(np.linalg.norm(final_com - initial_com))

    # Run WITHOUT memory (baseline)
    sigma2 = 1.0 * np.exp(-r2 / (2 * 5.0**2))
    initial_com2 = compute_com(sigma2)
    speeds_on_base = []
    speeds_off_base = []

    for step in range(steps):
        com = compute_com(sigma2)
        if com is None:
            break

        pumps_active = step < pump_on_steps

        if pumps_active:
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
        sigma2 = sigma2 + D * laplacian * dt - lam_field * sigma2 * dt
        sigma2 = np.maximum(sigma2, 0)

        new_com = compute_com(sigma2)
        if new_com is not None and com is not None:
            speed = float(np.linalg.norm(new_com - com))
            if pumps_active:
                speeds_on_base.append(speed)
            else:
                speeds_off_base.append(speed)

    drift_base = 0
    final_com2 = compute_com(sigma2)
    if final_com2 is not None and initial_com2 is not None:
        drift_base = float(np.linalg.norm(final_com2 - initial_com2))

    # Analysis
    avg_off_mem = float(np.mean(speeds_off_mem)) if speeds_off_mem else 0
    avg_off_base = float(np.mean(speeds_off_base)) if speeds_off_base else 0
    avg_on_mem = float(np.mean(speeds_on_mem)) if speeds_on_mem else 0
    avg_on_base = float(np.mean(speeds_on_base)) if speeds_on_base else 0

    retention_mem = avg_off_mem / avg_on_mem if avg_on_mem > 0 else 0
    retention_base = avg_off_base / avg_on_base if avg_on_base > 0 else 0

    print(f"  {'':>20} {'With Memory':>14} {'Baseline':>14}")
    print(f"  {'─'*20} {'─'*14} {'─'*14}")
    print(f"  {'Speed (pumps ON)':>20} {avg_on_mem:>14.8f} "
          f"{avg_on_base:>14.8f}")
    print(f"  {'Speed (pumps OFF)':>20} {avg_off_mem:>14.8f} "
          f"{avg_off_base:>14.8f}")
    print(f"  {'Retention':>20} {retention_mem*100:>13.4f}% "
          f"{retention_base*100:>13.4f}%")
    print(f"  {'Total drift':>20} {drift_mem:>14.4f} "
          f"{drift_base:>14.4f}")

    if retention_mem > retention_base * 10:
        print(f"\n  MEMORY TERM RETAINS TRANSPORT.")
        print(f"  Kill Test 1 retention increased by "
              f"{retention_mem/max(retention_base,1e-10):.0f}x")
    elif retention_mem > retention_base * 2:
        print(f"\n  MEMORY TERM PARTIALLY RETAINS TRANSPORT.")
    else:
        print(f"\n  MEMORY TERM DID NOT BREAK KILL TEST 1.")

    return {
        "alpha": alpha,
        "retention_memory": round(retention_mem, 8),
        "retention_baseline": round(retention_base, 8),
        "drift_memory": round(drift_mem, 6),
        "drift_baseline": round(drift_base, 6),
        "avg_off_memory": round(avg_off_mem, 10),
        "avg_off_baseline": round(avg_off_base, 10),
    }


# ============================================================
# TEST 4: MEMORY ALPHA SWEEP
# ============================================================
def test_alpha_sweep(steps=1200, nx=128, ny=128,
                       dt=0.05, D=0.5, pump_A=0.5,
                       ratio=0.125, separation=15,
                       void_lambda=0.10,
                       pump_on_steps=300):
    """
    Sweep alpha (memory coefficient) from 0 to 0.9.
    Find the minimum alpha that gives measurable retention.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 4: MEMORY ALPHA SWEEP")
    print(f"  {'='*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    lam_field = np.full((nx, ny), void_lambda)
    pump_B = pump_A * ratio

    alphas = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30,
              0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
    results = []

    print(f"  {'Alpha':>8} {'Retention':>12} {'Off Speed':>14} "
          f"{'Total Drift':>12} {'Status':>10}")
    print(f"  {'─'*8} {'─'*12} {'─'*14} {'─'*12} {'─'*10}")

    for alpha in alphas:
        center = (nx // 3, ny // 2)
        r2 = (X - center[0])**2 + (Y - center[1])**2
        sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))
        sigma_prev = sigma.copy()

        initial_com = compute_com(sigma)
        speeds_on = []
        speeds_off = []

        stable = True
        for step in range(steps):
            com = compute_com(sigma)
            if com is None:
                stable = False
                break

            pumps_active = step < pump_on_steps

            if pumps_active:
                r2_A = (X - com[0])**2 + (Y - com[1])**2
                pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
                sigma += pA * dt
                bx = com[0] + separation
                r2_B = (X - bx)**2 + (Y - com[1])**2
                pB = pump_B * np.exp(-r2_B / (2 * 3.0**2))
                sigma += pB * dt

            laplacian = (
                np.roll(sigma, 1, axis=0) +
                np.roll(sigma, -1, axis=0) +
                np.roll(sigma, 1, axis=1) +
                np.roll(sigma, -1, axis=1) -
                4 * sigma
            )
            sigma_new = (sigma + D * laplacian * dt
                          - lam_field * sigma * dt)

            if alpha > 0:
                sigma_new = sigma_new + alpha * (sigma - sigma_prev)

            sigma_new = np.maximum(sigma_new, 0)

            # Check for blowup
            if float(np.max(sigma_new)) > 1e10:
                stable = False
                break

            sigma_prev = sigma.copy()
            sigma = sigma_new

            new_com = compute_com(sigma)
            if new_com is not None and com is not None:
                speed = float(np.linalg.norm(new_com - com))
                if pumps_active:
                    speeds_on.append(speed)
                else:
                    speeds_off.append(speed)

        avg_on = float(np.mean(speeds_on)) if speeds_on else 0
        avg_off = float(np.mean(speeds_off)) if speeds_off else 0
        retention = avg_off / avg_on if avg_on > 0 else 0

        final_com = compute_com(sigma)
        drift = 0
        if final_com is not None and initial_com is not None:
            drift = float(np.linalg.norm(final_com - initial_com))

        if not stable:
            status = "BLOWUP"
        elif retention > 0.01:
            status = "RETAINED"
        else:
            status = "LOST"

        print(f"  {alpha:>8.2f} {retention*100:>11.4f}% "
              f"{avg_off:>14.10f} {drift:>12.4f} {status:>10}")

        results.append({
            "alpha": alpha,
            "retention": round(retention, 8),
            "avg_off": round(avg_off, 12),
            "drift": round(drift, 6),
            "stable": stable,
            "status": status,
        })

    # Find threshold
    retained = [r for r in results
                if r["status"] == "RETAINED" and r["stable"]]
    if retained:
        threshold = min(retained, key=lambda r: r["alpha"])
        print(f"\n  MEMORY THRESHOLD: alpha = {threshold['alpha']}")
        print(f"    Retention: {threshold['retention']*100:.4f}%")
    else:
        print(f"\n  NO ALPHA PRODUCED RETENTION.")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="BCM v14 Lagrange Equilibrium Scanner")
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v14 — LAGRANGE EQUILIBRIUM SCANNER")
    print(f"  Find zero-velocity structures. Test persistence.")
    print(f"  Break Kill Test 1 with memory.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")

    all_results = {}

    # Test 1: Baseline scan
    r1 = test_baseline_scan(steps=min(1000, args.steps),
                              nx=nx, ny=ny)
    all_results["baseline_scan"] = {
        "n_candidates": r1["n_candidates"],
        "stable_count": r1["stable_count"],
        "candidates": r1["candidates"],
    }

    # Test 2: Pumps off persistence
    r2 = test_pumps_off_scan(r1["sigma_state"], r1["lam_field"],
                               steps=500, nx=nx, ny=ny)
    all_results["pumps_off_scan"] = r2

    # Test 3: Memory term
    r3 = test_memory_term(steps=args.steps, nx=nx, ny=ny,
                            alpha=0.3)
    all_results["memory_term"] = r3

    # Test 4: Alpha sweep
    r4 = test_alpha_sweep(steps=min(1200, args.steps),
                            nx=nx, ny=ny)
    all_results["alpha_sweep"] = r4

    # Summary
    print(f"\n{'='*65}")
    print(f"  LAGRANGE SCAN SUMMARY")
    print(f"{'='*65}")
    print(f"  Equilibria with pumps:    {r1['n_candidates']}")
    print(f"  Stable with pumps:       {r1['stable_count']}")
    print(f"  Persist without pumps:   "
          f"{'YES' if r2['persisted'] else 'NO'}")
    print(f"  Memory retention (a=0.3): "
          f"{r3['retention_memory']*100:.4f}%")
    print(f"  Baseline retention:      "
          f"{r3['retention_baseline']*100:.4f}%")

    retained = [r for r in r4
                if r["status"] == "RETAINED" and r["stable"]]
    if retained:
        print(f"  Memory threshold alpha:  "
              f"{retained[0]['alpha']}")
        print(f"\n  KILL TEST 1 STATUS: BREAKABLE")
    else:
        print(f"\n  KILL TEST 1 STATUS: HOLDS")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_lagrange_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v14 Lagrange Equilibrium Scanner",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Break Kill Test 1 — find persistent structure",
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
