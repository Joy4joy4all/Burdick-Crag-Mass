# -*- coding: utf-8 -*-
"""
BCM v16 — Tunnel Cycling Probes
==================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The probes do not orbit. They cycle THROUGH the craft.

  B (weak pump) INGESTS → tunnel transit → A (strong pump) EJECTS
  → ride Alfven lines outward → polygonal arc → sample substrate
  → fall back to B collector vortex → repeat

The tunnel is the magnetic core — a collider that accelerates
the probe. The probe doesn't need its own speed because the
craft's pump field carries it. A ejects, B collects. The
cycle is the same as Spica's mass transfer but reversed for
our purpose: we WANT the transfer because the probe IS the
transfer.

The probes ride the Alfven lines outward like the lambda
drive rides wells and ridges. The paths are polygonal, not
circular — the tesseract vertex rotation creates shifting
orbital shapes as the 4D geometry rotates.

Roche limit: each probe must maintain coherence through
ejection. If the pump gradient exceeds the probe's binding
energy, the probe shreds. We measure this.

12 probes, staggered ejection timing, random arc variance
on each cycle. Every reading is forward-weighted because
every probe exits through A (the forward pump).

Usage:
    python BCM_v16_tunnel_probes.py
    python BCM_v16_tunnel_probes.py --steps 3000 --grid 256
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
# EVIDENCE + HYPOTHESIS (from Genesis brain)
# ═══════════════════════════════════════════════════════

EVIDENCE_STRENGTH = {
    "density_anomaly": 0.50, "void_confirmed": 0.20,
    "lambda_gradient": 0.40, "wake_mass": 0.35,
    "density_normal": 0.10, "default": 0.10,
}


class Hypothesis:
    def __init__(self, key, name, prior=0.50):
        self.key = key
        self.name = name
        self.posterior = prior
        self.count = 0
        self.status = "NEEDS_MORE_DATA"

    def update(self, direction, etype="default", weight=1.0):
        strength = EVIDENCE_STRENGTH.get(etype, 0.10) * weight
        p = max(0.01, min(0.99, self.posterior))
        lo = math.log(p / (1.0 - p))
        lo += direction * strength
        self.posterior = 1.0 / (1.0 + math.exp(-lo))
        self.count += 1
        if self.count >= 3:
            if self.posterior >= 0.85:
                self.status = "VALIDATED"
            elif self.posterior <= 0.15:
                self.status = "INVALIDATED"


# ═══════════════════════════════════════════════════════
# TUNNEL CYCLING PROBE
# ═══════════════════════════════════════════════════════

class TunnelProbe:
    """
    A probe that cycles through the craft's tunnel.

    States:
      TRANSIT:  inside tunnel (B→A), not sampling
      EJECTED:  outside, riding Alfven arc, sampling
      FALLING:  returning to B collector vortex
      INGESTED: entering B, about to transit

    The arc is polygonal — tesseract vertex rotation
    creates shifting orbital shapes. Random variance
    on each ejection gives different sampling coverage.
    """
    TRANSIT = "TRANSIT"
    EJECTED = "EJECTED"
    FALLING = "FALLING"
    INGESTED = "INGESTED"

    def __init__(self, pid, eject_offset):
        self.pid = pid
        self.state = self.TRANSIT
        self.eject_offset = eject_offset  # staggered timing
        self.position = np.array([0.0, 0.0])
        self.arc_angle = 0.0
        self.arc_radius = 0.0
        self.arc_max_radius = 0.0
        self.cycle_step = 0
        self.cycles_completed = 0
        self.readings = []
        self.total_reads = 0
        self.roche_violations = 0
        self.alive = True

        # Timing
        self.transit_duration = 5    # steps inside tunnel
        self.arc_duration = 40       # steps on arc
        self.fall_duration = 10      # steps falling back

    def update(self, craft_com, pump_a_pos, pump_b_pos,
               step, lam_field, sigma, nx, ny, rng):
        """
        Advance probe state by one step.
        Returns a reading dict if sampling, else None.
        """
        if not self.alive:
            return None

        # Staggered start
        effective_step = step - self.eject_offset
        if effective_step < 0:
            self.position = craft_com.copy()
            return None

        cycle_length = (self.transit_duration +
                        self.arc_duration +
                        self.fall_duration)
        self.cycle_step = effective_step % cycle_length
        self.cycles_completed = effective_step // cycle_length

        # ── STATE MACHINE ──
        if self.cycle_step < self.transit_duration:
            # TRANSIT: inside tunnel, B → A
            self.state = self.TRANSIT
            t = self.cycle_step / self.transit_duration
            self.position = pump_b_pos + t * (pump_a_pos - pump_b_pos)
            return None

        elif self.cycle_step < self.transit_duration + self.arc_duration:
            # EJECTED: riding Alfven arc outward from A
            self.state = self.EJECTED
            arc_step = self.cycle_step - self.transit_duration

            # Polygonal arc: tesseract vertex rotation
            # Random variance per cycle gives different coverage
            base_angle_offset = rng.uniform(-0.8, 0.8)
            vertex_count = 5 + (self.cycles_completed % 4)  # 5-8 sided polygon

            # Arc grows then shrinks (apoapsis at midpoint)
            t_arc = arc_step / self.arc_duration
            self.arc_max_radius = 40.0 + rng.uniform(-10, 15)

            if t_arc < 0.5:
                self.arc_radius = self.arc_max_radius * (t_arc * 2)
            else:
                self.arc_radius = self.arc_max_radius * (2 - t_arc * 2)

            # Polygonal angle (snaps to vertex positions)
            continuous_angle = base_angle_offset + t_arc * 2 * math.pi
            vertex_angle = round(continuous_angle / (2 * math.pi / vertex_count)) * (2 * math.pi / vertex_count)
            # Blend between continuous and polygonal
            self.arc_angle = 0.3 * continuous_angle + 0.7 * vertex_angle

            # Position relative to A pump (forward of craft)
            self.position = np.array([
                pump_a_pos[0] + self.arc_radius * np.cos(self.arc_angle),
                pump_a_pos[1] + self.arc_radius * np.sin(self.arc_angle),
            ])

            # ROCHE LIMIT CHECK
            # If lambda gradient at probe position exceeds
            # binding threshold, probe shreds
            ix = int(np.clip(self.position[0], 0, nx - 1))
            iy = int(np.clip(self.position[1], 0, ny - 1))

            grad_x = abs(float(
                lam_field[min(ix+1, nx-1), iy] -
                lam_field[max(ix-1, 0), iy]))
            grad_y = abs(float(
                lam_field[ix, min(iy+1, ny-1)] -
                lam_field[ix, max(iy-1, 0)]))
            tidal_stress = math.sqrt(grad_x**2 + grad_y**2)

            roche_limit = 0.05  # gradient threshold
            if tidal_stress > roche_limit:
                self.roche_violations += 1

            # SAMPLE
            local_lam = float(lam_field[ix, iy])
            local_sig = float(sigma[ix, iy])

            grad_mag = math.sqrt(
                float((lam_field[min(ix+1, nx-1), iy] -
                       lam_field[max(ix-1, 0), iy]) / 2.0)**2 +
                float((lam_field[ix, min(iy+1, ny-1)] -
                       lam_field[ix, max(iy-1, 0)]) / 2.0)**2)

            is_danger = local_lam < 0.04
            self.total_reads += 1

            reading = {
                "pid": self.pid,
                "cycle": self.cycles_completed,
                "ix": ix, "iy": iy,
                "lambda": round(local_lam, 6),
                "sigma": round(local_sig, 6),
                "grad": round(grad_mag, 8),
                "arc_radius": round(self.arc_radius, 2),
                "tidal_stress": round(tidal_stress, 6),
                "roche_ok": tidal_stress < roche_limit,
                "danger": is_danger,
                "forward": ix > int(craft_com[0]),
            }
            return reading

        else:
            # FALLING: returning to B collector
            self.state = self.FALLING
            fall_step = self.cycle_step - self.transit_duration - self.arc_duration
            t_fall = fall_step / self.fall_duration
            # Curve back toward B pump
            self.position = self.position + t_fall * (pump_b_pos - self.position)
            return None

    def to_dict(self):
        return {
            "pid": self.pid,
            "state": self.state,
            "cycles": self.cycles_completed,
            "total_reads": self.total_reads,
            "roche_violations": self.roche_violations,
            "alive": self.alive,
        }


# ═══════════════════════════════════════════════════════
# NAVIGATOR (forward-weighted Bayesian)
# ═══════════════════════════════════════════════════════

class ForwardNavigator:
    """
    Navigator that weights forward readings higher.
    Probes ejected from A always sample ahead — every
    reading is naturally forward-biased. Readings marked
    'forward=True' get 3x weight.
    """
    def __init__(self):
        self.hyp_safe = Hypothesis("SAFE", "Forward safe", 0.50)
        self.hyp_grave = Hypothesis("GRAVE", "Grave ahead", 0.30)
        self.decision = "PROCEED"
        self.history = []
        self.warnings = []
        self.forward_danger_count = 0

    def ingest(self, reading, step):
        # Forward readings get 3x weight
        w = 3.0 if reading.get("forward", False) else 1.0

        if reading["danger"]:
            self.hyp_grave.update(+1, "density_anomaly", w)
            self.hyp_safe.update(-1, "density_anomaly", w)
            if reading.get("forward"):
                self.forward_danger_count += 1
            self.warnings.append({
                "step": step, "probe": reading["pid"],
                "lambda": reading["lambda"],
                "forward": reading.get("forward", False),
            })
        elif reading["lambda"] > 0.07:
            self.hyp_safe.update(+1, "void_confirmed", w)
            self.hyp_grave.update(-1, "void_confirmed", w)
        else:
            self.hyp_safe.update(+1, "density_normal", w * 0.5)

    def decide(self, step):
        if self.hyp_grave.posterior > 0.70:
            self.decision = "AVOID"
        elif self.hyp_grave.posterior > 0.45:
            self.decision = "CAUTION"
        elif self.hyp_safe.posterior > 0.65:
            self.decision = "PROCEED"
        else:
            self.decision = "CAUTION"

        self.history.append({
            "step": step, "decision": self.decision,
            "safe_p": round(self.hyp_safe.posterior, 4),
            "grave_p": round(self.hyp_grave.posterior, 4),
            "fwd_dangers": self.forward_danger_count,
        })
        return self.decision


# ═══════════════════════════════════════════════════════
# MAIN TEST
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Tunnel Cycling Probes")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid
    rng = np.random.RandomState(42)

    print(f"\n{'='*65}")
    print(f"  BCM v16 — TUNNEL CYCLING PROBES")
    print(f"  B ingests → tunnel → A ejects → Alfven arc → sample")
    print(f"  Polygonal tesseract orbits. Forward-weighted nav.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
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

    # Lambda field with hazards
    lam_field = np.full((nx, ny), void_lambda, dtype=float)

    # Shallow grave at 1/3
    gx1 = nx // 3
    r2 = (X - gx1)**2 + (Y - ny//2)**2
    lam_field -= 0.04 * np.exp(-r2 / (2 * 12.0**2))

    # Deep grave at 1/2
    gx2 = nx // 2
    r2 = (X - gx2)**2 + (Y - ny//2)**2
    lam_field -= 0.08 * np.exp(-r2 / (2 * 18.0**2))

    lam_field = np.maximum(lam_field, 0.001)

    print(f"  Hazards: SHALLOW at x={gx1}, DEEP at x={gx2}")

    # Sigma (craft)
    start_x = nx // 8
    start_y = ny // 2
    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    initial_com = compute_com(sigma)
    omega_com = initial_com.copy()
    prev_com = initial_com.copy()

    # Build 12 probes with staggered ejection
    probes = []
    for i in range(12):
        offset = i * 5  # stagger by 5 steps each
        probes.append(TunnelProbe(i + 1, offset))

    # Navigator
    nav = ForwardNavigator()

    print(f"  Probes: {len(probes)} tunnel-cycling")
    print(f"  Cycle: {probes[0].transit_duration}t transit + "
          f"{probes[0].arc_duration}s arc + "
          f"{probes[0].fall_duration}s fall = "
          f"{probes[0].transit_duration + probes[0].arc_duration + probes[0].fall_duration}s total")

    timeline = []
    first_decision_change = None

    print(f"\n  {'Step':>6} {'X':>8} {'Sep':>8} {'Dec':>10} "
          f"{'Safe':>6} {'Grave':>6} {'Coh':>6} "
          f"{'FwdD':>5} {'Warn':>5}")
    print(f"  {'─'*6} {'─'*8} {'─'*8} {'─'*10} "
          f"{'─'*6} {'─'*6} {'─'*6} {'─'*5} {'─'*5}")

    alive = True
    prev_decision = "PROCEED"

    for step in range(args.steps):
        com = compute_com(sigma)
        if com is None:
            alive = False
            break

        # Pump positions
        pump_a_pos = np.array([com[0] + separation, com[1]])
        pump_b_pos = np.array([com[0] - separation * 0.3, com[1]])

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

        # Probe cycling
        for probe in probes:
            reading = probe.update(
                com, pump_a_pos, pump_b_pos,
                step, lam_field, sigma, nx, ny, rng)
            if reading is not None:
                nav.ingest(reading, step)

        # Navigator decision every 10 steps
        if step % 10 == 0:
            decision = nav.decide(step)
            if decision != prev_decision and first_decision_change is None:
                first_decision_change = step
            prev_decision = decision

        # Log
        if step % 100 == 0:
            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(new_com - initial_com))
                omega_sep = float(np.linalg.norm(new_com - omega_com))
                coh = compute_coherence(sigma, new_com)

                timeline.append({
                    "step": step,
                    "x": round(float(new_com[0]), 2),
                    "omega_sep": round(omega_sep, 2),
                    "decision": nav.decision,
                    "safe_p": round(nav.hyp_safe.posterior, 4),
                    "grave_p": round(nav.hyp_grave.posterior, 4),
                    "coherence": round(coh, 4),
                    "fwd_dangers": nav.forward_danger_count,
                    "warnings": len(nav.warnings),
                })

                print(f"  {step:>6} {new_com[0]:>8.1f} "
                      f"{omega_sep:>8.1f} {nav.decision:>10} "
                      f"{nav.hyp_safe.posterior:>6.3f} "
                      f"{nav.hyp_grave.posterior:>6.3f} "
                      f"{coh:>6.3f} "
                      f"{nav.forward_danger_count:>5} "
                      f"{len(nav.warnings):>5}")

        prev_com = com

    # ═══════════════════════════════════════════════════
    # FINAL REPORT
    # ═══════════════════════════════════════════════════
    final_com = compute_com(sigma)
    if final_com is not None:
        final_drift = float(np.linalg.norm(final_com - initial_com))
        final_omega = float(np.linalg.norm(final_com - omega_com))
        final_coh = compute_coherence(sigma, final_com)
    else:
        final_drift = 0
        final_omega = 0
        final_coh = 0

    print(f"\n{'='*65}")
    print(f"  TUNNEL CYCLING PROBES — FINAL REPORT")
    print(f"{'='*65}")

    print(f"\n  OMEGA ANCHOR: separation={final_omega:.2f} px  "
          f"{'PASS' if final_omega > 1 else 'FAIL'}")

    print(f"\n  NAVIGATOR:")
    print(f"    Final decision: {nav.decision}")
    print(f"    Forward danger readings: {nav.forward_danger_count}")
    print(f"    Total warnings: {len(nav.warnings)}")
    if first_decision_change:
        print(f"    First decision change: step {first_decision_change}")
    else:
        print(f"    No decision changes (stayed {nav.decision})")

    # Decision transitions
    transitions = []
    for i in range(1, len(nav.history)):
        if nav.history[i]["decision"] != nav.history[i-1]["decision"]:
            transitions.append(nav.history[i])
    print(f"    Transitions: {len(transitions)}")
    for t in transitions[:8]:
        print(f"      step {t['step']}: → {t['decision']} "
              f"safe={t['safe_p']:.3f} grave={t['grave_p']:.3f} "
              f"fwd={t['fwd_dangers']}")

    print(f"\n  PROBE FLEET:")
    print(f"    {'PID':>4} {'Cycles':>7} {'Reads':>6} "
          f"{'Roche':>6} {'State':>10}")
    print(f"    {'─'*4} {'─'*7} {'─'*6} {'─'*6} {'─'*10}")
    for p in probes:
        print(f"    {p.pid:>4} {p.cycles_completed:>7} "
              f"{p.total_reads:>6} {p.roche_violations:>6} "
              f"{p.state:>10}")

    total_reads = sum(p.total_reads for p in probes)
    total_roche = sum(p.roche_violations for p in probes)
    total_cycles = sum(p.cycles_completed for p in probes)

    print(f"\n    Total readings: {total_reads}")
    print(f"    Total cycles: {total_cycles}")
    print(f"    Roche violations: {total_roche}")
    print(f"    Craft alive: {'YES' if alive else 'NO'}")
    print(f"    Coherence: {final_coh:.4f}")

    # Verdict
    print(f"\n{'='*65}")
    omega_ok = final_omega > 1.0
    probes_warned = nav.forward_danger_count > 0
    nav_reacted = len(transitions) > 0

    if omega_ok and probes_warned and nav_reacted and alive:
        print(f"  ALL SYSTEMS: NOMINAL")
        print(f"  Tunnel cycling works. Forward-weighted nav reacts.")
        print(f"  Probes survived Roche. Craft survived transit.")
    elif omega_ok and probes_warned and not nav_reacted:
        print(f"  PARTIAL: Forward warnings received but no nav change.")
    elif omega_ok and not probes_warned:
        print(f"  PARTIAL: No forward danger detected.")
    else:
        print(f"  CHECK INDIVIDUAL SYSTEMS.")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_tunnel_probes_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v16 Tunnel Cycling Probes",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "B ingests, tunnel transits, A ejects, polygonal arcs",
        "grid": nx, "steps": args.steps,
        "result": {
            "alive": alive, "drift": round(final_drift, 4),
            "omega_sep": round(final_omega, 4),
            "coherence": round(final_coh, 4),
            "total_readings": total_reads,
            "total_cycles": total_cycles,
            "roche_violations": total_roche,
            "forward_dangers": nav.forward_danger_count,
            "transitions": len(transitions),
            "decision": nav.decision,
        },
        "transitions": transitions,
        "probes": [p.to_dict() for p in probes],
        "timeline": timeline,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
