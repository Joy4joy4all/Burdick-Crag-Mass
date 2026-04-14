# -*- coding: utf-8 -*-
"""
BCM Stellar Renderer
====================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Standalone visualization for the BCM stellar substrate wave solver.
Companion to BCM_stellar_wave.py

Shows:
  - Star gallery (5 stars, scanline sphere renderer)
  - Alfven Hamiltonian energy spectrum H(m) = (v_A - OmegaR/m)^2
  - Tachocline field visualization
  - Phase dynamics (cos_delta_phi proxy)
  - Scale invariance table (galactic -> planetary -> stellar)
  - Tensor hypercube (inherited from planetary renderer)

Same architecture as BCM_planetary_renderer.py
Scanline sphere renderer, PIL fast path, same color palette.

Usage:
    python BCM_stellar_renderer.py
    python BCM_stellar_renderer.py --star Sun
    python BCM_stellar_renderer.py --json data/results/BCM_Sun_stellar_wave.json
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import json
import os
import math

try:
    from scipy.special import jv
    _SCIPY = True
except ImportError:
    _SCIPY = False

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

# ─────────────────────────────────────────
# COLOR PALETTE -- same as planetary renderer
# ─────────────────────────────────────────

BG_DARK     = "#080a0e"
BG_MID      = "#0c0e14"
BG_PANEL    = "#10131a"
ACCENT      = "#60aaff"
GOLD        = "#ffbb44"
GREEN       = "#40ee70"
RED         = "#ff5555"
WHITE       = "#e0e8f0"
DIM         = "#3a4a60"
STELLAR_HOT = "#ff9944"
STELLAR_COOL= "#44aaff"

# ─────────────────────────────────────────
# STAR DEFINITIONS
# Visual bands derived from spectral type
# ─────────────────────────────────────────

STARS = {
    "Sun": {
        "bands":        ["#fff5a0","#ffe060","#fff0a0","#ffd840","#ffe880"],
        "corona_color": "#ffcc44",
        "flare":        False,
        "spectral":     "G2V",
        "bcm_class":    "Class I -- Stable Coupled",
        "m_confirmed":  4,
        "status":       "CONFIRMED",
    },
    "Tabby": {
        "bands":        ["#fff0c0","#ffe8a0","#fff4c8","#ffd890","#ffec80"],
        "corona_color": "#ffaa22",
        "flare":        False,
        "spectral":     "F3V",
        "bcm_class":    "Class ? -- Anomalous",
        "m_confirmed":  0,
        "status":       "PREDICTION",
    },
    "Proxima": {
        "bands":        ["#ff6644","#cc3322","#ff7755","#ee4433","#dd5540"],
        "corona_color": "#ff3322",
        "flare":        True,
        "spectral":     "M5.5Ve",
        "bcm_class":    "Class V-A -- Suppressed",
        "m_confirmed":  1,
        "status":       "CONFIRMED",
    },
    "EV_Lac": {
        "bands":        ["#ff5533","#cc2211","#ee4422","#dd3311","#ff6644"],
        "corona_color": "#ff2200",
        "flare":        True,
        "spectral":     "M3.5Ve",
        "bcm_class":    "Class II -- Marginal",
        "m_confirmed":  2,
        "status":       "CONFIRMED",
    },
    "HR_1099": {
        "bands":        ["#ffcc88","#eebb66","#ffd899","#ddaa55","#ffbb77"],
        "corona_color": "#ffaa44",
        "flare":        False,
        "spectral":     "K1IV",
        "bcm_class":    "Class VI -- Tidal Bar",
        "m_confirmed":  2,
        "status":       "BOUNDARY",
    },
}


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _lerp_color(c0, c1, a):
    return (
        int(c0[0]*(1-a) + c1[0]*a),
        int(c0[1]*(1-a) + c1[1]*a),
        int(c0[2]*(1-a) + c1[2]*a),
    )


# ─────────────────────────────────────────
# STAR SPHERE RENDERER
# Same scanline approach as planetary renderer
# ─────────────────────────────────────────

def draw_star(canvas, star_name, cx, cy, radius):
    """
    Scanline sphere renderer for stellar bodies.
    Per-pixel spherical lighting, smooth band blending, limb darkening.
    Corona glow drawn as concentric ovals outside sphere.
    Flare spike drawn for active M dwarfs.
    """
    cfg    = STARS.get(star_name, STARS["Sun"])
    bands  = cfg["bands"]
    n      = len(bands)
    r      = int(radius)
    if r < 4:
        return
    cx = int(cx); cy = int(cy)

    # Light direction -- top left, toward viewer
    LX, LY, LZ = -0.40, -0.30, 0.85
    ln = math.sqrt(LX*LX + LY*LY + LZ*LZ)
    LX /= ln; LY /= ln; LZ /= ln

    CHUNK = max(2, r // 40)

    # ── Corona glow ──
    cc = cfg.get("corona_color", "#ffcc44")
    cc_rgb = _hex_to_rgb(cc)
    for ri in range(r + 30, r - 1, -4):
        alpha = max(0.0, 1.0 - (ri - r) / 32.0)
        cr = int(cc_rgb[0] * alpha * 0.6)
        cg = int(cc_rgb[1] * alpha * 0.4)
        cb = int(cc_rgb[2] * alpha * 0.15)
        gcol = f"#{min(255,cr):02x}{min(255,cg):02x}{min(255,cb):02x}"
        canvas.create_oval(cx-ri, cy-ri, cx+ri, cy+ri,
                           outline=gcol, fill="")

    # ── Scanline sphere ──
    for dy in range(-r, r+1, CHUNK):
        x_chord = int(math.sqrt(max(0.0, float(r*r - dy*dy))))
        if x_chord < 1:
            continue
        t = (dy + r) / (2.0 * r)
        t_scaled = t * (n - 1)
        i0 = int(t_scaled)
        i1 = min(i0 + 1, n - 1)
        blend = t_scaled - i0
        rgb0 = _hex_to_rgb(bands[i0])
        rgb1 = _hex_to_rgb(bands[i1])
        band_rgb = _lerp_color(rgb0, rgb1, blend)

        dx_step = max(1, CHUNK)
        for dx in range(-x_chord, x_chord + 1, dx_step):
            nx = dx / float(r)
            ny = dy / float(r)
            nz2 = 1.0 - nx*nx - ny*ny
            if nz2 < 0:
                continue
            nz = math.sqrt(nz2)
            diffuse = max(0.0, nx*LX + ny*LY + nz*LZ)
            limb = nz ** 0.5
            brightness = max(0.15, 0.25 + 0.55*diffuse + 0.20*limb)
            lit = "#{:02x}{:02x}{:02x}".format(
                int(min(255, band_rgb[0] * brightness)),
                int(min(255, band_rgb[1] * brightness)),
                int(min(255, band_rgb[2] * brightness)))
            x_abs = cx + dx
            y_abs = cy + dy
            canvas.create_rectangle(
                x_abs, y_abs,
                x_abs + dx_step, y_abs + CHUNK,
                fill=lit, outline="")

    # ── Tachocline ring ──
    # Shows the depth of the substrate coupling interface
    cfg_data = STARS.get(star_name, {})
    # Approximate tachocline as fraction of radius
    tach_fracs = {
        "Sun": 0.713, "Tabby": 0.85, "Proxima": 0.0,
        "EV_Lac": 0.1, "HR_1099": 0.65
    }
    tf = tach_fracs.get(star_name, 0.5)
    if tf > 0.05:
        tr = r * tf
        canvas.create_oval(cx-tr, cy-tr, cx+tr, cy+tr,
                           outline=GOLD, dash=(4,4), width=1)

    # ── Flare spike for active M dwarfs ──
    if cfg.get("flare"):
        for angle_deg in [30, 150, 250]:
            a = math.radians(angle_deg)
            fx0 = cx + r * math.cos(a)
            fy0 = cy + r * math.sin(a)
            fl = r * 0.35
            fx1 = cx + (r + fl) * math.cos(a)
            fy1 = cy + (r + fl) * math.sin(a)
            canvas.create_line(fx0, fy0, fx1, fy1,
                               fill=RED, width=2)

    # ── Labels ──
    canvas.create_text(cx, cy + r + 16, text=star_name,
                       fill=WHITE, font=("Consolas", 10, "bold"))
    canvas.create_text(cx, cy + r + 29,
                       text=cfg.get("spectral", ""),
                       fill=DIM, font=("Consolas", 8))
    sub = cfg.get("bcm_class", "")
    status = cfg.get("status", "")
    lc = GREEN if status == "CONFIRMED" else GOLD if status == "PREDICTION" else RED if status == "BOUNDARY" else DIM
    canvas.create_text(cx, cy + r + 42, text=sub,
                       fill=lc, font=("Consolas", 7))


def draw_standing_wave_stellar(canvas, cx, cy, radius, m, color):
    """Draw m-armed standing wave polygon on star."""
    if not m or m <= 0:
        return
    pts = []
    for i in range(m):
        angle = math.radians(360 * i / m - 90)
        pts.append(cx + radius * 0.78 * math.cos(angle))
        pts.append(cy + radius * 0.78 * math.sin(angle))
    if len(pts) >= 4:
        canvas.create_polygon(*pts, outline=color,
                               fill="", width=2, dash=(5, 3))
    for i in range(m):
        angle = math.radians(360 * i / m - 90)
        vx = cx + radius * 0.78 * math.cos(angle)
        vy = cy + radius * 0.78 * math.sin(angle)
        canvas.create_line(cx, cy, vx, vy,
                           fill=color, width=1, dash=(2, 5))
    canvas.create_oval(cx-4, cy-4, cx+4, cy+4,
                       fill=color, outline="")


# ─────────────────────────────────────────
# FIELD GENERATORS
# ─────────────────────────────────────────

def generate_alfven_field(grid=256, m=4, v_A=353.0, omega_r=1420.0):
    """
    Generate 2D visualization of Alfven Hamiltonian H(m).
    Shows the tachocline coupling field -- where v_A meets OmegaR/m.
    Bright region = low H(m) = strong substrate coupling.
    """
    cx = cy = grid // 2
    x = np.arange(grid) - cx
    y = np.arange(grid) - cy
    X, Y = np.meshgrid(x, y)
    r = np.sqrt(X**2 + Y**2)
    theta = np.arctan2(Y, X)
    r_max = grid // 2
    r_norm = r / (r_max + 1e-9)

    # H(m) varies radially -- v_phase = omega * r_tach / m
    # At coupling radius: v_A = omega * r / m -> H(m) = 0
    coupling_r = v_A / (omega_r / (m + 1e-9)) if omega_r > 0 else 0.5
    coupling_r = min(max(coupling_r, 0.1), 1.5)

    H_field = (v_A - omega_r * r_norm / m) ** 2
    H_field = H_field / (np.max(H_field) + 1e-9)
    # Invert so bright = low H = strong coupling
    field = 1.0 - H_field

    # Azimuthal modulation at mode m
    azimuthal = 0.5 + 0.5 * np.cos(m * theta)
    field = field * (0.6 + 0.4 * azimuthal)

    # Tachocline boundary
    tach_frac = 0.713  # solar default
    mask = r_norm <= 1.0
    field[~mask] = 0.0
    fmax = np.max(np.abs(field))
    if fmax > 0:
        field /= fmax
    return field


def generate_tachocline_field(grid=256, conv_depth=0.287):
    """
    Visualize the tachocline interface layer.
    Inner region: radiative zone (substrate gate closed).
    Tachocline ring: coupling interface (substrate gate).
    Outer region: convective zone (substrate flowing).
    """
    cx = cy = grid // 2
    x = np.arange(grid) - cx
    y = np.arange(grid) - cy
    X, Y = np.meshgrid(x, y)
    r = np.sqrt(X**2 + Y**2)
    r_norm = r / (grid // 2 + 1e-9)

    r_tach = 1.0 - conv_depth
    sigma = 0.04

    # Tachocline ring = Gaussian peak at r_tach
    field = np.exp(-((r_norm - r_tach)**2) / (2 * sigma**2))

    # Radiative zone (inner) -- dim
    radiative = (r_norm < r_tach - sigma * 2).astype(float) * 0.1
    # Convective zone (outer) -- medium
    convective = (r_norm > r_tach + sigma * 2).astype(float) * 0.3

    field = field + radiative + convective
    mask = r_norm <= 1.0
    field[~mask] = 0.0
    fmax = np.max(field)
    if fmax > 0:
        field /= fmax
    return field


def field_to_image_stellar(field, mode="alfven", size=None):
    """PIL field renderer for stellar views."""
    f = field.astype(float)
    fmin = f.min(); fmax = f.max()
    frange = fmax - fmin
    if frange > 0:
        f = (f - fmin) / frange
    else:
        f = np.zeros_like(f)
    H, W = f.shape
    img = np.zeros((H, W, 3), dtype=np.uint8)

    if mode == "alfven":
        # Gold-white for Alfven coupling field
        img[..., 0] = np.clip(40 + f*215, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(20 + f*180, 0, 255).astype(np.uint8)
        img[..., 2] = np.clip(f*80, 0, 255).astype(np.uint8)
    elif mode == "tachocline":
        # Blue inner, gold ring, orange outer
        img[..., 0] = np.clip(20 + f*200, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(f*140, 0, 255).astype(np.uint8)
        img[..., 2] = np.clip(80 + f*100, 0, 255).astype(np.uint8)
    elif mode == "signed":
        raw = (field / (abs(field).max() + 1e-9))
        pos = np.clip(raw, 0, 1); neg = np.clip(-raw, 0, 1)
        img[..., 0] = np.clip(pos*220+30, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(pos*60+neg*60, 0, 255).astype(np.uint8)
        img[..., 2] = np.clip(neg*220+30, 0, 255).astype(np.uint8)
    else:
        img[..., 0] = np.clip(40 + f*215, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(20 + f*180, 0, 255).astype(np.uint8)
        img[..., 2] = np.clip(f*80, 0, 255).astype(np.uint8)

    pil_img = Image.fromarray(img, mode="RGB")
    if size:
        pil_img = pil_img.resize(size, Image.NEAREST)
    return pil_img


# ─────────────────────────────────────────
# TENSOR HYPERCUBE (inherited from planetary)
# ─────────────────────────────────────────

def generate_hypercube_vertices(q):
    n_verts = 2**q
    verts_nd = [[(i >> d) & 1 for d in range(q)] for i in range(n_verts)]
    edges = [(i,j) for i in range(n_verts) for j in range(i+1,n_verts)
             if sum(1 for d in range(q) if verts_nd[i][d]!=verts_nd[j][d])==1]
    return verts_nd, edges


def project_hypercube(verts_nd, q, angle, cx, cy, scale):
    proj = []
    for v in verts_nd:
        coords = [c - 0.5 for c in v]
        for d in range(min(q-1, 4)):
            a = angle * (1.0 + d * 0.3)
            if d+1 < len(coords):
                c0, c1 = coords[d], coords[d+1]
                coords[d]   = c0*math.cos(a) - c1*math.sin(a)
                coords[d+1] = c0*math.sin(a) + c1*math.cos(a)
        x = cx + coords[0] * scale
        y = cy + coords[1] * scale * 0.8
        depth = sum(coords[2:]) if len(coords) > 2 else 0
        proj.append((x, y, depth))
    return proj


# ─────────────────────────────────────────
# MAIN RENDERER
# ─────────────────────────────────────────

class StellarRenderer:

    def __init__(self, parent, json_path=None, star_name=None, binary_data=None):
        self.parent    = parent
        self.json_path = json_path
        self.result    = {}
        self.star_name = star_name or "Sun"
        self.m_pred    = 4
        self.v_A       = 353.0
        self.omega_r   = 1420.0
        self._angle    = 0.0
        self._anim_id  = None
        self.v_tidal   = 0.0
        self.m_alfven  = 4
        self.m_tidal   = 4
        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        self.binary_data = binary_data
        # === END ADDITION ===

        # Load JSON if provided
        if json_path and os.path.exists(json_path):
            with open(json_path, encoding="utf-8") as f:
                self.result = json.load(f)
            self.star_name = self.result.get("star", self.star_name)
            self.m_pred    = self.result.get("m_predicted_H", 4)
            self.v_A       = self.result.get("v_A_ms", 353.0)
            # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
            # Load physical omega*R_tach for accurate Alfven line placement
            omega_s = self.result.get("omega_rad_s", None)
            R_tach  = self.result.get("R_tach_m", None)
            if omega_s and R_tach:
                self.omega_r = omega_s * R_tach
            # Tidal velocity for binary stars
            self.v_tidal   = self.result.get("v_tidal_ms", 0.0)
            self.m_alfven  = self.result.get("m_alfven", self.m_pred)
            self.m_tidal   = self.result.get("m_tidal", self.m_pred)
            # === END ADDITION ===

        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        # Binary mode: override star name for window title
        if self.binary_data:
            info = self.binary_data.get('info', {})
            self.star_name = (f"{info.get('star_A', '?')} + "
                              f"{info.get('star_B', '?')}")
        # === END ADDITION ===

        # Regenerate fields for current star
        conv_depths = {
            "Sun": 0.287, "Tabby": 0.15, "Proxima": 1.0,
            "EV_Lac": 0.9, "HR_1099": 0.35
        }
        cd = conv_depths.get(self.star_name, 0.287)
        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        # Skip field generation in binary mode — not needed
        if not self.binary_data:
            self.alfven_field     = generate_alfven_field(256, m=max(1,self.m_pred),
                                                           v_A=self.v_A,
                                                           omega_r=self.omega_r)
            self.tachocline_field = generate_tachocline_field(256, conv_depth=cd)
        else:
            self.alfven_field     = np.zeros((64, 64))
            self.tachocline_field = np.zeros((64, 64))
        # === END ADDITION ===

        self._build()

    def _load_all_star_results(self):
        base = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(base, "data", "results")
        star_data = {}
        for name in STARS:
            fpath = os.path.join(results_dir, f"BCM_{name}_stellar_wave.json")
            if os.path.exists(fpath):
                try:
                    with open(fpath, encoding="utf-8") as f:
                        star_data[name] = json.load(f)
                except Exception:
                    pass
        # Also try batch file
        batch_path = os.path.join(results_dir, "BCM_stellar_batch.json")
        if os.path.exists(batch_path):
            try:
                with open(batch_path, encoding="utf-8") as f:
                    batch = json.load(f)
                for name, data in batch.get("stars", {}).items():
                    if name not in star_data:
                        star_data[name] = data
            except Exception:
                pass
        return star_data

    def _build(self):
        self.win = tk.Toplevel(self.parent)
        self.win.title(f"BCM STELLAR RENDERER -- {self.star_name} Substrate Field")
        self.win.geometry("1500x950")
        self.win.configure(bg=BG_DARK)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Header ──
        hf = tk.Frame(self.win, bg=BG_DARK)
        hf.pack(fill="x", padx=12, pady=(8,4))
        tk.Label(hf, text="BCM STELLAR RENDERER",
                 font=("Georgia", 18), fg=WHITE, bg=BG_DARK).pack(side="left")
        tk.Label(hf, text="  Tachocline Coherence Engine -- Stellar Scale-Invariance",
                 font=("Consolas", 10), fg="#6a7a90", bg=BG_DARK).pack(side="left")
        tk.Button(hf, text="X Close", command=self._on_close,
                  bg="#2a1010", fg=RED,
                  font=("Consolas", 10), relief="flat").pack(side="right")

        # ── View selector ──
        vf = tk.Frame(self.win, bg=BG_MID)
        vf.pack(fill="x", padx=12, pady=(0,4))
        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        self.view_var = tk.StringVar(
            value="binary" if self.binary_data else "stars")
        # === END ADDITION ===
        views = [
            ("Stars",          "stars"),
            ("Alfven Field",   "alfven"),
            ("Tachocline",     "tachocline"),
            ("Signed",         "signed"),
            ("H(m) Spectrum",  "spectrum"),
            ("Scale Table",    "scale"),
            ("Tensor Hypercube","tensor"),
            # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
            ("Binary Bridge",  "binary"),
            # === END ADDITION ===
        ]
        for label, val in views:
            tk.Radiobutton(vf, text=label, variable=self.view_var,
                           value=val, command=self._on_view_change,
                           bg=BG_MID, fg=ACCENT, selectcolor=BG_DARK,
                           font=("Consolas", 10),
                           activebackground=BG_MID).pack(side="left", padx=6, pady=4)

        # Tensor Q spinbox
        qf = tk.Frame(vf, bg=BG_MID)
        qf.pack(side="right", padx=12)
        tk.Label(qf, text="Tensor Q:", font=("Consolas", 10),
                 fg=GOLD, bg=BG_MID).pack(side="left", padx=(0,4))
        self.q_var = tk.IntVar(value=4)
        ttk.Spinbox(qf, from_=2, to=7, textvariable=self.q_var,
                    width=4, command=self._on_q_change,
                    font=("Consolas", 11)).pack(side="left")
        tk.Label(qf, text="dim", font=("Consolas", 9),
                 fg=DIM, bg=BG_MID).pack(side="left", padx=(2,0))
        self.q_info = tk.Label(qf, text="16 verts  32 edges",
                                font=("Consolas", 8), fg=DIM, bg=BG_MID)
        self.q_info.pack(side="left", padx=(6,0))

        # ── Main area ──
        main = tk.Frame(self.win, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=12, pady=4)

        self.canvas = tk.Canvas(main, bg=BG_DARK, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_resize)
        self._cw = 900
        self._ch = 750

        # Right panel
        rp = tk.Frame(main, bg=BG_DARK, width=340)
        rp.pack(side="left", fill="y", padx=(8,0))
        rp.pack_propagate(False)
        self._build_right(rp)

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.win, textvariable=self.status_var,
                 font=("Consolas", 10), fg=DIM, bg=BG_DARK).pack(
                     fill="x", padx=12, pady=(0,4))

        self._update_q_info()
        self._refresh()

    def _build_right(self, parent):
        # Star parameters
        sf = tk.LabelFrame(parent, text=f"{self.star_name.upper()} PARAMETERS",
                           bg=BG_MID, fg=GOLD,
                           font=("Consolas", 10, "bold"))
        sf.pack(fill="x", padx=4, pady=4)

        params = self.result.get("planet_parameters", {})
        rows = [
            ("Spectral", self.result.get("spectral_type",
                          STARS.get(self.star_name, {}).get("spectral","?"))),
            ("BCM Class", self.result.get("bcm_class",
                          STARS.get(self.star_name, {}).get("bcm_class","?"))),
            ("v_A m/s",  f"{self.result.get('v_A_ms', self.v_A):.1f}"),
            ("J_ind",    f"{self.result.get('J_ind_SI', 0):.3e} A/m^2"),
            ("m_obs",    f"{self.result.get('m_observed','?')}"),
            ("m_pred",   f"{self.result.get('m_predicted_H', self.m_pred)}"),
            ("Match",    "YES" if self.result.get("match_hamiltonian") is True
                         else "NO" if self.result.get("match_hamiltonian") is False
                         else "N/A"),
        ]
        for label, val in rows:
            rf = tk.Frame(sf, bg=BG_MID)
            rf.pack(fill="x", padx=4, pady=1)
            tk.Label(rf, text=f"{label}:", font=("Consolas", 9),
                     fg=DIM, bg=BG_MID, width=9, anchor="w").pack(side="left")
            color = (GREEN if "YES" in str(val)
                     else RED if val == "NO"
                     else GOLD if val == "N/A" else WHITE)
            tk.Label(rf, text=str(val), font=("Consolas", 9, "bold"),
                     fg=color, bg=BG_MID).pack(side="left")

        # H(m) Alfven energy bars
        hf = tk.LabelFrame(parent, text="ALFVEN HAMILTONIAN H(m)",
                           bg=BG_MID, fg=GOLD,
                           font=("Consolas", 10, "bold"))
        hf.pack(fill="x", padx=4, pady=4)
        tk.Label(hf, text="H(m) = (v_A - OmegaR/m)^2",
                 font=("Consolas", 8), fg=DIM, bg=BG_MID).pack(padx=4)

        H_data = self.result.get("H_alfven", {})
        if H_data:
            vals = {int(k): v for k, v in H_data.items()}
            h_min = min(vals.values()); h_max = max(vals.values())
            h_range = h_max - h_min if h_max > h_min else 1
            m_pred = self.result.get("m_predicted_H", self.m_pred)
            m_obs  = self.result.get("m_observed", 0)
            for m in sorted(vals.keys()):
                h = vals[m]
                # Low H = strong coupling = tall bar (inverted)
                norm = 1.0 - (h - h_min) / h_range
                bar_w = int(norm * 140)
                is_pred = (m == m_pred)
                is_obs  = (m == m_obs and m_obs > 0)
                rf2 = tk.Frame(hf, bg=BG_MID)
                rf2.pack(fill="x", padx=4, pady=1)
                lbl_c = GREEN if is_obs else GOLD if is_pred else DIM
                tk.Label(rf2, text=f"m={m:2d}", font=("Consolas", 8),
                         fg=lbl_c, bg=BG_MID, width=5).pack(side="left")
                bf = tk.Frame(rf2, bg=BG_DARK, height=10, width=155)
                bf.pack(side="left", padx=1)
                bf.pack_propagate(False)
                bc = GREEN if is_obs else GOLD if is_pred else ACCENT
                tk.Frame(bf, bg=bc, height=10,
                         width=max(2, bar_w)).place(x=0, y=0)
                tag = " OBS" if is_obs else " MIN" if is_pred else ""
                if tag:
                    tk.Label(rf2, text=tag, font=("Consolas", 7),
                             fg=bc, bg=BG_MID).pack(side="left")
        else:
            tk.Label(hf, text="Run BCM_stellar_wave.py --batch",
                     font=("Consolas", 9), fg=DIM, bg=BG_MID).pack(padx=4, pady=4)

        # Phase dynamics
        pf = tk.LabelFrame(parent, text="PHASE DYNAMICS",
                           bg=BG_MID, fg=GOLD,
                           font=("Consolas", 10, "bold"))
        pf.pack(fill="x", padx=4, pady=4)
        cdp = self.result.get("cos_delta_phi", 1.0)
        dr  = self.result.get("decoupling_ratio", 0.0)
        regime = ("coupled" if cdp > 0.7
                  else "prime-lock" if cdp > 0.2
                  else "void/anti-phase")
        p_rows = [
            ("cos(dphi)", f"{cdp:.4f}"),
            ("regime",    regime),
            ("decouple",  f"{dr:.4e}"),
            ("note",      "Bessel proxy"),
        ]
        for label, val in p_rows:
            rf3 = tk.Frame(pf, bg=BG_MID)
            rf3.pack(fill="x", padx=4, pady=1)
            tk.Label(rf3, text=f"{label}:", font=("Consolas", 9),
                     fg=DIM, bg=BG_MID, width=9, anchor="w").pack(side="left")
            vc = GREEN if "coupled" in val else GOLD if "prime" in val else DIM
            tk.Label(rf3, text=val, font=("Consolas", 9),
                     fg=vc, bg=BG_MID).pack(side="left")

        # Scale invariance summary
        scf = tk.LabelFrame(parent, text="SCALE INVARIANCE",
                            bg=BG_MID, fg=GOLD,
                            font=("Consolas", 10, "bold"))
        scf.pack(fill="x", padx=4, pady=4)
        si_rows = [
            ("Galactic",  "SMBH",     "lam=0.1",   "--"),
            ("Planetary", "Dynamo",   "lam=0.082", "6"),
            ("Stellar",   "Tachocline","lam=?",    "3/4"),
        ]
        for row in si_rows:
            rf5 = tk.Frame(scf, bg=BG_MID)
            rf5.pack(fill="x", padx=4, pady=1)
            colors = [GOLD, "#c8a84b", GREEN]
            c = colors[si_rows.index(row)]
            for cell, w in zip(row, [9, 10, 8, 4]):
                tk.Label(rf5, text=cell, font=("Consolas", 8),
                         fg=c, bg=BG_MID, width=w, anchor="w").pack(side="left")

    # ── View routing ──

    def _on_view_change(self):
        if self._anim_id:
            self.win.after_cancel(self._anim_id)
            self._anim_id = None
        self._refresh()

    def _on_resize(self, event):
        self._cw = event.width
        self._ch = event.height
        self._refresh()

    def _on_q_change(self):
        self._update_q_info()
        if self.view_var.get() == "tensor":
            self._refresh()

    def _update_q_info(self):
        q = self.q_var.get()
        n_v = 2**q
        n_e = q * 2**(q-1)
        self.q_info.config(text=f"{n_v} verts  {n_e} edges")

    def _on_close(self):
        if self._anim_id:
            self.win.after_cancel(self._anim_id)
        self.win.destroy()

    def _refresh(self):
        view = self.view_var.get()
        self.canvas.delete("all")
        if view == "stars":         self._draw_stars()
        elif view == "alfven":      self._draw_field(self.alfven_field, False,
                                        f"Alfven Coupling Field  m={self.m_pred}  v_A={self.v_A:.0f} m/s",
                                        mode="alfven")
        elif view == "tachocline":  self._draw_field(self.tachocline_field, False,
                                        "Tachocline Interface -- Substrate Gate",
                                        mode="tachocline")
        elif view == "signed":      self._draw_field(self.alfven_field, True,
                                        "Signed Alfven Field -- coupling vs void zones",
                                        mode="signed")
        elif view == "spectrum":    self._draw_spectrum()
        elif view == "scale":       self._draw_scale_table()
        elif view == "tensor":      self._start_tensor_anim()
        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        elif view == "binary":      self._draw_binary()

    # ── Star gallery ──

    def _draw_stars(self):
        W, H = self._cw, self._ch
        star_names = list(STARS.keys())
        n = len(star_names)
        cols = 3
        rows = math.ceil(n / cols)
        cell_w = W // cols
        cell_h = (H - 60) // rows

        self.canvas.create_text(W//2, 18,
            text="BCM STELLAR SUBSTRATE -- Alfven Hamiltonian Scale-Invariance Gallery",
            fill=WHITE, font=("Consolas", 12, "bold"))

        star_data = self._load_all_star_results()
        confirmed = sum(1 for d in star_data.values()
                       if d.get("match_hamiltonian") is True)
        total_known = sum(1 for d in star_data.values()
                         if isinstance(d.get("match_hamiltonian"), bool))
        self.canvas.create_text(W//2, 38,
            text=f"Alfven H(m) confirmed: {confirmed}/{total_known}  |  "
                 f"Same Hamiltonian. Different medium. Same scale invariance.",
            fill=DIM, font=("Consolas", 9))

        for i, name in enumerate(star_names):
            col = i % cols
            row = i // cols
            cx = col * cell_w + cell_w // 2
            cy = row * cell_h + cell_h // 2 + 60
            radius = min(cell_w, cell_h) // 3 - 16

            draw_star(self.canvas, name, cx, cy, radius)

            # Live result badge
            sdata   = star_data.get(name, {})
            match   = sdata.get("match_hamiltonian")
            m_pred  = sdata.get("m_predicted_H", STARS[name].get("m_confirmed", 0))
            m_obs   = sdata.get("m_observed", STARS[name].get("m_confirmed", 0))

            bx, by = cx, cy + radius + 58

            if match is True:
                draw_standing_wave_stellar(self.canvas, cx, cy, radius, m_pred, GREEN)
                self.canvas.create_rectangle(bx-36, by-8, bx+36, by+8,
                    fill="#0a2010", outline=GREEN)
                self.canvas.create_text(bx, by,
                    text=f"m={m_pred}  ALFVEN LOCK",
                    fill=GREEN, font=("Consolas", 7, "bold"))
            elif match is False:
                draw_standing_wave_stellar(self.canvas, cx, cy, radius,
                                           max(1, m_obs), RED)
                self.canvas.create_rectangle(bx-36, by-8, bx+36, by+8,
                    fill="#200a0a", outline=RED)
                self.canvas.create_text(bx, by,
                    text=f"m_pred={m_pred}  m_obs={m_obs}  BOUNDARY",
                    fill=RED, font=("Consolas", 7))
            elif m_obs == 0:
                draw_standing_wave_stellar(self.canvas, cx, cy, radius,
                                           max(1, m_pred), GOLD)
                self.canvas.create_rectangle(bx-36, by-8, bx+36, by+8,
                    fill="#201000", outline=GOLD)
                self.canvas.create_text(bx, by,
                    text=f"m={m_pred}  BCM PREDICTION",
                    fill=GOLD, font=("Consolas", 7, "bold"))
            else:
                self.canvas.create_rectangle(bx-36, by-8, bx+36, by+8,
                    fill="#101010", outline=DIM)
                self.canvas.create_text(bx, by,
                    text="NO DATA",
                    fill=DIM, font=("Consolas", 7))

        self.status_var.set(
            f"{n} stars  |  {confirmed}/{total_known} Alfven confirmed  |  "
            f"BCM Stellar Scale-Invariance  v_A = B / sqrt(mu0*rho)")

    # ── Field view ──

    def _draw_field(self, field, signed, title, mode="alfven"):
        W, H = self._cw, self._ch
        S = min(W, H) - 40
        G = field.shape[0]
        ox = (W - S) // 2
        oy = (H - S) // 2 + 20

        if _PIL:
            img_mode = "signed" if signed else mode
            pil_img = field_to_image_stellar(field, mode=img_mode, size=(S, S))
            self._tk_img_field = ImageTk.PhotoImage(pil_img)
            self.canvas.create_image(ox, oy, anchor="nw",
                                     image=self._tk_img_field)
        else:
            step = max(1, int(G / 180))
            px = S / G
            fmax = np.max(np.abs(field)) or 1.0
            for iy in range(0, G, step):
                for ix in range(0, G, step):
                    v = field[iy, ix] / fmax
                    if signed:
                        if v >= 0:
                            col = f"#{int(v*30):02x}{int(v*80):02x}{int(40+v*215):02x}"
                        else:
                            col = f"#{int(-v*220+30):02x}{int(-v*30):02x}20"
                    else:
                        col = f"#{int(40+v*215):02x}{int(20+v*180):02x}{int(v*80):02x}"
                    x0 = ox + ix*px; y0 = oy + iy*px
                    self.canvas.create_rectangle(x0, y0,
                        x0+px*step+1, y0+px*step+1,
                        fill=col, outline="")

        cx = ox + S//2; cy = oy + S//2
        r_hex = S * 0.42

        # Tachocline ring overlay
        conv_depths = {
            "Sun": 0.287, "Tabby": 0.15, "Proxima": 1.0,
            "EV_Lac": 0.9, "HR_1099": 0.35
        }
        cd = conv_depths.get(self.star_name, 0.287)
        r_tach = r_hex * (1.0 - cd)
        if r_tach > 10:
            self.canvas.create_oval(cx-r_tach, cy-r_tach,
                                    cx+r_tach, cy+r_tach,
                                    outline=GOLD, dash=(6,4), width=2)
            self.canvas.create_text(cx + r_tach + 5, cy,
                                    text="tachocline", fill=GOLD,
                                    font=("Consolas", 8), anchor="w")

        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        # Alfven resonance lines — where H(m) = 0 for each mode
        # r_resonance(m) = v_A * m / omega_r  (normalized to field view)
        # Bright ring = predicted mode, dim rings = other modes
        if self.omega_r > 0 and self.v_A > 0:
            for m in range(1, 7):
                r_res_norm = (self.v_A * m) / self.omega_r
                r_res_px = int(r_res_norm * r_hex)
                if 8 < r_res_px < r_hex * 1.3:
                    is_pred = (m == self.m_pred)
                    is_tidal = (m == self.m_tidal and self.v_tidal > 0)
                    if is_pred:
                        color = GREEN
                        width = 2
                        dash = ()
                    elif is_tidal:
                        color = RED
                        width = 2
                        dash = (4, 3)
                    else:
                        color = DIM
                        width = 1
                        dash = (2, 6)
                    self.canvas.create_oval(
                        cx - r_res_px, cy - r_res_px,
                        cx + r_res_px, cy + r_res_px,
                        outline=color, dash=dash, width=width)
                    label_y = cy - r_res_px - 6
                    if label_y > cy - r_hex - 30:
                        tag = f"m={m}" + (" ★" if is_pred else "")
                        tag += (" TIDAL" if is_tidal else "")
                        self.canvas.create_text(
                            cx + 8, label_y, text=tag,
                            fill=color, font=("Consolas", 7),
                            anchor="w")

            # Standing wave node lines for predicted mode
            m_draw = max(1, self.m_pred)
            for i in range(m_draw):
                angle_rad = math.radians(360 * i / m_draw - 90)
                x0 = cx
                y0 = cy
                x1 = cx + int(r_hex * 0.95 * math.cos(angle_rad))
                y1 = cy + int(r_hex * 0.95 * math.sin(angle_rad))
                self.canvas.create_line(x0, y0, x1, y1,
                    fill=GREEN, width=1, dash=(3, 6))

            # Alfven speed annotation
            v_tidal_txt = f"  v_tid={self.v_tidal:.0f}" if self.v_tidal > 0 else ""
            self.canvas.create_text(
                ox + 8, oy + S - 8,
                text=f"v_A={self.v_A:.0f} m/s  ΩR={self.omega_r:.0f}{v_tidal_txt}",
                fill=ACCENT, font=("Consolas", 8), anchor="sw")
        # === END ADDITION ===

        # Outer boundary
        self.canvas.create_oval(cx-r_hex, cy-r_hex,
                                cx+r_hex, cy+r_hex,
                                outline=DIM, dash=(3,6))

        # Center dot
        self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5,
                                fill=STELLAR_HOT, outline="")

        self.canvas.create_text(W//2, oy-14, text=title,
                                fill=WHITE, font=("Consolas", 11, "bold"))
        self.status_var.set(f"Star: {self.star_name}  m={self.m_pred}  v_A={self.v_A:.0f} m/s")

    # ── H(m) Spectrum ──

    def _draw_spectrum(self):
        W, H = self._cw, self._ch
        H_data = self.result.get("H_alfven", {})

        if not H_data:
            # Generate from defaults if no JSON loaded
            m_range = range(1, 13)
            omega_r = self.omega_r
            v_A = self.v_A
            H_data = {str(m): (v_A - omega_r/m)**2 for m in m_range}

        vals = {int(k): v for k, v in H_data.items()}
        h_min = min(vals.values()); h_max = max(vals.values())
        h_range = h_max - h_min if h_max > h_min else 1

        m_pred = self.result.get("m_predicted_H", self.m_pred)
        m_obs  = self.result.get("m_observed", 0)

        ml, mr, mt, mb = 80, 40, 70, 80
        pw = W - ml - mr; ph = H - mt - mb
        n = len(vals); bw = pw // n - 4

        self.canvas.create_rectangle(ml, mt, W-mr, H-mb,
                                     outline=DIM, fill=BG_MID)
        self.canvas.create_text(W//2, mt-40,
            text=f"Alfven Hamiltonian H(m) = (v_A - OmegaR/m)^2  --  {self.star_name}",
            fill=WHITE, font=("Consolas", 11, "bold"))
        self.canvas.create_text(W//2, mt-22,
            text=f"v_A = {self.v_A:.1f} m/s  |  m* = argmin H(m)  |  minimum = predicted mode",
            fill=DIM, font=("Consolas", 9))
        self.canvas.create_text(W//2, H-18,
            text="m  (Alfven Hamiltonian minimum = predicted tachocline standing wave)",
            fill=DIM, font=("Consolas", 9))

        for idx, m in enumerate(sorted(vals.keys())):
            h = vals[m]
            # Invert: low H = strong coupling = tall bar
            norm = 1.0 - (h - h_min) / h_range
            bh = int(norm * ph * 0.85) + 4
            x0 = ml + idx*(bw+4) + 2; x1 = x0 + bw
            y1 = H - mb; y0 = y1 - bh
            is_pred = (m == m_pred)
            is_obs  = (m == m_obs and m_obs > 0)
            color = GREEN if is_obs else GOLD if is_pred else ACCENT
            self.canvas.create_rectangle(x0, y0, x1, y1,
                                         fill=color, outline="")
            self.canvas.create_text((x0+x1)//2, y1+14,
                                    text=str(m), fill=WHITE,
                                    font=("Consolas", 9))
            if is_obs:
                self.canvas.create_text((x0+x1)//2, y0-14,
                    text="OBS", fill=GREEN, font=("Consolas", 8, "bold"))
            elif is_pred:
                self.canvas.create_text((x0+x1)//2, y0-14,
                    text="MIN", fill=GOLD, font=("Consolas", 8, "bold"))

        # H=0 resonance line
        y_zero = H - mb - int((1.0 - (0 - h_min)/h_range) * ph * 0.85) - 4
        self.canvas.create_line(ml, y_zero, W-mr, y_zero,
                                fill=GREEN, dash=(4,4), width=1)
        self.canvas.create_text(W-mr-4, y_zero-8,
            text="H=0\nresonance", fill=GREEN,
            font=("Consolas", 7), anchor="e")

        self.status_var.set(
            f"H(m) spectrum -- {self.star_name}  "
            f"m_predicted={m_pred}  m_observed={m_obs if m_obs > 0 else '?'}")

    # ── Scale Table ──

    def _draw_scale_table(self):
        W, H = self._cw, self._ch
        self.canvas.create_text(W//2, 30,
            text="BCM SUBSTRATE SCALE INVARIANCE -- STELLAR EXTENSION",
            fill=WHITE, font=("Consolas", 15, "bold"))
        self.canvas.create_text(W//2, 56,
            text="Same Hamiltonian. Different medium. Different phase speed.",
            fill=DIM, font=("Consolas", 11))

        headers = ["Scale", "Pump", "Phase Speed", "Hamiltonian", "Match"]
        col_x = [60, 200, 370, 580, 820]
        y_h = 100
        for h, x in zip(headers, col_x):
            self.canvas.create_text(x, y_h, text=h, fill=GOLD,
                font=("Consolas", 11, "bold"), anchor="w")
        self.canvas.create_line(50, y_h+18, W-40, y_h+18, fill=DIM)

        rows = [
            ("Galactic",  "SMBH neutrino",    "c_wave = 1.0",
             "H(m) = (c_s - OmegaR/m)^2",   "122/175 galaxies"),
            ("Planetary", "Metallic H dynamo", "c_s acoustic",
             "H(m) = (c_s - OmegaR/m)^2",   "6/8 planets"),
            ("Stellar",   "Tachocline B field","v_A Alfven",
             "H(m) = (v_A - OmegaR/m)^2",   "3/4 single stars"),
            ("Binary?",   "Tidal forcing",     "v_tidal?",
             "H(m) = (v_A+v_tid - OmegaR/m)^2","HR_1099 pending"),
            ("Lab?",      "Galinstan Taylor-C","v_A liquid metal",
             "H(m) = (v_A - OmegaR/m)^2",   "$225 experiment"),
        ]
        row_colors = [GREEN, "#c8a84b", ACCENT, GOLD, DIM]
        y = y_h + 38
        for row, color in zip(rows, row_colors):
            for val, x in zip(row, col_x):
                self.canvas.create_text(x, y, text=val, fill=color,
                    font=("Consolas", 9), anchor="w")
            self.canvas.create_line(50, y+18, W-40, y+18, fill="#1a2030")
            y += 38

        y += 30
        self.canvas.create_text(W//2, y,
            text="IF  v_A_stellar / (OmegaR/m) ~ 1.0  ACROSS ALL STARS",
            fill=WHITE, font=("Consolas", 13, "bold"))
        y += 34
        self.canvas.create_text(W//2, y,
            text="BCM Alfven Hamiltonian is the universal substrate gate equation",
            fill=GREEN, font=("Consolas", 13, "bold"))
        y += 30
        self.canvas.create_text(W//2, y,
            text="Galactic -> Planetary -> Stellar -> Lab  |  12 orders of magnitude",
            fill=ACCENT, font=("Consolas", 11))
        y += 40
        self.canvas.create_text(W//2, y,
            text="v6 status: Sun m=4 confirmed  Proxima m=1 confirmed  EV Lac m=2 confirmed  |  HR_1099 = stellar Class VI boundary",
            fill=GOLD, font=("Consolas", 10))

        self.status_var.set("Scale invariance -- galactic -> planetary -> stellar")

    # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
    # Binary Bridge View — dual-pump substrate field visualization

    def _draw_binary(self):
        """Draw binary substrate bridge: two pumps, coupling field, vectors."""
        W, H = self._cw, self._ch

        if not self.binary_data:
            self.canvas.create_text(W//2, H//2,
                text="No binary data loaded.\n"
                     "Run Binary Substrate Bridge from launcher first.",
                fill=GOLD, font=("Consolas", 12))
            return

        info = self.binary_data.get('info', {})
        cpf = self.binary_data.get('cpf')
        dpf = self.binary_data.get('dpf')
        J = self.binary_data.get('J')
        grid = info.get('grid', 64)

        # ── Header ──
        pair_label = f"{info.get('star_A', '?')} + {info.get('star_B', '?')}"
        bcm_class = info.get('bcm_class', '')
        self.canvas.create_text(W//2, 22,
            text=f"BCM BINARY SUBSTRATE BRIDGE — {pair_label}",
            fill=WHITE, font=("Consolas", 14, "bold"))
        self.canvas.create_text(W//2, 44,
            text=f"{bcm_class}  |  sep={info.get('sep_AU', 0):.1f} AU  "
                 f"e={info.get('eccentricity', 0):.3f}  "
                 f"phase={info.get('orbital_phase', 0):.2f}",
            fill=DIM, font=("Consolas", 10))

        # ── Layout: field fills left 70%, diagnostics on far right ──
        diag_width = 260
        field_size = min(W - diag_width - 50, H - 100)
        if field_size < 200:
            field_size = min(W, H) - 40
        ox = 20
        oy = 70

        # ── Render coupling field as PIL image ──
        if cpf is not None and _PIL:
            from PIL import Image, ImageTk
            f = cpf.astype(float)
            fmax = np.max(np.abs(f))
            if fmax > 0:
                f = f / fmax
            gh, gw = f.shape
            img = np.zeros((gh, gw, 3), dtype=np.uint8)
            # Emerald palette: dark red -> gold -> green -> white
            img[..., 0] = np.clip(40 + f * 60, 0, 255).astype(np.uint8)
            img[..., 1] = np.clip(20 + f * 235, 0, 255).astype(np.uint8)
            img[..., 2] = np.clip(f * 80, 0, 255).astype(np.uint8)
            pil_img = Image.fromarray(img, mode="RGB")
            pil_img = pil_img.resize((field_size, field_size), Image.NEAREST)
            self._tk_binary_img = ImageTk.PhotoImage(pil_img)
            self.canvas.create_image(ox, oy, anchor="nw",
                                     image=self._tk_binary_img)
        elif cpf is not None:
            # Fallback: draw rectangles
            step = max(1, grid // 60)
            px = field_size / grid
            fmax = np.max(np.abs(cpf)) or 1.0
            for iy in range(0, grid, step):
                for ix in range(0, grid, step):
                    v = cpf[iy, ix] / fmax
                    g = int(min(255, 20 + v * 235))
                    col = f"#28{g:02x}28"
                    x0 = ox + ix * px
                    y0 = oy + iy * px
                    self.canvas.create_rectangle(
                        x0, y0, x0 + px*step + 1, y0 + px*step + 1,
                        fill=col, outline="")

        scale = field_size / grid

        # ── Gradient vectors ──
        if dpf is not None:
            grad_y, grad_x = np.gradient(dpf)
            mag = np.sqrt(grad_x**2 + grad_y**2)
            mag_max = np.max(mag) if np.max(mag) > 0 else 1.0
            vstep = max(1, grid // 16)
            for iy in range(vstep, grid - vstep, vstep):
                for ix in range(vstep, grid - vstep, vstep):
                    gx = grad_x[iy, ix]
                    gy = grad_y[iy, ix]
                    m = mag[iy, ix]
                    if m < mag_max * 0.05:
                        continue
                    x0 = ox + ix * scale
                    y0 = oy + iy * scale
                    arrow_len = min(scale * vstep * 0.8,
                                    m / mag_max * scale * vstep)
                    if m > 0:
                        dx = gx / m * arrow_len
                        dy = gy / m * arrow_len
                    else:
                        dx = dy = 0
                    brightness = min(255, int(80 + m / mag_max * 175))
                    col = f"#{brightness:02x}{brightness//2:02x}20"
                    self.canvas.create_line(
                        x0, y0, x0 + dx, y0 + dy,
                        fill=col, width=1, arrow="last",
                        arrowshape=(4, 6, 2))

        # ── Star markers ──
        pump_A = info.get('pump_A', (grid//4, grid//2))
        pump_B = info.get('pump_B', (3*grid//4, grid//2))
        l1 = info.get('L1', (grid//2, grid//2))

        def _star_marker(px, py, name, amp, color):
            sx = ox + px * scale
            sy = oy + py * scale
            r = max(12, int(amp * 2.5))
            # Corona glow
            for ri in range(r + 10, r - 1, -2):
                alpha = max(0, 1.0 - (ri - r) / 12.0)
                gc = int(alpha * 60)
                gcol = f"#{gc:02x}{gc:02x}10"
                self.canvas.create_oval(sx-ri, sy-ri, sx+ri, sy+ri,
                                        outline=gcol, fill="")
            # Star body
            self.canvas.create_oval(sx-r, sy-r, sx+r, sy+r,
                                    fill=color, outline=WHITE, width=1)
            # Label
            self.canvas.create_text(sx, sy + r + 14, text=name,
                fill=WHITE, font=("Consolas", 9, "bold"))
            self.canvas.create_text(sx, sy + r + 26,
                text=f"amp={amp:.1f}",
                fill=DIM, font=("Consolas", 7))

        _star_marker(pump_A[0], pump_A[1],
                     info.get('star_A', 'A'), info.get('amp_A', 8),
                     STELLAR_HOT)
        _star_marker(pump_B[0], pump_B[1],
                     info.get('star_B', 'B'), info.get('amp_B', 4),
                     STELLAR_COOL)

        # ── L1 marker ──
        l1x = ox + l1[0] * scale
        l1y = oy + l1[1] * scale
        self.canvas.create_polygon(
            l1x, l1y - 10, l1x + 8, l1y, l1x, l1y + 10, l1x - 8, l1y,
            fill=GOLD, outline=WHITE, width=1)
        self.canvas.create_text(l1x, l1y - 16, text="L1",
            fill=GOLD, font=("Consolas", 10, "bold"))

        # ── Bridge line ──
        ax = ox + pump_A[0] * scale
        ay = oy + pump_A[1] * scale
        bx = ox + pump_B[0] * scale
        by = oy + pump_B[1] * scale
        self.canvas.create_line(ax, ay, bx, by,
            fill=ACCENT, width=1, dash=(4, 8))

        # ── Diagnostics panel (right-aligned) ──
        dx = W - diag_width
        dy = oy
        diag_items = [
            ("BRIDGE DIAGNOSTICS", GOLD, ("Consolas", 11, "bold")),
            ("", None, None),
            (f"Star A: {info.get('star_A', '?')}", WHITE, ("Consolas", 9)),
            (f"  amp = {info.get('amp_A', 0):.1f}", DIM, ("Consolas", 9)),
            (f"Star B: {info.get('star_B', '?')}", WHITE, ("Consolas", 9)),
            (f"  amp = {info.get('amp_B', 0):.1f}", DIM, ("Consolas", 9)),
            ("", None, None),
            (f"Separation: {info.get('sep_AU', 0):.1f} AU", ACCENT,
             ("Consolas", 9)),
            (f"Eccentricity: {info.get('eccentricity', 0):.3f}", ACCENT,
             ("Consolas", 9)),
            (f"Orbital phase: {info.get('orbital_phase', 0):.2f}", ACCENT,
             ("Consolas", 9)),
            (f"Synchronized: {'YES' if info.get('synchronized') else 'NO'}",
             GREEN if info.get('synchronized') else GOLD, ("Consolas", 9)),
            ("", None, None),
            ("L1 COUPLING:", GOLD, ("Consolas", 10, "bold")),
            (f"  cos(Δφ) = {info.get('L1_cos_mean', 0):+.6f}",
             GREEN if info.get('L1_cos_mean', 0) > 0.99 else GOLD,
             ("Consolas", 9)),
            (f"  std     = {info.get('L1_cos_std', 0):.6f}", DIM,
             ("Consolas", 9)),
            (f"  curl    = {info.get('L1_curl_max', 0):.2e}", DIM,
             ("Consolas", 9)),
            ("", None, None),
        ]

        # Verdict
        cos_l1 = info.get('L1_cos_mean', 0)
        curl_l1 = info.get('L1_curl_max', 0)
        if cos_l1 > 0.99:
            verdict = "COHERENT BRIDGE"
            v_color = GREEN
        elif cos_l1 > 0.9:
            verdict = "PARTIAL BRIDGE"
            v_color = GOLD
        else:
            verdict = "DECOHERENT"
            v_color = RED
        diag_items.append((f">>> {verdict}", v_color,
                           ("Consolas", 11, "bold")))

        if curl_l1 > 0.001:
            diag_items.append((">>> SUBSTRATE POOLING", RED,
                               ("Consolas", 10, "bold")))
        else:
            diag_items.append((">>> Laminar (no vorticity)", DIM,
                               ("Consolas", 9)))

        for text, color, font in diag_items:
            if text == "":
                dy += 6
                continue
            self.canvas.create_text(dx, dy, text=text,
                fill=color, font=font, anchor="nw")
            dy += 16

        # ── Footer ──
        self.canvas.create_text(W//2, H - 12,
            text="BCM v7 Binary Substrate Bridge — "
                 "Emerald Entities LLC — GIBUSH Systems — 2026",
            fill=DIM, font=("Consolas", 8))

        self.status_var.set(
            f"Binary: {pair_label}  L1 cos={cos_l1:+.4f}  "
            f"sep={info.get('sep_AU', 0):.1f} AU  {verdict}")
    # === END ADDITION ===

    # ── Tensor Hypercube (same as planetary renderer) ──

    def _start_tensor_anim(self):
        self._draw_tensor()
        self._anim_id = self.win.after(50, self._anim_tensor)

    def _anim_tensor(self):
        if self.view_var.get() != "tensor":
            return
        self._angle += 0.018
        self._draw_tensor()
        self._anim_id = self.win.after(50, self._anim_tensor)

    def _draw_tensor(self):
        W, H = self._cw, self._ch
        self.canvas.delete("all")
        q = self.q_var.get()
        n_v = 2**q; n_e = q * 2**(q-1)

        self.canvas.create_text(W//2, 22,
            text=f"TENSOR Q={q} HYPERCUBE -- Stellar Substrate Impedance Projection",
            fill=WHITE, font=("Consolas", 11, "bold"))
        self.canvas.create_text(W//2, 42,
            text=f"{q}D -> 2D  |  {n_v} vertices  {n_e} edges  |  Z_ij = v_A*delta_ij + chi*epsilon_ij",
            fill=DIM, font=("Consolas", 9))

        cx, cy = W//2, H//2 + 20
        scale = min(W, H) * 0.28

        verts_nd, edges = generate_hypercube_vertices(q)
        proj = project_hypercube(verts_nd, q, self._angle, cx, cy, scale)

        depths = [p[2] for p in proj]
        d_min = min(depths); d_max = max(depths)
        d_range = d_max - d_min if d_max > d_min else 1.0

        for i, j in edges:
            x0,y0,d0 = proj[i]; x1,y1,d1 = proj[j]
            depth_avg = ((d0+d1)/2 - d_min) / d_range
            diff_dim = next(d for d in range(q)
                           if verts_nd[i][d] != verts_nd[j][d])
            dim_colors = [ACCENT, GOLD, GREEN, RED, "#cc88ff", "#ff8844", "#44ffcc"]
            color = dim_colors[diff_dim % len(dim_colors)]
            alpha = int(80 + depth_avg * 175)
            r_c = int(int(color[1:3],16) * alpha/255)
            g_c = int(int(color[3:5],16) * alpha/255)
            b_c = int(int(color[5:7],16) * alpha/255)
            edge_color = f"#{r_c:02x}{g_c:02x}{b_c:02x}"
            width = max(1, int(1 + depth_avg * 2))
            self.canvas.create_line(x0,y0,x1,y1, fill=edge_color, width=width)

        for i, (x,y,depth) in enumerate(proj):
            depth_norm = (depth - d_min) / d_range
            r_v = int(3 + depth_norm * 5)
            v_color = GOLD if depth_norm > 0.8 else ACCENT if depth_norm > 0.4 else DIM
            self.canvas.create_oval(x-r_v,y-r_v,x+r_v,y+r_v,
                                     fill=v_color, outline="")

        dim_names = ["v_A (Alfven)", "OmegaR/m", "rho_tach", "B_tach",
                     "sigma", "v_conv", "J_ind"]
        dim_colors = [ACCENT, GOLD, GREEN, RED, "#cc88ff", "#ff8844", "#44ffcc"]
        for d in range(min(q, 4)):
            lx = 60; ly = H - 80 + d*18
            self.canvas.create_line(lx, ly, lx+20, ly,
                fill=dim_colors[d], width=2)
            self.canvas.create_text(lx+26, ly,
                text=dim_names[d] if d < len(dim_names) else f"v{d+1}",
                fill=dim_colors[d], font=("Consolas", 9), anchor="w")

        self.canvas.create_text(W//2, H-18,
            text="Each axis = one component of the stellar substrate impedance tensor",
            fill=DIM, font=("Consolas", 9))
        self.status_var.set(
            f"Tensor Q={q}  {n_v} vertices  {n_e} edges  "
            f"theta={math.degrees(self._angle):.1f} deg")


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BCM Stellar Renderer")
    parser.add_argument("--star", type=str, default=None,
                        help=f"Star name. Options: {list(STARS.keys())}")
    parser.add_argument("--json", type=str, default=None,
                        help="Path to stellar wave JSON result")
    args = parser.parse_args()

    json_path = args.json
    star_name = args.star or "Sun"

    if json_path is None:
        base = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(base, "data", "results")
        # Try last_run pointer
        last_run = os.path.join(results_dir, "BCM_stellar_last_run.json")
        if os.path.exists(last_run):
            try:
                with open(last_run, encoding="utf-8") as f:
                    lr = json.load(f)
                candidate = os.path.join(results_dir, lr.get("last_file", ""))
                if os.path.exists(candidate):
                    json_path = candidate
                    star_name = lr.get("last_star", star_name)
            except Exception:
                pass
        # Try star-specific file
        if json_path is None:
            candidate = os.path.join(results_dir,
                                     f"BCM_{star_name}_stellar_wave.json")
            if os.path.exists(candidate):
                json_path = candidate

    root = tk.Tk()
    root.withdraw()
    app = StellarRenderer(root, json_path=json_path, star_name=star_name)
    app.win.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
