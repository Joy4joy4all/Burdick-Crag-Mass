# -*- coding: utf-8 -*-
"""
BCM v15 — Test E Raw (Governor Stripped)
==========================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The first Test E run showed negative V-F correlation
(-0.70). The governor was hiding the coupling by
maintaining constant velocity across all conditions.

This rerun STRIPS the governor, telescope, and check
valve. Raw sigma. Raw lambda. Raw coupling. No
regulation. If the substrate pushes back, this is
where it shows.

Sweep pump ratios from 0.03 to 0.75. Measure:
  - Raw velocity (no governor compensation)
  - Raw reaction force (grad_lambda . v_hat * sigma)
  - Lambda distortion (wake footprint)

If V-F correlation flips positive: the substrate is
a medium and the governor was masking it.

If V-F stays negative or zero: the coupling model
needs theoretical correction.

Usage:
    python BCM_v15_test_E_raw.py
    python BCM_v15_test_E_raw.py --steps 2000 --grid 128
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


def run_raw_ratio(steps, nx, ny, dt, D, void_lambda,
                  pump_A, ratio, separation, alpha,
                  exhaust_coupling):
    """
    Run one ratio with NO governor, NO telescope, NO check valve.
    Raw binary pump. Measure velocity and reaction force.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2_init = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    # Lambda field — coupled, no governor
    lam_field = np.full((nx, ny), void_lambda, dtype=float)
    lam_initial = lam_field.copy()

    initial_com = compute_com(sigma)
    prev_com = initial_com.copy()

    # Accumulators
    F_samples = []
    V_samples = []
    timeline = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])
        speed = float(np.linalg.norm(velocity_vec))

        # ── RAW PUMPS — fixed ratio, fixed separation ──
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        actual_B = pump_A * ratio
        pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        # ── EXHAUST COUPLING ──
        # sigma deposits into lambda behind the ship
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

        # ── EVOLVE PDE ──
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma_new = sigma + D * laplacian * dt - lam_field * sigma * dt

        # Memory term (keep alpha — that's physics, not governor)
        if alpha > 0:
            sigma_new = sigma_new + alpha * (sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)

        # NO check valve. NO telescope. NO governor.

        if float(np.max(sigma_new)) > 1e10:
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # ── MEASURE REACTION FORCE ──
        if speed > 1e-10 and step > 50:
            v_hat = velocity_vec / speed

            grad_lam_x = (np.roll(lam_field, -1, axis=0) -
                          np.roll(lam_field, 1, axis=0)) / 2.0
            grad_lam_y = (np.roll(lam_field, -1, axis=1) -
                          np.roll(lam_field, 1, axis=1)) / 2.0

            grad_dot_v = grad_lam_x * v_hat[0] + grad_lam_y * v_hat[1]

            # Ship envelope
            r2_env = (X - com[0])**2 + (Y - com[1])**2
            envelope = r2_env < 10.0**2

            F_local = grad_dot_v * sigma * envelope
            F_reaction = float(np.sum(F_local))

            F_samples.append(abs(F_reaction))
            V_samples.append(speed)

        # Timeline every 100 steps
        if step % 100 == 0 or step == steps - 1:
            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(new_com - initial_com))
                coh = compute_coherence(sigma, new_com)
                timeline.append({
                    "step": step,
                    "x": round(float(new_com[0]), 4),
                    "drift": round(drift, 4),
                    "speed": round(speed, 8),
                    "coherence": round(coh, 4),
                })

        prev_com = com

    # Final
    final_com = compute_com(sigma)
    if final_com is not None:
        total_drift = float(np.linalg.norm(final_com - initial_com))
        final_coh = compute_coherence(sigma, final_com)
    else:
        total_drift = 0
        final_coh = 0

    avg_v = float(np.mean(V_samples)) if V_samples else 0
    avg_F = float(np.mean(F_samples)) if F_samples else 0
    max_v = float(np.max(V_samples)) if V_samples else 0
    max_F = float(np.max(F_samples)) if F_samples else 0
    lam_distortion = float(np.sum(np.abs(lam_field - lam_initial)))

    return {
        "ratio": ratio,
        "drift": round(total_drift, 6),
        "coherence": round(final_coh, 4),
        "avg_velocity": round(avg_v, 10),
        "avg_F_reaction": round(avg_F, 10),
        "max_velocity": round(max_v, 10),
        "max_F_reaction": round(max_F, 10),
        "lambda_distortion": round(lam_distortion, 6),
        "n_samples": len(V_samples),
        "timeline": timeline,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v15 Test E Raw — Governor Stripped")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v15 — TEST E RAW (Governor Stripped)")
    print(f"  No governor. No telescope. No check valve.")
    print(f"  Raw sigma vs raw lambda.")
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

    # Wider ratio sweep — 10 points
    ratios = [0.03, 0.05, 0.08, 0.10, 0.15,
              0.20, 0.25, 0.35, 0.50, 0.75]

    results = []

    print(f"\n  {'Ratio':>6} {'Drift':>10} {'Avg_V':>12} "
          f"{'Avg_F':>12} {'Max_V':>12} {'Max_F':>12} "
          f"{'Lam_Dist':>10}")
    print(f"  {'─'*6} {'─'*10} {'─'*12} {'─'*12} "
          f"{'─'*12} {'─'*12} {'─'*10}")

    for ratio in ratios:
        r = run_raw_ratio(args.steps, nx, ny, dt, D,
                          void_lambda, pump_A, ratio,
                          separation, alpha, exhaust_coupling)
        results.append(r)

        print(f"  {ratio:>6.2f} {r['drift']:>10.3f} "
              f"{r['avg_velocity']:>12.8f} "
              f"{r['avg_F_reaction']:>12.8f} "
              f"{r['max_velocity']:>12.8f} "
              f"{r['max_F_reaction']:>12.8f} "
              f"{r['lambda_distortion']:>10.4f}")

    # ── Correlation Analysis ──
    print(f"\n{'='*65}")
    print(f"  V-F CORRELATION ANALYSIS (RAW — NO GOVERNOR)")
    print(f"{'='*65}")

    velocities = [r["avg_velocity"] for r in results]
    forces = [r["avg_F_reaction"] for r in results]
    max_velocities = [r["max_velocity"] for r in results]
    max_forces = [r["max_F_reaction"] for r in results]
    drifts = [r["drift"] for r in results]
    distortions = [r["lambda_distortion"] for r in results]

    # Average V vs average F
    v_arr = np.array(velocities)
    f_arr = np.array(forces)
    if np.std(v_arr) > 1e-15 and np.std(f_arr) > 1e-15:
        corr_avg = float(np.corrcoef(v_arr, f_arr)[0, 1])
    else:
        corr_avg = 0.0

    # Max V vs max F
    mv_arr = np.array(max_velocities)
    mf_arr = np.array(max_forces)
    if np.std(mv_arr) > 1e-15 and np.std(mf_arr) > 1e-15:
        corr_max = float(np.corrcoef(mv_arr, mf_arr)[0, 1])
    else:
        corr_max = 0.0

    # Drift vs distortion
    d_arr = np.array(drifts)
    dist_arr = np.array(distortions)
    if np.std(d_arr) > 1e-15 and np.std(dist_arr) > 1e-15:
        corr_drift_dist = float(np.corrcoef(d_arr, dist_arr)[0, 1])
    else:
        corr_drift_dist = 0.0

    # Ratio vs velocity (does more asymmetry = more speed?)
    r_arr = np.array(ratios)
    if np.std(r_arr) > 1e-15 and np.std(v_arr) > 1e-15:
        corr_ratio_v = float(np.corrcoef(r_arr, v_arr)[0, 1])
    else:
        corr_ratio_v = 0.0

    # Ratio vs force
    if np.std(r_arr) > 1e-15 and np.std(f_arr) > 1e-15:
        corr_ratio_f = float(np.corrcoef(r_arr, f_arr)[0, 1])
    else:
        corr_ratio_f = 0.0

    print(f"\n  Correlations:")
    print(f"  {'─'*50}")
    print(f"  Avg Velocity vs Avg Force:   r = {corr_avg:>+.6f}")
    print(f"  Max Velocity vs Max Force:   r = {corr_max:>+.6f}")
    print(f"  Drift vs Lambda Distortion:  r = {corr_drift_dist:>+.6f}")
    print(f"  Ratio vs Velocity:           r = {corr_ratio_v:>+.6f}")
    print(f"  Ratio vs Force:              r = {corr_ratio_f:>+.6f}")

    # ── Verdict ──
    print(f"\n  {'─'*50}")
    has_force = any(f > 1e-12 for f in forces)

    if corr_avg > 0.7:
        verdict = "PASS"
        reason = (f"Positive V-F correlation (r={corr_avg:+.4f}). "
                  f"Governor was masking it. Substrate pushes back.")
    elif corr_avg > 0.3:
        verdict = "PARTIAL"
        reason = (f"Weak positive correlation (r={corr_avg:+.4f}). "
                  f"Coupling exists but noisy.")
    elif corr_avg < -0.3:
        verdict = "NEGATIVE COUPLING"
        reason = (f"Negative V-F correlation persists (r={corr_avg:+.4f}) "
                  f"even without governor. This is not masking — "
                  f"the coupling model itself produces inverse scaling.")
    else:
        verdict = "NO COUPLING"
        reason = (f"No V-F correlation (r={corr_avg:+.4f}). "
                  f"No medium interaction detected.")

    print(f"  VERDICT: {verdict}")
    print(f"  {reason}")

    # Additional diagnostics
    if corr_ratio_v > 0.5:
        print(f"\n  NOTE: Ratio-Velocity correlation is positive "
              f"(r={corr_ratio_v:+.4f}).")
        print(f"  More asymmetry → more speed. Transport law holds raw.")
    elif corr_ratio_v < -0.5:
        print(f"\n  NOTE: Ratio-Velocity correlation is NEGATIVE "
              f"(r={corr_ratio_v:+.4f}).")
        print(f"  More asymmetry → LESS speed. Saturation regime.")

    if corr_ratio_f > 0.5:
        print(f"  Ratio-Force correlation positive "
              f"(r={corr_ratio_f:+.4f}).")
        print(f"  More asymmetry → more reaction. Substrate resists "
              f"harder pumping.")

    print(f"  {'─'*50}")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v15_test_E_raw_{time.strftime('%Y%m%d_%H%M%S')}.json")

    # Strip timelines for compact JSON
    results_compact = []
    for r in results:
        rc = {k: v for k, v in r.items() if k != "timeline"}
        results_compact.append(rc)

    out_data = {
        "title": "BCM v15 Test E Raw — Governor Stripped",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Raw V-F coupling without governor masking",
        "grid": nx,
        "steps": args.steps,
        "parameters": {
            "dt": dt, "D": D, "void_lambda": void_lambda,
            "pump_A": pump_A, "alpha": alpha,
            "separation": separation,
            "exhaust_coupling": exhaust_coupling,
            "governor": "OFF", "telescope": "OFF",
            "check_valve": "OFF",
        },
        "correlations": {
            "avg_V_vs_avg_F": round(corr_avg, 6),
            "max_V_vs_max_F": round(corr_max, 6),
            "drift_vs_distortion": round(corr_drift_dist, 6),
            "ratio_vs_velocity": round(corr_ratio_v, 6),
            "ratio_vs_force": round(corr_ratio_f, 6),
        },
        "verdict": verdict,
        "reason": reason,
        "ratio_sweep": results_compact,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
