# -*- coding: utf-8 -*-
"""
BCM v16 -- Diagnostic 3B: Perturbation Decomposition
======================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

ChatGPT demanded 3-run decomposition before any further
diagnostics. CERN fracture 6 demands sensor/actuator
separation. Fracture 4 demands reverse-field test.

FOUR RUNS, identical hazard field, identical pumps:

  Run A: NO PROBES         (baseline)
  Run B: PASSIVE PROBES    (read-only, zero injection)
  Run C: ACTIVE PROBES     (stamp sigma, current model)
  Run D: REVERSE PROBES    (negative injection, anti-stamp)

Decomposition:
  delta_substrate = B - A   (passive probe effect on solver)
  delta_probe     = C - B   (injection-only effect)
  delta_reverse   = D - B   (reverse injection effect)

Kill conditions:
  1. If |delta_substrate| is NOT near zero, passive probes
     somehow change the field -> sampling is contaminated
  2. If |delta_probe| >= |hazard signal| -> observer blinds
  3. If Run D drift INCREASES -> artifact (fracture 4 kills)
     If Run D drift DECREASES -> physical coupling confirmed

Usage:
    python BCM_v16_diag_decomposition.py
    python BCM_v16_diag_decomposition.py --steps 3000 --grid 256
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
# DECOMPOSITION PROBE
# ═══════════════════════════════════════════════════════

class DecompProbe:
    """
    Probe with configurable injection mode:
      mode='passive'  -> reads field, stamps nothing
      mode='active'   -> reads field, stamps +sigma
      mode='reverse'  -> reads field, stamps -sigma
    """
    def __init__(self, pid, eject_offset, mode='passive',
                 probe_mass=0.1, probe_width=2.0):
        self.pid = pid
        self.eject_offset = eject_offset
        self.mode = mode
        self.probe_mass = probe_mass
        self.probe_width = probe_width
        self.position = np.array([0.0, 0.0])
        self.state = "TRANSIT"
        self.cycle_step = 0
        self.cycles_completed = 0
        self.total_reads = 0
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
            return False  # not sampling

        cycle_length = (self.transit_duration +
                        self.arc_duration +
                        self.fall_duration)
        self.cycle_step = effective_step % cycle_length
        self.cycles_completed = effective_step // cycle_length

        if self.cycle_step < self.transit_duration:
            self.state = "TRANSIT"
            t = self.cycle_step / self.transit_duration
            self.position = (pump_b_pos +
                             t * (pump_a_pos - pump_b_pos))
            return False

        elif self.cycle_step < (self.transit_duration +
                                self.arc_duration):
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

            continuous_angle = (base_angle_offset +
                                t_arc * 2 * math.pi)
            vertex_angle = (
                round(continuous_angle /
                      (2 * math.pi / vertex_count))
                * (2 * math.pi / vertex_count))
            arc_angle = (0.3 * continuous_angle +
                         0.7 * vertex_angle)

            self.position = np.array([
                pump_a_pos[0] +
                self.arc_radius * np.cos(arc_angle),
                pump_a_pos[1] +
                self.arc_radius * np.sin(arc_angle),
            ])
            self.total_reads += 1
            return True  # sampling this step

        else:
            self.state = "FALLING"
            fall_step = (self.cycle_step -
                         self.transit_duration -
                         self.arc_duration)
            t_fall = fall_step / self.fall_duration
            self.position = (self.position +
                             t_fall *
                             (pump_b_pos - self.position))
            return False

    def stamp_sigma(self, sigma, nx, ny):
        """Apply probe footprint based on mode."""
        if self.state != "EJECTED":
            return
        if self.mode == 'passive':
            return  # read-only, no stamp

        x_arr = np.arange(nx)
        y_arr = np.arange(ny)
        X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')
        r2 = ((X - self.position[0])**2 +
              (Y - self.position[1])**2)
        footprint = self.probe_mass * np.exp(
            -r2 / (2 * self.probe_width**2))

        if self.mode == 'active':
            sigma += footprint
        elif self.mode == 'reverse':
            sigma -= footprint
            np.maximum(sigma, 0, out=sigma)


# ═══════════════════════════════════════════════════════
# SINGLE TRANSIT RUN
# ═══════════════════════════════════════════════════════

def run_transit(nx, ny, steps, dt, D, void_lambda, pump_A,
                ratio, alpha, separation,
                probe_mode, rng_seed):
    """
    Run one transit.
    probe_mode: 'none', 'passive', 'active', 'reverse'
    Returns: final sigma, timeline list
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

    # Build probes
    probes = []
    if probe_mode != 'none':
        for i in range(12):
            probes.append(DecompProbe(
                pid=i + 1,
                eject_offset=i * 5,
                mode=probe_mode,
            ))

    timeline = []
    snapshots = {}

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        pump_a_pos = np.array([com[0] + separation, com[1]])
        pump_b_pos = np.array([com[0] - separation * 0.3,
                               com[1]])

        # Pumps
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        actual_B = pump_A * ratio
        pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        # Sigma PDE
        lap = (np.roll(sigma, 1, 0) +
               np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) +
               np.roll(sigma, -1, 1) - 4 * sigma)
        sigma_new = (sigma + D * lap * dt -
                     lam_field * sigma * dt)
        if alpha > 0:
            sigma_new += alpha * (sigma - sigma_prev)
        sigma_new = np.maximum(sigma_new, 0)

        if float(np.max(sigma_new)) > 1e10:
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Probe cycling
        for probe in probes:
            probe.update(com, pump_a_pos, pump_b_pos,
                         step, nx, ny, rng)
            probe.stamp_sigma(sigma, nx, ny)

        # Checkpoint every 100 steps
        if step % 100 == 0:
            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(
                    new_com - initial_com))
                coh = compute_coherence(sigma, new_com)
                timeline.append({
                    "step": step,
                    "x": round(float(new_com[0]), 2),
                    "drift": round(drift, 2),
                    "coherence": round(coh, 4),
                    "sigma_total": round(
                        float(np.sum(sigma)), 4),
                    "sigma_max": round(
                        float(np.max(sigma)), 6),
                })

        # Snapshots at key steps
        if step in [500, 1000, 1500, 2000, 2500, 2999]:
            snapshots[step] = sigma.copy()

    return sigma, timeline, snapshots, lam_field


# ═══════════════════════════════════════════════════════
# MAIN DIAGNOSTIC
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Diagnostic 3B: Decomposition")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v16 -- DIAGNOSTIC 3B: PERTURBATION DECOMPOSITION")
    print(f"  4-run test: none / passive / active / reverse")
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

    gx2 = nx // 2  # deep grave center

    runs = {}
    run_order = [
        ("A_none",    "none"),
        ("B_passive", "passive"),
        ("C_active",  "active"),
        ("D_reverse", "reverse"),
    ]

    for label, mode in run_order:
        desc = {
            "none": "NO PROBES (baseline)",
            "passive": "PASSIVE PROBES (read-only)",
            "active": "ACTIVE PROBES (stamp +sigma)",
            "reverse": "REVERSE PROBES (stamp -sigma)",
        }[mode]

        print(f"\n  {'─'*55}")
        print(f"  RUN {label}: {desc}")
        print(f"  {'─'*55}")

        sigma, timeline, snaps, lam_field = run_transit(
            nx, ny, args.steps, dt, D, void_lambda,
            pump_A, ratio, alpha, separation,
            probe_mode=mode, rng_seed=42)

        runs[label] = {
            "sigma": sigma,
            "timeline": timeline,
            "snapshots": snaps,
        }

        if timeline:
            print(f"  Final drift:     {timeline[-1]['drift']} px")
            print(f"  Final coherence: {timeline[-1]['coherence']}")
            print(f"  Final x:         {timeline[-1]['x']}")

    # ═══════════════════════════════════════════════════
    # DECOMPOSITION ANALYSIS
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  DECOMPOSITION ANALYSIS")
    print(f"{'='*65}")

    # Grave mask
    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')
    grave_mask = ((X - gx2)**2 + (Y - ny//2)**2) < 20**2

    sig_A = runs["A_none"]["sigma"]
    sig_B = runs["B_passive"]["sigma"]
    sig_C = runs["C_active"]["sigma"]
    sig_D = runs["D_reverse"]["sigma"]

    # Decomposition deltas
    delta_substrate = sig_B - sig_A   # passive probe effect
    delta_probe = sig_C - sig_B       # injection-only effect
    delta_reverse = sig_D - sig_B     # reverse injection effect

    rms_substrate = float(np.sqrt(np.mean(delta_substrate**2)))
    rms_probe = float(np.sqrt(np.mean(delta_probe**2)))
    rms_reverse = float(np.sqrt(np.mean(delta_reverse**2)))
    rms_grave = float(np.sqrt(np.mean(sig_A[grave_mask]**2)))

    max_substrate = float(np.max(np.abs(delta_substrate)))
    max_probe = float(np.max(np.abs(delta_probe)))
    max_reverse = float(np.max(np.abs(delta_reverse)))

    print(f"\n  FIELD DELTAS (RMS over full grid):")
    print(f"    delta_substrate (B-A): {rms_substrate:.8f}")
    print(f"    delta_probe     (C-B): {rms_probe:.8f}")
    print(f"    delta_reverse   (D-B): {rms_reverse:.8f}")
    print(f"    grave signal (A):      {rms_grave:.8f}")

    print(f"\n  FIELD DELTAS (MAX absolute):")
    print(f"    delta_substrate (B-A): {max_substrate:.8f}")
    print(f"    delta_probe     (C-B): {max_probe:.8f}")
    print(f"    delta_reverse   (D-B): {max_reverse:.8f}")

    # ── KILL CONDITION 1: Passive probe contamination ──
    print(f"\n  {'─'*55}")
    print(f"  KILL CONDITION 1: Passive probe contamination")
    passive_clean = rms_substrate < 1e-6
    print(f"    RMS delta_substrate: {rms_substrate:.8f}")
    print(f"    Threshold: < 1e-6")
    print(f"    Verdict: {'PASS -- passive probes do NOT contaminate' if passive_clean else 'FAIL -- passive probes change the field'}")

    # ── KILL CONDITION 2: Probe signal vs grave ──
    print(f"\n  {'─'*55}")
    print(f"  KILL CONDITION 2: Probe injection vs hazard signal")
    if rms_probe > 1e-15:
        snr = rms_grave / rms_probe
    else:
        snr = float('inf')
    probe_separable = snr > 1.0
    print(f"    Grave signal RMS:  {rms_grave:.8f}")
    print(f"    Probe inject RMS:  {rms_probe:.8f}")
    print(f"    SNR (grave/probe): {snr:.4f}")
    print(f"    Verdict: {'PASS -- hazard > probe fingerprint' if probe_separable else 'FAIL -- probe blinds sensor'}")

    # ── KILL CONDITION 3: Reverse-field test ──
    print(f"\n  {'─'*55}")
    print(f"  KILL CONDITION 3: Reverse-field (fracture 4)")
    drift_A = runs["A_none"]["timeline"][-1]["drift"] if runs["A_none"]["timeline"] else 0
    drift_B = runs["B_passive"]["timeline"][-1]["drift"] if runs["B_passive"]["timeline"] else 0
    drift_C = runs["C_active"]["timeline"][-1]["drift"] if runs["C_active"]["timeline"] else 0
    drift_D = runs["D_reverse"]["timeline"][-1]["drift"] if runs["D_reverse"]["timeline"] else 0

    print(f"    Drift A (none):    {drift_A:.2f} px")
    print(f"    Drift B (passive): {drift_B:.2f} px")
    print(f"    Drift C (active):  {drift_C:.2f} px")
    print(f"    Drift D (reverse): {drift_D:.2f} px")

    # If reverse drift >= active drift -> artifact
    reverse_physical = drift_D < drift_C
    # Stronger test: reverse should reduce drift vs passive
    reverse_reduces = drift_D < drift_B

    if drift_D >= drift_C:
        rev_verdict = "FAIL -- reverse injection INCREASES drift = ARTIFACT"
    elif drift_D >= drift_B:
        rev_verdict = ("CAUTION -- reverse does not reduce below "
                       "passive baseline")
    else:
        rev_verdict = ("PASS -- reverse injection REDUCES drift = "
                       "PHYSICAL COUPLING")
    print(f"    Verdict: {rev_verdict}")

    # ── TRAJECTORY COMPARISON ──
    print(f"\n  {'─'*55}")
    print(f"  TRAJECTORY COMPARISON (every 500 steps)")
    print(f"  {'Step':>6} {'A(none)':>10} {'B(pass)':>10} "
          f"{'C(actv)':>10} {'D(rev)':>10}")
    print(f"  {'-'*6} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    traj_comparison = []
    max_steps_check = min(
        len(runs["A_none"]["timeline"]),
        len(runs["B_passive"]["timeline"]),
        len(runs["C_active"]["timeline"]),
        len(runs["D_reverse"]["timeline"]),
    )

    for i in range(0, max_steps_check, 5):
        tA = runs["A_none"]["timeline"][i]
        tB = runs["B_passive"]["timeline"][i]
        tC = runs["C_active"]["timeline"][i]
        tD = runs["D_reverse"]["timeline"][i]

        traj_comparison.append({
            "step": tA["step"],
            "x_none": tA["x"],
            "x_passive": tB["x"],
            "x_active": tC["x"],
            "x_reverse": tD["x"],
        })

        print(f"  {tA['step']:>6} {tA['x']:>10.2f} "
              f"{tB['x']:>10.2f} {tC['x']:>10.2f} "
              f"{tD['x']:>10.2f}")

    # ── SNAPSHOT DECOMPOSITION AT KEY STEPS ──
    print(f"\n  {'─'*55}")
    print(f"  SNAPSHOT DECOMPOSITION")
    print(f"  {'Step':>6} {'dSubst':>12} {'dProbe':>12} "
          f"{'dReverse':>12} {'GraveSig':>12} {'SNR':>8}")
    print(f"  {'-'*6} {'-'*12} {'-'*12} {'-'*12} "
          f"{'-'*12} {'-'*8}")

    snap_results = []
    for step in sorted(runs["A_none"]["snapshots"].keys()):
        sA = runs["A_none"]["snapshots"].get(step)
        sB = runs["B_passive"]["snapshots"].get(step)
        sC = runs["C_active"]["snapshots"].get(step)
        sD = runs["D_reverse"]["snapshots"].get(step)

        if sA is None or sB is None or sC is None or sD is None:
            continue

        ds = float(np.sqrt(np.mean((sB - sA)**2)))
        dp = float(np.sqrt(np.mean((sC - sB)**2)))
        dr = float(np.sqrt(np.mean((sD - sB)**2)))
        gs = float(np.sqrt(np.mean(sA[grave_mask]**2)))
        s = gs / dp if dp > 1e-15 else float('inf')

        snap_results.append({
            "step": step,
            "rms_substrate": round(ds, 8),
            "rms_probe": round(dp, 8),
            "rms_reverse": round(dr, 8),
            "rms_grave": round(gs, 8),
            "snr": round(s, 4) if s != float('inf') else "inf",
        })

        s_str = f"{s:.2f}" if s != float('inf') else "inf"
        print(f"  {step:>6} {ds:>12.8f} {dp:>12.8f} "
              f"{dr:>12.8f} {gs:>12.8f} {s_str:>8}")

    # ═══════════════════════════════════════════════════
    # COMBINED VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  COMBINED VERDICT")
    print(f"{'='*65}")

    print(f"\n  Kill 1 (passive clean):  "
          f"{'PASS' if passive_clean else 'FAIL'}")
    print(f"  Kill 2 (SNR > 1):       "
          f"{'PASS' if probe_separable else 'FAIL'} "
          f"(SNR={snr:.2f})")
    print(f"  Kill 3 (reverse field):  {rev_verdict}")

    all_pass = passive_clean and probe_separable and reverse_physical
    if all_pass:
        print(f"\n  ALL KILL CONDITIONS PASS")
        print(f"  Observer-coupled field interaction is physical,")
        print(f"  not numerical artifact.")
    else:
        print(f"\n  ONE OR MORE KILL CONDITIONS FAILED")
        print(f"  Architecture requires investigation.")
    print(f"{'='*65}")

    # ═══════════════════════════════════════════════════
    # SAVE
    # ═══════════════════════════════════════════════════

    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_diag_decomposition_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v16 Diagnostic 3B: Perturbation Decomposition",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("4-run decomposition: none/passive/active/"
                     "reverse -- separates sensor from actuator"),
        "grid": nx,
        "steps": args.steps,
        "drifts": {
            "A_none": drift_A,
            "B_passive": drift_B,
            "C_active": drift_C,
            "D_reverse": drift_D,
        },
        "field_deltas_rms": {
            "delta_substrate_BA": round(rms_substrate, 8),
            "delta_probe_CB": round(rms_probe, 8),
            "delta_reverse_DB": round(rms_reverse, 8),
            "grave_signal_A": round(rms_grave, 8),
        },
        "field_deltas_max": {
            "delta_substrate_BA": round(max_substrate, 8),
            "delta_probe_CB": round(max_probe, 8),
            "delta_reverse_DB": round(max_reverse, 8),
        },
        "kill_conditions": {
            "kill_1_passive_clean": passive_clean,
            "kill_2_snr": round(snr, 4) if snr != float('inf')
                          else "inf",
            "kill_2_pass": probe_separable,
            "kill_3_reverse_physical": reverse_physical,
            "kill_3_reverse_reduces": reverse_reduces,
        },
        "verdict": "PASS" if all_pass else "FAIL",
        "snapshot_decomposition": snap_results,
        "trajectory_comparison": traj_comparison,
        "timelines": {
            "A_none": runs["A_none"]["timeline"],
            "B_passive": runs["B_passive"]["timeline"],
            "C_active": runs["C_active"]["timeline"],
            "D_reverse": runs["D_reverse"]["timeline"],
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
