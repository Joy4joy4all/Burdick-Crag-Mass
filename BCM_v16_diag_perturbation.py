# -*- coding: utf-8 -*-
"""
BCM v16 -- Diagnostic 3: Perturbation Isolation Test
======================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Predicted Attack 3: "The measurement changes the substrate.
Your readings are artifacts of your own probes."

ChatGPT Attack Vector 5: "Observer loop is self-referential.
The craft navigates based on its own wake interpreted as
external structure."

This test runs TWO IDENTICAL transits through the same
hazard field:
  Run A: NO PROBES  (blind transit -- pumps only)
  Run B: 12 PROBES  (tunnel cycling, Bayesian navigation)

At every 100-step checkpoint, we snapshot sigma and lambda.
At the end, we compute:
  delta_sigma = sigma_B - sigma_A
  delta_lambda = lam_B - lam_A  (lambda is static here,
                 but sigma feedback may differ)

Metrics:
  1. Probe fingerprint: RMS of delta_sigma
  2. Hazard signal: RMS of sigma in the grave region
  3. Signal-to-noise: hazard_signal / probe_fingerprint
  4. Field correlation: spatial correlation between A and B

Kill condition: if probe fingerprint >= hazard signal,
the probes are blinding themselves. SNR < 1 = FAIL.

Usage:
    python BCM_v16_diag_perturbation.py
    python BCM_v16_diag_perturbation.py --steps 3000 --grid 256
"""

import numpy as np
import json
import os
import time
import math
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


# ═══════════════════════════════════════════════════════
# MINIMAL PROBE (no navigator -- just the perturbation)
# ═══════════════════════════════════════════════════════

class DiagProbe:
    """
    Stripped-down probe for perturbation measurement.
    Same state machine and arc geometry as tunnel_probes.py.
    No navigator logic -- we only care about the sigma
    field disturbance the probe causes by existing.

    The probe IS a sigma packet. When it exists on the
    grid, it adds its amplitude to the local sigma.
    This is the perturbation we are measuring.
    """
    def __init__(self, pid, eject_offset, probe_mass=0.1,
                 probe_width=2.0):
        self.pid = pid
        self.eject_offset = eject_offset
        self.probe_mass = probe_mass
        self.probe_width = probe_width
        self.position = np.array([0.0, 0.0])
        self.state = "TRANSIT"
        self.cycle_step = 0
        self.cycles_completed = 0
        self.arc_radius = 0.0

        self.transit_duration = 5
        self.arc_duration = 40
        self.fall_duration = 10

    def update(self, craft_com, pump_a_pos, pump_b_pos,
               step, nx, ny, rng):
        effective_step = step - self.eject_offset
        if effective_step < 0:
            self.position = craft_com.copy()
            self.state = "TRANSIT"
            return

        cycle_length = (self.transit_duration +
                        self.arc_duration +
                        self.fall_duration)
        self.cycle_step = effective_step % cycle_length
        self.cycles_completed = effective_step // cycle_length

        if self.cycle_step < self.transit_duration:
            self.state = "TRANSIT"
            t = self.cycle_step / self.transit_duration
            self.position = pump_b_pos + t * (pump_a_pos - pump_b_pos)

        elif self.cycle_step < self.transit_duration + self.arc_duration:
            self.state = "EJECTED"
            arc_step = self.cycle_step - self.transit_duration
            base_angle_offset = rng.uniform(-0.8, 0.8)
            vertex_count = 5 + (self.cycles_completed % 4)
            t_arc = arc_step / self.arc_duration
            arc_max_radius = 40.0 + rng.uniform(-10, 15)

            if t_arc < 0.5:
                self.arc_radius = arc_max_radius * (t_arc * 2)
            else:
                self.arc_radius = arc_max_radius * (2 - t_arc * 2)

            continuous_angle = base_angle_offset + t_arc * 2 * math.pi
            vertex_angle = (round(continuous_angle /
                                  (2 * math.pi / vertex_count))
                            * (2 * math.pi / vertex_count))
            arc_angle = 0.3 * continuous_angle + 0.7 * vertex_angle

            self.position = np.array([
                pump_a_pos[0] + self.arc_radius * np.cos(arc_angle),
                pump_a_pos[1] + self.arc_radius * np.sin(arc_angle),
            ])

        else:
            self.state = "FALLING"
            fall_step = (self.cycle_step - self.transit_duration
                         - self.arc_duration)
            t_fall = fall_step / self.fall_duration
            self.position = (self.position +
                             t_fall * (pump_b_pos - self.position))

    def stamp_sigma(self, sigma, nx, ny):
        """
        Add the probe's sigma footprint to the field.
        This IS the perturbation. The probe exists as a
        funded sigma packet on the grid.
        """
        if self.state != "EJECTED":
            return
        ix = int(np.clip(self.position[0], 0, nx - 1))
        iy = int(np.clip(self.position[1], 0, ny - 1))

        # Gaussian footprint centered on probe position
        x_arr = np.arange(nx)
        y_arr = np.arange(ny)
        X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')
        r2 = (X - self.position[0])**2 + (Y - self.position[1])**2
        footprint = self.probe_mass * np.exp(
            -r2 / (2 * self.probe_width**2))

        sigma += footprint


# ═══════════════════════════════════════════════════════
# SINGLE TRANSIT RUN
# ═══════════════════════════════════════════════════════

def run_transit(nx, ny, steps, dt, D, void_lambda, pump_A,
                ratio, alpha, separation, use_probes, rng_seed):
    """
    Run one transit. Returns final sigma, timeline of COM,
    and snapshots of sigma at checkpoints.
    """
    rng = np.random.RandomState(rng_seed)

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    # Lambda field with hazards (identical to tunnel_probes.py)
    lam_field = np.full((nx, ny), void_lambda, dtype=float)
    gx1 = nx // 3
    r2 = (X - gx1)**2 + (Y - ny//2)**2
    lam_field -= 0.04 * np.exp(-r2 / (2 * 12.0**2))
    gx2 = nx // 2
    r2 = (X - gx2)**2 + (Y - ny//2)**2
    lam_field -= 0.08 * np.exp(-r2 / (2 * 18.0**2))
    lam_field = np.maximum(lam_field, 0.001)

    # Sigma (craft)
    start_x = nx // 8
    start_y = ny // 2
    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    initial_com = compute_com(sigma)

    # Probes (if enabled)
    probes = []
    if use_probes:
        for i in range(12):
            probes.append(DiagProbe(i + 1, i * 5))

    timeline = []
    snapshots = {}

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        pump_a_pos = np.array([com[0] + separation, com[1]])
        pump_b_pos = np.array([com[0] - separation * 0.3, com[1]])

        # Pumps (identical in both runs)
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        actual_B = pump_A * ratio
        pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        # Sigma PDE
        lap = (np.roll(sigma, 1, 0) + np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) + np.roll(sigma, -1, 1) -
               4 * sigma)
        sigma_new = sigma + D * lap * dt - lam_field * sigma * dt
        if alpha > 0:
            sigma_new += alpha * (sigma - sigma_prev)
        sigma_new = np.maximum(sigma_new, 0)

        if float(np.max(sigma_new)) > 1e10:
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Probe cycling + stamping
        if use_probes:
            for probe in probes:
                probe.update(com, pump_a_pos, pump_b_pos,
                             step, nx, ny, rng)
                probe.stamp_sigma(sigma, nx, ny)

        # Checkpoint
        if step % 100 == 0:
            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(new_com - initial_com))
                coh = compute_coherence(sigma, new_com)
                timeline.append({
                    "step": step,
                    "x": round(float(new_com[0]), 2),
                    "drift": round(drift, 2),
                    "coherence": round(coh, 4),
                    "sigma_total": round(float(np.sum(sigma)), 4),
                    "sigma_max": round(float(np.max(sigma)), 6),
                })

        # Save snapshots at key steps
        if step in [500, 1000, 1500, 2000, 2500, 2999]:
            snapshots[step] = sigma.copy()

    return sigma, timeline, snapshots, lam_field


# ═══════════════════════════════════════════════════════
# MAIN DIAGNOSTIC
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Diagnostic 3: Perturbation Isolation")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v16 -- DIAGNOSTIC 3: PERTURBATION ISOLATION")
    print(f"  Does the probe distort what it measures?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    ratio = 0.25
    alpha = 0.80
    separation = 15.0

    # ── RUN A: NO PROBES (blind transit) ──
    print(f"\n  {'─'*55}")
    print(f"  RUN A: BLIND TRANSIT (no probes)")
    print(f"  {'─'*55}")

    sigma_A, timeline_A, snaps_A, lam_field = run_transit(
        nx, ny, args.steps, dt, D, void_lambda,
        pump_A, ratio, alpha, separation,
        use_probes=False, rng_seed=42)

    print(f"  Checkpoints: {len(timeline_A)}")
    if timeline_A:
        print(f"  Final drift: {timeline_A[-1]['drift']} px")
        print(f"  Final coherence: {timeline_A[-1]['coherence']}")

    # ── RUN B: WITH PROBES ──
    print(f"\n  {'─'*55}")
    print(f"  RUN B: PROBED TRANSIT (12 tunnel-cycling probes)")
    print(f"  {'─'*55}")

    sigma_B, timeline_B, snaps_B, _ = run_transit(
        nx, ny, args.steps, dt, D, void_lambda,
        pump_A, ratio, alpha, separation,
        use_probes=True, rng_seed=42)

    print(f"  Checkpoints: {len(timeline_B)}")
    if timeline_B:
        print(f"  Final drift: {timeline_B[-1]['drift']} px")
        print(f"  Final coherence: {timeline_B[-1]['coherence']}")

    # ═══════════════════════════════════════════════════
    # FIELD COMPARISON
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  PERTURBATION ANALYSIS")
    print(f"{'='*65}")

    # Hazard regions (same as tunnel_probes.py)
    gx1 = nx // 3   # shallow grave
    gx2 = nx // 2   # deep grave

    # Define grave region mask (within 20px of deep grave)
    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')
    grave_mask = ((X - gx2)**2 + (Y - ny//2)**2) < 20**2

    # Comparison at each snapshot step
    print(f"\n  {'Step':>6} {'Fingerprint':>12} {'GraveSignal':>12} "
          f"{'SNR':>8} {'Corr':>8} {'Verdict':>10}")
    print(f"  {'-'*6} {'-'*12} {'-'*12} {'-'*8} {'-'*8} {'-'*10}")

    snapshot_results = []

    for step in sorted(snaps_A.keys()):
        if step not in snaps_B:
            continue

        sA = snaps_A[step]
        sB = snaps_B[step]

        # Delta field: the probe fingerprint
        delta = sB - sA

        # Probe fingerprint: RMS of delta across entire field
        fingerprint_rms = float(np.sqrt(np.mean(delta**2)))

        # Hazard signal: RMS of sigma_A in the grave region
        # (what the probes SHOULD be detecting)
        grave_signal_rms = float(np.sqrt(
            np.mean(sA[grave_mask]**2)))

        # Signal-to-noise
        if fingerprint_rms > 1e-15:
            snr = grave_signal_rms / fingerprint_rms
        else:
            snr = float('inf')

        # Spatial correlation between A and B fields
        # (1.0 = identical, <1.0 = probes changed the field)
        a_flat = sA.flatten()
        b_flat = sB.flatten()
        if np.std(a_flat) > 1e-15 and np.std(b_flat) > 1e-15:
            corr = float(np.corrcoef(a_flat, b_flat)[0, 1])
        else:
            corr = 1.0

        verdict = "PASS" if snr > 1.0 else "FAIL"

        snapshot_results.append({
            "step": step,
            "fingerprint_rms": round(fingerprint_rms, 8),
            "grave_signal_rms": round(grave_signal_rms, 8),
            "snr": round(snr, 4) if snr != float('inf') else "inf",
            "correlation": round(corr, 8),
            "verdict": verdict,
        })

        snr_str = f"{snr:.2f}" if snr != float('inf') else "inf"
        print(f"  {step:>6} {fingerprint_rms:>12.8f} "
              f"{grave_signal_rms:>12.8f} {snr_str:>8} "
              f"{corr:>8.6f} {verdict:>10}")

    # ── FIELD-WIDE COMPARISON AT FINAL STEP ──
    delta_final = sigma_B - sigma_A
    fp_final = float(np.sqrt(np.mean(delta_final**2)))
    grave_final = float(np.sqrt(np.mean(sigma_A[grave_mask]**2)))
    snr_final = grave_final / fp_final if fp_final > 1e-15 else float('inf')
    max_delta = float(np.max(np.abs(delta_final)))
    mean_delta = float(np.mean(np.abs(delta_final)))

    # Where is the fingerprint strongest?
    max_delta_loc = np.unravel_index(
        np.argmax(np.abs(delta_final)), delta_final.shape)

    print(f"\n  FINAL FIELD COMPARISON (step {args.steps - 1}):")
    print(f"    Max |delta_sigma|:   {max_delta:.8f}")
    print(f"    Mean |delta_sigma|:  {mean_delta:.8f}")
    print(f"    Max delta location:  ({max_delta_loc[0]}, "
          f"{max_delta_loc[1]})")
    print(f"    Grave center:        ({gx2}, {ny//2})")
    print(f"    Distance from grave: "
          f"{np.sqrt((max_delta_loc[0]-gx2)**2 + (max_delta_loc[1]-ny//2)**2):.1f} px")

    # ── DRIFT COMPARISON ──
    print(f"\n  TRAJECTORY COMPARISON:")
    if timeline_A and timeline_B:
        for i in range(0, min(len(timeline_A), len(timeline_B)),
                       max(1, len(timeline_A)//6)):
            tA = timeline_A[i]
            tB = timeline_B[i]
            dx = tB['x'] - tA['x']
            print(f"    step {tA['step']:>5}: "
                  f"blind x={tA['x']:>8.2f}  "
                  f"probed x={tB['x']:>8.2f}  "
                  f"delta_x={dx:>+8.4f}")

    # ═══════════════════════════════════════════════════
    # VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    all_pass = all(r["verdict"] == "PASS" for r in snapshot_results)
    min_snr = min((r["snr"] if r["snr"] != "inf" else 1e6)
                  for r in snapshot_results) if snapshot_results else 0

    if all_pass and snr_final > 1.0:
        print(f"  DIAGNOSTIC 3: PASS")
        print(f"  Probe fingerprint is smaller than hazard signal.")
        print(f"  Final SNR: {snr_final:.2f}")
        print(f"  Minimum SNR across all checkpoints: {min_snr:.2f}")
        print(f"  The probes are NOT blinding themselves.")
        print(f"  Observer perturbation < environmental signal.")
    else:
        print(f"  DIAGNOSTIC 3: FAIL")
        print(f"  Probe fingerprint >= hazard signal at one or more steps.")
        print(f"  Final SNR: {snr_final:.4f}")
        print(f"  The probes ARE reading their own wake.")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_diag_perturbation_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v16 Diagnostic 3: Perturbation Isolation",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Separate probe fingerprint from hazard signal",
        "grid": nx,
        "steps": args.steps,
        "run_A": "blind (no probes)",
        "run_B": "probed (12 tunnel-cycling)",
        "final_snr": round(snr_final, 4) if snr_final != float('inf') else "inf",
        "final_fingerprint_rms": round(fp_final, 8),
        "final_grave_signal_rms": round(grave_final, 8),
        "max_delta_sigma": round(max_delta, 8),
        "max_delta_location": list(max_delta_loc),
        "verdict": "PASS" if (all_pass and snr_final > 1.0) else "FAIL",
        "snapshots": snapshot_results,
        "timeline_blind": timeline_A,
        "timeline_probed": timeline_B,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
