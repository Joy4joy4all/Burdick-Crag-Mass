# -*- coding: utf-8 -*-
"""
BCM v20 -- Stellar Transit Test (7D Coherence)
=================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

At 12,000c the craft operates on the 2D substrate.
Stars are 3D projections ON the substrate. The craft
is a different pattern on the same substrate. Two
patterns on the same sheet don't collide -- they
overlap.

THIS TEST: Fly the craft straight through Alpha
Centauri's substrate field. The star has:
  - Active tachocline pump (m=1 mode, v4)
  - High sigma (fully funded substrate)
  - Strong lambda (low decay -- well maintained)
  - Resonance Hamiltonian H(m) active

Does the craft's coherence survive passage through
a live stellar substrate field? Three regimes:

Phase 1: APPROACH (void substrate, lambda=0.05)
Phase 2: STELLAR ENTRY (lambda drops to 0.001,
         sigma spikes from stellar pump)
Phase 3: CORE TRANSIT (maximum stellar funding,
         lambda=0.0005, sigma at peak)
Phase 4: STELLAR EXIT (lambda rises back to 0.005)
Phase 5: RECOVERY (void substrate, lambda=0.05)

If coherence holds: 3D objects are transparent to
substrate transit. The gate works through stars.

If coherence breaks: the stellar pump disrupts the
craft's pattern. 3D objects are obstacles even on
the substrate.

Crew safety gates from v19 active throughout.

Usage:
    python BCM_v20_stellar_transit.py
    python BCM_v20_stellar_transit.py --steps 20000 --grid 256
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

    print(f"\n  {'Step':>6} {'Phase':>12} {'Lam':>8} "
          f"{'Pump':>6} {'BrRMS':>8} {'PhiRMS':>8} "
          f"{'Chi':>8} {'Zone':>6}")
    print(f"  {'-'*6} {'-'*12} {'-'*8} {'-'*6} "
          f"{'-'*8} {'-'*8} {'-'*8} {'-'*6}")

    for step in range(steps):
        lam_val, stellar_pump, phase = get_stellar_profile(
            step, steps)

        lam=np.full((nx,ny),lam_val)
        gx=nx//2; r2g=(X-gx)**2+(Y-ny//2)**2
        lam-=0.08*np.exp(-r2g/(2*18.0**2))
        lam=np.maximum(lam,0.001)

        com=compute_com(sigma)
        if com is None:
            print(f"  *** DISSOLVED step {step} ***"); break
        pa=np.array([com[0]+separation,com[1]])
        pb=np.array([com[0]-separation*0.3,com[1]])

        # Craft pumps
        r2A=(X-com[0])**2+(Y-com[1])**2
        sigma+=pump_A*np.exp(-r2A/(2*4.0**2))*dt
        bx=com[0]+separation
        r2B=(X-bx)**2+(Y-com[1])**2
        sigma+=pump_A*ratio*np.exp(-r2B/(2*3.0**2))*dt

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

            print(f"  {step:>6} {phase:>12} "
                  f"{lam_val:>8.4f} {stellar_pump:>6.1f} "
                  f"{bruce_rms:>8.5f} {phi_rms:>8.5f} "
                  f"{chi_t:>8.1f} {zone:>6}")

            flight_log.append({
                "step": step, "phase": phase,
                "lambda": round(lam_val,4),
                "stellar_pump": round(stellar_pump,2),
                "bruce_rms": round(bruce_rms,6),
                "phi_rms": round(phi_rms,6),
                "chi_total": round(chi_t,4),
                "zone": zone,
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

    if not abort:
        if max_bruce < 0.010:
            print(f"\n  VERDICT: STELLAR TRANSIT CLEAR")
            print(f"  The craft passed through Alpha Centauri A.")
            print(f"  3D mass is TRANSPARENT on the 2D substrate.")
            print(f"  7D coherence HOLDS through stellar field.")
            verdict="TRANSPARENT"
        else:
            print(f"\n  VERDICT: STELLAR TRANSIT SURVIVED")
            print(f"  Craft coherent but stressed.")
            print(f"  3D mass creates substrate turbulence")
            print(f"  but does not block transit.")
            verdict="STRESSED"
    else:
        print(f"\n  VERDICT: STELLAR TRANSIT FAILED")
        print(f"  Craft lost coherence inside stellar field.")
        print(f"  3D mass IS an obstacle on the substrate.")
        verdict="BLOCKED"

    print(f"{'='*65}")

    # Save
    base=os.path.dirname(os.path.abspath(__file__))
    out_dir=os.path.join(base,"data","results")
    os.makedirs(out_dir,exist_ok=True)
    out_path=os.path.join(out_dir,
        f"BCM_v20_stellar_transit_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data={
        "title":"BCM v20 Stellar Transit Test",
        "author":"Stephen Justin Burdick Sr. -- "
                 "Emerald Entities LLC",
        "purpose":"Fly through Alpha Centauri A. "
                  "Test 7D substrate coherence through "
                  "live stellar field.",
        "target":"Alpha Centauri A (m=1 tachocline)",
        "c_substrate":"12,000c",
        "grid":nx,"steps":steps,
        "max_bruce_rms":round(max_bruce,8),
        "verdict":verdict,
        "abort_reason":abort_reason,
        "total_bled":round(total_bled,4),
        "final_sigma":round(final_sigma,4),
        "final_chi":round(final_chi,4),
        "flight_log":flight_log,
    }

    with open(out_path,"w") as f:
        json.dump(out_data,f,indent=2,default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
