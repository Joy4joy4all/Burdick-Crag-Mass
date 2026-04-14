# -*- coding: utf-8 -*-
"""
BCM v17 -- Diagnostic: Coherence Frequency Lock
==================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

"Goal frequency curve lock that works with outer CMB path
real time. Otherwise cells in humans will excite and
hemorrhage." -- Stephen Burdick Sr.

THE PROBLEM:
The craft has multiple oscillating subsystems:
  - Pump A injection cycle
  - Pump B collection cycle
  - Probe tunnel cycling (55-step period)
  - Substrate lambda response
  - Memory term (alpha) feedback oscillation
  - Sigma PDE natural modes

If these frequencies beat constructively at biological
resonance frequencies, crew tissue hemorrhages. The craft
kills its own crew from internal harmonics.

THE DIAGNOSTIC:
1. Run the transport model for 3000 steps
2. Sample sigma amplitude at craft COM every step
3. FFT decompose into frequency spectrum
4. Identify dominant modes from each subsystem
5. Compare against biological harm bands
6. Compare against CMB reference (160.2 GHz / 2.725K)
7. Find the coherence lock window where:
   - craft harmonics align (constructive)
   - biological bands are avoided (destructive notch)
   - CMB coupling is maintained (navigation)

BIOLOGICAL HARM BANDS (literature reference ranges):
  - 0.5-3 Hz: vestibular disruption (motion sickness)
  - 4-8 Hz: organ resonance (thorax, abdomen)
  - 8-12 Hz: spinal column resonance
  - 15-20 Hz: head/neck resonance
  - 20-80 Hz: eyeball resonance, blurred vision
  - 100-200 Hz: cellular membrane disruption
  These are in real Hz. We map to solver frequency
  units (cycles/step) and check if any craft harmonic
  falls in a danger band under unit conversion.

FREQUENCY ARCHITECTURE:
  Pump A: fires every step -> f_pump = 1/dt = 20 Hz equiv
  Pump B: fires every step -> same as A
  Probe cycle: 55 steps (5+40+10) -> f_probe = 1/55 steps
  Memory alpha: feedback at 1-step lag -> f_mem = 1/dt
  Substrate response: natural diffusion mode

The diagnostic does NOT assume unit mapping. It measures
the spectrum in solver units and identifies where modes
cluster, beat, or resonate. The unit mapping (step->sec)
determines which biological band gets hit. The SAFE
condition is: no mode clustering in ANY band regardless
of unit mapping.

Usage:
    python BCM_v17_diag_frequency.py
    python BCM_v17_diag_frequency.py --steps 3000 --grid 256
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
# TRANSPORT PROBE (scoop/deposit)
# ═══════════════════════════════════════════════════════

class FreqProbe:
    def __init__(self, pid, eject_offset, scoop_eff=0.05,
                 scoop_r=2.0):
        self.pid = pid
        self.eject_offset = eject_offset
        self.scoop_eff = scoop_eff
        self.scoop_r = scoop_r
        self.pos = np.array([0.0, 0.0])
        self.state = "TRANSIT"
        self.cycle_step = 0
        self.cycles = 0
        self.payload = 0.0
        self.t_transit = 5
        self.t_arc = 35   # locked: 5+35+10=50 (integer of 0.200)
        self.t_fall = 10

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
# MAIN DIAGNOSTIC
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v17 Frequency Coherence Lock")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v17 -- COHERENCE FREQUENCY (PHASE INVERSION)")
    print(f"  Pi-phase cancel on f/2 subharmonic")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    ratio = 0.25
    alpha = 0.80
    separation = 15.0

    rng = np.random.RandomState(42)
    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    # Lambda with grave
    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny//2)**2
    lam -= 0.08 * np.exp(-r2g / (2*18.0**2))
    lam = np.maximum(lam, 0.001)

    # Sigma
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2*5.0**2))
    sigma_prev = sigma.copy()

    probes = [FreqProbe(i+1, i*5) for i in range(12)]

    # ── TIME SERIES COLLECTION ──
    # Sample multiple channels at craft COM every step
    ts_sigma_peak = []       # peak sigma at COM
    ts_sigma_total = []      # total field sigma
    ts_com_x = []            # COM x position
    ts_com_vx = []           # COM velocity (dx/dt)
    ts_lambda_local = []     # lambda at COM
    ts_payload_total = []    # total probe payload
    ts_coherence = []        # craft coherence

    prev_com_x = None

    print(f"\n  Running transport model...")

    for step in range(args.steps):
        com = compute_com(sigma)
        if com is None:
            break

        pa = np.array([com[0] + separation, com[1]])
        pb = np.array([com[0] - separation*0.3, com[1]])

        # Pumps
        r2A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2A / (2*4.0**2))
        sigma += pA * dt
        bx = com[0] + separation
        r2B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_A * ratio * np.exp(-r2B / (2*3.0**2))
        sigma += pB * dt

        # PDE
        lap = (np.roll(sigma, 1, 0) + np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) + np.roll(sigma, -1, 1) -
               4*sigma)
        sn = sigma + D*lap*dt - lam*sigma*dt
        if alpha > 0:
            # Phase inversion: alternate sign on memory term
            # Targets f/2 subharmonic with destructive
            # interference. Does NOT alter f_0 fundamental.
            phase = 1.0 if step % 2 == 0 else -1.0
            sn += phase * alpha * (sigma - sigma_prev)
        sn = np.maximum(sn, 0)
        if float(np.max(sn)) > 1e10:
            break
        sigma_prev = sigma.copy()
        sigma = sn

        # Probes
        for p in probes:
            p.update(com, pa, pb, step, sigma, nx, ny, rng)

        # Sample time series
        ix_com = int(np.clip(com[0], 0, nx-1))
        iy_com = int(np.clip(com[1], 0, ny-1))

        ts_sigma_peak.append(float(sigma[ix_com, iy_com]))
        ts_sigma_total.append(float(np.sum(sigma)))
        ts_com_x.append(float(com[0]))

        if prev_com_x is not None:
            ts_com_vx.append(float(com[0]) - prev_com_x)
        else:
            ts_com_vx.append(0.0)
        prev_com_x = float(com[0])

        ts_lambda_local.append(float(lam[ix_com, iy_com]))
        ts_payload_total.append(
            sum(p.payload for p in probes))

        # Coherence
        r2c = (X - com[0])**2 + (Y - com[1])**2
        inside = float(np.sum(sigma[r2c < 64]))
        total = float(np.sum(sigma))
        ts_coherence.append(inside / total if total > 1e-15
                            else 0)

    n_samples = len(ts_sigma_peak)
    print(f"  Collected {n_samples} time samples")

    # ═══════════════════════════════════════════════════
    # FFT DECOMPOSITION
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  FREQUENCY DECOMPOSITION")
    print(f"{'='*65}")

    # Channels to analyze
    channels = {
        "sigma_peak": np.array(ts_sigma_peak),
        "sigma_total": np.array(ts_sigma_total),
        "com_velocity": np.array(ts_com_vx),
        "coherence": np.array(ts_coherence),
    }

    # Known architectural frequencies (in cycles/step)
    probe_cycle = 50  # LOCKED: 5+35+10 (integer of 0.200)
    f_probe = 1.0 / probe_cycle  # 0.01818 cycles/step
    f_pump = 1.0  # fires every step
    f_memory = 1.0  # alpha feedback every step

    # Harmonic set from probe cycling
    probe_harmonics = [f_probe * n for n in range(1, 11)]

    print(f"\n  ARCHITECTURAL FREQUENCIES:")
    print(f"    Probe cycle:  {probe_cycle} steps "
          f"(f = {f_probe:.5f} cycles/step)")
    print(f"    Pump:         every step "
          f"(f = {f_pump:.5f} cycles/step)")
    print(f"    Memory alpha: 1-step lag "
          f"(f = {f_memory:.5f} cycles/step)")
    print(f"    Probe harmonics: "
          f"{[round(h, 5) for h in probe_harmonics[:5]]}")

    all_channel_results = {}

    for ch_name, signal in channels.items():
        # Remove DC (mean)
        sig_centered = signal - np.mean(signal)

        # Apply Hanning window to reduce spectral leakage
        window = np.hanning(len(sig_centered))
        sig_windowed = sig_centered * window

        # FFT
        fft_vals = np.fft.rfft(sig_windowed)
        freqs = np.fft.rfftfreq(len(sig_windowed), d=1.0)
        power = np.abs(fft_vals)**2

        # Normalize
        power_norm = power / np.max(power) if np.max(power) > 0 else power

        # Find peaks (local maxima above 5% of max)
        peaks = []
        for i in range(1, len(power_norm) - 1):
            if (power_norm[i] > power_norm[i-1] and
                    power_norm[i] > power_norm[i+1] and
                    power_norm[i] > 0.05):
                peaks.append({
                    "freq": round(float(freqs[i]), 6),
                    "power": round(float(power_norm[i]), 6),
                    "period_steps": (round(1.0/freqs[i], 1)
                                    if freqs[i] > 0 else 0),
                })

        # Sort by power
        peaks.sort(key=lambda p: p["power"], reverse=True)
        peaks = peaks[:10]  # top 10

        all_channel_results[ch_name] = {
            "peaks": peaks,
            "total_power": round(float(np.sum(power)), 4),
            "dc_component": round(float(np.mean(signal)), 6),
        }

        print(f"\n  CHANNEL: {ch_name}")
        print(f"  {'Rank':>5} {'Freq':>12} {'Period':>10} "
              f"{'Power':>10} {'Match':>20}")
        print(f"  {'-'*5} {'-'*12} {'-'*10} {'-'*10} {'-'*20}")

        for i, pk in enumerate(peaks[:8]):
            # Check if peak matches known architecture
            match = ""
            if abs(pk["freq"] - f_probe) < 0.002:
                match = "PROBE FUNDAMENTAL"
            elif any(abs(pk["freq"] - h) < 0.002
                     for h in probe_harmonics):
                n = min(range(len(probe_harmonics)),
                        key=lambda j: abs(
                            pk["freq"] - probe_harmonics[j]))
                match = f"PROBE HARMONIC {n+1}"
            elif pk["freq"] > 0.4:
                match = "HIGH (pump/memory)"
            elif pk["period_steps"] > 0:
                # Check for beating frequencies
                for h1 in probe_harmonics[:5]:
                    for h2 in probe_harmonics[:5]:
                        beat = abs(h1 - h2)
                        if beat > 0.001 and abs(
                                pk["freq"] - beat) < 0.002:
                            match = "BEAT FREQUENCY"
                            break

            print(f"  {i+1:>5} {pk['freq']:>12.6f} "
                  f"{pk['period_steps']:>10.1f} "
                  f"{pk['power']:>10.6f} {match:>20}")

    # ═══════════════════════════════════════════════════
    # BIOLOGICAL HARM BAND ANALYSIS
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  BIOLOGICAL HARM BAND ANALYSIS")
    print(f"{'='*65}")

    # Harm bands in Hz (real world)
    harm_bands = [
        ("vestibular", 0.5, 3.0),
        ("organ_resonance", 4.0, 8.0),
        ("spinal", 8.0, 12.0),
        ("head_neck", 15.0, 20.0),
        ("eyeball", 20.0, 80.0),
        ("cellular", 100.0, 200.0),
    ]

    # We don't know step->second mapping yet.
    # Instead, compute: for each dominant craft frequency,
    # what step->second conversion would place it in a
    # harm band? This gives the FORBIDDEN unit mappings.

    print(f"\n  For each dominant frequency, which unit mappings")
    print(f"  would place it in a biological harm band?")
    print(f"  These are the FORBIDDEN dt values.")

    dominant_freqs = []
    for ch_name, ch_data in all_channel_results.items():
        for pk in ch_data["peaks"][:3]:
            if pk["freq"] > 0.001:
                dominant_freqs.append({
                    "channel": ch_name,
                    "freq_solver": pk["freq"],
                    "power": pk["power"],
                })

    # Remove duplicates by frequency
    seen = set()
    unique_freqs = []
    for df in dominant_freqs:
        key = round(df["freq_solver"], 4)
        if key not in seen:
            seen.add(key)
            unique_freqs.append(df)

    forbidden_zones = []

    print(f"\n  {'Freq(solver)':>14} {'Band':>18} "
          f"{'dt_min(s)':>12} {'dt_max(s)':>12} {'Status':>10}")
    print(f"  {'-'*14} {'-'*18} {'-'*12} {'-'*12} {'-'*10}")

    for df in unique_freqs:
        f_sol = df["freq_solver"]  # cycles per step
        for band_name, f_lo, f_hi in harm_bands:
            # f_real = f_solver / dt_seconds
            # f_lo < f_solver/dt < f_hi
            # dt_min = f_solver/f_hi
            # dt_max = f_solver/f_lo
            if f_sol > 0:
                dt_min = f_sol / f_hi
                dt_max = f_sol / f_lo
                status = "FORBIDDEN"

                forbidden_zones.append({
                    "freq_solver": round(f_sol, 6),
                    "band": band_name,
                    "dt_min_s": round(dt_min, 8),
                    "dt_max_s": round(dt_max, 8),
                })

                print(f"  {f_sol:>14.6f} {band_name:>18} "
                      f"{dt_min:>12.8f} {dt_max:>12.8f} "
                      f"{status:>10}")

    # ═══════════════════════════════════════════════════
    # COHERENCE LOCK ANALYSIS
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  COHERENCE LOCK ANALYSIS")
    print(f"{'='*65}")

    # Check if dominant frequencies are harmonically related
    # (integer ratios = locked; irrational ratios = beating)
    if len(unique_freqs) >= 2:
        print(f"\n  HARMONIC RATIOS (integer = locked, "
              f"irrational = beating):")
        print(f"  {'F1':>12} {'F2':>12} {'Ratio':>10} "
              f"{'Nearest':>10} {'Error':>10} {'Status':>12}")
        print(f"  {'-'*12} {'-'*12} {'-'*10} {'-'*10} "
              f"{'-'*10} {'-'*12}")

        ratio_results = []
        for i in range(len(unique_freqs)):
            for j in range(i+1, len(unique_freqs)):
                f1 = unique_freqs[i]["freq_solver"]
                f2 = unique_freqs[j]["freq_solver"]
                if f2 > 0 and f1 > 0:
                    r = f1 / f2 if f1 > f2 else f2 / f1
                    # Find nearest integer ratio
                    best_n = 1
                    best_d = 1
                    best_err = abs(r - 1)
                    for n in range(1, 20):
                        for d in range(1, 20):
                            err = abs(r - n/d)
                            if err < best_err:
                                best_err = err
                                best_n = n
                                best_d = d

                    locked = best_err < 0.02
                    status = ("LOCKED" if locked
                              else "BEATING")

                    ratio_results.append({
                        "f1": round(f1, 6),
                        "f2": round(f2, 6),
                        "ratio": round(r, 4),
                        "nearest": f"{best_n}/{best_d}",
                        "error": round(best_err, 4),
                        "status": status,
                    })

                    print(f"  {f1:>12.6f} {f2:>12.6f} "
                          f"{r:>10.4f} "
                          f"{best_n}/{best_d}:>10 "
                          f"{best_err:>10.4f} {status:>12}")

    # ═══════════════════════════════════════════════════
    # CMB REFERENCE
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  CMB REFERENCE COUPLING")
    print(f"{'='*65}")

    cmb_peak_hz = 160.2e9  # 160.2 GHz (2.725K peak)
    print(f"\n  CMB peak frequency: {cmb_peak_hz:.2e} Hz")
    print(f"  CMB temperature: 2.725 K")

    # For the craft to couple to CMB, one of its harmonics
    # must be a rational subdivision of CMB peak
    # f_craft * N = f_cmb (where N is the subdivision)
    # This constrains the step->second mapping

    if unique_freqs:
        f_dom = unique_freqs[0]["freq_solver"]
        if f_dom > 0:
            # dt_cmb = f_dom / f_cmb
            dt_cmb = f_dom / cmb_peak_hz
            print(f"\n  Dominant craft freq: {f_dom:.6f} "
                  f"cycles/step")
            print(f"  CMB lock dt: {dt_cmb:.4e} seconds/step")
            print(f"  This means 1 solver step = "
                  f"{dt_cmb:.4e} seconds")
            print(f"  At this mapping, craft frequency = "
                  f"CMB peak")

            # Check if this dt falls in any forbidden zone
            in_forbidden = False
            for fz in forbidden_zones:
                if fz["dt_min_s"] <= dt_cmb <= fz["dt_max_s"]:
                    in_forbidden = True
                    print(f"\n  !! CMB lock dt falls in "
                          f"FORBIDDEN zone: {fz['band']}")
                    print(f"     Range: {fz['dt_min_s']:.4e} "
                          f"to {fz['dt_max_s']:.4e}")
            if not in_forbidden:
                print(f"\n  CMB lock dt is CLEAR of all "
                      f"biological harm bands")

    # ═══════════════════════════════════════════════════
    # VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  COHERENCE FREQUENCY VERDICT")
    print(f"{'='*65}")

    # Count beating pairs
    beating_count = sum(1 for r in ratio_results
                        if r["status"] == "BEATING") \
        if 'ratio_results' in dir() else 0
    locked_count = sum(1 for r in ratio_results
                       if r["status"] == "LOCKED") \
        if 'ratio_results' in dir() else 0

    print(f"\n  Locked frequency pairs:  {locked_count}")
    print(f"  Beating frequency pairs: {beating_count}")
    print(f"  Forbidden dt zones:      {len(forbidden_zones)}")

    if beating_count == 0:
        print(f"\n  ALL FREQUENCIES LOCKED")
        print(f"  Craft harmonics are integer-related.")
        print(f"  No internal beating. Coherence maintained.")
    elif beating_count <= 2:
        print(f"\n  PARTIAL LOCK -- {beating_count} beating pairs")
        print(f"  Active damping required at beat frequencies.")
    else:
        print(f"\n  DISSONANCE DETECTED -- {beating_count} "
              f"beating pairs")
        print(f"  Craft harmonics not locked. Internal "
              f"hemorrhage risk under wrong unit mapping.")
        print(f"  Requires frequency governor or probe cycle "
              f"adjustment.")

    print(f"\n  SAFE OPERATING CONDITION:")
    print(f"  Choose dt (step->second) that places ALL craft")
    print(f"  frequencies OUTSIDE biological harm bands.")
    print(f"  The forbidden zones above define what dt values")
    print(f"  to avoid. The CMB lock dt defines the target.")
    print(f"{'='*65}")

    # ═══════════════════════════════════════════════════
    # SAVE
    # ═══════════════════════════════════════════════════

    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v17_diag_frequency_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v17 Coherence Frequency Lock",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Frequency decomposition of craft "
                     "harmonics, biological harm band "
                     "analysis, CMB coupling check"),
        "grid": nx,
        "steps": args.steps,
        "architectural_frequencies": {
            "probe_cycle_steps": probe_cycle,
            "f_probe": round(f_probe, 6),
            "f_pump": f_pump,
            "f_memory": f_memory,
        },
        "channel_results": {
            ch: {"peaks": d["peaks"][:5],
                 "dc": d["dc_component"]}
            for ch, d in all_channel_results.items()
        },
        "forbidden_zones": forbidden_zones[:20],
        "cmb_peak_hz": cmb_peak_hz,
        "dominant_freqs": unique_freqs[:5],
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
