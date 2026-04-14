# -*- coding: utf-8 -*-
"""
BCM v19.4 -- Combined Drain + Chi Freeboard
==============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

v19.3 proved kappa_drain works at the source (two GREEN
windows at lambda=0.04 and 0.10). But bled orbital sigma
accumulated in the field (final_sigma nearly doubled).
The bled shive residual needs a recovery path.

THIS TEST: Combine kappa_drain (source attack) with chi
freeboard (Baume residual absorption). Two mechanisms,
two scales, one system.

  kappa_drain: bleeds orbital sigma at B1/B2 boundaries
               -> breaks Brucetron injection at source
  chi freeboard: absorbs bled residual into 4D headspace
               -> prevents field inflation / contrail

The kraft mill recovery boiler: drain cracks the blow
valve, chi burns the black liquor in 4D headspace.

THREE CONFIGS at each density:
    A: No mechanisms (baseline)
    B: kappa_drain only (v19.3 reference)
    C: kappa_drain + chi freeboard (combined)

Density sweep: lambda 0.02 - 0.20 (same as v19.3)

Usage:
    python BCM_v19_combined_drain_chi.py
    python BCM_v19_combined_drain_chi.py --steps 5000 --grid 256
"""

import numpy as np
import json
import os
import time
import math
import argparse


KAPPA_DRAIN = 0.35  # frozen -- orbital sigma bleed


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


def compute_chi_operator(phi, dx=1.0):
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
    return float(np.sum(np.abs(chi_op)))


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
        self.total_bled = 0.0

    def update(self, com, pa, pb, step, sigma, nx, ny, rng,
               probe_hits, kappa_drain, chi_field, use_chi):
        eff = step - self.eject_offset
        if eff < 0:
            self.pos = com.copy()
            self.prev_pos = self.pos.copy()
            return 0.0, 0.0
        cl = self.t_transit + self.t_arc + self.t_fall
        prev = self.cycles
        self.cycle_step = eff % cl
        self.cycles = eff // cl

        bleed = 0.0

        if self.cycles > prev and self.payload > 0:
            # NAVIGATIONAL DRAIN at deposit boundary
            if kappa_drain > 0:
                bleed_amount = kappa_drain * self.payload
                self.payload -= bleed_amount
                self.total_bled += bleed_amount
                bleed = bleed_amount
                # Route bled sigma to chi freeboard
                if use_chi and chi_field is not None:
                    bx = int(np.clip(pb[0], 0, nx - 1))
                    by = int(np.clip(pb[1], 0, ny - 1))
                    xa = np.arange(max(0, bx - 4),
                                   min(nx, bx + 5))
                    ya = np.arange(max(0, by - 4),
                                   min(ny, by + 5))
                    if len(xa) > 0 and len(ya) > 0:
                        Xl, Yl = np.meshgrid(xa, ya,
                                             indexing='ij')
                        r2 = ((Xl - pb[0])**2 +
                              (Yl - pb[1])**2)
                        w = np.exp(-r2 / (2 * 2.0**2))
                        ws = float(np.sum(w))
                        if ws > 1e-15:
                            chi_field[np.ix_(xa, ya)] += (
                                w * (bleed_amount / ws))
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
            ar = (amr * (ta * 2) if ta < 0.5
                  else amr * (2 - ta * 2))
            ca = bao + ta * 2 * math.pi
            va = (round(ca / (2 * math.pi / vc)) *
                  (2 * math.pi / vc))
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
            self.pos = (self.prev_pos +
                        tf * (pb - self.prev_pos))
            if fs >= self.t_fall - 1:
                if kappa_drain > 0:
                    bleed_amount = kappa_drain * self.payload
                    self.payload -= bleed_amount
                    self.total_bled += bleed_amount
                    bleed += bleed_amount
                    if use_chi and chi_field is not None:
                        bx = int(np.clip(pb[0], 0, nx - 1))
                        by = int(np.clip(pb[1], 0, ny - 1))
                        xa = np.arange(max(0, bx - 4),
                                       min(nx, bx + 5))
                        ya = np.arange(max(0, by - 4),
                                       min(ny, by + 5))
                        if len(xa) > 0 and len(ya) > 0:
                            Xl, Yl = np.meshgrid(
                                xa, ya, indexing='ij')
                            r2 = ((Xl - pb[0])**2 +
                                  (Yl - pb[1])**2)
                            w = np.exp(-r2 / (2 * 2.0**2))
                            ws = float(np.sum(w))
                            if ws > 1e-15:
                                chi_field[np.ix_(xa, ya)] += (
                                    w * (bleed_amount / ws))
                self._deposit(sigma, pb, nx, ny)

        disp = float(np.linalg.norm(
            self.pos - self.prev_pos))
        at_boundary = (abs(self.cycle_step - b1) <= 1 or
                       abs(self.cycle_step - b2) <= 1)
        jump = disp if at_boundary else 0.0
        return jump, bleed

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
               pump_A, ratio, void_lambda, X, Y,
               kappa_drain, use_chi, rng_seed=42):
    rng = np.random.RandomState(rng_seed)
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    chi_field = np.zeros((nx, ny))
    phi = np.zeros((nx, ny))
    probe_hits = np.zeros((nx, ny))

    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny // 2)**2
    lam -= 0.08 * np.exp(-r2g / (2 * 18.0**2))
    lam = np.maximum(lam, 0.001)

    probes = [PhaseProbe(i + 1, i * 5) for i in range(12)]
    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95

    ts_bruce = []
    total_bled = 0.0
    initial_sigma = float(np.sum(sigma))

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

        for p in probes:
            jump, bleed = p.update(
                com, pa, pb, step, sigma, nx, ny, rng,
                probe_hits, kappa_drain, chi_field, use_chi)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx - 1))
                iy = int(np.clip(p.pos[1], 0, ny - 1))
                bruce_field[ix, iy] += jump * 0.1
            total_bled += bleed
        bruce_field *= bruce_decay

        # Chi freeboard decay + sigma interaction
        if use_chi:
            # Spill/drain (v17 mechanism)
            ix_c = int(np.clip(com[0], 0, nx - 1))
            iy_c = int(np.clip(com[1], 0, ny - 1))
            r_v = 20
            x_lo = max(0, ix_c - r_v)
            x_hi = min(nx, ix_c + r_v)
            y_lo = max(0, iy_c - r_v)
            y_hi = min(ny, iy_c + r_v)
            ls = sigma[x_lo:x_hi, y_lo:y_hi]
            fl = (float(np.mean(ls)) +
                  1.5 * float(np.std(ls)))
            overflow = np.maximum(sigma - fl, 0)
            spill = overflow * 0.5
            sigma -= spill
            chi_field += spill
            deficit = np.maximum(fl * 0.8 - sigma, 0)
            drain = np.minimum(chi_field * 0.1, deficit)
            sigma += drain
            chi_field -= drain
            # Chi decay (4D headspace absorption)
            chi_field *= 0.999
            # Brucetron into chi
            bruce_in = bruce_field * 0.05
            chi_field += bruce_in * 0.01
            bruce_field -= bruce_in
            bruce_field = np.maximum(bruce_field, 0)

        ts_bruce.append(float(np.sum(bruce_field**2)))

    n = len(ts_bruce)
    skip = 100
    rate = 0
    if n > skip * 2:
        steps_fit = np.arange(skip, n, dtype=float)
        rate = np.polyfit(steps_fit, ts_bruce[skip:], 1)[0]

    final_sigma = float(np.sum(sigma))
    final_chi = float(np.sum(chi_field))
    phi_rms = float(np.sqrt(np.mean(phi**2)))
    bruce_rms = float(np.sqrt(np.mean(bruce_field**2)))

    gp_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
    gp_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
    xi = float(np.sum(phi**2 + gp_x**2 + gp_y**2))
    chi_op = compute_chi_operator(phi)

    # Conservation: sigma + chi + bled = initial + pumped
    total_system = final_sigma + final_chi

    return {
        "growth_rate": round(rate, 8),
        "bruce_rms": round(bruce_rms, 8),
        "phi_rms": round(phi_rms, 8),
        "chi_op_late": round(chi_op, 6),
        "xi_late": round(xi, 4),
        "total_bled": round(total_bled, 4),
        "final_sigma": round(final_sigma, 4),
        "final_chi": round(final_chi, 4),
        "total_system": round(total_system, 4),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v19.4 Combined Drain + Chi")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v19.4 -- COMBINED DRAIN + CHI FREEBOARD")
    print(f"  kappa_drain at source + chi absorbs residual")
    print(f"  The recovery boiler.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"  kappa_drain: {KAPPA_DRAIN} (FROZEN)")

    dt = 0.05; D = 0.5
    pump_A = 0.5; ratio = 0.25; alpha = 0.80
    separation = 15.0

    x_arr = np.arange(nx); y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    densities = [0.02, 0.04, 0.06, 0.08, 0.10,
                 0.12, 0.15, 0.20]

    all_results = []

    for lam_val in densities:
        print(f"\n  {'='*55}")
        print(f"  LAMBDA = {lam_val:.2f}")
        print(f"  {'='*55}")

        configs = [
            ("A: Baseline", 0.0, False),
            ("B: Drain only", KAPPA_DRAIN, False),
            ("C: Drain + Chi", KAPPA_DRAIN, True),
        ]

        density_results = {"lambda": lam_val, "configs": []}

        for name, kd, uc in configs:
            print(f"\n  {'─'*45}")
            print(f"  {name}")
            print(f"  {'─'*45}")

            r = run_config(
                nx, ny, args.steps, dt, D, alpha,
                separation, pump_A, ratio, lam_val,
                X, Y, kappa_drain=kd, use_chi=uc)

            # Zone classification
            rate = r["growth_rate"]
            if rate < -1e-6:
                zone = "GREEN"
            elif abs(rate) < 1e-6:
                zone = "YELLOW"
            else:
                zone = "RED"

            entry = {"name": name, **r, "zone": zone}
            density_results["configs"].append(entry)

            print(f"  Rate:     {rate:.8f}  [{zone}]")
            print(f"  BruceRMS: {r['bruce_rms']:.8f}")
            print(f"  PhiRMS:   {r['phi_rms']:.8f}")
            print(f"  Sigma:    {r['final_sigma']:.2f}")
            print(f"  Chi:      {r['final_chi']:.2f}")
            print(f"  System:   {r['total_system']:.2f}")
            print(f"  Bled:     {r['total_bled']:.2f}")

        all_results.append(density_results)

    # ---- ENVELOPE TABLE ----
    print(f"\n{'='*65}")
    print(f"  COMBINED ENVELOPE")
    print(f"  kappa_drain = {KAPPA_DRAIN} (FROZEN)")
    print(f"{'='*65}")

    print(f"\n  {'Lam':>6} {'A Rate':>12} {'B Rate':>12} "
          f"{'C Rate':>12} {'B Zone':>8} {'C Zone':>8}")
    print(f"  {'-'*6} {'-'*12} {'-'*12} "
          f"{'-'*12} {'-'*8} {'-'*8}")

    for dr in all_results:
        a = dr["configs"][0]
        b = dr["configs"][1]
        c = dr["configs"][2]
        print(f"  {dr['lambda']:>6.2f} "
              f"{a['growth_rate']:>12.8f} "
              f"{b['growth_rate']:>12.8f} "
              f"{c['growth_rate']:>12.8f} "
              f"{b['zone']:>8} {c['zone']:>8}")

    # Conservation check
    print(f"\n  CONSERVATION CHECK (Drain+Chi):")
    print(f"  {'Lam':>6} {'Sigma':>10} {'Chi':>10} "
          f"{'System':>10} {'Bled':>10}")
    print(f"  {'-'*6} {'-'*10} {'-'*10} "
          f"{'-'*10} {'-'*10}")
    for dr in all_results:
        c = dr["configs"][2]
        print(f"  {dr['lambda']:>6.2f} "
              f"{c['final_sigma']:>10.2f} "
              f"{c['final_chi']:>10.2f} "
              f"{c['total_system']:>10.2f} "
              f"{c['total_bled']:>10.2f}")

    print(f"{'='*65}")

    # ---- SAVE JSON ----
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v19_combined_drain_chi_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v19.4 Combined Drain + Chi Freeboard",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Combined kappa_drain source attack "
                     "with chi freeboard residual "
                     "absorption. Recovery boiler test."),
        "grid": nx, "steps": args.steps,
        "kappa_drain": KAPPA_DRAIN,
        "results": all_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
