# -*- coding: utf-8 -*-
"""
BCM v19.6 -- Corridor Flight Test
=====================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

First long-burn transit through the GREEN corridor with
all v19 mechanisms active and real-time diagnostics.

Frozen constants:
    kappa_drain = 0.35
    chi_decay_rate = 0.997
    alpha = 0.80
    pump-probe ratio = 10
    probe cycle = 50 (5/35/10)

GREEN corridor: lambda 0.02 - 0.08

Density profile (realistic transit):
    Phase 1: Funded space (lambda=0.03, steps 0-2000)
    Phase 2: Void entry (lambda ramps 0.03->0.05, 2000-4000)
    Phase 3: Deep void (lambda=0.06, 4000-8000)
    Phase 4: Graveyard crossing (lambda dips to 0.03, 8000-10000)
    Phase 5: Recovery (lambda=0.05, 10000-14000)
    Phase 6: Re-emergence (lambda ramps 0.05->0.03, 14000-16000)
    Phase 7: Arrival (lambda=0.03, 16000-20000)

Real-time diagnostics every 200 steps:
    Brucetron RMS, phi heartbeat, chi level, Baume gauge,
    conservation check, crew safety, zone status

Usage:
    python BCM_v19_corridor_flight.py
    python BCM_v19_corridor_flight.py --steps 20000 --grid 256
"""

import numpy as np
import json
import os
import time
import math
import argparse


# ---- FROZEN CONSTANTS ----
KAPPA_DRAIN = 0.35
CHI_DECAY = 0.997
ALPHA = 0.80
PROBE_CYCLE = 50


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


def get_density_profile(step, total_steps):
    """
    Realistic transit density profile.
    Returns lambda value and phase name.
    All values inside GREEN corridor [0.02-0.08].
    """
    frac = step / total_steps
    if frac < 0.10:
        # Phase 1: Funded space
        return 0.03, "FUNDED"
    elif frac < 0.20:
        # Phase 2: Void entry (ramp up)
        t = (frac - 0.10) / 0.10
        return 0.03 + t * 0.02, "ENTRY"
    elif frac < 0.40:
        # Phase 3: Deep void
        return 0.06, "DEEP_VOID"
    elif frac < 0.50:
        # Phase 4: Graveyard crossing (dip)
        t = (frac - 0.40) / 0.10
        lam = 0.06 - t * 0.03
        return max(0.03, lam), "GRAVEYARD"
    elif frac < 0.70:
        # Phase 5: Recovery
        return 0.05, "RECOVERY"
    elif frac < 0.80:
        # Phase 6: Re-emergence (ramp down)
        t = (frac - 0.70) / 0.10
        return 0.05 - t * 0.02, "RE_EMERGE"
    else:
        # Phase 7: Arrival
        return 0.03, "ARRIVAL"


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
               probe_hits, chi_field):
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
            ba = KAPPA_DRAIN * self.payload
            self.payload -= ba
            self.total_bled += ba
            bleed = ba
            bx = int(np.clip(pb[0], 0, nx-1))
            by = int(np.clip(pb[1], 0, ny-1))
            xa = np.arange(max(0,bx-4), min(nx,bx+5))
            ya = np.arange(max(0,by-4), min(ny,by+5))
            if len(xa) > 0 and len(ya) > 0:
                Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
                r2 = (Xl-pb[0])**2+(Yl-pb[1])**2
                w = np.exp(-r2/(2*2.0**2))
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
            self.pos = pb + t*(pa-pb)
        elif self.cycle_step < b2:
            self.state = "EJECTED"
            as_ = self.cycle_step - self.t_transit
            bao = rng.uniform(-0.8, 0.8)
            vc = 5 + (self.cycles % 4)
            ta = as_ / self.t_arc
            amr = 40.0 + rng.uniform(-10, 15)
            ar = amr*(ta*2) if ta < 0.5 else amr*(2-ta*2)
            ca = bao + ta*2*math.pi
            va = round(ca/(2*math.pi/vc))*(2*math.pi/vc)
            aa = 0.3*ca + 0.7*va
            self.pos = np.array([
                pa[0]+ar*np.cos(aa),
                pa[1]+ar*np.sin(aa)])
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
                ba = KAPPA_DRAIN * self.payload
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
        xa = np.arange(max(0,ix-4), min(nx,ix+5))
        ya = np.arange(max(0,iy-4), min(ny,iy+5))
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
        xa = np.arange(max(0,ix-4), min(nx,ix+5))
        ya = np.arange(max(0,iy-4), min(ny,iy+5))
        if len(xa)==0 or len(ya)==0: return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl-pos[0])**2+(Yl-pos[1])**2
        w = np.exp(-r2/(2*self.scoop_r**2))
        ws = float(np.sum(w))
        if ws > 1e-15:
            sigma[np.ix_(xa,ya)] += w*(self.payload/ws)
        self.payload = 0.0


def main():
    parser = argparse.ArgumentParser(
        description="BCM v19.6 Corridor Flight Test")
    parser.add_argument("--steps", type=int, default=20000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx = ny = args.grid
    steps = args.steps

    print(f"\n{'='*65}")
    print(f"  BCM v19.6 -- CORRIDOR FLIGHT TEST")
    print(f"  First long-burn transit through GREEN corridor")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {steps}")
    print(f"  kappa_drain: {KAPPA_DRAIN}  chi_decay: {CHI_DECAY}")
    print(f"  Corridor: lambda [0.02 - 0.08]")
    print(f"{'='*65}")

    dt = 0.05; D = 0.5
    pump_A = 0.5; ratio = 0.25
    separation = 15.0

    x_arr = np.arange(nx); y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    rng = np.random.RandomState(42)
    sx, sy = nx//8, ny//2
    r2i = (X-sx)**2 + (Y-sy)**2
    sigma = 1.0 * np.exp(-r2i/(2*5.0**2))
    sigma_prev = sigma.copy()
    chi_field = np.zeros((nx, ny))
    phi = np.zeros((nx, ny))
    probe_hits = np.zeros((nx, ny))

    probes = [PhaseProbe(i+1, i*5) for i in range(12)]
    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95

    # Flight log
    flight_log = []
    total_bled = 0.0
    crew_violations = 0
    max_bruce_rms = 0.0
    diag_interval = 200

    # Real-time diagnostic header
    print(f"\n  {'Step':>6} {'Phase':>12} {'Lam':>6} "
          f"{'BrRMS':>8} {'PhiRMS':>8} {'Chi':>8} "
          f"{'Sigma':>8} {'Baume':>8} {'Zone':>6}")
    print(f"  {'-'*6} {'-'*12} {'-'*6} {'-'*8} "
          f"{'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*6}")

    for step in range(steps):
        # Get current density from transit profile
        lam_val, phase = get_density_profile(step, steps)

        # Build lambda field for this step
        lam = np.full((nx, ny), lam_val)
        gx = nx//2
        r2g = (X-gx)**2 + (Y-ny//2)**2
        lam -= 0.08*np.exp(-r2g/(2*18.0**2))
        lam = np.maximum(lam, 0.001)

        com = compute_com(sigma)
        if com is None:
            print(f"  *** CRAFT DISSOLVED at step {step} ***")
            break
        pa = np.array([com[0]+separation, com[1]])
        pb = np.array([com[0]-separation*0.3, com[1]])
        r2A = (X-com[0])**2+(Y-com[1])**2
        sigma += pump_A*np.exp(-r2A/(2*4.0**2))*dt
        bx = com[0]+separation
        r2B = (X-bx)**2+(Y-com[1])**2
        sigma += pump_A*ratio*np.exp(-r2B/(2*3.0**2))*dt

        lap = (np.roll(sigma,1,0)+np.roll(sigma,-1,0)+
               np.roll(sigma,1,1)+np.roll(sigma,-1,1)-
               4*sigma)
        sn = sigma + D*lap*dt - lam*sigma*dt
        sn += ALPHA*(sigma-sigma_prev)
        sn = np.maximum(sn, 0)
        if float(np.max(sn)) > 1e10:
            print(f"  *** BLOWUP at step {step} ***")
            break

        phi = phi*0.95 + (sigma - sigma_prev)
        sigma_prev = sigma.copy()
        sigma = sn

        step_bleed = 0.0
        for p in probes:
            jump, bleed = p.update(
                com, pa, pb, step, sigma, nx, ny, rng,
                probe_hits, chi_field)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx-1))
                iy = int(np.clip(p.pos[1], 0, ny-1))
                bruce_field[ix, iy] += jump*0.1
            step_bleed += bleed
        bruce_field *= bruce_decay
        total_bled += step_bleed

        # Chi freeboard with frozen decay
        ix_c = int(np.clip(com[0], 0, nx-1))
        iy_c = int(np.clip(com[1], 0, ny-1))
        r_v = 20
        x_lo = max(0, ix_c-r_v); x_hi = min(nx, ix_c+r_v)
        y_lo = max(0, iy_c-r_v); y_hi = min(ny, iy_c+r_v)
        ls = sigma[x_lo:x_hi, y_lo:y_hi]
        fl = float(np.mean(ls))+1.5*float(np.std(ls))
        overflow = np.maximum(sigma-fl, 0)
        spill = overflow*0.5
        sigma -= spill
        chi_field += spill
        deficit = np.maximum(fl*0.8-sigma, 0)
        drain = np.minimum(chi_field*0.1, deficit)
        sigma += drain
        chi_field -= drain
        chi_field *= CHI_DECAY
        bruce_in = bruce_field*0.05
        chi_field += bruce_in*0.01
        bruce_field -= bruce_in
        bruce_field = np.maximum(bruce_field, 0)

        # ---- REAL-TIME DIAGNOSTICS ----
        if step % diag_interval == 0 or step == steps-1:
            bruce_rms = float(np.sqrt(np.mean(bruce_field**2)))
            phi_rms = float(np.sqrt(np.mean(phi**2)))
            chi_total = float(np.sum(chi_field))
            sigma_total = float(np.sum(sigma))
            system_total = sigma_total + chi_total

            # Baume gauge: orbital sigma / substrate sigma
            orbital_sum = sum(p.payload for p in probes)
            substrate_local = float(np.mean(
                sigma[max(0,ix_c-10):min(nx,ix_c+10),
                      max(0,iy_c-10):min(ny,iy_c+10)]))
            baume = (orbital_sum / (substrate_local + 1e-10))

            # Zone classification
            if bruce_rms < 0.006:
                zone = "GREEN"
            elif bruce_rms < 0.010:
                zone = "YELLOW"
            else:
                zone = "RED"

            # Crew safety check
            if bruce_rms > 0.012:
                crew_violations += 1

            if bruce_rms > max_bruce_rms:
                max_bruce_rms = bruce_rms

            print(f"  {step:>6} {phase:>12} {lam_val:>6.3f} "
                  f"{bruce_rms:>8.5f} {phi_rms:>8.5f} "
                  f"{chi_total:>8.1f} {sigma_total:>8.1f} "
                  f"{baume:>8.4f} {zone:>6}")

            entry = {
                "step": step,
                "phase": phase,
                "lambda": round(lam_val, 4),
                "bruce_rms": round(bruce_rms, 8),
                "phi_rms": round(phi_rms, 8),
                "chi_total": round(chi_total, 4),
                "sigma_total": round(sigma_total, 4),
                "system_total": round(system_total, 4),
                "baume": round(baume, 6),
                "zone": zone,
                "total_bled": round(total_bled, 4),
            }
            flight_log.append(entry)

    # ---- FLIGHT SUMMARY ----
    print(f"\n{'='*65}")
    print(f"  CORRIDOR FLIGHT SUMMARY")
    print(f"{'='*65}")

    final_sigma = float(np.sum(sigma))
    final_chi = float(np.sum(chi_field))
    final_system = final_sigma + final_chi

    greens = sum(1 for e in flight_log if e["zone"] == "GREEN")
    yellows = sum(1 for e in flight_log if e["zone"] == "YELLOW")
    reds = sum(1 for e in flight_log if e["zone"] == "RED")
    total_diag = len(flight_log)

    print(f"\n  Duration:        {steps} steps")
    print(f"  Grid:            {nx}x{ny}")
    print(f"  kappa_drain:     {KAPPA_DRAIN}")
    print(f"  chi_decay:       {CHI_DECAY}")
    print(f"\n  Zone breakdown:")
    print(f"    GREEN:  {greens}/{total_diag} "
          f"({greens/total_diag*100:.1f}%)")
    print(f"    YELLOW: {yellows}/{total_diag} "
          f"({yellows/total_diag*100:.1f}%)")
    print(f"    RED:    {reds}/{total_diag} "
          f"({reds/total_diag*100:.1f}%)")

    print(f"\n  Crew safety:")
    print(f"    Violations: {crew_violations}")
    print(f"    Max BruceRMS: {max_bruce_rms:.6f}")
    if crew_violations == 0:
        print(f"    Status: ALL CLEAR")
    else:
        print(f"    Status: *** VIOLATION ***")

    print(f"\n  Conservation:")
    print(f"    Final sigma:  {final_sigma:.2f}")
    print(f"    Final chi:    {final_chi:.2f}")
    print(f"    System total: {final_system:.2f}")
    print(f"    Total bled:   {total_bled:.2f}")

    print(f"\n  Heartbeat (f/2):")
    final_phi = float(np.sqrt(np.mean(phi**2)))
    print(f"    Phi RMS: {final_phi:.6f}")
    if 0.0003 < final_phi < 0.005:
        print(f"    Status: STEADY TONE")
        hb = "STEADY"
    elif final_phi <= 0.0003:
        print(f"    Status: QUIET (may have lost heartbeat)")
        hb = "QUIET"
    else:
        print(f"    Status: ELEVATED")
        hb = "ELEVATED"

    # Overall mission verdict
    print(f"\n{'='*65}")
    if (crew_violations == 0 and
            greens / total_diag > 0.7):
        print(f"  MISSION: GO FOR TRANSIT")
        mission = "GO"
    elif crew_violations == 0:
        print(f"  MISSION: MARGINAL — review yellow phases")
        mission = "MARGINAL"
    else:
        print(f"  MISSION: ABORT — crew safety violated")
        mission = "ABORT"
    print(f"{'='*65}")

    # ---- SAVE JSON ----
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v19_corridor_flight_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v19.6 Corridor Flight Test",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("First long-burn transit through "
                     "GREEN corridor with all v19 "
                     "mechanisms active"),
        "grid": nx, "steps": steps,
        "frozen_constants": {
            "kappa_drain": KAPPA_DRAIN,
            "chi_decay": CHI_DECAY,
            "alpha": ALPHA,
            "probe_cycle": PROBE_CYCLE,
        },
        "corridor": [0.02, 0.08],
        "mission_verdict": mission,
        "crew_violations": crew_violations,
        "max_bruce_rms": round(max_bruce_rms, 8),
        "heartbeat": hb,
        "zone_breakdown": {
            "green": greens,
            "yellow": yellows,
            "red": reds,
            "total": total_diag,
            "green_pct": round(greens/total_diag*100, 1),
        },
        "conservation": {
            "final_sigma": round(final_sigma, 4),
            "final_chi": round(final_chi, 4),
            "system_total": round(final_system, 4),
            "total_bled": round(total_bled, 4),
        },
        "flight_log": flight_log,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
