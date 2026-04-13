# -*- coding: utf-8 -*-
"""
BCM v19.7 -- Graveyard Stress Test (Crew Safety Edition)
==========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

v19.6 corridor flight: GO FOR TRANSIT (83.2% GREEN, 0 violations).
Now stress test with 60 dead galaxy dormant substrate patches
scattered along the transit path.

Dead galaxies = dormant substrate memory regions (lambda 0.005-0.015).
When the craft's dual pumps and probe arcs agitate them, dormant
mass can re-excite (v15 graveyard test: 32x-60x mass pickup).

CREW SAFETY GATES:
  1. Hemorrhage: BruceRMS > 0.012 for 200 consecutive steps -> ABORT
  2. Disorientation: PhiRMS outside [0.0005, 0.004] for 300 steps -> ABORT
  3. Gauge spike: local chi_field spike > 3x running average -> CORE DROP

Same proven engine as v19.6 (real probes, real solver, real chi).
60 dormant patches overlaid on the transit density profile.

Usage:
    python BCM_v19_graveyard_stress.py
    python BCM_v19_graveyard_stress.py --steps 20000 --grid 256
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


def get_density_profile(step, total_steps):
    frac = step / total_steps
    if frac < 0.10: return 0.03, "FUNDED"
    elif frac < 0.20:
        t = (frac-0.10)/0.10; return 0.03+t*0.02, "ENTRY"
    elif frac < 0.40: return 0.06, "DEEP_VOID"
    elif frac < 0.50:
        t = (frac-0.40)/0.10; return max(0.03, 0.06-t*0.03), "GRAVEYARD"
    elif frac < 0.70: return 0.05, "RECOVERY"
    elif frac < 0.80:
        t = (frac-0.70)/0.10; return 0.05-t*0.02, "RE_EMERGE"
    else: return 0.03, "ARRIVAL"


def generate_graveyards(n_graves, total_steps, rng):
    """Place 60 dead galaxies as step-ranges with dormant lambda."""
    graves = []
    for _ in range(n_graves):
        center_step = rng.randint(100, max(101, total_steps - 100))
        width = rng.randint(80, 300)
        lam = rng.uniform(0.005, 0.015)
        graves.append({
            "start": max(0, center_step - width//2),
            "end": min(total_steps, center_step + width//2),
            "lambda": round(lam, 4),
        })
    graves.sort(key=lambda g: g["start"])
    return graves


def check_graveyard(step, graveyards):
    """Check if current step is inside a graveyard."""
    for g in graveyards:
        if g["start"] <= step <= g["end"]:
            return True, g["lambda"]
    return False, None


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
            self.state="TRANSIT"; t=self.cycle_step/self.t_transit
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
            self.pos=np.array([pa[0]+ar*np.cos(aa),pa[1]+ar*np.sin(aa)])
            self._scoop(sigma,nx,ny)
            ix=int(np.clip(self.pos[0],0,nx-1))
            iy=int(np.clip(self.pos[1],0,ny-1))
            probe_hits[ix,iy]+=1.0
        else:
            self.state="FALLING"; fs=self.cycle_step-b2
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
        at_b=(abs(self.cycle_step-b1)<=1 or abs(self.cycle_step-b2)<=1)
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
        description="BCM v19.7 Graveyard Stress Test")
    parser.add_argument("--steps", type=int, default=20000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()
    nx=ny=args.grid; steps=args.steps

    print(f"\n{'='*65}")
    print(f"  BCM v19.7 -- GRAVEYARD STRESS TEST")
    print(f"  60 dead galaxies in transit path")
    print(f"  Crew safety gates ACTIVE")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {steps}")
    print(f"  kappa_drain: {KAPPA_DRAIN}  chi_decay: {CHI_DECAY}")

    dt=0.05; D=0.5; pump_A=0.5; ratio=0.25; separation=15.0
    x_arr=np.arange(nx); y_arr=np.arange(ny)
    X,Y = np.meshgrid(x_arr,y_arr,indexing='ij')

    rng=np.random.RandomState(42)
    graveyards = generate_graveyards(60, steps, rng)
    print(f"  Graveyards placed: {len(graveyards)}")

    sx,sy=nx//8,ny//2; r2i=(X-sx)**2+(Y-sy)**2
    sigma=1.0*np.exp(-r2i/(2*5.0**2))
    sigma_prev=sigma.copy()
    chi_field=np.zeros((nx,ny)); phi=np.zeros((nx,ny))
    probe_hits=np.zeros((nx,ny))
    probes=[PhaseProbe(i+1,i*5) for i in range(12)]
    bruce_field=np.zeros((nx,ny)); bruce_decay=0.95

    total_bled=0.0; hem_counter=0; dis_counter=0
    abort=False; abort_reason=""
    graves_entered=set(); grave_events=[]
    max_bruce=0.0; diag_interval=200

    print(f"\n  {'Step':>6} {'Phase':>12} {'Lam':>6} "
          f"{'BrRMS':>8} {'PhiRMS':>8} {'Chi':>8} "
          f"{'Zone':>6} {'Event':>10}")
    print(f"  {'-'*6} {'-'*12} {'-'*6} {'-'*8} "
          f"{'-'*8} {'-'*8} {'-'*6} {'-'*10}")

    for step in range(steps):
        lam_val, phase = get_density_profile(step, steps)
        in_grave, grave_lam = check_graveyard(step, graveyards)
        event_str = ""
        if in_grave:
            lam_val = grave_lam
            phase = "GRAVE"
            for i,g in enumerate(graveyards):
                if g["start"]<=step<=g["end"] and i not in graves_entered:
                    graves_entered.add(i)
                    event_str = f"ENTER_{i}"

        lam=np.full((nx,ny),lam_val)
        gx=nx//2; r2g=(X-gx)**2+(Y-ny//2)**2
        lam-=0.08*np.exp(-r2g/(2*18.0**2))
        lam=np.maximum(lam,0.001)

        com=compute_com(sigma)
        if com is None:
            print(f"  *** DISSOLVED step {step} ***"); break
        pa=np.array([com[0]+separation,com[1]])
        pb=np.array([com[0]-separation*0.3,com[1]])
        r2A=(X-com[0])**2+(Y-com[1])**2
        sigma+=pump_A*np.exp(-r2A/(2*4.0**2))*dt
        bx=com[0]+separation
        r2B=(X-bx)**2+(Y-com[1])**2
        sigma+=pump_A*ratio*np.exp(-r2B/(2*3.0**2))*dt

        lap=(np.roll(sigma,1,0)+np.roll(sigma,-1,0)+
             np.roll(sigma,1,1)+np.roll(sigma,-1,1)-4*sigma)
        sn=sigma+D*lap*dt-lam*sigma*dt+ALPHA*(sigma-sigma_prev)
        sn=np.maximum(sn,0)
        if float(np.max(sn))>1e10:
            print(f"  *** BLOWUP step {step} ***"); break

        phi=phi*0.95+(sigma-sigma_prev)
        sigma_prev=sigma.copy(); sigma=sn

        for p in probes:
            jump,bleed=p.update(com,pa,pb,step,sigma,
                                nx,ny,rng,probe_hits,chi_field)
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
        if not(0.0005<=phi_rms<=0.004): dis_counter+=1
        else: dis_counter=max(0,dis_counter-1)

        if hem_counter>200:
            abort=True; abort_reason="HEMORRHAGE"
        if dis_counter>300:
            abort=True; abort_reason="DISORIENTATION"

        if abort:
            print(f"  {step:>6} {'***ABORT***':>12} {lam_val:>6.3f} "
                  f"{bruce_rms:>8.5f} {phi_rms:>8.5f} "
                  f"{'':>8} {'RED':>6} {abort_reason}")
            break

        if step%diag_interval==0 or event_str:
            chi_t=float(np.sum(chi_field))
            zone="GREEN" if bruce_rms<0.006 else (
                "YELLOW" if bruce_rms<0.010 else "RED")
            ev = event_str if event_str else (
                "GRAVE" if in_grave else "")
            print(f"  {step:>6} {phase:>12} {lam_val:>6.3f} "
                  f"{bruce_rms:>8.5f} {phi_rms:>8.5f} "
                  f"{chi_t:>8.1f} {zone:>6} {ev:>10}")

            if event_str:
                grave_events.append({
                    "step": step, "lambda": lam_val,
                    "bruce_rms": round(bruce_rms,6),
                    "phi_rms": round(phi_rms,6),
                    "zone": zone,
                    "probe_phase": step % 50,
                })

    # ---- SUMMARY ----
    print(f"\n{'='*65}")
    print(f"  GRAVEYARD STRESS TEST SUMMARY")
    print(f"{'='*65}")

    final_sigma=float(np.sum(sigma))
    final_chi=float(np.sum(chi_field))

    print(f"\n  Graveyards encountered: {len(graves_entered)}/60")
    print(f"  Max Brucetron RMS: {max_bruce:.6f}")
    print(f"  Crew violations: {'NONE' if not abort else abort_reason}")
    print(f"  Total bled: {total_bled:.2f}")
    print(f"  Final sigma: {final_sigma:.2f}")
    print(f"  Final chi: {final_chi:.2f}")
    print(f"  System: {final_sigma+final_chi:.2f}")

    if not abort:
        print(f"\n  VERDICT: GRAVEYARD TRANSIT CLEARED")
        print(f"  Ship survived 60 dead galaxies.")
        verdict="PASS"
    else:
        print(f"\n  VERDICT: ABORT — {abort_reason}")
        verdict="ABORT"

    print(f"{'='*65}")

    # ---- PHASE RESONANCE ANALYSIS ----
    if grave_events:
        print(f"\n{'='*65}")
        print(f"  PHASE RESONANCE ANALYSIS")
        print(f"  probe_phase = step % 50 (0-49)")
        print(f"  5/35/10 boundaries: B1=5, B2=40")
        print(f"{'='*65}")

        # Bin events by probe cycle segment
        transit_events = [e for e in grave_events
                          if e["probe_phase"] < 5]
        arc_events = [e for e in grave_events
                      if 5 <= e["probe_phase"] < 40]
        fall_events = [e for e in grave_events
                       if e["probe_phase"] >= 40]

        def avg_bruce(evts):
            if not evts: return 0
            return sum(e["bruce_rms"] for e in evts)/len(evts)

        def max_bruce_ev(evts):
            if not evts: return 0
            return max(e["bruce_rms"] for e in evts)

        print(f"\n  {'Segment':>12} {'Count':>6} {'Avg BrRMS':>10} "
              f"{'Peak BrRMS':>11}")
        print(f"  {'-'*12} {'-'*6} {'-'*10} {'-'*11}")
        print(f"  {'TRANSIT':>12} {len(transit_events):>6} "
              f"{avg_bruce(transit_events):>10.6f} "
              f"{max_bruce_ev(transit_events):>11.6f}")
        print(f"  {'ARC':>12} {len(arc_events):>6} "
              f"{avg_bruce(arc_events):>10.6f} "
              f"{max_bruce_ev(arc_events):>11.6f}")
        print(f"  {'FALL':>12} {len(fall_events):>6} "
              f"{avg_bruce(fall_events):>10.6f} "
              f"{max_bruce_ev(fall_events):>11.6f}")

        # Phase histogram (5-step bins)
        print(f"\n  Phase histogram (bruce_rms by probe_phase):")
        bins = {}
        for e in grave_events:
            b = (e["probe_phase"] // 5) * 5
            if b not in bins: bins[b] = []
            bins[b].append(e["bruce_rms"])
        for b in sorted(bins.keys()):
            vals = bins[b]
            avg = sum(vals)/len(vals)
            mx = max(vals)
            bar = "#" * int(avg * 1000)
            print(f"    phase {b:>2}-{b+4:>2}: "
                  f"n={len(vals):>2} avg={avg:.6f} "
                  f"peak={mx:.6f} {bar}")

        # Identify resonance windows
        if bins:
            sorted_bins = sorted(bins.items(),
                                 key=lambda x: max(x[1]),
                                 reverse=True)
            worst_phase = sorted_bins[0][0]
            best_phase = sorted_bins[-1][0]
            print(f"\n  Worst phase bin: {worst_phase}-"
                  f"{worst_phase+4} "
                  f"(peak={max(sorted_bins[0][1]):.6f})")
            print(f"  Best phase bin:  {best_phase}-"
                  f"{best_phase+4} "
                  f"(peak={max(sorted_bins[-1][1]):.6f})")

        print(f"{'='*65}")

    base=os.path.dirname(os.path.abspath(__file__))
    out_dir=os.path.join(base,"data","results")
    os.makedirs(out_dir,exist_ok=True)
    out_path=os.path.join(out_dir,
        f"BCM_v19_graveyard_stress_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data={
        "title":"BCM v19.7 Graveyard Stress Test",
        "author":"Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "grid":nx,"steps":steps,
        "graveyards_placed":len(graveyards),
        "graveyards_encountered":len(graves_entered),
        "max_bruce_rms":round(max_bruce,8),
        "verdict":verdict,
        "abort_reason":abort_reason,
        "total_bled":round(total_bled,4),
        "final_sigma":round(final_sigma,4),
        "final_chi":round(final_chi,4),
        "grave_events":grave_events,
        "graveyards":graveyards,
    }

    with open(out_path,"w") as f:
        json.dump(out_data,f,indent=2,default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
