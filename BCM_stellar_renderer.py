# -*- coding: utf-8 -*-
"""
BCM Stellar Renderer
====================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
NSF I-Corps -- Team GIBUSH

# === BCM MASTER BUILD ADDITION v2.2 | 2026-03-31 EST ===

Publication-quality visualization for BCM stellar wave results.
Companion to BCM_stellar_wave.py, BCM_stellar_overrides.py.

Outputs PNG files for Zenodo, papers, and in-chat review.
Uses matplotlib (headless-compatible) -- no tkinter required.

Panels:
    1. Star Gallery        -- 13 stars, class-colored, mode badges
    2. Bessel Spectrum      -- eigenmode energy per star
    3. Tachocline Gate      -- m_observed vs conv_depth_frac
    4. J_ind Landscape      -- induction current across all stars
    5. Combined Arms Table  -- galactic class <-> stellar analog
    6. Lambda Scale Plot    -- lambda ratio across scales

Usage:
    python BCM_stellar_renderer.py
    python BCM_stellar_renderer.py --star Sun
    python BCM_stellar_renderer.py --gallery
    python BCM_stellar_renderer.py --all

# === END ADDITION ===
"""

import numpy as np
import json
import os
import sys
import argparse

import matplotlib
matplotlib.use("Agg")  # headless -- no display required
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

try:
    from scipy.special import jv
    _SCIPY = True
except ImportError:
    _SCIPY = False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from BCM_stellar_wave import compute_stellar_params, STELLAR_REGISTRY, LAM_GALACTIC, LAM_PLANETARY

# ─────────────────────────────────────────
# COLOR PALETTE -- Emerald Entities
# ─────────────────────────────────────────

BG_DARK     = "#080a0e"
BG_PANEL    = "#10131a"
EMERALD     = "#40ee70"
SCARLET     = "#ff5555"
GOLD        = "#ffbb44"
BLUE        = "#60aaff"
WHITE       = "#e0e8f0"
DIM         = "#3a4a60"
CYAN        = "#40dddd"
PURPLE      = "#bb77ff"

# Class colors
CLASS_COLORS = {
    "I":    EMERALD,
    "II":   GOLD,
    "III":  DIM,
    "IV":   SCARLET,
    "V-A":  CYAN,
    "VI":   PURPLE,
    "?":    GOLD,
}

def _class_key(bcm_class):
    """Extract class number from bcm_class string."""
    for key in ["V-A", "V-B", "VI", "IV", "III", "II", "I", "?"]:
        if key in bcm_class:
            return key
    return "?"


def _load_overrides_registry():
    """Load full 13-star registry from overrides if available."""
    try:
        from BCM_stellar_overrides import get_full_registry
        return get_full_registry()
    except ImportError:
        return dict(STELLAR_REGISTRY)


def _get_results_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "results")


# ─────────────────────────────────────────
# PANEL 1: STAR GALLERY
# ─────────────────────────────────────────

def render_gallery(registry=None, save_path=None):
    """
    13-star gallery grid. Each star: colored circle with spectral type,
    m badge, class label.
    """
    reg = registry or _load_overrides_registry()
    stars = list(reg.items())
    n = len(stars)

    # Grid layout
    ncols = 4
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, nrows * 3.8),
                              facecolor=BG_DARK)
    fig.suptitle("BCM STELLAR WAVE GALLERY -- Combined Arms Registry",
                 fontsize=16, color=WHITE, fontweight="bold", y=0.98)
    fig.text(0.5, 0.955,
             "Stephen Justin Burdick Sr. -- Emerald Entities LLC -- 2026",
             ha="center", fontsize=9, color=DIM)

    # Spectral type -> star color mapping
    SPEC_COLORS = {
        "O": "#9bb0ff", "B": "#aabfff", "A": "#cad7ff",
        "F": "#f8f7ff", "G": "#fff4ea", "K": "#ffd2a1",
        "M": "#ffb56c",
    }

    for idx in range(nrows * ncols):
        row = idx // ncols
        col = idx % ncols
        ax = axes[row][col] if nrows > 1 else axes[col]
        ax.set_facecolor(BG_PANEL)
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.8, 1.5)
        ax.set_aspect("equal")
        ax.axis("off")

        if idx >= n:
            ax.set_visible(False)
            continue

        name, params = stars[idx]
        derived = compute_stellar_params(name, params)
        spec = params.get("spectral_type", "G2V")
        m_obs = params.get("m_observed", 0)
        m_pred = derived["m_predicted"]
        bcm_class = params.get("bcm_class", "")
        cls_key = _class_key(bcm_class)
        cls_color = CLASS_COLORS.get(cls_key, DIM)

        # Star color from spectral type
        star_color = SPEC_COLORS.get(spec[0], "#fff4ea")

        # Draw star circle
        star_radius = 0.6
        # Scale by actual radius (log scale, normalized)
        r_km = params.get("radius_km", 695700)
        r_scale = np.clip(np.log10(r_km / 695700.0) * 0.3 + 0.6, 0.3, 1.1)
        star_radius = r_scale

        circle = plt.Circle((0, 0.2), star_radius, color=star_color,
                             ec=cls_color, linewidth=2.5, zorder=2)
        ax.add_patch(circle)

        # m badge
        if m_obs > 0:
            match = (m_pred == m_obs)
            badge_color = EMERALD if match else SCARLET
            badge_text = f"m={m_obs}"
            if match:
                badge_text += " \u2713"
        else:
            badge_color = GOLD
            badge_text = "m=?"

        ax.text(star_radius * 0.7, 0.2 + star_radius * 0.7,
                badge_text, fontsize=8, fontweight="bold",
                color=BG_DARK, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.2", fc=badge_color,
                          ec="none", alpha=0.9), zorder=3)

        # Star name
        ax.text(0, -0.9, name.replace("_", " "),
                fontsize=11, fontweight="bold", color=WHITE,
                ha="center", va="center")

        # Spectral type + class
        ax.text(0, -1.2, f"{spec}  --  {cls_key}",
                fontsize=8, color=cls_color, ha="center", va="center")

        # J_ind
        J = derived["J_ind_SI"]
        ax.text(0, -1.5, f"J={J:.2e} A/m\u00b2",
                fontsize=7, color=DIM, ha="center", va="center")

    plt.tight_layout(rect=[0, 0, 1, 0.94])

    if save_path is None:
        save_path = os.path.join(_get_results_dir(),
                                 "BCM_stellar_gallery.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, facecolor=BG_DARK,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")
    return save_path


# ─────────────────────────────────────────
# PANEL 2: BESSEL SPECTRUM
# ─────────────────────────────────────────

def render_spectrum(star_name, params, save_path=None):
    """
    Bessel eigenmode energy spectrum for a single star.
    Shows energy at each m, marks observed and predicted.
    """
    derived = compute_stellar_params(star_name, params)
    H_energies = derived["H_energies"]
    m_obs = params.get("m_observed", 0)
    m_pred = derived["m_predicted"]

    modes = sorted([int(k) for k in H_energies.keys()])
    vals = [H_energies[str(m)] for m in modes]

    fig, ax = plt.subplots(1, 1, figsize=(10, 5), facecolor=BG_DARK)
    ax.set_facecolor(BG_PANEL)

    # Bar colors -- minimum H = resonance (inverted from old Bessel max)
    colors = []
    for m in modes:
        if m == m_obs and m_obs > 0:
            colors.append(EMERALD)
        elif m == m_pred:
            colors.append(BLUE)
        else:
            colors.append(DIM)

    ax.bar(modes, vals, color=colors, edgecolor="#1a1a2e", linewidth=0.5)

    # Labels
    ax.set_xlabel("Azimuthal Mode m", color=WHITE, fontsize=11)
    ax.set_ylabel("H(m) = (c_s \u2212 \u03a9R/m)\u00b2", color=WHITE, fontsize=11)
    ax.set_title(f"BCM RESONANCE HAMILTONIAN -- {star_name}  "
                 f"({params.get('spectral_type','')})  "
                 f"m_obs={m_obs}  m_pred={m_pred}",
                 color=WHITE, fontsize=13, fontweight="bold")

    ax.tick_params(colors=DIM)
    ax.spines["bottom"].set_color(DIM)
    ax.spines["left"].set_color(DIM)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend
    patches = [
        mpatches.Patch(color=EMERALD, label=f"Observed m={m_obs}"),
        mpatches.Patch(color=BLUE, label=f"Predicted m={m_pred}"),
    ]
    ax.legend(handles=patches, loc="upper right",
              facecolor=BG_PANEL, edgecolor=DIM, labelcolor=WHITE)

    if save_path is None:
        save_path = os.path.join(_get_results_dir(),
                                 f"BCM_{star_name}_spectrum.png")
    fig.savefig(save_path, dpi=150, facecolor=BG_DARK,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")
    return save_path


# ─────────────────────────────────────────
# PANEL 3: TACHOCLINE GATE DIAGRAM
# ─────────────────────────────────────────

def render_tachocline_gate(registry=None, save_path=None):
    """
    Scatter plot: conv_depth_frac vs m_observed.
    Fully convective (1.0) stars should cluster at m=1.
    Tachocline stars should spread to higher m.
    The gate.
    """
    reg = registry or _load_overrides_registry()

    fig, ax = plt.subplots(1, 1, figsize=(10, 6), facecolor=BG_DARK)
    ax.set_facecolor(BG_PANEL)

    for name, params in reg.items():
        derived = compute_stellar_params(name, params)
        m_obs = params.get("m_observed", 0)
        conv = params.get("conv_depth_frac", 0.3)
        cls_key = _class_key(params.get("bcm_class", ""))
        color = CLASS_COLORS.get(cls_key, DIM)

        if m_obs == 0:
            # Unknown m -- plot as X
            ax.scatter(conv, 0.5, marker="x", s=120, color=GOLD,
                       zorder=3, linewidths=2)
            ax.annotate(name.replace("_", " "), (conv, 0.5),
                        textcoords="offset points", xytext=(8, 5),
                        fontsize=8, color=GOLD)
        else:
            ax.scatter(conv, m_obs, s=150, color=color,
                       edgecolors=WHITE, linewidths=0.5, zorder=3)
            ax.annotate(name.replace("_", " "), (conv, m_obs),
                        textcoords="offset points", xytext=(8, 5),
                        fontsize=8, color=WHITE)

    # Gate line
    ax.axvline(x=0.90, color=SCARLET, linestyle="--", alpha=0.5, linewidth=1.5)
    ax.text(0.92, 5.5, "TACHOCLINE\nGATE", fontsize=9, color=SCARLET,
            ha="left", va="center", alpha=0.7)
    ax.text(0.95, 1.2, "m=1\nceiling", fontsize=8, color=CYAN,
            ha="center", va="center", alpha=0.7)

    # Shaded region for fully convective
    ax.axvspan(0.88, 1.02, alpha=0.08, color=CYAN)

    ax.set_xlabel("Convection Zone Depth Fraction", color=WHITE, fontsize=11)
    ax.set_ylabel("Observed Mode m", color=WHITE, fontsize=11)
    ax.set_title("BCM TACHOCLINE GATE -- Convection Depth vs Substrate Mode",
                 color=WHITE, fontsize=13, fontweight="bold")
    ax.set_xlim(-0.02, 1.08)
    ax.set_ylim(0, 7)

    ax.tick_params(colors=DIM)
    ax.spines["bottom"].set_color(DIM)
    ax.spines["left"].set_color(DIM)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if save_path is None:
        save_path = os.path.join(_get_results_dir(),
                                 "BCM_tachocline_gate.png")
    fig.savefig(save_path, dpi=150, facecolor=BG_DARK,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")
    return save_path


# ─────────────────────────────────────────
# PANEL 4: J_IND LANDSCAPE
# ─────────────────────────────────────────

def render_j_landscape(registry=None, save_path=None):
    """
    Horizontal bar chart of J_ind across all stars.
    Color by BCM class. Log scale.
    """
    reg = registry or _load_overrides_registry()

    names = []
    j_vals = []
    colors = []
    for name, params in reg.items():
        derived = compute_stellar_params(name, params)
        names.append(name.replace("_", " "))
        j_vals.append(derived["J_ind_SI"])
        cls_key = _class_key(params.get("bcm_class", ""))
        colors.append(CLASS_COLORS.get(cls_key, DIM))

    # Sort by J_ind
    order = np.argsort(j_vals)
    names = [names[i] for i in order]
    j_vals = [j_vals[i] for i in order]
    colors = [colors[i] for i in order]

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), facecolor=BG_DARK)
    ax.set_facecolor(BG_PANEL)

    y_pos = range(len(names))
    ax.barh(y_pos, j_vals, color=colors, edgecolor=BG_DARK, linewidth=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=9, color=WHITE)
    ax.set_xscale("log")
    ax.set_xlabel("Induction Current J_ind (A/m\u00b2)", color=WHITE, fontsize=11)
    ax.set_title("BCM STELLAR INDUCTION LANDSCAPE",
                 color=WHITE, fontsize=13, fontweight="bold")

    ax.tick_params(colors=DIM)
    ax.spines["bottom"].set_color(DIM)
    ax.spines["left"].set_color(DIM)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add J values as text
    for i, (j, c) in enumerate(zip(j_vals, colors)):
        ax.text(j * 1.3, i, f"{j:.2e}", fontsize=7,
                color=c, va="center")

    if save_path is None:
        save_path = os.path.join(_get_results_dir(),
                                 "BCM_stellar_j_landscape.png")
    fig.savefig(save_path, dpi=150, facecolor=BG_DARK,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")
    return save_path


# ─────────────────────────────────────────
# PANEL 5: LAMBDA SCALE COMPARISON
# ─────────────────────────────────────────

def render_lambda_scale(registry=None, save_path=None):
    """
    Lambda ratio plot across galactic, planetary, and stellar scales.
    Shows scale invariance visually.
    """
    reg = registry or _load_overrides_registry()

    fig, ax = plt.subplots(1, 1, figsize=(10, 5), facecolor=BG_DARK)
    ax.set_facecolor(BG_PANEL)

    # Galactic and planetary baselines
    ax.axhline(y=1.0, color=EMERALD, linestyle="-", alpha=0.3,
               linewidth=2, label="Perfect scale invariance")
    ax.axhspan(0.5, 2.0, alpha=0.05, color=EMERALD)

    # Galactic
    ax.scatter([0], [1.0], s=200, color=EMERALD, marker="D",
               edgecolors=WHITE, linewidths=1, zorder=4)
    ax.annotate("Galactic\n(175 galaxies)\n\u03bb=0.100",
                (0, 1.0), textcoords="offset points", xytext=(0, -40),
                fontsize=8, color=EMERALD, ha="center")

    # Planetary
    ratio_plan = LAM_PLANETARY / LAM_GALACTIC
    ax.scatter([1], [ratio_plan], s=200, color=BLUE, marker="s",
               edgecolors=WHITE, linewidths=1, zorder=4)
    ax.annotate(f"Planetary\n(8 planets)\n\u03bb={LAM_PLANETARY:.3f}\nratio={ratio_plan:.2f}",
                (1, ratio_plan), textcoords="offset points", xytext=(0, -50),
                fontsize=8, color=BLUE, ha="center")

    # Stellar — individual stars
    x_stellar = 2
    stellar_ratios = []
    for name, params in reg.items():
        derived = compute_stellar_params(name, params)
        m_obs = params.get("m_observed", 0)
        if m_obs <= 0:
            continue
        from BCM_stellar_wave import solve_lambda_stellar
        lam, ratio = solve_lambda_stellar(name, params, derived)
        if ratio is not None:
            stellar_ratios.append((name, ratio))
            cls_key = _class_key(params.get("bcm_class", ""))
            color = CLASS_COLORS.get(cls_key, DIM)
            ax.scatter([x_stellar], [ratio], s=80, color=color,
                       edgecolors=WHITE, linewidths=0.5, zorder=3)
            ax.annotate(name.replace("_", " "),
                        (x_stellar, ratio),
                        textcoords="offset points",
                        xytext=(10, 0), fontsize=7, color=DIM)

    if stellar_ratios:
        avg = np.mean([r for _, r in stellar_ratios])
        ax.scatter([x_stellar], [avg], s=200, color=GOLD, marker="*",
                   edgecolors=WHITE, linewidths=1, zorder=5)
        ax.annotate(f"Stellar avg\nratio={avg:.3f}",
                    (x_stellar, avg), textcoords="offset points",
                    xytext=(-50, 15), fontsize=9, color=GOLD,
                    fontweight="bold")

    ax.set_xlim(-0.5, 3)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["Galactic", "Planetary", "Stellar"],
                        fontsize=11, color=WHITE)
    ax.set_ylabel("\u03bb ratio (scale / galactic)", color=WHITE, fontsize=11)
    ax.set_title("BCM SCALE INVARIANCE -- \u03bb Across Three Scales",
                 color=WHITE, fontsize=13, fontweight="bold")
    ax.text(1.0, 2.1, "SCALE INVARIANT BAND (0.5 - 2.0)",
            fontsize=8, color=EMERALD, ha="center", alpha=0.5)

    ax.tick_params(colors=DIM)
    ax.spines["bottom"].set_color(DIM)
    ax.spines["left"].set_color(DIM)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if save_path is None:
        save_path = os.path.join(_get_results_dir(),
                                 "BCM_lambda_scale.png")
    fig.savefig(save_path, dpi=150, facecolor=BG_DARK,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")
    return save_path


# ─────────────────────────────────────────
# PANEL 6: COMBINED ARMS TABLE
# ─────────────────────────────────────────

def render_combined_arms_table(registry=None, save_path=None):
    """
    Summary table: galaxy class, stellar analog, match status.
    Rendered as figure for publication.
    """
    reg = registry or _load_overrides_registry()

    from BCM_stellar_overrides import STELLAR_CLASS_MAP

    fig, ax = plt.subplots(1, 1, figsize=(14, 6), facecolor=BG_DARK)
    ax.set_facecolor(BG_DARK)
    ax.axis("off")

    # Table data
    headers = ["BCM Class", "Galaxy Example", "Stellar Analogs",
               "m Range", "Tachocline", "Status"]
    galaxy_examples = {
        "I": "NGC2841", "II": "UGC04305", "III": "Various",
        "IV": "NGC0801", "V-A": "NGC2976", "VI": "NGC3953",
        "?": "Anomalous",
    }

    rows = []
    for cls, star_list in STELLAR_CLASS_MAP.items():
        gal = galaxy_examples.get(cls, "--")
        m_vals = []
        tach_status = set()
        for s in star_list:
            p = reg.get(s, {})
            m = p.get("m_observed", 0)
            if m > 0:
                m_vals.append(str(m))
            else:
                m_vals.append("?")
            cd = p.get("conv_depth_frac", 0.3)
            tach_status.add("NO" if cd >= 0.9 else "YES" if cd > 0.05 else "MINIMAL")

        stars_str = ", ".join([s.replace("_", " ") for s in star_list])
        m_str = ", ".join(m_vals)
        tach_str = "/".join(sorted(tach_status))

        # Match count
        matched = 0
        total = 0
        for s in star_list:
            p = reg.get(s, {})
            m_obs = p.get("m_observed", 0)
            if m_obs > 0:
                total += 1
                d = compute_stellar_params(s, p)
                if d["m_predicted"] == m_obs:
                    matched += 1

        status = f"{matched}/{total}" if total > 0 else "N/A"
        rows.append([f"Class {cls}", gal, stars_str, m_str, tach_str, status])

    table = ax.table(cellText=rows, colLabels=headers,
                     cellLoc="center", loc="center",
                     colWidths=[0.10, 0.10, 0.30, 0.10, 0.10, 0.08])

    # Style
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.6)

    for (r, c), cell in table.get_celld().items():
        cell.set_facecolor(BG_PANEL)
        cell.set_edgecolor(DIM)
        if r == 0:
            cell.set_facecolor("#1a1e2a")
            cell.set_text_props(color=GOLD, fontweight="bold")
        else:
            cls_str = rows[r-1][0].replace("Class ", "")
            color = CLASS_COLORS.get(cls_str, DIM)
            if c == 0:
                cell.set_text_props(color=color, fontweight="bold")
            else:
                cell.set_text_props(color=WHITE)

    ax.set_title("BCM COMBINED ARMS -- Galaxy Class \u2194 Stellar Analog",
                 color=WHITE, fontsize=14, fontweight="bold", pad=20)

    if save_path is None:
        save_path = os.path.join(_get_results_dir(),
                                 "BCM_combined_arms_table.png")
    fig.savefig(save_path, dpi=150, facecolor=BG_DARK,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")
    return save_path


# ─────────────────────────────────────────
# PANEL 7: m COMPARISON — Hamiltonian vs Rossby vs Observed
# ─────────────────────────────────────────

def render_m_comparison(registry=None, save_path=None):
    """
    Side-by-side: Hamiltonian m_pred vs observed, Rossby m_pred vs observed.
    Shows why resonance Hamiltonian dominates Rossby estimate.
    Stars with m_observed=0 are excluded (no ground truth).
    """
    reg = registry or _load_overrides_registry()

    # Collect stars with m_observed > 0
    names, m_obs_list, m_H_list, m_Ro_list, cls_list = [], [], [], [], []
    for star_name, params in reg.items():
        m_obs = params.get("m_observed", 0)
        if m_obs <= 0:
            continue
        derived = compute_stellar_params(star_name, params)
        names.append(star_name)
        m_obs_list.append(m_obs)
        m_H_list.append(derived["m_predicted"])
        m_Ro_list.append(round(derived["m_rossby"]))
        cls_list.append(_class_key(params.get("bcm_class", "?")))

    n = len(names)
    if n == 0:
        print("  SKIP: No stars with m_observed > 0")
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG_DARK)

    x = np.arange(n)
    bar_w = 0.35

    for ax, m_pred_list, title_label, pred_color in [
        (ax1, m_H_list, "Hamiltonian H(m)", EMERALD),
        (ax2, m_Ro_list, "Rossby m = R/L_R", SCARLET),
    ]:
        ax.set_facecolor(BG_PANEL)

        # Observed bars
        bars_obs = ax.bar(x - bar_w/2, m_obs_list, bar_w,
                          color=BLUE, edgecolor="#1a1a2e", label="Observed")
        # Predicted bars
        bars_pred = ax.bar(x + bar_w/2, m_pred_list, bar_w,
                           color=pred_color, edgecolor="#1a1a2e", label=title_label)

        # Match markers
        matches = sum(1 for o, p in zip(m_obs_list, m_pred_list) if o == p)
        ax.set_title(f"{title_label}  ({matches}/{n} match)",
                     color=WHITE, fontsize=12, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha="right", color=WHITE, fontsize=8)
        ax.set_ylabel("Mode m", color=WHITE, fontsize=10)
        ax.tick_params(colors=DIM)
        ax.spines["bottom"].set_color(DIM)
        ax.spines["left"].set_color(DIM)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # 1:1 reference line
        max_m = max(max(m_obs_list), max(m_pred_list)) + 1
        ax.set_ylim(0, max_m)

        ax.legend(loc="upper right",
                  facecolor=BG_PANEL, edgecolor=DIM, labelcolor=WHITE)

    fig.suptitle("BCM STELLAR MODE PREDICTION — Hamiltonian vs Rossby",
                 color=WHITE, fontsize=14, fontweight="bold", y=1.02)

    plt.tight_layout()

    if save_path is None:
        save_path = os.path.join(_get_results_dir(),
                                 "BCM_stellar_m_comparison.png")
    fig.savefig(save_path, dpi=150, facecolor=BG_DARK,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")
    return save_path


# ─────────────────────────────────────────
# MAIN — RENDER ALL
# ─────────────────────────────────────────

def render_all(registry=None):
    """Generate all panels."""
    reg = registry or _load_overrides_registry()
    results_dir = _get_results_dir()

    print(f"\n{'='*65}")
    print(f"  BCM STELLAR RENDERER -- Generating All Panels")
    print(f"{'='*65}\n")

    paths = []

    # Gallery
    p = render_gallery(reg)
    paths.append(p)

    # Tachocline gate
    p = render_tachocline_gate(reg)
    paths.append(p)

    # J landscape
    p = render_j_landscape(reg)
    paths.append(p)

    # Lambda scale
    p = render_lambda_scale(reg)
    paths.append(p)

    # Combined arms table
    try:
        p = render_combined_arms_table(reg)
        paths.append(p)
    except ImportError:
        print("  SKIP: Combined arms table requires BCM_stellar_overrides.py")

    # m comparison (Hamiltonian vs Rossby)
    p = render_m_comparison(reg)
    if p:
        paths.append(p)

    # Individual spectra for key stars
    key_stars = ["Sun", "Proxima", "Betelgeuse", "V374_Peg", "AB_Dor"]
    for star_name in key_stars:
        if star_name in reg:
            p = render_spectrum(star_name, reg[star_name])
            paths.append(p)

    print(f"\n  {'='*65}")
    print(f"  Done. {len(paths)} images generated.")
    print(f"  {'='*65}\n")
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM Stellar Renderer -- publication figures")
    parser.add_argument("--star", type=str, default=None,
                        help="Render spectrum for single star")
    parser.add_argument("--gallery", action="store_true",
                        help="Render star gallery only")
    parser.add_argument("--gate", action="store_true",
                        help="Render tachocline gate diagram only")
    parser.add_argument("--landscape", action="store_true",
                        help="Render J_ind landscape only")
    parser.add_argument("--lambda-scale", action="store_true",
                        help="Render lambda scale comparison only")
    parser.add_argument("--m-compare", action="store_true",
                        help="Render m_comparison plot (Hamiltonian vs Rossby)")
    parser.add_argument("--all", action="store_true",
                        help="Render all panels")
    args = parser.parse_args()

    reg = _load_overrides_registry()

    if args.star:
        if args.star in reg:
            render_spectrum(args.star, reg[args.star])
        else:
            print(f"Star '{args.star}' not found. Available: {list(reg.keys())}")
    elif args.gallery:
        render_gallery(reg)
    elif args.gate:
        render_tachocline_gate(reg)
    elif args.landscape:
        render_j_landscape(reg)
    elif args.lambda_scale:
        render_lambda_scale(reg)
    elif args.m_compare:
        render_m_comparison(reg)
    elif args.all:
        render_all(reg)
    else:
        render_all(reg)
