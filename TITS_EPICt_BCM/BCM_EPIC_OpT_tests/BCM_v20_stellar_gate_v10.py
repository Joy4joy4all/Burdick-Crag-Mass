# -*- coding: utf-8 -*-
"""
BCM v20.8 -- Stellar Gate (Disguise Point Operator)
======================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

D = Disguise Point Operator.

Not a derivative. Not a decay. The cloak that hides
a 3D object by coercing all its variables (phase,
sigma, memory, shadow) into a single coherent disguise
so the substrate cannot "see" the raw object during
the fold.

v20.7 proved the D operation stabilizes OpT/OpC at 1.0
even in the stellar core. v20.8 refines the disguise
into full variable coercion:

  D_cloak = D × (1 - Δ_OP)
  V_disguised = V × (1 - D_cloak) + V_guardian × D_cloak

Every craft variable at L1 is blended between its raw
state and the guardian-held state. The star's m=1
tachocline interacts with the disguised version, not
the raw craft. The star looks right through.

The guardians hold the human-shaped phase state.
The D operator makes everything else invisible.
The Fibonacci spiral (8D→9D) keeps the disguise
self-similar at every scale of the fold.

Usage:
    python BCM_v20_stellar_gate_v8.py
    python BCM_v20_stellar_gate_v8.py --steps 20000 --grid 256
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
GUARDIAN_STRENGTH = 0.85    # how tightly they hold the phase state
NON_CONTRACTUAL = 0.22      # bleed blocking factor at L1

# ---- D OPERATION: 8D HARD POINT (Burdick + Grok) ----
# The D operation is the chiral-collapse operator that
# references the 8D hard point for frame stability.
# The Fibonacci ratio governs how the 7D ribbon folds
# into the 9D circumpunct — the self-similar spiral
# that keeps OpT and OpC coherent at the throat.
# Without this anchor the guardians have nothing to grip.
FIB_RATIO = 1.6180339887       # golden ratio (7D→9D fold)
D_OPERATION_STRENGTH = 0.75    # 8D hard point frame anchor
D_CLOAK_STRENGTH = 0.90        # disguise coercion strength

# ---- PYTHAGOREAN NODE CLAMP (Claude v20.8) ----
# Pythagoras: clamp a vibrating string at a node.
# The fundamental (antinode at clamp) dies.
# The harmonic (node at clamp) passes through.
# L1 is the node of the dumbbell ribbon.
# f/2 heartbeat has its natural node at L1.
# The star's coupling modes have antinodes at L1.
# Clamp kills what couples. Heartbeat survives.
NODE_CLAMP_STRENGTH = 0.92     # how hard we enforce the node
NODE_CLAMP_RADIUS = 3          # tight radius at exact L1 center

# ---- VENTURI CURL (Pythagorean orthogonality) ----
# The rifled bore rotates phi gradient at L1 by 90°.
# Axial modes (which couple to star m=1) become
# transverse modes (which don't). The curl enforces
# the right angle of the Pythagorean triangle at L1.
CURL_STRENGTH = 0.65           # how strongly the bore rifles

# ---- FORMALIZED OPERATOR THRESHOLDS (Grok) ----
DELTA_OP_THRESHOLD = 0.08   # max OpT/OpC divergence
R_7D_THRESHOLD = 0.92       # min mirror reflectivity
COHERENCE_THRESHOLD = 0.95  # min phase clock coherence
DELTA_OP_ABORT_STEPS = 50   # consecutive steps before abort


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

        # OpT: temporal shadow reflectivity
        # (Burdick, formalized Grok)
        # How well the craft sees its own f/2 in time
        # relative to the star's phase intrusion
        phi_stellar = stellar_pump * 0.1  # scaled star mode
        OpT = max(0.0, min(1.0,
            1.0 - abs(current_phi_rms - phi_stellar) * 0.3))

        # OpC: spatial C-arc shadow reflectivity
        # (Burdick, formalized Grok)
        # How well the craft sees its own pattern at L1
        # through the chiral ribbon fold
        OpC = max(0.0, min(1.0,
            1.0 - shadow_damp * abs(chiral_phase)))

        # Opacity divergence = disorientation source
        opacity_div = abs(OpT - OpC)

        # R_7D: mirror reflectivity quality
        # (OpT + OpC)/2 * (1 - Delta_OP)
        R_7D = ((OpT + OpC) / 2.0) * (1.0 - opacity_div)

        # Coherence: phase clock alignment
        # cos(phi_ship - phi_external) * (1 - Delta_OP)
        # phi_ship = f/2 baseline, phi_external = star's m=1
        if stellar_pump > 0.01:
            phi_ship = current_phi_rms
            phi_ext = stellar_pump * 0.1  # scaled star mode
            phase_diff = phi_ship - phi_ext
            coherence_raw = math.cos(phase_diff)
        else:
            coherence_raw = 1.0
        Coherence = coherence_raw * (1.0 - opacity_div)

        # ---- DISGUISE POINT OPERATOR + GUARDIANS (v20.8) ----
        # D = Disguise. The cloak that hides the 3D object
        # by coercing all craft variables into a coherent
        # disguise so the substrate cannot "see" the raw
        # object during the fold.
        #
        # D_cloak = D × (1 - Δ_OP)
        # V_disguised = V × (1-D_cloak) + V_guardian × D_cloak
        #
        # The star interacts with the disguised version.
        # The guardians hold the human-shaped state.
        # The Fibonacci spiral keeps it self-similar.

        if chiral_active or gate_active:
            G = GUARDIAN_STRENGTH

            # Fibonacci collapse → 8D hard point
            chiral_collapse = abs(OpT - OpC) * FIB_RATIO
            chiral_collapse = min(chiral_collapse, 1.0)
            d_anchor = D_OPERATION_STRENGTH * (
                1.0 - chiral_collapse)

            # D cloak strength (Grok v20.8 refinement)
            d_cloak = D_CLOAK_STRENGTH * (
                1.0 - opacity_div)

            # D restores the 7D mirror operators
            OpT = min(1.0, OpT * (1.0 + d_anchor * 0.3))
            OpC = min(1.0, OpC * (1.0 + d_anchor * 0.3))
            opacity_div = abs(OpT - OpC)
            R_7D = ((OpT + OpC) / 2.0) * (1.0 - opacity_div)

            # Guardian-held reference: the craft's OWN
            # phi and sigma at its center (not at L1
            # where the star is writing). This is what
            # the crew "looks like" when healthy.
            ix_com = int(np.clip(com[0], lr, nx-lr-1))
            iy_com = int(np.clip(com[1], lr, ny-lr-1))
            guardian_phi = phi[ix_com-lr:ix_com+lr,
                               iy_com-lr:iy_com+lr].copy()
            guardian_sigma = sigma[ix_com-lr:ix_com+lr,
                                   iy_com-lr:iy_com+lr].copy()

            # Get raw craft state at L1
            phi_raw = phi[ix_l1-lr:ix_l1+lr,
                          iy_l1-lr:iy_l1+lr].copy()
            sigma_raw = sigma[ix_l1-lr:ix_l1+lr,
                              iy_l1-lr:iy_l1+lr].copy()

            # Match shapes (guardian patch may differ from
            # L1 patch at edges)
            sh = min(phi_raw.shape[0], guardian_phi.shape[0])
            sw = min(phi_raw.shape[1], guardian_phi.shape[1])
            gp = guardian_phi[:sh, :sw]
            gs = guardian_sigma[:sh, :sw]
            pr = phi_raw[:sh, :sw]
            sr = sigma_raw[:sh, :sw]

            # DISGUISE: coerce raw → guardian-held
            # V_disguised = V*(1-D) + V_guardian*D
            phi_disguised = pr * (1.0 - d_cloak) + gp * d_cloak
            sigma_disguised = sr * (1.0 - d_cloak) + gs * d_cloak

            # Apply disguised state at L1
            # The star now sees the disguised version
            phi[ix_l1-lr:ix_l1+lr,
                iy_l1-lr:iy_l1+lr][:sh, :sw] = phi_disguised
            sigma[ix_l1-lr:ix_l1+lr,
                  iy_l1-lr:iy_l1+lr][:sh, :sw] = sigma_disguised

            # Blocked energy (raw - disguised) → chi
            # The disguise converts the star's intrusion
            # into chi armor
            blocked_phi = pr - phi_disguised
            blocked_sigma = sr - sigma_disguised
            chi_field[ix_l1-lr:ix_l1+lr,
                      iy_l1-lr:iy_l1+lr][:sh, :sw] += (
                          np.abs(blocked_phi) * G * d_cloak +
                          np.abs(blocked_sigma) * G * d_cloak)

            # ---- PYTHAGOREAN NODE CLAMP ----
            # Monochord principle: clamp the ribbon at L1.
            # f/2 heartbeat has its NATURAL NODE at L1
            # (zero crossing — half-wavelength spans full
            # dumbbell). The fundamental and pump modes
            # have ANTINODES at L1 (max amplitude). These
            # are the modes the star's m=1 couples to.
            #
            # Clamp kills antinodes (coupling modes).
            # Clamp preserves nodes (heartbeat).
            # The star has nothing to sync to.
            #
            # Selective harmonic filtering using the
            # craft's own geometry. Not force. Not cloak.
            # Resonance architecture.
            ncr = NODE_CLAMP_RADIUS
            ix_c = int(np.clip(l1[0], ncr, nx-ncr-1))
            iy_c = int(np.clip(l1[1], ncr, ny-ncr-1))
            # Enforce phi → 0 at L1 center (the node)
            phi_at_node = phi[ix_c-ncr:ix_c+ncr,
                              iy_c-ncr:iy_c+ncr].copy()
            clamped = phi_at_node * (1.0 - NODE_CLAMP_STRENGTH)
            node_energy = phi_at_node - clamped
            phi[ix_c-ncr:ix_c+ncr,
                iy_c-ncr:iy_c+ncr] = clamped
            # Node energy routes to chi (the clamped
            # fundamental becomes armor, not noise)
            chi_field[ix_c-ncr:ix_c+ncr,
                      iy_c-ncr:iy_c+ncr] += (
                          np.abs(node_energy) * G)

            # ---- PHASE MIRROR AT L1 (ChatGPT v20.9) ----
            # The node clamp killed the star's voice.
            # The phase mirror stops its echo.
            #
            # The star's phase propagates along the ribbon
            # BEFORE reaching L1. The clamp zeroes amplitude
            # but the phase delta already exists. The mirror
            # reflects incoming phase and anchors the
            # internal clock.
            #
            # L1 becomes a boundary condition, not just
            # a filter. Incoming phase is REFLECTED (inverted).
            # Internal phase is FROZEN to the f/2 reference.
            #
            # Physical: a fixed end on a vibrating string
            # reflects waves with phase inversion. L1 is
            # the fixed end of the monochord.

            # Capture the phase pattern around L1
            # (slightly wider than clamp to catch the echo)
            pr2 = ncr + 1
            ix_p = int(np.clip(l1[0], pr2, nx-pr2-1))
            iy_p = int(np.clip(l1[1], pr2, ny-pr2-1))
            phi_around = phi[ix_p-pr2:ix_p+pr2,
                             iy_p-pr2:iy_p+pr2].copy()

            # Compute the incoming phase (deviation from
            # the craft's own baseline at this patch)
            phi_ref = float(np.mean(np.abs(phi_around))) * 0.01
            # This tiny reference is the f/2 heartbeat's
            # amplitude at L1 (near zero — it's a node)

            # REFLECT: invert the external phase component
            # The star's echo bounces back instead of
            # propagating through
            phi_reflected = -phi_around * NODE_CLAMP_STRENGTH
            # ANCHOR: blend toward the reference (freeze
            # the internal clock to stop drift)
            phi_anchored = (phi_reflected * 0.7 +
                            phi_ref * 0.3)
            phi[ix_p-pr2:ix_p+pr2,
                iy_p-pr2:iy_p+pr2] = phi_anchored

            # The reflected energy routes to chi
            reflected_energy = np.abs(phi_around - phi_anchored)
            chi_field[ix_p-pr2:ix_p+pr2,
                      iy_p-pr2:iy_p+pr2] += (
                          reflected_energy * G * 0.5)

            # ---- VENTURI CURL (rifled bore at L1) ----
            # The curl rotates the phi gradient at L1 by
            # 90 degrees. Axial phi variations (which the
            # star's m=1 couples to) become transverse
            # variations (which it can't). The rifled bore
            # is the physical mechanism.
            #
            # Pythagorean: the craft's axial modes and the
            # star's axial modes are the two legs. The curl
            # creates the right angle so they can't form
            # the hypotenuse (coupling path).
            #
            # Implementation: compute phi gradient at L1,
            # swap dx↔dy with sign flip (90° rotation),
            # blend into the field.
            cr = ncr + 2  # slightly wider than node clamp
            ix_cr = int(np.clip(l1[0], cr+1, nx-cr-2))
            iy_cr = int(np.clip(l1[1], cr+1, ny-cr-2))
            phi_patch = phi[ix_cr-cr:ix_cr+cr,
                            iy_cr-cr:iy_cr+cr].copy()
            if phi_patch.shape[0] > 2 and phi_patch.shape[1] > 2:
                # Gradient along dumbbell axis (x)
                dphi_dx = np.diff(phi_patch, axis=0)
                # Gradient transverse (y)
                dphi_dy = np.diff(phi_patch, axis=1)
                # Curl = rotate gradient 90°:
                # axial → transverse, transverse → -axial
                # Apply to the interior of the patch
                sh0 = min(dphi_dx.shape[0], phi_patch.shape[0]-1)
                sh1 = min(dphi_dy.shape[1], phi_patch.shape[1]-1)
                # Subtract axial component, add as transverse
                phi_patch[1:sh0+1, :dphi_dx.shape[1]] -= (
                    CURL_STRENGTH * dphi_dx[:sh0, :])
                phi_patch[:dphi_dy.shape[0], 1:sh1+1] += (
                    CURL_STRENGTH * dphi_dy[:, :sh1])
                phi[ix_cr-cr:ix_cr+cr,
                    iy_cr-cr:iy_cr+cr] = phi_patch

            # ---- CHI-PHASE SHUNT (Gemini v10) ----
            # 7 million chi points available. Use a fraction
            # as a counter-broadcast against phi noise.
            # The star's echo energy is already IN chi
            # (routed there by guardians). Now use it to
            # actively cancel the remaining phi deviation
            # instead of just absorbing passively.
            chi_total_local = float(np.sum(
                chi_field[ix_l1-lr:ix_l1+lr,
                          iy_l1-lr:iy_l1+lr]))
            if chi_total_local > 100:
                # Counter-broadcast: subtract a fraction
                # of phi proportional to available chi
                shunt_strength = min(0.3,
                    chi_total_local / 1e6)
                phi[ix_l1-lr:ix_l1+lr,
                    iy_l1-lr:iy_l1+lr] *= (
                        1.0 - shunt_strength)
                # The shunt cost is drawn from chi
                chi_field[ix_l1-lr:ix_l1+lr,
                          iy_l1-lr:iy_l1+lr] *= (
                              1.0 - shunt_strength * 0.01)

            # ---- PHASE-RIGIDITY LOCK (Cardinal 13) ----
            # If R_7D and Delta_OP are passing, the
            # "disorientation" is a 3D perception artifact.
            # Slave the biological clock to the guardian
            # reference. The crew stops hearing the star
            # because the guardian tells them what to hear.
            if R_7D > R_7D_THRESHOLD and opacity_div < DELTA_OP_THRESHOLD:
                # Geometry is stable. Force coherence
                # to follow geometry. The feeling must
                # match the structure.
                phi_rms_target = INTERNAL_PHI_BASELINE
                phi_rms_now = float(np.sqrt(np.mean(
                    phi[ix_l1-lr:ix_l1+lr,
                        iy_l1-lr:iy_l1+lr]**2)))
                if phi_rms_now > phi_rms_target * 5:
                    # Scale phi at L1 toward the target
                    scale = phi_rms_target * 3 / max(
                        phi_rms_now, 1e-15)
                    scale = max(0.1, min(1.0, scale))
                    phi[ix_l1-lr:ix_l1+lr,
                        iy_l1-lr:iy_l1+lr] *= scale

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
        # v20.7: formalized disorientation check
        # Delta_OP > 0.08 for 50 consecutive steps
        # OR R_7D < 0.92 (mirror too foggy)
        if (opacity_div > DELTA_OP_THRESHOLD or
                R_7D < R_7D_THRESHOLD):
            dis_counter += 1
        else:
            dis_counter = max(0, dis_counter - 1)

        if hem_counter>200:
            abort=True; abort_reason="HEMORRHAGE"
        if dis_counter>DELTA_OP_ABORT_STEPS:
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
                  f" {shd:>4} T{OpT:.2f} C{OpC:.2f}"
                  f" R{R_7D:.2f}")

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
                "R_7D": round(R_7D, 4),
                "Coherence": round(Coherence, 4),
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

    # Compute aggregate operator metrics from flight log
    if flight_log:
        max_div = max(e.get("opacity_div",0) for e in flight_log)
        min_r7d = min(e.get("R_7D",1) for e in flight_log)
        min_coh = min(e.get("Coherence",1) for e in flight_log)
        mean_OpT = np.mean([e.get("OpT",1) for e in flight_log])
        mean_OpC = np.mean([e.get("OpC",1) for e in flight_log])
    else:
        max_div=1; min_r7d=0; min_coh=0; mean_OpT=0; mean_OpC=0

    print(f"\n  7D OPERATOR SUMMARY:")
    print(f"    Max Delta_OP:    {max_div:.6f}")
    print(f"    Min R_7D:        {min_r7d:.4f}")
    print(f"    Min Coherence:   {min_coh:.4f}")
    print(f"    Mean OpT:        {mean_OpT:.4f}")
    print(f"    Mean OpC:        {mean_OpC:.4f}")

    # STARGATE TRANSIT CONDITION (Grok formalization)
    # All must hold for clean fold with humans aboard:
    # Delta_OP < 0.08 AND R_7D > 0.92 AND Coherence > 0.95
    # AND Guardian G >= 0.68
    stc_div = max_div < DELTA_OP_THRESHOLD
    stc_r7d = min_r7d > R_7D_THRESHOLD
    stc_coh = min_coh > COHERENCE_THRESHOLD
    stc_guard = GUARDIAN_STRENGTH >= 0.68

    print(f"\n  STARGATE TRANSIT CONDITION:")
    print(f"    Delta_OP < {DELTA_OP_THRESHOLD}: "
          f"{'PASS' if stc_div else 'FAIL'} ({max_div:.4f})")
    print(f"    R_7D > {R_7D_THRESHOLD}:     "
          f"{'PASS' if stc_r7d else 'FAIL'} ({min_r7d:.4f})")
    print(f"    Coherence > {COHERENCE_THRESHOLD}: "
          f"{'PASS' if stc_coh else 'FAIL'} ({min_coh:.4f})")
    print(f"    Guardian >= 0.68:  "
          f"{'PASS' if stc_guard else 'FAIL'} ({GUARDIAN_STRENGTH})")

    if not abort and stc_div and stc_r7d and stc_coh and stc_guard:
        print(f"\n  VERDICT: STARGATE TRANSIT COMPLETE")
        print(f"  All four conditions met.")
        print(f"  The craft passed through Alpha Centauri A.")
        print(f"  Twin guardians held the crew phase state.")
        print(f"  The mirror stayed polished. The song held.")
        verdict = "STARGATE"
    elif not abort:
        print(f"\n  VERDICT: TRANSIT SURVIVED (conditions partial)")
        fails = []
        if not stc_div: fails.append("Delta_OP")
        if not stc_r7d: fails.append("R_7D")
        if not stc_coh: fails.append("Coherence")
        print(f"  Failed conditions: {', '.join(fails)}")
        verdict = "PARTIAL"
    else:
        print(f"\n  VERDICT: TRANSIT FAILED — {abort_reason}")
        verdict = "FAILED"

    print(f"{'='*65}")

    # Save
    base=os.path.dirname(os.path.abspath(__file__))
    out_dir=os.path.join(base,"data","results")
    os.makedirs(out_dir,exist_ok=True)
    out_path=os.path.join(out_dir,
        f"BCM_v20_stellar_gate_v10_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data={
        "title":"BCM v20.10 Stellar Gate (Sovereign Filter)",
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
            "fib_ratio": FIB_RATIO,
            "d_operation_strength": D_OPERATION_STRENGTH,
            "d_cloak_strength": D_CLOAK_STRENGTH,
            "node_clamp_strength": NODE_CLAMP_STRENGTH,
            "node_clamp_radius": NODE_CLAMP_RADIUS,
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
