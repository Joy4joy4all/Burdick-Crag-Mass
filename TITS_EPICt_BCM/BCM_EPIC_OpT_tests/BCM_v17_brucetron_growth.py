# -*- coding: utf-8 -*-
"""
BCM v17 -- Brucetron Growth Bound (Physics Route A)
=====================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

"A physics must be resolved before human conditions can
be met. If we don't know what that is solved then humans
will undergo a transition, possibly even the craft collapse
in warp." -- Stephen Burdick Sr.

THE QUESTION:
How fast does phase residue accumulate, and when does it
reach the biological harm threshold?

This diagnostic:
  1. Runs the transport model for extended duration (5000+)
  2. Measures brucetron energy E_phi at every step
  3. Fits the growth curve (linear, power, exponential)
  4. Derives the growth rate dE_phi/dt
  5. Computes mission time limit T_max for each bio band
  6. Maps to real time via CMB-locked dt

The growth bound is the MISSION CLOCK. Not fuel. Not
coherence. Phase residue accumulation is the constraint
that limits interstellar transit duration.

ChatGPT's formulation:
  dE_phi/dt = integral over cycle of
    delta_phi(x,t) * grad_sigma(x,t) dx

  Failure: D(t) = integral of |delta_phi_residual| dt
  Kill:    D(t) >= D_bio_threshold

This is State Debt -- accumulated phase error that the
crew's biology cannot discharge.

Usage:
    python BCM_v17_brucetron_growth.py
    python BCM_v17_brucetron_growth.py --steps 5000 --grid 256
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


# ═══════════════════════════════════════════════════════
# TRANSPORT PROBE (50-step locked, 5/35/10)
# ═══════════════════════════════════════════════════════

class GrowthProbe:
    def __init__(self, pid, eject_offset, scoop_eff=0.05,
                 scoop_r=2.0):
        self.pid = pid
        self.eject_offset = eject_offset
        self.scoop_eff = scoop_eff
        self.scoop_r = scoop_r
        self.pos = np.array([0.0, 0.0])
        self.prev_pos = np.array([0.0, 0.0])
        self.state = "TRANSIT"
        self.cycle_step = 0
        self.cycles = 0
        self.payload = 0.0
        self.t_transit = 5
        self.t_arc = 35
        self.t_fall = 10

    def update(self, com, pa, pb, step, sigma, nx, ny, rng):
        eff = step - self.eject_offset
        if eff < 0:
            self.pos = com.copy()
            self.prev_pos = self.pos.copy()
            return 0.0

        cl = self.t_transit + self.t_arc + self.t_fall
        prev = self.cycles
        self.cycle_step = eff % cl
        self.cycles = eff // cl

        if self.cycles > prev and self.payload > 0:
            self._deposit(sigma, pb, nx, ny)

        self.prev_pos = self.pos.copy()
        b1 = self.t_transit
        b2 = self.t_transit + self.t_arc

        if self.cycle_step < self.t_transit:
            self.state = "TRANSIT"
            t = self.cycle_step / self.t_transit
            self.pos = pb + t * (pa - pb)
        elif self.cycle_step < b2:
            self.state = "EJECTED"
            as_ = self.cycle_step - self.t_transit
            bao = rng.uniform(-0.8, 0.8)
            vc = 5 + (self.cycles % 4)
            ta = as_ / self.t_arc
            amr = 40.0 + rng.uniform(-10, 15)
            if ta < 0.5:
                ar = amr * (ta * 2)
            else:
                ar = amr * (2 - ta * 2)
            ca = bao + ta * 2 * math.pi
            va = round(ca/(2*math.pi/vc)) * (2*math.pi/vc)
            aa = 0.3*ca + 0.7*va
            self.pos = np.array([
                pa[0] + ar*np.cos(aa),
                pa[1] + ar*np.sin(aa)])
            self._scoop(sigma, nx, ny)
        else:
            self.state = "FALLING"
            fs = self.cycle_step - b2
            tf = fs / self.t_fall
            self.pos = self.prev_pos + tf * (pb - self.prev_pos)
            if fs >= self.t_fall - 1:
                self._deposit(sigma, pb, nx, ny)

        # Phase jump at boundaries
        disp = float(np.linalg.norm(self.pos - self.prev_pos))
        at_boundary = (abs(self.cycle_step - b1) <= 1 or
                       abs(self.cycle_step - b2) <= 1)
        return disp if at_boundary else 0.0

    def _scoop(self, sigma, nx, ny):
        ix = int(np.clip(self.pos[0], 0, nx-1))
        iy = int(np.clip(self.pos[1], 0, ny-1))
        xa = np.arange(max(0, ix-4), min(nx, ix+5))
        ya = np.arange(max(0, iy-4), min(ny, iy+5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl-self.pos[0])**2 + (Yl-self.pos[1])**2
        w = np.exp(-r2/(2*self.scoop_r**2))
        loc = sigma[np.ix_(xa, ya)]
        sc = np.minimum(loc*w*self.scoop_eff, loc)
        sc = np.maximum(sc, 0)
        sigma[np.ix_(xa, ya)] -= sc
        self.payload += float(np.sum(sc))

    def _deposit(self, sigma, pos, nx, ny):
        if self.payload <= 0:
            return
        ix = int(np.clip(pos[0], 0, nx-1))
        iy = int(np.clip(pos[1], 0, ny-1))
        xa = np.arange(max(0, ix-4), min(nx, ix+5))
        ya = np.arange(max(0, iy-4), min(ny, iy+5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl-pos[0])**2 + (Yl-pos[1])**2
        w = np.exp(-r2/(2*self.scoop_r**2))
        ws = float(np.sum(w))
        if ws > 1e-15:
            sigma[np.ix_(xa, ya)] += w*(self.payload/ws)
        self.payload = 0.0


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v17 Brucetron Growth Bound")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v17 -- BRUCETRON GROWTH BOUND")
    print(f"  How long before phase debt kills the crew?")
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

    rng = np.random.RandomState(42)
    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny//2)**2
    lam -= 0.08 * np.exp(-r2g / (2*18.0**2))
    lam = np.maximum(lam, 0.001)

    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2*5.0**2))
    sigma_prev = sigma.copy()

    probes = [GrowthProbe(i+1, i*5) for i in range(12)]

    # Brucetron tracking
    brucetron_field = np.zeros((nx, ny))
    brucetron_decay = 0.95

    # Time series -- sample EVERY step for growth fitting
    ts_orb_energy = []      # sum(brucetron^2)
    ts_phase_debt = []      # cumulative |delta_phi|
    ts_phase_rate = []      # instantaneous phase injection

    cumulative_debt = 0.0

    print(f"\n  Running extended transport model...")

    for step in range(args.steps):
        com = compute_com(sigma)
        if com is None:
            print(f"  !! Craft dissolved at step {step}")
            break

        pa = np.array([com[0] + separation, com[1]])
        pb = np.array([com[0] - separation*0.3, com[1]])

        # Pumps
        r2A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2A / (2*4.0**2))
        sigma += pA * dt
        bx = com[0] + separation
        r2B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_A * ratio * np.exp(-r2B / (2*3.0**2))
        sigma += pB * dt

        # PDE
        lap = (np.roll(sigma, 1, 0) + np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) + np.roll(sigma, -1, 1) -
               4*sigma)
        sn = sigma + D*lap*dt - lam*sigma*dt
        if alpha > 0:
            sn += alpha * (sigma - sigma_prev)
        sn = np.maximum(sn, 0)
        if float(np.max(sn)) > 1e10:
            break
        sigma_prev = sigma.copy()
        sigma = sn

        # Probes + phase measurement
        total_jump = 0.0
        for p in probes:
            jump = p.update(com, pa, pb, step, sigma,
                            nx, ny, rng)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx-1))
                iy = int(np.clip(p.pos[1], 0, ny-1))
                brucetron_field[ix, iy] += jump * 0.1
                total_jump += jump

        brucetron_field *= brucetron_decay

        # Track
        orb_e = float(np.sum(brucetron_field**2))
        cumulative_debt += total_jump
        ts_orb_energy.append(orb_e)
        ts_phase_debt.append(cumulative_debt)
        ts_phase_rate.append(total_jump)

        if step % 500 == 0 and step > 0:
            print(f"  step {step:>5}: orb_E={orb_e:.4f}  "
                  f"debt={cumulative_debt:.2f}  "
                  f"rate={total_jump:.4f}")

    n_samples = len(ts_orb_energy)
    print(f"\n  Collected {n_samples} samples")

    # ═══════════════════════════════════════════════════
    # GROWTH CURVE FITTING
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  GROWTH CURVE ANALYSIS")
    print(f"{'='*65}")

    orb_arr = np.array(ts_orb_energy)
    debt_arr = np.array(ts_phase_debt)
    steps_arr = np.arange(n_samples, dtype=float)

    # Skip first 100 steps (transient)
    skip = min(100, n_samples // 5)
    orb_fit = orb_arr[skip:]
    debt_fit = debt_arr[skip:]
    steps_fit = steps_arr[skip:]

    # Fit 1: Linear (E = a*t + b)
    if len(steps_fit) > 2:
        coeffs_lin = np.polyfit(steps_fit, orb_fit, 1)
        orb_rate_linear = coeffs_lin[0]

        # Fit 2: Power law (log E = a*log t + b)
        pos_mask = (steps_fit > 0) & (orb_fit > 0)
        if np.sum(pos_mask) > 2:
            log_s = np.log(steps_fit[pos_mask])
            log_e = np.log(orb_fit[pos_mask])
            coeffs_pow = np.polyfit(log_s, log_e, 1)
            power_exponent = coeffs_pow[0]
        else:
            power_exponent = 0

        # Fit 3: Debt growth (linear fit to cumulative)
        coeffs_debt = np.polyfit(steps_fit, debt_fit, 1)
        debt_rate = coeffs_debt[0]  # phase debt per step

        print(f"\n  BRUCETRON ENERGY GROWTH:")
        print(f"    Linear rate (dE/dt):  {orb_rate_linear:.6f} "
              f"per step")
        print(f"    Power law exponent:   {power_exponent:.4f}")
        print(f"    (E ~ t^{power_exponent:.2f})")

        print(f"\n  PHASE DEBT GROWTH:")
        print(f"    Debt rate:            {debt_rate:.4f} "
              f"per step")
        print(f"    Total debt at end:    {cumulative_debt:.2f}")

        # ── GROWTH CLASSIFICATION ──
        if power_exponent < 0.5:
            growth_class = "SUBLINEAR (saturating)"
        elif power_exponent < 1.1:
            growth_class = "LINEAR"
        elif power_exponent < 2.0:
            growth_class = "SUPERLINEAR (accelerating)"
        else:
            growth_class = "EXPLOSIVE"

        print(f"    Growth class:         {growth_class}")

    else:
        orb_rate_linear = 0
        power_exponent = 0
        debt_rate = 0
        growth_class = "INSUFFICIENT DATA"

    # ═══════════════════════════════════════════════════
    # MISSION TIME LIMIT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  MISSION TIME LIMIT (State Debt)")
    print(f"{'='*65}")

    # Biological thresholds (arbitrary units -- relative)
    # These represent the integrated phase exposure that
    # causes measurable biological effect
    bio_thresholds = {
        "discomfort":    cumulative_debt * 2,    # 2x current
        "impairment":    cumulative_debt * 5,    # 5x current
        "danger":        cumulative_debt * 10,   # 10x current
        "hemorrhage":    cumulative_debt * 50,   # 50x current
    }

    # CMB-locked dt
    f_dom = 0.020  # probe fundamental
    cmb_hz = 160.2e9
    dt_cmb = f_dom / cmb_hz  # seconds per step

    print(f"\n  CMB-locked dt: {dt_cmb:.4e} seconds/step")
    print(f"  Current debt rate: {debt_rate:.4f} units/step")

    if debt_rate > 0:
        print(f"\n  {'Level':>15} {'Threshold':>12} "
              f"{'Steps':>12} {'Time(s)':>14} {'Time(hr)':>12}")
        print(f"  {'-'*15} {'-'*12} {'-'*12} {'-'*14} {'-'*12}")

        mission_limits = {}
        for level, threshold in bio_thresholds.items():
            steps_to_threshold = threshold / debt_rate
            time_seconds = steps_to_threshold * dt_cmb
            time_hours = time_seconds / 3600

            mission_limits[level] = {
                "threshold": round(threshold, 2),
                "steps": round(steps_to_threshold, 0),
                "seconds": round(time_seconds, 6),
                "hours": round(time_hours, 6),
            }

            print(f"  {level:>15} {threshold:>12.2f} "
                  f"{steps_to_threshold:>12.0f} "
                  f"{time_seconds:>14.4e} "
                  f"{time_hours:>12.4e}")

        # At CMB scale, times will be extremely small
        # because dt_cmb ~ 1e-13 seconds
        # Real mission times require different dt mapping
        print(f"\n  NOTE: CMB-locked dt ({dt_cmb:.2e} s/step)")
        print(f"  produces extremely short mission times.")
        print(f"  The physical dt mapping determines whether")
        print(f"  these limits are nanoseconds or years.")

    # ── GROWTH BOUND FORMULA ──
    print(f"\n{'='*65}")
    print(f"  BRUCETRON GROWTH BOUND")
    print(f"{'='*65}")

    print(f"\n  CANDIDATE LAW:")
    print(f"    E_brucetron(t) ~ t^{power_exponent:.2f}")
    print(f"    D_debt(t) = {debt_rate:.4f} * t")
    print(f"")
    print(f"  MISSION CONSTRAINT:")
    print(f"    T_max = D_threshold / debt_rate")
    print(f"    T_max = D_threshold / {debt_rate:.4f}")
    print(f"")
    print(f"  GROWTH BOUND CLASSIFICATION: {growth_class}")

    if growth_class == "SUBLINEAR (saturating)":
        print(f"\n  FAVORABLE: phase debt grows slower over time.")
        print(f"  Long-duration transit may be feasible with")
        print(f"  periodic debt discharge (phase reset).")
    elif growth_class == "LINEAR":
        print(f"\n  NEUTRAL: phase debt grows at constant rate.")
        print(f"  Mission time is directly proportional to")
        print(f"  threshold. No acceleration, no saturation.")
    elif "SUPERLINEAR" in growth_class:
        print(f"\n  UNFAVORABLE: phase debt accelerates.")
        print(f"  Long-duration transit requires active")
        print(f"  brucetron discharge mechanism.")
    else:
        print(f"\n  CRITICAL: explosive growth. Transit not")
        print(f"  feasible without fundamental redesign.")

    print(f"{'='*65}")

    # ═══════════════════════════════════════════════════
    # SAVE
    # ═══════════════════════════════════════════════════

    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v17_brucetron_growth_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    # Subsample time series for JSON (every 10th)
    out_data = {
        "title": "BCM v17 Brucetron Growth Bound",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Phase residue accumulation rate and "
                     "mission time limit derivation"),
        "grid": nx,
        "steps": args.steps,
        "growth_analysis": {
            "linear_rate": round(orb_rate_linear, 8),
            "power_exponent": round(power_exponent, 4),
            "growth_class": growth_class,
            "debt_rate_per_step": round(debt_rate, 6),
            "total_debt": round(cumulative_debt, 4),
        },
        "mission_limits": mission_limits if debt_rate > 0 else {},
        "cmb_dt": dt_cmb,
        "timeseries_sampled": {
            "brucetron_energy": [round(float(orb_arr[i]), 6)
                                for i in range(0, n_samples, 10)],
            "phase_debt": [round(float(debt_arr[i]), 4)
                           for i in range(0, n_samples, 10)],
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
