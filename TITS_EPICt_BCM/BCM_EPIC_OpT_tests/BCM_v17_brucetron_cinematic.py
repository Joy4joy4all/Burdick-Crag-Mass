# -*- coding: utf-8 -*-
"""
BCM v17 -- Brucetron Cinematic (6-Pane Phase Viewer)
======================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Gemini's attack: "If the Brucetron says the crew dies in
50k steps, we don't fix the crew; we fix the growth rate."

6 PANES showing the Brucetron in action:
  1. Sigma field + craft + probes (transport reality)
  2. Brucetron field (phase residue accumulation map)
  3. Delta Brucetron (where residue is being INJECTED)
  4. Cycle phase indicator (where in 5/35/10 are we?)
  5. Brucetron energy timeline (growth curve live)
  6. Phase debt + mission clock (time to threshold)

WHAT WE'RE LOOKING FOR:
  - Phase pooling: does residue stay under the ship
    or leave a wake? (wake = environmental damage)
  - Harmonic interaction: does the 0.010 heartbeat
    pulse visually in the Brucetron field?
  - Divergence point: where in the 5/35/10 cycle does
    the Brucetron energy spike?
  - Freeboard: is there a natural buffer zone where
    phase energy could be relieved? (chi candidate)

Usage:
    python BCM_v17_brucetron_cinematic.py
    python BCM_v17_brucetron_cinematic.py --grid 128 --speed 2
"""

import numpy as np
import os
import math
import argparse

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


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
# BRUCETRON PROBE
# ═══════════════════════════════════════════════════════

class BruceProbe:
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
        self.last_jump = 0.0
        self.segment_name = "TRANSIT"

    def update(self, com, pa, pb, step, sigma, nx, ny, rng):
        eff = step - self.eject_offset
        if eff < 0:
            self.pos = com.copy()
            self.prev_pos = self.pos.copy()
            self.last_jump = 0.0
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
            self.segment_name = "TRANSIT"
            t = self.cycle_step / self.t_transit
            self.pos = pb + t * (pa - pb)
        elif self.cycle_step < b2:
            self.state = "EJECTED"
            self.segment_name = "ARC"
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
            self.segment_name = "FALL"
            fs = self.cycle_step - b2
            tf = fs / self.t_fall
            self.pos = self.prev_pos + tf * (pb - self.prev_pos)
            if fs >= self.t_fall - 1:
                self._deposit(sigma, pb, nx, ny)

        disp = float(np.linalg.norm(self.pos - self.prev_pos))
        at_boundary = (abs(self.cycle_step - b1) <= 1 or
                       abs(self.cycle_step - b2) <= 1)
        self.last_jump = disp if at_boundary else 0.0
        return self.last_jump

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
# CINEMATIC
# ═══════════════════════════════════════════════════════

def run_cinematic(grid=128, speed=2):
    if not HAS_MPL:
        print("  matplotlib required.")
        return

    nx = ny = grid
    dt = 0.05; D = 0.5; void_lambda = 0.10
    pump_A = 0.5; ratio = 0.25; alpha = 0.80
    separation = 15.0

    rng = np.random.RandomState(42)
    x_arr = np.arange(nx); y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny//2)**2
    lam -= 0.08 * np.exp(-r2g / (2*18.0**2))
    lam = np.maximum(lam, 0.001)

    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2*5.0**2))
    sigma_prev = sigma.copy()
    initial_com = compute_com(sigma)

    probes = [BruceProbe(i+1, i*5) for i in range(12)]

    bruce_field = np.zeros((nx, ny))
    bruce_prev = np.zeros((nx, ny))
    bruce_decay = 0.95

    t_bruce_energy = []
    t_debt = []
    t_jump_rate = []
    cumulative_debt = 0.0

    # Danger threshold (from growth bound)
    debt_danger = 112187.0

    # ── FIGURE ──
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.patch.set_facecolor('#080a0e')
    fig.suptitle(
        "BCM v17 — BRUCETRON CINEMATIC\n"
        "Stephen Justin Burdick Sr. — Emerald Entities LLC",
        color='#ff9944', fontsize=11, fontweight='bold')

    ax_sig = axes[0, 0]    # sigma
    ax_bruce = axes[0, 1]  # brucetron field
    ax_delta = axes[0, 2]  # delta brucetron
    ax_cycle = axes[1, 0]  # cycle phase
    ax_energy = axes[1, 1] # energy timeline
    ax_debt = axes[1, 2]   # debt + mission clock

    for ax in axes.flat:
        ax.set_facecolor('#0c0e14')
        ax.tick_params(colors='#404040', labelsize=6)

    # Pane 1: Sigma
    ax_sig.set_title("SIGMA FIELD", color='#ff9944', fontsize=9)
    im_sig = ax_sig.imshow(sigma.T, cmap='inferno',
                           origin='lower', extent=[0,nx,0,ny],
                           vmin=0, vmax=0.5)
    craft_dot, = ax_sig.plot([], [], 'o', color='#ff9944',
                              markersize=7, zorder=10)
    probe_dots, = ax_sig.plot([], [], '.', color='#60aaff',
                               markersize=3, zorder=9)

    # Pane 2: Brucetron field
    ax_bruce.set_title("BRUCETRON FIELD", color='#ff4444',
                       fontsize=9)
    im_bruce = ax_bruce.imshow(bruce_field.T, cmap='hot',
                               origin='lower',
                               extent=[0,nx,0,ny],
                               vmin=0, vmax=0.01)

    # Pane 3: Delta Brucetron
    ax_delta.set_title("DELTA BRUCETRON (injection)",
                       color='#40ccaa', fontsize=9)
    im_delta = ax_delta.imshow(np.zeros((nx,ny)).T, cmap='bwr',
                               origin='lower',
                               extent=[0,nx,0,ny],
                               vmin=-0.001, vmax=0.001)

    # Pane 4: Cycle phase indicator
    ax_cycle.set_title("CYCLE PHASE", color='#60aaff',
                       fontsize=9)
    ax_cycle.set_xlim(0, 50)
    ax_cycle.set_ylim(0, 3)
    ax_cycle.set_yticks([0.5, 1.5, 2.5])
    ax_cycle.set_yticklabels(['FALL', 'ARC', 'TRANSIT'],
                             color='#a0a0a0', fontsize=8)
    # Phase regions
    ax_cycle.axvspan(0, 5, color='#224466', alpha=0.3)
    ax_cycle.axvspan(5, 40, color='#446622', alpha=0.3)
    ax_cycle.axvspan(40, 50, color='#664422', alpha=0.3)
    ax_cycle.axvline(5, color='#ff4444', linewidth=2,
                     linestyle='--', label='T→A boundary')
    ax_cycle.axvline(40, color='#ff4444', linewidth=2,
                     linestyle='--', label='A→F boundary')
    cycle_marker, = ax_cycle.plot([], [], 'v', color='#ff9944',
                                  markersize=12, zorder=10)
    jump_bar = ax_cycle.bar([0], [0], width=1,
                            color='#ff4444', alpha=0.5)[0]
    cycle_text = ax_cycle.text(25, 2.8, "", ha='center',
                               color='#e0e8f0', fontsize=10,
                               fontweight='bold')

    # Pane 5: Energy timeline
    ax_energy.set_title("BRUCETRON ENERGY", color='#ff4444',
                        fontsize=9)
    ax_energy.set_xlabel("Step", color='#808080', fontsize=7)
    line_energy, = ax_energy.plot([], [], '-', color='#ff4444',
                                  linewidth=1.5)

    # Pane 6: Debt + mission clock
    ax_debt.set_title("PHASE DEBT / MISSION CLOCK",
                      color='#ffbb44', fontsize=9)
    ax_debt.set_xlabel("Step", color='#808080', fontsize=7)
    line_debt, = ax_debt.plot([], [], '-', color='#ffbb44',
                              linewidth=1.5, label='Debt')
    ax_debt.axhline(debt_danger, color='#ff4444',
                    linestyle='--', linewidth=1, alpha=0.5,
                    label='Danger')
    ax_debt.legend(fontsize=7, loc='upper left',
                   facecolor='#10131a', edgecolor='#404040',
                   labelcolor='#a0a0a0')
    clock_text = ax_debt.text(0.98, 0.95, "",
                              transform=ax_debt.transAxes,
                              ha='right', va='top',
                              color='#ffbb44', fontsize=10,
                              fontweight='bold',
                              fontfamily='monospace')

    step_state = {"s": 0}

    def animate(frame):
        nonlocal sigma, sigma_prev, bruce_field, bruce_prev
        nonlocal cumulative_debt

        s = step_state["s"]

        com = compute_com(sigma)
        if com is None:
            return []

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
        sn = np.maximum(sn, 0)
        sigma_prev = sigma.copy()
        sigma = sn

        # Probes + Brucetron injection
        bruce_prev = bruce_field.copy()
        total_jump = 0.0
        for p in probes:
            jump = p.update(com, pa, pb, s, sigma,
                            nx, ny, rng)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx-1))
                iy = int(np.clip(p.pos[1], 0, ny-1))
                bruce_field[ix, iy] += jump * 0.1
                total_jump += jump

        bruce_field *= bruce_decay
        cumulative_debt += total_jump

        bruce_e = float(np.sum(bruce_field**2))
        delta_bruce = bruce_field - bruce_prev

        t_bruce_energy.append(bruce_e)
        t_debt.append(cumulative_debt)
        t_jump_rate.append(total_jump)

        # ── VISUALS ──

        # Pane 1: Sigma
        vmax_s = max(0.05, float(np.max(sigma)) * 0.8)
        im_sig.set_array(sigma.T)
        im_sig.set_clim(0, vmax_s)
        craft_dot.set_data([com[1]], [com[0]])
        px = [p.pos[1] for p in probes if p.state == "EJECTED"]
        py = [p.pos[0] for p in probes if p.state == "EJECTED"]
        probe_dots.set_data(px, py)

        # Pane 2: Brucetron field
        vmax_b = max(0.001, float(np.max(bruce_field)) * 0.8)
        im_bruce.set_array(bruce_field.T)
        im_bruce.set_clim(0, vmax_b)

        # Pane 3: Delta Brucetron
        dmax = max(0.0001, float(np.max(np.abs(delta_bruce)))*0.8)
        im_delta.set_array(delta_bruce.T)
        im_delta.set_clim(-dmax, dmax)

        # Pane 4: Cycle phase
        # Use first probe's cycle step as representative
        cs = probes[0].cycle_step if probes else 0
        seg = probes[0].segment_name if probes else "TRANSIT"
        seg_y = {"TRANSIT": 2.5, "ARC": 1.5, "FALL": 0.5}.get(
            seg, 1.5)
        cycle_marker.set_data([cs], [seg_y])

        # Jump bar at boundaries
        if total_jump > 0:
            jump_bar.set_x(cs - 0.5)
            jump_bar.set_height(3)
            jump_bar.set_alpha(min(1.0, total_jump / 10.0))
        else:
            jump_bar.set_height(0)

        seg_col = {"TRANSIT": '#4488cc', "ARC": '#44cc44',
                   "FALL": '#cc8844'}.get(seg, '#ffffff')
        cycle_text.set_text(f"{seg} (step {cs}/50)")
        cycle_text.set_color(seg_col)

        # Pane 5: Energy
        steps_arr = list(range(len(t_bruce_energy)))
        line_energy.set_data(steps_arr, t_bruce_energy)
        if steps_arr:
            ax_energy.set_xlim(0, max(100, steps_arr[-1]))
            ax_energy.set_ylim(0, max(0.1,
                               max(t_bruce_energy) * 1.1))

        # Pane 6: Debt + clock
        line_debt.set_data(steps_arr, t_debt)
        if steps_arr:
            ax_debt.set_xlim(0, max(100, steps_arr[-1]))
            ax_debt.set_ylim(0, max(debt_danger * 0.1,
                             max(t_debt) * 1.2))

        # Mission clock
        if cumulative_debt > 0:
            steps_to_danger = (debt_danger - cumulative_debt) / (
                total_jump + 0.001)
            pct_used = (cumulative_debt / debt_danger) * 100
            clock_text.set_text(
                f"Debt: {cumulative_debt:.0f}\n"
                f"Limit: {debt_danger:.0f}\n"
                f"Used: {pct_used:.1f}%")
            if pct_used > 50:
                clock_text.set_color('#ff4444')
            elif pct_used > 25:
                clock_text.set_color('#ffbb44')
            else:
                clock_text.set_color('#40ee70')

        step_state["s"] += speed
        return []

    ani = FuncAnimation(fig, animate, frames=5000 // speed,
                        interval=40, blit=False, repeat=False)
    plt.tight_layout(rect=[0, 0.02, 1, 0.94])
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="BCM v17 Brucetron Cinematic")
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--speed", type=int, default=2)
    args = parser.parse_args()

    print(f"\n{'='*55}")
    print(f"  BCM v17 -- BRUCETRON CINEMATIC")
    print(f"  See the phase debt accumulate")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*55}")
    print(f"  Grid: {args.grid}  Speed: {args.speed}x")
    print(f"  Panes: sigma | brucetron | delta")
    print(f"         cycle | energy | debt clock")
    print(f"{'='*55}\n")

    run_cinematic(grid=args.grid, speed=args.speed)


if __name__ == "__main__":
    main()
