# -*- coding: utf-8 -*-
"""
BCM v14 — Ghost Packet Diagnostic
=====================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

No spooks in our system. Three packets. Same field.
Same start. Only controls differ.

  GHOST:     No pump. No control. Pure PDE. Dies or drifts?
  FIXED:     Pump A+B fixed parameters. No regulation.
  REGULATED: Full governor + check valve + telescope.

Track all three simultaneously. Report position, energy,
coherence, alive/dead every 100 steps. The differential
displacement between GHOST and REGULATED is the transport
signal — if it exists.

Usage:
    python BCM_ghost_packet.py
    python BCM_ghost_packet.py --steps 2000 --grid 128
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


def run_packet(steps, nx, ny, dt, D, void_lambda,
                pump_A, pump_B, separation,
                use_governor, use_check_valve,
                use_telescope, alpha,
                cv_strength=0.3,
                target_lambda=0.05,
                label="PACKET"):
    """
    Run one packet through the full simulation.
    Returns timeline of position, energy, coherence.
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2_init = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    lam_field = np.full((nx, ny), void_lambda)

    initial_com = compute_com(sigma)
    prev_com = initial_com.copy()

    timeline = []
    alive = True
    last_com = initial_com.copy()

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            alive = False
            # Record death
            timeline.append({
                "step": step,
                "alive": False,
                "x": float(last_com[0]) if last_com is not None else 0,
                "drift": float(np.linalg.norm(
                    last_com - initial_com)) if last_com is not None else 0,
                "E": 0,
                "coh": 0,
                "peak": 0,
            })
            break

        last_com = com.copy()

        # Velocity for telescope
        velocity = 0
        if prev_com is not None:
            velocity = float(np.linalg.norm(com - prev_com))

        # Local lambda for governor
        ix = min(max(int(com[0]), 0), nx - 1)
        iy = min(max(int(com[1]), 0), ny - 1)
        local_lam = float(lam_field[ix, iy])

        # Determine separation (telescope)
        if use_telescope:
            v_norm = min(velocity / 0.02, 1.0)
            sep = 8.0 + (25.0 - 8.0) * v_norm
        else:
            sep = separation

        # Determine ratio (governor)
        if use_governor:
            error = local_lam - target_lambda
            if error > 0:
                boost = min(error * 5.0, 1.0)
                ratio = 0.125 + (0.50 - 0.125) * boost
            else:
                ratio = max(0.03, 0.125 + error)
        else:
            ratio = pump_B / pump_A if pump_A > 0 else 0

        # Apply pumps
        if pump_A > 0:
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            if pump_B > 0 or use_governor:
                bx = com[0] + sep
                r2_B = (X - bx)**2 + (Y - com[1])**2
                actual_B = pump_A * ratio
                pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
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

        # Check valve
        if use_check_valve and cv_strength > 0:
            flow = sigma_new - sigma
            flow_grad_x = (np.roll(flow, -1, axis=0) -
                            np.roll(flow, 1, axis=0)) / 2.0
            backflow = flow_grad_x < 0
            valve = np.ones_like(sigma_new)
            valve[backflow] = 1.0 - cv_strength
            sigma_new = sigma_new * valve

        # Blowup check
        if float(np.max(sigma_new)) > 1e10:
            timeline.append({
                "step": step, "alive": False,
                "x": float(com[0]), "drift": 0,
                "E": 0, "coh": 0, "peak": 0,
                "status": "BLOWUP",
            })
            alive = False
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Record every 50 steps
        if step % 50 == 0 or step == steps - 1:
            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(new_com - initial_com))
                E = float(np.sum(sigma**2))
                peak = float(np.max(sigma))
                coh = compute_coherence(sigma, new_com)
                timeline.append({
                    "step": step,
                    "alive": True,
                    "x": round(float(new_com[0]), 4),
                    "drift": round(drift, 4),
                    "E": round(E, 6),
                    "coh": round(coh, 4),
                    "peak": round(peak, 4),
                })

        prev_com = com

    # Final state
    final_com = compute_com(sigma)
    if final_com is not None:
        total_drift = float(np.linalg.norm(final_com - initial_com))
        final_E = float(np.sum(sigma**2))
        final_coh = compute_coherence(sigma, final_com)
    else:
        total_drift = 0
        final_E = 0
        final_coh = 0

    return {
        "label": label,
        "alive": alive,
        "total_drift": round(total_drift, 6),
        "final_E": round(final_E, 6),
        "final_coh": round(final_coh, 4),
        "steps_survived": len(timeline),
        "timeline": timeline,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v14 Ghost Packet Diagnostic")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v14 — GHOST PACKET DIAGNOSTIC")
    print(f"  No spooks in our system.")
    print(f"  Three packets. Same field. Same start.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")

    void_lambdas = [0.10, 0.20, 0.30]
    all_results = {}

    for vl in void_lambdas:
        print(f"\n{'='*65}")
        print(f"  VOID LAMBDA = {vl}")
        print(f"{'='*65}")

        # GHOST: no pump, no control, no memory
        print(f"\n  --- GHOST (no pump, pure PDE) ---")
        ghost = run_packet(args.steps, nx, ny, 0.05, 0.5, vl,
                            pump_A=0, pump_B=0, separation=15,
                            use_governor=False,
                            use_check_valve=False,
                            use_telescope=False,
                            alpha=0,
                            label="GHOST")

        # FIXED: pump A+B, fixed params, no regulation
        print(f"  --- FIXED (pump, no regulation) ---")
        fixed = run_packet(args.steps, nx, ny, 0.05, 0.5, vl,
                            pump_A=0.5, pump_B=0.0625,
                            separation=15,
                            use_governor=False,
                            use_check_valve=False,
                            use_telescope=False,
                            alpha=0.80,
                            label="FIXED")

        # REGULATED: full governor + check valve + telescope
        print(f"  --- REGULATED (full control) ---")
        regulated = run_packet(args.steps, nx, ny, 0.05, 0.5, vl,
                                pump_A=0.5, pump_B=0.0625,
                                separation=15,
                                use_governor=True,
                                use_check_valve=True,
                                use_telescope=True,
                                alpha=0.80,
                                cv_strength=0.2,
                                label="REGULATED")

        # Comparison table
        print(f"\n  {'─'*60}")
        print(f"  COMPARISON AT VOID LAMBDA = {vl}")
        print(f"  {'─'*60}")
        print(f"  {'':>14} {'GHOST':>12} {'FIXED':>12} "
              f"{'REGULATED':>12}")
        print(f"  {'─'*14} {'─'*12} {'─'*12} {'─'*12}")
        print(f"  {'Alive':>14} "
              f"{'YES' if ghost['alive'] else 'DEAD':>12} "
              f"{'YES' if fixed['alive'] else 'DEAD':>12} "
              f"{'YES' if regulated['alive'] else 'DEAD':>12}")
        print(f"  {'Drift (px)':>14} "
              f"{ghost['total_drift']:>12.4f} "
              f"{fixed['total_drift']:>12.4f} "
              f"{regulated['total_drift']:>12.4f}")
        print(f"  {'Final E':>14} "
              f"{ghost['final_E']:>12.6f} "
              f"{fixed['final_E']:>12.6f} "
              f"{regulated['final_E']:>12.6f}")
        print(f"  {'Coherence':>14} "
              f"{ghost['final_coh']:>12.4f} "
              f"{fixed['final_coh']:>12.4f} "
              f"{regulated['final_coh']:>12.4f}")

        # Transport signal
        if ghost['alive']:
            transport_signal = regulated['total_drift'] - ghost['total_drift']
            print(f"\n  Transport signal (Regulated - Ghost): "
                  f"{transport_signal:.4f} px")
        else:
            print(f"\n  Ghost DEAD — transport = survival + drift")
            print(f"  Ghost dissolved. Regulated: "
                  f"{regulated['total_drift']:.4f} px alive.")

        # Timeline comparison (sample every 200 steps)
        print(f"\n  TIMELINE (sampled):")
        print(f"  {'Step':>6} {'G_alive':>8} {'G_drift':>10} "
              f"{'F_drift':>10} {'R_drift':>10}")
        print(f"  {'─'*6} {'─'*8} {'─'*10} {'─'*10} {'─'*10}")

        g_tl = {t["step"]: t for t in ghost["timeline"]}
        f_tl = {t["step"]: t for t in fixed["timeline"]}
        r_tl = {t["step"]: t for t in regulated["timeline"]}

        sample_steps = list(range(0, args.steps, 200))
        for s in sample_steps:
            g = g_tl.get(s, {})
            f = f_tl.get(s, {})
            r = r_tl.get(s, {})

            g_alive = "YES" if g.get("alive", False) else "DEAD"
            g_d = f"{g.get('drift', 0):.4f}" if g.get("alive") else "---"
            f_d = f"{f.get('drift', 0):.4f}" if f.get("alive") else "---"
            r_d = f"{r.get('drift', 0):.4f}" if r.get("alive") else "---"

            print(f"  {s:>6} {g_alive:>8} {g_d:>10} "
                  f"{f_d:>10} {r_d:>10}")

        all_results[f"lambda_{vl}"] = {
            "ghost": ghost,
            "fixed": fixed,
            "regulated": regulated,
        }

    # Final summary
    print(f"\n{'='*65}")
    print(f"  GHOST PACKET SUMMARY")
    print(f"{'='*65}")

    for vl in void_lambdas:
        key = f"lambda_{vl}"
        g = all_results[key]["ghost"]
        f = all_results[key]["fixed"]
        r = all_results[key]["regulated"]

        print(f"\n  Lambda={vl}:")
        print(f"    Ghost:     {'ALIVE' if g['alive'] else 'DEAD':>8}  "
              f"drift={g['total_drift']:.4f}")
        print(f"    Fixed:     {'ALIVE' if f['alive'] else 'DEAD':>8}  "
              f"drift={f['total_drift']:.4f}")
        print(f"    Regulated: {'ALIVE' if r['alive'] else 'DEAD':>8}  "
              f"drift={r['total_drift']:.4f}")

    print(f"\n  THE VERDICT:")
    all_ghosts_dead = all(
        not all_results[f"lambda_{vl}"]["ghost"]["alive"]
        for vl in void_lambdas)
    all_reg_alive = all(
        all_results[f"lambda_{vl}"]["regulated"]["alive"]
        for vl in void_lambdas)

    if all_ghosts_dead and all_reg_alive:
        print(f"  ALL GHOSTS DEAD. ALL REGULATED ALIVE.")
        print(f"  There is no passive reference because")
        print(f"  passive doesn't survive.")
        print(f"  Transport = survival + displacement.")
        print(f"  The regulator delivers both.")
    elif not all_ghosts_dead:
        print(f"  Some ghosts survived — compare displacements.")
    else:
        print(f"  Mixed results — check individual void levels.")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_ghost_packet_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v14 Ghost Packet Diagnostic",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "No spooks — three packets, same field, same start",
        "grid": nx,
        "steps": args.steps,
        "void_lambdas": void_lambdas,
        "results": all_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
