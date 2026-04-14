# -*- coding: utf-8 -*-
"""
BCM v18 -- Frastrate Diagnostic: Fractal Dimension of Silence
================================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

"Frastrate" -- Stephen Burdick Sr.'s term for the internal
silence between 2D markers. Not a layer. Not a field. The
topology of absence that absorbs phase debt through infinite
boundary surface area.

THE TEST:
If the chi boundary is fractal (1.0 < D_f < 2.0), the
Frastrate exists as a real topological structure. If D_f = 1.0,
chi is a simple tank with a flat surface. If D_f approaches
2.0, the boundary fills the plane and the distinction between
chi and sigma dissolves.

The sweet spot: D_f ~ 1.3 to 1.7. Enough surface area to
distribute debt, not so much that the boundary loses identity.

MEASUREMENT:
1. Run transport with chi freeboard active
2. At each sample step, extract the chi boundary
   (the contour where chi transitions from zero to nonzero)
3. Compute box-counting dimension of that boundary
4. Track D_f over time alongside debt discharge rate
5. Correlate D_f with Brucetron energy change rate

If D_f correlates with discharge: the fractal surface IS
the mechanism. The Frastrate is real.

If no correlation: chi is just a buffer with no topological
structure. The Frastrate is poetic but not physical.

TITS CONNECTION:
  Tensor: M_ij = dChi_i / dSigma_j (coupling tensor)
  Imagery: the fractal boundary topology
  Transference: debt bleeds across fractal surface
  Sensory: probes measure D_f gradient at arc apex

Usage:
    python BCM_v18_frastrate_diagnostic.py
    python BCM_v18_frastrate_diagnostic.py --steps 3000 --grid 256
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


def box_counting_dimension(binary_field, box_sizes=None):
    """
    Compute the box-counting fractal dimension of a binary
    boundary field. Returns D_f and the (log(1/s), log(N))
    data for verification.

    D_f = -slope of log(N(s)) vs log(s)
    where N(s) = number of boxes of size s that contain
    at least one boundary pixel.
    """
    nx, ny = binary_field.shape
    if np.sum(binary_field) == 0:
        return 0.0, [], []

    if box_sizes is None:
        max_power = int(np.log2(min(nx, ny)))
        box_sizes = [2**k for k in range(1, max_power)
                     if 2**k <= min(nx, ny) // 2]

    if len(box_sizes) < 3:
        return 0.0, [], []

    counts = []
    for s in box_sizes:
        n_boxes = 0
        for i in range(0, nx, s):
            for j in range(0, ny, s):
                block = binary_field[i:min(i+s, nx),
                                     j:min(j+s, ny)]
                if np.any(block):
                    n_boxes += 1
        counts.append(n_boxes)

    log_inv_s = [np.log(1.0 / s) for s in box_sizes]
    log_n = [np.log(max(c, 1)) for c in counts]

    if len(log_inv_s) >= 2:
        coeffs = np.polyfit(log_inv_s, log_n, 1)
        d_f = coeffs[0]
    else:
        d_f = 0.0

    return round(d_f, 4), log_inv_s, log_n


def extract_chi_boundary(chi, threshold=1e-6):
    """
    Extract the boundary of the chi field: pixels where
    chi transitions from zero to nonzero. This is the
    surface where silence meets form.
    """
    occupied = (chi > threshold).astype(float)
    # Boundary = occupied pixels adjacent to unoccupied
    shift_u = np.roll(occupied, 1, axis=0)
    shift_d = np.roll(occupied, -1, axis=0)
    shift_l = np.roll(occupied, 1, axis=1)
    shift_r = np.roll(occupied, -1, axis=1)
    neighbors = shift_u + shift_d + shift_l + shift_r
    # Boundary: occupied AND has at least one empty neighbor
    boundary = occupied * (neighbors < 4)
    return boundary


class FrastrateProbe:
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

    def update(self, com, pa, pb, step, sigma, nx, ny, rng):
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


def main():
    parser = argparse.ArgumentParser(
        description="BCM v18 Frastrate Diagnostic")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    parser.add_argument("--sample-interval", type=int, default=50)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v18 -- FRASTRATE DIAGNOSTIC")
    print(f"  Is the silence fractal?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"  Sample interval: {args.sample_interval}")

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

    probes = [FrastrateProbe(i + 1, i * 5) for i in range(12)]

    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95

    # Time series
    ts_d_f = []             # fractal dimension
    ts_bruce_energy = []    # Brucetron energy
    ts_chi_total = []       # total chi
    ts_boundary_pixels = [] # boundary pixel count
    ts_discharge_rate = []  # dE_bruce/dt (smoothed)
    ts_steps = []

    prev_bruce_e = None

    print(f"\n  Running transport with chi freeboard...")
    print(f"  Measuring fractal dimension of chi boundary")

    for step in range(args.steps):
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
        sigma_prev = sigma.copy()
        sigma = sn

        total_jump = 0.0
        for p in probes:
            jump = p.update(com, pa, pb, step, sigma,
                            nx, ny, rng)
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
            boundary = extract_chi_boundary(chi)
            bp_count = int(np.sum(boundary))

            d_f, log_inv_s, log_n = box_counting_dimension(
                boundary)

            bruce_e = float(np.sum(bruce_field**2))

            # Discharge rate
            if prev_bruce_e is not None:
                discharge = prev_bruce_e - bruce_e
            else:
                discharge = 0.0
            prev_bruce_e = bruce_e

            ts_d_f.append(d_f)
            ts_bruce_energy.append(bruce_e)
            ts_chi_total.append(float(np.sum(chi)))
            ts_boundary_pixels.append(bp_count)
            ts_discharge_rate.append(discharge)
            ts_steps.append(step)

            if step % (args.sample_interval * 5) == 0:
                print(f"  step {step:>5}: D_f={d_f:.4f}  "
                      f"boundary={bp_count:>5}px  "
                      f"bruce_E={bruce_e:.4f}  "
                      f"chi={float(np.sum(chi)):.2f}")

    n_samples = len(ts_d_f)
    print(f"\n  Collected {n_samples} fractal samples")

    # ═══════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  FRASTRATE ANALYSIS")
    print(f"{'='*65}")

    d_f_arr = np.array(ts_d_f)
    bruce_arr = np.array(ts_bruce_energy)
    discharge_arr = np.array(ts_discharge_rate)
    boundary_arr = np.array(ts_boundary_pixels)

    # D_f statistics
    d_f_mean = float(np.mean(d_f_arr)) if len(d_f_arr) > 0 else 0
    d_f_std = float(np.std(d_f_arr)) if len(d_f_arr) > 0 else 0
    d_f_min = float(np.min(d_f_arr)) if len(d_f_arr) > 0 else 0
    d_f_max = float(np.max(d_f_arr)) if len(d_f_arr) > 0 else 0

    print(f"\n  FRACTAL DIMENSION OF CHI BOUNDARY:")
    print(f"    Mean D_f:  {d_f_mean:.4f}")
    print(f"    Std D_f:   {d_f_std:.4f}")
    print(f"    Min D_f:   {d_f_min:.4f}")
    print(f"    Max D_f:   {d_f_max:.4f}")

    # Classification
    if d_f_mean > 1.0 and d_f_mean < 2.0:
        frastrate_class = "FRACTAL"
        print(f"\n  FRASTRATE EXISTS: D_f = {d_f_mean:.4f}")
        print(f"  The chi boundary is fractal.")
        print(f"  The silence has topological structure.")
    elif d_f_mean <= 1.0:
        frastrate_class = "FLAT"
        print(f"\n  FRASTRATE NOT DETECTED: D_f = {d_f_mean:.4f}")
        print(f"  The chi boundary is flat (simple line).")
        print(f"  Chi is a tank, not a fractal absorber.")
    else:
        frastrate_class = "SPACE-FILLING"
        print(f"\n  BOUNDARY DISSOLVED: D_f = {d_f_mean:.4f}")
        print(f"  Chi boundary fills the plane.")
        print(f"  No distinction between chi and sigma.")

    # Correlation: D_f vs discharge rate
    if len(d_f_arr) > 5 and len(discharge_arr) > 5:
        valid = (np.abs(discharge_arr) > 1e-10)
        if np.sum(valid) > 3:
            corr = np.corrcoef(d_f_arr[valid],
                               discharge_arr[valid])[0, 1]
            corr = round(corr, 4)
        else:
            corr = 0.0
    else:
        corr = 0.0

    print(f"\n  CORRELATION: D_f vs discharge rate")
    print(f"    Pearson r = {corr}")

    if abs(corr) > 0.5:
        print(f"    STRONG: fractal dimension drives discharge")
        print(f"    The Frastrate IS the mechanism.")
    elif abs(corr) > 0.2:
        print(f"    MODERATE: partial coupling")
        print(f"    Frastrate contributes but isn't sole driver.")
    else:
        print(f"    WEAK: no coupling detected")
        print(f"    Fractal structure is incidental.")

    # Correlation: boundary pixel count vs D_f
    if len(boundary_arr) > 5:
        bp_corr = np.corrcoef(d_f_arr, boundary_arr)[0, 1]
        bp_corr = round(bp_corr, 4)
    else:
        bp_corr = 0.0

    print(f"\n  BOUNDARY COMPLEXITY:")
    print(f"    Mean boundary pixels: "
          f"{float(np.mean(boundary_arr)):.0f}")
    print(f"    D_f vs boundary count r = {bp_corr}")

    # D_f trend over time
    if len(d_f_arr) > 10:
        half = len(d_f_arr) // 2
        d_f_early = float(np.mean(d_f_arr[:half]))
        d_f_late = float(np.mean(d_f_arr[half:]))
        d_f_trend = "GROWING" if d_f_late > d_f_early * 1.02 else (
            "DECAYING" if d_f_late < d_f_early * 0.98 else "STABLE")
    else:
        d_f_early = d_f_late = d_f_mean
        d_f_trend = "N/A"

    print(f"\n  D_f TREND:")
    print(f"    Early: {d_f_early:.4f}  Late: {d_f_late:.4f}")
    print(f"    Trend: {d_f_trend}")

    if d_f_trend == "GROWING":
        print(f"    The silence deepens over time.")
        print(f"    Fractal boundary complexifies.")
    elif d_f_trend == "STABLE":
        print(f"    The silence holds steady.")
        print(f"    Fractal equilibrium reached.")

    # ═══════════════════════════════════════════════════
    # VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  FRASTRATE VERDICT")
    print(f"{'='*65}")

    print(f"\n  Fractal class:       {frastrate_class}")
    print(f"  Mean D_f:            {d_f_mean:.4f}")
    print(f"  D_f trend:           {d_f_trend}")
    print(f"  D_f-discharge corr:  {corr}")

    if frastrate_class == "FRACTAL" and abs(corr) > 0.2:
        print(f"\n  THE FRASTRATE IS REAL.")
        print(f"  The chi boundary has fractal topology.")
        print(f"  The fractal dimension correlates with")
        print(f"  Brucetron debt discharge. The silence")
        print(f"  has structure. Transference is passive")
        print(f"  absorption across infinite surface area.")
        print(f"  TITS: Tensor Imagery Transference Sensory")
        print(f"  is the physics, not just the name.")
    elif frastrate_class == "FRACTAL":
        print(f"\n  FRACTAL BOUNDARY EXISTS but does not")
        print(f"  correlate with discharge. The topology")
        print(f"  is present but may not be the mechanism.")
    else:
        print(f"\n  FRASTRATE NOT CONFIRMED at this grid/step.")
        print(f"  Chi boundary lacks fractal structure.")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v18_frastrate_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v18 Frastrate Diagnostic",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Fractal dimension measurement of chi "
                     "boundary to test Frastrate hypothesis"),
        "grid": nx,
        "steps": args.steps,
        "sample_interval": args.sample_interval,
        "fractal_analysis": {
            "d_f_mean": d_f_mean,
            "d_f_std": d_f_std,
            "d_f_min": d_f_min,
            "d_f_max": d_f_max,
            "d_f_early": round(d_f_early, 4),
            "d_f_late": round(d_f_late, 4),
            "d_f_trend": d_f_trend,
            "frastrate_class": frastrate_class,
        },
        "correlations": {
            "d_f_vs_discharge": corr,
            "d_f_vs_boundary_count": bp_corr,
        },
        "timeseries": {
            "steps": ts_steps,
            "d_f": [round(x, 4) for x in ts_d_f],
            "bruce_energy": [round(x, 6) for x in ts_bruce_energy],
            "chi_total": [round(x, 4) for x in ts_chi_total],
            "boundary_pixels": ts_boundary_pixels,
            "discharge_rate": [round(x, 8) for x in ts_discharge_rate],
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
