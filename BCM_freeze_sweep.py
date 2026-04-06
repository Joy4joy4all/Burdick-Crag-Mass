# -*- coding: utf-8 -*-
"""
BCM v13 — Freeze Energy Gradient Sweep
=========================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

ChatGPT's deciding test: "freeze energy, vary gradient."

Fix total energy by normalizing sigma every step.
Sweep nabla_lambda. Measure drift.

If drift persists at fixed energy: transport is purely
geometric / entropic. Not energy-mediated. BCM confirmed.

If drift disappears at fixed energy: transport requires
energy budget. Different physics.

This is the test that decides everything.

Usage:
    python BCM_freeze_sweep.py
    python BCM_freeze_sweep.py --steps 2000 --grid 128
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


def run_frozen_drift(steps, nx, ny, dt, D,
                      delta_lam, void_lambda=0.10,
                      normalize_energy=True,
                      label="FROZEN"):
    """
    Run drift test with energy normalization.

    Each step:
    1. Build lambda dipole with given delta_lam
    2. Evolve sigma (diffusion + decay)
    3. NORMALIZE sigma so total energy is constant
    4. Measure COM displacement

    If drift exists after normalization, the transport
    is geometric, not energy-mediated.
    """
    center = (nx // 2, ny // 2)
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    # Reference energy (freeze at this level)
    E_ref = float(np.sum(sigma**2))

    lam_bg = np.full((nx, ny), void_lambda)

    trajectory = []
    energies = []
    coherences = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        # Drive dipole centered on COM
        d = np.array([1.0, 0.0])
        proj = (X - com[0]) * d[0] + (Y - com[1]) * d[1]
        drive = -delta_lam * np.tanh(proj / 6.0)
        lam_step = np.maximum(lam_bg + drive, 0.005)

        # Diffusion
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt

        # Decay
        sigma -= lam_step * sigma * dt
        sigma = np.maximum(sigma, 0)

        # NORMALIZE — freeze energy at E_ref
        if normalize_energy:
            E_current = float(np.sum(sigma**2))
            if E_current > 1e-15:
                scale = np.sqrt(E_ref / E_current)
                sigma *= scale

        # Track
        E_now = float(np.sum(sigma**2))
        energies.append(E_now)
        trajectory.append(com.copy())

        coh = compute_coherence(sigma, com)
        coherences.append(coh)

    traj = np.array(trajectory) if trajectory else np.zeros((1, 2))
    if len(traj) > 1:
        disp = traj[-1] - traj[0]
        total_drift = float(np.linalg.norm(disp))
    else:
        total_drift = 0

    # Energy variance (should be near zero if frozen)
    E_array = np.array(energies)
    E_cv = float(np.std(E_array) / np.mean(E_array)) if len(E_array) > 0 else 0

    return {
        "label": label,
        "delta_lam": delta_lam,
        "normalized": normalize_energy,
        "total_drift": round(total_drift, 6),
        "E_ref": round(E_ref, 6),
        "E_final": round(energies[-1], 6) if energies else 0,
        "E_cv": round(E_cv, 8),
        "coherence_end": round(coherences[-1], 4) if coherences else 0,
        "steps_completed": len(trajectory),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 Freeze Energy Gradient Sweep")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v13 FREEZE ENERGY GRADIENT SWEEP")
    print(f"  ChatGPT's Deciding Test")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"{'='*65}")

    results = []

    # ============================================================
    # TEST 1: Gradient sweep with FROZEN energy
    # ============================================================
    print(f"\n  {'='*60}")
    print(f"  TEST 1: FROZEN ENERGY — GRADIENT SWEEP")
    print(f"  {'='*60}")
    print(f"  Energy normalized every step. Only gradient varies.")
    print(f"  If drift exists: transport is geometric.")
    print(f"  If drift = 0: transport requires energy.")
    print(f"  {'─'*60}")

    deltas = [0.000, 0.005, 0.010, 0.025, 0.050, 0.075, 0.100]

    print(f"  {'delta_lam':>10} {'Drift (px)':>12} {'E_final':>10} "
          f"{'E_cv':>12} {'Coh':>8} {'Verdict':>12}")
    print(f"  {'─'*10} {'─'*12} {'─'*10} {'─'*12} {'─'*8} "
          f"{'─'*12}")

    for dl in deltas:
        r = run_frozen_drift(args.steps, nx, ny, 0.05, 0.5,
                              delta_lam=dl, normalize_energy=True,
                              label=f"FROZEN_dl={dl}")
        results.append(r)

        if dl == 0:
            verdict = "CONTROL"
        elif r["total_drift"] > 0.1:
            verdict = "GEOMETRIC"
        else:
            verdict = "NO DRIFT"

        print(f"  {dl:>10.3f} {r['total_drift']:>12.6f} "
              f"{r['E_final']:>10.4f} {r['E_cv']:>12.8f} "
              f"{r['coherence_end']:>8.4f} {verdict:>12}")

    # ============================================================
    # TEST 2: Same sweep WITHOUT energy normalization (comparison)
    # ============================================================
    print(f"\n  {'='*60}")
    print(f"  TEST 2: FREE ENERGY — SAME GRADIENT SWEEP")
    print(f"  {'='*60}")
    print(f"  No normalization. Energy evolves freely.")
    print(f"  {'─'*60}")

    free_results = []

    print(f"  {'delta_lam':>10} {'Drift (px)':>12} {'E_final':>10} "
          f"{'E_cv':>12} {'Coh':>8}")
    print(f"  {'─'*10} {'─'*12} {'─'*10} {'─'*12} {'─'*8}")

    for dl in deltas:
        r = run_frozen_drift(args.steps, nx, ny, 0.05, 0.5,
                              delta_lam=dl, normalize_energy=False,
                              label=f"FREE_dl={dl}")
        free_results.append(r)

        print(f"  {dl:>10.3f} {r['total_drift']:>12.6f} "
              f"{r['E_final']:>10.4f} {r['E_cv']:>12.8f} "
              f"{r['coherence_end']:>8.4f}")

    results.extend(free_results)

    # ============================================================
    # TEST 3: v proportional to nabla_lambda at fixed energy?
    # ============================================================
    print(f"\n  {'='*60}")
    print(f"  TEST 3: v vs nabla_lambda (FROZEN)")
    print(f"  {'='*60}")
    print(f"  Does v scale linearly with gradient at fixed energy?")
    print(f"  {'─'*60}")

    frozen_drifts = [(r["delta_lam"], r["total_drift"])
                      for r in results[:len(deltas)]
                      if r["normalized"]]

    if len(frozen_drifts) > 2:
        dls = [d[0] for d in frozen_drifts if d[0] > 0]
        drs = [d[1] for d in frozen_drifts if d[0] > 0]

        if len(dls) > 1:
            # Check linearity: ratio of drift to delta_lam
            ratios = [dr / dl for dl, dr in zip(dls, drs) if dl > 0]
            ratio_cv = float(np.std(ratios) / np.mean(ratios)) if ratios else 0

            print(f"  Drift/gradient ratios:")
            for dl, dr in zip(dls, drs):
                ratio = dr / dl if dl > 0 else 0
                print(f"    dl={dl:.3f}  drift={dr:.6f}  "
                      f"ratio={ratio:.4f}")

            print(f"\n  Ratio CV: {ratio_cv:.4f}")
            if ratio_cv < 0.15:
                print(f"  v ~ nabla_lambda CONFIRMED (linear regime)")
            elif ratio_cv < 0.30:
                print(f"  v ~ nabla_lambda APPROXIMATELY (sublinear)")
            else:
                print(f"  v ~ nabla_lambda NOT LINEAR")

    # ============================================================
    # SUMMARY
    # ============================================================
    print(f"\n{'='*65}")
    print(f"  FREEZE SWEEP SUMMARY")
    print(f"{'='*65}")

    frozen_control = results[0]  # delta_lam = 0
    frozen_max = results[-1] if results[0]["normalized"] else results[len(deltas)-1]

    print(f"  Control (dl=0, frozen):  drift = "
          f"{frozen_control['total_drift']:.6f}")

    # Find max frozen drift
    max_frozen = max([r for r in results[:len(deltas)]],
                      key=lambda r: r["total_drift"])
    print(f"  Max frozen drift:        drift = "
          f"{max_frozen['total_drift']:.6f} at dl="
          f"{max_frozen['delta_lam']:.3f}")

    print(f"\n  THE DECIDING QUESTION:")
    if max_frozen["total_drift"] > 0.1:
        print(f"  DRIFT EXISTS AT FIXED ENERGY.")
        print(f"  Transport is GEOMETRIC / ENTROPIC.")
        print(f"  Not energy-mediated. Gradient IS the mover.")
        print(f"")
        print(f"  In BCM terms: gravity is not a force.")
        print(f"  It is the substrate's memory gradient.")
        print(f"  Objects move toward lower lambda because")
        print(f"  survival probability is higher there.")
        print(f"  No energy exchange required. Pure geometry.")
    else:
        print(f"  DRIFT REQUIRES ENERGY.")
        print(f"  Transport is energy-mediated.")
        print(f"  Different physics than BCM predicts.")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_freeze_sweep_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 Freeze Energy Gradient Sweep",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "ChatGPT deciding test — geometric vs energy transport",
        "grid": nx,
        "steps": args.steps,
        "results": results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
