# -*- coding: utf-8 -*-
"""
BCM v17 -- Multi-Pane Transport Cinematic (Reviewer Mode)
===========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

6 synchronized panes proving causality, not just motion.

  PANE 1: Sigma field + craft + probes (what IS)
  PANE 2: Delta sigma transport map (what CHANGED)
  PANE 3: Control field, no probes (what WOULD happen)
  PANE 4: Transport flow vectors (WHY it moves)
  PANE 5: Navigator sampling map (HOW it decides)
  PANE 6: Accounting timeline (PROOF it conserves)

Two parallel simulations run with identical seed and field:
  Active: pumps + transport probes (scoop/deposit)
  Control: pumps only (no probes)

The control comparison visually kills "it would happen
anyway." The delta map shows causality. The vectors show
mechanism. The accounting shows conservation.

ChatGPT advocate standard: "If someone watches this and
says 'I can see WHY it moves' -- you succeeded."

Usage:
    python BCM_v17_reviewer_cinematic.py
    python BCM_v17_reviewer_cinematic.py --grid 128 --speed 2
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
# TRANSPORT PROBE (scoop/deposit)
# ═══════════════════════════════════════════════════════

class CinemaProbe:
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
        self.total_scooped = 0.0
        self.total_deposited = 0.0
        self.arc_radius = 0.0
        self.t_transit = 5
        self.t_arc = 40
        self.t_fall = 10
        self.danger_reading = False

    def update(self, com, pa, pb, step, sigma, lam,
               nx, ny, rng):
        self.danger_reading = False
        eff = step - self.eject_offset
        if eff < 0:
            self.pos = com.copy()
            self.state = "TRANSIT"
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
                self.arc_radius = amr * (ta * 2)
            else:
                self.arc_radius = amr * (2 - ta * 2)
            ca = bao + ta * 2 * math.pi
            va = round(ca / (2*math.pi/vc)) * (2*math.pi/vc)
            aa = 0.3 * ca + 0.7 * va
            self.pos = np.array([
                pa[0] + self.arc_radius * np.cos(aa),
                pa[1] + self.arc_radius * np.sin(aa)])
            self._scoop(sigma, nx, ny)
            # Check danger
            ix = int(np.clip(self.pos[0], 0, nx-1))
            iy = int(np.clip(self.pos[1], 0, ny-1))
            if lam[ix, iy] < 0.04:
                self.danger_reading = True
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
        w = np.exp(-r2 / (2*self.scoop_r**2))
        loc = sigma[np.ix_(xa, ya)]
        sc = np.minimum(loc * w * self.scoop_eff, loc)
        sc = np.maximum(sc, 0)
        t = float(np.sum(sc))
        sigma[np.ix_(xa, ya)] -= sc
        self.payload += t
        self.total_scooped += t

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
        w = np.exp(-r2 / (2*self.scoop_r**2))
        ws = float(np.sum(w))
        if ws > 1e-15:
            sigma[np.ix_(xa, ya)] += w * (self.payload / ws)
        self.total_deposited += self.payload
        self.payload = 0.0


# ═══════════════════════════════════════════════════════
# PDE STEP (shared between active and control)
# ═══════════════════════════════════════════════════════

def pde_step(sigma, sigma_prev, lam, X, Y, com,
             pump_A, ratio, separation, D, dt, alpha,
             do_pumps=True):
    nx, ny = sigma.shape
    if do_pumps and com is not None:
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
    return sn


# ═══════════════════════════════════════════════════════
# CINEMATIC ENGINE
# ═══════════════════════════════════════════════════════

def run_cinematic(grid=128, speed=1):
    if not HAS_MPL:
        print("  matplotlib required.")
        return

    nx = ny = grid
    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    ratio = 0.25
    alpha = 0.80
    separation = 15.0

    rng_active = np.random.RandomState(42)
    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    # Lambda with grave
    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny//2)**2
    lam -= 0.08 * np.exp(-r2g / (2*18.0**2))
    lam = np.maximum(lam, 0.001)

    # Initial sigma (shared)
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma_init = 1.0 * np.exp(-r2i / (2*5.0**2))
    initial_com = compute_com(sigma_init)

    # ACTIVE state
    sig_a = sigma_init.copy()
    sig_a_prev = sigma_init.copy()
    probes = [CinemaProbe(i+1, i*5) for i in range(12)]

    # CONTROL state (no probes)
    sig_c = sigma_init.copy()
    sig_c_prev = sigma_init.copy()

    # Timeline data
    t_steps = []
    t_drift_a = []
    t_drift_c = []
    t_scooped = []
    t_deposited = []
    t_reactor = []
    reactor = 200.0

    # ── FIGURE: 2x3 grid ──
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.patch.set_facecolor('#080a0e')
    fig.suptitle(
        "BCM v17 — REVIEWER MODE CINEMATIC\n"
        "Stephen Justin Burdick Sr. — Emerald Entities LLC"
        " — GIBUSH Systems",
        color='#ff9944', fontsize=11, fontweight='bold')

    ax_field = axes[0, 0]   # sigma + craft + probes
    ax_delta = axes[0, 1]   # delta sigma (transport map)
    ax_ctrl  = axes[0, 2]   # control (no probes)
    ax_vec   = axes[1, 0]   # transport vectors
    ax_nav   = axes[1, 1]   # navigator sampling
    ax_time  = axes[1, 2]   # accounting timeline

    for ax in axes.flat:
        ax.set_facecolor('#0c0e14')
        ax.tick_params(colors='#404040', labelsize=6)

    # Pane 1: Sigma field
    ax_field.set_title("SIGMA FIELD (Active)", color='#ff9944',
                       fontsize=9)
    im_a = ax_field.imshow(sig_a.T, cmap='inferno',
                           origin='lower', extent=[0,nx,0,ny],
                           vmin=0, vmax=0.5)
    craft_dot, = ax_field.plot([], [], 'o', color='#ff9944',
                               markersize=7, zorder=10)
    probe_dots, = ax_field.plot([], [], '.', color='#60aaff',
                                markersize=3, zorder=9)

    # Pane 2: Delta sigma
    ax_delta.set_title("DELTA SIGMA (Transport Map)",
                       color='#40ccaa', fontsize=9)
    delta_data = np.zeros((nx, ny))
    im_d = ax_delta.imshow(delta_data.T, cmap='bwr',
                           origin='lower', extent=[0,nx,0,ny],
                           vmin=-0.02, vmax=0.02)

    # Pane 3: Control
    ax_ctrl.set_title("CONTROL (No Probes)", color='#a0a0a0',
                      fontsize=9)
    im_c = ax_ctrl.imshow(sig_c.T, cmap='inferno',
                          origin='lower', extent=[0,nx,0,ny],
                          vmin=0, vmax=0.5)
    ctrl_dot, = ax_ctrl.plot([], [], 'o', color='#a0a0a0',
                             markersize=7, zorder=10)

    # Pane 4: Vectors (updated periodically)
    ax_vec.set_title("TRANSPORT FLOW", color='#60aaff',
                     fontsize=9)
    ax_vec.set_xlim(0, nx)
    ax_vec.set_ylim(0, ny)
    quiver_obj = None

    # Pane 5: Navigator
    ax_nav.set_title("NAVIGATOR SAMPLING", color='#40ee70',
                     fontsize=9)
    ax_nav.set_xlim(0, nx)
    ax_nav.set_ylim(0, ny)
    im_lam = ax_nav.imshow(lam.T, cmap='RdYlGn',
                           origin='lower', extent=[0,nx,0,ny],
                           vmin=0, vmax=0.12, alpha=0.5)
    safe_dots, = ax_nav.plot([], [], '.', color='#44ff88',
                             markersize=3)
    danger_dots, = ax_nav.plot([], [], '.', color='#ff4444',
                               markersize=5)
    nav_text = ax_nav.text(0.05, 0.92, "", transform=ax_nav.transAxes,
                           color='#40ee70', fontsize=10,
                           fontweight='bold')

    # Pane 6: Timeline
    ax_time.set_title("ACCOUNTING", color='#ffbb44',
                      fontsize=9)
    ax_time.set_xlabel("Step", color='#808080', fontsize=7)
    line_da, = ax_time.plot([], [], '-', color='#ff9944',
                            linewidth=1.5, label='Active drift')
    line_dc, = ax_time.plot([], [], '-', color='#808080',
                            linewidth=1.5, label='Control drift')
    line_sc, = ax_time.plot([], [], '-', color='#ff4444',
                            linewidth=1, label='Scooped')
    line_dp, = ax_time.plot([], [], '-', color='#44ff88',
                            linewidth=1, label='Deposited')
    ax_time.legend(fontsize=6, loc='upper left',
                   facecolor='#10131a', edgecolor='#404040',
                   labelcolor='#a0a0a0')

    # Scene label
    scene_text = fig.text(0.5, 0.02, "", ha='center',
                          color='#ff9944', fontsize=12,
                          fontweight='bold')

    step_state = {"s": 0}

    scenes = [
        (0, 50, "BASELINE — No Pumps, No Drift"),
        (50, 200, "PUMPS ONLY — Local Deformation"),
        (200, 600, "PROBE CYCLING — Scoop/Deposit Active"),
        (600, 1000, "DRIFT EMERGENCE — Asymmetry Builds"),
        (1000, 1800, "HAZARD DETECTION — Navigator Reacts"),
        (1800, 2500, "TRANSIT — Full System"),
        (2500, 3000, "ACCOUNTING — Conservation Visible"),
    ]

    def get_scene(s):
        for start, end, name in scenes:
            if start <= s < end:
                return name
        return "COMPLETE"

    # Navigator state
    nav_safe_pts = []
    nav_danger_pts = []
    nav_decision = "PROCEED"
    nav_safe_p = 0.5
    nav_grave_p = 0.3

    def animate(frame):
        nonlocal sig_a, sig_a_prev, sig_c, sig_c_prev
        nonlocal reactor, quiver_obj
        nonlocal nav_decision, nav_safe_p, nav_grave_p
        nonlocal nav_safe_pts, nav_danger_pts

        s = step_state["s"]
        pumps_on = s >= 50
        probes_on = s >= 200

        # ── ACTIVE simulation ──
        com_a = compute_com(sig_a)
        if com_a is None:
            return []

        pa = np.array([com_a[0] + separation, com_a[1]])
        pb = np.array([com_a[0] - separation*0.3, com_a[1]])

        sig_a_snap = sig_a.copy()
        sig_a_new = pde_step(sig_a, sig_a_prev, lam, X, Y,
                             com_a, pump_A, ratio, separation,
                             D, dt, alpha, do_pumps=pumps_on)
        sig_a_prev = sig_a_snap
        sig_a = sig_a_new

        if pumps_on:
            r2A = (X-com_a[0])**2 + (Y-com_a[1])**2
            pc = float(np.sum(pump_A*np.exp(-r2A/(2*4**2))*dt))
            reactor -= pc

        if probes_on:
            for p in probes:
                p.update(com_a, pa, pb, s, sig_a, lam,
                         nx, ny, rng_active)
                if p.state == "EJECTED":
                    if p.danger_reading:
                        nav_danger_pts.append(
                            (p.pos[1], p.pos[0]))
                        nav_grave_p = min(0.99,
                            nav_grave_p + 0.02)
                        nav_safe_p = max(0.01,
                            nav_safe_p - 0.01)
                    else:
                        nav_safe_pts.append(
                            (p.pos[1], p.pos[0]))
                        nav_grave_p = max(0.01,
                            nav_grave_p - 0.005)
                        nav_safe_p = min(0.99,
                            nav_safe_p + 0.005)

            if nav_grave_p > 0.70:
                nav_decision = "AVOID"
            elif nav_grave_p > 0.45:
                nav_decision = "CAUTION"
            else:
                nav_decision = "PROCEED"

        # Keep last 200 nav points
        nav_safe_pts = nav_safe_pts[-200:]
        nav_danger_pts = nav_danger_pts[-200:]

        # ── CONTROL simulation ──
        com_c = compute_com(sig_c)
        sig_c_snap = sig_c.copy()
        sig_c_new = pde_step(sig_c, sig_c_prev, lam, X, Y,
                             com_c, pump_A, ratio, separation,
                             D, dt, alpha, do_pumps=pumps_on)
        sig_c_prev = sig_c_snap
        sig_c = sig_c_new

        # ── DELTA ──
        delta = sig_a - sig_c

        # ── TIMELINE ──
        drift_a = float(np.linalg.norm(com_a - initial_com))
        drift_c = (float(np.linalg.norm(com_c - initial_com))
                   if com_c is not None else 0)
        total_sc = sum(p.total_scooped for p in probes)
        total_dep = sum(p.total_deposited for p in probes)

        t_steps.append(s)
        t_drift_a.append(drift_a)
        t_drift_c.append(drift_c)
        t_scooped.append(total_sc)
        t_deposited.append(total_dep)

        # ── UPDATE VISUALS ──
        vmax_a = max(0.05, float(np.max(sig_a)) * 0.8)
        im_a.set_array(sig_a.T)
        im_a.set_clim(0, vmax_a)
        craft_dot.set_data([com_a[1]], [com_a[0]])

        if probes_on:
            px = [p.pos[1] for p in probes
                  if p.state == "EJECTED"]
            py = [p.pos[0] for p in probes
                  if p.state == "EJECTED"]
            probe_dots.set_data(px, py)
        else:
            probe_dots.set_data([], [])

        # Delta
        im_d.set_array(delta.T)
        dmax = max(0.005, float(np.max(np.abs(delta))) * 0.8)
        im_d.set_clim(-dmax, dmax)

        # Control
        vmax_c = max(0.05, float(np.max(sig_c)) * 0.8)
        im_c.set_array(sig_c.T)
        im_c.set_clim(0, vmax_c)
        if com_c is not None:
            ctrl_dot.set_data([com_c[1]], [com_c[0]])

        # Vectors (every 20 frames)
        if frame % 20 == 0:
            ax_vec.clear()
            ax_vec.set_facecolor('#0c0e14')
            ax_vec.set_title("TRANSPORT FLOW", color='#60aaff',
                             fontsize=9)
            ax_vec.set_xlim(0, ny)
            ax_vec.set_ylim(0, nx)
            step_v = max(4, nx // 16)
            gy, gx = np.gradient(sig_a)
            ax_vec.quiver(
                Y[::step_v, ::step_v],
                X[::step_v, ::step_v],
                -gx[::step_v, ::step_v],
                -gy[::step_v, ::step_v],
                color='#60aaff', alpha=0.7,
                scale=max(0.1, float(np.max(np.abs(gx)))*50))

        # Navigator
        if nav_safe_pts:
            sx_pts = [p[0] for p in nav_safe_pts]
            sy_pts = [p[1] for p in nav_safe_pts]
            safe_dots.set_data(sx_pts, sy_pts)
        if nav_danger_pts:
            dx_pts = [p[0] for p in nav_danger_pts]
            dy_pts = [p[1] for p in nav_danger_pts]
            danger_dots.set_data(dx_pts, dy_pts)

        dec_col = {'PROCEED': '#40ee70', 'CAUTION': '#ffbb44',
                   'AVOID': '#ff5555'}.get(nav_decision,
                                           '#e0e8f0')
        nav_text.set_text(f"{nav_decision}\n"
                          f"safe={nav_safe_p:.2f} "
                          f"grave={nav_grave_p:.2f}")
        nav_text.set_color(dec_col)

        # Timeline
        line_da.set_data(t_steps, t_drift_a)
        line_dc.set_data(t_steps, t_drift_c)
        line_sc.set_data(t_steps, t_scooped)
        line_dp.set_data(t_steps, t_deposited)
        if t_steps:
            ax_time.set_xlim(0, max(100, t_steps[-1]))
            all_vals = (t_drift_a + t_drift_c +
                        t_scooped + t_deposited)
            if all_vals:
                ax_time.set_ylim(0, max(1, max(all_vals)*1.1))

        # Scene label
        scene_text.set_text(get_scene(s))

        step_state["s"] += speed

        return []

    ani = FuncAnimation(fig, animate, frames=3000 // speed,
                        interval=40, blit=False, repeat=False)

    plt.tight_layout(rect=[0, 0.04, 1, 0.94])
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="BCM v17 Reviewer Mode Cinematic")
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--speed", type=int, default=2)
    args = parser.parse_args()

    print(f"\n{'='*55}")
    print(f"  BCM v17 -- REVIEWER MODE CINEMATIC")
    print(f"  6 panes. 2 simulations. Causality visible.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*55}")
    print(f"  Grid: {args.grid}  Speed: {args.speed}x")
    print(f"  Panes: field | delta | control")
    print(f"         vectors | navigator | accounting")
    print(f"{'='*55}\n")

    run_cinematic(grid=args.grid, speed=args.speed)


if __name__ == "__main__":
    main()
