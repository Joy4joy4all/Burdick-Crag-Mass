# -*- coding: utf-8 -*-
"""
BCM v19 -- Chi Operator Diagnostic
=====================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

v19 Test A proved Brucetron is phase-rigid in TIME (0.8%).
Combined with v18 spatial invariance, the Brucetron is now
classified as a time-invariant attractor in phase space.

The ONLY mechanism that achieves negative growth is the
chi tank (v17). This test does NOT add a new mechanism.
It MEASURES what the chi tank is already doing by computing
the chi operator at each step:

    chi_op = div(phi * grad(Xi_local)) - Xi_local * lap(phi)

Where Xi_local(x,t) = phi^2 + |grad_phi|^2 is the local
6D field-shape density (per-pixel, not summed).

Term 1: div(phi * grad(Xi_local))
    Coupled flux -- how phi flows along Xi gradients.

Term 2: Xi_local * lap(phi)
    Structure-weighted curvature of phi.

When these diverge: mode destabilizes.
When these balance: mode persists (Brucetron locks).

Goal: find chi_c -- the operator magnitude threshold
where Brucetron growth crosses permanently negative.

THREE CONFIGS (no new mechanisms):
    A: No dissipation (baseline) -- chi_op measured
    B: Chi tank (v17) -- chi_op measured
    C: Phase projection (v18) -- chi_op measured

Usage:
    python BCM_v19_chi_operator.py
    python BCM_v19_chi_operator.py --steps 5000 --grid 256
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


def gaussian_blur(field, sigma_blur=3.0):
    k = int(sigma_blur * 3)
    x = np.arange(-k, k + 1)
    kernel = np.exp(-x**2 / (2 * sigma_blur**2))
    kernel /= kernel.sum()
    out = np.zeros_like(field)
    for i in range(field.shape[0]):
        out[i, :] = np.convolve(field[i, :], kernel, mode='same')
    result = np.zeros_like(out)
    for j in range(field.shape[1]):
        result[:, j] = np.convolve(out[:, j], kernel, mode='same')
    return result


def compute_chi_operator(phi, dx=1.0):
    """
    chi_op = div(phi * grad(Xi_local)) - Xi_local * lap(phi)
    Xi_local = phi^2 + |grad_phi|^2

    DIAGNOSTIC ONLY. Does not modify any field.
    """
    dphi_x = (np.roll(phi, -1, 0) - np.roll(phi, 1, 0)) / (2 * dx)
    dphi_y = (np.roll(phi, -1, 1) - np.roll(phi, 1, 1)) / (2 * dx)
    lap_phi = (np.roll(phi, 1, 0) + np.roll(phi, -1, 0) +
               np.roll(phi, 1, 1) + np.roll(phi, -1, 1) -
               4 * phi) / (dx * dx)
    xi_local = phi**2 + dphi_x**2 + dphi_y**2
    dxi_x = (np.roll(xi_local, -1, 0) -
             np.roll(xi_local, 1, 0)) / (2 * dx)
    dxi_y = (np.roll(xi_local, -1, 1) -
             np.roll(xi_local, 1, 1)) / (2 * dx)
    flux_x = phi * dxi_x
    flux_y = phi * dxi_y
    div_flux = ((np.roll(flux_x, -1, 0) -
                 np.roll(flux_x, 1, 0)) / (2 * dx) +
                (np.roll(flux_y, -1, 1) -
                 np.roll(flux_y, 1, 1)) / (2 * dx))
    struct_curv = xi_local * lap_phi
    chi_op = div_flux - struct_curv
    chi_mag = float(np.sum(np.abs(chi_op)))
    chi_max = float(np.max(np.abs(chi_op)))
    return chi_op, chi_mag, chi_max


class PhaseProbe:
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

    def update(self, com, pa, pb, step, sigma, nx, ny, rng,
               probe_hits):
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
            ar = amr * (ta * 2) if ta < 0.5 else amr * (2 - ta * 2)
            ca = bao + ta * 2 * math.pi
            va = round(ca / (2 * math.pi / vc)) * (2 * math.pi / vc)
            aa = 0.3 * ca + 0.7 * va
            self.pos = np.array([
                pa[0] + ar * np.cos(aa),
                pa[1] + ar * np.sin(aa)])
            self._scoop(sigma, nx, ny)
            ix = int(np.clip(self.pos[0], 0, nx - 1))
            iy = int(np.clip(self.pos[1], 0, ny - 1))
            probe_hits[ix, iy] += 1.0
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
               mode, kappa_phase=0.002, rng_seed=42):
    rng = np.random.RandomState(rng_seed)
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    chi = np.zeros((nx, ny))
    phi = np.zeros((nx, ny))
    probe_hits = np.zeros((nx, ny))

    probes = [PhaseProbe(i + 1, i * 5) for i in range(12)]
    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95

    ts_bruce_energy = []
    ts_phi_energy = []
    ts_dissipated = []
    ts_sigma_total = []
    ts_xi_metric = []
    ts_chi_op_mag = []
    ts_chi_op_max = []
    cumulative_dissipated = 0.0

    chi_c_step = None
    chi_c_mag = None

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

        phase_error = sigma - sigma_prev
        phi = phi * 0.95 + phase_error

        sigma_prev = sigma.copy()
        sigma = sn

        total_jump = 0.0
        for p in probes:
            jump = p.update(com, pa, pb, step, sigma,
                            nx, ny, rng, probe_hits)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx - 1))
                iy = int(np.clip(p.pos[1], 0, ny - 1))
                bruce_field[ix, iy] += jump * 0.1
                total_jump += jump
        bruce_field *= bruce_decay

        dissipated_this_step = 0.0

        if mode == 'chi_tank':
            ix_c = int(np.clip(com[0], 0, nx - 1))
            iy_c = int(np.clip(com[1], 0, ny - 1))
            r_v = 20
            x_lo = max(0, ix_c - r_v)
            x_hi = min(nx, ix_c + r_v)
            y_lo = max(0, iy_c - r_v)
            y_hi = min(ny, iy_c + r_v)
            ls = sigma[x_lo:x_hi, y_lo:y_hi]
            fl = float(np.mean(ls)) + 1.5 * float(np.std(ls))
            overflow = np.maximum(sigma - fl, 0)
            spill = overflow * 0.5
            sigma -= spill
            chi += spill
            deficit = np.maximum(fl * 0.8 - sigma, 0)
            drain = np.minimum(chi * 0.1, deficit)
            sigma += drain
            chi -= drain
            chi *= 0.999
            bruce_in = bruce_field * 0.05
            chi += bruce_in * 0.01
            bruce_field -= bruce_in
            bruce_field = np.maximum(bruce_field, 0)
            dissipated_this_step = float(np.sum(spill))

        elif mode == 'phase_projection':
            density = gaussian_blur(probe_hits, sigma_blur=3.0)
            d_max = float(np.max(density))
            if d_max > 0:
                density /= d_max
            grad_phi_x = (np.roll(phi, -1, 0) -
                          np.roll(phi, 1, 0))
            grad_phi_y = (np.roll(phi, -1, 1) -
                          np.roll(phi, 1, 1))
            grad_phi_sq = grad_phi_x**2 + grad_phi_y**2
            weight = np.power(density + 1e-10, 0.5)
            phi_dissip = kappa_phase * grad_phi_sq * weight
            phi -= phi_dissip
            bruce_proj = bruce_field * weight * 0.05
            bruce_field -= bruce_proj
            bruce_field = np.maximum(bruce_field, 0)
            dissipated_this_step = (float(np.sum(phi_dissip)) +
                                    float(np.sum(bruce_proj)))

        cumulative_dissipated += dissipated_this_step

        # ---- DIAGNOSTICS (all configs) ----
        bruce_e = float(np.sum(bruce_field**2))
        phi_e = float(np.sum(phi**2))

        gp_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
        gp_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
        xi = float(np.sum(phi**2 + gp_x**2 + gp_y**2))

        # Chi operator -- DIAGNOSTIC ONLY
        _, chi_mag, chi_max = compute_chi_operator(phi)

        # Track chi_c: first step where running growth
        # rate goes negative (chi tank only)
        if (mode == 'chi_tank' and chi_c_step is None
                and step > 200):
            window = ts_bruce_energy[-100:] if len(
                ts_bruce_energy) >= 100 else ts_bruce_energy
            if len(window) >= 50:
                t_fit = np.arange(len(window), dtype=float)
                slope = np.polyfit(t_fit, window, 1)[0]
                if slope < 0:
                    chi_c_step = step
                    chi_c_mag = chi_mag

        ts_bruce_energy.append(bruce_e)
        ts_phi_energy.append(phi_e)
        ts_xi_metric.append(xi)
        ts_chi_op_mag.append(chi_mag)
        ts_chi_op_max.append(chi_max)
        ts_dissipated.append(cumulative_dissipated)
        ts_sigma_total.append(float(np.sum(sigma)))

    return {
        "ts_bruce_energy": np.array(ts_bruce_energy),
        "ts_phi_energy": np.array(ts_phi_energy),
        "ts_dissipated": np.array(ts_dissipated),
        "ts_sigma_total": np.array(ts_sigma_total),
        "ts_xi_metric": np.array(ts_xi_metric),
        "ts_chi_op_mag": np.array(ts_chi_op_mag),
        "ts_chi_op_max": np.array(ts_chi_op_max),
        "final_bruce_rms": float(np.sqrt(
            np.mean(bruce_field**2))),
        "final_phi_rms": float(np.sqrt(np.mean(phi**2))),
        "final_sigma": float(np.sum(sigma)),
        "chi_c_step": chi_c_step,
        "chi_c_mag": chi_c_mag,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v19 Chi Operator Diagnostic")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v19 -- CHI OPERATOR DIAGNOSTIC")
    print(f"  Measure chi_op = div(phi*grad(Xi)) - Xi*lap(phi)")
    print(f"  on existing mechanisms. Find chi_c.")
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

    configs = [
        ("A: No dissipation", "none"),
        ("B: Chi tank (v17)", "chi_tank"),
        ("C: Phase projection (v18)", "phase_projection"),
    ]

    all_results = []

    for name, mode in configs:
        print(f"\n  {'─'*55}")
        print(f"  {name}")
        print(f"  {'─'*55}")

        result = run_config(
            nx, ny, args.steps, dt, D, alpha, separation,
            pump_A, ratio, lam, X, Y, mode=mode)

        n = len(result["ts_bruce_energy"])
        skip = 100
        early = late = rate = exp = 0
        if n > skip * 2:
            early = float(np.mean(
                result["ts_bruce_energy"][skip:skip + 100]))
            late = float(np.mean(
                result["ts_bruce_energy"][-100:]))
            steps_fit = np.arange(skip, n, dtype=float)
            rate = np.polyfit(
                steps_fit,
                result["ts_bruce_energy"][skip:], 1)[0]
            pm = (steps_fit > 0) & (
                result["ts_bruce_energy"][skip:] > 0)
            if np.sum(pm) > 2:
                exp = np.polyfit(
                    np.log(steps_fit[pm]),
                    np.log(result["ts_bruce_energy"][skip:][pm]),
                    1)[0]

        phi_early = phi_late = 0
        xi_early = xi_late = 0
        chi_op_early = chi_op_late = 0
        if n > skip * 2:
            phi_early = float(np.mean(
                result["ts_phi_energy"][skip:skip + 100]))
            phi_late = float(np.mean(
                result["ts_phi_energy"][-100:]))
            xi_early = float(np.mean(
                result["ts_xi_metric"][skip:skip + 100]))
            xi_late = float(np.mean(
                result["ts_xi_metric"][-100:]))
            chi_op_early = float(np.mean(
                result["ts_chi_op_mag"][skip:skip + 100]))
            chi_op_late = float(np.mean(
                result["ts_chi_op_mag"][-100:]))

        entry = {
            "name": name,
            "mode": mode,
            "bruce_early": round(early, 6),
            "bruce_late": round(late, 6),
            "growth_rate": round(rate, 8),
            "power_exp": round(exp, 4),
            "final_bruce_rms": round(
                result["final_bruce_rms"], 8),
            "final_phi_rms": round(
                result["final_phi_rms"], 8),
            "final_sigma": round(result["final_sigma"], 4),
            "phi_early": round(phi_early, 4),
            "phi_late": round(phi_late, 4),
            "xi_early": round(xi_early, 4),
            "xi_late": round(xi_late, 4),
            "chi_op_early": round(chi_op_early, 4),
            "chi_op_late": round(chi_op_late, 4),
            "total_dissipated": round(float(
                result["ts_dissipated"][-1]) if len(
                    result["ts_dissipated"]) > 0 else 0, 4),
            "chi_c_step": result["chi_c_step"],
            "chi_c_mag": (round(result["chi_c_mag"], 6)
                          if result["chi_c_mag"] is not None
                          else None),
        }
        all_results.append(entry)

        print(f"  Bruce early:      {entry['bruce_early']:.6f}")
        print(f"  Bruce late:       {entry['bruce_late']:.6f}")
        print(f"  Growth rate:      {entry['growth_rate']:.8f}")
        print(f"  Power exponent:   {entry['power_exp']:.4f}")
        print(f"  Bruce RMS:        {entry['final_bruce_rms']:.8f}")
        print(f"  Phi RMS:          {entry['final_phi_rms']:.8f}")
        print(f"  Xi early:         {entry['xi_early']:.4f}")
        print(f"  Xi late:          {entry['xi_late']:.4f}")
        if xi_early > 0:
            xi_chg = (xi_late / xi_early - 1) * 100
            print(f"  Xi change:        {xi_chg:+.1f}%")
        print(f"  Chi_op early:     {entry['chi_op_early']:.4f}")
        print(f"  Chi_op late:      {entry['chi_op_late']:.4f}")
        if chi_op_early > 0:
            cop_chg = (chi_op_late / chi_op_early - 1) * 100
            print(f"  Chi_op change:    {cop_chg:+.1f}%")
        print(f"  Total dissipated: {entry['total_dissipated']:.4f}")
        if entry["chi_c_step"] is not None:
            print(f"  *** chi_c found at step {entry['chi_c_step']}"
                  f"  mag={entry['chi_c_mag']:.6f} ***")

    # ---- COMPARISON TABLE ----
    print(f"\n{'='*65}")
    print(f"  CHI OPERATOR COMPARISON")
    print(f"{'='*65}")

    print(f"\n  {'Config':>28} {'Rate':>12} {'Xi_late':>10} "
          f"{'ChiOp_E':>10} {'ChiOp_L':>10}")
    print(f"  {'-'*28} {'-'*12} {'-'*10} {'-'*10} {'-'*10}")

    for r in all_results:
        print(f"  {r['name']:>28} {r['growth_rate']:>12.8f} "
              f"{r['xi_late']:>10.4f} "
              f"{r['chi_op_early']:>10.4f} "
              f"{r['chi_op_late']:>10.4f}")

    rate_a = all_results[0]["growth_rate"]
    rate_b = all_results[1]["growth_rate"]
    rate_c = all_results[2]["growth_rate"]

    red_b = (1 - rate_b / rate_a) * 100 if rate_a > 0 else 0
    red_c = (1 - rate_c / rate_a) * 100 if rate_a > 0 else 0

    print(f"\n  Rate reduction vs baseline (A):")
    print(f"    B: Chi tank (v17):         {red_b:.1f}%")
    print(f"    C: Phase projection (v18): {red_c:.1f}%")

    # ---- CHI_C ANALYSIS ----
    print(f"\n{'='*65}")
    print(f"  CHI_C THRESHOLD ANALYSIS")
    print(f"{'='*65}")

    b = all_results[1]
    if b["chi_c_step"] is not None:
        print(f"\n  Chi_c FOUND in chi tank run:")
        print(f"    Step:      {b['chi_c_step']}")
        print(f"    Chi_op:    {b['chi_c_mag']:.6f}")
        print(f"")
        print(f"  Interpretation: Brucetron growth crosses")
        print(f"  negative when chi operator magnitude")
        print(f"  reaches {b['chi_c_mag']:.6f}.")
        print(f"")
        print(f"  Below chi_c: mode persists (A, C)")
        print(f"  Above chi_c: mode collapses (B)")
    else:
        print(f"\n  Chi_c NOT found in chi tank run.")
        print(f"  Growth may already be negative from step 1")
        print(f"  or threshold crossed before tracking window.")

    print(f"\n  Chi operator magnitude comparison:")
    for r in all_results:
        print(f"    {r['name']:>28}: "
              f"early={r['chi_op_early']:.4f} "
              f"late={r['chi_op_late']:.4f}")

    a_cop = all_results[0]["chi_op_late"]
    b_cop = all_results[1]["chi_op_late"]
    if a_cop > 0:
        ratio_ba = b_cop / a_cop
        print(f"\n  Chi_op ratio (B/A late): {ratio_ba:.4f}")
        if ratio_ba < 0.5:
            print(f"  Chi tank SUPPRESSES operator (mode killed)")
        elif ratio_ba > 2.0:
            print(f"  Chi tank AMPLIFIES operator (active shear)")
        else:
            print(f"  Chi tank MODIFIES operator moderately")

    print(f"{'='*65}")

    # ---- SAVE JSON ----
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v19_chi_operator_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v19 Chi Operator Diagnostic",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Measure chi operator "
                     "div(phi*grad(Xi)) - Xi*lap(phi) "
                     "on existing mechanisms to find "
                     "chi_c threshold"),
        "grid": nx, "steps": args.steps,
        "chi_operator": ("div(phi * grad(Xi_local)) "
                         "- Xi_local * lap(phi)"),
        "xi_local_def": "phi^2 + |grad_phi|^2",
        "configs": all_results,
        "rate_reduction": {
            "chi_tank_vs_baseline": round(red_b, 2),
            "phase_projection_vs_baseline": round(red_c, 2),
        },
        "chi_c": {
            "step": b["chi_c_step"],
            "magnitude": b["chi_c_mag"],
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
