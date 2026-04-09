# -*- coding: utf-8 -*-
"""
BCM v18 -- Frastrate Diagnostic v2: Causal Frontier
======================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

v1 measured the chi tank boundary. D_f = 0.88. Wrong
boundary. Chi is a smooth buffer — of course it's flat.

The Frastrate isn't chi vs sigma. It's ACTIVATED vs
LATENT. Where causality has touched vs where it hasn't.
The grid isn't pre-built — it's written by interaction.

"Space looks substrate until an event causes the
causality to become substrate observer in grid."
-- Stephen Burdick Sr.

THE CAUSAL FRONTIER:
Every grid cell the craft has ever activated:
  - Probe touched it (arc trajectory)
  - Pump injected into it (sigma > threshold)
  - Wake passed through it (sigma memory)

The boundary of that activation map is the Frastrate
surface — the edge of the craft's causal universe.
The 12 probes trace irregular polygonal paths at
different phases, radii, scoop depths. That boundary
SHOULD be fractal because the activation pattern is
self-similar at multiple scales.

THREE BOUNDARIES MEASURED:
  1. Causal frontier (activation map edge)
  2. Probe trajectory boundary (arc paths only)
  3. Chi boundary (v1 comparison)

If the causal frontier D_f > 1.0 while chi D_f < 1.0,
the Frastrate lives at the observation boundary, not
the pressure relief boundary.

Usage:
    python BCM_v18_frastrate_v2.py
    python BCM_v18_frastrate_v2.py --steps 3000 --grid 256
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


def box_counting_dimension(binary_field):
    nx, ny = binary_field.shape
    if np.sum(binary_field) < 5:
        return 0.0

    max_power = int(np.log2(min(nx, ny)))
    box_sizes = [2**k for k in range(1, max_power)
                 if 2**k <= min(nx, ny) // 2]

    if len(box_sizes) < 3:
        return 0.0

    counts = []
    for s in box_sizes:
        n_boxes = 0
        for i in range(0, nx, s):
            for j in range(0, ny, s):
                block = binary_field[i:min(i + s, nx),
                                     j:min(j + s, ny)]
                if np.any(block):
                    n_boxes += 1
        counts.append(n_boxes)

    log_inv_s = [np.log(1.0 / s) for s in box_sizes]
    log_n = [np.log(max(c, 1)) for c in counts]

    if len(log_inv_s) >= 2:
        d_f = np.polyfit(log_inv_s, log_n, 1)[0]
    else:
        d_f = 0.0

    return round(d_f, 4)


def extract_boundary(occupied_field):
    occupied = (occupied_field > 0).astype(float)
    if np.sum(occupied) < 2:
        return np.zeros_like(occupied)
    shift_u = np.roll(occupied, 1, axis=0)
    shift_d = np.roll(occupied, -1, axis=0)
    shift_l = np.roll(occupied, 1, axis=1)
    shift_r = np.roll(occupied, -1, axis=1)
    neighbors = shift_u + shift_d + shift_l + shift_r
    boundary = occupied * (neighbors < 4)
    return boundary


class CausalProbe:
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
               activation_map, probe_map):
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
            # Mark probe trajectory on BOTH maps
            ix = int(np.clip(self.pos[0], 0, nx - 1))
            iy = int(np.clip(self.pos[1], 0, ny - 1))
            activation_map[ix, iy] = 1
            probe_map[ix, iy] = 1
        else:
            self.state = "FALLING"
            fs = self.cycle_step - b2
            tf = fs / self.t_fall
            self.pos = self.prev_pos + tf * (pb - self.prev_pos)
            if fs >= self.t_fall - 1:
                self._deposit(sigma, pb, nx, ny, activation_map)
        # Mark current position as activated
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
        # Mark scoop region as causally activated
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


def main():
    parser = argparse.ArgumentParser(
        description="BCM v18 Frastrate v2: Causal Frontier")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    parser.add_argument("--sample-interval", type=int, default=50)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v18 -- FRASTRATE v2: CAUSAL FRONTIER")
    print(f"  Is the observation boundary fractal?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    dt = 0.05; D = 0.5; void_lambda = 0.10
    pump_A = 0.5; ratio = 0.25; alpha = 0.80
    separation = 15.0

    rng = np.random.RandomState(42)
    x_arr = np.arange(nx); y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny // 2)**2
    lam -= 0.08 * np.exp(-r2g / (2 * 18.0**2))
    lam = np.maximum(lam, 0.001)

    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    chi = np.zeros((nx, ny))
    drain_rate = 0.1
    spill_rate = 0.5

    probes = [CausalProbe(i + 1, i * 5) for i in range(12)]

    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95

    # THREE ACTIVATION MAPS
    # 1. Full causal map: everything the craft has touched
    activation_map = np.zeros((nx, ny))
    # 2. Probe-only map: just arc trajectories
    probe_map = np.zeros((nx, ny))
    # 3. Sigma threshold map: where sigma ever exceeded noise
    sigma_ever = np.zeros((nx, ny))

    sigma_threshold = 0.001  # above this = causally activated

    ts_d_f_causal = []
    ts_d_f_probe = []
    ts_d_f_chi = []
    ts_d_f_sigma = []
    ts_bruce_energy = []
    ts_activated_pct = []
    ts_boundary_causal = []
    ts_boundary_probe = []
    ts_steps = []

    prev_bruce_e = None
    ts_discharge = []

    print(f"\n  Running transport with causal frontier tracking...")

    for step in range(args.steps):
        com = compute_com(sigma)
        if com is None:
            break

        pa = np.array([com[0] + separation, com[1]])
        pb = np.array([com[0] - separation * 0.3, com[1]])

        r2A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2A / (2 * 4.0**2))
        sigma += pA * dt

        # Mark pump injection zones as activated
        pump_mask = (pA * dt > sigma_threshold)
        activation_map[pump_mask] = 1

        bx = com[0] + separation
        r2B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_A * ratio * np.exp(-r2B / (2 * 3.0**2))
        sigma += pB * dt

        pump_mask_b = (pB * dt > sigma_threshold)
        activation_map[pump_mask_b] = 1

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

        # Track sigma activation
        sigma_ever = np.maximum(sigma_ever,
                                (sigma > sigma_threshold).astype(float))

        total_jump = 0.0
        for p in probes:
            jump = p.update(com, pa, pb, step, sigma,
                            nx, ny, rng,
                            activation_map, probe_map)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx - 1))
                iy = int(np.clip(p.pos[1], 0, ny - 1))
                bruce_field[ix, iy] += jump * 0.1
                total_jump += jump
        bruce_field *= bruce_decay

        # Chi freeboard
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
        available_drain = np.minimum(chi * drain_rate, deficit)
        sigma += available_drain
        chi -= available_drain
        chi *= 0.999

        bruce_in_chi = bruce_field * 0.05
        chi += bruce_in_chi * 0.01
        bruce_field -= bruce_in_chi
        bruce_field = np.maximum(bruce_field, 0)

        # ── FRACTAL MEASUREMENT ──
        if step % args.sample_interval == 0 and step > 0:
            # Boundary 1: full causal frontier
            b_causal = extract_boundary(activation_map)
            d_f_causal = box_counting_dimension(b_causal)
            bp_causal = int(np.sum(b_causal))

            # Boundary 2: probe trajectory only
            b_probe = extract_boundary(probe_map)
            d_f_probe = box_counting_dimension(b_probe)
            bp_probe = int(np.sum(b_probe))

            # Boundary 3: chi field
            b_chi = extract_boundary((chi > 1e-6).astype(float))
            d_f_chi = box_counting_dimension(b_chi)

            # Boundary 4: sigma activation
            b_sigma = extract_boundary(sigma_ever)
            d_f_sigma = box_counting_dimension(b_sigma)

            bruce_e = float(np.sum(bruce_field**2))
            activated_pct = float(np.sum(activation_map)) / (nx * ny) * 100

            if prev_bruce_e is not None:
                discharge = prev_bruce_e - bruce_e
            else:
                discharge = 0.0
            prev_bruce_e = bruce_e

            ts_d_f_causal.append(d_f_causal)
            ts_d_f_probe.append(d_f_probe)
            ts_d_f_chi.append(d_f_chi)
            ts_d_f_sigma.append(d_f_sigma)
            ts_bruce_energy.append(bruce_e)
            ts_activated_pct.append(activated_pct)
            ts_boundary_causal.append(bp_causal)
            ts_boundary_probe.append(bp_probe)
            ts_steps.append(step)
            ts_discharge.append(discharge)

            if step % (args.sample_interval * 5) == 0:
                print(f"  step {step:>5}: "
                      f"D_causal={d_f_causal:.4f} "
                      f"D_probe={d_f_probe:.4f} "
                      f"D_chi={d_f_chi:.4f} "
                      f"D_sigma={d_f_sigma:.4f} "
                      f"active={activated_pct:.1f}%")

    n_samples = len(ts_d_f_causal)
    print(f"\n  Collected {n_samples} samples")

    # ═══════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  CAUSAL FRONTIER ANALYSIS")
    print(f"{'='*65}")

    boundaries = {
        "causal_frontier": np.array(ts_d_f_causal),
        "probe_trajectory": np.array(ts_d_f_probe),
        "chi_boundary": np.array(ts_d_f_chi),
        "sigma_activation": np.array(ts_d_f_sigma),
    }

    print(f"\n  {'Boundary':>20} {'Mean D_f':>10} {'Std':>8} "
          f"{'Min':>8} {'Max':>8} {'Class':>12}")
    print(f"  {'-'*20} {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*12}")

    results = {}
    for name, arr in boundaries.items():
        if len(arr) > 0:
            m = float(np.mean(arr))
            s = float(np.std(arr))
            mn = float(np.min(arr))
            mx = float(np.max(arr))
            cls = ("FRACTAL" if m > 1.0 and m < 2.0 else
                   "FLAT" if m <= 1.0 else "SPACE-FILLING")
        else:
            m = s = mn = mx = 0
            cls = "N/A"

        results[name] = {
            "mean": round(m, 4), "std": round(s, 4),
            "min": round(mn, 4), "max": round(mx, 4),
            "class": cls
        }

        print(f"  {name:>20} {m:>10.4f} {s:>8.4f} "
              f"{mn:>8.4f} {mx:>8.4f} {cls:>12}")

    # Correlation: each D_f vs discharge rate
    discharge_arr = np.array(ts_discharge)
    print(f"\n  CORRELATION WITH DISCHARGE RATE:")
    correlations = {}
    for name, arr in boundaries.items():
        if len(arr) > 5 and len(discharge_arr) > 5:
            valid = np.abs(discharge_arr) > 1e-12
            if np.sum(valid) > 3:
                r = np.corrcoef(arr[valid],
                                discharge_arr[valid])[0, 1]
                r = round(r, 4) if not np.isnan(r) else 0.0
            else:
                r = 0.0
        else:
            r = 0.0
        correlations[name] = r
        strength = ("STRONG" if abs(r) > 0.5 else
                    "MODERATE" if abs(r) > 0.2 else "WEAK")
        print(f"    {name:>20}: r = {r:>7.4f}  ({strength})")

    # Activation coverage
    final_activated = float(np.sum(activation_map)) / (nx * ny) * 100
    final_probe = float(np.sum(probe_map)) / (nx * ny) * 100
    print(f"\n  ACTIVATION COVERAGE:")
    print(f"    Full causal:     {final_activated:.1f}% of grid")
    print(f"    Probe only:      {final_probe:.1f}% of grid")
    print(f"    Causal boundary: {ts_boundary_causal[-1] if ts_boundary_causal else 0} px")
    print(f"    Probe boundary:  {ts_boundary_probe[-1] if ts_boundary_probe else 0} px")

    # ═══════════════════════════════════════════════════
    # VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  FRASTRATE VERDICT (v2 — CAUSAL FRONTIER)")
    print(f"{'='*65}")

    # Find the boundary with highest D_f
    best_name = max(results.keys(),
                    key=lambda k: results[k]["mean"])
    best = results[best_name]
    best_corr = correlations.get(best_name, 0)

    print(f"\n  Highest D_f boundary: {best_name}")
    print(f"  Mean D_f:            {best['mean']:.4f}")
    print(f"  Class:               {best['class']}")
    print(f"  Discharge corr:      {best_corr:.4f}")

    # The test
    if best["class"] == "FRACTAL":
        print(f"\n  THE FRASTRATE IS REAL.")
        print(f"  The {best_name} has fractal dimension")
        print(f"  {best['mean']:.4f} — between line (1.0)")
        print(f"  and plane (2.0).")
        if abs(best_corr) > 0.2:
            print(f"  AND it correlates with debt discharge.")
            print(f"  The fractal boundary IS the mechanism.")
        else:
            print(f"  Discharge correlation is weak.")
            print(f"  Topology exists but mechanism unconfirmed.")
    else:
        # Check if probe boundary is more complex than chi
        d_probe = results["probe_trajectory"]["mean"]
        d_chi = results["chi_boundary"]["mean"]
        d_causal = results["causal_frontier"]["mean"]

        if d_probe > d_chi or d_causal > d_chi:
            print(f"\n  PARTIAL FRASTRATE DETECTED.")
            print(f"  Probe/causal boundary ({max(d_probe, d_causal):.4f})")
            print(f"  exceeds chi boundary ({d_chi:.4f}).")
            print(f"  The observation surface is more complex")
            print(f"  than the pressure relief surface.")
            print(f"  The Frastrate emerges from interaction,")
            print(f"  not from containment.")
        else:
            print(f"\n  FRASTRATE NOT CONFIRMED.")
            print(f"  All boundaries are flat (D_f < 1.0).")
            print(f"  May require higher grid resolution or")
            print(f"  irregular polygonal probe trajectories.")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v18_frastrate_v2_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v18 Frastrate v2: Causal Frontier",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Fractal dimension of causal frontier vs "
                     "chi boundary vs probe trajectory"),
        "grid": nx, "steps": args.steps,
        "boundaries": results,
        "correlations": correlations,
        "activation_coverage": {
            "causal_pct": round(final_activated, 2),
            "probe_pct": round(final_probe, 2),
        },
        "timeseries": {
            "steps": ts_steps,
            "d_f_causal": [round(x, 4) for x in ts_d_f_causal],
            "d_f_probe": [round(x, 4) for x in ts_d_f_probe],
            "d_f_chi": [round(x, 4) for x in ts_d_f_chi],
            "d_f_sigma": [round(x, 4) for x in ts_d_f_sigma],
            "bruce_energy": [round(x, 6) for x in ts_bruce_energy],
            "activated_pct": [round(x, 2) for x in ts_activated_pct],
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
