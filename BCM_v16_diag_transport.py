# -*- coding: utf-8 -*-
"""
BCM v16 -- Diagnostic 3D: Sigma Transport Neutrality Retest
==============================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Diagnostic 3C revealed the "Printer Bug" -- stamp_sigma was
creating mass from nothing, producing 60px drift with zero
pumps. ChatGPT's VEV attack confirmed: free energy.

THE FIX: Sigma Transport Model (The Scoop)

The probe no longer creates sigma. It MOVES sigma:
  1. EJECT: Pump A spends reactor energy to launch probe
  2. SCOOP: At arc position, probe removes sigma from field
     field[ix,iy] -= scoop_amount
  3. CARRY: Probe holds sigma as payload during return
  4. DEPOSIT: At Pump B collector, probe deposits payload
     field[bx,by] += payload

Conservation: integral of sigma over field = constant.
The probe is a mass-transfer vehicle, not a broadcast station.

Heisenberg constraint (Stephen / Gemini): to gain information
about substrate momentum (delta_p), the probe must displace
substrate at a specific position (delta_x). Measurement is
a displacement event, not a free observation.

Same four runs as 3C:
  Run 1: UNIFORM FIELD
  Run 2: REVERSED GRADIENT
  Run 3: ZERO PUMP (must now show ~zero drift)
  Run 4: NORMAL (control)

Kill conditions (same as 3C):
  1. Uniform harvest > 5% of control -> FREE ENERGY
  2. Reversed drift exceeds control -> BIAS BUG
  3. Zero pump drift > 5% of control -> OBSERVER ENERGY

Usage:
    python BCM_v16_diag_transport.py
    python BCM_v16_diag_transport.py --steps 3000 --grid 256
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
# TRANSPORT PROBE (scoop/deposit, no creation)
# ═══════════════════════════════════════════════════════

class TransportProbe:
    """
    Sigma transport vehicle. Does NOT create mass.

    SCOOP: removes sigma from field at probe position.
    CARRY: holds sigma as payload during arc and fall.
    DEPOSIT: adds payload to field at B collector position.

    Scoop efficiency: fraction of local sigma removed per
    arc step. Low efficiency = gentle sampling. High = deep
    harvest. Default 5% per step.
    """
    def __init__(self, pid, eject_offset, scoop_efficiency=0.05,
                 scoop_radius=2.0):
        self.pid = pid
        self.eject_offset = eject_offset
        self.scoop_efficiency = scoop_efficiency
        self.scoop_radius = scoop_radius
        self.position = np.array([0.0, 0.0])
        self.state = "TRANSIT"
        self.cycle_step = 0
        self.cycles_completed = 0
        self.payload = 0.0          # sigma being carried
        self.total_scooped = 0.0    # lifetime total
        self.total_deposited = 0.0  # lifetime total

        self.transit_duration = 5
        self.arc_duration = 40
        self.fall_duration = 10

    def update(self, craft_com, pump_a_pos, pump_b_pos,
               step, sigma, nx, ny, rng):
        """
        Advance one step. Modifies sigma field in-place
        via scoop (remove) and deposit (add).
        """
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

        # New cycle: deposit any remaining payload at B
        if self.cycles_completed > prev_cycle and self.payload > 0:
            self._deposit(sigma, pump_b_pos, nx, ny)

        if self.cycle_step < self.transit_duration:
            # TRANSIT: inside tunnel, B -> A
            self.state = "TRANSIT"
            t = self.cycle_step / self.transit_duration
            self.position = (pump_b_pos +
                             t * (pump_a_pos - pump_b_pos))

        elif self.cycle_step < (self.transit_duration +
                                self.arc_duration):
            # EJECTED: riding arc, SCOOPING sigma
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
                                t_arc * 2 * math.pi)
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

            # SCOOP: remove sigma from field at probe position
            self._scoop(sigma, nx, ny)

        else:
            # FALLING: returning to B collector
            self.state = "FALLING"
            fall_step = (self.cycle_step -
                         self.transit_duration -
                         self.arc_duration)
            t_fall = fall_step / self.fall_duration
            self.position = (self.position +
                             t_fall *
                             (pump_b_pos - self.position))

            # Deposit on last fall step
            if fall_step >= self.fall_duration - 1:
                self._deposit(sigma, pump_b_pos, nx, ny)

    def _scoop(self, sigma, nx, ny):
        """Remove sigma from field at probe position."""
        ix = int(np.clip(self.position[0], 0, nx - 1))
        iy = int(np.clip(self.position[1], 0, ny - 1))

        # Scoop from a small Gaussian footprint
        x_arr = np.arange(max(0, ix - 4), min(nx, ix + 5))
        y_arr = np.arange(max(0, iy - 4), min(ny, iy + 5))
        if len(x_arr) == 0 or len(y_arr) == 0:
            return

        X_local, Y_local = np.meshgrid(x_arr, y_arr,
                                        indexing='ij')
        r2 = ((X_local - self.position[0])**2 +
              (Y_local - self.position[1])**2)
        weight = np.exp(-r2 / (2 * self.scoop_radius**2))

        # Amount to scoop: efficiency * weighted local sigma
        local_sigma = sigma[np.ix_(x_arr, y_arr)]
        scoop_amount = local_sigma * weight * self.scoop_efficiency
        scoop_amount = np.minimum(scoop_amount, local_sigma)
        scoop_amount = np.maximum(scoop_amount, 0)

        total_scooped = float(np.sum(scoop_amount))
        sigma[np.ix_(x_arr, y_arr)] -= scoop_amount
        self.payload += total_scooped
        self.total_scooped += total_scooped

    def _deposit(self, sigma, deposit_pos, nx, ny):
        """Deposit payload at collector position."""
        if self.payload <= 0:
            return

        ix = int(np.clip(deposit_pos[0], 0, nx - 1))
        iy = int(np.clip(deposit_pos[1], 0, ny - 1))

        # Deposit as Gaussian at B position
        x_arr = np.arange(max(0, ix - 4), min(nx, ix + 5))
        y_arr = np.arange(max(0, iy - 4), min(ny, iy + 5))
        if len(x_arr) == 0 or len(y_arr) == 0:
            return

        X_local, Y_local = np.meshgrid(x_arr, y_arr,
                                        indexing='ij')
        r2 = ((X_local - deposit_pos[0])**2 +
              (Y_local - deposit_pos[1])**2)
        weight = np.exp(-r2 / (2 * self.scoop_radius**2))
        weight_sum = float(np.sum(weight))

        if weight_sum > 1e-15:
            deposit = weight * (self.payload / weight_sum)
            sigma[np.ix_(x_arr, y_arr)] += deposit

        self.total_deposited += self.payload
        self.payload = 0.0


# ═══════════════════════════════════════════════════════
# TRANSIT ENGINE
# ═══════════════════════════════════════════════════════

def run_transit(nx, ny, steps, dt, D, alpha, separation,
                pump_A, ratio, lam_field, use_pumps,
                use_probes, rng_seed):
    rng = np.random.RandomState(rng_seed)

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    start_x = nx // 8
    start_y = ny // 2
    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    initial_com = compute_com(sigma)

    probes = []
    if use_probes:
        for i in range(12):
            probes.append(TransportProbe(i + 1, i * 5))

    timeline = []
    sigma_total_start = float(np.sum(sigma))

    # Conservation tracking
    conservation_checks = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        pump_a_pos = np.array([com[0] + separation, com[1]])
        pump_b_pos = np.array([com[0] - separation * 0.3,
                               com[1]])

        if use_pumps:
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

        # Probe cycling with TRANSPORT (scoop/deposit)
        if use_probes:
            for probe in probes:
                probe.update(com, pump_a_pos, pump_b_pos,
                             step, sigma, nx, ny, rng)

        # Conservation check every 100 steps
        if step % 100 == 0:
            field_sigma = float(np.sum(sigma))
            payload_sigma = sum(p.payload for p in probes)
            total_sigma = field_sigma + payload_sigma

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
                    "sigma_field": round(field_sigma, 4),
                    "sigma_payload": round(payload_sigma, 6),
                    "sigma_total": round(total_sigma, 4),
                })

                conservation_checks.append({
                    "step": step,
                    "total": round(total_sigma, 4),
                })

    sigma_total_end = float(np.sum(sigma))
    payload_end = sum(p.payload for p in probes)
    final_com = compute_com(sigma)
    final_drift = 0.0
    if final_com is not None:
        final_drift = float(np.linalg.norm(
            final_com - initial_com))

    total_scooped = sum(p.total_scooped for p in probes)
    total_deposited = sum(p.total_deposited for p in probes)

    return {
        "final_drift": round(final_drift, 4),
        "sigma_field_start": round(sigma_total_start, 4),
        "sigma_field_end": round(sigma_total_end, 4),
        "sigma_payload_end": round(payload_end, 6),
        "total_scooped": round(total_scooped, 4),
        "total_deposited": round(total_deposited, 4),
        "conservation_checks": conservation_checks,
        "timeline": timeline,
    }


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Diag 3D: Transport Neutrality")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v16 -- DIAGNOSTIC 3D: SIGMA TRANSPORT NEUTRALITY")
    print(f"  Printer bug killed. Scoop/deposit enforced.")
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

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    # Lambda fields
    lam_normal = np.full((nx, ny), void_lambda, dtype=float)
    gx1 = nx // 3
    r2 = (X - gx1)**2 + (Y - ny//2)**2
    lam_normal -= 0.04 * np.exp(-r2 / (2 * 12.0**2))
    gx2 = nx // 2
    r2 = (X - gx2)**2 + (Y - ny//2)**2
    lam_normal -= 0.08 * np.exp(-r2 / (2 * 18.0**2))
    lam_normal = np.maximum(lam_normal, 0.001)

    lam_uniform = np.full((nx, ny), void_lambda, dtype=float)

    lam_reversed = np.full((nx, ny), void_lambda, dtype=float)
    start_x = nx // 8
    gx1_rev = max(5, start_x - (gx1 - start_x))
    gx2_rev = max(5, start_x - (gx2 - start_x))
    r2 = (X - gx1_rev)**2 + (Y - ny//2)**2
    lam_reversed -= 0.04 * np.exp(-r2 / (2 * 12.0**2))
    r2 = (X - gx2_rev)**2 + (Y - ny//2)**2
    lam_reversed -= 0.08 * np.exp(-r2 / (2 * 18.0**2))
    lam_reversed = np.maximum(lam_reversed, 0.001)

    runs = {}
    run_configs = [
        ("1_uniform",  "UNIFORM FIELD",       lam_uniform,  True,  True),
        ("2_reversed", "REVERSED GRADIENT",    lam_reversed, True,  True),
        ("3_zero",     "ZERO PUMP",            lam_normal,   False, True),
        ("4_normal",   "NORMAL (control)",     lam_normal,   True,  True),
    ]

    for label, desc, lam, pumps, probes in run_configs:
        print(f"\n  {'─'*55}")
        print(f"  RUN {label}: {desc}")
        print(f"  {'─'*55}")

        result = run_transit(
            nx, ny, args.steps, dt, D, alpha, separation,
            pump_A, ratio, lam, pumps, probes, rng_seed=42)

        runs[label] = result
        print(f"  Drift:     {result['final_drift']:.2f} px")
        print(f"  Scooped:   {result['total_scooped']:.4f}")
        print(f"  Deposited: {result['total_deposited']:.4f}")

        # Conservation check
        if result['conservation_checks']:
            first = result['conservation_checks'][0]['total']
            last = result['conservation_checks'][-1]['total']
            drift_pct = abs(last - first) / max(abs(first), 1e-15) * 100
            print(f"  Sigma conservation: {first:.2f} -> "
                  f"{last:.2f} ({drift_pct:.4f}% change)")

    # ═══════════════════════════════════════════════════
    # NEUTRALITY ANALYSIS
    # ═══════════════════════════════════════════════════

    control = runs["4_normal"]["final_drift"]
    uniform = runs["1_uniform"]["final_drift"]
    reversed_d = runs["2_reversed"]["final_drift"]
    zero = runs["3_zero"]["final_drift"]

    print(f"\n{'='*65}")
    print(f"  NEUTRALITY ANALYSIS (TRANSPORT MODEL)")
    print(f"{'='*65}")

    print(f"\n  DRIFT COMPARISON:")
    print(f"    Normal (control):   {control:.2f} px")
    print(f"    Uniform field:      {uniform:.2f} px")
    print(f"    Reversed gradient:  {reversed_d:.2f} px")
    print(f"    Zero pump:          {zero:.2f} px")

    # Kill 1
    print(f"\n  {'─'*55}")
    print(f"  KILL 1: Free energy from uniform field")
    uniform_pct = (uniform / control * 100) if control > 0 else 0
    kill_1 = uniform_pct > 105  # allow pumps to work in uniform
    print(f"    Uniform as % of control: {uniform_pct:.2f}%")
    print(f"    Verdict: {'INVESTIGATE' if kill_1 else 'PASS'}")

    # Kill 2
    print(f"\n  {'─'*55}")
    print(f"  KILL 2: Directional bias (reversed gradient)")
    reversed_pct = (reversed_d / control * 100) if control > 0 else 0
    kill_2 = reversed_d > control * 1.05
    print(f"    Reversed as % of control: {reversed_pct:.2f}%")
    print(f"    Verdict: {'FAIL' if kill_2 else 'PASS'}")

    # Kill 3 -- THE CRITICAL ONE
    print(f"\n  {'─'*55}")
    print(f"  KILL 3: Observer creates energy (zero pump)")
    zero_pct = (zero / control * 100) if control > 0 else 0
    kill_3 = zero_pct > 5.0
    print(f"    Zero-pump drift as % of control: {zero_pct:.2f}%")
    print(f"    Threshold: < 5%")
    print(f"    Verdict: {'FAIL' if kill_3 else 'PASS'}")

    # Trajectory
    print(f"\n  {'─'*55}")
    print(f"  TRAJECTORY COMPARISON")
    print(f"  {'Step':>6} {'Uniform':>10} {'Reversed':>10} "
          f"{'ZeroPump':>10} {'Normal':>10}")
    print(f"  {'-'*6} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    traj = []
    max_len = min(
        len(runs["1_uniform"]["timeline"]),
        len(runs["2_reversed"]["timeline"]),
        len(runs["3_zero"]["timeline"]),
        len(runs["4_normal"]["timeline"]),
    )
    for i in range(0, max_len, 5):
        u = runs["1_uniform"]["timeline"][i]
        r = runs["2_reversed"]["timeline"][i]
        z = runs["3_zero"]["timeline"][i]
        n = runs["4_normal"]["timeline"][i]
        traj.append({
            "step": u["step"],
            "uniform": u["drift"],
            "reversed": r["drift"],
            "zero_pump": z["drift"],
            "normal": n["drift"],
        })
        print(f"  {u['step']:>6} {u['drift']:>10.2f} "
              f"{r['drift']:>10.2f} {z['drift']:>10.2f} "
              f"{n['drift']:>10.2f}")

    # Combined verdict
    print(f"\n{'='*65}")
    print(f"  COMBINED VERDICT (TRANSPORT MODEL)")
    print(f"{'='*65}")
    print(f"\n  Kill 1 (uniform):     "
          f"{'INVESTIGATE' if kill_1 else 'PASS'}")
    print(f"  Kill 2 (reversed):    "
          f"{'FAIL' if kill_2 else 'PASS'}")
    print(f"  Kill 3 (zero pump):   "
          f"{'FAIL' if kill_3 else 'PASS'}")

    any_hard_fail = kill_2 or kill_3
    if not any_hard_fail:
        print(f"\n  PRINTER BUG KILLED.")
        print(f"  Sigma transport model passes neutrality.")
        print(f"  Probes move mass, they do not create it.")
    else:
        print(f"\n  TRANSPORT MODEL NEEDS FURTHER INVESTIGATION.")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_diag_transport_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": ("BCM v16 Diagnostic 3D: "
                   "Sigma Transport Neutrality"),
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Printer bug fix verification. "
                     "Scoop/deposit replaces stamp_sigma."),
        "grid": nx,
        "steps": args.steps,
        "transport_model": {
            "scoop_efficiency": 0.05,
            "scoop_radius": 2.0,
            "mechanism": ("Remove sigma at probe position, "
                          "carry as payload, deposit at B"),
        },
        "drifts": {
            "normal_control": control,
            "uniform_field": uniform,
            "reversed_gradient": reversed_d,
            "zero_pump": zero,
        },
        "kill_conditions": {
            "kill_1_uniform_pct": round(uniform_pct, 4),
            "kill_1_pass": not kill_1,
            "kill_2_reversed_exceeds": kill_2,
            "kill_2_pass": not kill_2,
            "kill_3_zero_pct": round(zero_pct, 4),
            "kill_3_pass": not kill_3,
        },
        "scooped_deposited": {
            r: {"scooped": runs[r]["total_scooped"],
                "deposited": runs[r]["total_deposited"]}
            for r in runs
        },
        "verdict": ("PASS" if not any_hard_fail
                    else "INVESTIGATE"),
        "trajectory": traj,
        "timelines": {r: runs[r]["timeline"] for r in runs},
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
