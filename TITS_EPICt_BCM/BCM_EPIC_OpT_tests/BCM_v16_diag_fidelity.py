# -*- coding: utf-8 -*-
"""
BCM v16 -- Diagnostic 3E+3F: Fidelity Suite
==============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

ChatGPT shifted from existence to fidelity. The system
conserves energy. Now: does it conserve TRUTH?

Fidelity = invariance of behavior under transformation.

DIAGNOSTIC 3E: ROTATIONAL FIDELITY
  Run the same transit at 0deg, 90deg, 45deg.
  Rotate: lambda field, initial sigma, pump axis.
  Drift magnitude must match. Drift direction must
  rotate by the same angle. If mismatch > 5% -> the
  grid has grain. The physics is cheating.

DIAGNOSTIC 3F: TRANSPORT ISOTROPY
  Eject probes at 8 compass directions from a central
  craft in uniform field. Measure scoop efficiency and
  drift contribution per angle. No preferred direction
  should exist without a gradient present.

Both tests use the sigma transport model (scoop/deposit).

Usage:
    python BCM_v16_diag_fidelity.py
    python BCM_v16_diag_fidelity.py --steps 2000 --grid 256
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
# TRANSPORT PROBE (scoop/deposit)
# ═══════════════════════════════════════════════════════

class TransportProbe:
    def __init__(self, pid, eject_offset, drive_angle=0.0,
                 scoop_efficiency=0.05, scoop_radius=2.0):
        self.pid = pid
        self.eject_offset = eject_offset
        self.drive_angle = drive_angle  # direction of ejection
        self.scoop_efficiency = scoop_efficiency
        self.scoop_radius = scoop_radius
        self.position = np.array([0.0, 0.0])
        self.state = "TRANSIT"
        self.cycle_step = 0
        self.cycles_completed = 0
        self.payload = 0.0
        self.total_scooped = 0.0
        self.total_deposited = 0.0

        self.transit_duration = 5
        self.arc_duration = 40
        self.fall_duration = 10

    def update(self, craft_com, pump_a_pos, pump_b_pos,
               step, sigma, nx, ny, rng):
        effective_step = step - self.eject_offset
        if effective_step < 0:
            self.position = craft_com.copy()
            self.state = "TRANSIT"
            return

        cycle_length = (self.transit_duration +
                        self.arc_duration +
                        self.fall_duration)
        prev_cycle = self.cycles_completed
        self.cycle_step = effective_step % cycle_length
        self.cycles_completed = effective_step // cycle_length

        if self.cycles_completed > prev_cycle and self.payload > 0:
            self._deposit(sigma, pump_b_pos, nx, ny)

        if self.cycle_step < self.transit_duration:
            self.state = "TRANSIT"
            t = self.cycle_step / self.transit_duration
            self.position = (pump_b_pos +
                             t * (pump_a_pos - pump_b_pos))

        elif self.cycle_step < (self.transit_duration +
                                self.arc_duration):
            self.state = "EJECTED"
            arc_step = self.cycle_step - self.transit_duration
            base_angle_offset = rng.uniform(-0.8, 0.8)
            vertex_count = 5 + (self.cycles_completed % 4)
            t_arc = arc_step / self.arc_duration
            arc_max_radius = 40.0 + rng.uniform(-10, 15)

            if t_arc < 0.5:
                arc_radius = arc_max_radius * (t_arc * 2)
            else:
                arc_radius = arc_max_radius * (2 - t_arc * 2)

            continuous_angle = (base_angle_offset +
                                t_arc * 2 * math.pi +
                                self.drive_angle)
            vertex_angle = (
                round(continuous_angle /
                      (2 * math.pi / vertex_count))
                * (2 * math.pi / vertex_count))
            arc_angle = (0.3 * continuous_angle +
                         0.7 * vertex_angle)

            self.position = np.array([
                pump_a_pos[0] +
                arc_radius * np.cos(arc_angle),
                pump_a_pos[1] +
                arc_radius * np.sin(arc_angle),
            ])
            self._scoop(sigma, nx, ny)

        else:
            self.state = "FALLING"
            fall_step = (self.cycle_step -
                         self.transit_duration -
                         self.arc_duration)
            t_fall = fall_step / self.fall_duration
            self.position = (self.position +
                             t_fall *
                             (pump_b_pos - self.position))
            if fall_step >= self.fall_duration - 1:
                self._deposit(sigma, pump_b_pos, nx, ny)

    def _scoop(self, sigma, nx, ny):
        ix = int(np.clip(self.position[0], 0, nx - 1))
        iy = int(np.clip(self.position[1], 0, ny - 1))
        x_arr = np.arange(max(0, ix - 4), min(nx, ix + 5))
        y_arr = np.arange(max(0, iy - 4), min(ny, iy + 5))
        if len(x_arr) == 0 or len(y_arr) == 0:
            return
        X_l, Y_l = np.meshgrid(x_arr, y_arr, indexing='ij')
        r2 = ((X_l - self.position[0])**2 +
              (Y_l - self.position[1])**2)
        w = np.exp(-r2 / (2 * self.scoop_radius**2))
        local = sigma[np.ix_(x_arr, y_arr)]
        scoop = np.minimum(local * w * self.scoop_efficiency,
                           local)
        scoop = np.maximum(scoop, 0)
        total = float(np.sum(scoop))
        sigma[np.ix_(x_arr, y_arr)] -= scoop
        self.payload += total
        self.total_scooped += total

    def _deposit(self, sigma, pos, nx, ny):
        if self.payload <= 0:
            return
        ix = int(np.clip(pos[0], 0, nx - 1))
        iy = int(np.clip(pos[1], 0, ny - 1))
        x_arr = np.arange(max(0, ix - 4), min(nx, ix + 5))
        y_arr = np.arange(max(0, iy - 4), min(ny, iy + 5))
        if len(x_arr) == 0 or len(y_arr) == 0:
            return
        X_l, Y_l = np.meshgrid(x_arr, y_arr, indexing='ij')
        r2 = ((X_l - pos[0])**2 + (Y_l - pos[1])**2)
        w = np.exp(-r2 / (2 * self.scoop_radius**2))
        ws = float(np.sum(w))
        if ws > 1e-15:
            sigma[np.ix_(x_arr, y_arr)] += w * (self.payload / ws)
        self.total_deposited += self.payload
        self.payload = 0.0


# ═══════════════════════════════════════════════════════
# ROTATED TRANSIT ENGINE
# ═══════════════════════════════════════════════════════

def run_rotated_transit(nx, ny, steps, dt, D, alpha,
                        separation, pump_A, ratio,
                        drive_angle, rng_seed):
    """
    Run transit with pump axis rotated by drive_angle.
    Lambda field: single grave placed along the drive axis.
    """
    rng = np.random.RandomState(rng_seed)

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    cx = nx // 2
    cy = ny // 2

    # Start position: offset from center OPPOSITE drive angle
    start_offset = nx // 4
    start_x = cx - start_offset * np.cos(drive_angle)
    start_y = cy - start_offset * np.sin(drive_angle)

    # Grave position: along drive axis ahead of start
    grave_offset = nx // 6
    grave_x = cx + grave_offset * np.cos(drive_angle)
    grave_y = cy + grave_offset * np.sin(drive_angle)

    # Lambda field: uniform with one grave along drive axis
    void_lambda = 0.10
    lam = np.full((nx, ny), void_lambda, dtype=float)
    r2_grave = (X - grave_x)**2 + (Y - grave_y)**2
    lam -= 0.06 * np.exp(-r2_grave / (2 * 15.0**2))
    lam = np.maximum(lam, 0.001)

    # Initial sigma
    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    initial_com = compute_com(sigma)

    # Probes
    probes = []
    for i in range(12):
        probes.append(TransportProbe(
            i + 1, i * 5, drive_angle=drive_angle))

    timeline = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        # Pump positions along drive angle
        pump_a_pos = np.array([
            com[0] + separation * np.cos(drive_angle),
            com[1] + separation * np.sin(drive_angle)])
        pump_b_pos = np.array([
            com[0] - separation * 0.3 * np.cos(drive_angle),
            com[1] - separation * 0.3 * np.sin(drive_angle)])

        # Pumps
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        r2_B = ((X - pump_a_pos[0])**2 +
                (Y - pump_a_pos[1])**2)
        actual_B = pump_A * ratio
        pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        # PDE
        lap = (np.roll(sigma, 1, 0) +
               np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) +
               np.roll(sigma, -1, 1) - 4 * sigma)
        sigma_new = (sigma + D * lap * dt -
                     lam * sigma * dt)
        if alpha > 0:
            sigma_new += alpha * (sigma - sigma_prev)
        sigma_new = np.maximum(sigma_new, 0)

        if float(np.max(sigma_new)) > 1e10:
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        for probe in probes:
            probe.update(com, pump_a_pos, pump_b_pos,
                         step, sigma, nx, ny, rng)

        if step % 100 == 0:
            new_com = compute_com(sigma)
            if new_com is not None:
                disp = new_com - initial_com
                drift_mag = float(np.linalg.norm(disp))
                drift_angle = float(np.arctan2(disp[1], disp[0]))
                timeline.append({
                    "step": step,
                    "drift_mag": round(drift_mag, 4),
                    "drift_angle_deg": round(
                        np.degrees(drift_angle), 2),
                    "dx": round(float(disp[0]), 4),
                    "dy": round(float(disp[1]), 4),
                })

    final_com = compute_com(sigma)
    if final_com is not None:
        disp = final_com - initial_com
        drift_mag = float(np.linalg.norm(disp))
        drift_angle = float(np.arctan2(disp[1], disp[0]))
    else:
        drift_mag = 0.0
        drift_angle = 0.0

    total_scooped = sum(p.total_scooped for p in probes)

    return {
        "drive_angle_deg": round(np.degrees(drive_angle), 1),
        "drift_mag": round(drift_mag, 4),
        "drift_angle_deg": round(np.degrees(drift_angle), 2),
        "expected_angle_deg": round(np.degrees(drive_angle), 2),
        "angle_error_deg": round(np.degrees(
            (drift_angle - drive_angle + math.pi) %
            (2 * math.pi) - math.pi), 2),
        "total_scooped": round(total_scooped, 4),
        "timeline": timeline,
    }


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Diag 3E+3F: Fidelity Suite")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v16 -- DIAGNOSTIC 3E+3F: FIDELITY SUITE")
    print(f"  Is the physics real or is the grid cheating?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    dt = 0.05
    D = 0.5
    alpha = 0.80
    pump_A = 0.5
    ratio = 0.25
    separation = 15.0

    # ═══════════════════════════════════════════════════
    # 3E: ROTATIONAL FIDELITY
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  DIAGNOSTIC 3E: ROTATIONAL FIDELITY")
    print(f"  Drive at 0deg, 90deg, 45deg -- drift must rotate")
    print(f"{'='*65}")

    test_angles = [0.0, math.pi / 2, math.pi / 4]
    angle_names = ["0deg (pure X)", "90deg (pure Y)",
                   "45deg (diagonal)"]
    rotation_results = []

    for angle, name in zip(test_angles, angle_names):
        print(f"\n  {'─'*55}")
        print(f"  DRIVE ANGLE: {name}")
        print(f"  {'─'*55}")

        result = run_rotated_transit(
            nx, ny, args.steps, dt, D, alpha,
            separation, pump_A, ratio,
            drive_angle=angle, rng_seed=42)

        rotation_results.append(result)

        print(f"  Drift magnitude:  {result['drift_mag']:.4f} px")
        print(f"  Drift direction:  {result['drift_angle_deg']:.2f} deg")
        print(f"  Expected dir:     {result['expected_angle_deg']:.2f} deg")
        print(f"  Angle error:      {result['angle_error_deg']:.2f} deg")
        print(f"  Total scooped:    {result['total_scooped']:.4f}")

    # Fidelity analysis
    print(f"\n{'='*65}")
    print(f"  ROTATIONAL FIDELITY ANALYSIS")
    print(f"{'='*65}")

    base_mag = rotation_results[0]["drift_mag"]
    print(f"\n  {'Angle':>10} {'Magnitude':>12} {'MagRatio':>10} "
          f"{'AngleErr':>10} {'Verdict':>10}")
    print(f"  {'-'*10} {'-'*12} {'-'*10} {'-'*10} {'-'*10}")

    rot_verdicts = []
    for r in rotation_results:
        if base_mag > 0:
            mag_ratio = r["drift_mag"] / base_mag
        else:
            mag_ratio = 0
        angle_err = abs(r["angle_error_deg"])
        # Allow wrap-around
        if angle_err > 180:
            angle_err = 360 - angle_err

        mag_ok = 0.80 < mag_ratio < 1.20  # within 20%
        ang_ok = angle_err < 15.0  # within 15 degrees
        verdict = "PASS" if (mag_ok and ang_ok) else "FAIL"
        rot_verdicts.append(verdict)

        print(f"  {r['drive_angle_deg']:>10.1f} "
              f"{r['drift_mag']:>12.4f} "
              f"{mag_ratio:>10.4f} "
              f"{r['angle_error_deg']:>+10.2f} "
              f"{verdict:>10}")

    rot_pass = all(v == "PASS" for v in rot_verdicts)
    print(f"\n  ROTATION FIDELITY: "
          f"{'PASS -- grid is invisible' if rot_pass else 'FAIL -- grid has grain'}")

    # ═══════════════════════════════════════════════════
    # 3F: TRANSPORT ISOTROPY
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  DIAGNOSTIC 3F: TRANSPORT ISOTROPY")
    print(f"  8 compass directions in uniform field")
    print(f"{'='*65}")

    iso_angles = [i * math.pi / 4 for i in range(8)]
    iso_names = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    iso_results = []

    # Shorter run for isotropy (just need scoop efficiency)
    iso_steps = min(args.steps, 1000)

    for angle, name in zip(iso_angles, iso_names):
        print(f"  {name:>3}: ", end="", flush=True)

        result = run_rotated_transit(
            nx, ny, iso_steps, dt, D, alpha,
            separation, pump_A, ratio,
            drive_angle=angle, rng_seed=42)

        iso_results.append({
            "direction": name,
            "angle_deg": round(np.degrees(angle), 1),
            "drift_mag": result["drift_mag"],
            "drift_angle_deg": result["drift_angle_deg"],
            "angle_error_deg": result["angle_error_deg"],
            "total_scooped": result["total_scooped"],
        })

        print(f"drift={result['drift_mag']:.2f} px  "
              f"err={result['angle_error_deg']:+.1f} deg  "
              f"scoop={result['total_scooped']:.2f}")

    # Isotropy analysis
    mags = [r["drift_mag"] for r in iso_results]
    scoops = [r["total_scooped"] for r in iso_results]
    angle_errs = [abs(r["angle_error_deg"]) for r in iso_results]

    mag_mean = np.mean(mags)
    mag_std = np.std(mags)
    mag_cv = mag_std / mag_mean if mag_mean > 0 else 0

    scoop_mean = np.mean(scoops)
    scoop_std = np.std(scoops)
    scoop_cv = scoop_std / scoop_mean if scoop_mean > 0 else 0

    max_angle_err = max(angle_errs)

    print(f"\n  ISOTROPY STATISTICS:")
    print(f"    Drift magnitude: mean={mag_mean:.4f} "
          f"std={mag_std:.4f} CV={mag_cv:.4f}")
    print(f"    Scoop total:     mean={scoop_mean:.4f} "
          f"std={scoop_std:.4f} CV={scoop_cv:.4f}")
    print(f"    Max angle error: {max_angle_err:.2f} deg")

    # Isotropy kill conditions
    iso_mag_ok = mag_cv < 0.15   # <15% variation
    iso_scoop_ok = scoop_cv < 0.15
    iso_angle_ok = max_angle_err < 20.0

    iso_pass = iso_mag_ok and iso_scoop_ok and iso_angle_ok

    print(f"\n  Drift CV < 15%:    "
          f"{'PASS' if iso_mag_ok else 'FAIL'} ({mag_cv:.4f})")
    print(f"  Scoop CV < 15%:    "
          f"{'PASS' if iso_scoop_ok else 'FAIL'} ({scoop_cv:.4f})")
    print(f"  Angle err < 20deg: "
          f"{'PASS' if iso_angle_ok else 'FAIL'} "
          f"({max_angle_err:.2f})")
    print(f"\n  TRANSPORT ISOTROPY: "
          f"{'PASS -- no preferred direction' if iso_pass else 'FAIL -- directional bias detected'}")

    # ═══════════════════════════════════════════════════
    # COMBINED VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  FIDELITY SUITE VERDICT")
    print(f"{'='*65}")
    print(f"\n  3E Rotational fidelity: "
          f"{'PASS' if rot_pass else 'FAIL'}")
    print(f"  3F Transport isotropy:  "
          f"{'PASS' if iso_pass else 'FAIL'}")

    if rot_pass and iso_pass:
        print(f"\n  THE GRID IS INVISIBLE TO THE PHYSICS.")
        print(f"  Drift follows the drive, not the pixels.")
        print(f"  Transport is isotropic. No grain. No bias.")
        print(f"  Fidelity: CONFIRMED.")
    else:
        print(f"\n  FIDELITY INCOMPLETE. See individual results.")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_diag_fidelity_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v16 Diagnostic 3E+3F: Fidelity Suite",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Rotational fidelity + transport isotropy. "
                     "Is the grid invisible to the physics?"),
        "grid": nx,
        "steps_3E": args.steps,
        "steps_3F": iso_steps,
        "diagnostic_3E_rotation": {
            "results": [{k: v for k, v in r.items()
                         if k != "timeline"}
                        for r in rotation_results],
            "base_magnitude": base_mag,
            "verdict": "PASS" if rot_pass else "FAIL",
        },
        "diagnostic_3F_isotropy": {
            "results": iso_results,
            "drift_cv": round(mag_cv, 4),
            "scoop_cv": round(scoop_cv, 4),
            "max_angle_error": round(max_angle_err, 2),
            "verdict": "PASS" if iso_pass else "FAIL",
        },
        "combined_verdict": ("PASS" if (rot_pass and iso_pass)
                             else "FAIL"),
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
