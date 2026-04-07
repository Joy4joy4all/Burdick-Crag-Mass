# -*- coding: utf-8 -*-
"""
BCM v14 — Dual Pump Stability & Transport Matrix
====================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

ChatGPT test matrix for dual pump craft parameters.
Beat on it until we have safe, useful transit.

Phase A: Fine alpha sweep at bifurcation (0.70-0.90)
Phase B: Memory decay curve (gamma fitting)
Phase C: Dual pump with frequency/phase control
Phase D: Transport metric definition and measurement

Usage:
    python BCM_dual_pump_matrix.py
    python BCM_dual_pump_matrix.py --steps 1200 --grid 128
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


def run_memory_test(steps, nx, ny, dt, D, pump_A, ratio,
                     separation, void_lambda, alpha,
                     pump_on_steps, oscillate_B=False,
                     B_frequency=0.0, B_phase=0.0):
    """
    Core runner: binary pump with memory term.
    Optional: oscillating pump B for frequency/phase tests.
    Returns on-speed, off-speed, retention, drift, decay curve.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    lam_field = np.full((nx, ny), void_lambda)
    pump_B_base = pump_A * ratio

    initial_com = compute_com(sigma)
    speeds_on = []
    speeds_off = []
    decay_curve = []  # (step_after_off, speed)

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        pumps_active = step < pump_on_steps

        if pumps_active:
            # Pump A
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            # Pump B (optionally oscillating)
            bx = com[0] + separation
            r2_B = (X - bx)**2 + (Y - com[1])**2

            if oscillate_B and B_frequency > 0:
                B_amp = pump_B_base * (0.5 + 0.5 * np.sin(
                    2 * np.pi * B_frequency * step * dt + B_phase))
            else:
                B_amp = pump_B_base

            pB = B_amp * np.exp(-r2_B / (2 * 3.0**2))
            sigma += pB * dt

        # Evolve
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma_new = (sigma + D * laplacian * dt
                      - lam_field * sigma * dt)

        # Memory term
        if alpha > 0:
            sigma_new = sigma_new + alpha * (sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)

        # Blowup check
        if float(np.max(sigma_new)) > 1e10:
            return {
                "stable": False, "blowup_step": step,
                "alpha": alpha,
            }

        sigma_prev = sigma.copy()
        sigma = sigma_new

        new_com = compute_com(sigma)
        if new_com is not None and com is not None:
            speed = float(np.linalg.norm(new_com - com))
            if pumps_active:
                speeds_on.append(speed)
            else:
                speeds_off.append(speed)
                decay_curve.append((step - pump_on_steps, speed))

    final_com = compute_com(sigma)
    drift = 0
    if final_com is not None and initial_com is not None:
        drift = float(np.linalg.norm(final_com - initial_com))

    avg_on = float(np.mean(speeds_on)) if speeds_on else 0
    avg_off = float(np.mean(speeds_off)) if speeds_off else 0
    retention = avg_off / avg_on if avg_on > 0 else 0

    # Fit decay: find half-life of off-speed
    half_life = None
    if decay_curve and decay_curve[0][1] > 0:
        initial_off_speed = decay_curve[0][1]
        for step_off, spd in decay_curve:
            if spd < initial_off_speed * 0.5:
                half_life = step_off
                break

    # Transport metric: net directed displacement
    J = sum(speeds_off)  # total displacement after pumps off

    return {
        "stable": True,
        "alpha": alpha,
        "avg_on": round(avg_on, 12),
        "avg_off": round(avg_off, 12),
        "retention": round(retention, 8),
        "drift": round(drift, 6),
        "half_life": half_life,
        "transport_J": round(J, 8),
        "decay_samples": len(decay_curve),
    }


# ============================================================
# PHASE A: FINE ALPHA SWEEP AT BIFURCATION
# ============================================================
def phase_A_fine_sweep(steps=1200, nx=128, ny=128,
                        dt=0.05, D=0.5, pump_A=0.5,
                        ratio=0.125, separation=15,
                        void_lambda=0.10,
                        pump_on_steps=300):
    """
    Fine sweep alpha = 0.70 to 0.90 in 0.01 steps.
    Map the stability boundary precisely.
    """
    print(f"\n  {'='*60}")
    print(f"  PHASE A: FINE ALPHA SWEEP (bifurcation zone)")
    print(f"  {'='*60}")
    print(f"  Alpha 0.70 to 0.90, step 0.01")
    print(f"  {'─'*60}")

    alphas = [round(0.70 + i * 0.01, 2) for i in range(21)]
    results = []

    print(f"  {'Alpha':>8} {'Retention%':>12} {'Off Speed':>14} "
          f"{'Half-life':>10} {'J_transport':>12} {'Status':>8}")
    print(f"  {'─'*8} {'─'*12} {'─'*14} {'─'*10} {'─'*12} "
          f"{'─'*8}")

    for alpha in alphas:
        r = run_memory_test(steps, nx, ny, dt, D, pump_A,
                             ratio, separation, void_lambda,
                             alpha, pump_on_steps)

        if not r.get("stable", True):
            print(f"  {alpha:>8.2f} {'---':>12} {'---':>14} "
                  f"{'---':>10} {'---':>12} {'BLOWUP':>8}")
            results.append({"alpha": alpha, "stable": False})
            continue

        hl = str(r["half_life"]) if r["half_life"] else ">900"
        status = "RETAIN" if r["retention"] > 0.01 else "LOST"

        print(f"  {alpha:>8.2f} {r['retention']*100:>11.4f}% "
              f"{r['avg_off']:>14.10f} {hl:>10} "
              f"{r['transport_J']:>12.8f} {status:>8}")

        results.append(r)

    # Find precise threshold
    retained = [r for r in results
                if r.get("stable") and r.get("retention", 0) > 0.01]
    if retained:
        threshold = min(retained, key=lambda r: r["alpha"])
        print(f"\n  PRECISE THRESHOLD: alpha = {threshold['alpha']}")
        print(f"  Retention: {threshold['retention']*100:.4f}%")
    else:
        print(f"\n  No retention in sweep range.")

    # Find blowup boundary
    blowups = [r for r in results if not r.get("stable", True)]
    if blowups:
        first_blow = min(blowups, key=lambda r: r["alpha"])
        print(f"  BLOWUP BOUNDARY: alpha = {first_blow['alpha']}")

    return results


# ============================================================
# PHASE B: MEMORY DECAY CURVE
# ============================================================
def phase_B_decay_curve(steps=2000, nx=128, ny=128,
                          dt=0.05, D=0.5, pump_A=0.5,
                          ratio=0.125, separation=15,
                          void_lambda=0.10,
                          pump_on_steps=400):
    """
    At alpha=0.80 (threshold), measure the EXACT decay
    curve after pumps stop. Fit exponential.
    """
    print(f"\n  {'='*60}")
    print(f"  PHASE B: MEMORY DECAY CURVE (alpha=0.80)")
    print(f"  {'='*60}")
    print(f"  Pumps ON 400 steps, OFF 1600 steps.")
    print(f"  Track speed decay. Fit gamma.")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    lam_field = np.full((nx, ny), void_lambda)
    pump_B = pump_A * ratio
    alpha = 0.80

    decay_speeds = []
    prev_com = compute_com(sigma)

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        if step < pump_on_steps:
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
                      - lam_field * sigma * dt
                      + alpha * (sigma - sigma_prev))
        sigma_new = np.maximum(sigma_new, 0)

        if float(np.max(sigma_new)) > 1e10:
            print(f"  BLOWUP at step {step}")
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        new_com = compute_com(sigma)
        if new_com is not None and prev_com is not None:
            speed = float(np.linalg.norm(new_com - prev_com))
            if step >= pump_on_steps:
                decay_speeds.append({
                    "step_off": step - pump_on_steps,
                    "speed": round(speed, 14),
                })
        prev_com = new_com

    # Fit exponential: speed ~ A * exp(-gamma * t)
    if len(decay_speeds) > 10:
        steps_arr = np.array([d["step_off"] for d in decay_speeds])
        speed_arr = np.array([d["speed"] for d in decay_speeds])

        # Log-linear fit for gamma
        pos_mask = speed_arr > 1e-15
        if np.sum(pos_mask) > 10:
            log_speed = np.log(speed_arr[pos_mask])
            steps_pos = steps_arr[pos_mask]

            # Simple linear regression on log(speed) vs step
            n = len(steps_pos)
            sx = np.sum(steps_pos)
            sy = np.sum(log_speed)
            sxx = np.sum(steps_pos**2)
            sxy = np.sum(steps_pos * log_speed)

            denom = n * sxx - sx**2
            if abs(denom) > 1e-15:
                gamma = -(n * sxy - sx * sy) / denom
                A = np.exp((sy + gamma * sx) / n)
                half_life = np.log(2) / gamma if gamma > 0 else float('inf')

                print(f"  Decay fit: speed ~ {A:.6f} * exp(-{gamma:.6f} * t)")
                print(f"  Gamma (decay rate): {gamma:.6f}")
                print(f"  Half-life: {half_life:.1f} steps")

                # Sample the decay curve
                print(f"\n  {'Step_off':>10} {'Speed':>14} {'Fitted':>14}")
                for d in decay_speeds[::100]:
                    fitted = A * np.exp(-gamma * d["step_off"])
                    print(f"  {d['step_off']:>10} {d['speed']:>14.10f} "
                          f"{fitted:>14.10f}")

                return {
                    "gamma": round(gamma, 8),
                    "A": round(A, 8),
                    "half_life": round(half_life, 2),
                    "n_samples": len(decay_speeds),
                }

    print(f"  Insufficient data for fit.")
    return {"gamma": None, "n_samples": len(decay_speeds)}


# ============================================================
# PHASE C: DUAL PUMP FREQUENCY/PHASE INTERACTION
# ============================================================
def phase_C_dual_pump(steps=1200, nx=128, ny=128,
                        dt=0.05, D=0.5, pump_A=0.5,
                        ratio=0.125, separation=15,
                        void_lambda=0.10, alpha=0.80,
                        pump_on_steps=1200):
    """
    Introduce oscillating pump B. Sweep frequency and phase.
    Look for resonance peaks and transport enhancement.
    """
    print(f"\n  {'='*60}")
    print(f"  PHASE C: DUAL PUMP FREQUENCY/PHASE SWEEP")
    print(f"  {'='*60}")
    print(f"  Pump B oscillates. Sweep frequency and phase.")
    print(f"  Alpha={alpha}. Look for resonance.")
    print(f"  {'─'*60}")

    # Frequency sweep (phase=0)
    print(f"\n  --- FREQUENCY SWEEP (phase=0) ---")
    freqs = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05,
             0.10, 0.20, 0.50, 1.0]
    freq_results = []

    print(f"  {'Freq':>8} {'Drift':>10} {'Speed':>12} "
          f"{'J_transport':>12} {'Status':>8}")
    print(f"  {'─'*8} {'─'*10} {'─'*12} {'─'*12} {'─'*8}")

    for freq in freqs:
        r = run_memory_test(steps, nx, ny, dt, D, pump_A,
                             ratio, separation, void_lambda,
                             alpha, pump_on_steps,
                             oscillate_B=freq > 0,
                             B_frequency=freq)

        if not r.get("stable", True):
            print(f"  {freq:>8.3f} {'BLOWUP':>10}")
            freq_results.append({"freq": freq, "stable": False})
            continue

        print(f"  {freq:>8.3f} {r['drift']:>10.4f} "
              f"{r['avg_on']:>12.8f} "
              f"{r.get('transport_J',0):>12.8f} "
              f"{'OK' if r['stable'] else 'FAIL':>8}")

        r["freq"] = freq
        freq_results.append(r)

    # Find resonance peak (max drift)
    valid_freq = [r for r in freq_results if r.get("stable")]
    if valid_freq:
        best = max(valid_freq, key=lambda r: r.get("drift", 0))
        print(f"\n  PEAK DRIFT at freq={best.get('freq', 0):.3f}: "
              f"{best.get('drift',0):.4f} px")

    # Phase sweep (at best frequency)
    best_freq = best.get("freq", 0.01) if valid_freq else 0.01
    print(f"\n  --- PHASE SWEEP (freq={best_freq}) ---")
    phases = [0, np.pi/4, np.pi/2, 3*np.pi/4,
              np.pi, 5*np.pi/4, 3*np.pi/2, 7*np.pi/4]
    phase_results = []

    print(f"  {'Phase':>8} {'Drift':>10} {'Speed':>12}")
    print(f"  {'─'*8} {'─'*10} {'─'*12}")

    for phase in phases:
        r = run_memory_test(steps, nx, ny, dt, D, pump_A,
                             ratio, separation, void_lambda,
                             alpha, pump_on_steps,
                             oscillate_B=True,
                             B_frequency=best_freq,
                             B_phase=phase)

        if not r.get("stable", True):
            continue

        deg = int(np.degrees(phase))
        print(f"  {deg:>7}d {r['drift']:>10.4f} "
              f"{r['avg_on']:>12.8f}")

        r["phase_deg"] = deg
        phase_results.append(r)

    return {
        "frequency_sweep": freq_results,
        "phase_sweep": phase_results,
        "best_frequency": best_freq,
    }


# ============================================================
# PHASE D: OPERATING ENVELOPE SUMMARY
# ============================================================
def phase_D_envelope(alpha_results, decay_result,
                       dual_pump_results):
    """
    Compile the operating envelope from all phases.
    """
    print(f"\n  {'='*60}")
    print(f"  PHASE D: OPERATING ENVELOPE")
    print(f"  {'='*60}")

    # Alpha bounds
    stable = [r for r in alpha_results
              if r.get("stable", True)]
    retained = [r for r in stable
                if r.get("retention", 0) > 0.01]
    blowups = [r for r in alpha_results
               if not r.get("stable", True)]

    alpha_min = retained[0]["alpha"] if retained else None
    alpha_max = blowups[0]["alpha"] if blowups else None

    print(f"  Memory coefficient (alpha):")
    print(f"    Minimum for retention: {alpha_min}")
    print(f"    Maximum before blowup: {alpha_max}")
    if alpha_min and alpha_max:
        print(f"    Operating band: {alpha_min} to {alpha_max}")
        print(f"    Band width: {alpha_max - alpha_min:.2f}")

    # Decay rate
    if decay_result.get("gamma"):
        print(f"\n  Memory decay:")
        print(f"    Gamma: {decay_result['gamma']}")
        print(f"    Half-life: {decay_result['half_life']} steps")

    # Best frequency
    freq_data = dual_pump_results.get("frequency_sweep", [])
    valid = [r for r in freq_data if r.get("stable") and r.get("drift", 0) > 0]
    if valid:
        best = max(valid, key=lambda r: r.get("drift", 0))
        print(f"\n  Optimal pump B frequency: {best.get('freq', 0)}")
        print(f"    Drift at optimum: {best.get('drift', 0):.4f}")

    print(f"\n  {'='*60}")
    print(f"  OPERATING ENVELOPE DEFINED")
    print(f"  {'='*60}")

    return {
        "alpha_min": alpha_min,
        "alpha_max": alpha_max,
        "gamma": decay_result.get("gamma"),
        "half_life": decay_result.get("half_life"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v14 Dual Pump Stability Matrix")
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v14 — DUAL PUMP STABILITY & TRANSPORT MATRIX")
    print(f"  Beat on it until we have safe useful transit.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")

    all_results = {}

    # Phase A
    rA = phase_A_fine_sweep(steps=args.steps, nx=nx, ny=ny)
    all_results["phase_A"] = rA

    # Phase B
    rB = phase_B_decay_curve(steps=min(2000, args.steps + 800),
                               nx=nx, ny=ny)
    all_results["phase_B"] = rB

    # Phase C
    rC = phase_C_dual_pump(steps=args.steps, nx=nx, ny=ny)
    all_results["phase_C"] = rC

    # Phase D
    rD = phase_D_envelope(rA, rB, rC)
    all_results["phase_D"] = rD

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_dual_pump_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v14 Dual Pump Stability & Transport Matrix",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Define safe operating envelope for dual pump craft",
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
