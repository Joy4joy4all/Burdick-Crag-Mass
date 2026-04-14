# -*- coding: utf-8 -*-
"""
BCM v15 — Live Substrate (Lambda PDE)
========================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Lambda is no longer a static map. It lives.

The substrate evolves under its own PDE:

  d_lambda/dt = D_lam * laplacian(lambda)
                - beta * sigma
                + Gamma * (lambda_void - lambda)

Three terms:

  1. DIFFUSION: D_lam * laplacian(lambda)
     Substrate heals its own scars. Gradients smooth out.
     The wake dissipates. The grave fills in.

  2. COUPLING: -beta * sigma
     The ship eats the substrate. Where sigma is high,
     lambda drops. This is the cost of existence.

  3. RELAXATION: Gamma * (lambda_void - lambda)
     Substrate drifts back to void baseline. Without
     active funding, the field returns to ground state.
     This is what makes void dark.

With lambda alive, we can measure:
  - Does transport still work when the medium reacts?
  - Does the substrate heal behind the ship?
  - Does the wake persist or dissolve?
  - Is energy conserved between sigma and lambda?

Three runs:
  A) STATIC lambda (v14 baseline, lambda frozen)
  B) LIVE lambda (full PDE, weak coupling)
  C) LIVE lambda (full PDE, strong coupling)

If transport survives the live substrate, the physics
holds. If it dies, the transport was an artifact of
a static medium.

Usage:
    python BCM_v15_live_substrate.py
    python BCM_v15_live_substrate.py --steps 2000 --grid 128
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


def run_live_substrate(steps, nx, ny, dt, D_sigma, pump_A,
                       ratio, separation, alpha,
                       void_lambda,
                       D_lam, beta, Gamma,
                       live_substrate=True,
                       label="LIVE"):
    """
    Run transport with live or static lambda.

    If live_substrate=True, lambda evolves under its own PDE.
    If False, lambda is static (v14 baseline).
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Initial sigma packet
    center = (nx // 3, ny // 2)
    r2_init = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    # Lambda field
    lam_field = np.full((nx, ny), void_lambda, dtype=float)
    lam_initial = lam_field.copy()

    initial_com = compute_com(sigma)
    prev_com = initial_com.copy()

    # Energy tracking
    E_sigma_history = []
    E_lambda_history = []
    E_total_history = []

    timeline = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])
        speed = float(np.linalg.norm(velocity_vec))

        # ── PUMPS (raw, no governor — open loop) ──
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        actual_B = pump_A * ratio
        pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        # ── SIGMA PDE ──
        lap_sigma = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma_new = (sigma
                     + D_sigma * lap_sigma * dt
                     - lam_field * sigma * dt)

        # Memory term
        if alpha > 0:
            sigma_new = sigma_new + alpha * (sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)

        # ── LAMBDA PDE (if live) ──
        if live_substrate:
            lap_lambda = (
                np.roll(lam_field, 1, axis=0) +
                np.roll(lam_field, -1, axis=0) +
                np.roll(lam_field, 1, axis=1) +
                np.roll(lam_field, -1, axis=1) -
                4 * lam_field
            )

            # Three terms:
            # 1. Diffusion: substrate heals scars
            diffusion_term = D_lam * lap_lambda * dt

            # 2. Coupling: ship eats substrate
            coupling_term = -beta * sigma * dt

            # 3. Relaxation: substrate returns to void
            relaxation_term = Gamma * (void_lambda - lam_field) * dt

            lam_new = lam_field + diffusion_term + coupling_term + relaxation_term
            lam_new = np.maximum(lam_new, 0.001)  # floor

            lam_field = lam_new

        # Blowup guard
        if float(np.max(sigma_new)) > 1e10:
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # ── ENERGY TRACKING ──
        E_sigma = float(np.sum(sigma**2))
        E_lambda = float(np.sum(lam_field**2))
        E_total = E_sigma + E_lambda

        if step % 50 == 0 or step == steps - 1:
            E_sigma_history.append(round(E_sigma, 6))
            E_lambda_history.append(round(E_lambda, 6))
            E_total_history.append(round(E_total, 6))

        # ── TIMELINE ──
        if step % 100 == 0 or step == steps - 1:
            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(new_com - initial_com))
                coh = compute_coherence(sigma, new_com)

                # Lambda state at ship position
                ix = min(max(int(new_com[0]), 0), nx - 1)
                iy = min(max(int(new_com[1]), 0), ny - 1)
                local_lam = float(lam_field[ix, iy])

                # Lambda deviation from baseline
                lam_deviation = float(
                    np.sum(np.abs(lam_field - void_lambda)))

                # Wake: lambda behind ship
                aft_lam = float(np.mean(
                    lam_field[max(0, ix-20):ix,
                              max(0, iy-5):min(ny, iy+5)]))

                timeline.append({
                    "step": step,
                    "x": round(float(new_com[0]), 4),
                    "drift": round(drift, 4),
                    "speed": round(speed, 8),
                    "coherence": round(coh, 4),
                    "local_lambda": round(local_lam, 6),
                    "aft_lambda": round(aft_lam, 6),
                    "lam_deviation": round(lam_deviation, 4),
                    "E_sigma": round(E_sigma, 4),
                    "E_lambda": round(E_lambda, 4),
                    "E_total": round(E_total, 4),
                })

        prev_com = com

    # ── Final ──
    final_com = compute_com(sigma)
    if final_com is not None:
        total_drift = float(np.linalg.norm(final_com - initial_com))
        final_coh = compute_coherence(sigma, final_com)
        ix = min(max(int(final_com[0]), 0), nx - 1)
        iy = min(max(int(final_com[1]), 0), ny - 1)
        final_local_lam = float(lam_field[ix, iy])
    else:
        total_drift = 0
        final_coh = 0
        final_local_lam = 0

    final_lam_deviation = float(
        np.sum(np.abs(lam_field - void_lambda)))

    # Energy change
    if len(E_total_history) > 1:
        E_change = E_total_history[-1] - E_total_history[0]
        E_change_pct = (E_change / E_total_history[0]) * 100 if E_total_history[0] > 0 else 0
    else:
        E_change = 0
        E_change_pct = 0

    return {
        "label": label,
        "live_substrate": live_substrate,
        "D_lam": D_lam,
        "beta": beta,
        "Gamma": Gamma,
        "drift": round(total_drift, 6),
        "coherence": round(final_coh, 4),
        "local_lambda_final": round(final_local_lam, 6),
        "lam_deviation_final": round(final_lam_deviation, 4),
        "E_sigma_initial": E_sigma_history[0] if E_sigma_history else 0,
        "E_sigma_final": E_sigma_history[-1] if E_sigma_history else 0,
        "E_lambda_initial": E_lambda_history[0] if E_lambda_history else 0,
        "E_lambda_final": E_lambda_history[-1] if E_lambda_history else 0,
        "E_total_initial": E_total_history[0] if E_total_history else 0,
        "E_total_final": E_total_history[-1] if E_total_history else 0,
        "E_change": round(E_change, 6),
        "E_change_pct": round(E_change_pct, 4),
        "timeline": timeline,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v15 Live Substrate")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v15 — LIVE SUBSTRATE (Lambda PDE)")
    print(f"  Lambda lives. The medium reacts.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    # Shared parameters
    dt = 0.05
    D_sigma = 0.5
    pump_A = 0.5
    ratio = 0.25
    separation = 15.0
    alpha = 0.80
    void_lambda = 0.10

    # Substrate PDE parameters to sweep
    configs = [
        {
            "label": "STATIC",
            "live": False,
            "D_lam": 0.0, "beta": 0.0, "Gamma": 0.0,
            "desc": "v14 baseline — lambda frozen",
        },
        {
            "label": "LIVE_WEAK",
            "live": True,
            "D_lam": 0.1, "beta": 0.001, "Gamma": 0.005,
            "desc": "Weak coupling — substrate barely reacts",
        },
        {
            "label": "LIVE_MED",
            "live": True,
            "D_lam": 0.2, "beta": 0.005, "Gamma": 0.01,
            "desc": "Medium coupling — substrate responds",
        },
        {
            "label": "LIVE_STRONG",
            "live": True,
            "D_lam": 0.3, "beta": 0.01, "Gamma": 0.02,
            "desc": "Strong coupling — substrate fights back",
        },
        {
            "label": "LIVE_EXTREME",
            "live": True,
            "D_lam": 0.5, "beta": 0.02, "Gamma": 0.05,
            "desc": "Extreme coupling — substrate dominates",
        },
    ]

    results = []

    print(f"\n  {'Label':>14} {'Drift':>8} {'Coh':>6} "
          f"{'LocalLam':>9} {'LamDev':>10} "
          f"{'E_sig':>10} {'E_lam':>10} {'E_tot':>10} "
          f"{'E_chg%':>8}")
    print(f"  {'─'*14} {'─'*8} {'─'*6} {'─'*9} {'─'*10} "
          f"{'─'*10} {'─'*10} {'─'*10} {'─'*8}")

    for cfg in configs:
        r = run_live_substrate(
            args.steps, nx, ny, dt, D_sigma, pump_A,
            ratio, separation, alpha, void_lambda,
            D_lam=cfg["D_lam"],
            beta=cfg["beta"],
            Gamma=cfg["Gamma"],
            live_substrate=cfg["live"],
            label=cfg["label"])

        results.append(r)

        print(f"  {cfg['label']:>14} {r['drift']:>8.2f} "
              f"{r['coherence']:>6.3f} "
              f"{r['local_lambda_final']:>9.5f} "
              f"{r['lam_deviation_final']:>10.4f} "
              f"{r['E_sigma_final']:>10.2f} "
              f"{r['E_lambda_final']:>10.2f} "
              f"{r['E_total_final']:>10.2f} "
              f"{r['E_change_pct']:>+8.2f}%")

    # ── Comparison ──
    print(f"\n{'='*65}")
    print(f"  LIVE SUBSTRATE COMPARISON")
    print(f"{'='*65}")

    static = results[0]
    print(f"\n  Baseline (STATIC): drift={static['drift']:.2f} px, "
          f"coh={static['coherence']:.3f}")

    for r in results[1:]:
        drift_change = ((r['drift'] - static['drift']) /
                        static['drift'] * 100) if static['drift'] > 0 else 0
        coh_change = ((r['coherence'] - static['coherence']) /
                      static['coherence'] * 100) if static['coherence'] > 0 else 0

        print(f"\n  {r['label']}:")
        print(f"    D_lam={r['D_lam']}  beta={r['beta']}  "
              f"Gamma={r['Gamma']}")
        print(f"    Drift: {r['drift']:.2f} px "
              f"({drift_change:+.1f}% vs static)")
        print(f"    Coherence: {r['coherence']:.3f} "
              f"({coh_change:+.1f}% vs static)")
        print(f"    Lambda at ship: {r['local_lambda_final']:.5f}")
        print(f"    Lambda deviation: {r['lam_deviation_final']:.4f}")
        print(f"    Energy change: {r['E_change_pct']:+.2f}%")

    # ── Verdict ──
    print(f"\n{'='*65}")
    print(f"  VERDICT")
    print(f"{'='*65}")

    transport_survives = all(r['drift'] > 1.0 for r in results)
    coherence_survives = all(r['coherence'] > 0.15 for r in results)

    if transport_survives and coherence_survives:
        print(f"\n  TRANSPORT SURVIVES LIVE SUBSTRATE.")
        print(f"  Drift is positive at all coupling strengths.")
        print(f"  Coherence maintained above dissolution threshold.")
        print(f"  The physics holds when the medium fights back.")
    elif transport_survives:
        print(f"\n  TRANSPORT SURVIVES but coherence degraded.")
        print(f"  Ship moves but loses structural integrity")
        print(f"  at high coupling.")
    else:
        print(f"\n  TRANSPORT FAILS under live substrate.")
        print(f"  Static medium was load-bearing for the transport.")
        print(f"  The physics does not survive a reactive medium.")

    # Lambda healing check
    print(f"\n  SUBSTRATE HEALING:")
    for r in results:
        if r['live_substrate']:
            if r['lam_deviation_final'] < r.get('lam_deviation_final', 999):
                print(f"    {r['label']}: deviation={r['lam_deviation_final']:.4f} "
                      f"(Gamma={r['Gamma']})")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v15_live_substrate_{time.strftime('%Y%m%d_%H%M%S')}.json")

    # Strip timelines for compact save
    results_compact = []
    for r in results:
        rc = {k: v for k, v in r.items() if k != "timeline"}
        results_compact.append(rc)

    out_data = {
        "title": "BCM v15 Live Substrate — Lambda PDE",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Does transport survive when the medium fights back?",
        "grid": nx,
        "steps": args.steps,
        "parameters": {
            "dt": dt, "D_sigma": D_sigma, "pump_A": pump_A,
            "ratio": ratio, "separation": separation,
            "alpha": alpha, "void_lambda": void_lambda,
        },
        "substrate_PDE": "d_lam/dt = D_lam*lap(lam) - beta*sigma + Gamma*(lam_void - lam)",
        "configs": configs,
        "results": results_compact,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
