# -*- coding: utf-8 -*-
"""
BCM v9 3D Cinematic Renderer — Substrate Glow
================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Full-pane volumetric renderer with substrate glow, split
normalization, log compression, and TCF accounting overlay.

Usage:
    python BCM_3d_renderer.py --pair Spica --phase 0.0
    python BCM_3d_renderer.py --pair HR_1099 --phase 0.5
    python BCM_3d_renderer.py --pair Spica --phase 0.0 --grid 192
"""

import numpy as np
import argparse
import os
import time


def render_3d(pair_name="Spica", phase=0.0, grid=128,
              field_type="sigma", settle=15000, measure=5000,
              n_theta=72):
    """
    Cinematic 3D azimuthal revolution with substrate glow.
    """
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from BCM_stellar_overrides import run_binary

    print(f"\n{'='*60}")
    print(f"  BCM 3D CINEMATIC — {pair_name} phase={phase:.2f}")
    print(f"  Grid: {grid}  Field: {field_type}")
    print(f"{'='*60}")

    # Run solver
    print(f"  Running binary solver...")
    result, J, info = run_binary(pair_name, grid=grid,
                                  orbital_phase=phase,
                                  settle=settle, measure=measure,
                                  verbose=True)

    rho_avg = result.get("rho_avg")
    sigma_avg = result.get("sigma_avg")

    if field_type == "sigma":
        field_2d = sigma_avg.sum(axis=0)
    else:
        field_2d = np.abs(rho_avg.sum(axis=0))

    # Log compression for dynamic range
    field_2d = np.log1p(field_2d)

    # Bridge geometry
    axis_y = grid // 2
    pump_A = info["pump_A"]
    pump_B = info["pump_B"]
    l1 = info["L1"]
    l1x = l1[0]
    amp_A = info.get("amp_A", 0)
    amp_B = info.get("amp_B", 0)

    # Split normalization at L1
    field_norm = np.zeros_like(field_2d)
    a_side = field_2d[:, :l1x]
    b_side = field_2d[:, l1x:]
    a_max = np.max(a_side) if np.max(a_side) > 0 else 1.0
    b_max = np.max(b_side) if np.max(b_side) > 0 else 1.0
    field_norm[:, :l1x] = a_side / a_max
    field_norm[:, l1x:] = b_side / b_max

    print(f"  Split norm: A={a_max:.1f}  B={b_max:.1f}  "
          f"ratio={a_max/b_max:.1f}:1")

    # Smooth
    try:
        from scipy.ndimage import uniform_filter
        field_smooth = uniform_filter(field_norm, size=3)
    except ImportError:
        field_smooth = field_norm

    r_from_axis = np.abs(np.arange(grid) - axis_y).astype(float)
    thetas = np.linspace(0, 2 * np.pi, n_theta)

    # --- Cinematic canvas ---
    fig = plt.figure(figsize=(19, 10), facecolor='black')
    ax = fig.add_subplot(111, projection='3d', facecolor='black')
    ax.set_axis_off()
    plt.subplots_adjust(top=1, bottom=0, right=1, left=0,
                         hspace=0, wspace=0)

    print(f"  Building cinematic shells...")

    # --- Glow shells (many thin layers for atmosphere) ---
    levels = [0.02, 0.05, 0.08, 0.12, 0.18, 0.25,
              0.35, 0.48, 0.62, 0.80]
    base_alphas = [0.03, 0.04, 0.05, 0.07, 0.10,
                   0.14, 0.20, 0.28, 0.38, 0.55]

    for li, (level, alpha) in enumerate(zip(levels, base_alphas)):
        shell_r = np.zeros(grid)
        shell_val = np.zeros(grid)
        shell_side = np.zeros(grid)  # 0=A, 1=B

        for ix in range(grid):
            col = field_smooth[:, ix]
            above = np.where(col > level)[0]
            if len(above) > 0:
                shell_r[ix] = np.max(r_from_axis[above])
                shell_val[ix] = np.mean(col[above])
                # Track which side of L1
                shell_side[ix] = 0.0 if ix < l1x else 1.0

        if np.max(shell_r) < 2:
            continue

        # Smooth
        try:
            from scipy.ndimage import uniform_filter1d
            shell_r = uniform_filter1d(shell_r, size=5)
        except ImportError:
            pass

        # Build revolution surface
        X_s = np.zeros((grid, n_theta))
        Y_s = np.zeros((grid, n_theta))
        Z_s = np.zeros((grid, n_theta))
        C_s = np.zeros((grid, n_theta, 4))

        for ix in range(grid):
            r = shell_r[ix]
            val = min(shell_val[ix], 1.0)

            # Position along bridge (0=A, 1=B)
            t = (ix - pump_A[0]) / max(1, pump_B[0] - pump_A[0])
            t = np.clip(t, 0, 1)

            # Magma-style color blending
            # A side: warm (gold → orange → red at core)
            # B side: cool (teal → cyan → white at core)
            if t < 0.5:
                # A-dominant
                base_rgb = cm.inferno(0.3 + 0.6 * val)[:3]
            else:
                # B-dominant
                base_rgb = cm.cool(0.2 + 0.6 * val)[:3]

            # Bridge corridor gets green-white tint
            bridge_zone = 1.0 - min(1.0, abs(ix - l1x) / max(1, grid * 0.15))
            if bridge_zone > 0.3 and val > 0.05:
                mix = bridge_zone * 0.4
                base_rgb = tuple(
                    base_rgb[c] * (1 - mix) + [0.3, 1.0, 0.5][c] * mix
                    for c in range(3))

            brightness = 0.2 + 0.8 * val

            for it, th in enumerate(thetas):
                X_s[ix, it] = ix
                Y_s[ix, it] = r * np.cos(th)
                Z_s[ix, it] = r * np.sin(th)
                C_s[ix, it] = [base_rgb[0] * brightness,
                               base_rgb[1] * brightness,
                               base_rgb[2] * brightness,
                               alpha * (0.2 + 0.8 * val)]

        ax.plot_surface(X_s, Y_s, Z_s,
                       facecolors=C_s,
                       shade=False, antialiased=True,
                       linewidth=0, rstride=2, cstride=2)

    # --- Bridge corridor (bright green tube) ---
    bridge_x0 = min(pump_A[0], pump_B[0]) + 2
    bridge_x1 = max(pump_A[0], pump_B[0]) - 2
    bridge_xs = np.arange(bridge_x0, bridge_x1)

    if len(bridge_xs) > 2:
        corridor_r = np.zeros(len(bridge_xs))
        for i, ix in enumerate(bridge_xs):
            col = field_smooth[:, int(ix)]
            above = np.where(col > 0.06)[0]
            if len(above) > 0:
                corridor_r[i] = np.max(r_from_axis[above]) * 0.10
            else:
                corridor_r[i] = 0.5

        try:
            from scipy.ndimage import uniform_filter1d
            corridor_r = uniform_filter1d(corridor_r, size=5)
        except ImportError:
            pass

        BX = np.zeros((len(bridge_xs), n_theta))
        BY = np.zeros((len(bridge_xs), n_theta))
        BZ = np.zeros((len(bridge_xs), n_theta))

        for i, ix in enumerate(bridge_xs):
            r = max(corridor_r[i], 0.3)
            for it, th in enumerate(thetas):
                BX[i, it] = ix
                BY[i, it] = r * np.cos(th)
                BZ[i, it] = r * np.sin(th)

        ax.plot_surface(BX, BY, BZ, color='#30ff60',
                       alpha=0.30, shade=False, linewidth=0,
                       rstride=1, cstride=2)

    # --- Alfven rings ---
    ring_th = np.linspace(0, 2 * np.pi, 120)
    for pump, c, lw in [(pump_A, '#ffcc00', 2.5),
                          (pump_B, '#00ddff', 2.0)]:
        px = pump[0]
        col = field_smooth[:, px]
        above = np.where(col > 0.15)[0]
        ring_r = np.max(r_from_axis[above]) * 0.45 if len(above) > 0 else grid * 0.05
        ax.plot(np.full(120, px),
               ring_r * np.cos(ring_th),
               ring_r * np.sin(ring_th),
               color=c, linewidth=lw, alpha=0.9)

    # --- Star markers ---
    ax.scatter([pump_A[0]], [0], [0], c='#ffdd00', s=400,
              marker='*', edgecolors='white', linewidths=0.5,
              zorder=10)
    ax.scatter([pump_B[0]], [0], [0], c='#00eeff', s=280,
              marker='*', edgecolors='white', linewidths=0.5,
              zorder=10)
    ax.scatter([l1x], [0], [0], c='#ff2020', s=100,
              marker='o', edgecolors='white', linewidths=0.5,
              zorder=10)

    # Bridge axis
    ax.plot([pump_A[0], pump_B[0]], [0, 0], [0, 0],
           color='#40ff80', linewidth=1.0, alpha=0.3,
           linestyle='--')

    # --- View ---
    max_r = grid * 0.45
    ax.set_ylim(-max_r, max_r)
    ax.set_zlim(-max_r, max_r)
    ax.set_xlim(0, grid)
    ax.view_init(elev=15, azim=-50)

    # --- Title overlay (top) ---
    fig.text(0.50, 0.96,
             f"BCM 3D \u2014 {pair_name}  phase={phase:.1f}",
             ha='center', va='top',
             fontsize=16, fontweight='bold',
             color='#d0e8ff', family='sans-serif')

    # --- TCF Accounting HUD (bottom right) ---
    # Quick TCF from the run data
    sig_field = sigma_avg.sum(axis=0)
    r = min(8, grid // 16)

    def _sample(f, cx, cy):
        y0, y1 = max(0, cy - r), min(grid, cy + r)
        x0, x1 = max(0, cx - r), min(grid, cx + r)
        return float(np.max(np.abs(f[y0:y1, x0:x1])))

    mid_ax = (pump_A[0] + l1x) // 2
    mid_bx = (l1x + pump_B[0]) // 2
    sig_ma = _sample(sig_field, mid_ax, axis_y)
    sig_l1 = _sample(sig_field, l1x, axis_y)
    sig_mb = _sample(sig_field, mid_bx, axis_y)
    sig_drift = sig_ma - sig_mb
    i_b = sig_mb - sig_l1

    sync = info.get("synchronized", False)
    sync_label = "SYNC" if sync else "UNSYNC"
    status = "RESISTANT" if i_b > 0 else "DRAIN"

    hud_text = (
        f"SUBSTRATE INVOICE\n"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        f"Pump A: {amp_A:.1f}   Pump B: {amp_B:.1f}\n"
        f"Ratio:  {amp_A/max(0.01,amp_B):.1f}:1   {sync_label}\n"
        f"\u03C3 drift: {sig_drift:+.0f}\n"
        f"I_B:    {i_b:+.1f}  [{status}]\n"
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

    # --- Watermark (bottom left) ---
    fig.text(0.02, 0.02,
             f"GIBUSH v9 | {pair_name} | "
             f"{time.strftime('%Y-%m-%d')}",
             color='#406080', fontsize=8, alpha=0.5,
             family='monospace')

    # --- Save directory ---
    base = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(base, "data", "images")
    os.makedirs(img_dir, exist_ok=True)

    # Auto-save initial view
    out_path = os.path.join(img_dir,
        f"BCM_3d_{pair_name}_phase{phase:.1f}_{field_type}.png")
    fig.savefig(out_path, dpi=200, bbox_inches='tight',
                facecolor='black')
    print(f"  Saved: {out_path}")

    # --- Capture button (saves current rotation angle) ---
    from matplotlib.widgets import Button

    capture_count = [0]

    def _capture(event):
        capture_count[0] += 1
        elev = ax.elev
        azim = ax.azim
        cap_path = os.path.join(img_dir,
            f"BCM_3d_{pair_name}_phase{phase:.1f}_"
            f"cap{capture_count[0]:02d}_e{int(elev)}a{int(azim)}.png")
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
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM 3D Cinematic Renderer")
    parser.add_argument("--pair", type=str, default="Spica")
    parser.add_argument("--phase", type=float, default=0.0)
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--field", type=str, default="sigma",
                        choices=["sigma", "rho"])
    parser.add_argument("--theta", type=int, default=72)
    parser.add_argument("--settle", type=int, default=15000)
    parser.add_argument("--measure", type=int, default=5000)
    args = parser.parse_args()

    render_3d(pair_name=args.pair, phase=args.phase, grid=args.grid,
              field_type=args.field, n_theta=args.theta,
              settle=args.settle, measure=args.measure)
