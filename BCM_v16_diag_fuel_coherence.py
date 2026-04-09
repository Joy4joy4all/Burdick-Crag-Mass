# -*- coding: utf-8 -*-
"""
BCM v16 -- Diagnostic 1+2: Probe Fuel Budget & Coherence Decay
================================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Predicted Attack 1: "The probes cost fuel you haven't budgeted."
Predicted Attack 2: "The probe dissolves outside the funded bubble."

This diagnostic instruments the tunnel cycling architecture with:
  1. Reactor accounting: every pump injection and every probe
     ejection/arc-step is debited from a finite reactor budget.
     Reports propulsion vs observation split.
  2. Coherence tracking: probe sigma amplitude is computed at
     every arc position through the full cycle. Reports minimum
     coherence at apoapsis and whether the probe survives the
     return to B.

Kill condition (Attack 1): probes > 20% of total reactor budget.
Kill condition (Attack 2): probe sigma < dissolution threshold
  at any point during arc before return to B.

Uses MICRO weight class (mass=0.1, width=2.0) -- the cheapest
probe, worst case for coherence, best case for budget. If MICRO
survives both tests, all heavier classes survive too (they cost
more fuel but have higher coherence margin).

Usage:
    python BCM_v16_diag_fuel_coherence.py
    python BCM_v16_diag_fuel_coherence.py --steps 3000 --grid 256
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
# PROBE WITH COHERENCE TRACKING
# ═══════════════════════════════════════════════════════

class InstrumentedProbe:
    """
    Same state machine as TunnelProbe but tracks:
      - sigma amplitude at every arc position
      - tax paid per arc step
      - coherence at apoapsis
    """
    TRANSIT = "TRANSIT"
    EJECTED = "EJECTED"
    FALLING = "FALLING"

    def __init__(self, pid, eject_offset, probe_mass, probe_width,
                 void_lambda, bubble_radius, dt, D):
        self.pid = pid
        self.eject_offset = eject_offset
        self.position = np.array([0.0, 0.0])
        self.state = self.TRANSIT
        self.cycle_step = 0
        self.cycles_completed = 0
        self.total_reads = 0
        self.alive = True

        # Probe physical properties (from BoM)
        self.probe_mass = probe_mass
        self.probe_width = probe_width
        self.current_peak = probe_mass  # starts at full
        self.void_lambda = void_lambda
        self.bubble_radius = bubble_radius
        self.dt = dt
        self.D = D

        # Timing (same as tunnel_probes.py)
        self.transit_duration = 5
        self.arc_duration = 40
        self.fall_duration = 10

        # Coherence tracking
        self.arc_peaks = []         # peak sigma at each arc step
        self.arc_distances = []     # distance from craft at each step
        self.min_peak_this_cycle = probe_mass
        self.apoapsis_peak = probe_mass
        self.apoapsis_distance = 0.0
        self.total_tax_paid = 0.0
        self.worst_apoapsis_peak = probe_mass
        self.worst_apoapsis_distance = 0.0

        # Budget tracking
        self.ejection_count = 0
        self.arc_tax_total = 0.0

    def update(self, craft_com, pump_a_pos, pump_b_pos,
               step, lam_field, sigma, nx, ny, rng):
        if not self.alive:
            return None

        effective_step = step - self.eject_offset
        if effective_step < 0:
            self.position = craft_com.copy()
            return None

        cycle_length = (self.transit_duration +
                        self.arc_duration +
                        self.fall_duration)
        prev_cycle = self.cycles_completed
        self.cycle_step = effective_step % cycle_length
        self.cycles_completed = effective_step // cycle_length

        # New cycle started -- reset coherence tracking
        if self.cycles_completed > prev_cycle:
            # Record worst apoapsis across all cycles
            if self.apoapsis_peak < self.worst_apoapsis_peak:
                self.worst_apoapsis_peak = self.apoapsis_peak
                self.worst_apoapsis_distance = self.apoapsis_distance
            # Reset for new cycle
            self.min_peak_this_cycle = self.probe_mass
            self.apoapsis_peak = self.probe_mass
            self.apoapsis_distance = 0.0
            # Tunnel refuels the probe (stated in session doc)
            self.current_peak = self.probe_mass
            self.ejection_count += 1

        # -- STATE MACHINE --
        if self.cycle_step < self.transit_duration:
            # TRANSIT: inside tunnel, refueling
            self.state = self.TRANSIT
            t = self.cycle_step / self.transit_duration
            self.position = pump_b_pos + t * (pump_a_pos - pump_b_pos)
            self.current_peak = self.probe_mass  # funded inside craft
            return None

        elif self.cycle_step < self.transit_duration + self.arc_duration:
            # EJECTED: riding Alfven arc
            self.state = self.EJECTED
            arc_step = self.cycle_step - self.transit_duration

            # Same polygonal arc as tunnel_probes.py
            base_angle_offset = rng.uniform(-0.8, 0.8)
            vertex_count = 5 + (self.cycles_completed % 4)
            t_arc = arc_step / self.arc_duration
            arc_max_radius = 40.0 + rng.uniform(-10, 15)

            if t_arc < 0.5:
                arc_radius = arc_max_radius * (t_arc * 2)
            else:
                arc_radius = arc_max_radius * (2 - t_arc * 2)

            continuous_angle = base_angle_offset + t_arc * 2 * math.pi
            vertex_angle = (round(continuous_angle / (2 * math.pi / vertex_count))
                            * (2 * math.pi / vertex_count))
            arc_angle = 0.3 * continuous_angle + 0.7 * vertex_angle

            self.position = np.array([
                pump_a_pos[0] + arc_radius * np.cos(arc_angle),
                pump_a_pos[1] + arc_radius * np.sin(arc_angle),
            ])

            # -- COHERENCE DECAY --
            # Distance from craft center
            dist_from_craft = float(np.linalg.norm(
                self.position - craft_com))

            # Lambda at probe position (from craft bubble model)
            # Same model as probe_bom.py: low near craft, rises
            # to void baseline
            r2_craft = dist_from_craft**2
            local_lam = (self.void_lambda -
                         0.08 * math.exp(-r2_craft /
                                         (2 * self.bubble_radius**2)))
            local_lam = max(local_lam, 0.001)

            # Substrate tax
            tax_this_step = local_lam * self.current_peak * self.dt
            self.current_peak -= tax_this_step

            # Diffusion decay
            diff_loss = (self.D * self.dt * self.current_peak /
                         (self.probe_width**2))
            self.current_peak -= diff_loss
            self.current_peak = max(0, self.current_peak)

            self.total_tax_paid += tax_this_step
            self.arc_tax_total += tax_this_step

            # Track coherence
            self.arc_peaks.append(round(self.current_peak, 6))
            self.arc_distances.append(round(dist_from_craft, 2))

            if self.current_peak < self.min_peak_this_cycle:
                self.min_peak_this_cycle = self.current_peak

            # Track apoapsis (max distance point)
            if dist_from_craft > self.apoapsis_distance:
                self.apoapsis_distance = dist_from_craft
                self.apoapsis_peak = self.current_peak

            # Sample the actual field (same as tunnel_probes)
            ix = int(np.clip(self.position[0], 0, nx - 1))
            iy = int(np.clip(self.position[1], 0, ny - 1))
            local_lam_field = float(lam_field[ix, iy])
            local_sig = float(sigma[ix, iy])
            is_danger = local_lam_field < 0.04
            self.total_reads += 1

            reading = {
                "pid": self.pid,
                "cycle": self.cycles_completed,
                "ix": ix, "iy": iy,
                "lambda": round(local_lam_field, 6),
                "sigma": round(local_sig, 6),
                "arc_radius": round(arc_radius, 2),
                "probe_peak": round(self.current_peak, 6),
                "probe_mass_frac": round(
                    self.current_peak / self.probe_mass, 4),
                "dist_from_craft": round(dist_from_craft, 2),
                "danger": is_danger,
                "forward": ix > int(craft_com[0]),
            }
            return reading

        else:
            # FALLING: returning to B
            self.state = self.FALLING
            fall_step = (self.cycle_step - self.transit_duration
                         - self.arc_duration)
            t_fall = fall_step / self.fall_duration
            self.position = (self.position +
                             t_fall * (pump_b_pos - self.position))
            # Probe still decaying during fall but re-entering
            # funded zone -- tax decreases
            dist = float(np.linalg.norm(self.position - craft_com))
            r2_craft = dist**2
            local_lam = (self.void_lambda -
                         0.08 * math.exp(-r2_craft /
                                         (2 * self.bubble_radius**2)))
            local_lam = max(local_lam, 0.001)
            tax = local_lam * self.current_peak * self.dt
            self.current_peak -= tax
            self.current_peak = max(0, self.current_peak)
            self.arc_tax_total += tax
            return None

    def to_dict(self):
        return {
            "pid": self.pid,
            "state": self.state,
            "cycles": self.cycles_completed,
            "ejections": self.ejection_count,
            "total_reads": self.total_reads,
            "total_tax_paid": round(self.total_tax_paid, 6),
            "arc_tax_total": round(self.arc_tax_total, 6),
            "worst_apoapsis_peak": round(self.worst_apoapsis_peak, 6),
            "worst_apoapsis_distance": round(
                self.worst_apoapsis_distance, 2),
            "final_peak": round(self.current_peak, 6),
            "alive": self.alive,
        }


# ═══════════════════════════════════════════════════════
# MAIN DIAGNOSTIC
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Diagnostic 1+2: Fuel Budget & Coherence")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v16 -- DIAGNOSTIC 1+2")
    print(f"  Attack 1: Probe fuel budget")
    print(f"  Attack 2: Probe coherence decay")
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
    bubble_radius = 30.0

    # MICRO probe class (cheapest, worst coherence margin)
    probe_mass = 0.1
    probe_width = 2.0
    dissolution_threshold = 0.01

    # Reactor budget (from v15 finite reactor framework)
    # Using MEDIUM_CORE = 200 units
    reactor_initial = 200.0
    reactor_budget = reactor_initial

    # Creation cost per probe (from BoM: initial_mass for MICRO)
    # MICRO initial_mass = 2.5133 but that's the integrated
    # Gaussian. The reactor pays the peak mass, not the
    # integrated field -- the probe IS a sigma packet of
    # amplitude probe_mass. Creation cost = probe_mass.
    creation_cost_per_probe = probe_mass

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    # Lambda field with hazards (same as tunnel_probes.py)
    lam_field = np.full((nx, ny), void_lambda, dtype=float)
    gx1 = nx // 3
    r2 = (X - gx1)**2 + (Y - ny//2)**2
    lam_field -= 0.04 * np.exp(-r2 / (2 * 12.0**2))
    gx2 = nx // 2
    r2 = (X - gx2)**2 + (Y - ny//2)**2
    lam_field -= 0.08 * np.exp(-r2 / (2 * 18.0**2))
    lam_field = np.maximum(lam_field, 0.001)

    print(f"  Hazards: SHALLOW at x={gx1}, DEEP at x={gx2}")
    print(f"  Probe class: MICRO (mass={probe_mass}, "
          f"width={probe_width})")
    print(f"  Reactor: MEDIUM_CORE ({reactor_initial} units)")
    print(f"  Dissolution threshold: {dissolution_threshold}")

    # Sigma (craft)
    start_x = nx // 8
    start_y = ny // 2
    rng = np.random.RandomState(42)
    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    initial_com = compute_com(sigma)

    # Build 12 instrumented probes
    probes = []
    for i in range(12):
        offset = i * 5
        probes.append(InstrumentedProbe(
            pid=i + 1,
            eject_offset=offset,
            probe_mass=probe_mass,
            probe_width=probe_width,
            void_lambda=void_lambda,
            bubble_radius=bubble_radius,
            dt=dt,
            D=D,
        ))

    # Budget accumulators
    total_pump_spend = 0.0
    total_probe_creation_spend = 0.0
    total_probe_arc_tax = 0.0
    prev_ejection_counts = [0] * 12

    # Coherence kill tracking
    any_probe_dissolved = False
    dissolution_events = []

    timeline = []

    print(f"\n  {'Step':>6} {'Reactor':>10} {'PumpSpd':>10} "
          f"{'ProbeSpd':>10} {'Probe%':>8} {'MinPeak':>8}")
    print(f"  {'-'*6} {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*8}")

    alive = True

    for step in range(args.steps):
        com = compute_com(sigma)
        if com is None:
            alive = False
            break

        # Pump positions
        pump_a_pos = np.array([com[0] + separation, com[1]])
        pump_b_pos = np.array([com[0] - separation * 0.3, com[1]])

        # Pumps -- DEBIT REACTOR
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        pump_inject_A = float(np.sum(pA * dt))

        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        actual_B = pump_A * ratio
        pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
        pump_inject_B = float(np.sum(pB * dt))

        pump_cost_this_step = pump_inject_A + pump_inject_B
        total_pump_spend += pump_cost_this_step
        reactor_budget -= pump_cost_this_step

        sigma += pA * dt
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
            alive = False
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Probe cycling -- DEBIT REACTOR for new ejections
        min_peak_all = probe_mass
        for idx, probe in enumerate(probes):
            reading = probe.update(
                com, pump_a_pos, pump_b_pos,
                step, lam_field, sigma, nx, ny, rng)

            # Check for new ejection (cycle count increased)
            if probe.ejection_count > prev_ejection_counts[idx]:
                # New ejection -- pay creation cost
                creation_debit = creation_cost_per_probe
                total_probe_creation_spend += creation_debit
                reactor_budget -= creation_debit
                prev_ejection_counts[idx] = probe.ejection_count

            # Track coherence
            if probe.current_peak < min_peak_all:
                min_peak_all = probe.current_peak

            # Dissolution check
            if (probe.state == InstrumentedProbe.EJECTED and
                    probe.current_peak < dissolution_threshold):
                if not any_probe_dissolved:
                    any_probe_dissolved = True
                dissolution_events.append({
                    "step": step,
                    "pid": probe.pid,
                    "cycle": probe.cycles_completed,
                    "peak": round(probe.current_peak, 8),
                    "distance": round(float(np.linalg.norm(
                        probe.position - com)), 2),
                })

        # Accumulate arc tax from all probes
        total_probe_arc_tax = sum(p.arc_tax_total for p in probes)

        # Check reactor
        if reactor_budget <= 0:
            print(f"\n  ** REACTOR DEPLETED at step {step} **")
            alive = False
            break

        # Log every 100 steps
        if step % 100 == 0:
            total_probe_spend = (total_probe_creation_spend +
                                 total_probe_arc_tax)
            total_spend = total_pump_spend + total_probe_spend
            probe_pct = ((total_probe_spend / total_spend * 100)
                         if total_spend > 0 else 0)

            timeline.append({
                "step": step,
                "reactor_remaining": round(reactor_budget, 4),
                "total_pump_spend": round(total_pump_spend, 4),
                "total_probe_spend": round(total_probe_spend, 6),
                "probe_pct": round(probe_pct, 4),
                "min_probe_peak": round(min_peak_all, 6),
            })

            print(f"  {step:>6} {reactor_budget:>10.2f} "
                  f"{total_pump_spend:>10.2f} "
                  f"{total_probe_spend:>10.4f} "
                  f"{probe_pct:>7.3f}% "
                  f"{min_peak_all:>8.4f}")

    # ═══════════════════════════════════════════════════
    # FINAL REPORT
    # ═══════════════════════════════════════════════════
    total_probe_arc_tax = sum(p.arc_tax_total for p in probes)
    total_probe_spend = total_probe_creation_spend + total_probe_arc_tax
    total_spend = total_pump_spend + total_probe_spend
    probe_pct = (total_probe_spend / total_spend * 100
                 if total_spend > 0 else 0)
    pump_pct = 100.0 - probe_pct

    print(f"\n{'='*65}")
    print(f"  DIAGNOSTIC 1: PROBE FUEL BUDGET")
    print(f"{'='*65}")
    print(f"\n  Reactor initial:    {reactor_initial:.2f}")
    print(f"  Reactor remaining:  {reactor_budget:.2f}")
    print(f"  Reactor consumed:   {reactor_initial - reactor_budget:.2f}")
    print(f"\n  PROPULSION (pumps): {total_pump_spend:.4f} "
          f"({pump_pct:.3f}%)")
    print(f"  OBSERVATION total:  {total_probe_spend:.6f} "
          f"({probe_pct:.3f}%)")
    print(f"    Creation cost:    {total_probe_creation_spend:.6f}")
    print(f"    Arc substrate tax:{total_probe_arc_tax:.6f}")

    total_ejections = sum(p.ejection_count for p in probes)
    print(f"\n  Total ejections:    {total_ejections}")
    print(f"  Cost per ejection:  {creation_cost_per_probe:.4f}")

    # VERDICT
    budget_kill = probe_pct > 20.0
    print(f"\n  KILL CONDITION (>20%): {'FAIL -- PARASITIC' if budget_kill else 'PASS'}")
    print(f"  Probe budget share:   {probe_pct:.4f}%")

    print(f"\n{'='*65}")
    print(f"  DIAGNOSTIC 2: PROBE COHERENCE DECAY")
    print(f"{'='*65}")

    print(f"\n  {'PID':>4} {'Cycles':>7} {'WorstPeak':>10} "
          f"{'WorstDist':>10} {'FinalPeak':>10} {'Survived':>9}")
    print(f"  {'-'*4} {'-'*7} {'-'*10} {'-'*10} {'-'*10} {'-'*9}")

    for p in probes:
        survived = "YES" if p.worst_apoapsis_peak > dissolution_threshold else "DEAD"
        print(f"  {p.pid:>4} {p.cycles_completed:>7} "
              f"{p.worst_apoapsis_peak:>10.6f} "
              f"{p.worst_apoapsis_distance:>10.2f} "
              f"{p.current_peak:>10.6f} {survived:>9}")

    worst_probe = min(probes, key=lambda p: p.worst_apoapsis_peak)
    print(f"\n  Worst apoapsis peak:  {worst_probe.worst_apoapsis_peak:.6f} "
          f"(probe {worst_probe.pid})")
    print(f"  Worst apoapsis dist:  {worst_probe.worst_apoapsis_distance:.2f} px")
    print(f"  Dissolution threshold:{dissolution_threshold}")
    print(f"  Margin:               "
          f"{worst_probe.worst_apoapsis_peak / dissolution_threshold:.2f}x")

    coherence_kill = any_probe_dissolved
    print(f"\n  KILL CONDITION (dissolves): "
          f"{'FAIL -- GHOST SHIP' if coherence_kill else 'PASS'}")
    if dissolution_events:
        print(f"  Dissolution events: {len(dissolution_events)}")
        for de in dissolution_events[:5]:
            print(f"    step {de['step']}: probe {de['pid']} "
                  f"peak={de['peak']:.8f} dist={de['distance']} px")

    # ═══════════════════════════════════════════════════
    # COMBINED VERDICT
    # ═══════════════════════════════════════════════════
    print(f"\n{'='*65}")
    if not budget_kill and not coherence_kill:
        print(f"  BOTH DIAGNOSTICS PASS")
        print(f"  Probes cost {probe_pct:.4f}% of budget (under 20%)")
        print(f"  Worst coherence {worst_probe.worst_apoapsis_peak:.6f} "
              f"(above {dissolution_threshold})")
        print(f"  Architecture survives Attacks 1 and 2.")
    elif budget_kill and not coherence_kill:
        print(f"  DIAGNOSTIC 1 FAIL: Probes are parasitic ({probe_pct:.2f}%)")
        print(f"  DIAGNOSTIC 2 PASS: Probes survive coherence decay")
    elif coherence_kill and not budget_kill:
        print(f"  DIAGNOSTIC 1 PASS: Budget within limits")
        print(f"  DIAGNOSTIC 2 FAIL: Probes dissolve at apoapsis")
    else:
        print(f"  BOTH DIAGNOSTICS FAIL")
        print(f"  Architecture needs redesign.")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_diag_fuel_coherence_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v16 Diagnostic 1+2: Fuel Budget & Coherence",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Pre-emptive defense against Attacks 1 and 2",
        "grid": nx,
        "steps": args.steps,
        "probe_class": "MICRO",
        "probe_mass": probe_mass,
        "probe_width": probe_width,
        "reactor_initial": reactor_initial,
        "dissolution_threshold": dissolution_threshold,
        "diagnostic_1_fuel_budget": {
            "reactor_remaining": round(reactor_budget, 4),
            "total_pump_spend": round(total_pump_spend, 4),
            "total_probe_spend": round(total_probe_spend, 6),
            "probe_creation_spend": round(
                total_probe_creation_spend, 6),
            "probe_arc_tax": round(total_probe_arc_tax, 6),
            "probe_pct_of_total": round(probe_pct, 4),
            "total_ejections": total_ejections,
            "kill_threshold_pct": 20.0,
            "verdict": "FAIL" if budget_kill else "PASS",
        },
        "diagnostic_2_coherence": {
            "worst_apoapsis_peak": round(
                worst_probe.worst_apoapsis_peak, 6),
            "worst_apoapsis_distance": round(
                worst_probe.worst_apoapsis_distance, 2),
            "worst_probe_pid": worst_probe.pid,
            "margin_over_threshold": round(
                worst_probe.worst_apoapsis_peak /
                dissolution_threshold, 4),
            "dissolution_events": len(dissolution_events),
            "verdict": "FAIL" if coherence_kill else "PASS",
        },
        "probes": [p.to_dict() for p in probes],
        "timeline": timeline,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
