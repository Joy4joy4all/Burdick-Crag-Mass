"""
Burdick's Crag Mass — Genesis Renderer
========================================
Stephen Justin Burdick, 2026 — Emerald Entities LLC
NSF I-Corps Program — Team GIBUSH

Standalone substrate field visualizer.
Called from launcher after solver run completes.
Receives rho_avg (L x G x G) from solver result.

Layout:
  - Default: N slice panes tiled (N = layers configured)
  - Each slice: ρ_eff heatmap + layer coherence score
  - Click any slice → full Genesis Renderer view (torus geometry)
  - Close full view → back to tiled slices
  - Close tiled → window closes

Usage (from launcher):
    from Burdick_Crag_Mass_Genesis_Renderer import GenesisRenderer
    GenesisRenderer(parent_root, rho_avg, galaxy_name, layers)

Usage (standalone test):
    python Burdick_Crag_Mass_Genesis_Renderer.py
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import math
try:
    from scipy.ndimage import maximum_filter
    _SCIPY = True
except ImportError:
    _SCIPY = False

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.cm as cm
    _MPL = True
except ImportError:
    _MPL = False

# Physical unit constants for λ→Λ conversion
# λ=0.1 (solver) → r_Compton = 1/√λ = 3.16 grid units
# At grid=128 spanning ~30 kpc: 1 grid unit ≈ 0.47 kpc
# Vacuum energy density: ρ_vac ≈ 5.4e-10 J/m³
LAM_SOLVER     = 0.1
GRID_TO_KPC    = 0.234   # kpc per grid unit at grid=128, r_max=30 kpc
RHO_VAC_SI     = 5.4e-10  # J/m³


# ─────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────

BG_DARK   = "#080a0e"
BG_MID    = "#0c0e14"
BG_PANEL  = "#10131a"
ACCENT    = "#60aaff"
GOLD      = "#ffbb44"
GREEN     = "#40ee70"
RED       = "#ff5555"
WHITE     = "#e0e8f0"
DIM       = "#3a4a60"


def field_to_image(field, mode="energy", size=None):
    """
    Convert field array to PIL Image for fast canvas rendering.
    ~50x faster than per-rectangle drawing.
    Falls back gracefully if PIL not available.
    """
    f = field.astype(float)
    fmin = f.min(); fmax = f.max()
    frange = fmax - fmin
    if frange > 0:
        f = (f - fmin) / frange
    else:
        f = np.zeros_like(f)

    H, W = f.shape
    img = np.zeros((H, W, 3), dtype=np.uint8)

    if mode in ("energy", "rho2", "stack", "vp"):
        # Deep blue -> electric blue -> white core
        img[..., 2] = np.clip(60 + f * 195, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(f * 80, 0, 255).astype(np.uint8)
        img[..., 0] = np.clip(f * 30, 0, 255).astype(np.uint8)
    elif mode in ("signed", "flux", "div", "lap"):
        # Diverging: blue=negative, red=positive
        pos = np.clip(f, 0, 1)
        neg = np.clip(-f + 1.0, 0, 1)  # inverted for negative
        # Reconstruct signed from normalized
        raw = field / (abs(fmax) + 1e-9)
        pos_m = np.clip(raw, 0, 1)
        neg_m = np.clip(-raw, 0, 1)
        img[..., 0] = np.clip(pos_m * 220 + 30, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(pos_m * 60 + neg_m * 60, 0, 255).astype(np.uint8)
        img[..., 2] = np.clip(neg_m * 220 + 30, 0, 255).astype(np.uint8)
    elif mode == "grad":
        # Transport pressure: dark -> gold -> white
        img[..., 0] = np.clip(f * 255, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(f * 187, 0, 255).astype(np.uint8)
        img[..., 2] = np.clip(f * 68, 0, 255).astype(np.uint8)
    else:
        img[..., 2] = np.clip(60 + f * 195, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(f * 80, 0, 255).astype(np.uint8)
        img[..., 0] = np.clip(f * 30, 0, 255).astype(np.uint8)

    pil_img = Image.fromarray(img, mode="RGB")
    if size:
        pil_img = pil_img.resize(size, Image.NEAREST)
    return pil_img


def spherical_shading(field, light_dir=(0.4, -0.3, 0.85)):
    """
    Apply spherical surface shading to a 2D field.
    Treats field values as a height map on a sphere.
    Adds depth, limb darkening, and directional lighting.
    No GPU required.
    """
    G = field.shape[0]
    y_arr, x_arr = np.mgrid[0:G, 0:G]
    cx = cy = G // 2

    # Normalized sphere coordinates
    dx = (x_arr - cx) / (cx + 1e-6)
    dy = (y_arr - cy) / (cy + 1e-6)
    r2 = dx**2 + dy**2
    on_sphere = r2 <= 1.0

    # Surface normal from sphere geometry
    z_sphere = np.sqrt(np.clip(1 - r2, 0, 1))

    # Height map from field
    f_norm = field / (np.max(np.abs(field)) + 1e-9)
    gy_h, gx_h = np.gradient(f_norm)
    nx = -gx_h * 2.0
    ny = -gy_h * 2.0
    nz = np.ones_like(f_norm)
    n_len = np.sqrt(nx**2 + ny**2 + nz**2) + 1e-9
    nx /= n_len; ny /= n_len; nz /= n_len

    # Lighting
    lx, ly, lz = light_dir
    ln = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx /= ln; ly /= ln; lz /= ln

    diffuse = np.clip(nx*lx + ny*ly + nz*lz, 0, 1)
    # Limb darkening
    limb = np.clip(z_sphere, 0, 1) ** 0.5
    # Combined
    intensity = 0.5 * np.clip(f_norm, 0, 1) + 0.35 * diffuse + 0.15 * limb
    intensity[~on_sphere] = 0.0

    return intensity


def field_color(v, vmax):
    """Map normalized field value to RGB heatmap color."""
    if vmax <= 0:
        return "#000000"
    t = min(1.0, max(0.0, v / vmax))
    # Deep blue → electric blue → white core
    b = int(min(255, 60 + t * 195))
    g = int(min(255, t * 80))
    r = int(min(255, t * 30))
    return f"#{r:02x}{g:02x}{b:02x}"


def layer_coherence(rho_avg, layer_a, layer_b):
    """Pearson correlation between two layers."""
    a = rho_avg[layer_a].flatten()
    b = rho_avg[layer_b].flatten()
    if np.std(a) == 0 or np.std(b) == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


# ─────────────────────────────────────────
# SLICE CANVAS — one layer pane
# ─────────────────────────────────────────

class SlicePane(tk.Canvas):
    """
    Single layer slice showing ρ_eff heatmap.
    Clickable — calls on_click with layer index.
    """

    def __init__(self, parent, rho_avg, layer_idx, n_layers,
                 on_click=None, on_hover=None, on_leave=None,
                 width=200, height=160):
        super().__init__(parent, width=width, height=height,
                         bg=BG_DARK, highlightthickness=1,
                         highlightbackground=DIM)
        self.rho_avg    = rho_avg
        self.layer_idx  = layer_idx
        self.n_layers   = n_layers
        self.on_click   = on_click
        self.on_hover   = on_hover   # broadcast (gx, gy) to all panes
        self.on_leave   = on_leave   # clear crosshair on all panes
        self.w          = width
        self.h          = height
        self._cross_tag = "crosshair"

        self.bind("<Button-1>",  self._clicked)
        self.bind("<Enter>",     self._hover_on)
        self.bind("<Leave>",     self._hover_off_sync)
        self.bind("<Motion>",    self._motion)

        self._draw()

    def _draw(self):
        self.delete("all")
        rho = self.rho_avg
        L   = rho.shape[0]
        idx = min(self.layer_idx, L - 1)

        field = rho[idx] ** 2  # ρ_eff
        fm    = float(np.max(field))

        G  = field.shape[0]
        pw = self.w
        ph = self.h - 32  # leave room for label
        sx = max(1, G // pw)
        sy = max(1, G // ph)
        cw = pw / (G // sx)
        ch = ph / (G // sy)

        for iy in range(0, G, sy):
            for ix in range(0, G, sx):
                col = field_color(field[iy, ix], fm)
                x0  = (ix // sx) * cw
                y0  = (iy // sy) * ch
                self.create_rectangle(x0, y0, x0+cw+1, y0+ch+1,
                                      fill=col, outline="")

        # Coherence with adjacent layer
        if L > 1:
            adj = (idx + 1) % L
            coh = layer_coherence(rho, idx, adj)
            coh_col = GREEN if coh > 0.95 else GOLD if coh > 0.80 else RED
            coh_str = f"r={coh:+.3f}"
        else:
            coh_str = ""
            coh_col = WHITE

        # Layer label
        label = f"Layer {idx}"
        if idx == 0:
            label += "  [BH pump]"
        self.create_rectangle(0, ph, self.w, self.h,
                              fill=BG_MID, outline="")
        self.create_text(8, ph + 8, text=label,
                         fill=WHITE, font=("Consolas", 9, "bold"), anchor="w")
        if coh_str:
            self.create_text(self.w - 6, ph + 8, text=coh_str,
                             fill=coh_col, font=("Consolas", 9), anchor="e")

        # ρ_eff max
        self.create_text(8, ph + 20, text=f"|ρ²|={fm:.2f}",
                         fill=DIM, font=("Consolas", 8), anchor="w")

    def _clicked(self, event):
        if self.on_click:
            self.on_click(self.layer_idx)

    def _motion(self, event):
        """Broadcast grid coordinate to all sibling panes."""
        if self.on_hover:
            rho = self.rho_avg
            G   = rho.shape[1]
            ph  = self.h - 32
            # Convert canvas pixel → grid coordinate
            gx = int((event.x / self.w) * G)
            gy = int((event.y / ph) * G)
            gx = max(0, min(G-1, gx))
            gy = max(0, min(G-1, gy))
            self.on_hover(gx, gy, self.layer_idx)

    def _hover_on(self, event):
        self.configure(highlightbackground=ACCENT)

    def _hover_off_sync(self, event):
        self.configure(highlightbackground=DIM)
        if self.on_leave:
            self.on_leave()

    def draw_crosshair(self, gx, gy):
        """Draw sync crosshair at grid coordinate (gx, gy)."""
        self.delete(self._cross_tag)
        rho = self.rho_avg
        G   = rho.shape[1]
        ph  = self.h - 32
        px  = int((gx / G) * self.w)
        py  = int((gy / G) * ph)
        # Crosshair lines
        self.create_line(0, py, self.w, py,
                         fill=ACCENT, width=1, dash=(3,3),
                         tags=self._cross_tag)
        self.create_line(px, 0, px, ph,
                         fill=ACCENT, width=1, dash=(3,3),
                         tags=self._cross_tag)
        # Dot at intersection
        self.create_oval(px-3, py-3, px+3, py+3,
                         fill=ACCENT, outline="",
                         tags=self._cross_tag)
        # Value readout
        idx = min(self.layer_idx, rho.shape[0]-1)
        val = float(rho[idx, gy, gx] ** 2)
        self.create_text(px+6, py-10,
                         text=f"ρ²={val:.3f}",
                         fill=ACCENT, font=("Consolas", 7),
                         anchor="w", tags=self._cross_tag)

    def clear_crosshair(self):
        self.delete(self._cross_tag)


# ─────────────────────────────────────────
# FULL GENESIS RENDERER — torus view
# ─────────────────────────────────────────

class FullGenesisView(tk.Toplevel):
    """
    Full-screen Genesis Renderer.
    Shows single layer with torus geometry overlay.
    Layer selector to step through all N layers.
    """

    def __init__(self, parent, rho_avg, galaxy_name, start_layer=0):
        super().__init__(parent)
        self.rho_avg     = rho_avg
        self.galaxy_name = galaxy_name
        self.n_layers    = rho_avg.shape[0]
        self.layer_var   = tk.IntVar(value=start_layer)

        self.title(f"Genesis Renderer — {galaxy_name}")
        self.configure(bg=BG_DARK)
        self.geometry("1100x750")
        self.minsize(800, 600)

        self._build()
        self._draw()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG_DARK)
        hdr.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(hdr, text="GENESIS RENDERER",
                 font=("Georgia", 16), fg=WHITE, bg=BG_DARK).pack(side="left")
        tk.Label(hdr, text=f"  Circumpunct Coherence Engine — {self.galaxy_name}",
                 font=("Consolas", 10), fg=DIM, bg=BG_DARK).pack(side="left", padx=10)
        tk.Button(hdr, text="✕ Close", command=self.destroy,
                  font=("Consolas", 10), bg="#2a1515", fg=RED,
                  relief="flat", padx=8).pack(side="right")
        tk.Button(hdr, text="⬡ 3D Torus", command=self._open_3d,
                  font=("Consolas", 10), bg="#0a1a2a", fg=ACCENT,
                  relief="flat", padx=8).pack(side="right", padx=4)
        tk.Button(hdr, text="⊕ Hysteresis", command=self._show_hysteresis,
                  font=("Consolas", 10), bg="#1a0a2a", fg=GOLD,
                  relief="flat", padx=8).pack(side="right", padx=4)

        # Layer selector
        sel = tk.Frame(self, bg=BG_MID)
        sel.pack(fill="x", padx=10, pady=2)
        tk.Label(sel, text="Layer:", font=("Consolas", 10),
                 fg=WHITE, bg=BG_MID).pack(side="left", padx=8)
        for i in range(self.n_layers):
            label = f"L{i}"
            if i == 0: label += " [pump]"
            tk.Radiobutton(sel, text=label, variable=self.layer_var,
                           value=i, command=self._draw,
                           font=("Consolas", 9), fg=ACCENT, bg=BG_MID,
                           selectcolor=BG_DARK, activebackground=BG_MID).pack(side="left", padx=4)

        # View mode toggles
        modes = tk.Frame(self, bg=BG_PANEL)
        modes.pack(fill="x", padx=10, pady=2)
        self.view_mode = tk.StringVar(value="rho2")
        for val, lbl in [("rho2","ρ²  Energy"),("signed","ρ  Signed"),
                          ("flux","Flux L→L+1"),("grad","∇ρ  Gradient"),
                          ("stack","Layer Stack")]:
            tk.Radiobutton(modes, text=lbl, variable=self.view_mode,
                           value=val, command=self._draw,
                           font=("Consolas", 9), fg=GOLD, bg=BG_PANEL,
                           selectcolor=BG_DARK, activebackground=BG_PANEL).pack(side="left", padx=6)
        self.show_peaks  = tk.BooleanVar(value=True)
        self.show_grad   = tk.BooleanVar(value=False)
        self.show_torus  = tk.BooleanVar(value=True)
        tk.Checkbutton(modes, text="Peaks", variable=self.show_peaks,
                       command=self._draw, font=("Consolas",9), fg=GREEN,
                       bg=BG_PANEL, selectcolor=BG_DARK, activebackground=BG_PANEL).pack(side="left", padx=4)
        tk.Checkbutton(modes, text="Vectors", variable=self.show_grad,
                       command=self._draw, font=("Consolas",9), fg="#88ffaa",
                       bg=BG_PANEL, selectcolor=BG_DARK, activebackground=BG_PANEL).pack(side="left", padx=4)
        tk.Checkbutton(modes, text="Torus", variable=self.show_torus,
                       command=self._draw, font=("Consolas",9), fg=ACCENT,
                       bg=BG_PANEL, selectcolor=BG_DARK, activebackground=BG_PANEL).pack(side="left", padx=4)
        self.phys_units = tk.BooleanVar(value=False)
        tk.Checkbutton(modes, text="kpc/SI units", variable=self.phys_units,
                       command=self._draw, font=("Consolas",9), fg=WHITE,
                       bg=BG_PANEL, selectcolor=BG_DARK, activebackground=BG_PANEL).pack(side="left", padx=8)

        # Main canvas
        self.canvas = tk.Canvas(self, bg=BG_DARK, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=8)
        self.canvas.bind("<Configure>", lambda e: self._draw())

        # Stats bar
        self.stats_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.stats_var,
                 font=("Consolas", 10), fg=ACCENT, bg=BG_DARK).pack(
            fill="x", padx=10, pady=(0, 6))

    def _draw(self):
        self.canvas.delete("all")
        self.canvas.update_idletasks()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return

        idx   = self.layer_var.get()
        rho   = self.rho_avg
        L     = rho.shape[0]
        idx   = min(idx, L - 1)
        mode  = self.view_mode.get()

        # ── Field selection by view mode ──
        if mode == "rho2":
            field = rho[idx] ** 2
            field_label = "ρ² Energy Density"
        elif mode == "signed":
            raw   = rho[idx]
            field = raw  # keep signed
            field_label = "ρ Signed Field"
        elif mode == "flux" and idx < L - 1:
            field = rho[idx + 1] - rho[idx]
            field_label = f"Flux L{idx}→L{idx+1}"
        elif mode == "stack":
            field = np.mean(rho ** 2, axis=0)
            field_label = "Layer Stack Mean rho2"
        elif mode == "div":
            gy_d, gx_d = np.gradient(rho[idx])
            field = np.gradient(gx_d, axis=1) + np.gradient(gy_d, axis=0)
            field_label = "Divergence  +injection  -leakage"
        elif mode == "lap":
            f = rho[idx]
            field = (
                -4 * f +
                np.roll(f, 1, axis=0) + np.roll(f, -1, axis=0) +
                np.roll(f, 1, axis=1) + np.roll(f, -1, axis=1)
            )
            field_label = "Laplacian  trapping zones"
        elif mode == "vp":
            if idx < L - 1:
                dt_field = rho[idx+1] - rho[idx]
                gy_v, gx_v = np.gradient(rho[idx])
                grad_mag = np.sqrt(gx_v**2 + gy_v**2) + 1e-10
                field = dt_field / grad_mag
            else:
                field = rho[idx] ** 2
            field_label = "Vp  Phase velocity"
        else:
            field = rho[idx] ** 2
            field_label = "rho2 Energy Density"

        G  = field.shape[0]
        fm = float(np.max(np.abs(field))) if np.max(np.abs(field)) > 0 else 1.0

        # Field heatmap - left 60% of canvas
        fw = int(w * 0.60)
        fh = h - 20

        # Sphere shading mode
        render_field = field.copy()
        if mode == "planet":
            render_field = spherical_shading(field)
            field_label = "Planet Sphere - height+light shading"

        # === BCM MASTER BUILD ADDITION v2.2 | 2026-03-30 EST ===
        # cw/ch needed by gradient overlay regardless of PIL path
        sx = max(1, G // fw)
        sy = max(1, G // fh)
        cw = fw / (G // sx)
        ch = fh / (G // sy)
        # === END ADDITION ===

        # PIL fast path (~50x faster than rectangle loop)
        if _PIL:
            img_mode = mode if mode != "planet" else "energy"
            pil_img = field_to_image(render_field, mode=img_mode,
                                     size=(fw, fh))
            self._tk_img = ImageTk.PhotoImage(pil_img)
            self.canvas.create_image(0, 10, anchor="nw",
                                     image=self._tk_img)
        else:
            # Fallback: rectangle drawing
            sx = max(1, G // fw)
            sy = max(1, G // fh)
            cw = fw / (G // sx)
            ch = fh / (G // sy)
            for iy in range(0, G, sy):
                for ix in range(0, G, sx):
                    val = render_field[iy, ix]
                    if mode in ("signed", "flux", "div", "lap"):
                        t = val / (fm + 1e-9)
                        if t >= 0:
                            r_c=int(min(255,t*220)); g_c=int(min(255,t*60)); b_c=30
                        else:
                            r_c=30; g_c=int(min(255,-t*60)); b_c=int(min(255,-t*220))
                        col = f"#{r_c:02x}{g_c:02x}{b_c:02x}"
                    else:
                        col = field_color(abs(val), fm)
                    x0 = (ix // sx) * cw
                    y0 = 10 + (iy // sy) * ch
                    self.canvas.create_rectangle(x0, y0, x0+cw+1, y0+ch+1,
                                                 fill=col, outline="")

        # Atmospheric halo for planet mode
        if mode == "planet":
            cx_h = fw // 2; cy_h = h // 2
            r_base = int(min(fw, fh) * 0.44)
            for ri in range(0, 30, 3):
                alpha = max(0, 1.0 - ri/30)
                av = int(alpha * 120)
                hcol = f"#{int(av*0.4):02x}{int(av*0.55):02x}{av:02x}"
                self.canvas.create_oval(
                    cx_h-(r_base+ri), cy_h-(r_base+ri),
                    cx_h+(r_base+ri), cy_h+(r_base+ri),
                    outline=hcol)

        # Field label
        self.canvas.create_text(fw//2, fh + 12, text=field_label,
                                fill=DIM, font=("Consolas", 8))

        # ── Gradient vector field overlay ──
        if self.show_grad.get():
            gy, gx = np.gradient(rho[idx] ** 2)
            step = max(4, G // 24)
            for iy in range(step//2, G, step):
                for ix in range(step//2, G, step):
                    dx = float(gx[iy, ix])
                    dy = float(gy[iy, ix])
                    mag = math.sqrt(dx*dx + dy*dy) + 1e-9
                    scale = (cw * step * 0.45) / mag
                    x0v = (ix / G) * fw
                    y0v = 10 + (iy / G) * fh
                    x1v = x0v + dx * scale
                    y1v = y0v + dy * scale
                    alpha = min(1.0, mag / (fm * 0.1 + 1e-9))
                    brightness = int(80 + alpha * 175)
                    col = f"#00{brightness:02x}44"
                    self.canvas.create_line(x0v, y0v, x1v, y1v,
                                            fill=col, width=1, arrow=tk.LAST)

        # ── Peak detection overlay ──
        if self.show_peaks.get() and _SCIPY:
            peak_field = rho[idx] ** 2
            thresh = float(np.max(peak_field)) * 0.6
            local_max = maximum_filter(peak_field, size=max(3, G//16))
            peaks_mask = (peak_field == local_max) & (peak_field > thresh)
            peak_coords = np.argwhere(peaks_mask)
            n_peaks = len(peak_coords)
            for py, px_p in peak_coords:
                px_c = (px_p / G) * fw
                py_c = 10 + (py / G) * fh
                pcol = RED if n_peaks > 1 else GREEN
                self.canvas.create_oval(px_c-5, py_c-5, px_c+5, py_c+5,
                                        fill=pcol, outline=WHITE, width=1)
            # Label peak count
            peak_col = RED if n_peaks > 1 else GREEN
            peak_msg = f"Peaks: {n_peaks}  {'← MERGER SIGNATURE' if n_peaks > 1 else '← CLEAN'}"
            self.canvas.create_text(fw - 8, fh + 12, text=peak_msg,
                                    fill=peak_col, font=("Consolas", 8), anchor="e")

        # Torus geometry overlay — data-driven rings from field
        if self.show_torus.get():
            cx_f = fw // 2
            cy_f = h // 2
            # Compute radial profile for ring detection
            _G = field.shape[0]
            _iy, _ix = np.mgrid[0:_G, 0:_G]
            _ri = np.sqrt((_ix-_G//2)**2 + (_iy-_G//2)**2).astype(int)
            _mr = _G // 2 - 2
            _prof = np.array([
                np.mean(np.abs(field[_ri == r])) if np.any(_ri == r) else 0
                for r in range(_mr)])
            _pm = np.max(_prof) if np.max(_prof) > 0 else 1.0
            _prof_n = _prof / _pm
            # Data-driven radii
            _r_peak  = int(np.argmax(_prof_n))
            _r_break = int(np.argmax(np.gradient(_prof_n))) if _mr > 4 else _mr//2
            _half    = np.where(_prof_n > 0.5)[0]
            _r_core  = int(_half[-1]) if len(_half) > 0 else _mr//4
            # Scale grid coords to canvas coords
            def _gc(r): return int(r / (_G//2) * min(fw, fh) * 0.46)
            r_peak_c  = _gc(_r_peak)
            r_break_c = _gc(_r_break)
            r_core_c  = _gc(_r_core)
            r_outer_c = int(min(fw, fh) * 0.46)
            # Draw rings
            for r_px, col_r, dash_r, lbl_r in [
                (r_outer_c,  ACCENT, (8,4), "Torus rim"),
                (r_peak_c,   ACCENT, (6,3), "Peak ring"),
                (r_break_c,  RED,    (3,6), "Wave break"),
                (r_core_c,   GOLD,   (4,4), "Core (half-max)"),
            ]:
                if r_px > 4:
                    self.canvas.create_oval(
                        cx_f-r_px, cy_f-r_px, cx_f+r_px, cy_f+r_px,
                        outline=col_r, width=1, dash=dash_r)
            self.canvas.create_oval(cx_f-5, cy_f-5, cx_f+5, cy_f+5,
                                    fill=GOLD, outline="")
            # Legend
            legend_items = [
                (ACCENT, (8,4), "Torus rim"),
                (ACCENT, (6,3), "Peak ring"),
                (RED,    (3,6), "Wave break"),
                (GOLD,   (4,4), "Core half-max"),
            ]
            for li, (lc, ld, lt) in enumerate(legend_items):
                yy = 14 + li * 12
                self.canvas.create_line(10, yy, 35, yy, fill=lc, width=1, dash=ld)
                self.canvas.create_text(40, yy, text=lt, fill=lc,
                                        font=("Consolas", 8), anchor="w")

        # Right panel — radial profile + layer coherence
        px = fw + 15
        pw = w - px - 10
        if pw < 80:
            return

        # Radial profile
        cy_f2 = h // 2
        mr    = G // 2 - 5
        prof  = np.zeros(mr)
        cnt   = np.zeros(mr)
        iy_arr, ix_arr = np.mgrid[0:G, 0:G]
        ri_arr = np.sqrt((ix_arr - G//2)**2 + (iy_arr - G//2)**2).astype(int)
        for ri in range(mr):
            mask = ri_arr == ri
            if np.any(mask):
                prof[ri] = np.mean(field[mask])
                cnt[ri]  = 1

        pm = np.max(prof) if np.max(prof) > 0 else 1.0
        prof_n = prof / pm

        # Draw radial profile chart
        chart_h = int(h * 0.55)
        chart_y = (h - chart_h) // 2
        self.canvas.create_rectangle(px, chart_y, px + pw, chart_y + chart_h,
                                     fill=BG_MID, outline=DIM)
        self.canvas.create_text(px + pw//2, chart_y - 10,
                                text=f"Layer {idx} Radial ρ² Profile",
                                fill=WHITE, font=("Consolas", 9, "bold"))
        pts = []
        for ri in range(min(mr, len(prof_n))):
            x = px + int(ri / mr * pw)
            y = chart_y + chart_h - int(prof_n[ri] * chart_h * 0.9)
            pts.extend([x, y])
        if len(pts) >= 4:
            self.canvas.create_line(*pts, fill=ACCENT, width=2, smooth=True)

        # Layer coherence column
        coh_y = chart_y + chart_h + 20
        self.canvas.create_text(px + pw//2, coh_y,
                                text="Layer Coherence",
                                fill=WHITE, font=("Consolas", 9, "bold"))
        for i in range(min(L - 1, 8)):
            coh = layer_coherence(rho, i, i + 1)
            col = GREEN if coh > 0.95 else GOLD if coh > 0.80 else RED
            bar_w = int(coh * pw * 0.8)
            y = coh_y + 16 + i * 18
            self.canvas.create_rectangle(px, y, px + bar_w, y + 12,
                                         fill=col, outline="")
            self.canvas.create_text(px + pw - 2, y + 6,
                                    text=f"L{i}→L{i+1}: {coh:+.3f}",
                                    fill=col, font=("Consolas", 8), anchor="e")

        # ── Transport Efficiency — inner/mid/outer bands ──
        te_y = coh_y + 16 + min(L-1, 8) * 18 + 16
        self.canvas.create_text(px + pw//2, te_y,
                                text="Transport Efficiency",
                                fill=WHITE, font=("Consolas", 9, "bold"))
        _G2   = field.shape[0]
        _iy2, _ix2 = np.mgrid[0:_G2, 0:_G2]
        _ri2  = np.sqrt((_ix2-_G2//2)**2 + (_iy2-_G2//2)**2)
        _r_max2 = _G2 // 2
        _gy2, _gx2 = np.gradient(np.abs(field))
        _gmag2 = np.sqrt(_gx2**2 + _gy2**2)
        bands = [
            ("Inner",  0.0,  0.25, GOLD),
            ("Mid",    0.25, 0.65, GREEN),
            ("Outer",  0.65, 1.0,  ACCENT),
        ]
        te_vals = []
        for bname, r0, r1, bcol in bands:
            mask_b = (_ri2 >= r0*_r_max2) & (_ri2 < r1*_r_max2)
            te = float(np.mean(_gmag2[mask_b])) if np.any(mask_b) else 0
            te_vals.append((bname, te, bcol))
        te_max = max(v for _,v,_ in te_vals) if te_vals else 1.0
        for bi, (bname, te, bcol) in enumerate(te_vals):
            bar_w2 = int((te / (te_max + 1e-10)) * pw * 0.8)
            yb = te_y + 16 + bi * 18
            self.canvas.create_rectangle(px, yb, px+bar_w2, yb+12,
                                         fill=bcol, outline="")
            self.canvas.create_text(px + pw - 2, yb + 6,
                                    text=f"{bname}: {te:.3f}",
                                    fill=bcol, font=("Consolas", 8), anchor="e")

        # ── Anisotropy Detector ──
        ani_y = te_y + 16 + len(bands) * 18 + 14
        # Compute angular variance in mid-band
        _angles = np.arctan2(_iy2 - _G2//2, _ix2 - _G2//2)
        _mid_mask = (_ri2 >= 0.25*_r_max2) & (_ri2 < 0.65*_r_max2)
        _bins = np.linspace(-np.pi, np.pi, 33)
        _ang_energy = []
        for _bi in range(len(_bins)-1):
            _amask = _mid_mask & (_angles >= _bins[_bi]) & (_angles < _bins[_bi+1])
            _ang_energy.append(float(np.mean(np.abs(field[_amask])))
                               if np.any(_amask) else 0)
        _aniso = float(np.std(_ang_energy)) if _ang_energy else 0
        _aniso_norm = _aniso / (np.mean(_ang_energy) + 1e-10) if _ang_energy else 0
        _aniso_col = RED if _aniso_norm > 0.3 else GOLD if _aniso_norm > 0.15 else GREEN
        _aniso_lbl = ("HIGH — merger/asymmetry" if _aniso_norm > 0.3
                      else "MED — partial disruption" if _aniso_norm > 0.15
                      else "LOW — clean transport")
        self.canvas.create_text(px + pw//2, ani_y,
                                text="Anisotropy",
                                fill=WHITE, font=("Consolas", 9, "bold"))
        _ani_bar = int(min(_aniso_norm, 1.0) * pw * 0.8)
        self.canvas.create_rectangle(px, ani_y+14, px+_ani_bar, ani_y+26,
                                     fill=_aniso_col, outline="")
        self.canvas.create_text(px + pw//2, ani_y + 32,
                                text=f"sigma={_aniso_norm:.3f}  {_aniso_lbl}",
                                fill=_aniso_col, font=("Consolas", 7))

        # ── Layer Flow Coupling (alongside coherence) ──
        if L > 1:
            fc_y = ani_y + 50
            self.canvas.create_text(px + pw//2, fc_y,
                                    text="Layer Flow Coupling",
                                    fill=WHITE, font=("Consolas", 9, "bold"))
            for i in range(min(L-1, 4)):
                _fc = float(np.mean(np.abs(rho[i+1] - rho[i])))
                _ps = float(np.mean(np.sign(rho[i+1]) != np.sign(rho[i])))
                _fc_col = GREEN if _fc > 0.01 else GOLD if _fc > 0.001 else DIM
                yfc = fc_y + 16 + i * 18
                _fc_bar = int(min(_fc * 500, 1.0) * pw * 0.6)
                self.canvas.create_rectangle(px, yfc, px+_fc_bar, yfc+10,
                                             fill=_fc_col, outline="")
                self.canvas.create_text(px + pw - 2, yfc + 5,
                                        text=f"L{i}+{i+1}: {_fc:.4f} | ph:{_ps:.0%}",
                                        fill=_fc_col,
                                        font=("Consolas", 7), anchor="e")

        # ── Local Coherence Index (LCI) contour overlay ──
        if idx < L - 1:
            lci = np.abs(rho[idx] - rho[idx+1])
            lci_max = float(np.max(lci)) if np.max(lci) > 0 else 1.0
            lci_norm = lci / lci_max
            # Draw contour lines where LCI > 0.7 (turbulent boundary)
            step_c = max(2, G // 32)
            for iy_c in range(0, G-step_c, step_c):
                for ix_c in range(0, G-step_c, step_c):
                    v = lci_norm[iy_c, ix_c]
                    if v > 0.7:
                        x0c = (ix_c / G) * fw
                        y0c = 10 + (iy_c / G) * fh
                        col_c = RED if v > 0.85 else GOLD
                        self.canvas.create_rectangle(
                            x0c, y0c, x0c + cw*step_c, y0c + ch*step_c,
                            outline=col_c, fill="", width=1)

        # ── Physical unit scale bar ──
        if self.phys_units.get():
            kpc_per_grid = GRID_TO_KPC
            r_kpc = (G // 2) * kpc_per_grid
            bar_kpc = round(r_kpc * 0.25)
            bar_px  = int(bar_kpc / kpc_per_grid / (G / fw))
            bx0, by0 = 10, fh - 20
            self.canvas.create_line(bx0, by0, bx0+bar_px, by0,
                                    fill=WHITE, width=2)
            self.canvas.create_text(bx0 + bar_px//2, by0 - 8,
                                    text=f"{bar_kpc} kpc",
                                    fill=WHITE, font=("Consolas", 8))
            # Energy density label
            rho2_max = float(np.max(rho[idx]**2))
            e_si = rho2_max * RHO_VAC_SI
            self.canvas.create_text(fw - 8, fh - 12,
                                    text=f"ρ²_max ≈ {e_si:.2e} J/m³",
                                    fill=DIM, font=("Consolas", 7), anchor="e")

        # Stats bar
        rho_max = float(np.max(np.abs(rho[idx])))
        rho_eff_max = float(np.max(rho[idx]**2))
        n_peaks_str = ""
        if self.show_peaks.get() and _SCIPY:
            peak_field = rho[idx] ** 2
            thresh = float(np.max(peak_field)) * 0.6
            local_max = maximum_filter(peak_field, size=max(3, G//16))
            n_p = int(np.sum((peak_field == local_max) & (peak_field > thresh)))
            n_peaks_str = f"  |  Peaks={n_p} {'MERGER?' if n_p>1 else 'CLEAN'}"
        self.stats_var.set(
            f"Layer {idx} [{mode}]  |  |ρ|={rho_max:.3f}  |  |ρ²|={rho_eff_max:.3f}"
            f"  |  {G}x{G}  |  L={L}{n_peaks_str}"
        )


    def _open_3d(self):
        """3D Torus projection using matplotlib embedded in Tk."""
        if not _MPL:
            import tkinter.messagebox as mb
            mb.showwarning("3D Torus", "matplotlib not available.")
            return
        win = tk.Toplevel(self)
        win.title(f"3D Torus — {self.galaxy_name}")
        win.configure(bg=BG_DARK)
        win.geometry("900x700")

        rho  = self.rho_avg
        L    = rho.shape[0]
        G    = rho.shape[1]

        fig  = Figure(figsize=(9, 6.5), facecolor="#080a0e")
        ax   = fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#080a0e")
        ax.grid(False)
        ax.set_xlabel("X (grid)", color="#60aaff", fontsize=8)
        ax.set_ylabel("Y (grid)", color="#60aaff", fontsize=8)
        ax.set_zlabel("Layer", color="#ffbb44", fontsize=8)
        ax.tick_params(colors="#3a4a60", labelsize=7)
        fig.suptitle(f"Substrate Torus — {self.galaxy_name}",
                     color="#e0e8f0", fontsize=11)

        # Torus parameters
        R_maj = G * 0.35   # major radius (galactic disk plane)
        r_min = L * 1.8    # minor radius (layer depth)

        # Sample the field onto the torus surface
        n_theta = 64   # around the torus tube
        n_phi   = 128  # around the major circle

        theta = np.linspace(0, 2*np.pi, n_theta)
        phi   = np.linspace(0, 2*np.pi, n_phi)
        T, P  = np.meshgrid(theta, phi)

        # Torus coordinates
        X = (R_maj + r_min * np.cos(T)) * np.cos(P)
        Y = (R_maj + r_min * np.cos(T)) * np.sin(P)
        Z = r_min * np.sin(T)

        # Map layer index from T angle (0=layer0, π=opposite)
        layer_idx_t = ((T + np.pi) % (2*np.pi) / (2*np.pi) * L).astype(int)
        layer_idx_t = np.clip(layer_idx_t, 0, L-1)

        # Map grid position from P angle
        gx_t = (G//2 + (R_maj * np.cos(P) / R_maj * (G//2 - 5))).astype(int)
        gy_t = (G//2 + (R_maj * np.sin(P) / R_maj * (G//2 - 5))).astype(int)
        gx_t = np.clip(gx_t, 0, G-1)
        gy_t = np.clip(gy_t, 0, G-1)

        # Field values on torus
        C = np.zeros_like(X)
        for i in range(n_phi):
            for j in range(n_theta):
                li = layer_idx_t[i, j]
                C[i, j] = float(rho[li, gy_t[i,j], gx_t[i,j]] ** 2)

        C_max = np.max(C) if np.max(C) > 0 else 1.0
        C_norm = C / C_max

        surf = ax.plot_surface(X, Y, Z, facecolors=cm.plasma(C_norm),
                               alpha=0.85, linewidth=0, antialiased=True)

        # BH spike lines
        for angle_deg in range(0, 360, 45):
            angle = math.radians(angle_deg)
            xs = [0, R_maj * math.cos(angle)]
            ys = [0, R_maj * math.sin(angle)]
            zs = [0, 0]
            ax.plot(xs, ys, zs, color="#ffbb44", linewidth=0.8, alpha=0.6)

        # BH center
        ax.scatter([0], [0], [0], color="#ffbb44", s=80, zorder=10)

        canvas_3d = FigureCanvasTkAgg(fig, master=win)
        canvas_3d.draw()
        canvas_3d.get_tk_widget().pack(fill="both", expand=True)

        # Colorbar label
        tk.Label(win,
                 text=f"Color = ρ²  |  Layers={L}  |  Grid={G}x{G}  |  {self.galaxy_name}",
                 font=("Consolas", 9), fg=ACCENT, bg=BG_DARK).pack(pady=4)

    def _show_hysteresis(self):
        """
        Asymmetry detector — Crag-and-Tail analysis.
        Computes directional bias in substrate density.
        High asymmetry = merger fossil field signature.
        """
        rho   = self.rho_avg
        idx   = self.layer_var.get()
        G     = rho.shape[0]
        field = rho[idx] ** 2
        cx = cy = G // 2

        # Compute quadrant sums
        q_top    = np.sum(field[:cy, :])
        q_bot    = np.sum(field[cy:, :])
        q_left   = np.sum(field[:, :cx])
        q_right  = np.sum(field[:, cx:])
        total    = np.sum(field) + 1e-10

        # Asymmetry vectors
        vert_bias = (q_bot - q_top) / total   # + = bottom heavy
        horiz_bias = (q_right - q_left) / total  # + = right heavy
        asym_mag  = math.sqrt(vert_bias**2 + horiz_bias**2)

        win = tk.Toplevel(self)
        win.title(f"Hysteresis Analysis — {self.galaxy_name}")
        win.configure(bg=BG_DARK)
        win.geometry("420x320")

        tk.Label(win, text="CRAG-AND-TAIL ASYMMETRY DETECTOR",
                 font=("Consolas", 11, "bold"), fg=WHITE, bg=BG_DARK).pack(pady=10)
        tk.Label(win, text=f"Galaxy: {self.galaxy_name}  |  Layer {idx}",
                 font=("Consolas", 9), fg=DIM, bg=BG_DARK).pack()

        c = tk.Canvas(win, width=380, height=160, bg=BG_MID,
                      highlightthickness=0)
        c.pack(padx=16, pady=10)

        # Draw asymmetry compass
        ox, oy = 190, 80
        scale  = 120

        # Background circle
        c.create_oval(ox-scale, oy-scale, ox+scale, oy+scale,
                      outline=DIM, width=1)
        c.create_line(ox-scale, oy, ox+scale, oy, fill=DIM, width=1)
        c.create_line(ox, oy-scale, ox, oy+scale, fill=DIM, width=1)

        # Hysteresis vector
        vx = int(horiz_bias * scale * 3)
        vy = int(vert_bias * scale * 3)
        mag_col = RED if asym_mag > 0.15 else GOLD if asym_mag > 0.05 else GREEN
        c.create_line(ox, oy, ox+vx, oy+vy,
                      fill=mag_col, width=3, arrow=tk.LAST)

        # Labels
        c.create_text(ox, oy-scale-12, text="Top", fill=DIM, font=("Consolas",8))
        c.create_text(ox, oy+scale+12, text="Bottom", fill=DIM, font=("Consolas",8))
        c.create_text(ox-scale-20, oy, text="Left", fill=DIM, font=("Consolas",8))
        c.create_text(ox+scale+20, oy, text="Right", fill=DIM, font=("Consolas",8))
        c.create_text(ox, oy+8, text="BH", fill=GOLD, font=("Consolas",7))

        verdict = "MERGER FOSSIL FIELD DETECTED" if asym_mag > 0.15 else                   "MODERATE ASYMMETRY" if asym_mag > 0.05 else                   "CLEAN — SYMMETRIC SUBSTRATE"
        verdict_col = RED if asym_mag > 0.15 else GOLD if asym_mag > 0.05 else GREEN

        tk.Label(win, text=f"Asymmetry magnitude: {asym_mag:.4f}",
                 font=("Consolas", 10), fg=WHITE, bg=BG_DARK).pack()
        tk.Label(win, text=f"H-bias: {horiz_bias:+.4f}  V-bias: {vert_bias:+.4f}",
                 font=("Consolas", 9), fg=DIM, bg=BG_DARK).pack()
        tk.Label(win, text=verdict,
                 font=("Consolas", 11, "bold"), fg=verdict_col, bg=BG_DARK).pack(pady=6)
        tk.Button(win, text="Close", command=win.destroy,
                  font=("Consolas", 9), bg="#2a1515", fg=RED,
                  relief="flat", padx=12).pack(pady=4)


# ─────────────────────────────────────────
# TILED SLICE VIEW — the default
# ─────────────────────────────────────────

class GenesisRenderer(tk.Toplevel):
    """
    Main Genesis Renderer entry point.
    Called from launcher after solver run.

    Default view: N slice panes tiled in grid.
    Click any slice → FullGenesisView for that layer.
    """

    def __init__(self, parent, rho_avg, galaxy_name="", n_layers=None):
        super().__init__(parent)
        self.rho_avg     = rho_avg
        self.galaxy_name = galaxy_name
        self.n_layers    = n_layers or rho_avg.shape[0]

        self.title(f"Genesis Renderer — {galaxy_name} — {self.n_layers} layers")
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG_DARK)
        hdr.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(hdr, text="GENESIS RENDERER",
                 font=("Georgia", 15), fg=WHITE, bg=BG_DARK).pack(side="left")
        tk.Label(hdr,
                 text=f"  {self.galaxy_name}  —  {self.n_layers} substrate layers",
                 font=("Consolas", 10), fg=DIM, bg=BG_DARK).pack(side="left", padx=10)
        tk.Button(hdr, text="✕ Close", command=self.destroy,
                  font=("Consolas", 10), bg="#2a1515", fg=RED,
                  relief="flat", padx=8).pack(side="right")

        tk.Label(hdr, text="Click any slice to expand →",
                 font=("Consolas", 9), fg=DIM, bg=BG_DARK).pack(side="right", padx=12)
        tk.Button(hdr, text="⬡ 3D Torus All Layers",
                  command=lambda: FullGenesisView(
                      self, self.rho_avg, self.galaxy_name, 0)._open_3d()
                      if hasattr(FullGenesisView(
                      self, self.rho_avg, self.galaxy_name, 0), '_open_3d') else None,
                  font=("Consolas", 9), bg="#0a1a2a", fg=ACCENT,
                  relief="flat", padx=6).pack(side="right", padx=4)

        # Slice grid
        L = min(self.n_layers, self.rho_avg.shape[0])
        cols = min(L, 6)
        rows = math.ceil(L / cols)

        # Dynamically size window
        slice_w = 210
        slice_h = 170
        win_w   = cols * (slice_w + 6) + 20
        win_h   = rows * (slice_h + 6) + 70
        self.geometry(f"{win_w}x{win_h}")

        grid_frame = tk.Frame(self, bg=BG_DARK)
        grid_frame.pack(fill="both", expand=True, padx=8, pady=4)

        self._panes = []
        for i in range(L):
            row = i // cols
            col = i % cols
            pane = SlicePane(
                grid_frame, self.rho_avg, i, L,
                on_click=self._open_full,
                on_hover=self._sync_hover,
                on_leave=self._sync_leave,
                width=slice_w, height=slice_h
            )
            pane.grid(row=row, column=col, padx=3, pady=3)
            self._panes.append(pane)

        # Coord readout bar
        self._coord_var = tk.StringVar(value="Hover over any slice to sync all layers")
        tk.Label(self, textvariable=self._coord_var,
                 font=("Consolas", 9), fg=ACCENT, bg=BG_DARK).pack(pady=(0,4))

    def _sync_hover(self, gx, gy, source_layer):
        """Broadcast crosshair to all panes + update coord bar."""
        rho = self.rho_avg
        G   = rho.shape[1]
        vals = []
        for pane in self._panes:
            pane.draw_crosshair(gx, gy)
            idx = min(pane.layer_idx, rho.shape[0]-1)
            vals.append(f"L{idx}={float(rho[idx,gy,gx]**2):.3f}")
        self._coord_var.set(
            f"Grid ({gx},{gy})  |  " + "  ".join(vals)
        )

    def _sync_leave(self):
        """Clear all crosshairs."""
        for pane in self._panes:
            pane.clear_crosshair()
        self._coord_var.set("Hover over any slice to sync all layers")

    def _open_full(self, layer_idx):
        FullGenesisView(self, self.rho_avg, self.galaxy_name, layer_idx)


# ─────────────────────────────────────────
# SELF TEST
# ─────────────────────────────────────────

if __name__ == "__main__":
    import sys
    print("Genesis Renderer — Self Test")
    print("Generating synthetic substrate field...")

    # Synthetic rho_avg — 6 layers, 128x128
    G = 128
    L = 6
    rho_test = np.zeros((L, G, G))
    cx = cy = G // 2
    iy_g, ix_g = np.mgrid[0:G, 0:G]
    r_grid = np.sqrt((ix_g - cx)**2 + (iy_g - cy)**2).astype(float)

    for l in range(L):
        # Each layer has different structure
        sigma = G * (0.15 + l * 0.05)
        ring_r = G * 0.25 * (1 + l * 0.1)
        ring = np.exp(-((r_grid - ring_r)**2) / (2 * sigma**2))
        core = np.exp(-r_grid**2 / (2 * (G * 0.08)**2))
        rho_test[l] = (core * (1 - l * 0.1) + ring * (0.3 + l * 0.1))
        rho_test[l] *= np.random.uniform(0.85, 1.0, (G, G))

    root = tk.Tk()
    root.withdraw()
    app = GenesisRenderer(root, rho_test, "TEST_GALAXY_BCM", n_layers=L)
    app.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()
