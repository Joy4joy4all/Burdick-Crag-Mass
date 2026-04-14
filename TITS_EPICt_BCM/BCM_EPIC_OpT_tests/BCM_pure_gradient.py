# -*- coding: utf-8 -*-
"""
BCM v13 — Pure Gradient Isolation Tests
==========================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

ChatGPT caught the normalization as a hidden pump.
He's right. These tests strip EVERYTHING:

  A. No pump. No normalization. Raw diffusion + gradient.
     Does COM shift BEFORE dissolution?
  B. Symmetric initial condition + gradient.
     Does asymmetry emerge ONLY from lambda?
  C. Energy vs displacement curve.
     Is drift transient or sustained?
  D. Gradient sweep at raw (no injection).
     Does v still scale with nabla_lambda?

No tricks. No hidden pumps. No rescaling. Pure PDE.

Usage:
    python BCM_pure_gradient.py
    python BCM_pure_gradient.py --steps 2000 --grid 128
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


def raw_evolve(sigma, lam_field, D, dt):
    """Pure PDE step. No pump. No normalization. Nothing hidden."""
    laplacian = (
        np.roll(sigma, 1, axis=0) +
        np.roll(sigma, -1, axis=0) +
        np.roll(sigma, 1, axis=1) +
        np.roll(sigma, -1, axis=1) -
        4 * sigma
    )
    sigma = sigma + D * laplacian * dt - lam_field * sigma * dt
    return np.maximum(sigma, 0)


# ============================================================
# TEST A: RAW DRIFT — NO PUMP, NO NORMALIZATION
# ============================================================
def test_raw_drift(steps=2000, nx=128, ny=128,
                    dt=0.05, D=0.5, delta_lam=0.025,
                    void_lambda=0.10):
    """
    Pure diffusion + lambda gradient. Nothing else.
    Track COM every step. Track energy every step.
    Does COM shift WHILE energy is still high?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST A: RAW DRIFT (no pump, no normalization)")
    print(f"  {'='*60}")
    print(f"  Pure PDE: d_sigma/dt = D*laplacian - lambda*sigma")
    print(f"  delta_lam={delta_lam}  void_lam={void_lambda}")
    print(f"  {'─'*60}")

    center = (nx // 2, ny // 2)
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    # Static lambda field with gradient
    lam_bg = np.full((nx, ny), void_lambda)
    d_vec = np.array([1.0, 0.0])
    proj = (X - center[0]) * d_vec[0] + (Y - center[1]) * d_vec[1]
    drive = -delta_lam * np.tanh(proj / 6.0)
    lam_field = np.maximum(lam_bg + drive, 0.005)

    initial_com = compute_com(sigma)
    E_initial = float(np.sum(sigma**2))

    # Track every step
    com_log = []
    E_log = []
    drift_log = []

    print(f"  {'Step':>6} {'E_total':>12} {'E_pct':>8} "
          f"{'COM_x':>10} {'Drift':>10} {'Speed':>10}")
    print(f"  {'─'*6} {'─'*12} {'─'*8} {'─'*10} {'─'*10} "
          f"{'─'*10}")

    for step in range(steps):
        sigma = raw_evolve(sigma, lam_field, D, dt)

        com = compute_com(sigma)
        E = float(np.sum(sigma**2))
        E_log.append(E)

        if com is not None:
            com_log.append(com.copy())
            drift = float(np.linalg.norm(com - initial_com))
            drift_log.append(drift)
        else:
            com_log.append(None)
            drift_log.append(drift_log[-1] if drift_log else 0)
            if step < 100:
                print(f"  DISSOLVED at step {step}")
            break

        if step % 100 == 0 or step < 20 or (step < 200 and step % 20 == 0):
            E_pct = (E / E_initial) * 100
            speed = 0
            if len(com_log) > 1 and com_log[-2] is not None:
                speed = float(np.linalg.norm(com - com_log[-2]))
            print(f"  {step:>6} {E:>12.6f} {E_pct:>7.2f}% "
                  f"{com[0]:>10.4f} {drift:>10.6f} "
                  f"{speed:>10.6f}")

    # Analysis: when did drift happen relative to energy?
    print(f"\n  DRIFT TIMELINE ANALYSIS:")

    # Early drift (first 10% of energy life)
    alive_steps = len([e for e in E_log if e > E_initial * 0.01])
    early_cutoff = max(1, alive_steps // 10)
    early_drift = drift_log[min(early_cutoff, len(drift_log)-1)]

    # Mid drift (50% energy)
    mid_cutoff = max(1, alive_steps // 2)
    mid_drift = drift_log[min(mid_cutoff, len(drift_log)-1)]

    # Total drift
    total_drift = drift_log[-1] if drift_log else 0

    print(f"    Alive steps: {alive_steps}")
    print(f"    Early drift (10% life): {early_drift:.6f} px "
          f"at step {early_cutoff}")
    print(f"    Mid drift (50% life):   {mid_drift:.6f} px "
          f"at step {mid_cutoff}")
    print(f"    Total drift:            {total_drift:.6f} px")

    if early_drift > 0.01:
        print(f"\n    DRIFT OCCURS WHILE ENERGY IS HIGH.")
        print(f"    Not a dissolution artifact.")
    else:
        print(f"\n    Drift may be dissolution-driven.")

    return {
        "delta_lam": delta_lam,
        "alive_steps": alive_steps,
        "early_drift": round(early_drift, 6),
        "mid_drift": round(mid_drift, 6),
        "total_drift": round(total_drift, 6),
        "E_initial": round(E_initial, 6),
        "E_at_10pct": round(E_log[min(early_cutoff, len(E_log)-1)], 6),
        "E_at_50pct": round(E_log[min(mid_cutoff, len(E_log)-1)], 6),
    }


# ============================================================
# TEST B: SYMMETRIC INITIAL + GRADIENT
# ============================================================
def test_symmetric(steps=1000, nx=128, ny=128,
                    dt=0.05, D=0.5, delta_lam=0.025,
                    void_lambda=0.10):
    """
    Perfectly symmetric initial sigma at grid center.
    Apply asymmetric lambda field.
    Does COM move? If yes: lambda alone creates transport.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST B: SYMMETRIC INITIAL + GRADIENT")
    print(f"  {'='*60}")
    print(f"  Perfect Gaussian at center. Lambda gradient applied.")
    print(f"  Does symmetry break ONLY from lambda?")
    print(f"  {'─'*60}")

    center = (nx // 2, ny // 2)
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    # Verify symmetry
    com_0 = compute_com(sigma)
    print(f"  Initial COM: ({com_0[0]:.6f}, {com_0[1]:.6f})")
    print(f"  Center: ({center[0]}, {center[1]})")
    print(f"  Offset: {np.linalg.norm(com_0 - np.array(center)):.10f}")

    # Lambda field: gradient in +x
    lam_bg = np.full((nx, ny), void_lambda)
    proj = (X - center[0]) * 1.0
    drive = -delta_lam * np.tanh(proj / 6.0)
    lam_field = np.maximum(lam_bg + drive, 0.005)

    # Also run control: symmetric lambda (no gradient)
    lam_flat = np.full((nx, ny), void_lambda)

    # Gradient run
    sigma_grad = sigma.copy()
    grad_coms = []
    for step in range(steps):
        sigma_grad = raw_evolve(sigma_grad, lam_field, D, dt)
        com = compute_com(sigma_grad)
        if com is None:
            break
        grad_coms.append(com.copy())

    # Flat run (control)
    sigma_flat = sigma.copy()
    flat_coms = []
    for step in range(steps):
        sigma_flat = raw_evolve(sigma_flat, lam_flat, D, dt)
        com = compute_com(sigma_flat)
        if com is None:
            break
        flat_coms.append(com.copy())

    grad_drift = 0
    flat_drift = 0
    if grad_coms:
        grad_drift = float(np.linalg.norm(
            grad_coms[-1] - np.array(center)))
    if flat_coms:
        flat_drift = float(np.linalg.norm(
            flat_coms[-1] - np.array(center)))

    print(f"\n  Results:")
    print(f"    With gradient: COM drift = {grad_drift:.6f} px")
    print(f"    No gradient:   COM drift = {flat_drift:.6f} px")
    print(f"    Gradient steps survived: {len(grad_coms)}")
    print(f"    Flat steps survived: {len(flat_coms)}")

    if grad_drift > flat_drift * 10 and grad_drift > 0.01:
        print(f"\n    SYMMETRY BROKEN BY LAMBDA ALONE.")
        print(f"    Gradient is the sole cause of transport.")
    elif grad_drift > flat_drift:
        print(f"\n    Gradient contributes but may not be sole cause.")
    else:
        print(f"\n    No measurable gradient effect on symmetry.")

    return {
        "grad_drift": round(grad_drift, 6),
        "flat_drift": round(flat_drift, 6),
        "grad_steps": len(grad_coms),
        "flat_steps": len(flat_coms),
    }


# ============================================================
# TEST C: ENERGY vs DISPLACEMENT CURVE
# ============================================================
def test_energy_displacement(steps=2000, nx=128, ny=128,
                               dt=0.05, D=0.5,
                               delta_lam=0.025,
                               void_lambda=0.10):
    """
    Track cumulative drift vs cumulative energy loss.
    Plot the relationship. Is it linear? Proportional?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST C: ENERGY vs DISPLACEMENT CURVE")
    print(f"  {'='*60}")

    center = (nx // 2, ny // 2)
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    lam_bg = np.full((nx, ny), void_lambda)
    proj = (X - center[0]) * 1.0
    drive = -delta_lam * np.tanh(proj / 6.0)
    lam_field = np.maximum(lam_bg + drive, 0.005)

    E_initial = float(np.sum(sigma**2))
    cum_drift = 0
    prev_com = compute_com(sigma)
    curve = []

    for step in range(steps):
        E_before = float(np.sum(sigma**2))
        sigma = raw_evolve(sigma, lam_field, D, dt)
        E_after = float(np.sum(sigma**2))

        com = compute_com(sigma)
        if com is None:
            break

        if prev_com is not None:
            cum_drift += float(np.linalg.norm(com - prev_com))
        prev_com = com

        cum_E_lost = E_initial - E_after

        if step % 50 == 0:
            curve.append({
                "step": step,
                "cum_drift": round(cum_drift, 6),
                "cum_E_lost": round(cum_E_lost, 6),
                "E_remaining": round(E_after, 6),
                "E_pct": round((E_after / E_initial) * 100, 2),
            })

    print(f"  {'Step':>6} {'Drift':>10} {'E_lost':>12} "
          f"{'E_remain':>12} {'E%':>8}")
    print(f"  {'─'*6} {'─'*10} {'─'*12} {'─'*12} {'─'*8}")
    for c in curve[:20]:
        print(f"  {c['step']:>6} {c['cum_drift']:>10.4f} "
              f"{c['cum_E_lost']:>12.4f} "
              f"{c['E_remaining']:>12.4f} "
              f"{c['E_pct']:>7.2f}%")

    # Drift per unit energy lost
    if len(curve) > 2:
        efficiencies = []
        for i in range(1, len(curve)):
            dE = curve[i]["cum_E_lost"] - curve[i-1]["cum_E_lost"]
            dd = curve[i]["cum_drift"] - curve[i-1]["cum_drift"]
            if dE > 0:
                efficiencies.append(dd / dE)

        if efficiencies:
            print(f"\n  Drift per E_lost (efficiency):")
            print(f"    Mean:  {np.mean(efficiencies):.8f}")
            print(f"    Std:   {np.std(efficiencies):.8f}")
            cv = np.std(efficiencies) / np.mean(efficiencies) if np.mean(efficiencies) > 0 else 0
            print(f"    CV:    {cv:.4f}")
            if cv < 0.20:
                print(f"    CONSTANT efficiency — drift ~ E_lost")
            else:
                print(f"    Variable efficiency — nonlinear coupling")

    return curve


# ============================================================
# TEST D: RAW GRADIENT SWEEP (no injection)
# ============================================================
def test_raw_sweep(steps=1000, nx=128, ny=128,
                    dt=0.05, D=0.5, void_lambda=0.10):
    """
    Sweep gradient at raw (no pump, no normalization).
    Does v still scale with nabla_lambda?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST D: RAW GRADIENT SWEEP")
    print(f"  {'='*60}")
    print(f"  No pump. No normalization. Pure PDE.")
    print(f"  {'─'*60}")

    deltas = [0.000, 0.005, 0.010, 0.025, 0.050, 0.075, 0.100]
    results = []

    print(f"  {'dl':>8} {'Drift':>10} {'Alive':>8} "
          f"{'E_end':>12} {'Ratio':>10}")
    print(f"  {'─'*8} {'─'*10} {'─'*8} {'─'*12} {'─'*10}")

    for dl in deltas:
        center = (nx // 2, ny // 2)
        x = np.arange(nx)
        y = np.arange(ny)
        X, Y = np.meshgrid(x, y, indexing='ij')

        r2 = (X - center[0])**2 + (Y - center[1])**2
        sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

        lam_bg = np.full((nx, ny), void_lambda)
        proj = (X - center[0]) * 1.0
        drive = -dl * np.tanh(proj / 6.0)
        lam_field = np.maximum(lam_bg + drive, 0.005)

        initial_com = compute_com(sigma)
        alive = 0

        for step in range(steps):
            sigma = raw_evolve(sigma, lam_field, D, dt)
            com = compute_com(sigma)
            if com is None:
                break
            alive = step + 1

        final_com = compute_com(sigma)
        E_end = float(np.sum(sigma**2))

        if final_com is not None and initial_com is not None:
            drift = float(np.linalg.norm(final_com - initial_com))
        else:
            drift = 0

        ratio = drift / dl if dl > 0 else 0

        print(f"  {dl:>8.3f} {drift:>10.6f} {alive:>8} "
              f"{E_end:>12.8f} {ratio:>10.2f}")

        results.append({
            "delta_lam": dl,
            "drift": round(drift, 6),
            "alive_steps": alive,
            "E_final": round(E_end, 8),
            "drift_per_dl": round(ratio, 4),
        })

    # Linearity check
    non_zero = [r for r in results if r["delta_lam"] > 0]
    if len(non_zero) > 1:
        ratios = [r["drift_per_dl"] for r in non_zero]
        cv = np.std(ratios) / np.mean(ratios) if np.mean(ratios) > 0 else 0
        print(f"\n  Drift/gradient ratio CV: {cv:.4f}")
        if cv < 0.15:
            print(f"  v ~ nabla_lambda CONFIRMED (raw, no injection)")
        elif cv < 0.30:
            print(f"  Approximately linear")
        else:
            print(f"  Nonlinear regime")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 Pure Gradient Isolation Tests")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v13 PURE GRADIENT ISOLATION TESTS")
    print(f"  ChatGPT's Clean Kill Conditions")
    print(f"  No pump. No normalization. No hidden energy.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")

    all_results = {}

    # Test A
    rA = test_raw_drift(steps=args.steps, nx=nx, ny=ny)
    all_results["raw_drift"] = rA

    # Test B
    rB = test_symmetric(steps=min(1000, args.steps), nx=nx, ny=ny)
    all_results["symmetric"] = rB

    # Test C
    rC = test_energy_displacement(steps=args.steps, nx=nx, ny=ny)
    all_results["energy_displacement"] = rC

    # Test D
    rD = test_raw_sweep(steps=min(1000, args.steps), nx=nx, ny=ny)
    all_results["raw_sweep"] = rD

    # Summary
    print(f"\n{'='*65}")
    print(f"  PURE GRADIENT SUMMARY")
    print(f"{'='*65}")
    print(f"  Raw drift (no pump, no norm): "
          f"{rA['total_drift']:.6f} px")
    print(f"  Early drift (10% life):       "
          f"{rA['early_drift']:.6f} px")
    print(f"  Symmetric test: gradient drift="
          f"{rB['grad_drift']:.6f} vs flat="
          f"{rB['flat_drift']:.6f}")

    print(f"\n  THE FINAL QUESTION:")
    if rA['early_drift'] > 0.01:
        print(f"  DRIFT OCCURS WHILE ENERGY IS HIGH.")
        print(f"  Transport begins before dissolution.")
        print(f"  The gradient moves the structure.")
    if rB['grad_drift'] > rB['flat_drift'] * 10:
        print(f"  SYMMETRY BROKEN BY LAMBDA ALONE.")
        print(f"  No other asymmetry source exists.")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_pure_gradient_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 Pure Gradient Isolation Tests",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "ChatGPT clean kill conditions — no hidden energy",
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
