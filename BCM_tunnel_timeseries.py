# -*- coding: utf-8 -*-
"""
BCM v8 Tunnel Time-Series — Turnstile Diagnostics
===================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Instruments the existing solver callback to capture L1 tunnel
diagnostics at every 1000-step interval. Produces a time-series
of the bridge formation, stress, and settlement.

No solver math is modified. This is a measurement overlay.

What it measures at L1 per timestep:
  - rho amplitude (wave field energy at the tunnel)
  - sigma amplitude (memory field energy at the tunnel)
  - phase alignment between rho and sigma (local cos_delta_phi)
  - curl (vorticity at the throat)
  - rho/sigma ratio (instantaneous coupling)

Usage:
    python BCM_tunnel_timeseries.py --pair Spica --phase 0.0
    python BCM_tunnel_timeseries.py --pair Alpha_Cen --phase 0.5
"""

import numpy as np
import json
import os
import time
import argparse


class TunnelMonitor:
    """Captures diagnostics at three points along the bridge axis:
       mid_A (between pump A and L1), L1 (throat), mid_B (between L1 and pump B).
       Sigma-drift detected by comparing sig_amp across the three points."""

    def __init__(self, l1_coord, pump_A, pump_B, radius=8, settle=25000):
        self.l1x, self.l1y = l1_coord
        # Midpoint between pump A and L1
        self.mid_ax = (pump_A[0] + l1_coord[0]) // 2
        self.mid_ay = (pump_A[1] + l1_coord[1]) // 2
        # Midpoint between L1 and pump B
        self.mid_bx = (l1_coord[0] + pump_B[0]) // 2
        self.mid_by = (l1_coord[1] + pump_B[1]) // 2
        self.r = radius
        self.settle = settle
        self.history = []

    def _sample_region(self, field, cx, cy, grid):
        """Extract max, mean from a square region around (cx, cy)."""
        r = min(self.r, grid // 16)
        y0 = max(0, cy - r)
        y1 = min(grid, cy + r)
        x0 = max(0, cx - r)
        x1 = min(grid, cx + r)
        region = field[y0:y1, x0:x1]
        return float(np.max(np.abs(region))), float(np.mean(np.abs(region)))

    def callback(self, step, total, rho, sigma):
        """
        Called every 1000 solver steps.
        rho, sigma: (layers, grid, grid) arrays.
        Samples three points along the bridge axis.
        """
        # Layer sum — full entangled field
        rho_field = rho.sum(axis=0)
        sig_field = sigma.sum(axis=0)
        grid = rho_field.shape[0]

        # Sample all three points
        rho_l1_amp, rho_l1_mean = self._sample_region(
            rho_field, self.l1x, self.l1y, grid)
        sig_l1_amp, sig_l1_mean = self._sample_region(
            sig_field, self.l1x, self.l1y, grid)

        rho_ma_amp, _ = self._sample_region(
            rho_field, self.mid_ax, self.mid_ay, grid)
        sig_ma_amp, _ = self._sample_region(
            sig_field, self.mid_ax, self.mid_ay, grid)

        rho_mb_amp, _ = self._sample_region(
            rho_field, self.mid_bx, self.mid_by, grid)
        sig_mb_amp, _ = self._sample_region(
            sig_field, self.mid_bx, self.mid_by, grid)

        # Local phase alignment at L1
        r = min(self.r, grid // 16)
        y0 = max(0, self.l1y - r)
        y1 = min(grid, self.l1y + r)
        x0 = max(0, self.l1x - r)
        x1 = min(grid, self.l1x + r)
        rho_l1 = rho_field[y0:y1, x0:x1]
        sig_l1 = sig_field[y0:y1, x0:x1]

        rho_profile = rho_l1.mean(axis=0)
        sig_profile = sig_l1.mean(axis=0)
        n_half = len(rho_profile) // 2

        cos_dphi_local = 1.0
        if n_half >= 2:
            rho_fft = np.fft.fft(rho_profile)
            sig_fft = np.fft.fft(sig_profile)
            rho_dom = np.argmax(np.abs(rho_fft[1:n_half])) + 1
            sig_dom = np.argmax(np.abs(sig_fft[1:n_half])) + 1
            phase_rho = float(np.angle(rho_fft[rho_dom]))
            phase_sig = float(np.angle(sig_fft[sig_dom]))
            delta = float(np.angle(np.exp(1j * (phase_sig - phase_rho))))
            cos_dphi_local = float(np.cos(delta))

        # Local curl at L1
        grad_y, grad_x = np.gradient(rho_field)
        curl_field = np.gradient(grad_y, axis=1) - np.gradient(grad_x, axis=0)
        curl_l1_region = curl_field[y0:y1, x0:x1]
        curl_max = float(np.max(np.abs(curl_l1_region)))

        # Coupling ratio at L1
        coupling = sig_l1_amp / rho_l1_amp if rho_l1_amp > 0 else 0.0

        # Sigma drift: positive = drifting toward A, negative = toward B
        sig_drift = sig_ma_amp - sig_mb_amp

        self.history.append({
            "step":           step,
            "phase":          "settle" if step < self.settle else "measure",
            # L1 throat
            "rho_l1_amp":     round(rho_l1_amp, 6),
            "rho_l1_mean":    round(rho_l1_mean, 6),
            "sig_l1_amp":     round(sig_l1_amp, 4),
            "cos_dphi_local": round(cos_dphi_local, 6),
            "curl_max":       curl_max,
            "coupling":       round(coupling, 4),
            # Flanking points
            "rho_midA_amp":   round(rho_ma_amp, 6),
            "sig_midA_amp":   round(sig_ma_amp, 4),
            "rho_midB_amp":   round(rho_mb_amp, 6),
            "sig_midB_amp":   round(sig_mb_amp, 4),
            # Drift diagnostic
            "sig_drift":      round(sig_drift, 4),
        })


def run_timeseries(pair_name="Spica", phase=0.0, grid=192,
                   settle=25000, measure=6000):
    """
    Run binary solver with tunnel monitoring at L1.
    """
    from BCM_stellar_overrides import (run_binary, BINARY_REGISTRY,
                                        build_binary_source)

    if pair_name not in BINARY_REGISTRY:
        print(f"ERROR: '{pair_name}' not in BINARY_REGISTRY.")
        print(f"Available: {list(BINARY_REGISTRY.keys())}")
        return

    pair = BINARY_REGISTRY[pair_name]

    print(f"\n{'='*65}")
    print(f"  BCM v8 TUNNEL TIME-SERIES — {pair_name}")
    print(f"  phase={phase:.2f}  grid={grid}")
    print(f"  settle={settle}  measure={measure}")
    print(f"  Callback interval: every 1000 steps")
    print(f"{'='*65}")

    # Build source to get L1 coordinates
    J_pre, info_pre = build_binary_source(pair, grid=grid,
                                           orbital_phase=phase)
    l1_coord = info_pre["L1"]
    print(f"  L1 coordinates: ({l1_coord[0]}, {l1_coord[1]})")
    print(f"  Star A: {info_pre['star_A']}  amp={info_pre['amp_A']:.1f}")
    print(f"  Star B: {info_pre['star_B']}  amp={info_pre['amp_B']:.1f}")
    print(f"{'='*65}")

    # Create monitor with three sample points along bridge axis
    pump_A = info_pre["pump_A"]
    pump_B = info_pre["pump_B"]
    monitor = TunnelMonitor(l1_coord, pump_A=pump_A, pump_B=pump_B,
                             radius=min(8, grid // 16), settle=settle)
    print(f"  Sample points:")
    print(f"    mid_A: ({monitor.mid_ax}, {monitor.mid_ay})")
    print(f"    L1:    ({l1_coord[0]}, {l1_coord[1]})")
    print(f"    mid_B: ({monitor.mid_bx}, {monitor.mid_by})")

    # Run solver with monitor callback
    print(f"\n  Running solver with tunnel instrumentation...")
    result, J, info = run_binary(
        pair_name, grid=grid, orbital_phase=phase,
        settle=settle, measure=measure,
        verbose=True, callback=monitor.callback)

    # Print time-series summary
    n_points = len(monitor.history)
    print(f"\n{'='*65}")
    print(f"  TUNNEL TIME-SERIES — {n_points} data points captured")
    print(f"{'='*65}")

    print(f"\n  {'step':>6} {'phase':>8} {'rho_L1':>10} {'sig_L1':>10} "
          f"{'cos_dphi':>10} {'curl_max':>12} {'sig_drift':>10}")
    print(f"  {'-'*6} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*12} {'-'*10}")

    for entry in monitor.history:
        print(f"  {entry['step']:>6} {entry['phase']:>8} "
              f"{entry['rho_l1_amp']:>10.4f} {entry['sig_l1_amp']:>10.2f} "
              f"{entry['cos_dphi_local']:>+10.6f} "
              f"{entry['curl_max']:>12.2e} {entry['sig_drift']:>+10.4f}")

    # Analyze transitions
    settle_entries = [e for e in monitor.history if e["phase"] == "settle"]
    measure_entries = [e for e in monitor.history if e["phase"] == "measure"]

    if settle_entries:
        first_coherent = None
        for e in settle_entries:
            if e["cos_dphi_local"] > 0.999:
                first_coherent = e["step"]
                break

        print(f"\n  TURNSTILE ANALYSIS:")
        print(f"    First coherence (cos>0.999): step {first_coherent}"
              if first_coherent is not None
              else f"    First coherence: NOT REACHED during settle")

        curl_values = [e["curl_max"] for e in settle_entries]
        curl_peak_idx = np.argmax(curl_values)
        curl_peak_step = settle_entries[curl_peak_idx]["step"]
        print(f"    Peak curl during settle: {max(curl_values):.2e} "
              f"at step {curl_peak_step}")

        rho_values = [e["rho_l1_amp"] for e in settle_entries]
        print(f"    Rho amplitude range: {min(rho_values):.4f} "
              f"to {max(rho_values):.4f}")

        # Sigma drift analysis
        drift_values = [e["sig_drift"] for e in settle_entries]
        drift_mean = np.mean(drift_values)
        drift_final = drift_values[-1] if drift_values else 0
        if drift_mean > 0.01:
            drift_verdict = "DRIFTING TOWARD A (colonization)"
        elif drift_mean < -0.01:
            drift_verdict = "DRIFTING TOWARD B (counter-flow)"
        else:
            drift_verdict = "BALANCED (symmetric bridge)"
        print(f"\n  SIGMA DRIFT ANALYSIS:")
        print(f"    Mean drift:  {drift_mean:+.4f}")
        print(f"    Final drift: {drift_final:+.4f}")
        print(f"    Verdict:     {drift_verdict}")

    if measure_entries:
        cos_values = [e["cos_dphi_local"] for e in measure_entries]
        cos_std = np.std(cos_values)
        print(f"\n  STABILITY ANALYSIS (measurement window):")
        print(f"    cos_dphi std:  {cos_std:.8f}")
        print(f"    cos_dphi mean: {np.mean(cos_values):+.6f}")

        coupling_values = [e["coupling"] for e in measure_entries]
        print(f"    coupling std:  {np.std(coupling_values):.6f}")
        print(f"    coupling mean: {np.mean(coupling_values):.4f}")

        drift_m = [e["sig_drift"] for e in measure_entries]
        print(f"    sig_drift mean: {np.mean(drift_m):+.4f}")
        print(f"    sig_drift std:  {np.std(drift_m):.4f}")

        verdict = "STABLE" if cos_std < 0.001 else "OSCILLATING"
        print(f"    Event status:  {verdict}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(base, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir,
        f"BCM_tunnel_{pair_name}_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title":        "BCM v8 Tunnel Time-Series",
        "author":       "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "pair":         pair_name,
        "phase":        phase,
        "grid":         grid,
        "settle":       settle,
        "measure":      measure,
        "sample_points": {
            "mid_A": [monitor.mid_ax, monitor.mid_ay],
            "L1":    list(l1_coord),
            "mid_B": [monitor.mid_bx, monitor.mid_by],
        },
        "star_A":       info.get("star_A", ""),
        "star_B":       info.get("star_B", ""),
        "amp_A":        info.get("amp_A", 0),
        "amp_B":        info.get("amp_B", 0),
        "n_points":     n_points,
        "timeseries":   monitor.history,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")

    return monitor.history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v8 Tunnel Time-Series — Turnstile Diagnostics")
    parser.add_argument("--pair", type=str, default="Spica",
                        help="Binary pair name")
    parser.add_argument("--phase", type=float, default=0.0,
                        help="Orbital phase (0.0=periastron)")
    parser.add_argument("--grid", type=int, default=192,
                        help="Solver grid size")
    parser.add_argument("--settle", type=int, default=25000,
                        help="Solver settle steps")
    parser.add_argument("--measure", type=int, default=6000,
                        help="Solver measure steps")
    args = parser.parse_args()

    run_timeseries(pair_name=args.pair, phase=args.phase, grid=args.grid,
                   settle=args.settle, measure=args.measure)
