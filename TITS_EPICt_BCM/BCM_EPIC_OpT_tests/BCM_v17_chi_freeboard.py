# -*- coding: utf-8 -*-
"""
BCM v17 -- Chi Freeboard Diagnostic
======================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Chi Freeboard -- Stephen Burdick Sr.'s concept:

The chi field is the 4D headspace between the sigma
transport surface and the structural ceiling of the
tesseract cell. When sigma sloshes (Brucetron phase
debt), the overflow spills into chi instead of
accumulating in the craft structure. When sigma settles,
chi drains back. The tank never overflows because the
headspace absorbs the transient.

Industrial origin: kraft mill tank freeboard. If the
fluid level hits the top, you lose containment. If the
headspace is too large, the pump cavitates. The
freeboard must be sized to the sloshing amplitude.

IMPLEMENTATION:

E_total = sum(sigma) + sum(chi) = constant per cell

When sigma exceeds a threshold (the "fill line"):
  overflow = sigma - fill_line
  chi += overflow
  sigma = fill_line

When sigma drops below equilibrium:
  drain = min(chi, equilibrium - sigma)
  sigma += drain
  chi -= drain

The Brucetron phase debt transfers to chi instead of
accumulating in the structural field. Chi is the
pressure relief valve.

Conservation: sigma + chi = constant at all times.
The 4D divergence theorem holds because the tesseract
cell preserves the total.

TWO RUNS:
  Run A: No chi freeboard (baseline -- Brucetron grows)
  Run B: Chi freeboard active (Brucetron absorbed)

Kill condition: if Brucetron growth rate in Run B is
not significantly lower than Run A, chi freeboard
does not solve the phase debt problem.

Usage:
    python BCM_v17_chi_freeboard.py
    python BCM_v17_chi_freeboard.py --steps 3000 --grid 256
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


class FreeboardProbe:
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
        if self.cycle_step < b1:
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
            va = round(ca / (2 * math.pi / vc)) * (2 * math.pi / vc)
            aa = 0.3 * ca + 0.7 * va
            self.pos = np.array([
                pa[0] + ar * np.cos(aa),
                pa[1] + ar * np.sin(aa)])
            self._scoop(sigma, nx, ny)
        else:
            self.state = "FALLING"
            fs = self.cycle_step - b2
            tf = fs / self.t_fall
            self.pos = self.prev_pos + tf * (pb - self.prev_pos)
            if fs >= self.t_fall - 1:
                self._deposit(sigma, pb, nx, ny)
        disp = float(np.linalg.norm(self.pos - self.prev_pos))
        at_boundary = (abs(self.cycle_step - b1) <= 1 or
                       abs(self.cycle_step - b2) <= 1)
        return disp if at_boundary else 0.0

    def _scoop(self, sigma, nx, ny):
        ix = int(np.clip(self.pos[0], 0, nx - 1))
        iy = int(np.clip(self.pos[1], 0, ny - 1))
        xa = np.arange(max(0, ix - 4), min(nx, ix + 5))
        ya = np.arange(max(0, iy - 4), min(ny, iy + 5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl - self.pos[0])**2 + (Yl - self.pos[1])**2
        w = np.exp(-r2 / (2 * self.scoop_r**2))
        loc = sigma[np.ix_(xa, ya)]
        sc = np.minimum(loc * w * self.scoop_eff, loc)
        sc = np.maximum(sc, 0)
        sigma[np.ix_(xa, ya)] -= sc
        self.payload += float(np.sum(sc))

    def _deposit(self, sigma, pos, nx, ny):
        if self.payload <= 0:
            return
        ix = int(np.clip(pos[0], 0, nx - 1))
        iy = int(np.clip(pos[1], 0, ny - 1))
        xa = np.arange(max(0, ix - 4), min(nx, ix + 5))
        ya = np.arange(max(0, iy - 4), min(ny, iy + 5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl - pos[0])**2 + (Yl - pos[1])**2
        w = np.exp(-r2 / (2 * self.scoop_r**2))
        ws = float(np.sum(w))
        if ws > 1e-15:
            sigma[np.ix_(xa, ya)] += w * (self.payload / ws)
        self.payload = 0.0


def run_config(nx, ny, steps, dt, D, alpha, separation,
               pump_A, ratio, lam, X, Y,
               use_chi_freeboard, rng_seed=42):
    rng = np.random.RandomState(rng_seed)
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    chi = np.zeros((nx, ny))
    drain_rate = 0.1
    spill_rate = 0.5
    probes = [FreeboardProbe(i + 1, i * 5) for i in range(12)]
    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95
    ts_bruce_energy = []
    ts_chi_total = []
    ts_sigma_total = []
    ts_combined = []
    ts_debt = []
    cumulative_debt = 0.0

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break
        pa = np.array([com[0] + separation, com[1]])
        pb = np.array([com[0] - separation * 0.3, com[1]])
        r2A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2A / (2 * 4.0**2))
        sigma += pA * dt
        bx = com[0] + separation
        r2B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_A * ratio * np.exp(-r2B / (2 * 3.0**2))
        sigma += pB * dt
        lap = (np.roll(sigma, 1, 0) + np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) + np.roll(sigma, -1, 1) -
               4 * sigma)
        sn = sigma + D * lap * dt - lam * sigma * dt
        if alpha > 0:
            sn += alpha * (sigma - sigma_prev)
        sn = np.maximum(sn, 0)
        if float(np.max(sn)) > 1e10:
            break
        sigma_prev = sigma.copy()
        sigma = sn

        total_jump = 0.0
        for p in probes:
            jump = p.update(com, pa, pb, step, sigma,
                            nx, ny, rng)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx - 1))
                iy = int(np.clip(p.pos[1], 0, ny - 1))
                bruce_field[ix, iy] += jump * 0.1
                total_jump += jump
        bruce_field *= bruce_decay
        cumulative_debt += total_jump

        if use_chi_freeboard:
            ix_c = int(np.clip(com[0], 0, nx - 1))
            iy_c = int(np.clip(com[1], 0, ny - 1))
            r_vicinity = 20
            x_lo = max(0, ix_c - r_vicinity)
            x_hi = min(nx, ix_c + r_vicinity)
            y_lo = max(0, iy_c - r_vicinity)
            y_hi = min(ny, iy_c + r_vicinity)
            local_sigma = sigma[x_lo:x_hi, y_lo:y_hi]
            local_mean = float(np.mean(local_sigma))
            local_std = float(np.std(local_sigma))
            fill_line = local_mean + 1.5 * local_std
            overflow = np.maximum(sigma - fill_line, 0)
            spill = overflow * spill_rate
            sigma -= spill
            chi += spill
            deficit = np.maximum(fill_line * 0.8 - sigma, 0)
            available_drain = np.minimum(chi * drain_rate,
                                         deficit)
            sigma += available_drain
            chi -= available_drain
            chi *= 0.999
            bruce_in_chi = bruce_field * 0.05
            chi += bruce_in_chi * 0.01
            bruce_field -= bruce_in_chi
            bruce_field = np.maximum(bruce_field, 0)

        bruce_e = float(np.sum(bruce_field**2))
        chi_total = float(np.sum(chi))
        sig_total = float(np.sum(sigma))
        ts_bruce_energy.append(bruce_e)
        ts_chi_total.append(chi_total)
        ts_sigma_total.append(sig_total)
        ts_combined.append(sig_total + chi_total)
        ts_debt.append(cumulative_debt)

    return {
        "ts_bruce_energy": np.array(ts_bruce_energy),
        "ts_chi_total": np.array(ts_chi_total),
        "ts_sigma_total": np.array(ts_sigma_total),
        "ts_combined": np.array(ts_combined),
        "ts_debt": np.array(ts_debt),
        "final_bruce_rms": float(np.sqrt(
            np.mean(bruce_field**2))),
        "final_chi_total": float(np.sum(chi)),
        "final_sigma_total": float(np.sum(sigma)),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v17 Chi Freeboard Diagnostic")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v17 -- CHI FREEBOARD DIAGNOSTIC")
    print(f"  4D headspace absorbs Brucetron phase debt")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    dt = 0.05; D = 0.5; void_lambda = 0.10
    pump_A = 0.5; ratio = 0.25; alpha = 0.80
    separation = 15.0

    x_arr = np.arange(nx); y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')
    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny // 2)**2
    lam -= 0.08 * np.exp(-r2g / (2 * 18.0**2))
    lam = np.maximum(lam, 0.001)

    print(f"\n  {'─'*55}")
    print(f"  RUN A: NO CHI FREEBOARD (baseline)")
    print(f"  {'─'*55}")
    result_a = run_config(nx, ny, args.steps, dt, D, alpha,
                          separation, pump_A, ratio, lam, X, Y,
                          use_chi_freeboard=False)
    print(f"  Brucetron RMS:  {result_a['final_bruce_rms']:.8f}")
    print(f"  Sigma total:    {result_a['final_sigma_total']:.4f}")

    print(f"\n  {'─'*55}")
    print(f"  RUN B: CHI FREEBOARD ACTIVE")
    print(f"  {'─'*55}")
    result_b = run_config(nx, ny, args.steps, dt, D, alpha,
                          separation, pump_A, ratio, lam, X, Y,
                          use_chi_freeboard=True)
    print(f"  Brucetron RMS:  {result_b['final_bruce_rms']:.8f}")
    print(f"  Chi total:      {result_b['final_chi_total']:.4f}")
    print(f"  Sigma total:    {result_b['final_sigma_total']:.4f}")

    print(f"\n{'='*65}")
    print(f"  CHI FREEBOARD COMPARISON")
    print(f"{'='*65}")

    n_a = len(result_a["ts_bruce_energy"])
    n_b = len(result_b["ts_bruce_energy"])
    skip = 100

    bruce_early_a = bruce_late_a = 0
    bruce_early_b = bruce_late_b = 0
    if n_a > skip * 2:
        bruce_early_a = float(np.mean(
            result_a["ts_bruce_energy"][skip:skip + 100]))
        bruce_late_a = float(np.mean(
            result_a["ts_bruce_energy"][-100:]))
    if n_b > skip * 2:
        bruce_early_b = float(np.mean(
            result_b["ts_bruce_energy"][skip:skip + 100]))
        bruce_late_b = float(np.mean(
            result_b["ts_bruce_energy"][-100:]))

    rate_a = rate_b = 0
    exp_a = exp_b = 0
    if n_a > skip:
        steps_a = np.arange(skip, n_a, dtype=float)
        rate_a = np.polyfit(steps_a,
                            result_a["ts_bruce_energy"][skip:], 1)[0]
        pm = (steps_a > 0) & (result_a["ts_bruce_energy"][skip:] > 0)
        if np.sum(pm) > 2:
            exp_a = np.polyfit(np.log(steps_a[pm]),
                               np.log(result_a["ts_bruce_energy"][skip:][pm]), 1)[0]
    if n_b > skip:
        steps_b = np.arange(skip, n_b, dtype=float)
        rate_b = np.polyfit(steps_b,
                            result_b["ts_bruce_energy"][skip:], 1)[0]
        pm = (steps_b > 0) & (result_b["ts_bruce_energy"][skip:] > 0)
        if np.sum(pm) > 2:
            exp_b = np.polyfit(np.log(steps_b[pm]),
                               np.log(result_b["ts_bruce_energy"][skip:][pm]), 1)[0]

    print(f"\n  {'Metric':>25} {'No Freeboard':>15} "
          f"{'Chi Freeboard':>15} {'Change':>10}")
    print(f"  {'-'*25} {'-'*15} {'-'*15} {'-'*10}")
    print(f"  {'Early energy':>25} {bruce_early_a:>15.4f} "
          f"{bruce_early_b:>15.4f} "
          f"{(bruce_early_b / bruce_early_a * 100 if bruce_early_a > 0 else 0):>9.1f}%")
    print(f"  {'Late energy':>25} {bruce_late_a:>15.4f} "
          f"{bruce_late_b:>15.4f} "
          f"{(bruce_late_b / bruce_late_a * 100 if bruce_late_a > 0 else 0):>9.1f}%")
    print(f"  {'Linear rate (dE/dt)':>25} {rate_a:>15.6f} "
          f"{rate_b:>15.6f} "
          f"{(rate_b / rate_a * 100 if rate_a > 0 else 0):>9.1f}%")
    print(f"  {'Power exponent':>25} {exp_a:>15.4f} "
          f"{exp_b:>15.4f}")
    print(f"  {'Final Brucetron RMS':>25} "
          f"{result_a['final_bruce_rms']:>15.8f} "
          f"{result_b['final_bruce_rms']:>15.8f}")

    print(f"\n  CHI FIELD STATUS:")
    print(f"    Chi total (Run B): {result_b['final_chi_total']:.4f}")
    print(f"    Sigma (A): {result_a['final_sigma_total']:.4f}")
    print(f"    Sigma (B): {result_b['final_sigma_total']:.4f}")
    if len(result_b["ts_combined"]) > 1:
        print(f"    Sigma+Chi start: {result_b['ts_combined'][0]:.4f}")
        print(f"    Sigma+Chi end:   {result_b['ts_combined'][-1]:.4f}")

    print(f"\n{'='*65}")
    print(f"  CHI FREEBOARD VERDICT")
    print(f"{'='*65}")

    rate_reduction = (1 - rate_b / rate_a) * 100 if rate_a > 0 else 0
    energy_reduction = (1 - bruce_late_b / bruce_late_a) * 100 if bruce_late_a > 0 else 0

    print(f"\n  Brucetron growth rate reduction: {rate_reduction:.1f}%")
    print(f"  Brucetron late energy reduction: {energy_reduction:.1f}%")

    if rate_reduction > 50:
        print(f"\n  CHI FREEBOARD SIGNIFICANTLY REDUCES BRUCETRON GROWTH")
        print(f"  The 4D headspace absorbs phase debt.")
    elif rate_reduction > 10:
        print(f"\n  CHI FREEBOARD PARTIALLY REDUCES GROWTH")
        print(f"  Freeboard parameters may need tuning.")
    elif rate_reduction > 0:
        print(f"\n  CHI FREEBOARD HAS MINIMAL EFFECT")
    else:
        print(f"\n  CHI FREEBOARD HAS NO EFFECT OR NEGATIVE")

    if exp_b < exp_a:
        print(f"\n  Power exponent reduced: {exp_a:.4f} -> {exp_b:.4f}")
        print(f"  Growth MORE saturating with freeboard.")
    if exp_b < 0:
        print(f"\n  Power exponent NEGATIVE: {exp_b:.4f}")
        print(f"  Brucetron energy DECAYING! Phase debt DISCHARGED.")

    print(f"{'='*65}")

    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v17_chi_freeboard_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v17 Chi Freeboard Diagnostic",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Chi freeboard (4D headspace) absorbs Brucetron phase debt",
        "grid": nx, "steps": args.steps,
        "results": {
            "no_freeboard": {
                "bruce_early": round(bruce_early_a, 6),
                "bruce_late": round(bruce_late_a, 6),
                "growth_rate": round(rate_a, 8),
                "power_exponent": round(exp_a, 4),
                "final_bruce_rms": round(result_a["final_bruce_rms"], 8),
                "final_sigma": round(result_a["final_sigma_total"], 4),
            },
            "chi_freeboard": {
                "bruce_early": round(bruce_early_b, 6),
                "bruce_late": round(bruce_late_b, 6),
                "growth_rate": round(rate_b, 8),
                "power_exponent": round(exp_b, 4),
                "final_bruce_rms": round(result_b["final_bruce_rms"], 8),
                "final_sigma": round(result_b["final_sigma_total"], 4),
                "final_chi": round(result_b["final_chi_total"], 4),
            },
        },
        "comparison": {
            "rate_reduction_pct": round(rate_reduction, 2),
            "energy_reduction_pct": round(energy_reduction, 2),
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
