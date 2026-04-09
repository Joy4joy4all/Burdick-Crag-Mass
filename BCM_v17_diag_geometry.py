# -*- coding: utf-8 -*-
"""
BCM v17 -- Diagnostic: Segment Geometry Sweep
================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Three segment geometries tested inside the 50-step locked
cycle. The data decides which produces the cleanest spectrum.

  Config A: 5:35:10  (current locked -- asymmetric)
  Config B: 10:30:10 (symmetric entry/exit)
  Config C: 5:30:15  (ChatGPT candidate -- extended fall)

Metrics per configuration:
  1. Closure defect: count of ghost frequencies (beat
     products not in the harmonic ladder)
  2. Spectral entropy: H = -sum(p*log(p)) over power
     spectrum. Low = clean. High = noisy.
  3. Dominant mode count: how many modes carry >5% power
  4. Ghost power ratio: total power in ghosts / total power
  5. Harmonic purity: power in exact harmonics of f_probe
     / total power

Kill condition: the geometry with lowest spectral entropy
and fewest ghosts is the winner. If all three show ghosts,
the segment architecture itself needs redesign.

Usage:
    python BCM_v17_diag_geometry.py
    python BCM_v17_diag_geometry.py --steps 3000 --grid 256
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


# ═══════════════════════════════════════════════════════
# TRANSPORT PROBE (configurable segment timing)
# ═══════════════════════════════════════════════════════

class GeomProbe:
    def __init__(self, pid, eject_offset, t_transit, t_arc,
                 t_fall, scoop_eff=0.05, scoop_r=2.0):
        self.pid = pid
        self.eject_offset = eject_offset
        self.scoop_eff = scoop_eff
        self.scoop_r = scoop_r
        self.pos = np.array([0.0, 0.0])
        self.state = "TRANSIT"
        self.cycle_step = 0
        self.cycles = 0
        self.payload = 0.0
        self.t_transit = t_transit
        self.t_arc = t_arc
        self.t_fall = t_fall

    def update(self, com, pa, pb, step, sigma, nx, ny, rng):
        eff = step - self.eject_offset
        if eff < 0:
            self.pos = com.copy()
            return
        cl = self.t_transit + self.t_arc + self.t_fall
        prev = self.cycles
        self.cycle_step = eff % cl
        self.cycles = eff // cl

        if self.cycles > prev and self.payload > 0:
            self._deposit(sigma, pb, nx, ny)

        if self.cycle_step < self.t_transit:
            self.state = "TRANSIT"
            t = self.cycle_step / self.t_transit
            self.pos = pb + t * (pa - pb)
        elif self.cycle_step < self.t_transit + self.t_arc:
            self.state = "EJECTED"
            as_ = self.cycle_step - self.t_transit
            bao = rng.uniform(-0.8, 0.8)
            vc = 5 + (self.cycles % 4)
            ta = as_ / self.t_arc
            amr = 40.0 + rng.uniform(-10, 15)
            if ta < 0.5:
                ar = amr * (ta * 2)
            else:
                ar = amr * (2 - ta * 2)
            ca = bao + ta * 2 * math.pi
            va = round(ca/(2*math.pi/vc)) * (2*math.pi/vc)
            aa = 0.3*ca + 0.7*va
            self.pos = np.array([
                pa[0] + ar*np.cos(aa),
                pa[1] + ar*np.sin(aa)])
            self._scoop(sigma, nx, ny)
        else:
            self.state = "FALLING"
            fs = self.cycle_step - self.t_transit - self.t_arc
            tf = fs / self.t_fall
            self.pos = self.pos + tf * (pb - self.pos)
            if fs >= self.t_fall - 1:
                self._deposit(sigma, pb, nx, ny)

    def _scoop(self, sigma, nx, ny):
        ix = int(np.clip(self.pos[0], 0, nx-1))
        iy = int(np.clip(self.pos[1], 0, ny-1))
        xa = np.arange(max(0, ix-4), min(nx, ix+5))
        ya = np.arange(max(0, iy-4), min(ny, iy+5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl-self.pos[0])**2 + (Yl-self.pos[1])**2
        w = np.exp(-r2/(2*self.scoop_r**2))
        loc = sigma[np.ix_(xa, ya)]
        sc = np.minimum(loc*w*self.scoop_eff, loc)
        sc = np.maximum(sc, 0)
        sigma[np.ix_(xa, ya)] -= sc
        self.payload += float(np.sum(sc))

    def _deposit(self, sigma, pos, nx, ny):
        if self.payload <= 0:
            return
        ix = int(np.clip(pos[0], 0, nx-1))
        iy = int(np.clip(pos[1], 0, ny-1))
        xa = np.arange(max(0, ix-4), min(nx, ix+5))
        ya = np.arange(max(0, iy-4), min(ny, iy+5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl-pos[0])**2 + (Yl-pos[1])**2
        w = np.exp(-r2/(2*self.scoop_r**2))
        ws = float(np.sum(w))
        if ws > 1e-15:
            sigma[np.ix_(xa, ya)] += w*(self.payload/ws)
        self.payload = 0.0


# ═══════════════════════════════════════════════════════
# RUN ONE CONFIGURATION
# ═══════════════════════════════════════════════════════

def run_config(nx, ny, steps, dt, D, alpha, separation,
               pump_A, ratio, lam, X, Y,
               t_transit, t_arc, t_fall, rng_seed):
    rng = np.random.RandomState(rng_seed)

    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2*5.0**2))
    sigma_prev = sigma.copy()

    probes = [GeomProbe(i+1, i*5, t_transit, t_arc, t_fall)
              for i in range(12)]

    ts_com_vx = []
    ts_sigma_peak = []
    prev_cx = None

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        pa = np.array([com[0] + separation, com[1]])
        pb = np.array([com[0] - separation*0.3, com[1]])

        r2A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2A / (2*4.0**2))
        sigma += pA * dt
        bx = com[0] + separation
        r2B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_A * ratio * np.exp(-r2B / (2*3.0**2))
        sigma += pB * dt

        lap = (np.roll(sigma, 1, 0) + np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) + np.roll(sigma, -1, 1) -
               4*sigma)
        sn = sigma + D*lap*dt - lam*sigma*dt
        if alpha > 0:
            sn += alpha * (sigma - sigma_prev)
        sn = np.maximum(sn, 0)
        if float(np.max(sn)) > 1e10:
            break
        sigma_prev = sigma.copy()
        sigma = sn

        for p in probes:
            p.update(com, pa, pb, step, sigma, nx, ny, rng)

        cx = float(com[0])
        if prev_cx is not None:
            ts_com_vx.append(cx - prev_cx)
        else:
            ts_com_vx.append(0.0)
        prev_cx = cx

        ix_c = int(np.clip(com[0], 0, nx-1))
        iy_c = int(np.clip(com[1], 0, ny-1))
        ts_sigma_peak.append(float(sigma[ix_c, iy_c]))

    return np.array(ts_com_vx), np.array(ts_sigma_peak)


# ═══════════════════════════════════════════════════════
# SPECTRAL ANALYSIS
# ═══════════════════════════════════════════════════════

def analyze_spectrum(signal, f_probe):
    """
    Analyze signal spectrum. Returns metrics dict.
    f_probe: probe fundamental frequency (cycles/step)
    """
    sig_c = signal - np.mean(signal)
    window = np.hanning(len(sig_c))
    sig_w = sig_c * window

    fft_vals = np.fft.rfft(sig_w)
    freqs = np.fft.rfftfreq(len(sig_w), d=1.0)
    power = np.abs(fft_vals)**2
    total_power = float(np.sum(power))

    if total_power < 1e-15:
        return {
            "spectral_entropy": 0,
            "ghost_count": 0,
            "ghost_power_ratio": 0,
            "harmonic_purity": 0,
            "dominant_modes": 0,
            "peaks": [],
        }

    # Normalized power distribution
    p_norm = power / total_power
    p_norm = p_norm[p_norm > 1e-15]
    spectral_entropy = float(-np.sum(p_norm * np.log(p_norm)))

    # Identify peaks (>5% of max)
    power_rel = power / np.max(power) if np.max(power) > 0 else power
    peaks = []
    for i in range(1, len(power_rel) - 1):
        if (power_rel[i] > power_rel[i-1] and
                power_rel[i] > power_rel[i+1] and
                power_rel[i] > 0.05):
            peaks.append({
                "freq": round(float(freqs[i]), 6),
                "power": round(float(power_rel[i]), 6),
                "period": round(1.0/freqs[i], 1) if freqs[i] > 0 else 0,
            })
    peaks.sort(key=lambda p: p["power"], reverse=True)
    peaks = peaks[:15]

    dominant_modes = len([p for p in peaks if p["power"] > 0.05])

    # Classify each peak: harmonic or ghost
    harmonic_tolerance = 0.003
    harmonic_power = 0.0
    ghost_power = 0.0
    ghost_count = 0

    for pk in peaks:
        f = pk["freq"]
        if f < 0.001:
            continue
        # Check if f is a harmonic of f_probe
        ratio = f / f_probe
        nearest_int = round(ratio)
        err = abs(ratio - nearest_int)
        if err < harmonic_tolerance * nearest_int:
            pk["class"] = f"HARMONIC {nearest_int}"
            harmonic_power += pk["power"]
        else:
            pk["class"] = "GHOST"
            ghost_power += pk["power"]
            ghost_count += 1

    total_peak_power = harmonic_power + ghost_power
    harmonic_purity = (harmonic_power / total_peak_power
                       if total_peak_power > 0 else 0)
    ghost_ratio = (ghost_power / total_peak_power
                   if total_peak_power > 0 else 0)

    return {
        "spectral_entropy": round(spectral_entropy, 4),
        "ghost_count": ghost_count,
        "ghost_power_ratio": round(ghost_ratio, 4),
        "harmonic_purity": round(harmonic_purity, 4),
        "dominant_modes": dominant_modes,
        "peaks": peaks[:10],
    }


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v17 Segment Geometry Sweep")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v17 -- SEGMENT GEOMETRY SWEEP")
    print(f"  Which segment ratio produces cleanest spectrum?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"  All configs total 50 steps (pump-locked)")

    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    ratio = 0.25
    alpha = 0.80
    separation = 15.0

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny//2)**2
    lam -= 0.08 * np.exp(-r2g / (2*18.0**2))
    lam = np.maximum(lam, 0.001)

    configs = [
        {"name": "A: 5/35/10 (current)",
         "transit": 5, "arc": 35, "fall": 10},
        {"name": "B: 10/30/10 (symmetric)",
         "transit": 10, "arc": 30, "fall": 10},
        {"name": "C: 5/30/15 (extended fall)",
         "transit": 5, "arc": 30, "fall": 15},
    ]

    f_probe = 1.0 / 50.0  # 0.02 cycles/step

    all_results = []

    for cfg in configs:
        print(f"\n  {'─'*55}")
        print(f"  CONFIG {cfg['name']}")
        print(f"  Transit={cfg['transit']} Arc={cfg['arc']} "
              f"Fall={cfg['fall']} Total=50")
        print(f"  {'─'*55}")

        ts_vx, ts_peak = run_config(
            nx, ny, args.steps, dt, D, alpha, separation,
            pump_A, ratio, lam, X, Y,
            cfg["transit"], cfg["arc"], cfg["fall"],
            rng_seed=42)

        # Analyze both channels
        vx_analysis = analyze_spectrum(ts_vx, f_probe)
        peak_analysis = analyze_spectrum(ts_peak, f_probe)

        result = {
            "config": cfg["name"],
            "segments": {
                "transit": cfg["transit"],
                "arc": cfg["arc"],
                "fall": cfg["fall"],
            },
            "velocity_channel": vx_analysis,
            "sigma_peak_channel": peak_analysis,
        }
        all_results.append(result)

        print(f"\n  VELOCITY CHANNEL:")
        print(f"    Spectral entropy:  "
              f"{vx_analysis['spectral_entropy']:.4f}")
        print(f"    Ghost count:       "
              f"{vx_analysis['ghost_count']}")
        print(f"    Ghost power ratio: "
              f"{vx_analysis['ghost_power_ratio']:.4f}")
        print(f"    Harmonic purity:   "
              f"{vx_analysis['harmonic_purity']:.4f}")
        print(f"    Dominant modes:    "
              f"{vx_analysis['dominant_modes']}")

        print(f"\n    {'Rank':>5} {'Freq':>10} {'Period':>8} "
              f"{'Power':>8} {'Class':>16}")
        print(f"    {'-'*5} {'-'*10} {'-'*8} {'-'*8} {'-'*16}")
        for i, pk in enumerate(vx_analysis["peaks"][:8]):
            cls = pk.get("class", "")
            print(f"    {i+1:>5} {pk['freq']:>10.6f} "
                  f"{pk['period']:>8.1f} {pk['power']:>8.4f} "
                  f"{cls:>16}")

        print(f"\n  SIGMA PEAK CHANNEL:")
        print(f"    Spectral entropy:  "
              f"{peak_analysis['spectral_entropy']:.4f}")
        print(f"    Ghost count:       "
              f"{peak_analysis['ghost_count']}")
        print(f"    Harmonic purity:   "
              f"{peak_analysis['harmonic_purity']:.4f}")

    # ═══════════════════════════════════════════════════
    # COMPARISON
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  GEOMETRY COMPARISON")
    print(f"{'='*65}")

    print(f"\n  {'Config':>25} {'Entropy':>10} {'Ghosts':>8} "
          f"{'GhostPwr':>10} {'Purity':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*8} {'-'*10} {'-'*10}")

    best_entropy = None
    best_config = None

    for r in all_results:
        vx = r["velocity_channel"]
        print(f"  {r['config']:>25} "
              f"{vx['spectral_entropy']:>10.4f} "
              f"{vx['ghost_count']:>8} "
              f"{vx['ghost_power_ratio']:>10.4f} "
              f"{vx['harmonic_purity']:>10.4f}")

        # Score: lower entropy + fewer ghosts + higher purity
        score = (vx["spectral_entropy"] +
                 vx["ghost_count"] * 0.5 -
                 vx["harmonic_purity"] * 2)
        if best_entropy is None or score < best_entropy:
            best_entropy = score
            best_config = r["config"]

    print(f"\n  WINNER: {best_config}")
    print(f"  (lowest combined: entropy + ghosts - purity)")

    # ═══════════════════════════════════════════════════
    # VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  SEGMENT GEOMETRY VERDICT")
    print(f"{'='*65}")

    # Find winner details
    winner = [r for r in all_results
              if r["config"] == best_config][0]
    wvx = winner["velocity_channel"]

    if wvx["ghost_count"] == 0:
        print(f"\n  CLEAN SPECTRUM: zero ghosts in {best_config}")
        print(f"  All modes are harmonics of probe fundamental.")
        print(f"  Internal geometric aliasing eliminated.")
    elif wvx["ghost_count"] <= 2:
        print(f"\n  NEAR CLEAN: {wvx['ghost_count']} ghosts "
              f"in {best_config}")
        print(f"  Residual modes are low-power.")
        print(f"  Acceptable for crew safety with monitoring.")
    else:
        print(f"\n  GHOSTS PERSIST: {wvx['ghost_count']} in "
              f"{best_config}")
        print(f"  Segment architecture may need further work.")

    print(f"\n  Harmonic purity: {wvx['harmonic_purity']:.4f}")
    print(f"  Spectral entropy: {wvx['spectral_entropy']:.4f}")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v17_diag_geometry_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v17 Segment Geometry Sweep",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Compare segment ratios for spectral "
                     "cleanliness inside 50-step locked cycle"),
        "grid": nx,
        "steps": args.steps,
        "f_probe": f_probe,
        "configs": all_results,
        "winner": best_config,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
