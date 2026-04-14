# -*- coding: utf-8 -*-
"""
BCM v18 -- Sensory Flux Dissipation
======================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Sensory flux (Gemini formulation):
  Psi = (D_f - 1) * ln(grad_sigma^2)

Dissipation requires BOTH fractal depth AND sigma
gradient at the same location. Neither alone works.

THREE RUNS:
  A: No dissipation (baseline)
  B: Chi tank (v17 method)
  C: Sensory flux dissipation (Psi-weighted)

Usage:
    python BCM_v18_sensory_flux.py
    python BCM_v18_sensory_flux.py --steps 3000 --grid 256
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


def compute_local_df(activation_map):
    """
    Local fractal dimension proxy at each pixel.
    D_f_local = 1 + (vacancy / 4) where vacancy is
    number of unactivated neighbors. Interior=1.0,
    isolated frontier=2.0, smooth edge=1.25.
    """
    occ = (activation_map > 0).astype(float)
    su = np.roll(occ, 1, axis=0)
    sd = np.roll(occ, -1, axis=0)
    sl = np.roll(occ, 1, axis=1)
    sr = np.roll(occ, -1, axis=1)
    neighbor_count = su + sd + sl + sr
    vacancy = 4.0 - neighbor_count
    # D_f_local: 1.0 for interior, up to 2.0 for isolated
    d_f_local = 1.0 + vacancy / 4.0
    # Only at activated pixels
    d_f_local *= occ
    return d_f_local


def compute_sensory_flux(sigma, activation_map):
    """
    Psi = (D_f_local - 1) * ln(grad_sigma^2 + eps)
    Positive where both fractal depth and gradient exist.
    """
    d_f_local = compute_local_df(activation_map)
    grad_x = np.roll(sigma, -1, 0) - np.roll(sigma, 1, 0)
    grad_y = np.roll(sigma, -1, 1) - np.roll(sigma, 1, 1)
    grad_sq = grad_x**2 + grad_y**2
    # ln of grad^2, clamped to avoid log(0)
    ln_grad = np.log(np.maximum(grad_sq, 1e-20))
    # Psi: positive only where both terms contribute
    psi = (d_f_local - 1.0) * np.maximum(ln_grad, 0)
    return np.maximum(psi, 0)


class FluxProbe:
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
               activation_map):
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
            self._deposit(sigma, pb, nx, ny, activation_map)
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
            self._scoop(sigma, nx, ny, activation_map)
            ix = int(np.clip(self.pos[0], 0, nx - 1))
            iy = int(np.clip(self.pos[1], 0, ny - 1))
            activation_map[ix, iy] = 1
        else:
            self.state = "FALLING"
            fs = self.cycle_step - b2
            tf = fs / self.t_fall
            self.pos = self.prev_pos + tf * (pb - self.prev_pos)
            if fs >= self.t_fall - 1:
                self._deposit(sigma, pb, nx, ny, activation_map)
        ix = int(np.clip(self.pos[0], 0, nx - 1))
        iy = int(np.clip(self.pos[1], 0, ny - 1))
        activation_map[ix, iy] = 1
        disp = float(np.linalg.norm(self.pos - self.prev_pos))
        at_boundary = (abs(self.cycle_step - b1) <= 1 or
                       abs(self.cycle_step - b2) <= 1)
        return disp if at_boundary else 0.0

    def _scoop(self, sigma, nx, ny, activation_map):
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
        activation_map[np.ix_(xa, ya)] = np.maximum(
            activation_map[np.ix_(xa, ya)],
            (w > 0.01).astype(float))

    def _deposit(self, sigma, pos, nx, ny, activation_map):
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
        activation_map[np.ix_(xa, ya)] = np.maximum(
            activation_map[np.ix_(xa, ya)],
            (w > 0.01).astype(float))


def run_config(nx, ny, steps, dt, D, alpha, separation,
               pump_A, ratio, lam, X, Y,
               mode, kappa_psi=0.001, rng_seed=42):
    rng = np.random.RandomState(rng_seed)
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    chi = np.zeros((nx, ny))
    activation_map = np.zeros((nx, ny))
    probes = [FluxProbe(i + 1, i * 5) for i in range(12)]
    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95
    ts_bruce_energy = []
    ts_psi_total = []
    ts_sigma_total = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break
        pa = np.array([com[0] + separation, com[1]])
        pb = np.array([com[0] - separation * 0.3, com[1]])
        r2A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2A / (2 * 4.0**2))
        sigma += pA * dt
        activation_map = np.maximum(
            activation_map, (pA * dt > 0.001).astype(float))
        bx = com[0] + separation
        r2B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_A * ratio * np.exp(-r2B / (2 * 3.0**2))
        sigma += pB * dt
        activation_map = np.maximum(
            activation_map, (pB * dt > 0.001).astype(float))
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
                            nx, ny, rng, activation_map)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx - 1))
                iy = int(np.clip(p.pos[1], 0, ny - 1))
                bruce_field[ix, iy] += jump * 0.1
                total_jump += jump
        bruce_field *= bruce_decay

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

        elif mode == 'sensory_flux':
            # Sensory flux: Psi = (D_f_local - 1) * ln(grad^2)
            psi = compute_sensory_flux(sigma, activation_map)
            # Dissipate sigma proportional to Psi
            e_out = kappa_psi * psi * sigma
            sigma -= e_out
            sigma = np.maximum(sigma, 0)
            # Dissipate Brucetron proportional to Psi
            psi_at_bruce = compute_sensory_flux(
                bruce_field, activation_map)
            bruce_out = kappa_psi * 0.5 * psi_at_bruce * bruce_field
            bruce_field -= bruce_out
            bruce_field = np.maximum(bruce_field, 0)
            ts_psi_total.append(float(np.sum(psi)))
        else:
            ts_psi_total.append(0.0)

        if mode != 'sensory_flux':
            ts_psi_total.append(0.0)

        bruce_e = float(np.sum(bruce_field**2))
        ts_bruce_energy.append(bruce_e)
        ts_sigma_total.append(float(np.sum(sigma)))

    return {
        "ts_bruce_energy": np.array(ts_bruce_energy),
        "ts_psi_total": np.array(ts_psi_total),
        "ts_sigma_total": np.array(ts_sigma_total),
        "final_bruce_rms": float(np.sqrt(
            np.mean(bruce_field**2))),
        "final_sigma": float(np.sum(sigma)),
        "activation_pct": float(
            np.sum(activation_map)) / (nx * ny) * 100,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v18 Sensory Flux Dissipation")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v18 -- SENSORY FLUX DISSIPATION")
    print(f"  Psi = (D_f - 1) * ln(grad_sigma^2)")
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
        ("C: Sensory flux (Psi)", "sensory_flux"),
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

        entry = {
            "name": name,
            "mode": mode,
            "bruce_early": round(early, 6),
            "bruce_late": round(late, 6),
            "growth_rate": round(rate, 8),
            "power_exp": round(exp, 4),
            "final_bruce_rms": round(
                result["final_bruce_rms"], 8),
            "final_sigma": round(result["final_sigma"], 4),
            "activation_pct": round(
                result["activation_pct"], 2),
        }
        all_results.append(entry)

        print(f"  Brucetron early:  {entry['bruce_early']:.6f}")
        print(f"  Brucetron late:   {entry['bruce_late']:.6f}")
        print(f"  Growth rate:      {entry['growth_rate']:.8f}")
        print(f"  Power exponent:   {entry['power_exp']:.4f}")
        print(f"  Bruce RMS:        {entry['final_bruce_rms']:.8f}")
        print(f"  Activation:       {entry['activation_pct']:.1f}%")

    # ═══════════════════════════════════════════════════
    # COMPARISON
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  SENSORY FLUX COMPARISON")
    print(f"{'='*65}")

    print(f"\n  {'Config':>28} {'Rate':>12} {'Late E':>10} "
          f"{'Exp':>8} {'RMS':>12}")
    print(f"  {'-'*28} {'-'*12} {'-'*10} {'-'*8} {'-'*12}")

    for r in all_results:
        print(f"  {r['name']:>28} {r['growth_rate']:>12.8f} "
              f"{r['bruce_late']:>10.4f} "
              f"{r['power_exp']:>8.4f} "
              f"{r['final_bruce_rms']:>12.8f}")

    rate_a = all_results[0]["growth_rate"]
    rate_b = all_results[1]["growth_rate"]
    rate_c = all_results[2]["growth_rate"]

    red_b = (1 - rate_b / rate_a) * 100 if rate_a > 0 else 0
    red_c = (1 - rate_c / rate_a) * 100 if rate_a > 0 else 0

    print(f"\n  Rate reduction vs baseline:")
    print(f"    Chi tank (B):         {red_b:.1f}%")
    print(f"    Sensory flux (C):     {red_c:.1f}%")

    if rate_b != 0:
        flux_vs_chi = (1 - rate_c / rate_b) * 100
        print(f"    Flux vs chi tank:     {flux_vs_chi:.1f}%")

    # ═══════════════════════════════════════════════════
    # VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  SENSORY FLUX VERDICT")
    print(f"{'='*65}")

    if rate_c < rate_b and rate_c < rate_a:
        if rate_c < 0:
            print(f"\n  SENSORY FLUX ACHIEVES NEGATIVE GROWTH")
            print(f"  The Frastrate IS the closure mechanism.")
            print(f"  Psi-weighted dissipation outperforms chi.")
        else:
            print(f"\n  SENSORY FLUX OUTPERFORMS CHI TANK")
            print(f"  Overlap of fractal depth + gradient works.")
    elif rate_c < rate_a:
        print(f"\n  SENSORY FLUX REDUCES GROWTH BUT CHI WINS")
        print(f"  The overlap helps but smooth tank is stronger.")
    else:
        print(f"\n  SENSORY FLUX INEFFECTIVE")
        print(f"  Psi weighting does not improve closure.")

    best = min(all_results, key=lambda r: r["growth_rate"])
    print(f"\n  Best: {best['name']}")
    print(f"  Rate: {best['growth_rate']:.8f}")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v18_sensory_flux_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v18 Sensory Flux Dissipation",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Psi-weighted dissipation where fractal "
                     "depth and sigma gradient overlap"),
        "grid": nx, "steps": args.steps,
        "configs": all_results,
        "rate_reduction": {
            "chi_tank_vs_baseline": round(red_b, 2),
            "sensory_flux_vs_baseline": round(red_c, 2),
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
