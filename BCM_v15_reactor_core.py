# -*- coding: utf-8 -*-
"""
BCM v15 — Live Substrate + Finite Reactor Core
=================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The reactor is a nuclear core. It burns. When the
fuel is gone, the pumps stop and the ship dissolves.
Stephen identified this from the start.

CONSERVATION LAW:
  E_total = E_reactor + E_sigma + E_lambda

  E_reactor decreases every step the pumps fire.
  E_sigma increases from pump injection.
  E_lambda changes from substrate PDE coupling.

  If conservation holds: E_total stays constant
  (within numerical tolerance). No free energy.
  No infinite sources. The reactor is the bank
  account and every pump cycle is a withdrawal.

SUBSTRATE PDE (Gemini):
  d_lam/dt = D_lam * lap(lam) - beta * sigma
             + Gamma * (lam_void - lam)

REACTOR:
  d_reactor/dt = -(pump_A + pump_B) * burn_rate
  When reactor <= 0: pumps stop.

Three tests:
  A) INFINITE reactor (v14 baseline — no limit)
  B) LARGE reactor (enough fuel for full run)
  C) SMALL reactor (fuel runs out mid-transit)

Usage:
    python BCM_v15_reactor_core.py
    python BCM_v15_reactor_core.py --steps 2000 --grid 128
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


def run_reactor_test(steps, nx, ny, dt, D_sigma, pump_A,
                     ratio, separation, alpha, void_lambda,
                     D_lam, beta, Gamma,
                     reactor_budget, burn_rate,
                     label="TEST"):
    """
    Run with live substrate and finite reactor.
    Pumps draw from reactor. When reactor empties, pumps stop.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2_init = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    lam_field = np.full((nx, ny), void_lambda, dtype=float)

    initial_com = compute_com(sigma)
    prev_com = initial_com.copy()

    # Reactor state
    reactor = reactor_budget
    reactor_infinite = (reactor_budget < 0)  # negative = infinite
    reactor_empty_step = None

    # Initial energies — use field integrals (same units as reactor)
    E_sigma_0 = float(np.sum(sigma))
    E_lambda_0 = float(np.sum(lam_field))
    E_reactor_0 = reactor if not reactor_infinite else 0
    E_total_0 = E_sigma_0 + E_lambda_0 + E_reactor_0

    timeline = []
    alive = True

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            alive = False
            break

        velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])
        speed = float(np.linalg.norm(velocity_vec))

        # ── REACTOR CHECK ──
        pumps_active = reactor_infinite or reactor > 0

        # ── PUMPS (only if reactor has fuel) ──
        # KEY FIX: measure the exact integral of what pumps
        # inject into sigma, then subtract that same quantity
        # from the reactor. 1:1 exchange. No unit mismatch.
        # The reactor IS the sigma it hasn't injected yet.
        pump_energy_injected = 0.0

        if pumps_active:
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            injection_A = float(np.sum(pA * dt))

            bx = com[0] + separation
            r2_B = (X - bx)**2 + (Y - com[1])**2
            actual_B = pump_A * ratio
            pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
            injection_B = float(np.sum(pB * dt))

            total_injection = injection_A + injection_B

            # Check if reactor can afford this injection
            if not reactor_infinite:
                if reactor >= total_injection:
                    # Full injection — reactor pays
                    reactor -= total_injection
                    sigma += pA * dt
                    sigma += pB * dt
                    pump_energy_injected = total_injection
                elif reactor > 0:
                    # Partial injection — reactor gives what's left
                    # Scale pumps proportionally
                    scale = reactor / total_injection
                    sigma += pA * dt * scale
                    sigma += pB * dt * scale
                    pump_energy_injected = reactor
                    reactor = 0
                    reactor_empty_step = step
                else:
                    # Reactor empty — no injection
                    pumps_active = False
                    reactor_empty_step = reactor_empty_step or step
            else:
                # Infinite reactor — inject freely
                sigma += pA * dt
                sigma += pB * dt
                pump_energy_injected = total_injection

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

        if alpha > 0:
            sigma_new = sigma_new + alpha * (sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)

        # ── LAMBDA PDE ──
        lap_lambda = (
            np.roll(lam_field, 1, axis=0) +
            np.roll(lam_field, -1, axis=0) +
            np.roll(lam_field, 1, axis=1) +
            np.roll(lam_field, -1, axis=1) -
            4 * lam_field
        )

        lam_new = (lam_field
                   + D_lam * lap_lambda * dt
                   - beta * sigma * dt
                   + Gamma * (void_lambda - lam_field) * dt)

        lam_new = np.maximum(lam_new, 0.001)
        lam_field = lam_new

        if float(np.max(sigma_new)) > 1e10:
            alive = False
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # ── ENERGY ACCOUNTING ──
        if step % 50 == 0 or step == steps - 1:
            E_sigma = float(np.sum(sigma))
            E_lambda = float(np.sum(lam_field))
            E_reactor_now = reactor if not reactor_infinite else 0
            E_total = E_sigma + E_lambda + E_reactor_now

            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(new_com - initial_com))
                coh = compute_coherence(sigma, new_com)
                ix = min(max(int(new_com[0]), 0), nx - 1)
                iy = min(max(int(new_com[1]), 0), ny - 1)
                local_lam = float(lam_field[ix, iy])

                timeline.append({
                    "step": step,
                    "x": round(float(new_com[0]), 4),
                    "drift": round(drift, 4),
                    "speed": round(speed, 8),
                    "coherence": round(coh, 4),
                    "local_lambda": round(local_lam, 6),
                    "reactor": round(E_reactor_now, 4),
                    "pumps": "ON" if pumps_active else "OFF",
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
    else:
        total_drift = 0
        final_coh = 0

    E_sigma_f = float(np.sum(sigma))
    E_lambda_f = float(np.sum(lam_field))
    E_reactor_f = reactor if not reactor_infinite else 0
    E_total_f = E_sigma_f + E_lambda_f + E_reactor_f

    # Conservation check
    if not reactor_infinite and E_total_0 > 0:
        conservation_error = abs(E_total_f - E_total_0) / E_total_0 * 100
    else:
        conservation_error = -1  # not applicable

    return {
        "label": label,
        "reactor_budget": reactor_budget,
        "burn_rate": burn_rate,
        "alive": alive,
        "drift": round(total_drift, 6),
        "coherence": round(final_coh, 4),
        "reactor_remaining": round(E_reactor_f, 4),
        "reactor_empty_step": reactor_empty_step,
        "E_sigma_initial": round(E_sigma_0, 4),
        "E_sigma_final": round(E_sigma_f, 4),
        "E_lambda_initial": round(E_lambda_0, 4),
        "E_lambda_final": round(E_lambda_f, 4),
        "E_total_initial": round(E_total_0, 4),
        "E_total_final": round(E_total_f, 4),
        "conservation_error_pct": round(conservation_error, 4),
        "timeline": timeline,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v15 Live Substrate + Finite Reactor")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v15 — LIVE SUBSTRATE + FINITE REACTOR CORE")
    print(f"  The reactor burns. When fuel is gone, the ship dies.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    dt = 0.05
    D_sigma = 0.5
    pump_A = 0.5
    ratio = 0.25
    separation = 15.0
    alpha = 0.80
    void_lambda = 0.10

    # Substrate PDE — medium coupling
    D_lam = 0.2
    beta = 0.005
    Gamma = 0.01

    # Reactor configs
    configs = [
        {"label": "INFINITE", "budget": -1, "burn": 0.0,
         "desc": "No limit — baseline comparison"},
        {"label": "LARGE_CORE", "budget": 500.0, "burn": 1.0,
         "desc": "Enough fuel for ~full run"},
        {"label": "MEDIUM_CORE", "budget": 200.0, "burn": 1.0,
         "desc": "Fuel runs out mid-transit"},
        {"label": "SMALL_CORE", "budget": 50.0, "burn": 1.0,
         "desc": "Fuel runs out early"},
        {"label": "MICRO_CORE", "budget": 20.0, "burn": 1.0,
         "desc": "Minimal fuel — sprint start"},
    ]

    results = []

    print(f"\n  Substrate PDE: D_lam={D_lam} beta={beta} Gamma={Gamma}")
    print(f"\n  {'Label':>14} {'Budget':>8} {'Drift':>8} {'Coh':>6} "
          f"{'Reactor':>8} {'Empty@':>8} "
          f"{'E_total_0':>10} {'E_total_f':>10} {'ConsErr':>8}")
    print(f"  {'─'*14} {'─'*8} {'─'*8} {'─'*6} {'─'*8} {'─'*8} "
          f"{'─'*10} {'─'*10} {'─'*8}")

    for cfg in configs:
        r = run_reactor_test(
            args.steps, nx, ny, dt, D_sigma, pump_A,
            ratio, separation, alpha, void_lambda,
            D_lam, beta, Gamma,
            reactor_budget=cfg["budget"],
            burn_rate=cfg["burn"],
            label=cfg["label"])

        results.append(r)

        empty_str = str(r["reactor_empty_step"]) if r["reactor_empty_step"] else "—"
        cons_str = f"{r['conservation_error_pct']:.2f}%" if r['conservation_error_pct'] >= 0 else "N/A"

        print(f"  {cfg['label']:>14} {cfg['budget']:>8.0f} "
              f"{r['drift']:>8.2f} {r['coherence']:>6.3f} "
              f"{r['reactor_remaining']:>8.2f} {empty_str:>8} "
              f"{r['E_total_initial']:>10.2f} "
              f"{r['E_total_final']:>10.2f} "
              f"{cons_str:>8}")

    # ── Analysis ──
    print(f"\n{'='*65}")
    print(f"  REACTOR DEPLETION ANALYSIS")
    print(f"{'='*65}")

    for r in results:
        if r["reactor_empty_step"] is not None:
            print(f"\n  {r['label']}: Reactor empty at step "
                  f"{r['reactor_empty_step']}")
            print(f"    Drift before empty: see timeline")
            print(f"    Final drift: {r['drift']:.2f} px")
            print(f"    Ship alive: {'YES' if r['alive'] else 'NO'}")
            print(f"    Coherence at end: {r['coherence']:.3f}")

    # Conservation audit
    print(f"\n{'='*65}")
    print(f"  CONSERVATION AUDIT")
    print(f"  E_total = E_reactor + E_sigma + E_lambda")
    print(f"{'='*65}")

    for r in results:
        if r["conservation_error_pct"] >= 0:
            status = "PASS" if r["conservation_error_pct"] < 5.0 else "FAIL"
            print(f"\n  {r['label']}: E_total {r['E_total_initial']:.2f} "
                  f"→ {r['E_total_final']:.2f}  "
                  f"error={r['conservation_error_pct']:.2f}%  [{status}]")

    # ── Verdict ──
    print(f"\n{'='*65}")
    print(f"  VERDICT")
    print(f"{'='*65}")

    # Check if finite reactors still produce transport
    finite_results = [r for r in results if r["reactor_budget"] > 0]
    all_transport = all(r["drift"] > 1.0 for r in finite_results)
    all_alive = all(r["alive"] for r in finite_results)

    small_runs_out = [r for r in finite_results
                      if r["reactor_empty_step"] is not None]
    ship_dies_after = any(not r["alive"] for r in small_runs_out)

    if all_transport:
        print(f"\n  TRANSPORT SURVIVES FINITE REACTOR.")
        print(f"  Ship moves at all fuel levels.")
    else:
        print(f"\n  TRANSPORT FAILS at some fuel levels.")

    for r in finite_results:
        if r["reactor_empty_step"] is not None:
            if r["alive"]:
                print(f"\n  {r['label']}: Reactor empty at step "
                      f"{r['reactor_empty_step']}. Ship SURVIVED "
                      f"on residual sigma.")
            else:
                print(f"\n  {r['label']}: Reactor empty at step "
                      f"{r['reactor_empty_step']}. Ship DISSOLVED.")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v15_reactor_core_{time.strftime('%Y%m%d_%H%M%S')}.json")

    results_compact = []
    for r in results:
        rc = {k: v for k, v in r.items() if k != "timeline"}
        results_compact.append(rc)

    out_data = {
        "title": "BCM v15 Live Substrate + Finite Reactor Core",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Conservation law via finite reactor budget",
        "grid": nx,
        "steps": args.steps,
        "substrate_PDE": "d_lam/dt = D_lam*lap(lam) - beta*sigma + Gamma*(lam_void - lam)",
        "conservation_law": "E_total = E_reactor + E_sigma + E_lambda",
        "parameters": {
            "dt": dt, "D_sigma": D_sigma, "pump_A": pump_A,
            "ratio": ratio, "separation": separation,
            "alpha": alpha, "void_lambda": void_lambda,
            "D_lam": D_lam, "beta": beta, "Gamma": Gamma,
        },
        "configs": configs,
        "results": results_compact,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
