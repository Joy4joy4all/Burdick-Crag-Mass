# -*- coding: utf-8 -*-
"""
BCM v17 -- Transport Cinematic
================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Live animated visualization of the sigma transport model.
Shows the physics thinking -- not decoration, but diagnostic
instrument. A reviewer must SEE causality.

7 SCENES (ChatGPT advocate standard):
  1. Baseline    - ship sits still, field visible, no drift
  2. Pump active - A/B engage, local deformation only
  3. Probe cycle - scoop at apoapsis, deposit at B
  4. Drift       - ship begins moving, field asymmetry
  5. Hazard      - grave detection, navigator reacts
  6. Tunnel      - intake/acceleration/ejection visible
  7. Accounting  - reactor, scooped, deposited, drift live

Design principle: if someone watches this and says
"I can see WHY it moves" -- we succeeded.

Uses the sigma transport model (scoop/deposit) from
Diagnostic 3D. No printer. Conservation enforced.

Usage:
    python BCM_v17_transport_cinematic.py
    python BCM_v17_transport_cinematic.py --grid 128 --speed 2
"""

import numpy as np
import os
import math
import argparse

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch
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
# TRANSPORT PROBE (scoop/deposit, visual tracking)
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
        self.last_scoop_pos = None
        self.last_deposit_pos = None

        self.t_transit = 5
        self.t_arc = 40
        self.t_fall = 10

    def update(self, com, pa, pb, step, sigma, nx, ny, rng):
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
            va = (round(ca / (2 * math.pi / vc))
                  * (2 * math.pi / vc))
            aa = 0.3 * ca + 0.7 * va

            self.pos = np.array([
                pa[0] + self.arc_radius * np.cos(aa),
                pa[1] + self.arc_radius * np.sin(aa)])

            self._scoop(sigma, nx, ny)

        else:
            self.state = "FALLING"
            fs = (self.cycle_step - self.t_transit - self.t_arc)
            tf = fs / self.t_fall
            self.pos = self.pos + tf * (pb - self.pos)
            if fs >= self.t_fall - 1:
                self._deposit(sigma, pb, nx, ny)

    def _scoop(self, sigma, nx, ny):
        ix = int(np.clip(self.pos[0], 0, nx - 1))
        iy = int(np.clip(self.pos[1], 0, ny - 1))
        xa = np.arange(max(0, ix-4), min(nx, ix+5))
        ya = np.arange(max(0, iy-4), min(ny, iy+5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl - self.pos[0])**2 + (Yl - self.pos[1])**2
        w = np.exp(-r2 / (2 * self.scoop_r**2))
        loc = sigma[np.ix_(xa, ya)]
        sc = np.minimum(loc * w * self.scoop_eff, loc)
        sc = np.maximum(sc, 0)
        t = float(np.sum(sc))
        sigma[np.ix_(xa, ya)] -= sc
        self.payload += t
        self.total_scooped += t
        if t > 0.001:
            self.last_scoop_pos = self.pos.copy()

    def _deposit(self, sigma, pos, nx, ny):
        if self.payload <= 0:
            return
        ix = int(np.clip(pos[0], 0, nx - 1))
        iy = int(np.clip(pos[1], 0, ny - 1))
        xa = np.arange(max(0, ix-4), min(nx, ix+5))
        ya = np.arange(max(0, iy-4), min(ny, iy+5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl - pos[0])**2 + (Yl - pos[1])**2
        w = np.exp(-r2 / (2 * self.scoop_r**2))
        ws = float(np.sum(w))
        if ws > 1e-15:
            sigma[np.ix_(xa, ya)] += w * (self.payload / ws)
        self.total_deposited += self.payload
        self.last_deposit_pos = pos.copy()
        self.payload = 0.0


# ═══════════════════════════════════════════════════════
# NAVIGATOR (forward-weighted Bayesian)
# ═══════════════════════════════════════════════════════

class CinemaNav:
    def __init__(self):
        self.safe_p = 0.5
        self.grave_p = 0.3
        self.decision = "PROCEED"
        self.fwd_dangers = 0

    def ingest(self, lam_val, is_forward):
        w = 3.0 if is_forward else 1.0
        danger = lam_val < 0.04
        p = max(0.01, min(0.99, self.grave_p))
        lo = math.log(p / (1 - p))
        if danger:
            lo += 0.50 * w
            self.safe_p = max(0.01, self.safe_p - 0.02 * w)
            if is_forward:
                self.fwd_dangers += 1
        else:
            lo -= 0.10 * w * 0.5
            self.safe_p = min(0.99, self.safe_p + 0.01 * w)
        self.grave_p = 1.0 / (1.0 + math.exp(-lo))

        if self.grave_p > 0.70:
            self.decision = "AVOID"
        elif self.grave_p > 0.45:
            self.decision = "CAUTION"
        elif self.safe_p > 0.65:
            self.decision = "PROCEED"


# ═══════════════════════════════════════════════════════
# CINEMATIC ENGINE
# ═══════════════════════════════════════════════════════

def run_cinematic(grid=128, speed=1):
    if not HAS_MPL:
        print("  matplotlib required. Install: pip install matplotlib")
        return

    nx = ny = grid
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

    # Lambda field with grave
    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny//2)**2
    lam -= 0.08 * np.exp(-r2g / (2 * 18.0**2))
    lam = np.maximum(lam, 0.001)

    # Sigma
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    initial_com = compute_com(sigma)

    # Probes + Navigator
    probes = [CinemaProbe(i+1, i*5) for i in range(12)]
    nav = CinemaNav()

    # Scene phases (step ranges)
    scenes = {
        "BASELINE":    (0, 50),
        "PUMPS ONLY":  (50, 200),
        "PROBE CYCLE": (200, 600),
        "DRIFT":       (600, 1000),
        "HAZARD":      (1000, 1800),
        "TRANSIT":     (1800, 2500),
        "ACCOUNTING":  (2500, 3000),
    }

    # Figure
    fig, (ax_field, ax_hud) = plt.subplots(
        1, 2, figsize=(14, 6),
        gridspec_kw={"width_ratios": [2, 1]})
    fig.patch.set_facecolor('#080a0e')
    fig.suptitle(
        "BCM v17 — SIGMA TRANSPORT CINEMATIC\n"
        "Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems",
        color='#ff9944', fontsize=11, fontweight='bold')

    # Field display
    ax_field.set_facecolor('#080a0e')
    im = ax_field.imshow(
        sigma.T, cmap='inferno', origin='lower',
        extent=[0, nx, 0, ny], vmin=0, vmax=0.5,
        aspect='equal')
    craft_dot, = ax_field.plot([], [], 'o', color='#ff9944',
                                markersize=8, zorder=10)
    probe_dots, = ax_field.plot([], [], '.', color='#60aaff',
                                 markersize=4, zorder=9)
    scoop_markers, = ax_field.plot([], [], 'v', color='#ff4444',
                                    markersize=5, zorder=8)
    deposit_markers, = ax_field.plot([], [], '^', color='#44ff88',
                                      markersize=5, zorder=8)
    ax_field.set_xlim(0, nx)
    ax_field.set_ylim(0, ny)
    ax_field.set_xlabel("x (px)", color='#a0a0a0', fontsize=8)
    ax_field.set_ylabel("y (px)", color='#a0a0a0', fontsize=8)
    ax_field.tick_params(colors='#606060', labelsize=7)

    # HUD panel
    ax_hud.set_facecolor('#10131a')
    ax_hud.set_xlim(0, 10)
    ax_hud.set_ylim(0, 20)
    ax_hud.axis('off')

    hud_texts = {}
    labels = [
        ("scene", 19, '#ff9944'),
        ("step", 17.5, '#e0e8f0'),
        ("drift", 16, '#e0e8f0'),
        ("decision", 14.5, '#40ee70'),
        ("safe_p", 13, '#40ccaa'),
        ("grave_p", 11.5, '#ff5555'),
        ("reactor", 10, '#ffbb44'),
        ("scooped", 8.5, '#ff4444'),
        ("deposited", 7, '#44ff88'),
        ("payload", 5.5, '#60aaff'),
        ("cycles", 4, '#e0e8f0'),
        ("coherence", 2.5, '#40ccaa'),
    ]
    for key, ypos, col in labels:
        hud_texts[key] = ax_hud.text(
            0.5, ypos, "", fontsize=10, color=col,
            fontfamily='monospace', fontweight='bold')

    # State
    state = {
        "step": 0,
        "sigma": sigma,
        "sigma_prev": sigma_prev,
        "probes_active": False,
        "pumps_active": False,
        "reactor": 200.0,
    }

    def get_scene(step):
        for name, (s, e) in scenes.items():
            if s <= step < e:
                return name
        return "ACCOUNTING"

    def animate(frame):
        s = state["step"]
        sigma = state["sigma"]
        sigma_prev = state["sigma_prev"]

        scene = get_scene(s)

        # Scene control
        pumps_on = s >= 50
        probes_on = s >= 200

        com = compute_com(sigma)
        if com is None:
            return []

        pa = np.array([com[0] + separation, com[1]])
        pb = np.array([com[0] - separation * 0.3, com[1]])

        # Pumps
        if pumps_on:
            r2A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2A / (2 * 4.0**2))
            sigma += pA * dt
            bx = com[0] + separation
            r2B = (X - bx)**2 + (Y - com[1])**2
            aB = pump_A * ratio
            pB = aB * np.exp(-r2B / (2 * 3.0**2))
            sigma += pB * dt

            pump_cost = float(np.sum(pA * dt)) + float(np.sum(pB * dt))
            state["reactor"] -= pump_cost

        # PDE
        lap = (np.roll(sigma, 1, 0) + np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) + np.roll(sigma, -1, 1) -
               4 * sigma)
        sn = sigma + D * lap * dt - lam * sigma * dt
        if alpha > 0:
            sn += alpha * (sigma - sigma_prev)
        sn = np.maximum(sn, 0)
        state["sigma_prev"] = sigma.copy()
        state["sigma"] = sn
        sigma = sn

        # Probes
        scoop_xs, scoop_ys = [], []
        dep_xs, dep_ys = [], []

        if probes_on:
            for p in probes:
                p.update(com, pa, pb, s, sigma, nx, ny, rng)
                # Navigator
                if p.state == "EJECTED":
                    ix = int(np.clip(p.pos[0], 0, nx-1))
                    iy = int(np.clip(p.pos[1], 0, ny-1))
                    nav.ingest(float(lam[ix, iy]),
                               p.pos[0] > com[0])
                # Visual markers
                if p.last_scoop_pos is not None:
                    scoop_xs.append(p.last_scoop_pos[1])
                    scoop_ys.append(p.last_scoop_pos[0])
                if p.last_deposit_pos is not None:
                    dep_xs.append(p.last_deposit_pos[1])
                    dep_ys.append(p.last_deposit_pos[0])

        # Visuals
        im.set_array(sigma.T)
        vmax = max(0.1, float(np.max(sigma)) * 0.8)
        im.set_clim(0, vmax)

        craft_dot.set_data([com[1]], [com[0]])

        if probes_on:
            px = [p.pos[1] for p in probes
                  if p.state == "EJECTED"]
            py = [p.pos[0] for p in probes
                  if p.state == "EJECTED"]
            probe_dots.set_data(px, py)
        else:
            probe_dots.set_data([], [])

        scoop_markers.set_data(scoop_xs[-3:], scoop_ys[-3:])
        deposit_markers.set_data(dep_xs[-3:], dep_ys[-3:])

        # HUD
        drift = float(np.linalg.norm(com - initial_com))
        total_sc = sum(p.total_scooped for p in probes)
        total_dep = sum(p.total_deposited for p in probes)
        total_pay = sum(p.payload for p in probes)
        total_cyc = sum(p.cycles for p in probes)

        # Coherence
        r2c = (X - com[0])**2 + (Y - com[1])**2
        inside = float(np.sum(sigma[r2c < 64]))
        total = float(np.sum(sigma))
        coh = inside / total if total > 1e-15 else 0

        dec_col = {'PROCEED': '#40ee70', 'CAUTION': '#ffbb44',
                   'AVOID': '#ff5555'}.get(nav.decision, '#e0e8f0')

        hud_texts["scene"].set_text(f"SCENE: {scene}")
        hud_texts["step"].set_text(f"Step: {s}")
        hud_texts["drift"].set_text(f"Drift: {drift:.1f} px")
        hud_texts["decision"].set_text(f"NAV: {nav.decision}")
        hud_texts["decision"].set_color(dec_col)
        hud_texts["safe_p"].set_text(
            f"Safe: {nav.safe_p:.3f}")
        hud_texts["grave_p"].set_text(
            f"Grave: {nav.grave_p:.3f}")
        hud_texts["reactor"].set_text(
            f"Reactor: {state['reactor']:.1f}")
        hud_texts["scooped"].set_text(
            f"Scooped: {total_sc:.2f}")
        hud_texts["deposited"].set_text(
            f"Deposited: {total_dep:.2f}")
        hud_texts["payload"].set_text(
            f"In transit: {total_pay:.4f}")
        hud_texts["cycles"].set_text(
            f"Cycles: {total_cyc}")
        hud_texts["coherence"].set_text(
            f"Coherence: {coh:.3f}")

        # Advance
        state["step"] += speed

        return [im, craft_dot, probe_dots, scoop_markers,
                deposit_markers] + list(hud_texts.values())

    ani = FuncAnimation(fig, animate, frames=3000 // speed,
                        interval=30, blit=False, repeat=False)

    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="BCM v17 Transport Cinematic")
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--speed", type=int, default=1,
                        help="Steps per frame (1=slow, 5=fast)")
    args = parser.parse_args()

    print(f"\n{'='*55}")
    print(f"  BCM v17 -- TRANSPORT CINEMATIC")
    print(f"  See WHY the ship moves")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*55}")
    print(f"  Grid: {args.grid}  Speed: {args.speed}x")
    print(f"  Scenes: baseline -> pumps -> probes -> drift")
    print(f"          -> hazard -> transit -> accounting")
    print(f"{'='*55}\n")

    run_cinematic(grid=args.grid, speed=args.speed)


if __name__ == "__main__":
    main()
