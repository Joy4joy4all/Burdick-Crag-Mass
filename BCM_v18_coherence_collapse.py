# -*- coding: utf-8 -*-
"""
BCM v18.2 -- Coherence Collapse (Mode Destruction)
=====================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

"You're shaving peaks, not collapsing the mode."
-- ChatGPT adversarial review

v18 phase projection achieved 91.6% Brucetron growth
reduction BUT phi RMS was unchanged (0.00662). The energy
was drained but the mode structure persisted. The ghost
regenerates because phi remains coherent.

FIX: Two-term dissipation at the fractal boundary.
  k1 * (grad_phi^2 * weight)  -> magnitude drain (v18)
  k2 * (phi * weight)         -> coherence collapse (NEW)

The first removes energy. The second decorrelates the
phase field at the probe-written fractal boundary,
destroying the eigenmode that regenerates Brucetron.

FOUR RUNS:
  A: No dissipation (baseline)
  B: Chi tank (v17)
  C: Phase projection only (v18 - k1 only)
  D: Coherence collapse (v18.2 - k1 + k2)

Kill condition: if phi RMS drops in Run D vs Run C,
mode destruction is working.

Usage:
    python BCM_v18_coherence_collapse.py
    python BCM_v18_coherence_collapse.py --steps 3000 --grid 256
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


class CollapseProbe:
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
               mode, k1=0.002, k2=0.005, rng_seed=42):
    rng = np.random.RandomState(rng_seed)
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    chi = np.zeros((nx, ny))
    phi = np.zeros((nx, ny))
    probe_hits = np.zeros((nx, ny))
    probes = [CollapseProbe(i + 1, i * 5) for i in range(12)]
    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95
    ts_bruce_energy = []
    ts_phi_rms = []
    ts_sigma_total = []
    ts_dissipated = []
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

        elif mode == 'projection_only':
            density = gaussian_blur(probe_hits, sigma_blur=3.0)
            d_max = float(np.max(density))
            if d_max > 0:
                density /= d_max
            grad_phi_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
            grad_phi_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
            grad_phi_sq = grad_phi_x**2 + grad_phi_y**2
            weight = np.power(density + 1e-10, 0.5)
            phi_dissip = k1 * grad_phi_sq * weight
            phi -= phi_dissip
            bruce_proj = bruce_field * weight * 0.05
            bruce_field -= bruce_proj
            bruce_field = np.maximum(bruce_field, 0)
            dissipated_this_step = (float(np.sum(phi_dissip)) +
                                    float(np.sum(bruce_proj)))

        elif mode == 'coherence_collapse':
            density = gaussian_blur(probe_hits, sigma_blur=3.0)
            d_max = float(np.max(density))
            if d_max > 0:
                density /= d_max
            grad_phi_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
            grad_phi_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
            grad_phi_sq = grad_phi_x**2 + grad_phi_y**2
            weight = np.power(density + 1e-10, 0.5)
            # TERM 1: magnitude drain (existing)
            drain_term = k1 * grad_phi_sq * weight
            # TERM 2: coherence collapse (NEW)
            collapse_term = k2 * phi * weight
            # Apply both
            phi -= (drain_term + collapse_term)
            # Brucetron through same projection
            bruce_proj = bruce_field * weight * 0.05
            bruce_field -= bruce_proj
            bruce_field = np.maximum(bruce_field, 0)
            dissipated_this_step = (float(np.sum(drain_term)) +
                                    float(np.sum(collapse_term)) +
                                    float(np.sum(bruce_proj)))

        cumulative_dissipated += dissipated_this_step
        bruce_e = float(np.sum(bruce_field**2))
        phi_rms = float(np.sqrt(np.mean(phi**2)))
        ts_bruce_energy.append(bruce_e)
        ts_phi_rms.append(phi_rms)
        ts_sigma_total.append(float(np.sum(sigma)))
        ts_dissipated.append(cumulative_dissipated)

    return {
        "ts_bruce_energy": np.array(ts_bruce_energy),
        "ts_phi_rms": np.array(ts_phi_rms),
        "ts_sigma_total": np.array(ts_sigma_total),
        "ts_dissipated": np.array(ts_dissipated),
        "final_bruce_rms": float(np.sqrt(
            np.mean(bruce_field**2))),
        "final_phi_rms": float(np.sqrt(np.mean(phi**2))),
        "final_sigma": float(np.sum(sigma)),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v18.2 Coherence Collapse")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v18.2 -- COHERENCE COLLAPSE")
    print(f"  Shave peaks AND destroy the mode")
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
        ("C: Projection only (v18)", "projection_only"),
        ("D: Coherence collapse (v18.2)", "coherence_collapse"),
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
        phi_early = phi_late = 0
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
            phi_early = float(np.mean(
                result["ts_phi_rms"][skip:skip + 100]))
            phi_late = float(np.mean(
                result["ts_phi_rms"][-100:]))

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
            "phi_early": round(phi_early, 6),
            "phi_late": round(phi_late, 6),
            "final_sigma": round(result["final_sigma"], 4),
            "total_dissipated": round(float(
                result["ts_dissipated"][-1]) if len(
                    result["ts_dissipated"]) > 0 else 0, 4),
        }
        all_results.append(entry)

        print(f"  Bruce early:      {entry['bruce_early']:.6f}")
        print(f"  Bruce late:       {entry['bruce_late']:.6f}")
        print(f"  Growth rate:      {entry['growth_rate']:.8f}")
        print(f"  Phi RMS early:    {entry['phi_early']:.6f}")
        print(f"  Phi RMS late:     {entry['phi_late']:.6f}")
        print(f"  Final phi RMS:    {entry['final_phi_rms']:.8f}")
        print(f"  Total dissipated: {entry['total_dissipated']:.4f}")

    print(f"\n{'='*65}")
    print(f"  COHERENCE COLLAPSE COMPARISON")
    print(f"{'='*65}")

    print(f"\n  {'Config':>30} {'Rate':>12} {'PhiRMS':>10} "
          f"{'Dissip':>10}")
    print(f"  {'-'*30} {'-'*12} {'-'*10} {'-'*10}")

    for r in all_results:
        print(f"  {r['name']:>30} {r['growth_rate']:>12.8f} "
              f"{r['final_phi_rms']:>10.6f} "
              f"{r['total_dissipated']:>10.2f}")

    rate_a = all_results[0]["growth_rate"]
    rate_b = all_results[1]["growth_rate"]
    rate_c = all_results[2]["growth_rate"]
    rate_d = all_results[3]["growth_rate"]

    red_b = (1 - rate_b / rate_a) * 100 if rate_a > 0 else 0
    red_c = (1 - rate_c / rate_a) * 100 if rate_a > 0 else 0
    red_d = (1 - rate_d / rate_a) * 100 if rate_a > 0 else 0

    phi_a = all_results[0]["final_phi_rms"]
    phi_c = all_results[2]["final_phi_rms"]
    phi_d = all_results[3]["final_phi_rms"]

    print(f"\n  Rate reduction vs baseline:")
    print(f"    B (chi tank):           {red_b:.1f}%")
    print(f"    C (projection only):    {red_c:.1f}%")
    print(f"    D (coherence collapse): {red_d:.1f}%")

    print(f"\n  Phi RMS comparison:")
    print(f"    A (baseline):           {phi_a:.6f}")
    print(f"    C (projection only):    {phi_c:.6f}")
    print(f"    D (coherence collapse): {phi_d:.6f}")

    if phi_d < phi_c * 0.9:
        phi_drop = (1 - phi_d / phi_c) * 100
        print(f"    MODE DESTRUCTION: {phi_drop:.1f}% phi drop")
    elif phi_d < phi_c:
        print(f"    Partial mode reduction")
    else:
        print(f"    Phi RMS unchanged — mode persists")

    print(f"\n{'='*65}")
    print(f"  COHERENCE COLLAPSE VERDICT")
    print(f"{'='*65}")

    if rate_d < rate_c and phi_d < phi_c * 0.9:
        if rate_d < 0:
            print(f"\n  FULL CLOSURE: negative growth + mode collapse")
            print(f"  The Frastrate is a causal eraser.")
        else:
            print(f"\n  MODE DESTRUCTION CONFIRMED")
            print(f"  Phase coherence reduced at fractal boundary.")
            print(f"  Ghost eigenmode destabilized.")
    elif rate_d < rate_c:
        print(f"\n  IMPROVED RATE but mode persists")
        print(f"  k2 may need tuning.")
    else:
        print(f"\n  COHERENCE COLLAPSE INEFFECTIVE")

    best = min(all_results, key=lambda r: r["growth_rate"])
    print(f"\n  Best: {best['name']}")
    print(f"  Rate: {best['growth_rate']:.8f}")
    print(f"  Phi:  {best['final_phi_rms']:.8f}")
    print(f"{'='*65}")

    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v18_coherence_collapse_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v18.2 Coherence Collapse",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Dual-term dissipation: magnitude drain "
                     "plus phase coherence collapse at fractal "
                     "boundary"),
        "grid": nx, "steps": args.steps,
        "configs": all_results,
        "rate_reduction": {
            "chi_tank": round(red_b, 2),
            "projection_only": round(red_c, 2),
            "coherence_collapse": round(red_d, 2),
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
