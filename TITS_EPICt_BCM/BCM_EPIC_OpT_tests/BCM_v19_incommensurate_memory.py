# -*- coding: utf-8 -*-
"""
BCM v19 -- Incommensurate Memory (Temporal Attack A)
=====================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

ChatGPT v19 directive: "Stop modifying space. Start
breaking time."

v18 proved the Brucetron is phase-rigid under ALL spatial
operators. The mode locks to the 50-step cycle (f=0.020).
The integer harmonic ladder (f/2, f, 2f, ..., H10=pump)
creates a resonant lattice that resists spatial perturbation.

THIS TEST: Break the integer ratio by making the memory
coefficient oscillate at a frequency incommensurate with
the probe cycle. The golden ratio phi = (1+sqrt(5))/2
is the most irrational number -- maximally distant from
all rationals. If the eigenmode requires commensurate
feedback to maintain global synchrony, this kills it.

Implementation:
    alpha_t = alpha * (1 + epsilon * cos(2*pi*t*golden))

The memory strength now varies on a schedule that NEVER
repeats relative to the 50-step probe cycle. The lattice
cannot re-lock because the feedback gain is permanently
non-repeating.

WARNING (v17): The f/2 heartbeat and fundamental are
coupled eigenmodes. The goal is NOT to eliminate the mode.
The goal is to make the mode STABLE instead of GROWING.
Preserve the heartbeat. Break the GROWTH of phase debt.

FOUR CONFIGS:
    A: No dissipation (baseline -- reference)
    B: Chi tank (v17 method -- reference)
    C: Phase projection (v18 method -- 91.6% reference)
    D: Incommensurate memory (v19 temporal attack)

Usage:
    python BCM_v19_incommensurate_memory.py
    python BCM_v19_incommensurate_memory.py --steps 3000 --grid 256
    python BCM_v19_incommensurate_memory.py --epsilon 0.05
"""

import numpy as np
import json
import os
import time
import math
import argparse


GOLDEN = (1.0 + math.sqrt(5.0)) / 2.0  # 1.6180339887...


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
    """Simple separable Gaussian blur."""
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
               mode, kappa_phase=0.002, epsilon=0.05,
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
    ts_alpha_effective = []
    ts_xi_metric = []
    cumulative_dissipated = 0.0

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

        # ---- MEMORY TERM ----
        # In modes 'none', 'chi_tank', 'phase_projection':
        #     alpha is constant (standard v18 behavior)
        # In mode 'incommensurate_memory':
        #     alpha oscillates at golden ratio frequency
        #     relative to the 50-step probe cycle
        if mode == 'incommensurate_memory':
            # Golden ratio modulation: frequency is
            # permanently incommensurate with probe f=0.020
            # and all its harmonics
            alpha_t = alpha * (1.0 + epsilon * math.cos(
                2.0 * math.pi * step * GOLDEN))
            # Clamp to stable range [0.70, 0.85]
            # (blowup at 0.90 per v14)
            alpha_t = max(0.70, min(0.85, alpha_t))
            ts_alpha_effective.append(round(alpha_t, 6))
        else:
            alpha_t = alpha

        if alpha_t > 0:
            sn += alpha_t * (sigma - sigma_prev)
        sn = np.maximum(sn, 0)
        if float(np.max(sn)) > 1e10:
            break

        # Phase field: accumulated phase error
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
            grad_phi_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
            grad_phi_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
            grad_phi_sq = grad_phi_x**2 + grad_phi_y**2
            weight = np.power(density + 1e-10, 0.5)
            phi_dissip = kappa_phase * grad_phi_sq * weight
            phi -= phi_dissip
            bruce_proj = bruce_field * weight * 0.05
            bruce_field -= bruce_proj
            bruce_field = np.maximum(bruce_field, 0)
            dissipated_this_step = (float(np.sum(phi_dissip)) +
                                    float(np.sum(bruce_proj)))

        # Incommensurate memory has NO explicit dissipation
        # mechanism -- the attack is purely temporal. If the
        # growth rate changes, it's because the harmonic lock
        # is broken, not because energy was removed.

        cumulative_dissipated += dissipated_this_step
        bruce_e = float(np.sum(bruce_field**2))
        phi_e = float(np.sum(phi**2))

        # Xi_6D METRIC: total field-shape volume
        # Xi = phi^2 + |grad_phi|^2
        # Tracks structural contraction of the 6D field
        # shape, not just energy dissipation.
        # If Xi decreases: the field shape contracts
        # (harmonic lattice losing volume).
        # If Xi stays constant while energy drops:
        # starving the mode, not killing the topology.
        gp_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
        gp_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
        xi = float(np.sum(phi**2 + gp_x**2 + gp_y**2))

        ts_bruce_energy.append(bruce_e)
        ts_phi_energy.append(phi_e)
        ts_xi_metric.append(xi)
        ts_dissipated.append(cumulative_dissipated)
        ts_sigma_total.append(float(np.sum(sigma)))

    return {
        "ts_bruce_energy": np.array(ts_bruce_energy),
        "ts_phi_energy": np.array(ts_phi_energy),
        "ts_dissipated": np.array(ts_dissipated),
        "ts_sigma_total": np.array(ts_sigma_total),
        "ts_alpha_effective": ts_alpha_effective,
        "ts_xi_metric": np.array(ts_xi_metric),
        "final_bruce_rms": float(np.sqrt(
            np.mean(bruce_field**2))),
        "final_phi_rms": float(np.sqrt(np.mean(phi**2))),
        "final_sigma": float(np.sum(sigma)),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v19 Incommensurate Memory")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    parser.add_argument("--epsilon", type=float, default=0.05,
                        help="Modulation depth for golden "
                             "ratio detuning (default 0.05)")
    args = parser.parse_args()
    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v19 -- INCOMMENSURATE MEMORY (TEMPORAL ATTACK A)")
    print(f"  'Stop modifying space. Start breaking time.'")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"  Epsilon: {args.epsilon}")
    print(f"  Golden ratio: {GOLDEN:.10f}")
    print(f"  Alpha base: 0.80  Range: [0.70, 0.85]")

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
        ("D: Incommensurate memory", "incommensurate_memory"),
    ]

    all_results = []

    for name, mode in configs:
        print(f"\n  {'─'*55}")
        print(f"  {name}")
        print(f"  {'─'*55}")

        result = run_config(
            nx, ny, args.steps, dt, D, alpha, separation,
            pump_A, ratio, lam, X, Y, mode=mode,
            epsilon=args.epsilon)

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
        if n > skip * 2:
            phi_early = float(np.mean(
                result["ts_phi_energy"][skip:skip + 100]))
            phi_late = float(np.mean(
                result["ts_phi_energy"][-100:]))
            xi_early = float(np.mean(
                result["ts_xi_metric"][skip:skip + 100]))
            xi_late = float(np.mean(
                result["ts_xi_metric"][-100:]))

        # Alpha statistics for incommensurate mode
        alpha_stats = {}
        if len(result["ts_alpha_effective"]) > 0:
            ae = result["ts_alpha_effective"]
            alpha_stats = {
                "alpha_min": min(ae),
                "alpha_max": max(ae),
                "alpha_mean": round(sum(ae) / len(ae), 6),
                "alpha_std": round(float(np.std(ae)), 6),
            }

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
            "total_dissipated": round(float(
                result["ts_dissipated"][-1]) if len(
                    result["ts_dissipated"]) > 0 else 0, 4),
        }
        if alpha_stats:
            entry["alpha_stats"] = alpha_stats
        all_results.append(entry)

        print(f"  Bruce early:      {entry['bruce_early']:.6f}")
        print(f"  Bruce late:       {entry['bruce_late']:.6f}")
        print(f"  Growth rate:      {entry['growth_rate']:.8f}")
        print(f"  Power exponent:   {entry['power_exp']:.4f}")
        print(f"  Bruce RMS:        {entry['final_bruce_rms']:.8f}")
        print(f"  Phi RMS:          {entry['final_phi_rms']:.8f}")
        print(f"  Phi early:        {entry['phi_early']:.4f}")
        print(f"  Phi late:         {entry['phi_late']:.4f}")
        print(f"  Xi early:         {entry['xi_early']:.4f}")
        print(f"  Xi late:          {entry['xi_late']:.4f}")
        if xi_early > 0:
            xi_change = (xi_late / xi_early - 1) * 100
            print(f"  Xi change:        {xi_change:+.1f}%")
        print(f"  Total dissipated: {entry['total_dissipated']:.4f}")
        if alpha_stats:
            print(f"  Alpha range:      [{alpha_stats['alpha_min']}"
                  f" - {alpha_stats['alpha_max']}]")
            print(f"  Alpha mean:       {alpha_stats['alpha_mean']}")

    # ---- COMPARISON TABLE ----
    print(f"\n{'='*65}")
    print(f"  v19 TEMPORAL ATTACK COMPARISON")
    print(f"{'='*65}")

    print(f"\n  {'Config':>32} {'Rate':>12} {'Late E':>10} "
          f"{'PhiRMS':>10} {'Xi_late':>12}")
    print(f"  {'-'*32} {'-'*12} {'-'*10} {'-'*10} {'-'*12}")

    for r in all_results:
        print(f"  {r['name']:>32} {r['growth_rate']:>12.8f} "
              f"{r['bruce_late']:>10.4f} "
              f"{r['final_phi_rms']:>10.6f} "
              f"{r['xi_late']:>12.2f}")

    rate_a = all_results[0]["growth_rate"]
    rate_b = all_results[1]["growth_rate"]
    rate_c = all_results[2]["growth_rate"]
    rate_d = all_results[3]["growth_rate"]

    red_b = (1 - rate_b / rate_a) * 100 if rate_a > 0 else 0
    red_c = (1 - rate_c / rate_a) * 100 if rate_a > 0 else 0
    red_d = (1 - rate_d / rate_a) * 100 if rate_a > 0 else 0

    print(f"\n  Rate reduction vs baseline (A):")
    print(f"    B: Chi tank (v17):           {red_b:.1f}%")
    print(f"    C: Phase projection (v18):   {red_c:.1f}%")
    print(f"    D: Incommensurate memory:    {red_d:.1f}%")

    # ---- VERDICT ----
    print(f"\n{'='*65}")
    print(f"  TEMPORAL ATTACK VERDICT")
    print(f"{'='*65}")

    if rate_d < 0:
        print(f"\n  TEMPORAL ATTACK ACHIEVES NEGATIVE GROWTH")
        print(f"  The harmonic lock is BROKEN.")
        print(f"  Incommensurate memory destroys eigenmode.")
        verdict = "NEGATIVE_GROWTH"
    elif red_d > 50:
        print(f"\n  TEMPORAL ATTACK SIGNIFICANT ({red_d:.1f}%)")
        print(f"  The harmonic lock is WEAKENED.")
        print(f"  Golden ratio detuning disrupts phase sync.")
        verdict = "SIGNIFICANT"
    elif red_d > 10:
        print(f"\n  TEMPORAL ATTACK PARTIAL ({red_d:.1f}%)")
        print(f"  Some decorrelation but mode persists.")
        verdict = "PARTIAL"
    elif red_d > -10:
        print(f"\n  TEMPORAL ATTACK INEFFECTIVE ({red_d:.1f}%)")
        print(f"  The Brucetron is phase-rigid in TIME as well.")
        print(f"  The mode is a true invariant of the system.")
        verdict = "INVARIANT"
    else:
        print(f"\n  TEMPORAL ATTACK DESTABILIZING ({red_d:.1f}%)")
        print(f"  Incommensurate memory INCREASES growth.")
        print(f"  The detuning feeds the mode instead of")
        print(f"  breaking it.")
        verdict = "DESTABILIZING"

    best = min(all_results, key=lambda r: r["growth_rate"])
    print(f"\n  Best config: {best['name']}")
    print(f"  Best rate:   {best['growth_rate']:.8f}")

    # Heartbeat check: did f/2 survive?
    print(f"\n  Heartbeat (f/2) preservation:")
    print(f"    Baseline phi RMS:  "
          f"{all_results[0]['final_phi_rms']:.6f}")
    print(f"    Temporal phi RMS:  "
          f"{all_results[3]['final_phi_rms']:.6f}")
    phi_ratio = (all_results[3]["final_phi_rms"] /
                 all_results[0]["final_phi_rms"]
                 if all_results[0]["final_phi_rms"] > 0
                 else 0)
    print(f"    Ratio (D/A):       {phi_ratio:.4f}")
    if 0.5 < phi_ratio < 2.0:
        print(f"    Heartbeat: PRESERVED")
        hb_status = "PRESERVED"
    elif phi_ratio <= 0.5:
        print(f"    Heartbeat: SUPPRESSED (may have killed f/2)")
        hb_status = "SUPPRESSED"
    else:
        print(f"    Heartbeat: AMPLIFIED (detuning fed mode)")
        hb_status = "AMPLIFIED"

    print(f"{'='*65}")

    # 6D Field Shape Contraction analysis
    print(f"\n  6D FIELD SHAPE (Xi_6D):")
    xi_a_early = all_results[0]["xi_early"]
    xi_a_late = all_results[0]["xi_late"]
    xi_d_early = all_results[3]["xi_early"]
    xi_d_late = all_results[3]["xi_late"]
    print(f"    Baseline (A): {xi_a_early:.2f} -> {xi_a_late:.2f}")
    print(f"    Temporal (D): {xi_d_early:.2f} -> {xi_d_late:.2f}")
    if xi_a_late > 0:
        xi_ratio = xi_d_late / xi_a_late
        print(f"    Ratio D/A (late): {xi_ratio:.4f}")
        if xi_ratio < 0.9:
            print(f"    6D FIELD CONTRACTED — topology lost volume")
            xi_verdict = "CONTRACTED"
        elif xi_ratio > 1.1:
            print(f"    6D FIELD EXPANDED — detuning inflated shape")
            xi_verdict = "EXPANDED"
        else:
            print(f"    6D FIELD UNCHANGED — starved, not killed")
            xi_verdict = "UNCHANGED"
    else:
        xi_verdict = "NO_DATA"
    print(f"{'='*65}")
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v19_incommensurate_memory_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v19 Incommensurate Memory "
                 "(Temporal Attack A)",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Break Brucetron harmonic lock by "
                     "modulating alpha at golden ratio "
                     "frequency -- incommensurate with "
                     "50-step probe cycle"),
        "grid": nx, "steps": args.steps,
        "epsilon": args.epsilon,
        "golden_ratio": round(GOLDEN, 10),
        "alpha_base": 0.80,
        "alpha_clamp": [0.70, 0.85],
        "configs": all_results,
        "rate_reduction": {
            "chi_tank_vs_baseline": round(red_b, 2),
            "phase_projection_vs_baseline": round(red_c, 2),
            "incommensurate_vs_baseline": round(red_d, 2),
        },
        "verdict": verdict,
        "heartbeat_status": hb_status,
        "xi_6d_verdict": xi_verdict,
        "chatgpt_directive": "Stop modifying space. "
                             "Start breaking time.",
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
