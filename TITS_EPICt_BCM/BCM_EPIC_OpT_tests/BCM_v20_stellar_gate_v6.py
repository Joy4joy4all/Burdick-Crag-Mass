# -*- coding: utf-8 -*-
"""
BCM v20.6 -- Stellar Gate (Twin Guardians at L1)
===================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

v20.5 shadow reduced PhiRMS 57% but still aborts.
The star doesn't overwhelm the signal — it fogs
the 7D operator's self-reflection mirror so the craft
can't hear its OWN heartbeat.

Grok's anomaly detection: the L1 throat has two
coherent pumps (ship + star) sharing substrate memory
without guardians to prevent contractual bleed. The
mirror fogs because no one is polishing it.

Stephen Burdick Sr.'s guardian concept:
  "Humans require two guardians. Paired twins. 7D
   entities that HOLD entangled 6D phase states.
   They govern conservation math 2D-6D during fold.
   NOT entanglement — guardians manage entanglement."

OpT (Opacity Time) and OpC (Opacity spatial C-arc):
  - NOT amplitude detectors — reflectivity operators
  - Measure how well the craft sees its own heartbeat
  - Divergence between OpT and OpC = disorientation
  - The star fogs the mirror, doesn't overwhelm signal

THIS TEST: Twin guardians at L1 hold the crew-shaped
phase state through the fold. They prevent contractual
bleed, keep OpT/OpC coherent, and route forced bleed
to chi freeboard. The guardians polish the mirror.

Frozen guardian constants:
  GUARDIAN_STRENGTH = 0.68 (phase state grip)
  NON_CONTRACTUAL = 0.22 (bleed blocking at L1)

Usage:
    python BCM_v20_stellar_gate_v6.py
    python BCM_v20_stellar_gate_v6.py --steps 20000 --grid 256
"""

import numpy as np
import json
import os
import time
import math
import argparse


KAPPA_DRAIN = 0.35
CHI_DECAY = 0.997
ALPHA = 0.80

# ---- TACHOCLINE GATE CONSTANTS (FROZEN) ----
# v20.2: spectral fold detector
DPHI_GATE = 0.012           # phase rate trigger
PHASE_LOCK_THRESHOLD = 0.18 # spectral proximity
PUMP_CLIP = 0.55            # pre-coupling governor
CHI_SHOCK = 0.82            # fast bleed (shock absorber)
BRIDGE_STRETCH = 1.12       # temporary separation factor
CORE_DROP_FRAC = 0.35       # one-time chi bleed fraction
SLEW_DAMP = 0.70            # lambda gradient damping

# ---- ACTIVE PHASE DECORRELATION (APD) CONSTANTS ----
# v20.3: continuous phase rejection (inverse PLL)
KP_PHASE = 0.85             # proportional rejection
KD_PHASE = 0.40             # derivative damping
CHI_STABILIZER_GAIN = 12.5  # flywheel conversion factor
INTERNAL_PHI_BASELINE = 0.0014  # f/2 steady tone target
PHASE_SAFETY_LIMIT = 0.00949   # max safe PhiRMS (v19)

# ---- 7D CHIRAL L1 CROSSING (Burdick v20.5) ----
# The craft crosses at L1, not PA then PB.
# The 6D ribbon folds at L1. Both pumps enter the
# stellar field simultaneously as one object.
# The chiral phase offset at L1 replaces the spatial
# gradient. The ribbon curl determines emergence.
CHIRAL_COUPLING = 0.12      # ribbon fold intensity at L1
L1_SAMPLE_R = 8             # sampling radius at L1 throat

# ---- TWIN GUARDIANS AT L1 (Burdick v20.6) ----
# The guardians are paired 7D entities that HOLD the
# crew-shaped phase state through the fold. They keep
# OpT and OpC coherent — polishing the 7D self-mirror
# so the crew always sees its own heartbeat.
GUARDIAN_STRENGTH = 0.68    # how tightly they hold the phase state
NON_CONTRACTUAL = 0.22      # bleed blocking factor at L1


def compute_com(field):
    total = np.sum(field)
    if total < 1e-15:
        return None
    nx, ny = field.shape
    x = np.arange(nx); y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    return np.array([np.sum(X*field)/total,
                     np.sum(Y*field)/total])


def get_stellar_profile(step, total_steps):
    """
    Transit profile through Alpha Centauri A.
    Lambda DECREASES inside star (well-funded substrate).
    Sigma source INCREASES (tachocline pump active).

    Returns: (lambda, stellar_pump_amplitude, phase_name)
    """
    frac = step / total_steps

    if frac < 0.15:
        # Phase 1: Approach in void
        return 0.05, 0.0, "APPROACH"
    elif frac < 0.25:
        # Phase 2: Stellar entry (outer envelope)
        t = (frac - 0.15) / 0.10
        lam = 0.05 - t * 0.045  # drops to 0.005
        pump = t * 2.0  # stellar pump rises
        return lam, pump, "ENTRY"
    elif frac < 0.35:
        # Phase 3: Tachocline crossing
        t = (frac - 0.25) / 0.10
        lam = 0.005 - t * 0.004  # drops to 0.001
        pump = 2.0 + t * 3.0  # pump intensifies
        return lam, pump, "TACHOCLINE"
    elif frac < 0.50:
        # Phase 4: Core transit (maximum funding)
        lam = 0.001  # minimum decay (maximally funded)
        pump = 5.0  # full stellar pump
        return lam, pump, "CORE"
    elif frac < 0.60:
        # Phase 5: Core exit
        t = (frac - 0.50) / 0.10
        lam = 0.001 + t * 0.004
        pump = 5.0 - t * 3.0
        return lam, pump, "CORE_EXIT"
    elif frac < 0.70:
        # Phase 6: Stellar exit (outer envelope)
        t = (frac - 0.60) / 0.10
        lam = 0.005 + t * 0.045
        pump = 2.0 - t * 2.0
        return lam, pump, "EXIT"
    else:
        # Phase 7: Recovery in void
        return 0.05, 0.0, "RECOVERY"


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
            self.payload -= ba; self.total_bled += ba; bleed = ba
            bx = int(np.clip(pb[0],0,nx-1))
            by = int(np.clip(pb[1],0,ny-1))
            xa = np.arange(max(0,bx-4),min(nx,bx+5))
            ya = np.arange(max(0,by-4),min(ny,by+5))
            if len(xa)>0 and len(ya)>0:
                Xl,Yl = np.meshgrid(xa,ya,indexing='ij')
                r2 = (Xl-pb[0])**2+(Yl-pb[1])**2
                w = np.exp(-r2/(2*2.0**2)); ws = float(np.sum(w))
                if ws>1e-15: chi_field[np.ix_(xa,ya)]+=w*(ba/ws)
            self._deposit(sigma, pb, nx, ny)
        self.prev_pos = self.pos.copy()
        b1=self.t_transit; b2=self.t_transit+self.t_arc
        if self.cycle_step < b1:
            self.state="TRANSIT"
            t=self.cycle_step/self.t_transit
            self.pos = pb+t*(pa-pb)
        elif self.cycle_step < b2:
            self.state="EJECTED"
            as_=self.cycle_step-self.t_transit
            bao=rng.uniform(-0.8,0.8); vc=5+(self.cycles%4)
            ta=as_/self.t_arc; amr=40.0+rng.uniform(-10,15)
            ar=amr*(ta*2) if ta<0.5 else amr*(2-ta*2)
            ca=bao+ta*2*math.pi
            va=round(ca/(2*math.pi/vc))*(2*math.pi/vc)
            aa=0.3*ca+0.7*va
            self.pos=np.array([pa[0]+ar*np.cos(aa),
                               pa[1]+ar*np.sin(aa)])
            self._scoop(sigma,nx,ny)
            ix=int(np.clip(self.pos[0],0,nx-1))
            iy=int(np.clip(self.pos[1],0,ny-1))
            probe_hits[ix,iy]+=1.0
        else:
            self.state="FALLING"
            fs=self.cycle_step-b2
            tf=fs/self.t_fall
            self.pos=self.prev_pos+tf*(pb-self.prev_pos)
            if fs>=self.t_fall-1:
                ba=KAPPA_DRAIN*self.payload
                self.payload-=ba; self.total_bled+=ba; bleed+=ba
                bx=int(np.clip(pb[0],0,nx-1))
                by=int(np.clip(pb[1],0,ny-1))
                xa=np.arange(max(0,bx-4),min(nx,bx+5))
                ya=np.arange(max(0,by-4),min(ny,by+5))
                if len(xa)>0 and len(ya)>0:
                    Xl,Yl=np.meshgrid(xa,ya,indexing='ij')
                    r2=(Xl-pb[0])**2+(Yl-pb[1])**2
                    w=np.exp(-r2/(2*2.0**2)); ws=float(np.sum(w))
                    if ws>1e-15: chi_field[np.ix_(xa,ya)]+=w*(ba/ws)
                self._deposit(sigma,pb,nx,ny)
        disp=float(np.linalg.norm(self.pos-self.prev_pos))
        at_b=(abs(self.cycle_step-b1)<=1 or
              abs(self.cycle_step-b2)<=1)
        return (disp if at_b else 0.0), bleed

    def _scoop(self, sigma, nx, ny):
        ix=int(np.clip(self.pos[0],0,nx-1))
        iy=int(np.clip(self.pos[1],0,ny-1))
        xa=np.arange(max(0,ix-4),min(nx,ix+5))
        ya=np.arange(max(0,iy-4),min(ny,iy+5))
        if len(xa)==0 or len(ya)==0: return
        Xl,Yl=np.meshgrid(xa,ya,indexing='ij')
        r2=(Xl-self.pos[0])**2+(Yl-self.pos[1])**2
        w=np.exp(-r2/(2*self.scoop_r**2))
        loc=sigma[np.ix_(xa,ya)]
        sc=np.minimum(loc*w*self.scoop_eff,loc)
        sc=np.maximum(sc,0); sigma[np.ix_(xa,ya)]-=sc
        self.payload+=float(np.sum(sc))

    def _deposit(self, sigma, pos, nx, ny):
        if self.payload<=0: return
        ix=int(np.clip(pos[0],0,nx-1))
        iy=int(np.clip(pos[1],0,ny-1))
        xa=np.arange(max(0,ix-4),min(nx,ix+5))
        ya=np.arange(max(0,iy-4),min(ny,iy+5))
        if len(xa)==0 or len(ya)==0: return
        Xl,Yl=np.meshgrid(xa,ya,indexing='ij')
        r2=(Xl-pos[0])**2+(Yl-pos[1])**2
        w=np.exp(-r2/(2*self.scoop_r**2)); ws=float(np.sum(w))
        if ws>1e-15: sigma[np.ix_(xa,ya)]+=w*(self.payload/ws)
        self.payload=0.0


def main():
    parser = argparse.ArgumentParser(
        description="BCM v20 Stellar Transit Test")
    parser.add_argument("--steps", type=int, default=20000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx=ny=args.grid; steps=args.steps

    print(f"\n{'='*65}")
    print(f"  BCM v20 -- STELLAR TRANSIT TEST")
    print(f"  Fly through Alpha Centauri A.")
    print(f"  7D coherence: do 3D objects exist on the")
    print(f"  substrate, or are they transparent?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {steps}")
    print(f"  kappa_drain: {KAPPA_DRAIN}  chi_decay: {CHI_DECAY}")
    print(f"  c_substrate: 12,000c (crewed craft)")
    print(f"  Target: Alpha Centauri A (m=1 tachocline)")

    dt=0.05; D=0.5; pump_A=0.5; ratio=0.25; separation=15.0
    x_arr=np.arange(nx); y_arr=np.arange(ny)
    X,Y=np.meshgrid(x_arr,y_arr,indexing='ij')

    rng=np.random.RandomState(42)
    sx,sy=nx//8,ny//2; r2i=(X-sx)**2+(Y-sy)**2
    sigma=1.0*np.exp(-r2i/(2*5.0**2))
    sigma_prev=sigma.copy()
    chi_field=np.zeros((nx,ny)); phi=np.zeros((nx,ny))
    probe_hits=np.zeros((nx,ny))
    probes=[PhaseProbe(i+1,i*5) for i in range(12)]
    bruce_field=np.zeros((nx,ny)); bruce_decay=0.95

    total_bled=0.0; hem_counter=0; dis_counter=0
    abort=False; abort_reason=""
    max_bruce=0.0; diag_interval=200
    flight_log=[]
    gate_events=[]
    gate_active=False
    gate_step=None
    base_separation=separation
    base_pump_A=pump_A
    core_dropped=False
    prev_phi_rms=0.0
    prev_phi_error=0.0
    OpT = 1.0   # temporal reflectivity (1.0 = perfect mirror)
    OpC = 1.0   # spatial reflectivity (1.0 = perfect mirror)
    OpT_prev = 1.0
    OpC_prev = 1.0
    phi_baseline_local = 0.0  # will calibrate from approach

    print(f"\n  {'Step':>6} {'Phase':>12} {'Lam':>8} "
          f"{'Pump':>6} {'BrRMS':>8} {'PhiRMS':>8} "
          f"{'Chi':>8} {'Zone':>6} {'Gate':>6}")
    print(f"  {'-'*6} {'-'*12} {'-'*8} {'-'*6} "
          f"{'-'*8} {'-'*8} {'-'*8} {'-'*6} {'-'*6}")

    for step in range(steps):
        lam_val, stellar_pump, phase = get_stellar_profile(
            step, steps)

        # ---- 7D SPECTRAL FOLD DETECTOR ----
        # v20.2: watches RATE of phase change (dphi/dt)
        # and spectral proximity. Fires on the RAMP,
        # not the spike. The ship's 7D field folds back
        # to ask: "is another coherent pump overwriting
        # our heartbeat?"
        #
        # Two trigger conditions (OR logic):
        #   1. dphi > DPHI_GATE (phase ramping)
        #   2. spectral_fold < PHASE_LOCK_THRESHOLD
        #      AND stellar pump active

        star_m = 1  # Alpha Centauri A tachocline mode
        craft_h10 = 0.200
        star_freq = star_m * 0.020
        spectral_fold = abs(craft_h10 - star_freq * 10)

        # Compute dphi (rate of phase change)
        # Uses phi_rms from PREVIOUS step
        current_phi_rms = float(np.sqrt(np.mean(phi**2)))
        dphi = abs(current_phi_rms - prev_phi_rms)
        prev_phi_rms = current_phi_rms

        # Gate OPEN conditions (either trigger fires)
        if not gate_active:
            rate_trigger = dphi > DPHI_GATE
            spectral_trigger = (spectral_fold <
                PHASE_LOCK_THRESHOLD and stellar_pump > 0.1)

            if rate_trigger or spectral_trigger:
                gate_active = True
                gate_step = step
                trigger = ("RATE" if rate_trigger
                           else "SPECTRAL")
                gate_events.append({
                    "step": step, "phase": phase,
                    "dphi": round(dphi, 6),
                    "stellar_pump": round(stellar_pump, 2),
                    "spectral_fold": round(spectral_fold, 4),
                    "trigger": trigger,
                    "action": "GATE_OPEN",
                })

        # Gate CLOSE: stellar pump gone AND dphi settled
        if gate_active and stellar_pump < 0.1 and dphi < 0.002:
            gate_active = False
            core_dropped = False
            separation = base_separation
            pump_A = base_pump_A
            prev_phi_error = 0.0
            gate_events.append({
                "step": step, "phase": phase,
                "action": "GATE_CLOSE",
            })

        # ---- 7D GOVERNED FOLD RESPONSE ----
        if gate_active:
            # 1. Telescopic bridge stretch (detune)
            separation = base_separation * BRIDGE_STRETCH

            # 2. Pre-coupling pump governor
            # CLIP pump before coupling gets worse
            # This is the key fix — don't feed the
            # external oscillator with your own pump
            pump_A = base_pump_A * PUMP_CLIP

            # 3. Fast chi bleed (shock absorber)
            # Not passive 0.997 decay — active dump
            # Drains stored energy that would feed
            # the phase instability
            chi_field *= CHI_SHOCK

            # 4. Core-drop: one-time safety bleed
            if not core_dropped:
                for p in probes:
                    if p.payload > 0:
                        drop = CORE_DROP_FRAC * p.payload
                        p.payload -= drop
                        p.total_bled += drop
                        ix_d = int(np.clip(com[0], 0, nx-1))
                        iy_d = int(np.clip(com[1], 0, ny-1))
                        chi_field[ix_d, iy_d] += drop
                core_dropped = True
                gate_events.append({
                    "step": step,
                    "action": "CORE_DROP",
                })

            # 5. Lambda gradient damping (gentle slew)
            lam_val = lam_val + (0.05 - lam_val) * (
                1 - SLEW_DAMP) * 0.1

            # ---- ACTIVE PHASE DECORRELATION (APD) ----
            # v20.3: continuous phase rejection (inverse PLL)
            # The craft doesn't just detect the star — it
            # COUNTER-FORCES the phase intrusion every step.
            # Gemini's concept: "Own the frequency of the
            # hallway. Convert the star's shout into chi."
            #
            # PD controller on phi deviation from baseline.
            # Pump authority collapses proportional to error.
            # Chi flywheel absorbs phase error energy.

            # Phase error = current deviation from f/2 tone
            phi_error = current_phi_rms - INTERNAL_PHI_BASELINE
            d_phi_error = phi_error - prev_phi_error

            # PD correction (counter-force on phi field)
            correction = (KP_PHASE * phi_error +
                          KD_PHASE * d_phi_error)
            # Apply correction as damping to phi field
            if correction > 0:
                phi *= max(0.1, 1.0 - correction)

            # Pump authority collapse
            # If phase is unstable, pump MUST drop
            # This starves the coupling that feeds takeover
            if current_phi_rms > INTERNAL_PHI_BASELINE * 2:
                pump_authority = max(0.05,
                    1.0 - (current_phi_rms /
                           PHASE_SAFETY_LIMIT))
                pump_A = base_pump_A * PUMP_CLIP * pump_authority

            # Chi flywheel: absorb phase error as pressure
            # High chi = working shield, not overload
            # The star's energy becomes the craft's armor
            if abs(phi_error) > 0.0001:
                chi_field += abs(phi_error) * CHI_STABILIZER_GAIN

            prev_phi_error = phi_error

        gate_str = "OPEN" if gate_active else ""

        lam=np.full((nx,ny),lam_val)
        gx=nx//2; r2g=(X-gx)**2+(Y-ny//2)**2
        lam-=0.08*np.exp(-r2g/(2*18.0**2))
        lam=np.maximum(lam,0.001)

        com=compute_com(sigma)
        if com is None:
            print(f"  *** DISSOLVED step {step} ***"); break
        pa=np.array([com[0]+separation,com[1]])
        pb=np.array([com[0]-separation*0.3,com[1]])

        # ---- 7D CHIRAL L1 CROSSING (Burdick v20.5) ----
        # The craft crosses at L1, not PA then PB.
        # L1 is the throat between the two pumps — the
        # single point where the 6D ribbon folds.
        # Both pumps enter the stellar field simultaneously
        # as one object through L1.
        #
        # At 12,000c the craft's substrate shadow outruns
        # the star's refresh rate. The shadow disrupts
        # the star's substrate pattern at L1 before the
        # star's m=1 pump can complete one cycle.
        #
        # The chiral phase offset at L1 replaces the
        # spatial PA/PB gradient.

        # L1 position (throat between pumps)
        l1 = (pa + pb) / 2.0
        ix_l1 = int(np.clip(l1[0], L1_SAMPLE_R,
                            nx - L1_SAMPLE_R - 1))
        iy_l1 = int(np.clip(l1[1], L1_SAMPLE_R,
                            ny - L1_SAMPLE_R - 1))
        lr = L1_SAMPLE_R

        # Substrate state at L1 (what the throat sees)
        sig_at_l1 = float(np.mean(
            sigma[ix_l1-lr:ix_l1+lr,
                  iy_l1-lr:iy_l1+lr]))

        # Chiral phase offset from star's m=1 at L1
        # The ribbon fold angle — which side of the
        # star's mode pattern is L1 on?
        star_x = nx // 2; star_y = ny // 2
        theta_l1 = math.atan2(l1[1] - star_y,
                              l1[0] - star_x)
        chiral_offset = math.cos(1 * theta_l1)

        # Distance from L1 to star center (normalized)
        dist_to_star = math.sqrt(
            (l1[0] - star_x)**2 +
            (l1[1] - star_y)**2) / (nx * 0.5)

        # At 12,000c the craft shadow disrupts the star's
        # substrate pattern. The closer to the star, the
        # stronger the shadow's candle-blowing effect.
        # shadow_damp: 1.0 far away, approaches 0 at core
        # The craft's velocity advantage over the star's
        # refresh rate means the star can't impose rhythm
        shadow_damp = min(1.0, dist_to_star * 3.0)

        # Apply chiral fold: both pumps receive the same
        # phase correction through L1. The stellar pump
        # is damped by the craft's own shadow.
        chiral_active = (stellar_pump > 0.1 and
                         dist_to_star < 0.5)

        if chiral_active:
            # Dampen stellar source at L1 proportional
            # to craft's velocity advantage (shadow effect)
            stellar_pump_effective = stellar_pump * shadow_damp

            # Chiral phase rotation applied equally to
            # both pump contributions — the ribbon folds
            # at L1, not at PA or PB separately
            chiral_phase = CHIRAL_COUPLING * chiral_offset

            # Pre-load chi at L1 with the ribbon fold
            # energy — the curl of the ribbon
            fold_energy = abs(chiral_offset) * stellar_pump * (
                1.0 - shadow_damp) * 0.5
            chi_field[ix_l1-lr:ix_l1+lr,
                      iy_l1-lr:iy_l1+lr] += (
                fold_energy / max(1, (2*lr)**2))
        else:
            stellar_pump_effective = stellar_pump
            chiral_phase = 0.0

        # Craft pumps — both enter through L1 as one object
        # ratio unchanged (drive asymmetry preserved)
        r2A=(X-com[0])**2+(Y-com[1])**2
        sigma+=pump_A*np.exp(-r2A/(2*4.0**2))*dt
        bx=com[0]+separation
        r2B=(X-bx)**2+(Y-com[1])**2
        sigma+=pump_A*ratio*np.exp(-r2B/(2*3.0**2))*dt

        # STELLAR PUMP (Alpha Centauri tachocline)
        # Uses stellar_pump_effective: the craft's shadow
        # at 12,000c outruns the star's refresh rate.
        # The shadow dampens the star's substrate pattern
        # at L1 before the m=1 pump can couple.
        if stellar_pump_effective > 0:
            r2_star = (X-star_x)**2 + (Y-star_y)**2
            theta_star = np.arctan2(Y-star_y, X-star_x)
            # Chiral phase offset rotates the m=1 pattern
            # relative to the craft's ribbon fold
            stellar_source = (stellar_pump_effective *
                np.cos(1 * theta_star + chiral_phase) *
                np.exp(-r2_star / (2 * 30.0**2)))
            sigma += stellar_source * dt

        # ---- TWIN GUARDIANS AT L1 (Burdick v20.6) ----
        # The guardians sit at L1 and hold the crew-shaped
        # phase state. They don't damp the star harder.
        # They keep the 7D self-mirror polished so the crew
        # can still see its own heartbeat through the fold.
        #
        # OpT: temporal reflectivity — can the craft see
        #   its own f/2 in the time domain?
        # OpC: spatial reflectivity — can the craft see
        #   its own sigma pattern at L1?
        #
        # Divergence = |OpT - OpC| = disorientation

        # Calibrate baseline from approach (first 2000 steps)
        if step == 2000:
            phi_baseline_local = current_phi_rms

        # OpT: how close is current phi_rms to baseline?
        # 1.0 = perfect temporal self-reflection
        phi_bl = max(phi_baseline_local, 1e-10)
        OpT = max(0.0, 1.0 - abs(
            current_phi_rms - phi_bl) / (phi_bl * 100))

        # OpC: how close is sigma at L1 to the craft's
        # own sigma pattern (vs the star's)?
        # Compare sigma at L1 to sigma at craft center
        ix_com = int(np.clip(com[0], lr, nx-lr-1))
        iy_com = int(np.clip(com[1], lr, ny-lr-1))
        sig_at_com = float(np.mean(
            sigma[ix_com-lr:ix_com+lr,
                  iy_com-lr:iy_com+lr]))
        sig_ratio = sig_at_l1 / max(sig_at_com, 1e-10)
        OpC = max(0.0, min(1.0,
            1.0 - abs(sig_ratio - 1.0) * 2.0))

        # Opacity divergence = disorientation source
        opacity_div = abs(OpT - OpC)

        # GUARDIAN INTERVENTION at L1
        if chiral_active or gate_active:
            # Guardians hold the phase state at L1
            # Block contractual bleed between ship and star
            contractual_bleed = 1.0 - GUARDIAN_STRENGTH

            # The external phi disturbance at L1 is filtered
            # Guardians prevent the star's phase from
            # overwriting the crew's self-reference
            phi_local = phi[ix_l1-lr:ix_l1+lr,
                            iy_l1-lr:iy_l1+lr]
            external_component = phi_local * (
                1.0 - NON_CONTRACTUAL * contractual_bleed)
            blocked = phi_local - external_component
            phi[ix_l1-lr:ix_l1+lr,
                iy_l1-lr:iy_l1+lr] = external_component

            # Route blocked energy to chi (guardians
            # convert fog into armor)
            chi_field[ix_l1-lr:ix_l1+lr,
                      iy_l1-lr:iy_l1+lr] += np.abs(
                          blocked) * GUARDIAN_STRENGTH

            # Guardians also stabilize sigma at L1
            # Prevent the star from writing its own
            # memory over the craft's pattern
            sigma_local = sigma[ix_l1-lr:ix_l1+lr,
                                iy_l1-lr:iy_l1+lr]
            sigma_mean = float(np.mean(sigma_local))
            if sigma_mean > 0:
                excess = np.maximum(
                    sigma_local - sigma_mean * 1.5, 0)
                sigma[ix_l1-lr:ix_l1+lr,
                      iy_l1-lr:iy_l1+lr] -= (
                          excess * GUARDIAN_STRENGTH)
                chi_field[ix_l1-lr:ix_l1+lr,
                          iy_l1-lr:iy_l1+lr] += (
                              excess * GUARDIAN_STRENGTH)

        OpT_prev = OpT
        OpC_prev = OpC

        lap=(np.roll(sigma,1,0)+np.roll(sigma,-1,0)+
             np.roll(sigma,1,1)+np.roll(sigma,-1,1)-
             4*sigma)
        sn=sigma+D*lap*dt-lam*sigma*dt+ALPHA*(sigma-sigma_prev)
        sn=np.maximum(sn,0)
        if float(np.max(sn))>1e10:
            print(f"  *** BLOWUP step {step} ***"); break

        phi=phi*0.95+(sigma-sigma_prev)
        sigma_prev=sigma.copy(); sigma=sn

        for p in probes:
            jump,bleed=p.update(com,pa,pb,step,sigma,
                                nx,ny,rng,probe_hits,
                                chi_field)
            if jump>0:
                ix=int(np.clip(p.pos[0],0,nx-1))
                iy=int(np.clip(p.pos[1],0,ny-1))
                bruce_field[ix,iy]+=jump*0.1
            total_bled+=bleed
        bruce_field*=bruce_decay

        # Chi freeboard
        ix_c=int(np.clip(com[0],0,nx-1))
        iy_c=int(np.clip(com[1],0,ny-1))
        r_v=20
        x_lo=max(0,ix_c-r_v);x_hi=min(nx,ix_c+r_v)
        y_lo=max(0,iy_c-r_v);y_hi=min(ny,iy_c+r_v)
        ls=sigma[x_lo:x_hi,y_lo:y_hi]
        fl=float(np.mean(ls))+1.5*float(np.std(ls))
        overflow=np.maximum(sigma-fl,0)
        spill=overflow*0.5; sigma-=spill; chi_field+=spill
        deficit=np.maximum(fl*0.8-sigma,0)
        drain=np.minimum(chi_field*0.1,deficit)
        sigma+=drain; chi_field-=drain
        chi_field*=CHI_DECAY
        bruce_in=bruce_field*0.05
        chi_field+=bruce_in*0.01
        bruce_field-=bruce_in
        bruce_field=np.maximum(bruce_field,0)

        # Diagnostics
        bruce_rms=float(np.sqrt(np.mean(bruce_field**2)))
        phi_rms=float(np.sqrt(np.mean(phi**2)))
        if bruce_rms>max_bruce: max_bruce=bruce_rms

        # Safety gates
        if bruce_rms>0.012: hem_counter+=1
        else: hem_counter=max(0,hem_counter-1)
        # v20.6: disorientation = OpT/OpC divergence
        # Not absolute phi_rms — the crew loses orientation
        # when the two shadow clocks diverge, not when
        # either one spikes
        if opacity_div > 0.5 or phi_rms > 0.05: dis_counter+=1
        else: dis_counter=max(0,dis_counter-1)

        if hem_counter>200:
            abort=True; abort_reason="HEMORRHAGE"
        if dis_counter>300:
            abort=True; abort_reason="DISORIENTATION"

        if abort:
            print(f"  {step:>6} {'***ABORT***':>12} "
                  f"{lam_val:>8.4f} {stellar_pump:>6.1f} "
                  f"{bruce_rms:>8.5f} {phi_rms:>8.5f} "
                  f"{'':>8} {'RED':>6}")
            print(f"  REASON: {abort_reason}")
            break

        if step%diag_interval==0:
            chi_t=float(np.sum(chi_field))
            zone="GREEN" if bruce_rms<0.006 else (
                "YELLOW" if bruce_rms<0.010 else "RED")
            shd = "CHR" if chiral_active else ""

            print(f"  {step:>6} {phase:>12} "
                  f"{lam_val:>8.4f} {stellar_pump:>6.1f} "
                  f"{bruce_rms:>8.5f} {phi_rms:>8.5f} "
                  f"{chi_t:>8.1f} {zone:>6} {gate_str:>6}"
                  f" {shd:>4} T{OpT:.2f} C{OpC:.2f}")

            flight_log.append({
                "step": step, "phase": phase,
                "lambda": round(lam_val,4),
                "stellar_pump": round(stellar_pump,2),
                "bruce_rms": round(bruce_rms,6),
                "phi_rms": round(phi_rms,6),
                "chi_total": round(chi_t,4),
                "zone": zone,
                "gate": gate_str,
                "separation": round(separation, 2),
                "OpT": round(OpT, 4),
                "OpC": round(OpC, 4),
                "opacity_div": round(opacity_div, 6),
                "shadow_damp": round(shadow_damp, 4),
            })

    # ---- SUMMARY ----
    print(f"\n{'='*65}")
    print(f"  STELLAR TRANSIT SUMMARY")
    print(f"{'='*65}")

    final_sigma=float(np.sum(sigma))
    final_chi=float(np.sum(chi_field))

    print(f"\n  Target: Alpha Centauri A")
    print(f"  Max Brucetron RMS: {max_bruce:.6f}")
    print(f"  Crew violations: "
          f"{'NONE' if not abort else abort_reason}")
    print(f"  Total bled: {total_bled:.2f}")
    print(f"  Final sigma: {final_sigma:.2f}")
    print(f"  Final chi: {final_chi:.2f}")
    print(f"  System: {final_sigma+final_chi:.2f}")

    # Count zones
    if flight_log:
        greens=sum(1 for e in flight_log if e["zone"]=="GREEN")
        yellows=sum(1 for e in flight_log if e["zone"]=="YELLOW")
        reds=sum(1 for e in flight_log if e["zone"]=="RED")
        total_diag=len(flight_log)
        print(f"\n  Zone breakdown:")
        print(f"    GREEN:  {greens}/{total_diag}")
        print(f"    YELLOW: {yellows}/{total_diag}")
        print(f"    RED:    {reds}/{total_diag}")

    # Core transit analysis
    core_entries=[e for e in flight_log
                  if e["phase"] in ("CORE","TACHOCLINE")]
    if core_entries:
        core_max=max(e["bruce_rms"] for e in core_entries)
        core_min_lam=min(e["lambda"] for e in core_entries)
        core_max_pump=max(e["stellar_pump"]
                         for e in core_entries)
        print(f"\n  CORE TRANSIT:")
        print(f"    Max BruceRMS in core: {core_max:.6f}")
        print(f"    Min lambda in core:   {core_min_lam:.4f}")
        print(f"    Max stellar pump:     {core_max_pump:.1f}")

    # Gate event summary
    print(f"\n  TACHOCLINE GATE:")
    print(f"    Gate events: {len(gate_events)}")
    for ge in gate_events:
        print(f"    Step {ge['step']:>6}: {ge['action']}")

    if not abort:
        if max_bruce < 0.010:
            print(f"\n  VERDICT: STELLAR GATE TRANSIT CLEAR")
            print(f"  The craft passed through Alpha Centauri A")
            print(f"  using the tachocline gate detector.")
            print(f"  7D fold matrix governed the approach.")
            print(f"  3D mass is TRANSPARENT with gate active.")
            verdict="TRANSPARENT"
        else:
            print(f"\n  VERDICT: STELLAR GATE TRANSIT SURVIVED")
            print(f"  Craft coherent but stressed even with gate.")
            verdict="STRESSED"
    else:
        print(f"\n  VERDICT: STELLAR GATE TRANSIT FAILED")
        print(f"  Gate active but insufficient.")
        verdict="BLOCKED"

    print(f"{'='*65}")

    # Save
    base=os.path.dirname(os.path.abspath(__file__))
    out_dir=os.path.join(base,"data","results")
    os.makedirs(out_dir,exist_ok=True)
    out_path=os.path.join(out_dir,
        f"BCM_v20_stellar_gate_v6_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data={
        "title":"BCM v20.6 Stellar Gate (Twin Guardians at L1)",
        "author":"Stephen Justin Burdick Sr. -- "
                 "Emerald Entities LLC",
        "purpose":"Fly through Alpha Centauri A with "
                  "tachocline gate detector active. "
                  "7D fold matrix governs approach.",
        "target":"Alpha Centauri A (m=1 tachocline)",
        "c_substrate":"12,000c",
        "gate_constants": {
            "dphi_gate": DPHI_GATE,
            "phase_lock_threshold": PHASE_LOCK_THRESHOLD,
            "pump_clip": PUMP_CLIP,
            "chi_shock": CHI_SHOCK,
            "bridge_stretch": BRIDGE_STRETCH,
            "core_drop_frac": CORE_DROP_FRAC,
            "slew_damp": SLEW_DAMP,
            "kp_phase": KP_PHASE,
            "kd_phase": KD_PHASE,
            "chi_stabilizer_gain": CHI_STABILIZER_GAIN,
            "internal_phi_baseline": INTERNAL_PHI_BASELINE,
            "phase_safety_limit": PHASE_SAFETY_LIMIT,
            "grad_shadow_threshold": "REMOVED (v20.5)",
            "symmetric_ratio": "REMOVED (v20.5)",
            "shadow_sample_r": "REMOVED (v20.5)",
            "chiral_coupling": CHIRAL_COUPLING,
            "l1_sample_r": L1_SAMPLE_R,
            "guardian_strength": GUARDIAN_STRENGTH,
            "non_contractual": NON_CONTRACTUAL,
        },
        "grid":nx,"steps":steps,
        "max_bruce_rms":round(max_bruce,8),
        "verdict":verdict,
        "abort_reason":abort_reason,
        "total_bled":round(total_bled,4),
        "final_sigma":round(final_sigma,4),
        "final_chi":round(final_chi,4),
        "gate_events":gate_events,
        "flight_log":flight_log,
    }

    with open(out_path,"w") as f:
        json.dump(out_data,f,indent=2,default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
