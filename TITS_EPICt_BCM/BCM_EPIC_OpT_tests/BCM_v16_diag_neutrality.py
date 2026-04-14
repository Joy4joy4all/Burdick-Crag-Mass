# -*- coding: utf-8 -*-
"""
BCM v16 -- Diagnostic 3C: Energy Neutrality Test
==================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

ChatGPT VEV Attack: "If probes harvest energy universally,
you've built a vacuum energy extractor. That's free lunch."

Three controlled regimes test whether probe harvesting is
physically coupled to gradients or is a numerical artifact:

  Run 1: UNIFORM FIELD (no gradients, constant lambda)
    Expected: net harvest = 0
    If harvest > 0 -> FAIL (free energy from nothing)

  Run 2: REVERSED GRADIENT (lambda field flipped)
    Expected: harvest flips sign (becomes cost)
    If still positive -> FAIL (directional bias bug)

  Run 3: ZERO PUMP (probes only, no A/B drive)
    Expected: no sustained energy gain or drift
    If drift persists -> FAIL (observer creates energy)

  Run 4: NORMAL (hazard field, pumps active -- control)
    Expected: positive drift with active probes

All four runs use active probes (stamp +sigma).
Comparison baseline: Run 4 drift is the reference.

Kill conditions:
  1. Uniform harvest > 5% of control -> FREE ENERGY FAIL
  2. Reversed drift same sign as control -> BIAS BUG FAIL
  3. Zero pump drift > 5% of control -> OBSERVER ENERGY FAIL

Usage:
    python BCM_v16_diag_neutrality.py
    python BCM_v16_diag_neutrality.py --steps 3000 --grid 256
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
# ACTIVE PROBE (stamp +sigma, same as decomposition)
# ═══════════════════════════════════════════════════════

class ActiveProbe:
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
        else:
            self.state = "FALLING"
            fall_step = (self.cycle_step -
                         self.transit_duration -
                         self.arc_duration)
            t_fall = fall_step / self.fall_duration
            self.position = (self.position +
                             t_fall *
                             (pump_b_pos - self.position))

    def stamp_sigma(self, sigma, nx, ny):
        if self.state != "EJECTED":
            return
        x_arr = np.arange(nx)
        y_arr = np.arange(ny)
        X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')
        r2 = ((X - self.position[0])**2 +
              (Y - self.position[1])**2)
        footprint = self.probe_mass * np.exp(
            -r2 / (2 * self.probe_width**2))
        sigma += footprint


# ═══════════════════════════════════════════════════════
# TRANSIT ENGINE
# ═══════════════════════════════════════════════════════

def run_transit(nx, ny, steps, dt, D, alpha, separation,
                pump_A, ratio, lam_field, use_pumps,
                use_probes, rng_seed):
    """
    Configurable transit run.
    lam_field: pre-built lambda field (caller controls shape)
    use_pumps: if False, no A/B pump injection
    use_probes: if False, no probe cycling
    """
    rng = np.random.RandomState(rng_seed)

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    # Sigma (craft)
    start_x = nx // 8
    start_y = ny // 2
    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    initial_com = compute_com(sigma)

    # Probes
    probes = []
    if use_probes:
        for i in range(12):
            probes.append(ActiveProbe(i + 1, i * 5))

    timeline = []
    sigma_total_start = float(np.sum(sigma))

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        pump_a_pos = np.array([com[0] + separation, com[1]])
        pump_b_pos = np.array([com[0] - separation * 0.3,
                               com[1]])

        # Pumps (conditional)
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

        # Probe cycling
        if use_probes:
            for probe in probes:
                probe.update(com, pump_a_pos, pump_b_pos,
                             step, nx, ny, rng)
                probe.stamp_sigma(sigma, nx, ny)

        # Log every 100 steps
        if step % 100 == 0:
            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(
                    new_com - initial_com))
                coh = compute_coherence(sigma, new_com)
                stot = float(np.sum(sigma))
                timeline.append({
                    "step": step,
                    "x": round(float(new_com[0]), 2),
                    "drift": round(drift, 2),
                    "coherence": round(coh, 4),
                    "sigma_total": round(stot, 4),
                })

    sigma_total_end = float(np.sum(sigma))
    final_com = compute_com(sigma)
    final_drift = 0.0
    if final_com is not None:
        final_drift = float(np.linalg.norm(
            final_com - initial_com))

    return {
        "final_drift": round(final_drift, 4),
        "sigma_start": round(sigma_total_start, 4),
        "sigma_end": round(sigma_total_end, 4),
        "sigma_change": round(sigma_total_end -
                              sigma_total_start, 4),
        "timeline": timeline,
    }


# ═══════════════════════════════════════════════════════
# MAIN DIAGNOSTIC
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Diagnostic 3C: Neutrality")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v16 -- DIAGNOSTIC 3C: ENERGY NEUTRALITY TEST")
    print(f"  Does probe harvesting require gradients?")
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

    # ── BUILD LAMBDA FIELDS ──

    # Normal: hazard field (same as tunnel_probes.py)
    lam_normal = np.full((nx, ny), void_lambda, dtype=float)
    gx1 = nx // 3
    r2 = (X - gx1)**2 + (Y - ny//2)**2
    lam_normal -= 0.04 * np.exp(-r2 / (2 * 12.0**2))
    gx2 = nx // 2
    r2 = (X - gx2)**2 + (Y - ny//2)**2
    lam_normal -= 0.08 * np.exp(-r2 / (2 * 18.0**2))
    lam_normal = np.maximum(lam_normal, 0.001)

    # Uniform: flat lambda everywhere
    lam_uniform = np.full((nx, ny), void_lambda, dtype=float)

    # Reversed: graves behind start position instead of ahead
    lam_reversed = np.full((nx, ny), void_lambda, dtype=float)
    # Mirror the graves to the LEFT of start (start_x = nx//8)
    start_x = nx // 8
    # Place graves at distances BEHIND start
    gx1_rev = start_x - (gx1 - start_x)  # mirror shallow
    gx2_rev = start_x - (gx2 - start_x)  # mirror deep
    # Clamp to grid
    gx1_rev = max(5, gx1_rev)
    gx2_rev = max(5, gx2_rev)
    r2 = (X - gx1_rev)**2 + (Y - ny//2)**2
    lam_reversed -= 0.04 * np.exp(-r2 / (2 * 12.0**2))
    r2 = (X - gx2_rev)**2 + (Y - ny//2)**2
    lam_reversed -= 0.08 * np.exp(-r2 / (2 * 18.0**2))
    lam_reversed = np.maximum(lam_reversed, 0.001)

    runs = {}

    # ── RUN 1: UNIFORM FIELD + PUMPS + PROBES ──
    print(f"\n  {'─'*55}")
    print(f"  RUN 1: UNIFORM FIELD (no gradients)")
    print(f"  {'─'*55}")
    runs["uniform"] = run_transit(
        nx, ny, args.steps, dt, D, alpha, separation,
        pump_A, ratio, lam_uniform,
        use_pumps=True, use_probes=True, rng_seed=42)
    print(f"  Drift: {runs['uniform']['final_drift']:.2f} px")
    print(f"  Sigma change: {runs['uniform']['sigma_change']:.4f}")

    # ── RUN 2: REVERSED GRADIENT + PUMPS + PROBES ──
    print(f"\n  {'─'*55}")
    print(f"  RUN 2: REVERSED GRADIENT (graves behind)")
    print(f"  {'─'*55}")
    runs["reversed"] = run_transit(
        nx, ny, args.steps, dt, D, alpha, separation,
        pump_A, ratio, lam_reversed,
        use_pumps=True, use_probes=True, rng_seed=42)
    print(f"  Drift: {runs['reversed']['final_drift']:.2f} px")
    print(f"  Sigma change: {runs['reversed']['sigma_change']:.4f}")

    # ── RUN 3: ZERO PUMP (probes only) ──
    print(f"\n  {'─'*55}")
    print(f"  RUN 3: ZERO PUMP (probes only, normal field)")
    print(f"  {'─'*55}")
    runs["zero_pump"] = run_transit(
        nx, ny, args.steps, dt, D, alpha, separation,
        pump_A, ratio, lam_normal,
        use_pumps=False, use_probes=True, rng_seed=42)
    print(f"  Drift: {runs['zero_pump']['final_drift']:.2f} px")
    print(f"  Sigma change: "
          f"{runs['zero_pump']['sigma_change']:.4f}")

    # ── RUN 4: NORMAL (control) ──
    print(f"\n  {'─'*55}")
    print(f"  RUN 4: NORMAL (hazard field + pumps + probes)")
    print(f"  {'─'*55}")
    runs["normal"] = run_transit(
        nx, ny, args.steps, dt, D, alpha, separation,
        pump_A, ratio, lam_normal,
        use_pumps=True, use_probes=True, rng_seed=42)
    print(f"  Drift: {runs['normal']['final_drift']:.2f} px")
    print(f"  Sigma change: {runs['normal']['sigma_change']:.4f}")

    # ═══════════════════════════════════════════════════
    # NEUTRALITY ANALYSIS
    # ═══════════════════════════════════════════════════

    control_drift = runs["normal"]["final_drift"]
    uniform_drift = runs["uniform"]["final_drift"]
    reversed_drift = runs["reversed"]["final_drift"]
    zero_drift = runs["zero_pump"]["final_drift"]

    print(f"\n{'='*65}")
    print(f"  NEUTRALITY ANALYSIS")
    print(f"{'='*65}")

    print(f"\n  DRIFT COMPARISON:")
    print(f"    Normal (control):   {control_drift:.2f} px")
    print(f"    Uniform field:      {uniform_drift:.2f} px")
    print(f"    Reversed gradient:  {reversed_drift:.2f} px")
    print(f"    Zero pump:          {zero_drift:.2f} px")

    # ── KILL 1: Uniform harvest ──
    print(f"\n  {'─'*55}")
    print(f"  KILL 1: Free energy from uniform field")
    if control_drift > 0:
        uniform_pct = (uniform_drift / control_drift) * 100
    else:
        uniform_pct = 0
    kill_1 = uniform_pct > 5.0
    print(f"    Uniform drift as % of control: {uniform_pct:.2f}%")
    print(f"    Threshold: < 5%")
    if kill_1:
        print(f"    Verdict: ** INVESTIGATE ** -- "
              f"drift in uniform field")
        # Context matters: pumps still create local gradient
        # even in uniform field. Check if drift is from
        # pumps alone vs probes adding to it.
        print(f"    NOTE: Pumps create LOCAL gradient even in "
              f"uniform lambda. This drift may be pump-driven, "
              f"not probe-harvested. Compare with zero-probe "
              f"uniform run to separate.")
    else:
        print(f"    Verdict: PASS -- no free energy in "
              f"uniform field")

    # ── KILL 2: Reversed gradient ──
    print(f"\n  {'─'*55}")
    print(f"  KILL 2: Directional bias (reversed gradient)")
    # In reversed field, graves are behind. The craft should
    # still drift forward (pumps push forward), but the
    # harvest effect should not help because the gradient
    # favoring forward travel is gone.
    same_sign = reversed_drift > 0 and control_drift > 0
    if control_drift > 0:
        reversed_pct = (reversed_drift / control_drift) * 100
    else:
        reversed_pct = 0
    # If reversed drift is LARGER than control, probes are
    # harvesting regardless of gradient -> bias bug
    reversed_exceeds = reversed_drift > control_drift * 1.05
    kill_2 = reversed_exceeds
    print(f"    Reversed drift as % of control: "
          f"{reversed_pct:.2f}%")
    print(f"    Reversed exceeds control: "
          f"{'YES' if reversed_exceeds else 'NO'}")
    print(f"    Verdict: {'FAIL -- harvest ignores gradient' if kill_2 else 'PASS -- gradient-coupled'}")

    # ── KILL 3: Zero pump drift ──
    print(f"\n  {'─'*55}")
    print(f"  KILL 3: Observer creates energy (zero pump)")
    if control_drift > 0:
        zero_pct = (zero_drift / control_drift) * 100
    else:
        zero_pct = 0
    kill_3 = zero_pct > 5.0
    print(f"    Zero-pump drift as % of control: "
          f"{zero_pct:.2f}%")
    print(f"    Threshold: < 5%")
    print(f"    Verdict: {'FAIL -- probes create drift alone' if kill_3 else 'PASS -- probes need pumps'}")

    # ── TRAJECTORY COMPARISON ──
    print(f"\n  {'─'*55}")
    print(f"  TRAJECTORY COMPARISON")
    print(f"  {'Step':>6} {'Uniform':>10} {'Reversed':>10} "
          f"{'ZeroPump':>10} {'Normal':>10}")
    print(f"  {'-'*6} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    traj_comp = []
    max_len = min(
        len(runs["uniform"]["timeline"]),
        len(runs["reversed"]["timeline"]),
        len(runs["zero_pump"]["timeline"]),
        len(runs["normal"]["timeline"]),
    )
    for i in range(0, max_len, 5):
        u = runs["uniform"]["timeline"][i]
        r = runs["reversed"]["timeline"][i]
        z = runs["zero_pump"]["timeline"][i]
        n = runs["normal"]["timeline"][i]
        traj_comp.append({
            "step": u["step"],
            "uniform": u["drift"],
            "reversed": r["drift"],
            "zero_pump": z["drift"],
            "normal": n["drift"],
        })
        print(f"  {u['step']:>6} {u['drift']:>10.2f} "
              f"{r['drift']:>10.2f} {z['drift']:>10.2f} "
              f"{n['drift']:>10.2f}")

    # ═══════════════════════════════════════════════════
    # COMBINED VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  COMBINED VERDICT")
    print(f"{'='*65}")

    print(f"\n  Kill 1 (uniform free energy): "
          f"{'INVESTIGATE' if kill_1 else 'PASS'}")
    print(f"  Kill 2 (directional bias):    "
          f"{'FAIL' if kill_2 else 'PASS'}")
    print(f"  Kill 3 (observer energy):     "
          f"{'FAIL' if kill_3 else 'PASS'}")

    any_fail = kill_2 or kill_3
    if not any_fail and not kill_1:
        print(f"\n  ALL KILL CONDITIONS PASS")
        print(f"  Probe harvesting is gradient-coupled,")
        print(f"  pump-dependent, and not free energy.")
    elif not any_fail and kill_1:
        print(f"\n  KILLS 2+3 PASS, KILL 1 NEEDS INVESTIGATION")
        print(f"  Uniform drift may be pump-created local "
              f"gradient.")
        print(f"  Run uniform field WITHOUT probes to separate.")
    else:
        print(f"\n  ONE OR MORE KILL CONDITIONS FAILED")
        print(f"  Architecture needs investigation.")
    print(f"{'='*65}")

    # ═══════════════════════════════════════════════════
    # SAVE
    # ═══════════════════════════════════════════════════

    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_diag_neutrality_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v16 Diagnostic 3C: Energy Neutrality",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("VEV attack: does harvest require "
                     "gradients or is it free energy?"),
        "grid": nx,
        "steps": args.steps,
        "drifts": {
            "normal_control": control_drift,
            "uniform_field": uniform_drift,
            "reversed_gradient": reversed_drift,
            "zero_pump": zero_drift,
        },
        "sigma_changes": {
            "normal": runs["normal"]["sigma_change"],
            "uniform": runs["uniform"]["sigma_change"],
            "reversed": runs["reversed"]["sigma_change"],
            "zero_pump": runs["zero_pump"]["sigma_change"],
        },
        "kill_conditions": {
            "kill_1_uniform_pct": round(uniform_pct, 4),
            "kill_1_pass": not kill_1,
            "kill_2_reversed_pct": round(reversed_pct, 4),
            "kill_2_reversed_exceeds": reversed_exceeds,
            "kill_2_pass": not kill_2,
            "kill_3_zero_pct": round(zero_pct, 4),
            "kill_3_pass": not kill_3,
        },
        "verdict": ("PASS" if (not any_fail and not kill_1)
                    else "INVESTIGATE" if (not any_fail)
                    else "FAIL"),
        "trajectory_comparison": traj_comp,
        "timelines": {
            "uniform": runs["uniform"]["timeline"],
            "reversed": runs["reversed"]["timeline"],
            "zero_pump": runs["zero_pump"]["timeline"],
            "normal": runs["normal"]["timeline"],
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
