# -*- coding: utf-8 -*-
"""
BCM v11 Inspiral 3D Renderer — Binary Black Hole Merger Sequence
==================================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Renders 4 key frames of the inspiral sweep in cinematic 3D:
  Frame 1: Wide separation (inspiral)
  Frame 2: Phase snap (ISCO analog)
  Frame 3: Foreclosure (I_B negative)
  Frame 4: Merger (single pump)

Usage:
    python BCM_inspiral_renderer.py
    python BCM_inspiral_renderer.py --grid 128
"""

import numpy as np
import argparse
import os
import time


def render_inspiral_frame(grid, amp_A, amp_B, sep_frac, frame_label,
                           settle=15000, measure=5000, n_theta=64):
    """Render one inspiral frame in cinematic 3D."""
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from matplotlib.widgets import Button
    from core.substrate_solver import SubstrateSolver

    center = grid // 2
    sep_px = max(4, int(grid * sep_frac))
    pump_A_x = center - sep_px // 2
    pump_B_x = center + sep_px // 2
    pump_y = center
    width = max(3, grid // 20)

    # Build source
    yy, xx = np.mgrid[0:grid, 0:grid]
    r_A = np.sqrt((xx - pump_A_x)**2 + (yy - pump_y)**2)
    r_B = np.sqrt((xx - pump_B_x)**2 + (yy - pump_y)**2)
    J = amp_A * np.exp(-r_A**2 / (2*width**2)) + \
        amp_B * np.exp(-r_B**2 / (2*width**2))

    print(f"\n  Rendering: {frame_label}")
    print(f"  sep={sep_frac:.3f}  sep_px={sep_px}  "
          f"A@{pump_A_x} B@{pump_B_x}")

    # Run solver
    solver = SubstrateSolver(grid=grid, layers=6,
                              lam=0.1, gamma=0.05,
                              entangle=0.02, c_wave=1.0,
                              settle=settle, measure=measure)
    result = solver.run(J, verbose=False)

    sigma_avg = result.get("sigma_avg")
    field_2d = np.log1p(sigma_avg.sum(axis=0))

    # L1
    l1x = (pump_A_x + pump_B_x) // 2
    axis_y = center

    # Split normalization
    field_norm = np.zeros_like(field_2d)
    a_side = field_2d[:, :l1x]
    b_side = field_2d[:, l1x:]
    a_max = np.max(a_side) if np.max(a_side) > 0 else 1.0
    b_max = np.max(b_side) if np.max(b_side) > 0 else 1.0
    field_norm[:, :l1x] = a_side / a_max
    field_norm[:, l1x:] = b_side / b_max

    try:
        from scipy.ndimage import uniform_filter
        field_smooth = uniform_filter(field_norm, size=3)
    except ImportError:
        field_smooth = field_norm

    r_from_axis = np.abs(np.arange(grid) - axis_y).astype(float)
    thetas = np.linspace(0, 2 * np.pi, n_theta)

    # Cinematic canvas
    fig = plt.figure(figsize=(19, 10), facecolor='black')
    ax = fig.add_subplot(111, projection='3d', facecolor='black')
    ax.set_axis_off()
    plt.subplots_adjust(top=1, bottom=0, right=1, left=0)

    # Glow shells
    levels = [0.02, 0.05, 0.08, 0.12, 0.18, 0.25,
              0.35, 0.48, 0.62, 0.80]
    alphas = [0.03, 0.04, 0.05, 0.07, 0.10,
              0.14, 0.20, 0.28, 0.38, 0.55]

    for level, alpha in zip(levels, alphas):
        shell_r = np.zeros(grid)
        shell_val = np.zeros(grid)

        for ix in range(grid):
            col = field_smooth[:, ix]
            above = np.where(col > level)[0]
            if len(above) > 0:
                shell_r[ix] = np.max(r_from_axis[above])
                shell_val[ix] = np.mean(col[above])

        if np.max(shell_r) < 2:
            continue

        try:
            from scipy.ndimage import uniform_filter1d
            shell_r = uniform_filter1d(shell_r, size=5)
        except ImportError:
            pass

        X_s = np.zeros((grid, n_theta))
        Y_s = np.zeros((grid, n_theta))
        Z_s = np.zeros((grid, n_theta))
        C_s = np.zeros((grid, n_theta, 4))

        for ix in range(grid):
            r = shell_r[ix]
            val = min(shell_val[ix], 1.0)
            t = (ix - pump_A_x) / max(1, pump_B_x - pump_A_x)
            t = np.clip(t, 0, 1)

            if t < 0.5:
                base_rgb = cm.inferno(0.3 + 0.6 * val)[:3]
            else:
                base_rgb = cm.cool(0.2 + 0.6 * val)[:3]

            brightness = 0.2 + 0.8 * val

            for it, th in enumerate(thetas):
                X_s[ix, it] = ix
                Y_s[ix, it] = r * np.cos(th)
                Z_s[ix, it] = r * np.sin(th)
                C_s[ix, it] = [base_rgb[0] * brightness,
                               base_rgb[1] * brightness,
                               base_rgb[2] * brightness,
                               alpha * (0.2 + 0.8 * val)]

        ax.plot_surface(X_s, Y_s, Z_s, facecolors=C_s,
                       shade=False, antialiased=True,
                       linewidth=0, rstride=2, cstride=2)

    # --- Alfven rings (light purple) ---
    ring_th = np.linspace(0, 2 * np.pi, 100)
    for pump_x, ring_c, ring_r_frac in [
            (pump_A_x, '#c090ff', 0.45),
            (pump_B_x, '#c090ff', 0.40)]:
        col = field_smooth[:, pump_x]
        above = np.where(col > 0.15)[0]
        if len(above) > 0:
            ring_r = np.max(r_from_axis[above]) * ring_r_frac
        else:
            ring_r = grid * 0.05
        ax.plot(np.full(100, pump_x),
               ring_r * np.cos(ring_th),
               ring_r * np.sin(ring_th),
               color=ring_c, linewidth=1.5, alpha=0.6)

    # --- Bridge corridor (thin green tube) ---
    if sep_px > 8:
        bx0 = pump_A_x + max(3, sep_px // 6)
        bx1 = pump_B_x - max(3, sep_px // 6)
        bridge_xs = np.arange(bx0, bx1)
        if len(bridge_xs) > 2:
            corr_r = np.zeros(len(bridge_xs))
            for bi, bix in enumerate(bridge_xs):
                col = field_smooth[:, int(bix)]
                above = np.where(col > 0.06)[0]
                if len(above) > 0:
                    corr_r[bi] = np.max(r_from_axis[above]) * 0.08
                else:
                    corr_r[bi] = 0.3
            BX = np.zeros((len(bridge_xs), n_theta))
            BY = np.zeros((len(bridge_xs), n_theta))
            BZ = np.zeros((len(bridge_xs), n_theta))
            for bi, bix in enumerate(bridge_xs):
                r = max(corr_r[bi], 0.2)
                for it, th in enumerate(thetas):
                    BX[bi, it] = bix
                    BY[bi, it] = r * np.cos(th)
                    BZ[bi, it] = r * np.sin(th)
            ax.plot_surface(BX, BY, BZ, color='#30ff60',
                           alpha=0.20, shade=False, linewidth=0,
                           rstride=1, cstride=2)

    # --- Bridge axis (dashed) ---
    ax.plot([pump_A_x, pump_B_x], [0, 0], [0, 0],
           color='#40ff80', linewidth=1.0, alpha=0.3,
           linestyle='--')

    # --- Flow direction arrow (A→L1) ---
    if sep_px > 10:
        arr_x = (pump_A_x + l1x) // 2
        ax.quiver(arr_x, 0, 0, (l1x - pump_A_x) * 0.3, 0, 0,
                 color='#60ffa0', alpha=0.5, arrow_length_ratio=0.3,
                 linewidth=1.5)

    # Pump markers
    ax.scatter([pump_A_x], [0], [0], c='#ffdd00', s=400,
              marker='*', edgecolors='white', linewidths=0.5,
              zorder=10)
    ax.scatter([pump_B_x], [0], [0], c='#00eeff', s=350,
              marker='*', edgecolors='white', linewidths=0.5,
              zorder=10)
    if sep_px > 6:
        ax.scatter([l1x], [0], [0], c='#ff2020', s=100,
                  marker='o', edgecolors='white', linewidths=0.5,
                  zorder=10)

    # --- Labels ---
    label_z = grid * 0.12
    ax.text(pump_A_x, 0, label_z, "A",
            color='#ffdd00', fontsize=14, fontweight='bold',
            ha='center', zorder=11)
    ax.text(pump_B_x, 0, label_z, "B",
            color='#00eeff', fontsize=14, fontweight='bold',
            ha='center', zorder=11)
    if sep_px > 8:
        ax.text(l1x, 0, label_z * 0.7, "L1",
                color='#ff4040', fontsize=10,
                ha='center', zorder=11)

    # View — fill canvas
    max_r = grid * 0.38
    ax.set_ylim(-max_r, max_r)
    ax.set_zlim(-max_r, max_r)
    pad = grid * 0.05
    ax.set_xlim(max(0, pump_A_x - int(grid*0.15)),
                min(grid, pump_B_x + int(grid*0.15)))
    ax.view_init(elev=15, azim=-50)
    ax.dist = 7.5

    # Title
    fig.text(0.50, 0.96,
             f"BCM 3D \u2014 GW150914 Analog  {frame_label}",
             ha='center', va='top',
             fontsize=16, fontweight='bold',
             color='#d0e8ff', family='sans-serif')

    # HUD
    cos_dphi = result.get("cos_delta_phi", 0)
    sig_field = sigma_avg.sum(axis=0)
    rr = max(3, grid // 32)
    def _s(f, cx, cy):
        return float(np.max(np.abs(
            f[max(0,cy-rr):cy+rr, max(0,cx-rr):cx+rr])))
    mid_ax = (pump_A_x + l1x) // 2
    mid_bx = (l1x + pump_B_x) // 2
    sig_ma = _s(sig_field, mid_ax, pump_y)
    sig_l1 = _s(sig_field, l1x, pump_y)
    sig_mb = _s(sig_field, mid_bx, pump_y)
    sig_drift = sig_ma - sig_mb
    i_b = sig_mb - sig_l1

    hud_text = (
        f"INSPIRAL INVOICE\n"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        f"sep: {sep_frac:.3f}  ({sep_px} px)\n"
        f"cos_dphi: {cos_dphi:+.6f}\n"
        f"\u03C3 drift: {sig_drift:+.0f}\n"
        f"I_B:      {i_b:+.1f}\n"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        f"Emerald Entities LLC"
    )

    fig.text(0.98, 0.04, hud_text,
             ha='right', va='bottom',
             fontsize=9, color='#80c0ff', alpha=0.7,
             family='monospace',
             bbox=dict(boxstyle='round,pad=0.5',
                       facecolor='#0a0e18', edgecolor='#203050',
                       alpha=0.7))

    # Watermark
    fig.text(0.02, 0.02,
             f"GIBUSH v11 | GW150914 | {frame_label} | "
             f"{time.strftime('%Y-%m-%d')}",
             color='#406080', fontsize=8, alpha=0.5,
             family='monospace')

    # Save directory
    img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "images")
    os.makedirs(img_dir, exist_ok=True)

    # Auto-save
    auto_path = os.path.join(img_dir,
        f"BCM_inspiral_{frame_label.replace(' ','_')}.png")
    fig.savefig(auto_path, dpi=200, bbox_inches='tight',
                facecolor='black')
    print(f"  Saved: {auto_path}")

    # Capture button
    from matplotlib.widgets import Button
    cap_count = [0]

    def _capture(event):
        cap_count[0] += 1
        elev = ax.elev
        azim = ax.azim
        cap_path = os.path.join(img_dir,
            f"BCM_inspiral_{frame_label.replace(' ','_')}_"
            f"cap{cap_count[0]:02d}_e{int(elev)}a{int(azim)}.png")
        fig.savefig(cap_path, dpi=250, bbox_inches='tight',
                    facecolor='black')
        print(f"  Captured: {cap_path}")

    btn_ax = fig.add_axes([0.02, 0.92, 0.12, 0.04])
    btn = Button(btn_ax, '\u2B24  CAPTURE',
                 color='#152030', hovercolor='#254060')
    btn.label.set_color('#80d0ff')
    btn.label.set_fontsize(10)
    btn.label.set_family('monospace')
    btn.on_clicked(_capture)

    plt.show()


def run_inspiral_sequence(grid=128, settle=15000, measure=5000):
    """Render all 15 inspiral steps as sequential frames."""
    import numpy as np

    print(f"\n{'='*65}")
    print(f"  BCM v11 INSPIRAL 3D RENDERER — GW150914 Analog")
    print(f"  Grid: {grid}  Amp: 50.0 / 43.0 (1.16:1)")
    print(f"  15 steps: full inspiral → merger sequence")
    print(f"{'='*65}")

    seps = np.logspace(np.log10(0.60), np.log10(0.04), 15)

    for i, sep in enumerate(seps):
        label = f"{i+1:02d}_sep{sep:.3f}"
        render_inspiral_frame(grid, amp_A=50.0, amp_B=43.0,
                               sep_frac=float(sep),
                               frame_label=label,
                               settle=settle, measure=measure)

    print(f"\n{'='*65}")
    print(f"  All 4 frames rendered.")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v11 Inspiral 3D Renderer")
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--settle", type=int, default=15000)
    parser.add_argument("--measure", type=int, default=5000)
    args = parser.parse_args()

    run_inspiral_sequence(grid=args.grid,
                           settle=args.settle, measure=args.measure)
