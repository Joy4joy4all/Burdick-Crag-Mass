# -*- coding: utf-8 -*-
"""
BCM v20.4 -- Stellar Gate (7D Gradient Shadow)
=================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

v20.3 APD couldn't hold the heartbeat because the
SPATIAL cause was undetected: Pump A enters the stellar
field before Pump B. For those steps, the dumbbell is
two uncoupled singulars at different substrate states.
The 4D/5D entanglement cracks. Dipole casualty.

Stephen Burdick Sr.'s correction (April 11, 2026):
  "PumpA arrives on one side of the fold before PumpB.
   Any fraction crossing is a cause for dipole casualty.
   The fold holds a pump singular and B singular for a
   fraction of a second. In 7D you must account for the
   gradient shadow of the object to govern transition."

No AI identified this. Four AIs diagnosed phase
coherence loss. The Foreman identified the spatial
root cause: the craft's own geometry splits at the
fold boundary.

THIS TEST: Add the 7D gradient shadow detector.
Measures substrate state difference between Pump A
and Pump B positions (grad_shadow = sigma[PA] - sigma[PB]).
When gradient exceeds threshold, the guardian
temporarily equalizes pump ratios to make the dumbbell
symmetric at the boundary crossing. Drive ratio (8.4:1)
restores once both pumps are on the same side.

New frozen constant:
  GRAD_SHADOW_THRESHOLD = 0.15 (dipole break limit)
  SYMMETRIC_RATIO = 0.80 (equalized pump ratio)

Usage:
    python BCM_v20_stellar_gate_v4.py
    python BCM_v20_stellar_gate_v4.py --steps 20000 --grid 256
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

# ---- 7D GRADIENT SHADOW CONSTANTS (Burdick v20.4) ----
# The gradient shadow is the substrate state difference
# between Pump A and Pump B. When A enters a phase
# boundary before B, the dipole cracks. The guardian
# must equalize the pumps at the crossing.
GRAD_SHADOW_THRESHOLD = 0.15   # dipole break limit
SYMMETRIC_RATIO = 0.80         # equalized pump ratio
SHADOW_SAMPLE_R = 5            # sampling radius at pump


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

        # ---- 7D GRADIENT SHADOW (Burdick v20.4) ----
        # Measure substrate state at Pump A vs Pump B.
        # If A enters a phase boundary before B, the
        # dumbbell becomes two uncoupled singulars.
        # The 7D guardian must see this shadow and
        # equalize the pumps at the crossing.
        #
        # grad_shadow = mean(sigma near PA) - mean(sigma near PB)
        # Normalized by max to get fractional difference.
        ix_a = int(np.clip(pa[0], SHADOW_SAMPLE_R, nx-SHADOW_SAMPLE_R-1))
        iy_a = int(np.clip(pa[1], SHADOW_SAMPLE_R, ny-SHADOW_SAMPLE_R-1))
        ix_b = int(np.clip(pb[0], SHADOW_SAMPLE_R, nx-SHADOW_SAMPLE_R-1))
        iy_b = int(np.clip(pb[1], SHADOW_SAMPLE_R, ny-SHADOW_SAMPLE_R-1))

        sr = SHADOW_SAMPLE_R
        sig_at_a = float(np.mean(
            sigma[ix_a-sr:ix_a+sr, iy_a-sr:iy_a+sr]))
        sig_at_b = float(np.mean(
            sigma[ix_b-sr:ix_b+sr, iy_b-sr:iy_b+sr]))

        sig_max_ab = max(abs(sig_at_a), abs(sig_at_b), 1e-10)
        grad_shadow = abs(sig_at_a - sig_at_b) / sig_max_ab

        # 7D GUARDIAN RESPONSE: equalize pumps at boundary
        shadow_active = grad_shadow > GRAD_SHADOW_THRESHOLD
        if shadow_active:
            # Temporarily make dumbbell symmetric
            # Both pumps run at matched ratio until both
            # are on the same side of the fold
            ratio_current = SYMMETRIC_RATIO
            # Also pre-load chi with the differential energy
            shadow_energy = abs(sig_at_a - sig_at_b) * 0.1
            chi_field[ix_a-sr:ix_a+sr, iy_a-sr:iy_a+sr] += (
                shadow_energy / max(1, (2*sr)**2))
        else:
            ratio_current = ratio  # normal 8.4:1 drive

        # Craft pumps (using ratio_current from shadow)
        r2A=(X-com[0])**2+(Y-com[1])**2
        sigma+=pump_A*np.exp(-r2A/(2*4.0**2))*dt
        bx=com[0]+separation
        r2B=(X-bx)**2+(Y-com[1])**2
        sigma+=pump_A*ratio_current*np.exp(-r2B/(2*3.0**2))*dt

        # STELLAR PUMP (Alpha Centauri tachocline)
        # Adds substrate funding at grid center
        # This is the star's own SMBH-analog pump
        if stellar_pump > 0:
            star_x = nx // 2
            star_y = ny // 2
            r2_star = (X-star_x)**2 + (Y-star_y)**2
            # m=1 mode (Alpha Centauri, v4)
            theta_star = np.arctan2(Y-star_y, X-star_x)
            stellar_source = (stellar_pump *
                np.cos(1 * theta_star) *
                np.exp(-r2_star / (2 * 30.0**2)))
            sigma += stellar_source * dt

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
        if not(0.0005<=phi_rms<=0.006): dis_counter+=1
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
            shd = "SHAD" if shadow_active else ""

            print(f"  {step:>6} {phase:>12} "
                  f"{lam_val:>8.4f} {stellar_pump:>6.1f} "
                  f"{bruce_rms:>8.5f} {phi_rms:>8.5f} "
                  f"{chi_t:>8.1f} {zone:>6} {gate_str:>6}"
                  f" {shd:>4}")

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
                "grad_shadow": round(grad_shadow, 6),
                "shadow_active": shadow_active,
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
        f"BCM_v20_stellar_gate_v4_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data={
        "title":"BCM v20.4 Stellar Gate (7D Gradient Shadow)",
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
            "grad_shadow_threshold": GRAD_SHADOW_THRESHOLD,
            "symmetric_ratio": SYMMETRIC_RATIO,
            "shadow_sample_r": SHADOW_SAMPLE_R,
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
