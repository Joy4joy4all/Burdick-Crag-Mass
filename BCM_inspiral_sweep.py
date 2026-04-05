# -*- coding: utf-8 -*-
"""
BCM v11 Binary Inspiral Sweep — Black Hole Merger Analog
==========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Sweeps two pumps from wide separation toward merger, measuring
substrate response at each step. Designed to compare against
LIGO GW150914 waveform structure.

The prediction: the 1D substrate signature is visible in the
inspiral chirp. The frequency sweep is the alternating time
cost accelerating as the corridor closes.

Usage:
    python BCM_inspiral_sweep.py
    python BCM_inspiral_sweep.py --grid 192 --steps 20
    python BCM_inspiral_sweep.py --amp-A 50 --amp-B 43
"""

import numpy as np
import json
import os
import time
import argparse


def build_inspiral_source(grid, pump_A_x, pump_B_x, amp_A, amp_B,
                           pump_y=None, width=None):
    """
    Build dual-pump source field with explicit pump positions.
    Returns J(layers, y, x) and info dict.
    """
    layers = 6
    if pump_y is None:
        pump_y = grid // 2
    if width is None:
        width = max(3, grid // 20)

    J = np.zeros((grid, grid))
    yy, xx = np.mgrid[0:grid, 0:grid]

    # Pump A
    r_A = np.sqrt((xx - pump_A_x)**2 + (yy - pump_y)**2)
    profile_A = amp_A * np.exp(-r_A**2 / (2 * width**2))

    # Pump B
    r_B = np.sqrt((xx - pump_B_x)**2 + (yy - pump_y)**2)
    profile_B = amp_B * np.exp(-r_B**2 / (2 * width**2))

    J = profile_A + profile_B

    # L1 is midpoint
    l1x = (pump_A_x + pump_B_x) // 2

    info = {
        "pump_A": (pump_A_x, pump_y),
        "pump_B": (pump_B_x, pump_y),
        "L1":     (l1x, pump_y),
        "amp_A":  amp_A,
        "amp_B":  amp_B,
        "sep_px": pump_B_x - pump_A_x,
    }

    return J, info


def run_inspiral_sweep(grid=128, amp_A=50.0, amp_B=43.0,
                        sep_start=0.60, sep_end=0.04, steps=15,
                        settle=15000, measure=5000):
    """
    Sweep two pumps from wide separation toward merger.
    Separation expressed as fraction of grid.

    GW150914 mass ratio: 36/29 = 1.24:1
    Default amps: 50/43 ~ 1.16:1 (close to GW150914)
    """
    from core.substrate_solver import SubstrateSolver

    print(f"\n{'='*65}")
    print(f"  BCM v11 BINARY INSPIRAL SWEEP")
    print(f"  Grid: {grid}  amp_A={amp_A}  amp_B={amp_B}")
    print(f"  Ratio: {amp_A/amp_B:.2f}:1")
    print(f"  Separation: {sep_start:.2f} → {sep_end:.2f} "
          f"({steps} steps)")
    print(f"  GW150914 analog: {amp_A/amp_B:.2f}:1 "
          f"(observed: 1.24:1)")
    print(f"{'='*65}")

    # Log-spaced separations (more resolution near merger)
    seps = np.logspace(np.log10(sep_start), np.log10(sep_end), steps)

    center = grid // 2

    print(f"\n  {'sep_frac':>8} {'sep_px':>6} {'cos_dphi':>10} "
          f"{'sig_drift':>10} {'rho_L1':>10} {'I_B':>8} "
          f"{'elapsed':>8}")
    print(f"  {'-'*8} {'-'*6} {'-'*10} {'-'*10} {'-'*10} "
          f"{'-'*8} {'-'*8}")

    results = []

    for si, sep_frac in enumerate(seps):
        sep_px = max(4, int(grid * sep_frac))
        pump_A_x = center - sep_px // 2
        pump_B_x = center + sep_px // 2

        if pump_A_x < 3 or pump_B_x >= grid - 3:
            print(f"  {sep_frac:.4f} — SKIP (pumps at grid edge)")
            continue

        # Build source
        J, info = build_inspiral_source(
            grid, pump_A_x, pump_B_x, amp_A, amp_B)

        # Run solver
        t0 = time.time()
        solver = SubstrateSolver(grid=grid, layers=6,
                                  lam=0.1, gamma=0.05,
                                  entangle=0.02, c_wave=1.0,
                                  settle=settle, measure=measure)
        result = solver.run(J, verbose=False)
        elapsed = time.time() - t0

        # Extract diagnostics
        cos_dphi = result.get("cos_delta_phi", 0)

        sigma_avg = result.get("sigma_avg")
        rho_avg = result.get("rho_avg")

        # Measure at L1
        l1x = info["L1"][0]
        l1y = info["L1"][1]
        r = max(3, grid // 32)

        def _sample(f, cx, cy):
            y0 = max(0, cy - r)
            y1 = min(grid, cy + r)
            x0 = max(0, cx - r)
            x1 = min(grid, cx + r)
            return float(np.max(np.abs(f[y0:y1, x0:x1])))

        sig_field = sigma_avg.sum(axis=0)
        rho_field = rho_avg.sum(axis=0)

        rho_l1 = _sample(rho_field, l1x, l1y)

        mid_ax = (pump_A_x + l1x) // 2
        mid_bx = (l1x + pump_B_x) // 2
        sig_ma = _sample(sig_field, mid_ax, l1y)
        sig_l1 = _sample(sig_field, l1x, l1y)
        sig_mb = _sample(sig_field, mid_bx, l1y)

        sig_drift = sig_ma - sig_mb
        i_b = sig_mb - sig_l1

        print(f"  {sep_frac:>8.4f} {sep_px:>6} {cos_dphi:>+10.6f} "
              f"{sig_drift:>+10.1f} {rho_l1:>10.1f} {i_b:>+8.1f} "
              f"{elapsed:>7.1f}s")

        results.append({
            "step":       si,
            "sep_frac":   round(float(sep_frac), 6),
            "sep_px":     sep_px,
            "pump_A_x":   pump_A_x,
            "pump_B_x":   pump_B_x,
            "cos_delta_phi": cos_dphi,
            "sig_drift":  round(sig_drift, 2),
            "rho_L1":     round(rho_l1, 2),
            "I_B":        round(i_b, 2),
            "corr_full":  result.get("corr_full", 0),
            "elapsed":    round(elapsed, 1),
        })

    # --- Summary ---
    print(f"\n  {'='*65}")
    print(f"  INSPIRAL SUMMARY")
    print(f"  {'='*65}")

    if results:
        rho_vals = [r["rho_L1"] for r in results]
        cos_vals = [r["cos_delta_phi"] for r in results]
        print(f"  rho_L1 range: {min(rho_vals):.1f} → {max(rho_vals):.1f}")
        print(f"  cos_dphi range: {min(cos_vals):.6f} → "
              f"{max(cos_vals):.6f}")
        print(f"  sig_drift range: {results[0]['sig_drift']:.0f} → "
              f"{results[-1]['sig_drift']:.0f}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_inspiral_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title":   "BCM v11 Binary Inspiral Sweep",
        "author":  "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "analog":  "GW150914 (36+29 solar masses, ratio 1.24:1)",
        "grid":    grid,
        "amp_A":   amp_A,
        "amp_B":   amp_B,
        "ratio":   round(amp_A / amp_B, 3),
        "sep_range": [round(sep_start, 4), round(sep_end, 4)],
        "n_runs":  len(results),
        "results": results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")

    return out_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v11 Binary Inspiral Sweep")
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--amp-A", type=float, default=50.0,
                        help="Pump A amplitude (default 50)")
    parser.add_argument("--amp-B", type=float, default=43.0,
                        help="Pump B amplitude (default 43)")
    parser.add_argument("--sep-start", type=float, default=0.60,
                        help="Starting separation (frac of grid)")
    parser.add_argument("--sep-end", type=float, default=0.04,
                        help="Final separation (frac of grid)")
    parser.add_argument("--steps", type=int, default=15,
                        help="Number of separation steps")
    parser.add_argument("--settle", type=int, default=15000)
    parser.add_argument("--measure", type=int, default=5000)
    args = parser.parse_args()

    run_inspiral_sweep(grid=args.grid,
                        amp_A=args.amp_A, amp_B=args.amp_B,
                        sep_start=args.sep_start, sep_end=args.sep_end,
                        steps=args.steps,
                        settle=args.settle, measure=args.measure)
