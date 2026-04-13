# -*- coding: utf-8 -*-
"""
BCM v19.5 -- Recovery Boiler Tuning
======================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

v19.4 closed the ORANGE gap but flipped lambda=0.10 from
GREEN to RED. The chi freeboard is over-damping the
resonance that made that window work.

THIS TEST: Sweep chi_decay_rate at lambda=0.10 ONLY.
Hold kappa_drain=0.35 frozen. Find the decay rate where
lambda=0.10 returns to GREEN without losing the former
ORANGE gap (0.06-0.08).

Verification runs at lambda=0.06 (former ORANGE, now
GREEN) to confirm it stays GREEN at the tuned value.

chi_decay_rate controls how fast the 4D headspace
absorbs the Baume residual. Too fast (0.99) = over-damp
the resonance. Too slow (0.9999) = residual accumulates
and inflates the field.

Usage:
    python BCM_v19_boiler_tune.py
    python BCM_v19_boiler_tune.py --steps 5000 --grid 256
"""

import numpy as np
import json
import os
import time
import math
import argparse


KAPPA_DRAIN = 0.35


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
               probe_hits, kappa_drain, chi_field):
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
            if kappa_drain > 0:
                ba = kappa_drain * self.payload
                self.payload -= ba
                self.total_bled += ba
                bleed = ba
                bx = int(np.clip(pb[0], 0, nx - 1))
                by = int(np.clip(pb[1], 0, ny - 1))
                xa = np.arange(max(0, bx-4), min(nx, bx+5))
                ya = np.arange(max(0, by-4), min(ny, by+5))
                if len(xa) > 0 and len(ya) > 0:
                    Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
                    r2 = (Xl-pb[0])**2 + (Yl-pb[1])**2
                    w = np.exp(-r2 / (2*2.0**2))
                    ws = float(np.sum(w))
                    if ws > 1e-15:
                        chi_field[np.ix_(xa,ya)] += w*(ba/ws)
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
            ar = amr*(ta*2) if ta < 0.5 else amr*(2-ta*2)
            ca = bao + ta * 2 * math.pi
            va = round(ca/(2*math.pi/vc))*(2*math.pi/vc)
            aa = 0.3*ca + 0.7*va
            self.pos = np.array([
                pa[0]+ar*np.cos(aa), pa[1]+ar*np.sin(aa)])
            self._scoop(sigma, nx, ny)
            ix = int(np.clip(self.pos[0], 0, nx-1))
            iy = int(np.clip(self.pos[1], 0, ny-1))
            probe_hits[ix, iy] += 1.0
        else:
            self.state = "FALLING"
            fs = self.cycle_step - b2
            tf = fs / self.t_fall
            self.pos = self.prev_pos + tf*(pb-self.prev_pos)
            if fs >= self.t_fall - 1:
                if kappa_drain > 0:
                    ba = kappa_drain * self.payload
                    self.payload -= ba
                    self.total_bled += ba
                    bleed += ba
                    bx = int(np.clip(pb[0], 0, nx-1))
                    by = int(np.clip(pb[1], 0, ny-1))
                    xa = np.arange(max(0,bx-4), min(nx,bx+5))
                    ya = np.arange(max(0,by-4), min(ny,by+5))
                    if len(xa) > 0 and len(ya) > 0:
                        Xl, Yl = np.meshgrid(xa,ya,indexing='ij')
                        r2 = (Xl-pb[0])**2+(Yl-pb[1])**2
                        w = np.exp(-r2/(2*2.0**2))
                        ws = float(np.sum(w))
                        if ws > 1e-15:
                            chi_field[np.ix_(xa,ya)] += w*(ba/ws)
                self._deposit(sigma, pb, nx, ny)
        disp = float(np.linalg.norm(self.pos-self.prev_pos))
        at_b = (abs(self.cycle_step-b1) <= 1 or
                abs(self.cycle_step-b2) <= 1)
        return (disp if at_b else 0.0), bleed

    def _scoop(self, sigma, nx, ny):
        ix = int(np.clip(self.pos[0], 0, nx-1))
        iy = int(np.clip(self.pos[1], 0, ny-1))
        xa = np.arange(max(0, ix-4), min(nx, ix+5))
        ya = np.arange(max(0, iy-4), min(ny, iy+5))
        if len(xa)==0 or len(ya)==0: return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl-self.pos[0])**2+(Yl-self.pos[1])**2
        w = np.exp(-r2/(2*self.scoop_r**2))
        loc = sigma[np.ix_(xa, ya)]
        sc = np.minimum(loc*w*self.scoop_eff, loc)
        sc = np.maximum(sc, 0)
        sigma[np.ix_(xa, ya)] -= sc
        self.payload += float(np.sum(sc))

    def _deposit(self, sigma, pos, nx, ny):
        if self.payload <= 0: return
        ix = int(np.clip(pos[0], 0, nx-1))
        iy = int(np.clip(pos[1], 0, ny-1))
        xa = np.arange(max(0, ix-4), min(nx, ix+5))
        ya = np.arange(max(0, iy-4), min(ny, iy+5))
        if len(xa)==0 or len(ya)==0: return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl-pos[0])**2+(Yl-pos[1])**2
        w = np.exp(-r2/(2*self.scoop_r**2))
        ws = float(np.sum(w))
        if ws > 1e-15:
            sigma[np.ix_(xa,ya)] += w*(self.payload/ws)
        self.payload = 0.0


def run_config(nx, ny, steps, dt, D, alpha, separation,
               pump_A, ratio, void_lambda, X, Y,
               chi_decay, rng_seed=42):
    rng = np.random.RandomState(rng_seed)
    sx, sy = nx//8, ny//2
    r2i = (X-sx)**2 + (Y-sy)**2
    sigma = 1.0 * np.exp(-r2i/(2*5.0**2))
    sigma_prev = sigma.copy()
    chi_field = np.zeros((nx, ny))
    phi = np.zeros((nx, ny))
    probe_hits = np.zeros((nx, ny))
    lam = np.full((nx, ny), void_lambda)
    gx = nx//2
    r2g = (X-gx)**2 + (Y-ny//2)**2
    lam -= 0.08*np.exp(-r2g/(2*18.0**2))
    lam = np.maximum(lam, 0.001)

    probes = [PhaseProbe(i+1, i*5) for i in range(12)]
    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95
    ts_bruce = []
    total_bled = 0.0

    for step in range(steps):
        com = compute_com(sigma)
        if com is None: break
        pa = np.array([com[0]+separation, com[1]])
        pb = np.array([com[0]-separation*0.3, com[1]])
        r2A = (X-com[0])**2+(Y-com[1])**2
        sigma += pump_A*np.exp(-r2A/(2*4.0**2))*dt
        bx = com[0]+separation
        r2B = (X-bx)**2+(Y-com[1])**2
        sigma += pump_A*ratio*np.exp(-r2B/(2*3.0**2))*dt

        lap = (np.roll(sigma,1,0)+np.roll(sigma,-1,0)+
               np.roll(sigma,1,1)+np.roll(sigma,-1,1)-4*sigma)
        sn = sigma + D*lap*dt - lam*sigma*dt
        if alpha > 0:
            sn += alpha*(sigma-sigma_prev)
        sn = np.maximum(sn, 0)
        if float(np.max(sn)) > 1e10: break

        phi = phi*0.95 + (sigma - sigma_prev)
        sigma_prev = sigma.copy()
        sigma = sn

        for p in probes:
            jump, bleed = p.update(
                com, pa, pb, step, sigma, nx, ny, rng,
                probe_hits, KAPPA_DRAIN, chi_field)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx-1))
                iy = int(np.clip(p.pos[1], 0, ny-1))
                bruce_field[ix, iy] += jump*0.1
            total_bled += bleed
        bruce_field *= bruce_decay

        # Chi freeboard with variable decay rate
        ix_c = int(np.clip(com[0], 0, nx-1))
        iy_c = int(np.clip(com[1], 0, ny-1))
        r_v = 20
        x_lo = max(0, ix_c-r_v); x_hi = min(nx, ix_c+r_v)
        y_lo = max(0, iy_c-r_v); y_hi = min(ny, iy_c+r_v)
        ls = sigma[x_lo:x_hi, y_lo:y_hi]
        fl = float(np.mean(ls)) + 1.5*float(np.std(ls))
        overflow = np.maximum(sigma - fl, 0)
        spill = overflow * 0.5
        sigma -= spill
        chi_field += spill
        deficit = np.maximum(fl*0.8 - sigma, 0)
        drain = np.minimum(chi_field*0.1, deficit)
        sigma += drain
        chi_field -= drain
        chi_field *= chi_decay  # THE TUNABLE CONSTANT
        bruce_in = bruce_field * 0.05
        chi_field += bruce_in * 0.01
        bruce_field -= bruce_in
        bruce_field = np.maximum(bruce_field, 0)

        ts_bruce.append(float(np.sum(bruce_field**2)))

    n = len(ts_bruce)
    skip = 100
    rate = 0
    if n > skip*2:
        sf = np.arange(skip, n, dtype=float)
        rate = np.polyfit(sf, ts_bruce[skip:], 1)[0]

    return {
        "growth_rate": round(rate, 8),
        "bruce_rms": round(float(np.sqrt(np.mean(
            bruce_field**2))), 8),
        "phi_rms": round(float(np.sqrt(np.mean(
            phi**2))), 8),
        "final_sigma": round(float(np.sum(sigma)), 4),
        "final_chi": round(float(np.sum(chi_field)), 4),
        "total_system": round(float(
            np.sum(sigma)+np.sum(chi_field)), 4),
        "total_bled": round(total_bled, 4),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v19.5 Recovery Boiler Tuning")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v19.5 -- RECOVERY BOILER TUNING")
    print(f"  Sweep chi_decay_rate at lambda=0.10")
    print(f"  Verify lambda=0.06 stays GREEN")
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

    decay_values = [0.990, 0.993, 0.995, 0.997,
                    0.999, 0.9993, 0.9995, 0.9997,
                    0.9999]

    # Primary sweep: lambda=0.10
    print(f"\n  {'='*55}")
    print(f"  PRIMARY SWEEP: lambda=0.10")
    print(f"  {'='*55}")

    results_010 = []
    for dv in decay_values:
        print(f"\n  chi_decay={dv:.4f} ...", end="", flush=True)
        r = run_config(nx, ny, args.steps, dt, D, alpha,
                       separation, pump_A, ratio, 0.10,
                       X, Y, chi_decay=dv)
        rate = r["growth_rate"]
        zone = "GREEN" if rate < -1e-6 else (
            "YELLOW" if abs(rate) < 1e-6 else "RED")
        entry = {"chi_decay": dv, **r, "zone": zone}
        results_010.append(entry)
        print(f" rate={rate:.8f} [{zone}]")

    # Verification: lambda=0.06 at best decay
    # Find best decay for lambda=0.10
    greens = [r for r in results_010 if r["zone"] == "GREEN"]
    if greens:
        best_decay = min(greens,
                         key=lambda r: r["growth_rate"]
                         )["chi_decay"]
    else:
        yellows = [r for r in results_010
                   if r["zone"] == "YELLOW"]
        if yellows:
            best_decay = yellows[0]["chi_decay"]
        else:
            best_decay = min(results_010,
                             key=lambda r: r["growth_rate"]
                             )["chi_decay"]

    print(f"\n  {'='*55}")
    print(f"  VERIFICATION: lambda=0.06 at chi_decay={best_decay}")
    print(f"  (must stay GREEN)")
    print(f"  {'='*55}")

    r_verify = run_config(nx, ny, args.steps, dt, D, alpha,
                          separation, pump_A, ratio, 0.06,
                          X, Y, chi_decay=best_decay)
    rate_v = r_verify["growth_rate"]
    zone_v = "GREEN" if rate_v < -1e-6 else (
        "YELLOW" if abs(rate_v) < 1e-6 else "RED")

    print(f"  Rate: {rate_v:.8f} [{zone_v}]")
    print(f"  Sigma: {r_verify['final_sigma']:.2f}")
    print(f"  Chi: {r_verify['final_chi']:.2f}")

    # Also verify lambda=0.04
    print(f"\n  VERIFICATION: lambda=0.04 at chi_decay={best_decay}")

    r_v04 = run_config(nx, ny, args.steps, dt, D, alpha,
                       separation, pump_A, ratio, 0.04,
                       X, Y, chi_decay=best_decay)
    rate_v04 = r_v04["growth_rate"]
    zone_v04 = "GREEN" if rate_v04 < -1e-6 else (
        "YELLOW" if abs(rate_v04) < 1e-6 else "RED")
    print(f"  Rate: {rate_v04:.8f} [{zone_v04}]")

    # ---- SWEEP TABLE ----
    print(f"\n{'='*65}")
    print(f"  BOILER TUNING SWEEP (lambda=0.10)")
    print(f"{'='*65}")

    print(f"\n  {'Decay':>8} {'Rate':>12} {'BruceRMS':>10} "
          f"{'Sigma':>10} {'Chi':>10} {'Zone':>8}")
    print(f"  {'-'*8} {'-'*12} {'-'*10} {'-'*10} "
          f"{'-'*10} {'-'*8}")
    for r in results_010:
        print(f"  {r['chi_decay']:>8.4f} "
              f"{r['growth_rate']:>12.8f} "
              f"{r['bruce_rms']:>10.6f} "
              f"{r['final_sigma']:>10.2f} "
              f"{r['final_chi']:>10.2f} "
              f"{r['zone']:>8}")

    print(f"\n  Best decay for lambda=0.10: {best_decay}")
    print(f"\n  Verification:")
    print(f"    lambda=0.04: {zone_v04}")
    print(f"    lambda=0.06: {zone_v}")

    if (zone_v == "GREEN" and zone_v04 == "GREEN"
            and best_decay != 0.999):
        print(f"\n  ALL THREE WINDOWS GREEN at "
              f"chi_decay={best_decay}")
        print(f"  Lock chi_decay_rate = {best_decay}")
    elif zone_v == "GREEN" and zone_v04 == "GREEN":
        print(f"\n  Original chi_decay=0.999 holds.")
        print(f"  Lambda=0.10 needs different approach.")

    print(f"{'='*65}")

    # ---- SAVE JSON ----
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v19_boiler_tune_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v19.5 Recovery Boiler Tuning",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Sweep chi_decay_rate at lambda=0.10 "
                     "to recover GREEN window lost in "
                     "v19.4 combined system"),
        "grid": nx, "steps": args.steps,
        "kappa_drain": KAPPA_DRAIN,
        "sweep_lambda": 0.10,
        "decay_sweep": results_010,
        "best_decay": best_decay,
        "verification": {
            "lambda_006": {**r_verify, "zone": zone_v},
            "lambda_004": {**r_v04, "zone": zone_v04},
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
