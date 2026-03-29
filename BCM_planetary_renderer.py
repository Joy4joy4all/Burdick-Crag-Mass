"""
BCM Planetary Renderer
======================
Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC
NSF I-Corps — Team GIBUSH

Standalone visualization for the Saturn substrate wave solver.
Companion to BCM_planetary_wave.py and the Planetary tab in launcher.py.

Shows:
  - Hexagonal standing wave field (2D polar projection)
  - Bessel eigenmode energy spectrum
  - Induction source field J_ind
  - Storm decay curve (Geometric Deviation Registry)
  - Scale invariance comparison table
  - Procedural planet renders (Saturn, Jupiter, Uranus, Neptune, Earth)
  - Tensor Q spinbox — 3D/4D hypercube substrate projection

Usage:
    python BCM_planetary_renderer.py
    python BCM_planetary_renderer.py --json data/results/BCM_Saturn_planetary_wave.json

Called from launcher Planetary tab:
    from BCM_planetary_renderer import PlanetaryRenderer
    PlanetaryRenderer(parent_root, result_json_path)
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import json
import os
import sys
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
# COLOR PALETTE
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
SATURN_GOLD = "#c8a84b"


# ─────────────────────────────────────────
# PLANET DEFINITIONS
# Each planet: color bands, ring params, features
# ─────────────────────────────────────────

PLANETS = {
    "Mercury": {
        "bands":  ["#8c7853","#9e8a61","#7a6645","#b0a080"],
        "rings":  False, "hex": False, "storms": [],
        "substrate_class": "BCM PREDICTION -- m=1 BepiColombo target",
    },
    "Venus": {
        "bands":  ["#e8c87a","#d4a840","#f0d870","#c8922a","#e0b850"],
        "rings":  False, "hex": False, "storms": [],
        "substrate_class": "NULL -- No dynamo",
    },
    "Earth": {
        "bands":  ["#1a5296","#2874c8","#1a5296","#3a8fdc","#1a5296"],
        "rings":  False, "hex": False,
        "storms": [{"lat": 0.18, "lon": 0.55, "r": 0.055,
                    "color": "#a0c8e8", "label": ""}],
        "substrate_class": "CONFIRMED -- m=1 Dipole lock",
    },
    "Mars": {
        "bands":  ["#b54010","#9a3008","#cc5520","#e06030","#8a2808"],
        "rings":  False, "hex": False, "storms": [],
        "substrate_class": "NULL -- Dead dynamo",
    },
    "Jupiter": {
        "bands":  ["#c87840","#e8c080","#a05828","#d4a060","#f0d898","#b86840","#c87040"],
        "rings":  False, "hex": False,
        "storms": [{"lat": 0.22, "lon": 0.58, "r": 0.09,
                    "color": "#c04030", "label": "GRS"}],
        "substrate_class": "CONFIRMED -- m=1 Strong pump",
    },
    "Saturn": {
        "bands":  ["#c8a84b","#b8924a","#d4b870","#a07838","#c4a060","#dcc070"],
        "rings":  True,
        "ring_color": "#b8a060",
        "ring_inner": 1.28,
        "ring_outer": 2.1,
        "hex":    True,
        "hex_color": "#ffee88",
        "storms": [],
        "substrate_class": "CONFIRMED -- m=6 Hexagonal lock",
    },
    "Uranus": {
        "bands":  ["#7de8e8","#60d0d8","#88f0f0","#50c8d0","#70e0e8"],
        "rings":  True,
        "ring_color": "#3a7878",
        "ring_inner": 1.18,
        "ring_outer": 1.5,
        "hex":    False, "storms": [],
        "substrate_class": "CONFIRMED -- m=2 Ice giant",
    },
    "Neptune": {
        "bands":  ["#2050c0","#1840a8","#3068d8","#1030a0","#4080e0"],
        "rings":  True,
        "ring_color": "#182858",
        "ring_inner": 1.20,
        "ring_outer": 1.42,
        "hex":    False,
        "storms": [{"lat": 0.28, "lon": 0.48, "r": 0.08,
                    "color": "#0820a0", "label": "GDS"}],
        "substrate_class": "CONFIRMED -- m=2 Ice giant",
    },
}


# ─────────────────────────────────────────
# PLANET CANVAS DRAWING
# ─────────────────────────────────────────

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _lerp_color(c0, c1, a):
    """Linear interpolate between two RGB tuples."""
    return (
        int(c0[0]*(1-a) + c1[0]*a),
        int(c0[1]*(1-a) + c1[1]*a),
        int(c0[2]*(1-a) + c1[2]*a),
    )


def draw_planet(canvas, planet_name, cx, cy, radius):
    """
    Scanline sphere renderer with:
    - True per-pixel spherical lighting (not cylindrical)
    - Smooth band blending (no hard stripes)
    - Limb darkening
    - Circle-clipped scanlines (no rectangle bleed)

    Chunk width = 4px for balance of quality vs speed.
    """
    cfg   = PLANETS.get(planet_name, PLANETS["Saturn"])
    bands = cfg["bands"]
    n     = len(bands)
    r     = int(radius)
    if r < 4:
        return
    cx = int(cx); cy = int(cy)

    # Light direction: top-left, slightly toward viewer
    LX, LY, LZ = -0.40, -0.30, 0.85
    ln = math.sqrt(LX*LX + LY*LY + LZ*LZ)
    LX /= ln; LY /= ln; LZ /= ln

    # Pixel chunk width — 4px balances quality vs speed
    CHUNK = max(2, r // 40)

    # ── Rings back half ──
    if cfg.get("rings"):
        rc = cfg.get("ring_color", "#888844")
        ri = radius * cfg.get("ring_inner", 1.3)
        ro = radius * cfg.get("ring_outer", 2.0)
        for r_ring in np.linspace(ri, ro, 14):
            ry = r_ring * 0.26
            canvas.create_arc(
                cx-r_ring, cy-ry, cx+r_ring, cy+ry,
                start=0, extent=180,
                outline=rc, fill="", width=2, style="arc")

    # ── Scanline rendering ──
    for dy in range(-r, r+1, CHUNK):
        x_chord = int(math.sqrt(max(0.0, float(r*r - dy*dy))))
        if x_chord < 1:
            continue

        # Y fraction for band selection
        t = (dy + r) / (2.0 * r)
        t_scaled = t * (n - 1)
        i0 = int(t_scaled)
        i1 = min(i0 + 1, n - 1)
        blend = t_scaled - i0
        rgb0 = _hex_to_rgb(bands[i0])
        rgb1 = _hex_to_rgb(bands[i1])
        band_rgb = _lerp_color(rgb0, rgb1, blend)

        # Per-chunk lighting across the scanline
        dx_step = max(1, CHUNK)
        for dx in range(-x_chord, x_chord + 1, dx_step):
            nx = dx / float(r)
            ny = dy / float(r)
            nz2 = 1.0 - nx*nx - ny*ny
            if nz2 < 0:
                continue
            nz = math.sqrt(nz2)

            # Diffuse lighting
            diffuse = max(0.0, nx*LX + ny*LY + nz*LZ)
            # Limb darkening — nz falls to 0 at edges
            limb = nz ** 0.5
            # Combined brightness
            brightness = max(0.12, 0.30 + 0.50*diffuse + 0.20*limb)

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

    # ── Storms ──
    for storm in cfg.get("storms", []):
        sx = cx + (storm["lon"] - 0.5) * 2 * r * 0.72
        sy = cy + (storm["lat"] - 0.5) * 2 * r * 0.72
        sr = storm["r"] * r
        canvas.create_oval(sx-sr, sy-sr, sx+sr, sy+sr,
                            fill=storm["color"], outline="")
        if storm.get("label"):
            canvas.create_text(sx, sy, text=storm["label"],
                                fill=WHITE, font=("Consolas", 7, "bold"))

    # ── Saturn north-pole hexagon ──
    if cfg.get("hex"):
        hc  = cfg.get("hex_color", GOLD)
        r_h = r * 0.36
        pts = []
        for i in range(6):
            a = math.radians(60*i - 30)
            pts.append(cx + r_h * math.cos(a))
            pts.append(cy - r*0.52 + r_h*0.32*math.sin(a))
        canvas.create_polygon(*pts, outline=hc, fill="", width=2, dash=(4, 2))

    # ── Rings front half ──
    if cfg.get("rings"):
        rc = cfg.get("ring_color", "#888844")
        ri = radius * cfg.get("ring_inner", 1.3)
        ro = radius * cfg.get("ring_outer", 2.0)
        for r_ring in np.linspace(ri, ro, 14):
            ry = r_ring * 0.26
            canvas.create_arc(
                cx-r_ring, cy-ry, cx+r_ring, cy+ry,
                start=180, extent=180,
                outline=rc, fill="", width=2, style="arc")

    # ── Labels ──
    canvas.create_text(cx, cy + r + 14, text=planet_name,
                        fill=WHITE, font=("Consolas", 10, "bold"))
    sub = cfg.get("substrate_class", "")
    lc  = GREEN if "CONFIRMED" in sub else GOLD if "PREDICT" in sub else DIM
    canvas.create_text(cx, cy + r + 27, text=sub,
                        fill=lc, font=("Consolas", 7))



def field_to_image_planet(field, mode="energy", size=None):
    """Fast PIL-based field renderer for planetary views."""
    f = field.astype(float)
    fmin = f.min(); fmax = f.max()
    frange = fmax - fmin
    if frange > 0:
        f = (f - fmin) / frange
    else:
        f = np.zeros_like(f)
    H, W = f.shape
    img = np.zeros((H, W, 3), dtype=np.uint8)
    if mode in ("energy", "hexfield", "induction"):
        # Deep blue -> electric blue -> white core
        img[..., 2] = np.clip(60 + f*195, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(f*80, 0, 255).astype(np.uint8)
        img[..., 0] = np.clip(f*30, 0, 255).astype(np.uint8)
    elif mode == "signed":
        # Diverging: red=positive, blue=negative
        raw = (field / (abs(field).max() + 1e-9))
        pos = np.clip(raw, 0, 1); neg = np.clip(-raw, 0, 1)
        img[..., 0] = np.clip(pos*220+30, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(pos*60+neg*60, 0, 255).astype(np.uint8)
        img[..., 2] = np.clip(neg*220+30, 0, 255).astype(np.uint8)
    elif mode == "sphere":
        # Warm gold-white for planetary sphere
        img[..., 0] = np.clip(80 + f*175, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(60 + f*160, 0, 255).astype(np.uint8)
        img[..., 2] = np.clip(20 + f*100, 0, 255).astype(np.uint8)
    else:
        img[..., 2] = np.clip(60 + f*195, 0, 255).astype(np.uint8)
        img[..., 1] = np.clip(f*80, 0, 255).astype(np.uint8)
        img[..., 0] = np.clip(f*30, 0, 255).astype(np.uint8)
    pil_img = Image.fromarray(img, mode="RGB")
    if size:
        pil_img = pil_img.resize(size, Image.NEAREST)
    return pil_img


def spherical_shading_planet(field, m=6, light_dir=(0.4, -0.3, 0.85)):
    """
    Apply spherical shading to planetary substrate field.
    Adds depth lighting and limb darkening.
    Standing wave geometry visible as raised surface features.
    """
    G = field.shape[0]
    y_arr, x_arr = np.mgrid[0:G, 0:G]
    cx = cy = G // 2
    dx = (x_arr - cx) / (cx + 1e-6)
    dy = (y_arr - cy) / (cy + 1e-6)
    r2 = dx**2 + dy**2
    on_sphere = r2 <= 1.0
    z_sphere = np.sqrt(np.clip(1 - r2, 0, 1))
    # Surface normal from field height map
    f_norm = field / (np.max(np.abs(field)) + 1e-9)
    gy_h, gx_h = np.gradient(f_norm)
    nx = -gx_h * 2.0; ny = -gy_h * 2.0
    nz = np.ones_like(f_norm)
    n_len = np.sqrt(nx**2 + ny**2 + nz**2) + 1e-9
    nx /= n_len; ny /= n_len; nz /= n_len
    # Lighting
    lx, ly, lz = light_dir
    ln = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx /= ln; ly /= ln; lz /= ln
    diffuse = np.clip(nx*lx + ny*ly + nz*lz, 0, 1)
    limb = np.clip(z_sphere, 0, 1) ** 0.4
    intensity = 0.45*np.clip(f_norm, 0, 1) + 0.40*diffuse + 0.15*limb
    intensity[~on_sphere] = 0.0
    return intensity


def generate_hexagonal_field(grid=256, m=6, k_scale=1.0):
    cx = cy = grid // 2
    x = np.arange(grid) - cx
    y = np.arange(grid) - cy
    X, Y = np.meshgrid(x, y)
    r = np.sqrt(X**2 + Y**2)
    theta = np.arctan2(Y, X)
    r_max = grid // 2
    r_norm = r / r_max
    k = k_scale * 2.5
    if _SCIPY:
        J = jv(m, k * r_norm * r_max / (grid * 0.1))
    else:
        J = np.cos(k * r_norm * np.pi) * np.exp(-r_norm * 0.5)
    azimuthal = np.cos(m * theta)
    field = J * azimuthal
    mask = r <= r_max * 0.95
    field[~mask] = 0.0
    fmax = np.max(np.abs(field))
    if fmax > 0:
        field /= fmax
    return field


def generate_induction_field(grid=256):
    cx = cy = grid // 2
    x = np.arange(grid) - cx
    y = np.arange(grid) - cy
    X, Y = np.meshgrid(x, y)
    r = np.sqrt(X**2 + Y**2)
    r_norm = r / (grid // 2)
    r_dynamo = 0.4
    J = np.exp(-((r_norm - r_dynamo)**2) / (2 * 0.15**2))
    mask = r_norm <= 1.0
    J[~mask] = 0.0
    return J / (np.max(J) + 1e-10)


def hex_color(v):
    if v > 0:
        t = min(1.0, v)
        r = int(min(255, 30 + t*200)); g = int(min(255, 80+t*150))
        b = int(min(255, 180+t*75))
    else:
        t = min(1.0, -v)
        r = int(min(255, 120+t*135)); g = int(min(255, 20+t*30)); b = 20
    return f"#{r:02x}{g:02x}{b:02x}"


def energy_color(v):
    t = min(1.0, max(0.0, v))
    b = int(min(255, 60+t*195)); g = int(min(255, t*80)); r = int(min(255, t*30))
    return f"#{r:02x}{g:02x}{b:02x}"


# ─────────────────────────────────────────
# TENSOR HYPERCUBE
# ─────────────────────────────────────────

def generate_hypercube_vertices(q):
    """
    Generate vertices of a Q-dimensional hypercube.
    Q=3 → cube (8 vertices)
    Q=4 → tesseract (16 vertices)
    Q=N → 2^N vertices

    Projects to 2D using isometric-style rotation.
    Returns list of (x, y) screen coords and edge list.
    """
    n_verts = 2**q
    # Generate all binary combinations
    verts_nd = []
    for i in range(n_verts):
        v = [(i >> d) & 1 for d in range(q)]
        verts_nd.append(v)

    # Edges: two vertices connected if they differ in exactly one bit
    edges = []
    for i in range(n_verts):
        for j in range(i+1, n_verts):
            diff = sum(1 for d in range(q)
                       if verts_nd[i][d] != verts_nd[j][d])
            if diff == 1:
                edges.append((i, j))

    return verts_nd, edges


def project_hypercube(verts_nd, q, angle, cx, cy, scale):
    """
    Project Q-dimensional hypercube to 2D.
    Uses successive 2D rotations in each dimension pair.
    Returns list of (x, y) screen coords.
    """
    proj = []
    for v in verts_nd:
        # Center at origin
        coords = [c - 0.5 for c in v]

        # Rotate in each available plane
        for d in range(min(q-1, 4)):
            a = angle * (1.0 + d * 0.3)
            if d+1 < len(coords):
                c0, c1 = coords[d], coords[d+1]
                coords[d]   = c0*math.cos(a) - c1*math.sin(a)
                coords[d+1] = c0*math.sin(a) + c1*math.cos(a)

        # Project first two dimensions to screen
        x = cx + coords[0] * scale
        y = cy + coords[1] * scale * 0.8
        # Depth from remaining dims for size/color
        depth = sum(coords[2:]) if len(coords) > 2 else 0
        proj.append((x, y, depth))

    return proj


# ─────────────────────────────────────────
# MAIN RENDERER
# ─────────────────────────────────────────

class PlanetaryRenderer:

    def __init__(self, parent, json_path=None):
        self.parent   = parent
        self.json_path = json_path
        self.result   = {}
        self.grid     = 256
        self.m_observed = 6
        self._angle   = 0.0
        self._anim_id = None

        if json_path and os.path.exists(json_path):
            with open(json_path) as f:
                self.result = json.load(f)
            self.m_observed = self.result.get("observed_mode", 6)

        self.hex_field = generate_hexagonal_field(self.grid, m=self.m_observed)
        self.ind_field = generate_induction_field(self.grid)

        self._build()

    def _build(self):
        self.win = tk.Toplevel(self.parent)
        planet_name = self.result.get("planet", "Saturn") if self.result else "Saturn"
        self.win.title(f"BCM PLANETARY RENDERER -- {planet_name} Substrate Field")
        self.win.geometry("1500x950")
        self.win.configure(bg=BG_DARK)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Header ──
        hf = tk.Frame(self.win, bg=BG_DARK)
        hf.pack(fill="x", padx=12, pady=(8,4))
        tk.Label(hf, text="BCM PLANETARY RENDERER",
                 font=("Georgia", 18), fg=WHITE, bg=BG_DARK).pack(side="left")
        tk.Label(hf, text="  Circumpunct Coherence Engine — Substrate Scale-Invariance",
                 font=("Consolas", 10), fg="#6a7a90", bg=BG_DARK).pack(side="left")
        tk.Button(hf, text="✕ Close", command=self._on_close,
                  bg="#2a1010", fg=RED,
                  font=("Consolas", 10), relief="flat").pack(side="right")

        # ── View selector ──
        vf = tk.Frame(self.win, bg=BG_MID)
        vf.pack(fill="x", padx=12, pady=(0,4))
        self.view_var = tk.StringVar(value="planets")
        views = [
            ("Planets",          "planets"),
            ("Hex Field",        "hexfield"),
            ("Induction",        "induction"),
            ("Signed",           "signed"),
            ("Spectrum",         "spectrum"),
            ("Decay",            "decay"),
            ("Scale Table",      "scale"),
            ("Tensor Hypercube", "tensor"),
        ]
        for label, val in views:
            tk.Radiobutton(vf, text=label, variable=self.view_var,
                           value=val, command=self._on_view_change,
                           bg=BG_MID, fg=ACCENT, selectcolor=BG_DARK,
                           font=("Consolas", 10),
                           activebackground=BG_MID).pack(side="left", padx=6, pady=4)

        # ── Tensor Q spinbox (always visible) ──
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

        # Canvas
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

        # Status
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.win, textvariable=self.status_var,
                 font=("Consolas", 10), fg=DIM, bg=BG_DARK).pack(
                     fill="x", padx=12, pady=(0,4))

        self._update_q_info()
        self._refresh()

    def _build_right(self, parent):
        # Parameters
        pname = self.result.get("planet", "Saturn").upper()
        pf = tk.LabelFrame(parent, text=f"{pname} PARAMETERS",
                           bg=BG_MID, fg=GOLD,
                           font=("Consolas", 10, "bold"))
        pf.pack(fill="x", padx=4, pady=4)
        params = self.result.get("planet_parameters", self.result.get("saturn_parameters", {}))
        rows = [
            ("Ω",      f"{params.get('omega', 1.63e-4):.2e} rad/s"),
            ("B dyn",  f"{params.get('B_dynamo', 3.0e-4):.2e} T"),
            ("σ",      f"{params.get('sigma_mh', 1.0e5):.2e} S/m"),
            ("J_ind",  f"{self.result.get('induction_source', {}).get('J_ind_SI', 0):.2e} A/m²"),
            ("m obs",  f"{self.m_observed}  (hexagon)"),
            ("m pred", f"{self.result.get('minimum_energy_mode', '?')}"),
            ("Match",  "YES ✓" if self.result.get("match") else "PENDING"),
        ]
        for label, val in rows:
            rf = tk.Frame(pf, bg=BG_MID)
            rf.pack(fill="x", padx=4, pady=1)
            tk.Label(rf, text=f"{label}:", font=("Consolas", 9),
                     fg=DIM, bg=BG_MID, width=7, anchor="w").pack(side="left")
            color = GREEN if "YES" in val else GOLD if "PENDING" in val else WHITE
            tk.Label(rf, text=val, font=("Consolas", 9, "bold"),
                     fg=color, bg=BG_MID).pack(side="left")

        # Eigenmode bars
        ef = tk.LabelFrame(parent, text="BESSEL MODE ENERGIES",
                           bg=BG_MID, fg=GOLD,
                           font=("Consolas", 10, "bold"))
        ef.pack(fill="x", padx=4, pady=4)
        energies = self.result.get("bessel_energies", {})
        if energies:
            vals = {int(k): v for k, v in energies.items()}
            e_min = min(vals.values()); e_max = max(vals.values())
            e_range = e_max - e_min if e_max > e_min else 1
            for m in sorted(vals.keys()):
                e = vals[m]
                norm = 1.0 - (e - e_min) / e_range
                bar_w = int(norm * 140)
                is_obs = (m == self.m_observed)
                is_min = (m == self.result.get("minimum_energy_mode"))
                rf2 = tk.Frame(ef, bg=BG_MID)
                rf2.pack(fill="x", padx=4, pady=1)
                lbl_c = GREEN if is_obs else GOLD if is_min else DIM
                tk.Label(rf2, text=f"m={m:2d}", font=("Consolas", 8),
                         fg=lbl_c, bg=BG_MID, width=5).pack(side="left")
                bf = tk.Frame(rf2, bg=BG_DARK, height=10, width=155)
                bf.pack(side="left", padx=1)
                bf.pack_propagate(False)
                bc = GREEN if is_obs else GOLD if is_min else ACCENT
                tk.Frame(bf, bg=bc, height=10,
                         width=max(2, bar_w)).place(x=0, y=0)
                tag = " OBS" if is_obs else " MIN" if is_min else ""
                if tag:
                    tk.Label(rf2, text=tag, font=("Consolas", 7),
                             fg=bc, bg=BG_MID).pack(side="left")
        else:
            tk.Label(ef, text="Run solver to populate",
                     font=("Consolas", 9), fg=DIM, bg=BG_MID).pack(padx=4, pady=4)

        # Storm decay registry
        df = tk.LabelFrame(parent, text="DEVIATION REGISTRY",
                           bg=BG_MID, fg=GOLD,
                           font=("Consolas", 10, "bold"))
        df.pack(fill="x", padx=4, pady=4)
        storm_events = self.result.get("storm_events", {})
        for key, ev in storm_events.items():
            rf4 = tk.Frame(df, bg=BG_MID)
            rf4.pack(fill="x", padx=4, pady=1)
            dev = ev.get("deviation_deg", 0)
            bar_w = int(min(dev / 5.0, 1.0) * 100)
            bc = GREEN if dev < 1.0 else GOLD if dev < 3.0 else RED
            tk.Label(rf4, text=str(ev["year"]), font=("Consolas", 9),
                     fg=WHITE, bg=BG_MID, width=5).pack(side="left")
            bf = tk.Frame(rf4, bg=BG_DARK, height=8, width=110)
            bf.pack(side="left", padx=2)
            bf.pack_propagate(False)
            tk.Frame(bf, bg=bc, height=8,
                     width=max(2, bar_w)).place(x=0, y=0)
            tk.Label(rf4, text=f"{dev:.1f}°",
                     font=("Consolas", 8), fg=bc, bg=BG_MID).pack(side="left")

        # Scale invariance table
        sf = tk.LabelFrame(parent, text="SCALE INVARIANCE",
                           bg=BG_MID, fg=GOLD,
                           font=("Consolas", 10, "bold"))
        sf.pack(fill="x", padx=4, pady=4)
        si_data = [
            ("Galactic", "SMBH",   "0.1",     "—"),
            ("Planetary","Dynamo", "derived", "6"),
            ("Solar?",   "Dynamo", "?",       "?"),
        ]
        for row in si_data:
            rf5 = tk.Frame(sf, bg=BG_MID)
            rf5.pack(fill="x", padx=4, pady=1)
            for cell, w in zip(row, [9, 9, 9, 4]):
                c = GOLD if row[0] == "Galactic" else SATURN_GOLD if row[0]=="Planetary" else DIM
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
        if view == "planets":       self._draw_planets()
        elif view == "sphere":      self._draw_sphere()
        elif view == "hexfield":    self._draw_field(self.hex_field, False, f"Hexagonal Standing Wave  m={self.m_observed}")
        elif view == "induction":   self._draw_field(self.ind_field, False, "Induction Source  J_ind = sigma(v x B)")
        elif view == "signed":      self._draw_field(self.hex_field, True,  "Signed Field -- void zones in red")
        elif view == "divergence":  self._draw_divergence()
        elif view == "spectrum":    self._draw_spectrum()
        elif view == "decay":       self._draw_decay()
        elif view == "scale":       self._draw_scale_table()
        elif view == "tensor":      self._start_tensor_anim()

    # ── Planet gallery ──

    def _load_all_planet_results(self):
        """Load all 8 planet JSONs from data/results/ into a dict."""
        base = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(base, "data", "results")
        planet_data = {}
        for name in PLANETS:
            fpath = os.path.join(results_dir,
                                  f"BCM_{name}_planetary_wave.json")
            if os.path.exists(fpath):
                try:
                    with open(fpath, encoding="utf-8") as f:
                        planet_data[name] = json.load(f)
                except Exception:
                    pass
        return planet_data

    def _draw_standing_wave(self, cx, cy, radius, m, color):
        """Draw m-sided standing wave polygon on planet."""
        if not m or m <= 0:
            return
        pts = []
        for i in range(m):
            angle = math.radians(360 * i / m - 90)
            pts.append(cx + radius * 0.80 * math.cos(angle))
            pts.append(cy + radius * 0.80 * math.sin(angle))
        if len(pts) >= 4:
            self.canvas.create_polygon(*pts, outline=color,
                                        fill="", width=2, dash=(5, 3))
        for i in range(m):
            angle = math.radians(360 * i / m - 90)
            vx = cx + radius * 0.80 * math.cos(angle)
            vy = cy + radius * 0.80 * math.sin(angle)
            self.canvas.create_line(cx, cy, vx, vy,
                                     fill=color, width=1, dash=(2, 5))
        self.canvas.create_oval(cx-4, cy-4, cx+4, cy+4,
                                 fill=color, outline="")

    def _draw_planets(self):
        W, H = self._cw, self._ch
        planet_names = list(PLANETS.keys())
        n = len(planet_names)
        cols = 4
        rows = math.ceil(n / cols)
        cell_w = W // cols
        cell_h = (H - 50) // rows

        self.canvas.create_text(W//2, 18,
            text="BCM PLANETARY SUBSTRATE -- Scale-Invariance Gallery",
            fill=WHITE, font=("Consolas", 12, "bold"))

        planet_data = self._load_all_planet_results()
        confirmed = sum(1 for d in planet_data.values() if d.get("match") is True)
        predicted = sum(1 for d in planet_data.values() if d.get("bcm_status") == "prediction")
        null_ct   = sum(1 for d in planet_data.values() if d.get("match") == "N/A")
        self.canvas.create_text(W//2, 36,
            text=f"Confirmed: {confirmed}    Predicted: {predicted}    Null: {null_ct}    |    Same equation. Different scale.",
            fill=DIM, font=("Consolas", 9))

        for i, name in enumerate(planet_names):
            col = i % cols
            row = i // cols
            cx = col * cell_w + cell_w // 2
            cy = row * cell_h + cell_h // 2 + 50
            radius = min(cell_w, cell_h) // 3 - 14
            draw_planet(self.canvas, name, cx, cy, radius)

            # Live result badge
            pdata  = planet_data.get(name, {})
            match  = pdata.get("match")
            m_pred = pdata.get("minimum_energy_mode")
            status = pdata.get("bcm_status", "")

            bx, by = cx, cy + radius + 46
            if match is True and m_pred and m_pred > 0:
                self._draw_standing_wave(cx, cy, radius, m_pred, GREEN)
                self.canvas.create_rectangle(bx-30, by-8, bx+30, by+8,
                    fill="#0a2010", outline=GREEN)
                self.canvas.create_text(bx, by, text=f"m={m_pred}  LOCK",
                    fill=GREEN, font=("Consolas", 7, "bold"))
            elif status == "prediction":
                self._draw_standing_wave(cx, cy, radius, m_pred or 1, GOLD)
                self.canvas.create_rectangle(bx-36, by-8, bx+36, by+8,
                    fill="#201000", outline=GOLD)
                self.canvas.create_text(bx, by, text=f"m={m_pred}  PREDICT",
                    fill=GOLD, font=("Consolas", 7, "bold"))
            elif match == "N/A":
                self.canvas.create_rectangle(bx-30, by-8, bx+30, by+8,
                    fill="#101010", outline=DIM)
                self.canvas.create_text(bx, by, text="NO DYNAMO",
                    fill=DIM, font=("Consolas", 7))

        self.status_var.set(f"{n} planets  |  {confirmed} confirmed  {predicted} predicted  {null_ct} null  |  BCM Substrate Scale-Invariance")

    # ── 2D field views ──

    def _draw_field(self, field, signed, title):
        W, H = self._cw, self._ch
        S = min(W, H) - 40
        G = field.shape[0]
        px = S / G
        ox = (W - S) // 2
        oy = (H - S) // 2 + 20

        fmax = np.max(np.abs(field))
        if fmax <= 0: fmax = 1.0

        # PIL fast path
        if _PIL:
            img_mode = "signed" if signed else "energy"
            pil_img = field_to_image_planet(field, mode=img_mode,
                                            size=(S, S))
            self._tk_img_field = ImageTk.PhotoImage(pil_img)
            self.canvas.create_image(ox, oy, anchor="nw",
                                     image=self._tk_img_field)
        else:
            step = max(1, int(G / 180))
            for iy in range(0, G, step):
                for ix in range(0, G, step):
                    v = field[iy, ix]
                    color = hex_color(v/fmax) if signed else energy_color(abs(v)/fmax)
                    x0 = ox + ix*px; y0 = oy + iy*px
                    self.canvas.create_rectangle(x0, y0, x0+px*step+1, y0+px*step+1,
                                                  fill=color, outline="")

        cx, cy = ox + S//2, oy + S//2
        r_hex = S * 0.42
        self._draw_hex(cx, cy, r_hex)

        for frac in [0.15, 0.28]:
            r = S * frac
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                    outline=DIM, dash=(3,6))

        self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5,
                                 fill=SATURN_GOLD, outline="")
        self.canvas.create_text(W//2, oy-14, text=title,
                                 fill=WHITE, font=("Consolas", 11, "bold"))
        self.status_var.set(f"m={self.m_observed}  |ρ|_max={fmax:.3f}")

    def _draw_hex(self, cx, cy, r):
        pts = []
        for i in range(6):
            a = math.radians(60*i - 30)
            pts += [cx + r*math.cos(a), cy + r*math.sin(a)]
        self.canvas.create_polygon(*pts, outline=SATURN_GOLD,
                                    fill="", width=2, dash=(6,4))
        for i in range(6):
            a = math.radians(60*i - 30)
            vx = cx + (r+18)*math.cos(a)
            vy = cy + (r+18)*math.sin(a)
            self.canvas.create_text(vx, vy, text=str(i+1),
                                     fill=SATURN_GOLD, font=("Consolas",9))

    # ── Spectrum ──

    def _draw_sphere(self):
        """
        Spherical substrate visualization with height+lighting shading.
        The standing wave geometry appears as surface relief on the planetary body.
        """
        W, H = self._cw, self._ch
        S = min(W, H) - 40
        G = self.hex_field.shape[0]
        ox = (W - S) // 2
        oy = (H - S) // 2 + 20

        planet_name = self.result.get("planet", "Saturn") if self.result else "Saturn"
        m = self.m_observed

        # Apply spherical shading to the standing wave field
        shaded = spherical_shading_planet(self.hex_field, m=m)

        if _PIL:
            pil_img = field_to_image_planet(shaded, mode="sphere", size=(S, S))
            self._tk_img_sphere = ImageTk.PhotoImage(pil_img)
            self.canvas.create_image(ox, oy, anchor="nw",
                                     image=self._tk_img_sphere)
        else:
            # Fallback rectangle
            step = max(1, int(G / 180))
            px = S / G
            fmax = np.max(shaded) or 1.0
            for iy in range(0, G, step):
                for ix in range(0, G, step):
                    v = shaded[iy, ix] / fmax
                    r_c = int(min(255, 80 + v*175))
                    g_c = int(min(255, 60 + v*160))
                    b_c = int(min(255, 20 + v*100))
                    col = f"#{r_c:02x}{g_c:02x}{b_c:02x}"
                    self.canvas.create_rectangle(
                        ox+ix*px, oy+iy*px,
                        ox+ix*px+px*step+1, oy+iy*px+px*step+1,
                        fill=col, outline="")

        cx = ox + S//2; cy = oy + S//2

        # Atmospheric halo
        r_base = S // 2
        for ri in range(0, 25, 3):
            alpha = max(0, 1.0 - ri/25)
            av = int(alpha * 100)
            hcol = f"#{int(av*0.5):02x}{int(av*0.6):02x}{av:02x}"
            self.canvas.create_oval(
                cx-(r_base+ri), cy-(r_base+ri),
                cx+(r_base+ri), cy+(r_base+ri),
                outline=hcol)

        # Draw m-sided standing wave polygon overlay
        r_wave = int(S * 0.36)
        pts = []
        for i in range(m):
            angle = math.radians(360*i/m - 90)
            pts += [cx + r_wave*math.cos(angle), cy + r_wave*math.sin(angle)]
        if len(pts) >= 4:
            self.canvas.create_polygon(*pts, outline=SATURN_GOLD,
                                        fill="", width=2, dash=(5,3))
        # Radial spokes
        for i in range(m):
            angle = math.radians(360*i/m - 90)
            vx = cx + r_wave*math.cos(angle)
            vy = cy + r_wave*math.sin(angle)
            self.canvas.create_line(cx, cy, vx, vy,
                                     fill=SATURN_GOLD, width=1, dash=(3,5))
        # Center pump dot
        self.canvas.create_oval(cx-6, cy-6, cx+6, cy+6,
                                 fill=SATURN_GOLD, outline=WHITE)

        self.canvas.create_text(W//2, oy-16,
            text=f"{planet_name} -- Substrate Sphere  m={m}",
            fill=WHITE, font=("Consolas", 11, "bold"))
        self.status_var.set(
            f"Sphere mode  m={m}  planet={planet_name}  "
            f"PIL={'on' if _PIL else 'off'}")

    def _draw_divergence(self):
        """
        Divergence field: shows where substrate is injected vs leaking.
        Positive (blue) = substrate entering.
        Negative (red) = substrate exiting / void zone.
        """
        W, H = self._cw, self._ch
        S = min(W, H) - 40
        G = self.hex_field.shape[0]
        ox = (W - S) // 2
        oy = (H - S) // 2 + 20

        # Compute divergence of J = -grad(rho)
        gy_d, gx_d = np.gradient(self.hex_field)
        jx = -gx_d; jy = -gy_d
        div = np.gradient(jx, axis=1) + np.gradient(jy, axis=0)

        if _PIL:
            pil_img = field_to_image_planet(div, mode="signed", size=(S, S))
            self._tk_img_div = ImageTk.PhotoImage(pil_img)
            self.canvas.create_image(ox, oy, anchor="nw",
                                     image=self._tk_img_div)
        else:
            step = max(1, int(G / 180))
            px = S / G
            fmax = np.max(np.abs(div)) or 1.0
            for iy in range(0, G, step):
                for ix in range(0, G, step):
                    v = div[iy, ix] / fmax
                    if v >= 0:
                        col = f"#{int(v*30):02x}{int(v*60):02x}{int(30+v*220):02x}"
                    else:
                        col = f"#{int(-v*220+30):02x}{int(-v*60):02x}1e"
                    self.canvas.create_rectangle(
                        ox+ix*px, oy+iy*px,
                        ox+ix*px+px*step+1, oy+iy*px+px*step+1,
                        fill=col, outline="")

        cx = ox + S//2; cy = oy + S//2

        # Hexagon overlay
        self._draw_hex(cx, cy, S*0.42)

        # Legend
        self.canvas.create_rectangle(ox+10, oy+10, ox+22, oy+22,
                                      fill="#1e1eff", outline="")
        self.canvas.create_text(ox+28, oy+16, text="Injection (+)",
                                 fill=ACCENT, font=("Consolas", 9), anchor="w")
        self.canvas.create_rectangle(ox+10, oy+28, ox+22, oy+40,
                                      fill="#ff1e1e", outline="")
        self.canvas.create_text(ox+28, oy+34, text="Void / Leak (-)",
                                 fill=RED, font=("Consolas", 9), anchor="w")

        m = self.m_observed
        planet_name = self.result.get("planet", "Saturn") if self.result else "Saturn"
        self.canvas.create_text(W//2, oy-16,
            text=f"{planet_name} -- Substrate Divergence  m={m}",
            fill=WHITE, font=("Consolas", 11, "bold"))
        self.status_var.set(f"Divergence: injection=blue  void=red  m={m}")

    def _draw_spectrum(self):
        W, H = self._cw, self._ch
        energies = self.result.get("bessel_energies", {})
        if not energies:
            self.canvas.create_text(W//2, H//2,
                text="Run solver first", fill=DIM, font=("Consolas",12))
            return
        vals = {int(k): v for k, v in energies.items()}
        e_min = min(vals.values()); e_max = max(vals.values())
        e_range = e_max - e_min if e_max > e_min else 1
        ml,mr,mt,mb = 70,30,60,70
        pw = W-ml-mr; ph = H-mt-mb
        n = len(vals); bw = pw//n - 4
        self.canvas.create_rectangle(ml,mt,W-mr,H-mb, outline=DIM, fill=BG_MID)
        self.canvas.create_text(W//2, mt-30,
            text="Bessel Eigenmode Energy — Azimuthal Wave Number m",
            fill=WHITE, font=("Consolas",11,"bold"))
        self.canvas.create_text(W//2, H-20,
            text="m  (minimum energy = predicted standing wave geometry)",
            fill=DIM, font=("Consolas",9))
        for idx, m in enumerate(sorted(vals.keys())):
            e = vals[m]; norm = (e-e_min)/e_range
            bh = int(norm*ph*0.85)+4
            x0 = ml+idx*(bw+4)+2; x1=x0+bw; y1=H-mb; y0=y1-bh
            is_obs=(m==self.m_observed); is_min=(m==self.result.get("minimum_energy_mode"))
            color = GREEN if is_obs else GOLD if is_min else ACCENT
            self.canvas.create_rectangle(x0,y0,x1,y1, fill=color, outline="")
            self.canvas.create_text((x0+x1)//2, y1+12, text=str(m),
                                     fill=WHITE, font=("Consolas",9))
            if is_obs:
                self.canvas.create_text((x0+x1)//2, y0-12,
                    text="OBS", fill=GREEN, font=("Consolas",8,"bold"))
            elif is_min:
                self.canvas.create_text((x0+x1)//2, y0-12,
                    text="MIN", fill=GOLD, font=("Consolas",8,"bold"))
        self.status_var.set(f"Eigenmode spectrum — {n} modes")

    # ── Decay ──

    def _draw_decay(self):
        W, H = self._cw, self._ch
        storm_events = self.result.get("storm_events", {})
        if not storm_events:
            self.canvas.create_text(W//2, H//2,
                text="No storm data", fill=DIM, font=("Consolas",12)); return
        events = sorted(storm_events.values(), key=lambda x: x["year"])
        years=[e["year"] for e in events]; devs=[e["deviation_deg"] for e in events]
        notes=[e["notes"] for e in events]
        ml,mr,mt,mb=80,40,60,70; pw=W-ml-mr; ph=H-mt-mb
        yr_min,yr_max=min(years),max(years); dev_max=max(devs)*1.2 or 5.0
        self.canvas.create_rectangle(ml,mt,W-mr,H-mb,outline=DIM,fill=BG_MID)
        self.canvas.create_text(W//2,mt-30,
            text="Saturn Hexagon — Geometric Deviation Registry 1980–2017",
            fill=WHITE,font=("Consolas",12,"bold"))
        for i in range(5):
            y=mt+i*ph//4; val=dev_max*(1-i/4)
            self.canvas.create_line(ml,y,W-mr,y,fill=DIM,dash=(2,4))
            self.canvas.create_text(ml-8,y,text=f"{val:.1f}°",
                fill=WHITE,font=("Consolas",9),anchor="e")
        self.canvas.create_text(18,mt+ph//2,text="Deviation (°)",
            fill=WHITE,font=("Consolas",9),angle=90)
        self.canvas.create_text(W//2,H-18,text="Year",fill=DIM,font=("Consolas",9))
        def to_xy(yr,dev):
            x=ml+(yr-yr_min)/max(yr_max-yr_min,1)*pw
            y=mt+(1-dev/dev_max)*ph; return x,y
        yr_range=np.linspace(years[1],years[-1],100); d_max=devs[1]; tau=4.22
        pts=[]
        for yr in yr_range:
            d=d_max*np.exp(-(yr-years[1])/tau); x,y=to_xy(yr,d); pts+=[x,y]
        if len(pts)>=4:
            self.canvas.create_line(*pts,fill=ACCENT,width=2,smooth=True,dash=(6,3))
        colors=[GREEN,RED,GOLD]
        for i,(yr,dev,note) in enumerate(zip(years,devs,notes)):
            x,y=to_xy(yr,dev); c=colors[i%len(colors)]
            self.canvas.create_oval(x-8,y-8,x+8,y+8,fill=c,outline=WHITE,width=1)
            self.canvas.create_text(x,y-22,text=str(yr),fill=WHITE,font=("Consolas",9,"bold"))
            self.canvas.create_text(x,y+22,text=f"{dev:.1f}°",fill=c,font=("Consolas",9))
            self.canvas.create_text(x,H-mb-14,text=note[:18],fill=DIM,font=("Consolas",8))
        self.canvas.create_text(W-mr-12,mt+20,
            text=f"τ = 4.22 yr\nχ = 7.5×10⁻⁸",fill=GOLD,font=("Consolas",9),anchor="e")
        self.status_var.set("Recovery τ=4.22yr  χ=7.5e-8")

    # ── Scale Table ──

    def _draw_scale_table(self):
        W, H = self._cw, self._ch
        self.canvas.create_text(W//2,30,
            text="BCM SUBSTRATE SCALE INVARIANCE",fill=WHITE,font=("Consolas",15,"bold"))
        self.canvas.create_text(W//2,58,
            text="Same wave equation — different pump — different scale",
            fill=DIM,font=("Consolas",11))
        headers=["Scale","Pump","Geometry","J_source","λ","m"]
        col_x=[60,200,360,530,700,800]; y_h=100
        for h,x in zip(headers,col_x):
            self.canvas.create_text(x,y_h,text=h,fill=GOLD,
                font=("Consolas",11,"bold"),anchor="w")
        self.canvas.create_line(50,y_h+18,W-40,y_h+18,fill=DIM)
        rows=[
            ("Galactic","SMBH","Spiral Disk","J_baryon","0.1","—"),
            ("Planetary","Metallic H Dynamo","Polar Hexagon","J_ind (σv×B)","derived","6"),
            ("Solar?","Solar Dynamo","Coronal loops?","J_magnetic","?","?"),
            ("Atomic?","Nuclear","Orbital shells?","J_nuclear","?","?"),
        ]
        row_colors=[GREEN,SATURN_GOLD,DIM,DIM]
        y=y_h+38
        for row,color in zip(rows,row_colors):
            for val,x in zip(row,col_x):
                self.canvas.create_text(x,y,text=val,fill=color,
                    font=("Consolas",10),anchor="w")
            self.canvas.create_line(50,y+18,W-40,y+18,fill="#1a2030")
            y+=38
        y+=30
        self.canvas.create_text(W//2,y,
            text="IF  λ_planetary ≈ λ_galactic = 0.1",
            fill=WHITE,font=("Consolas",13,"bold"))
        y+=34
        self.canvas.create_text(W//2,y,
            text="BCM is a fundamental law of the vacuum",
            fill=GREEN,font=("Consolas",15,"bold"))
        y+=28
        self.canvas.create_text(W//2,y,
            text="not an astrophysical model",fill=GREEN,font=("Consolas",13,"bold"))
        y+=44
        self.canvas.create_text(W//2,y,
            text="Current: λ_planetary derivation in progress — k constraint from dynamo frequency pending",
            fill=GOLD,font=("Consolas",10))
        self.status_var.set("Scale invariance — galactic vs planetary")

    # ── Tensor Hypercube ──

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
            text=f"TENSOR Q={q} HYPERCUBE — Substrate Impedance Z_ij Projection",
            fill=WHITE, font=("Consolas",11,"bold"))
        self.canvas.create_text(W//2, 42,
            text=f"{q}D → 2D  |  {n_v} vertices  {n_e} edges  |  Z_ij = λδ_ij + χε_ij",
            fill=DIM, font=("Consolas",9))

        cx, cy = W//2, H//2 + 20
        scale = min(W, H) * 0.28

        verts_nd, edges = generate_hypercube_vertices(q)
        proj = project_hypercube(verts_nd, q, self._angle, cx, cy, scale)

        # Depth range for coloring
        depths = [p[2] for p in proj]
        d_min = min(depths); d_max = max(depths)
        d_range = d_max - d_min if d_max > d_min else 1.0

        # Draw edges
        for i, j in edges:
            x0,y0,d0 = proj[i]; x1,y1,d1 = proj[j]
            depth_avg = ((d0+d1)/2 - d_min) / d_range
            # Color edges by dimension they span
            diff_dim = next(d for d in range(q)
                           if verts_nd[i][d] != verts_nd[j][d])
            dim_colors = [ACCENT, GOLD, GREEN, RED, "#cc88ff",
                          "#ff8844", "#44ffcc"]
            color = dim_colors[diff_dim % len(dim_colors)]
            # Fade by depth
            alpha = int(80 + depth_avg * 175)
            r = int(int(color[1:3],16) * alpha/255)
            g = int(int(color[3:5],16) * alpha/255)
            b = int(int(color[5:7],16) * alpha/255)
            edge_color = f"#{r:02x}{g:02x}{b:02x}"
            width = max(1, int(1 + depth_avg * 2))
            self.canvas.create_line(x0,y0,x1,y1, fill=edge_color, width=width)

        # Draw vertices
        for i, (x,y,depth) in enumerate(proj):
            depth_norm = (depth - d_min) / d_range
            r_v = int(3 + depth_norm * 5)
            v_color = GOLD if depth_norm > 0.8 else ACCENT if depth_norm > 0.4 else DIM
            self.canvas.create_oval(x-r_v,y-r_v,x+r_v,y+r_v,
                                     fill=v_color, outline="")

        # Dimension color legend
        dim_colors = [ACCENT, GOLD, GREEN, RED, "#cc88ff", "#ff8844", "#44ffcc"]
        dim_names  = ["x (λ_iso)", "y (χε_xx)", "z (χε_yy)",
                      "w (χε_xy)", "v₅", "v₆", "v₇"]
        for d in range(min(q, 4)):
            lx = 60; ly = H - 80 + d*18
            self.canvas.create_line(lx,ly,lx+20,ly,
                fill=dim_colors[d], width=2)
            self.canvas.create_text(lx+26,ly,
                text=dim_names[d] if d < len(dim_names) else f"v{d+1}",
                fill=dim_colors[d], font=("Consolas",9), anchor="w")

        # BCM connection
        self.canvas.create_text(W//2, H-18,
            text=f"Each axis = one component of Z_ij — the substrate impedance tensor",
            fill=DIM, font=("Consolas",9))

        self.status_var.set(
            f"Tensor Q={q}  {n_v} vertices  {n_e} edges  "
            f"θ={math.degrees(self._angle):.1f}°")


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BCM Planetary Renderer")
    parser.add_argument("--json", type=str, default=None)
    args = parser.parse_args()

    json_path = args.json
    if json_path is None:
        base = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(base, "data", "results")
        # Load last_run pointer — shows whichever planet ran most recently
        last_run = os.path.join(results_dir, "BCM_planetary_last_run.json")
        if os.path.exists(last_run):
            try:
                with open(last_run) as f:
                    lr = json.load(f)
                candidate = os.path.join(results_dir, lr.get("last_file", ""))
                if os.path.exists(candidate):
                    json_path = candidate
            except Exception:
                pass
        # Fallback to Saturn
        if json_path is None:
            default = os.path.join(results_dir, "BCM_Saturn_planetary_wave.json")
            if os.path.exists(default):
                json_path = default

    root = tk.Tk()
    root.withdraw()
    app = PlanetaryRenderer(root, json_path)
    app.win.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
