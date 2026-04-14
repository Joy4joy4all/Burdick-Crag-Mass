# -*- coding: utf-8 -*-
"""
BCM v19.3 -- Navigational Drain with Frozen kappa_drain
=========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

v19.2 proved: active chi alignment is ineffective (identical
to baseline at 8 decimal places). The chi operator is a
diagnostic gauge, not a control variable. The causal chain
is sigma -> phi -> Xi -> chi_op. Control must happen at the
source: orbital sigma at the probe ingestion boundary.

THIS TEST: Freeze kappa_drain as a global constant. Sweep
substrate density across 10x range. Find the operating
envelope where Brucetron growth stays <= 0.

Two sigma streams:
  - Substrate sigma: the 2D ocean (local lambda field)
  - Orbital sigma: probe payloads in the Venturi tunnel

kappa_drain governs orbital sigma bleed per probe cycle
at the B1/B2 segment boundaries. It is the engine RPM.
Navigation is steering heading so substrate:orbital ratio
stays inside the envelope.

The Formers set the constants. The craft flies the drain.

Usage:
    python BCM_v19_navigational_drain.py
    python BCM_v19_navigational_drain.py --steps 5000 --grid 256
    python BCM_v19_navigational_drain.py --kappa 0.35
"""

import numpy as np
import json
import os
import time
import math
import argparse


KAPPA_DRAIN = 0.35  # frozen constant -- orbital sigma bleed


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
    """
    chi_op = div(phi * grad(Xi_local)) - Xi_local * lap(phi)
    Xi_local = phi^2 + |grad_phi|^2
    DIAGNOSTIC ONLY.
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
               probe_hits, kappa_drain):
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
            # Bleed a fraction of orbital sigma before
            # depositing at Pump B. This is the frozen
            # constant controlling Brucetron injection.
            bleed_amount = kappa_drain * self.payload
            self.payload -= bleed_amount
            self.total_bled += bleed_amount
            bleed = bleed_amount
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
                # NAVIGATIONAL DRAIN at fall-deposit boundary
                bleed_amount = kappa_drain * self.payload
                self.payload -= bleed_amount
                self.total_bled += bleed_amount
                bleed += bleed_amount
                self._deposit(sigma, pb, nx, ny)

        disp = float(np.linalg.norm(self.pos - self.prev_pos))
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


def run_density(nx, ny, steps, dt, D, alpha, separation,
                pump_A, ratio, void_lambda, X, Y,
                kappa_drain, rng_seed=42):
    """Run one density configuration with frozen kappa_drain."""
    rng = np.random.RandomState(rng_seed)
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    phi = np.zeros((nx, ny))
    probe_hits = np.zeros((nx, ny))

    # Lambda field with current void density
    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny // 2)**2
    lam -= 0.08 * np.exp(-r2g / (2 * 18.0**2))
    lam = np.maximum(lam, 0.001)

    probes = [PhaseProbe(i + 1, i * 5) for i in range(12)]
    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95

    ts_bruce = []
    ts_chi_op = []
    ts_xi = []
    total_bled = 0.0
    total_scooped = 0.0

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

        step_bleed = 0.0
        for p in probes:
            jump, bleed = p.update(com, pa, pb, step, sigma,
                                   nx, ny, rng, probe_hits,
                                   kappa_drain)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx - 1))
                iy = int(np.clip(p.pos[1], 0, ny - 1))
                bruce_field[ix, iy] += jump * 0.1
            step_bleed += bleed
        bruce_field *= bruce_decay
        total_bled += step_bleed

        bruce_e = float(np.sum(bruce_field**2))
        ts_bruce.append(bruce_e)

        # Chi_op diagnostic (every 50 steps to save time)
        if step % 50 == 0:
            chi_mag = compute_chi_operator(phi)
            gp_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
            gp_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
            xi = float(np.sum(phi**2 + gp_x**2 + gp_y**2))
            ts_chi_op.append(chi_mag)
            ts_xi.append(xi)

    # Compute growth rate
    n = len(ts_bruce)
    skip = 100
    rate = 0
    if n > skip * 2:
        steps_fit = np.arange(skip, n, dtype=float)
        rate = np.polyfit(steps_fit,
                          ts_bruce[skip:], 1)[0]

    # Total scooped by all probes
    for p in probes:
        total_scooped += p.total_bled

    phi_rms = float(np.sqrt(np.mean(phi**2)))
    bruce_rms = float(np.sqrt(np.mean(bruce_field**2)))

    chi_late = ts_chi_op[-1] if ts_chi_op else 0
    xi_late = ts_xi[-1] if ts_xi else 0

    return {
        "growth_rate": round(rate, 8),
        "bruce_rms": round(bruce_rms, 8),
        "phi_rms": round(phi_rms, 8),
        "chi_op_late": round(chi_late, 6),
        "xi_late": round(xi_late, 4),
        "total_bled": round(total_bled, 4),
        "final_sigma": round(float(np.sum(sigma)), 4),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v19.3 Navigational Drain")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--grid", type=int, default=256)
    parser.add_argument("--kappa", type=float, default=0.35,
                        help="Frozen kappa_drain constant")
    args = parser.parse_args()
    nx = ny = args.grid
    kappa = args.kappa

    print(f"\n{'='*65}")
    print(f"  BCM v19.3 -- NAVIGATIONAL DRAIN")
    print(f"  Frozen kappa_drain = {kappa}")
    print(f"  Sweep substrate density to find envelope")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"  kappa_drain: {kappa} (FROZEN)")
    print(f"  Probe cycle: 50 steps (5/35/10)")
    print(f"  Bleed at: deposit boundaries (B1/B2)")

    dt = 0.05; D = 0.5
    pump_A = 0.5; ratio = 0.25; alpha = 0.80
    separation = 15.0

    x_arr = np.arange(nx); y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    # Substrate density sweep: 10x range
    # Same range as v14/v15 graveyard tests
    densities = [0.02, 0.04, 0.06, 0.08, 0.10,
                 0.12, 0.15, 0.20]

    # Also run baseline (no drain, standard density)
    print(f"\n  {'─'*55}")
    print(f"  BASELINE: kappa_drain=0.0, lambda=0.10")
    print(f"  {'─'*55}")
    baseline = run_density(
        nx, ny, args.steps, dt, D, alpha, separation,
        pump_A, ratio, 0.10, X, Y, kappa_drain=0.0)
    print(f"  Growth rate: {baseline['growth_rate']:.8f}")
    print(f"  Bruce RMS:   {baseline['bruce_rms']:.8f}")
    print(f"  Phi RMS:     {baseline['phi_rms']:.8f}")
    print(f"  Total bled:  {baseline['total_bled']:.4f}")

    envelope = []

    for lam_val in densities:
        print(f"\n  {'─'*55}")
        print(f"  lambda={lam_val:.2f}  kappa_drain={kappa}")
        print(f"  {'─'*55}")

        result = run_density(
            nx, ny, args.steps, dt, D, alpha, separation,
            pump_A, ratio, lam_val, X, Y,
            kappa_drain=kappa)

        # Classify operating zone
        rate = result["growth_rate"]
        if rate < -1e-6:
            zone = "GREEN"
        elif rate < 1e-6:
            zone = "YELLOW"
        elif rate < baseline["growth_rate"] * 0.5:
            zone = "ORANGE"
        else:
            zone = "RED"

        entry = {
            "lambda": lam_val,
            "kappa_drain": kappa,
            **result,
            "zone": zone,
        }
        envelope.append(entry)

        red = 0
        if baseline["growth_rate"] > 0:
            red = (1 - rate / baseline["growth_rate"]) * 100

        print(f"  Growth rate: {rate:.8f}  [{zone}]")
        print(f"  Reduction:   {red:.1f}% vs baseline")
        print(f"  Bruce RMS:   {result['bruce_rms']:.8f}")
        print(f"  Phi RMS:     {result['phi_rms']:.8f}")
        print(f"  Chi_op:      {result['chi_op_late']:.6f}")
        print(f"  Xi late:     {result['xi_late']:.4f}")
        print(f"  Total bled:  {result['total_bled']:.4f}")

    # ---- ENVELOPE TABLE ----
    print(f"\n{'='*65}")
    print(f"  NAVIGATIONAL ENVELOPE")
    print(f"  kappa_drain = {kappa} (FROZEN)")
    print(f"{'='*65}")

    print(f"\n  {'Lambda':>8} {'Rate':>12} {'BruceRMS':>10} "
          f"{'Bled':>10} {'ChiOp':>10} {'Zone':>8}")
    print(f"  {'-'*8} {'-'*12} {'-'*10} {'-'*10} "
          f"{'-'*10} {'-'*8}")

    for e in envelope:
        print(f"  {e['lambda']:>8.2f} {e['growth_rate']:>12.8f} "
              f"{e['bruce_rms']:>10.6f} "
              f"{e['total_bled']:>10.2f} "
              f"{e['chi_op_late']:>10.6f} "
              f"{e['zone']:>8}")

    # Find boundaries
    greens = [e for e in envelope if e["zone"] == "GREEN"]
    yellows = [e for e in envelope if e["zone"] == "YELLOW"]

    print(f"\n  Operating envelope:")
    if greens:
        g_min = min(e["lambda"] for e in greens)
        g_max = max(e["lambda"] for e in greens)
        print(f"    GREEN (negative growth): "
              f"lambda {g_min:.2f} - {g_max:.2f}")
    else:
        print(f"    GREEN: none found at kappa={kappa}")
    if yellows:
        y_min = min(e["lambda"] for e in yellows)
        y_max = max(e["lambda"] for e in yellows)
        print(f"    YELLOW (near zero):      "
              f"lambda {y_min:.2f} - {y_max:.2f}")

    # Best density
    best = min(envelope, key=lambda e: e["growth_rate"])
    print(f"\n  Best density:  lambda={best['lambda']:.2f}")
    print(f"  Best rate:     {best['growth_rate']:.8f}")
    print(f"  Best zone:     {best['zone']}")
    print(f"{'='*65}")

    # ---- SAVE JSON ----
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v19_navigational_drain_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v19.3 Navigational Drain",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Frozen kappa_drain constant with "
                     "substrate density sweep to find "
                     "Brucetron operating envelope"),
        "grid": nx, "steps": args.steps,
        "kappa_drain": kappa,
        "kappa_drain_status": "FROZEN",
        "probe_cycle": "50 steps (5/35/10)",
        "bleed_location": "deposit boundaries (B1/B2)",
        "baseline": baseline,
        "envelope": envelope,
        "best_density": best["lambda"],
        "best_rate": best["growth_rate"],
        "best_zone": best["zone"],
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
