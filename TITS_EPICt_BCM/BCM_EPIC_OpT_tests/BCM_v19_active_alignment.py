# -*- coding: utf-8 -*-
"""
BCM v19.2 -- Active Chi Alignment Control
============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

v19 chi operator diagnostic revealed the INVERSION:
  - High |chi| (~0.05-0.09): mode PERSISTS
  - chi forced to ~0 (0.0007): mode COLLAPSES

The Brucetron is sustained by non-commutativity between
phi (observable phase) and Xi_local (latent 6D structure).
When chi -> 0, phi and Xi become locally commutative.
The shear that sustains the phase defect vanishes.

Burdick Chi-Coherence Collapse Law:
    |chi| >> chi_c  =>  mode persists (non-commutative)
    |chi| <  chi_c  =>  mode collapses (commutative)

    chi = div(phi * grad(Xi)) - Xi * lap(phi)
    chi_c ~ 0.002582 (measured v19, grid=256)

THIS TEST: Force chi toward zero WITHOUT the chi tank.
Direct active alignment -- pull phi toward Xi, push Xi
toward phi. If the mode collapses at similar chi_c
without massive dissipation: we have a GOVERNING LAW,
not just a passive sink.

If the mode re-locks: the chi tank has a hidden
dependency. Also a discovery.

FOUR CONFIGS:
    A: No dissipation (baseline)
    B: Chi tank (v17 reference)
    C: Active alignment eta=0.01
    D: Active alignment eta=0.05

Usage:
    python BCM_v19_active_alignment.py
    python BCM_v19_active_alignment.py --steps 5000 --grid 256
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
    Returns: chi_op field, magnitude, peak
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
               mode, kappa_phase=0.002, eta=0.01,
               rng_seed=42):
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

        elif mode == 'active_alignment':
            # ACTIVE CHI ALIGNMENT CONTROL
            # Force chi operator toward zero by pulling
            # phi toward Xi and pushing Xi toward phi.
            # NO chi tank. NO passive sink. Direct drive.
            chi_op, _, _ = compute_chi_operator(phi)

            # Pull phi toward commutation with Xi
            phi -= eta * chi_op

            # Track what was removed (diagnostic)
            dissipated_this_step = float(
                eta * np.sum(np.abs(chi_op)))

        cumulative_dissipated += dissipated_this_step

        # ---- DIAGNOSTICS (all configs) ----
        bruce_e = float(np.sum(bruce_field**2))
        phi_e = float(np.sum(phi**2))

        gp_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
        gp_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
        xi = float(np.sum(phi**2 + gp_x**2 + gp_y**2))

        _, chi_mag, _ = compute_chi_operator(phi)

        # Track chi_c for active alignment configs
        if (mode == 'active_alignment' and chi_c_step is None
                and step > 200):
            window = ts_bruce_energy[-100:] if len(
                ts_bruce_energy) >= 100 else ts_bruce_energy
            if len(window) >= 50:
                t_fit = np.arange(len(window), dtype=float)
                slope = np.polyfit(t_fit, window, 1)[0]
                if slope < 0:
                    chi_c_step = step
                    chi_c_mag = chi_mag

        # Also track for chi tank
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
        ts_dissipated.append(cumulative_dissipated)
        ts_sigma_total.append(float(np.sum(sigma)))

    return {
        "ts_bruce_energy": np.array(ts_bruce_energy),
        "ts_phi_energy": np.array(ts_phi_energy),
        "ts_dissipated": np.array(ts_dissipated),
        "ts_sigma_total": np.array(ts_sigma_total),
        "ts_xi_metric": np.array(ts_xi_metric),
        "ts_chi_op_mag": np.array(ts_chi_op_mag),
        "final_bruce_rms": float(np.sqrt(
            np.mean(bruce_field**2))),
        "final_phi_rms": float(np.sqrt(np.mean(phi**2))),
        "final_sigma": float(np.sum(sigma)),
        "chi_c_step": chi_c_step,
        "chi_c_mag": chi_c_mag,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v19.2 Active Chi Alignment")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v19.2 -- ACTIVE CHI ALIGNMENT CONTROL")
    print(f"  Force chi -> 0 without chi tank.")
    print(f"  Does the mode collapse under direct commutation?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"")
    print(f"  Burdick Chi-Coherence Collapse Law:")
    print(f"    |chi| >> chi_c  =>  mode persists")
    print(f"    |chi| <  chi_c  =>  mode collapses")
    print(f"    chi_c ~ 0.002582 (v19 measurement)")

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
        ("A: No dissipation", "none", 0.0),
        ("B: Chi tank (v17)", "chi_tank", 0.0),
        ("C: Active align eta=0.01", "active_alignment", 0.01),
        ("D: Active align eta=0.05", "active_alignment", 0.05),
    ]

    all_results = []

    for name, mode, eta_val in configs:
        print(f"\n  {'─'*55}")
        print(f"  {name}")
        print(f"  {'─'*55}")

        result = run_config(
            nx, ny, args.steps, dt, D, alpha, separation,
            pump_A, ratio, lam, X, Y, mode=mode,
            eta=eta_val)

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
            "eta": eta_val,
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
            "chi_op_early": round(chi_op_early, 6),
            "chi_op_late": round(chi_op_late, 6),
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
        print(f"  Bruce RMS:        {entry['final_bruce_rms']:.8f}")
        print(f"  Phi RMS:          {entry['final_phi_rms']:.8f}")
        print(f"  Xi early:         {entry['xi_early']:.4f}")
        print(f"  Xi late:          {entry['xi_late']:.4f}")
        if xi_early > 0:
            xi_chg = (xi_late / xi_early - 1) * 100
            print(f"  Xi change:        {xi_chg:+.1f}%")
        print(f"  Chi_op early:     {entry['chi_op_early']:.6f}")
        print(f"  Chi_op late:      {entry['chi_op_late']:.6f}")
        if chi_op_early > 0:
            cop_chg = (chi_op_late / chi_op_early - 1) * 100
            print(f"  Chi_op change:    {cop_chg:+.1f}%")
        print(f"  Total dissipated: {entry['total_dissipated']:.4f}")
        if entry["chi_c_step"] is not None:
            print(f"  *** chi_c at step {entry['chi_c_step']}"
                  f"  mag={entry['chi_c_mag']:.6f} ***")

    # ---- COMPARISON TABLE ----
    print(f"\n{'='*65}")
    print(f"  ACTIVE ALIGNMENT COMPARISON")
    print(f"{'='*65}")

    print(f"\n  {'Config':>30} {'Rate':>12} {'Xi_late':>10} "
          f"{'ChiOp_L':>10} {'Dissip':>10}")
    print(f"  {'-'*30} {'-'*12} {'-'*10} {'-'*10} {'-'*10}")

    for r in all_results:
        print(f"  {r['name']:>30} {r['growth_rate']:>12.8f} "
              f"{r['xi_late']:>10.4f} "
              f"{r['chi_op_late']:>10.6f} "
              f"{r['total_dissipated']:>10.2f}")

    rate_a = all_results[0]["growth_rate"]

    print(f"\n  Rate reduction vs baseline (A):")
    for r in all_results[1:]:
        if rate_a > 0:
            red = (1 - r["growth_rate"] / rate_a) * 100
        else:
            red = 0
        print(f"    {r['name']:>30}: {red:.1f}%")

    # ---- VERDICT ----
    print(f"\n{'='*65}")
    print(f"  ACTIVE ALIGNMENT VERDICT")
    print(f"{'='*65}")

    # Compare active alignment to chi tank
    rate_b = all_results[1]["growth_rate"]
    rate_c = all_results[2]["growth_rate"]
    rate_d = all_results[3]["growth_rate"]

    chi_b = all_results[1]["chi_op_late"]
    chi_c = all_results[2]["chi_op_late"]
    chi_d = all_results[3]["chi_op_late"]

    # Did active alignment achieve negative growth?
    active_negative = rate_c < 0 or rate_d < 0

    # Did active alignment drive chi toward zero?
    chi_a = all_results[0]["chi_op_late"]
    active_drove_chi = (chi_c < chi_a * 0.5 or
                        chi_d < chi_a * 0.5)

    if active_negative and active_drove_chi:
        print(f"\n  ACTIVE ALIGNMENT COLLAPSES THE MODE")
        print(f"  chi driven toward zero WITHOUT chi tank.")
        print(f"  The Chi-Coherence Collapse Law is a")
        print(f"  GOVERNING LAW, not a passive artifact.")
        verdict = "GOVERNING_LAW"
    elif active_drove_chi and not active_negative:
        print(f"\n  CHI DRIVEN DOWN BUT MODE PERSISTS")
        print(f"  Active alignment reduces chi but the")
        print(f"  mode re-locks. Chi tank has hidden")
        print(f"  dependency beyond commutation alone.")
        verdict = "HIDDEN_DEPENDENCY"
    elif active_negative and not active_drove_chi:
        print(f"\n  MODE COLLAPSED BUT CHI NOT DRIVEN DOWN")
        print(f"  Active alignment kills mode through a")
        print(f"  different mechanism than commutation.")
        verdict = "DIFFERENT_MECHANISM"
    else:
        print(f"\n  ACTIVE ALIGNMENT INEFFECTIVE")
        print(f"  Neither chi reduction nor mode collapse.")
        print(f"  Chi tank mechanism is unique.")
        verdict = "UNIQUE_MECHANISM"

    # Chi_c comparison
    print(f"\n  Chi_c comparison:")
    for r in all_results:
        if r["chi_c_step"] is not None:
            print(f"    {r['name']:>30}: step "
                  f"{r['chi_c_step']} "
                  f"chi_op={r['chi_c_mag']:.6f}")
        else:
            print(f"    {r['name']:>30}: not reached")

    print(f"\n  Dissipation comparison:")
    print(f"    Chi tank total:       "
          f"{all_results[1]['total_dissipated']:.2f}")
    print(f"    Active eta=0.01:      "
          f"{all_results[2]['total_dissipated']:.2f}")
    print(f"    Active eta=0.05:      "
          f"{all_results[3]['total_dissipated']:.2f}")
    if all_results[1]["total_dissipated"] > 0:
        for r in all_results[2:]:
            frac = (r["total_dissipated"] /
                    all_results[1]["total_dissipated"] * 100)
            print(f"    {r['name']:>30}: "
                  f"{frac:.1f}% of chi tank")

    print(f"{'='*65}")

    # ---- SAVE JSON ----
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v19_active_alignment_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v19.2 Active Chi Alignment Control",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Force chi operator toward zero "
                     "without chi tank. Test if "
                     "commutation alone collapses "
                     "the Brucetron mode."),
        "chi_coherence_law": (
            "|chi| >> chi_c => mode persists; "
            "|chi| < chi_c => mode collapses"),
        "chi_c_reference": 0.002582,
        "grid": nx, "steps": args.steps,
        "configs": all_results,
        "verdict": verdict,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
