# -*- coding: utf-8 -*-
"""
BCM v17 -- Brucetron Diagnostic
================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

"Brucetron" -- Stephen Burdick Sr.'s term for a persistent
phase defect that lives between the field and the memory.
Not a particle. A phase-retained transport residue caused
by discontinuous geometry interacting with finite memory.

THE EPIPHANY: ghosts aren't bugs to kill. They're untracked
state to promote. The system is not geometry-limited, it is
memory-residue limited.

IMPLEMENTATION:
  1. Brucetron field: tracks phase discontinuity at each
     segment boundary (transit->arc, arc->fall)
  2. Sigmoid transitions: smooth state changes instead of
     step functions, reducing discontinuity injection
  3. Brucetron feedback: residue couples back into transport
  4. Brucetron energy scalar: total |O| as safety metric

THREE RUNS for comparison:
  Run A: Locked baseline (sharp transitions, no brucetron)
  Run B: Sigmoid transitions only (smooth edges)
  Run C: Sigmoid + brucetron tracking + feedback

If sigmoid alone reduces ghosts -> the source was sharp
edges. If brucetron feedback further reduces -> the residue
coupling stabilizes the system. The secret is in the layer.

Usage:
    python BCM_v17_brucetron_diagnostic.py
    python BCM_v17_brucetron_diagnostic.py --steps 3000 --grid 256
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


def sigmoid(x):
    """Smooth transition function: 0->1 over x in [-6,6]."""
    return 1.0 / (1.0 + np.exp(-x))


# ═══════════════════════════════════════════════════════
# BRUCETRON PROBE (sigmoid transitions + phase tracking)
# ═══════════════════════════════════════════════════════

class BrucetronProbe:
    def __init__(self, pid, eject_offset, use_sigmoid=False,
                 scoop_eff=0.05, scoop_r=2.0,
                 sigmoid_width=3):
        self.pid = pid
        self.eject_offset = eject_offset
        self.scoop_eff = scoop_eff
        self.scoop_r = scoop_r
        self.use_sigmoid = use_sigmoid
        self.sigmoid_width = sigmoid_width  # blend steps

        self.pos = np.array([0.0, 0.0])
        self.prev_pos = np.array([0.0, 0.0])
        self.state = "TRANSIT"
        self.cycle_step = 0
        self.cycles = 0
        self.payload = 0.0
        self.t_transit = 5
        self.t_arc = 35  # 50-step locked
        self.t_fall = 10

        # Phase discontinuity tracking
        self.phase_jump_history = []
        self.total_phase_energy = 0.0

    def _compute_arc_pos(self, arc_step, pa, rng):
        bao = rng.uniform(-0.8, 0.8)
        vc = 5 + (self.cycles % 4)
        ta = arc_step / self.t_arc
        amr = 40.0 + rng.uniform(-10, 15)
        if ta < 0.5:
            ar = amr * (ta * 2)
        else:
            ar = amr * (2 - ta * 2)
        ca = bao + ta * 2 * math.pi
        va = round(ca/(2*math.pi/vc)) * (2*math.pi/vc)
        aa = 0.3*ca + 0.7*va
        return np.array([
            pa[0] + ar*np.cos(aa),
            pa[1] + ar*np.sin(aa)])

    def update(self, com, pa, pb, step, sigma, nx, ny, rng):
        eff = step - self.eject_offset
        if eff < 0:
            self.pos = com.copy()
            self.prev_pos = self.pos.copy()
            return 0.0  # no phase jump

        cl = self.t_transit + self.t_arc + self.t_fall
        prev_cycle = self.cycles
        self.cycle_step = eff % cl
        self.cycles = eff // cl

        if self.cycles > prev_cycle and self.payload > 0:
            self._deposit(sigma, pb, nx, ny)

        self.prev_pos = self.pos.copy()
        phase_jump = 0.0

        # Boundary positions
        b1 = self.t_transit  # transit -> arc
        b2 = self.t_transit + self.t_arc  # arc -> fall
        w = self.sigmoid_width

        if self.cycle_step < self.t_transit:
            # TRANSIT
            self.state = "TRANSIT"
            t = self.cycle_step / self.t_transit
            self.pos = pb + t * (pa - pb)

        elif self.cycle_step < b2:
            # ARC (with optional sigmoid blend at entry)
            self.state = "EJECTED"
            as_ = self.cycle_step - self.t_transit
            arc_pos = self._compute_arc_pos(as_, pa, rng)

            if self.use_sigmoid and as_ < w:
                # Sigmoid blend: transit endpoint -> arc start
                transit_end = pa.copy()
                blend = sigmoid((as_ - w/2) * 6.0 / w)
                self.pos = (1 - blend) * transit_end + blend * arc_pos
            else:
                self.pos = arc_pos

            self._scoop(sigma, nx, ny)

        else:
            # FALL (with optional sigmoid blend at entry)
            self.state = "FALLING"
            fs = self.cycle_step - b2
            t_fall_frac = fs / self.t_fall

            if self.use_sigmoid and fs < w:
                # Sigmoid blend: arc endpoint -> fall start
                blend = sigmoid((fs - w/2) * 6.0 / w)
                fall_target = self.prev_pos + t_fall_frac * (pb - self.prev_pos)
                self.pos = (1 - blend) * self.prev_pos + blend * fall_target
            else:
                self.pos = self.prev_pos + t_fall_frac * (pb - self.prev_pos)

            if fs >= self.t_fall - 1:
                self._deposit(sigma, pb, nx, ny)

        # Measure phase discontinuity (velocity jump)
        displacement = np.linalg.norm(self.pos - self.prev_pos)
        # At boundaries, displacement spikes
        at_boundary = (abs(self.cycle_step - b1) <= 1 or
                       abs(self.cycle_step - b2) <= 1)
        if at_boundary:
            phase_jump = displacement
            self.total_phase_energy += phase_jump**2
            self.phase_jump_history.append({
                "step": step,
                "boundary": "T->A" if abs(self.cycle_step - b1) <= 1 else "A->F",
                "jump": round(phase_jump, 6),
            })

        return phase_jump

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
# SINGLE RUN
# ═══════════════════════════════════════════════════════

def run_config(nx, ny, steps, dt, D, alpha, separation,
               pump_A, ratio, lam, X, Y,
               use_sigmoid, use_brucetron_feedback,
               brucetron_gamma=0.001, rng_seed=42):
    rng = np.random.RandomState(rng_seed)

    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2*5.0**2))
    sigma_prev = sigma.copy()

    probes = [BrucetronProbe(i+1, i*5, use_sigmoid=use_sigmoid)
              for i in range(12)]

    # Brucetron field: accumulated phase residue on grid
    brucetron_field = np.zeros((nx, ny))
    brucetron_decay = 0.95  # retention per step

    ts_com_vx = []
    ts_sigma_peak = []
    ts_brucetron_energy = []
    ts_phase_jumps = []
    prev_cx = None

    for step in range(steps):
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
            sn += alpha * (sigma - sigma_prev)

        # Brucetron feedback into transport
        if use_brucetron_feedback:
            sn -= brucetron_gamma * brucetron_field

        sn = np.maximum(sn, 0)
        if float(np.max(sn)) > 1e10:
            break
        sigma_prev = sigma.copy()
        sigma = sn

        # Probe cycling + phase jump measurement
        total_jump_this_step = 0.0
        for p in probes:
            jump = p.update(com, pa, pb, step, sigma,
                            nx, ny, rng)
            if jump > 0:
                # Deposit phase residue at probe position
                ix = int(np.clip(p.pos[0], 0, nx-1))
                iy = int(np.clip(p.pos[1], 0, ny-1))
                brucetron_field[ix, iy] += jump * 0.1
                total_jump_this_step += jump

        # Brucetron field decay
        brucetron_field *= brucetron_decay

        # Time series
        cx = float(com[0])
        if prev_cx is not None:
            ts_com_vx.append(cx - prev_cx)
        else:
            ts_com_vx.append(0.0)
        prev_cx = cx

        ix_c = int(np.clip(com[0], 0, nx-1))
        iy_c = int(np.clip(com[1], 0, ny-1))
        ts_sigma_peak.append(float(sigma[ix_c, iy_c]))
        ts_brucetron_energy.append(
            float(np.sum(brucetron_field**2)))
        ts_phase_jumps.append(total_jump_this_step)

    # Total phase energy across all probes
    total_phase_energy = sum(p.total_phase_energy
                             for p in probes)

    return {
        "ts_com_vx": np.array(ts_com_vx),
        "ts_sigma_peak": np.array(ts_sigma_peak),
        "ts_brucetron_energy": np.array(ts_brucetron_energy),
        "ts_phase_jumps": np.array(ts_phase_jumps),
        "total_phase_energy": total_phase_energy,
        "final_brucetron_rms": float(np.sqrt(
            np.mean(brucetron_field**2))),
    }


# ═══════════════════════════════════════════════════════
# SPECTRAL ANALYSIS
# ═══════════════════════════════════════════════════════

def analyze_spectrum(signal, f_probe=0.02):
    sig_c = signal - np.mean(signal)
    window = np.hanning(len(sig_c))
    sig_w = sig_c * window
    fft_vals = np.fft.rfft(sig_w)
    freqs = np.fft.rfftfreq(len(sig_w), d=1.0)
    power = np.abs(fft_vals)**2
    total_power = float(np.sum(power))

    if total_power < 1e-15:
        return {"entropy": 0, "ghost_count": 0,
                "purity": 0, "peaks": []}

    p_norm = power / total_power
    p_norm = p_norm[p_norm > 1e-15]
    entropy = float(-np.sum(p_norm * np.log(p_norm)))

    power_rel = power / np.max(power) if np.max(power) > 0 else power
    peaks = []
    for i in range(1, len(power_rel) - 1):
        if (power_rel[i] > power_rel[i-1] and
                power_rel[i] > power_rel[i+1] and
                power_rel[i] > 0.05):
            f = float(freqs[i])
            ratio = f / f_probe if f_probe > 0 else 0
            nearest = round(ratio)
            err = abs(ratio - nearest)
            cls = (f"H{nearest}" if err < 0.03 * max(1, nearest)
                   else "GHOST")
            peaks.append({
                "freq": round(f, 6),
                "power": round(float(power_rel[i]), 4),
                "class": cls,
            })
    peaks.sort(key=lambda p: p["power"], reverse=True)

    ghost_count = sum(1 for p in peaks if p["class"] == "GHOST")
    harm_power = sum(p["power"] for p in peaks
                     if p["class"] != "GHOST")
    ghost_power = sum(p["power"] for p in peaks
                      if p["class"] == "GHOST")
    total_pk = harm_power + ghost_power
    purity = harm_power / total_pk if total_pk > 0 else 0

    return {
        "entropy": round(entropy, 4),
        "ghost_count": ghost_count,
        "purity": round(purity, 4),
        "peaks": peaks[:10],
    }


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v17 Brucetron Diagnostic")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v17 -- BRUCETRON DIAGNOSTIC")
    print(f"  Phase defects promoted to state variable")
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

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny//2)**2
    lam -= 0.08 * np.exp(-r2g / (2*18.0**2))
    lam = np.maximum(lam, 0.001)

    configs = [
        ("A: Sharp (baseline)", False, False),
        ("B: Sigmoid only", True, False),
        ("C: Sigmoid + Brucetron", True, True),
    ]

    all_results = []

    for name, use_sig, use_orb in configs:
        print(f"\n  {'─'*55}")
        print(f"  {name}")
        print(f"  Sigmoid: {'ON' if use_sig else 'OFF'}  "
              f"Brucetron feedback: {'ON' if use_orb else 'OFF'}")
        print(f"  {'─'*55}")

        data = run_config(
            nx, ny, args.steps, dt, D, alpha, separation,
            pump_A, ratio, lam, X, Y,
            use_sigmoid=use_sig,
            use_brucetron_feedback=use_orb,
            rng_seed=42)

        vx_spec = analyze_spectrum(data["ts_com_vx"])
        pk_spec = analyze_spectrum(data["ts_sigma_peak"])

        # Brucetron energy trend
        orb_e = data["ts_brucetron_energy"]
        if len(orb_e) > 100:
            orb_early = float(np.mean(orb_e[:100]))
            orb_late = float(np.mean(orb_e[-100:]))
            orb_trend = "GROWING" if orb_late > orb_early * 1.1 else (
                "DECAYING" if orb_late < orb_early * 0.9 else "STABLE")
        else:
            orb_early = orb_late = 0
            orb_trend = "N/A"

        result = {
            "config": name,
            "velocity_spectrum": vx_spec,
            "sigma_spectrum": pk_spec,
            "total_phase_energy": round(
                data["total_phase_energy"], 4),
            "brucetron_rms": round(
                data["final_brucetron_rms"], 8),
            "brucetron_early": round(orb_early, 6),
            "brucetron_late": round(orb_late, 6),
            "brucetron_trend": orb_trend,
        }
        all_results.append(result)

        print(f"\n  VELOCITY SPECTRUM:")
        print(f"    Entropy: {vx_spec['entropy']:.4f}  "
              f"Ghosts: {vx_spec['ghost_count']}  "
              f"Purity: {vx_spec['purity']:.4f}")
        print(f"    {'Freq':>10} {'Power':>8} {'Class':>8}")
        for pk in vx_spec["peaks"][:6]:
            print(f"    {pk['freq']:>10.6f} {pk['power']:>8.4f} "
                  f"{pk['class']:>8}")

        print(f"\n  BRUCETRON METRICS:")
        print(f"    Total phase energy: "
              f"{data['total_phase_energy']:.4f}")
        print(f"    Brucetron field RMS:  "
              f"{data['final_brucetron_rms']:.8f}")
        print(f"    Energy trend:       {orb_trend} "
              f"({orb_early:.6f} -> {orb_late:.6f})")

    # ═══════════════════════════════════════════════════
    # COMPARISON
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  BRUCETRON COMPARISON")
    print(f"{'='*65}")

    print(f"\n  {'Config':>28} {'Entropy':>8} {'Ghosts':>7} "
          f"{'Purity':>8} {'PhaseE':>10} {'OrbTrend':>10}")
    print(f"  {'-'*28} {'-'*8} {'-'*7} {'-'*8} "
          f"{'-'*10} {'-'*10}")

    for r in all_results:
        vx = r["velocity_spectrum"]
        print(f"  {r['config']:>28} "
              f"{vx['entropy']:>8.4f} "
              f"{vx['ghost_count']:>7} "
              f"{vx['purity']:>8.4f} "
              f"{r['total_phase_energy']:>10.4f} "
              f"{r['brucetron_trend']:>10}")

    # ═══════════════════════════════════════════════════
    # VERDICT
    # ═══════════════════════════════════════════════════

    print(f"\n{'='*65}")
    print(f"  BRUCETRON VERDICT")
    print(f"{'='*65}")

    # Compare ghost counts
    g_a = all_results[0]["velocity_spectrum"]["ghost_count"]
    g_b = all_results[1]["velocity_spectrum"]["ghost_count"]
    g_c = all_results[2]["velocity_spectrum"]["ghost_count"]

    if g_b < g_a:
        print(f"\n  Sigmoid REDUCED ghosts: {g_a} -> {g_b}")
        print(f"  Sharp edges were injecting phase energy.")
    elif g_b == g_a:
        print(f"\n  Sigmoid had NO EFFECT on ghost count: "
              f"{g_a} -> {g_b}")
        print(f"  Ghosts are not edge-driven.")
    else:
        print(f"\n  Sigmoid INCREASED ghosts: {g_a} -> {g_b}")
        print(f"  Smoothing introduced new modes.")

    if g_c < g_b:
        print(f"\n  Brucetron feedback FURTHER REDUCED: "
              f"{g_b} -> {g_c}")
        print(f"  Phase residue coupling stabilizes system.")
    elif g_c == g_b:
        print(f"\n  Brucetron feedback had NO ADDITIONAL EFFECT.")
    else:
        print(f"\n  Brucetron feedback INCREASED ghosts: "
              f"{g_b} -> {g_c}")

    # Brucetron stability
    orb_c = all_results[2]
    if orb_c["brucetron_trend"] == "DECAYING":
        print(f"\n  BRUCETRON ENERGY IS DECAYING -> STABLE")
        print(f"  Phase defects are being absorbed, not growing.")
    elif orb_c["brucetron_trend"] == "STABLE":
        print(f"\n  BRUCETRON ENERGY IS STABLE -> BOUNDED")
        print(f"  Phase defects at equilibrium.")
    elif orb_c["brucetron_trend"] == "GROWING":
        print(f"\n  !! BRUCETRON ENERGY IS GROWING -> UNSTABLE")
        print(f"  Phase defects accumulating. Crew risk.")

    # f/2 ghost check
    f_half_present = any(
        abs(pk["freq"] - 0.010) < 0.002 and pk["class"] == "GHOST"
        for pk in all_results[2]["velocity_spectrum"]["peaks"])

    if f_half_present:
        print(f"\n  f/2 subharmonic (0.010): STILL PRESENT")
        print(f"  The heartbeat persists. Monitorable.")
    else:
        print(f"\n  f/2 subharmonic (0.010): RESOLVED")
        print(f"  Brucetron tracking absorbed the residue.")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v17_brucetron_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v17 Brucetron Diagnostic",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": ("Phase defect tracking with sigmoid "
                     "transitions and brucetron feedback"),
        "grid": nx,
        "steps": args.steps,
        "configs": [{k: v for k, v in r.items()}
                    for r in all_results],
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
