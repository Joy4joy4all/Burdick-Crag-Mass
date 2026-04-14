# -*- coding: utf-8 -*-
"""
BCM v13 SPINE — Self-Funded Ship Test
========================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems — Gemini advisory concept

The ship is not a passive sigma packet. It is a
self-funded 3D event — a micro-star that continuously
pumps the local substrate. The modulator creates the
gradient for drift. The pump creates the funding for
survival.

Tests:
  1. Passive packet vs self-funded ship in void
  2. Self-funded ship with drive through void
  3. Tunnel formation — does the ship leave a funded
     corridor behind it as it transits?
  4. Mass threshold — how much pump power keeps the
     ship alive at different void lambda levels?

Usage:
    python BCM_self_funded_ship.py
    python BCM_self_funded_ship.py --steps 3000 --grid 128
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


def compute_peak(sigma):
    return float(np.max(sigma))


def run_void_transit(steps, nx, ny, dt, D,
                      void_lambda, pump_strength,
                      drive_delta=0.025, use_drive=True,
                      label="TEST"):
    """
    Run a ship through void with optional self-funding pump.

    pump_strength = 0: passive packet (old behavior)
    pump_strength > 0: self-funded ship (continuous pump)

    The pump injects sigma at the ship's location every step,
    simulating a nuclear-powered substrate agitator.
    """
    center = (nx // 4, ny // 2)
    ship_pos = np.array(center, dtype=float)
    initial_pos = ship_pos.copy()

    # Initialize
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Start with Gaussian packet
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    # Void lambda field
    lam_bg = np.full((nx, ny), void_lambda)

    trajectory = []
    peaks = []
    coherences = []
    speeds = []
    pump_width = 4.0

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            print(f"    [{label}] DISSOLVED at step {step}")
            break

        # Self-funding pump: inject sigma at ship location
        if pump_strength > 0:
            r2_ship = ((X - com[0])**2 + (Y - com[1])**2)
            pump = pump_strength * np.exp(
                -r2_ship / (2 * pump_width**2))
            sigma += pump * dt

        # Drive dipole (if active)
        if use_drive and drive_delta > 0:
            d = np.array([1.0, 0.0])
            proj = (X - com[0]) * d[0] + (Y - com[1]) * d[1]
            drive = -drive_delta * np.tanh(proj / 6.0)
            lam_step = lam_bg + drive
        else:
            lam_step = lam_bg

        lam_step = np.maximum(lam_step, 0.005)

        # Diffusion
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt
        sigma -= lam_step * sigma * dt
        sigma = np.maximum(sigma, 0)

        # Measure
        peak = compute_peak(sigma)
        coh = compute_coherence(sigma, com)
        peaks.append(peak)
        coherences.append(coh)

        if len(trajectory) > 0:
            vel = com - trajectory[-1]
            speeds.append(float(np.linalg.norm(vel)))

        trajectory.append(com.copy())

        if step % 500 == 0:
            disp = com - initial_pos
            print(f"    [{label}] step={step:>5}  "
                  f"peak={peak:.6f}  coh={coh:.4f}  "
                  f"drift={np.linalg.norm(disp):.2f}")

    traj = np.array(trajectory) if trajectory else np.zeros((1, 2))
    disp = traj[-1] - traj[0] if len(traj) > 1 else np.zeros(2)

    # Measure tunnel: sigma along the path after transit
    midline = sigma[:, ny // 2]
    tunnel_profile = []
    for tx in range(0, nx, 4):
        tunnel_profile.append({
            "x": tx,
            "sigma": round(float(midline[tx]), 8),
        })

    survived = len(trajectory) >= steps and compute_peak(sigma) > 0.001

    return {
        "label": label,
        "void_lambda": void_lambda,
        "pump_strength": pump_strength,
        "drive_active": use_drive,
        "survived": survived,
        "steps_completed": len(trajectory),
        "total_drift": round(float(np.linalg.norm(disp)), 4),
        "mean_speed": round(float(np.mean(speeds)), 8) if speeds else 0,
        "peak_start": round(peaks[0], 6) if peaks else 0,
        "peak_end": round(peaks[-1], 6) if peaks else 0,
        "coherence_start": round(coherences[0], 4) if coherences else 0,
        "coherence_end": round(coherences[-1], 4) if coherences else 0,
        "min_coherence": round(min(coherences), 4) if coherences else 0,
        "tunnel_profile": tunnel_profile,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 Self-Funded Ship Test")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v13 SELF-FUNDED SHIP TEST")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"{'='*65}")

    results = []

    # TEST 1: Passive vs self-funded in void (no drive)
    print(f"\n  {'='*60}")
    print(f"  TEST 1: PASSIVE vs SELF-FUNDED (no drive)")
    print(f"  Void lambda = 0.12  No drive active.")
    print(f"  {'─'*60}")

    r1a = run_void_transit(args.steps, nx, ny, 0.05, 0.5,
                            void_lambda=0.12, pump_strength=0,
                            use_drive=False, label="PASSIVE")
    results.append(r1a)

    r1b = run_void_transit(args.steps, nx, ny, 0.05, 0.5,
                            void_lambda=0.12, pump_strength=0.5,
                            use_drive=False, label="FUNDED")
    results.append(r1b)

    print(f"\n  Passive: survived={r1a['survived']} "
          f"peak_end={r1a['peak_end']:.6f}")
    print(f"  Funded:  survived={r1b['survived']} "
          f"peak_end={r1b['peak_end']:.6f}")

    # TEST 2: Self-funded ship WITH drive through void
    print(f"\n  {'='*60}")
    print(f"  TEST 2: SELF-FUNDED SHIP WITH DRIVE")
    print(f"  Void lambda = 0.12  Drive + pump active.")
    print(f"  {'─'*60}")

    r2 = run_void_transit(args.steps, nx, ny, 0.05, 0.5,
                           void_lambda=0.12, pump_strength=0.5,
                           use_drive=True, drive_delta=0.025,
                           label="SHIP+DRIVE")
    results.append(r2)

    print(f"\n  Drift: {r2['total_drift']:.3f} px  "
          f"Speed: {r2['mean_speed']:.6f}  "
          f"Survived: {r2['survived']}")

    # TEST 3: Pump strength sweep — find minimum for survival
    print(f"\n  {'='*60}")
    print(f"  TEST 3: MINIMUM PUMP FOR VOID SURVIVAL")
    print(f"  Sweeping pump_strength at void lambda=0.12")
    print(f"  {'─'*60}")
    print(f"  {'Pump':>8} {'Peak_end':>10} {'Coh_end':>10} "
          f"{'Drift':>8} {'Survived':>10}")
    print(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*8} {'─'*10}")

    pumps = [0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 2.0]
    pump_results = []

    for pump in pumps:
        r = run_void_transit(min(2000, args.steps), nx, ny,
                              0.05, 0.5,
                              void_lambda=0.12,
                              pump_strength=pump,
                              use_drive=True,
                              label=f"P={pump}")
        pump_results.append(r)
        print(f"  {pump:>8.1f} {r['peak_end']:>10.6f} "
              f"{r['coherence_end']:>10.4f} "
              f"{r['total_drift']:>8.3f} "
              f"{'YES' if r['survived'] else 'DEAD':>10}")

    results.extend(pump_results)

    # Find threshold
    threshold_pump = None
    for r in pump_results:
        if r['survived'] and r['peak_end'] > 0.01:
            threshold_pump = r['pump_strength']
            break

    # TEST 4: Self-funded through different void levels
    print(f"\n  {'='*60}")
    print(f"  TEST 4: SELF-FUNDED SHIP vs VOID DEPTH")
    print(f"  Pump=0.5, drive active. Sweep void lambda.")
    print(f"  {'─'*60}")
    print(f"  {'Void_lam':>10} {'Peak_end':>10} {'Drift':>8} "
          f"{'Speed':>10} {'Survived':>10}")
    print(f"  {'─'*10} {'─'*10} {'─'*8} {'─'*10} {'─'*10}")

    void_results = []
    for vl in [0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30]:
        r = run_void_transit(min(2000, args.steps), nx, ny,
                              0.05, 0.5,
                              void_lambda=vl,
                              pump_strength=0.5,
                              use_drive=True,
                              label=f"V={vl}")
        void_results.append(r)
        print(f"  {vl:>10.2f} {r['peak_end']:>10.6f} "
              f"{r['total_drift']:>8.3f} "
              f"{r['mean_speed']:>10.6f} "
              f"{'YES' if r['survived'] else 'DEAD':>10}")

    results.extend(void_results)

    # Summary
    print(f"\n{'='*65}")
    print(f"  SELF-FUNDED SHIP SUMMARY")
    print(f"{'='*65}")
    print(f"  Passive packet in void:  "
          f"{'DISSOLVED' if not r1a['survived'] else 'survived'}")
    print(f"  Self-funded (no drive):  "
          f"{'SURVIVED' if r1b['survived'] else 'dissolved'} "
          f"(peak={r1b['peak_end']:.4f})")
    print(f"  Self-funded + drive:     "
          f"{'SURVIVED' if r2['survived'] else 'dissolved'} "
          f"(drift={r2['total_drift']:.2f}px)")
    if threshold_pump is not None:
        print(f"  Min pump for survival:   {threshold_pump}")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_self_funded_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 Self-Funded Ship Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "concept": "Gemini advisory — ship as self-funded sigma pump",
        "grid": nx,
        "steps": args.steps,
        "threshold_pump": threshold_pump,
        "results": results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
