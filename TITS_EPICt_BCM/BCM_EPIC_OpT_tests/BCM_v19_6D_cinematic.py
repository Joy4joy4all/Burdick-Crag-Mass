# -*- coding: utf-8 -*-
"""
BCM v19 -- 6D Field Shape Cinematic (Instrument Grade)
=========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

12 slides showing the 6D field shape during corridor
transit through the Bootes Void with 60 dead galaxies.

Instrument-grade upgrades:
  - Harmonic field shape (phase-driven, not ellipse)
  - Probe resonance visualization (phase-lit probes)
  - Graveyard coupling distortion (field pulled toward grave)
  - Chi absorption flow (inward flux, not static rings)
  - Wake = temporal decay trail (motion history)
  - Smooth background (imshow gradient, no banding)
  - HUD with derived metrics (phase offset, grad lambda)
  - Optional JSON replay from graveyard stress log

The 6D field shape is the total blast pattern of the
craft moving at velocity against the 2D substrate. It
deforms on turns, bloats in graveyards, stretches on
acceleration. Any excessive deformation registers as
stress on the 5D gauge and is felt by the crew as
vibration.

Usage:
    python BCM_v19_6D_cinematic.py
    python BCM_v19_6D_cinematic.py --save
    python BCM_v19_6D_cinematic.py --json data/results/BCM_v19_graveyard_stress_*.json
"""

import numpy as np
import os
import time
import math
import argparse
import json
import glob


# ---- COLOR PALETTE ----
BG         = '#050810'
CRAFT_A    = '#40ee70'
CRAFT_B    = '#40ccaa'
PROBE_BLUE = '#60aaff'
CHI_PURPLE = '#aa44ff'
GRAVE_RED  = '#ff4444'
GOLD       = '#ffbb44'
GREEN_ZONE = '#30ff60'
ORANGE_ZONE= '#ff9944'
RED_ZONE   = '#ff4444'
DIM        = '#3a4a60'
WHITE      = '#e0e8f0'
TEAL       = '#40ccaa'
FIELD_EDGE = '#30aa60'


def load_flight_log(json_path):
    """Load graveyard stress or corridor flight JSON."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    # Try flight_log key first (corridor flight)
    if "flight_log" in data:
        return data["flight_log"]
    # Try grave_events
    if "grave_events" in data:
        return data["grave_events"]
    return None


def extract_slide_from_log(entry):
    """Convert a flight log entry into slide parameters."""
    lam = entry.get("lambda", 0.03)
    bruce = entry.get("bruce_rms", 0.005)
    phi = entry.get("phi_rms", 0.002)
    chi = entry.get("chi_total", 500) / 2000.0
    chi = min(1.0, max(0.0, chi))
    zone = entry.get("zone", "GREEN")
    phase = entry.get("phase", "CORRIDOR")
    baume = entry.get("baume", 0.20)
    step = entry.get("step", 0)

    is_grave = "GRAVE" in str(phase).upper()

    return {
        "title": f"STEP {step} -- {phase}",
        "subtitle": f"Lambda={lam:.3f}  BruceRMS={bruce:.5f}  Zone={zone}",
        "phase": "graveyard" if is_grave else "corridor",
        "craft_x": 0.50,
        "lambda_bg": lam,
        "chi_level": chi,
        "bruce_rms": bruce,
        "phi_rms": phi,
        "baume": baume,
        "zone": zone,
        "step": step,
        "label": (f"Lambda: {lam:.4f}  Bruce RMS: {bruce:.6f}\n"
                  f"Phi RMS: {phi:.6f}  Chi: {chi:.3f}\n"
                  f"Baume: {baume:.4f}  Zone: {zone}"),
    }


def default_slides():
    """12 narrative slides for standalone mode."""
    return [
        {
            "title": "DEPARTURE -- 6D Field Shape Clean",
            "subtitle": "Craft enters GREEN corridor. All systems nominal.",
            "phase": "departure", "craft_x": 0.50,
            "lambda_bg": 0.03, "chi_level": 0.05,
            "bruce_rms": 0.002, "phi_rms": 0.001,
            "baume": 0.15, "zone": "GREEN", "step": 0,
            "label": "6D field shape: craft + wake + 12 probe\n"
                     "causeways + chi overflow. Clean torus.\n"
                     "kappa_drain=0.35  chi_decay=0.997",
        },
        {
            "title": "DUAL SIGMA -- Two Rivers Flow",
            "subtitle": "Substrate sigma (ocean) and orbital sigma (probes).",
            "phase": "corridor", "craft_x": 0.50,
            "lambda_bg": 0.04, "chi_level": 0.10,
            "bruce_rms": 0.004, "phi_rms": 0.002,
            "baume": 0.22, "zone": "GREEN", "step": 2000,
            "label": "Substrate sigma: the 2D ocean.\n"
                     "Orbital sigma: probe payloads cycling\n"
                     "in the Venturi tunnel. Two streams.",
        },
        {
            "title": "BLOW VALVE -- kappa_drain at B1/B2",
            "subtitle": "35% orbital sigma bled at each deposit boundary.",
            "phase": "blow_valve", "craft_x": 0.50,
            "lambda_bg": 0.04, "chi_level": 0.15,
            "bruce_rms": 0.005, "phi_rms": 0.002,
            "baume": 0.25, "zone": "GREEN", "step": 3000,
            "label": "Shives dissolve before entering Brucetron\n"
                     "memory. The blow line stays quiet.\n"
                     "Drain at the source, not the field.",
        },
        {
            "title": "RECOVERY BOILER -- Chi Absorbs Residual",
            "subtitle": "Bled sigma routed to 4D headspace. Baume burns.",
            "phase": "recovery", "craft_x": 0.50,
            "lambda_bg": 0.05, "chi_level": 0.35,
            "bruce_rms": 0.005, "phi_rms": 0.001,
            "baume": 0.20, "zone": "GREEN", "step": 4000,
            "label": "Chi freeboard captures bled orbital sigma.\n"
                     "Decays at 0.997/step (controlled burn).\n"
                     "No mass lost. No uncontrolled contrail.",
        },
        {
            "title": "DEEP VOID -- 6D Shape Stretches",
            "subtitle": "Maximum isolation. Lambda at corridor ceiling.",
            "phase": "deep_void", "craft_x": 0.50,
            "lambda_bg": 0.06, "chi_level": 0.45,
            "bruce_rms": 0.006, "phi_rms": 0.002,
            "baume": 0.12, "zone": "GREEN", "step": 6000,
            "label": "6D field shape elongates in direction\n"
                     "of travel. Wake trail visible behind.\n"
                     "Probe causeways write D_f=1.59 boundary.",
        },
        {
            "title": "GRAVEYARD HIT -- Dormant Galaxy Re-Excites",
            "subtitle": "Lambda drops to 0.008. Dormant substrate stirs.",
            "phase": "graveyard", "craft_x": 0.50,
            "lambda_bg": 0.008, "chi_level": 0.55,
            "bruce_rms": 0.009, "phi_rms": 0.003,
            "baume": 0.45, "zone": "YELLOW", "step": 8500,
            "label": "Dead galaxy substrate re-excites when\n"
                     "craft pumps agitate dormant memory.\n"
                     "6D shape bloats. Baume spikes.",
        },
        {
            "title": "PHASE SPIKE -- B1 Arc Entry Resonance",
            "subtitle": "Probe_phase 5-14: worst Brucetron window.",
            "phase": "phase_spike", "craft_x": 0.50,
            "lambda_bg": 0.008, "chi_level": 0.58,
            "bruce_rms": 0.0095, "phi_rms": 0.003,
            "baume": 0.50, "zone": "YELLOW", "step": 8700,
            "label": "Spikes correlate with probe cycle phase,\n"
                     "not raw density. Constructive interference\n"
                     "at geometry discontinuity B1 (step 5).",
        },
        {
            "title": "BOILER ABSORBS -- Graveyard Slosh Captured",
            "subtitle": "Chi routes re-agitation sigma to 4D headspace.",
            "phase": "recovery", "craft_x": 0.50,
            "lambda_bg": 0.03, "chi_level": 0.60,
            "bruce_rms": 0.006, "phi_rms": 0.002,
            "baume": 0.30, "zone": "GREEN", "step": 10000,
            "label": "Graveyard sigma slosh captured by chi.\n"
                     "System total +0.7% across 60 zones.\n"
                     "Conservation closed.",
        },
        {
            "title": "HEARTBEAT -- f/2 Steady Tone",
            "subtitle": "One steady hum = machine running. Crew safe.",
            "phase": "heartbeat", "craft_x": 0.50,
            "lambda_bg": 0.05, "chi_level": 0.45,
            "bruce_rms": 0.005, "phi_rms": 0.0014,
            "baume": 0.18, "zone": "GREEN", "step": 12000,
            "label": "f/2 = 0.010 cycles/step. Eigenmode.\n"
                     "Dead silence = machine stopped.\n"
                     "Multiple tones = hemorrhage.\n"
                     "One hum = safe.",
        },
        {
            "title": "GREEN CORRIDOR -- Operating Envelope",
            "subtitle": "Lambda [0.02-0.08]. Continuous flyable band.",
            "phase": "corridor_map", "craft_x": 0.50,
            "lambda_bg": 0.04, "chi_level": 0.35,
            "bruce_rms": 0.004, "phi_rms": 0.001,
            "baume": 0.20, "zone": "GREEN", "step": 14000,
            "label": "Four consecutive GREEN densities.\n"
                     "No ORANGE gap. Recovery boiler filled it.\n"
                     "The craft holds one wide corridor.",
        },
        {
            "title": "60 CLEARED -- All Graveyards Passed",
            "subtitle": "60/60 dead galaxies. Zero crew violations.",
            "phase": "cleared", "craft_x": 0.50,
            "lambda_bg": 0.03, "chi_level": 0.25,
            "bruce_rms": 0.005, "phi_rms": 0.001,
            "baume": 0.15, "zone": "GREEN", "step": 18000,
            "label": "Max BruceRMS: 0.00949 (21% headroom).\n"
                     "Phase resonance at B1 entry.\n"
                     "The dormant ocean stirred. Ship held.",
        },
        {
            "title": "GO FOR TRANSIT -- 6D Field Intact",
            "subtitle": "Mission complete. Crew safe. Constants held.",
            "phase": "arrival", "craft_x": 0.50,
            "lambda_bg": 0.03, "chi_level": 0.15,
            "bruce_rms": 0.003, "phi_rms": 0.001,
            "baume": 0.12, "zone": "GREEN", "step": 20000,
            "label": "20,000 steps. 83.2% GREEN. 0 violations.\n"
                     "Conservation closed. Heartbeat steady.\n"
                     "The Formers set the constants.\n"
                     "The Dark Mason flew the ship.",
        },
    ]


def build_cinematic(save_slides=False, json_path=None):
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    base = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(base, "data", "images")
    os.makedirs(img_dir, exist_ok=True)

    # Load data or use defaults
    slides = None
    if json_path:
        log = load_flight_log(json_path)
        if log and len(log) >= 12:
            indices = np.linspace(0, len(log)-1, 12).astype(int)
            slides = [extract_slide_from_log(log[i])
                      for i in indices]
            print(f"  Loaded {len(log)} entries from JSON")
            print(f"  Sampling 12 slides at key moments")

    if slides is None:
        slides = default_slides()
        print(f"  Using default narrative slides")

    print(f"\n{'='*60}")
    print(f"  BCM v19 -- 6D FIELD SHAPE CINEMATIC")
    print(f"  Instrument-Grade Visualization")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*60}")

    rng = np.random.RandomState(42)

    for si, s in enumerate(slides):
        fig, ax = plt.subplots(1, 1, figsize=(16, 9),
                               facecolor=BG)
        ax.set_facecolor(BG)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.axis('off')

        cx = s.get("craft_x", 0.50)
        cy = 0.50
        lam_bg = s["lambda_bg"]
        phase_offset = si * 0.4

        # ---- SMOOTH BACKGROUND (imshow, no banding) ----
        gx = np.linspace(0, 1, 400)
        gy = np.linspace(0, 1, 400)
        GX, GY = np.meshgrid(gx, gy)
        field_bg = lam_bg + 0.04 * np.sqrt(
            (GX - cx)**2 + (GY - cy)**2)
        ax.imshow(field_bg, extent=[0, 1, 0, 1],
                  origin='lower', cmap='magma',
                  alpha=0.20, aspect='auto')

        # ---- HARMONIC FIELD SHAPE (mode, not ellipse) ----
        theta = np.linspace(0, 2*np.pi, 300)
        r0 = 0.12
        r = r0 * (
            1.0
            + 0.6 * s["bruce_rms"] * 80 * np.cos(
                theta - phase_offset)
            + 0.3 * s["chi_level"] * np.sin(2 * theta)
            + 0.15 * s["chi_level"] * np.cos(3 * theta
                                               + phase_offset)
        )
        # Wake asymmetry (longer behind)
        r = np.where(np.cos(theta) < 0, r * 1.6, r)

        bx = cx + r * np.cos(theta)
        by = cy + r * np.sin(theta)

        # ---- GRAVEYARD DISTORTION (field pulled) ----
        is_grave = s.get("phase", "") in (
            "graveyard", "phase_spike")
        grave_x = cx + 0.18
        if is_grave and lam_bg < 0.02:
            dist = np.sqrt((bx - grave_x)**2 +
                           (by - cy)**2)
            pull = np.exp(-dist * 12) * 0.5
            bx -= pull * (bx - grave_x)
            by -= pull * (by - cy)

            # Grave marker with ripples
            ax.add_patch(Circle((grave_x, cy), 0.05,
                                fill=True,
                                facecolor='#180404',
                                edgecolor=GRAVE_RED,
                                linewidth=1,
                                linestyle='--',
                                alpha=0.5))
            ax.text(grave_x, cy, 'DORMANT',
                    ha='center', va='center',
                    fontsize=7, color=GRAVE_RED,
                    alpha=0.6)
            for rr in [0.06, 0.08, 0.10, 0.12]:
                ax.add_patch(Circle((grave_x, cy), rr,
                                    fill=False,
                                    edgecolor='#ff6644',
                                    linewidth=0.4,
                                    alpha=0.12))

        # ---- 6D FIELD GLOW (layered additive) ----
        for k in range(6, 0, -1):
            scale = 1.0 + k * 0.12
            fx = cx + (bx - cx) * scale
            fy = cy + (by - cy) * scale
            alpha_f = 0.025 + 0.015 * (6 - k) / 6
            ax.fill(fx, fy, color=TEAL, alpha=alpha_f)

        # Field boundary
        ax.plot(bx, by, color=FIELD_EDGE, linewidth=1.2,
                alpha=0.55, linestyle='-')

        # ---- WAKE TEMPORAL DECAY TRAIL ----
        for w in range(25):
            trail_x = cx - w * 0.012
            trail_alpha = 0.10 * (1 - w / 25)
            trail_r = 0.07 * (1 - w / 30)
            if trail_r > 0.005:
                ax.add_patch(Circle(
                    (trail_x, cy), trail_r,
                    fill=True, facecolor=TEAL,
                    alpha=trail_alpha, linewidth=0))

        # ---- PROBE RESONANCE (phase-lit) ----
        phase = (si * 0.5) % (2 * math.pi)
        sep = 0.04
        ax_pos = cx + sep * 0.6

        for pid in range(12):
            p_angle = pid * (2 * math.pi / 12)
            intensity = max(0, math.cos(phase - p_angle))
            pr = 0.08 + 0.06 * rng.random()
            px = ax_pos + pr * math.cos(p_angle)
            py = cy + pr * 0.8 * math.sin(p_angle)

            if 0.02 < px < 0.98 and 0.05 < py < 0.95:
                ax.plot([ax_pos, px], [cy, py],
                        color=PROBE_BLUE,
                        linewidth=0.5 + intensity * 1.5,
                        alpha=0.10 + 0.55 * intensity)
                ax.plot(px, py, 'o', color=PROBE_BLUE,
                        markersize=2 + intensity * 3,
                        alpha=0.3 + 0.5 * intensity)

        # ---- CHI ABSORPTION FLOW (inward flux) ----
        chi_lev = s["chi_level"]
        n_chi = int(20 + chi_lev * 30)
        for _ in range(n_chi):
            a = rng.random() * 2 * math.pi
            rad = rng.random() * 0.14
            x0 = cx + rad * math.cos(a)
            y0 = cy + rad * math.sin(a)
            ax.plot([x0, cx], [y0, cy],
                    color=CHI_PURPLE,
                    alpha=0.03 + 0.12 * chi_lev,
                    linewidth=0.4)

        # ---- CRAFT (dumbbell) ----
        pump_a_r = 0.014
        pump_b_r = 0.006
        bx_pos = cx - sep * 0.4

        pa = Circle((ax_pos, cy), pump_a_r, fill=True,
                     facecolor='#0a1a0e', edgecolor=CRAFT_A,
                     linewidth=2, alpha=0.9)
        ax.add_patch(pa)
        ax.text(ax_pos, cy, 'A', ha='center', va='center',
                fontsize=7, fontweight='bold', color=WHITE)

        pb = Circle((bx_pos, cy), pump_b_r, fill=True,
                     facecolor='#081015', edgecolor=CRAFT_B,
                     linewidth=1.5, alpha=0.9)
        ax.add_patch(pb)
        ax.text(bx_pos, cy, 'B', ha='center', va='center',
                fontsize=5, color=WHITE)

        # Venturi tunnel
        ax.plot([bx_pos + pump_b_r, ax_pos - pump_a_r],
                [cy - 0.003, cy - 0.001],
                color=DIM, linewidth=0.6)
        ax.plot([bx_pos + pump_b_r, ax_pos - pump_a_r],
                [cy + 0.003, cy + 0.001],
                color=DIM, linewidth=0.6)

        # ---- BLOW VALVE indicator ----
        if s.get("phase") == "blow_valve":
            for dy in [-0.025, 0.025]:
                ax.annotate('',
                            xy=(bx_pos - 0.04, cy + dy),
                            xytext=(bx_pos, cy + dy * 0.3),
                            arrowprops=dict(
                                arrowstyle='->', color=GOLD,
                                lw=1.5))
            ax.text(bx_pos - 0.06, cy, 'BLEED\n35%',
                    ha='center', fontsize=7, color=GOLD,
                    alpha=0.8)

        # ---- PHASE SPIKE indicator ----
        if s.get("phase") == "phase_spike":
            ax.text(ax_pos + 0.03, cy + 0.04,
                    'B1 SPIKE\nphase 5-14',
                    ha='center', fontsize=9, color=GOLD,
                    alpha=0.9, fontweight='bold')
            ax.annotate('',
                        xy=(ax_pos + pump_a_r + 0.005, cy),
                        xytext=(ax_pos + 0.04, cy + 0.03),
                        arrowprops=dict(arrowstyle='->',
                                        color=GOLD, lw=1.5))

        # ---- HEARTBEAT waveform ----
        if s.get("phase") == "heartbeat":
            wave_x = np.linspace(0.08, 0.42, 300)
            wave_y = 0.84 + 0.025 * np.sin(
                2 * np.pi * wave_x * 25)
            ax.plot(wave_x, wave_y, color=GREEN_ZONE,
                    linewidth=1.8, alpha=0.6)
            ax.text(0.25, 0.89, 'f/2 = 0.010  STEADY TONE',
                    ha='center', fontsize=10,
                    color=GREEN_ZONE, alpha=0.7,
                    fontweight='bold')

        # ---- CORRIDOR ENVELOPE ----
        if s.get("phase") == "corridor_map":
            ey_top = 0.83; ey_bot = 0.72
            ax.fill_between([0.10, 0.90], ey_bot, ey_top,
                            color='#0a200e', alpha=0.5)
            ax.plot([0.10, 0.90], [ey_top, ey_top],
                    color=GREEN_ZONE, linewidth=1, alpha=0.6)
            ax.plot([0.10, 0.90], [ey_bot, ey_bot],
                    color=GREEN_ZONE, linewidth=1, alpha=0.6)
            ax.text(0.50, ey_top + 0.02,
                    'GREEN CORRIDOR: \u03bb [0.02 \u2013 0.08]',
                    ha='center', fontsize=10,
                    color=GREEN_ZONE, alpha=0.8,
                    fontweight='bold')
            for lv, lbl in [(0.20, '0.02'), (0.40, '0.04'),
                            (0.60, '0.06'), (0.80, '0.08')]:
                ax.plot([lv, lv], [ey_bot, ey_top],
                        color=DIM, linewidth=0.5, alpha=0.3)
                ax.text(lv, ey_bot - 0.02, lbl,
                        ha='center', fontsize=7, color=DIM)

        # ---- 60 CLEARED ----
        if s.get("phase") == "cleared":
            ax.text(0.50, 0.84,
                    '60 / 60 GRAVEYARDS CLEARED',
                    ha='center', fontsize=16,
                    fontweight='bold', color=GREEN_ZONE,
                    alpha=0.9)
            ax.text(0.50, 0.78,
                    'ZERO CREW VIOLATIONS',
                    ha='center', fontsize=12,
                    color=GREEN_ZONE, alpha=0.7)

        # ---- HUD (instrument grade) ----
        zone = s["zone"]
        zone_col = (GREEN_ZONE if zone == "GREEN"
                    else GOLD if zone == "YELLOW"
                    else RED_ZONE)

        ax.text(0.98, 0.96, zone, ha='right', va='top',
                fontsize=22, fontweight='bold',
                color=zone_col, alpha=0.85,
                transform=ax.transAxes)

        lambda_grad = abs(lam_bg - 0.05)
        phi_rms = s.get("phi_rms", 0.001)

        hud = (
            f"LAMBDA:      {lam_bg:.4f}\n"
            f"BRUCE RMS:   {s['bruce_rms']:.5f}\n"
            f"PHI RMS:     {phi_rms:.5f}\n"
            f"CHI LEVEL:   {chi_lev:.3f}\n"
            f"BAUME:       {s['baume']:.3f}\n"
            f"\u0394PHASE:      {phase_offset:.2f}\n"
            f"\u2207\u03bb:         {lambda_grad:.4f}\n"
            f"KAPPA_DRAIN: 0.35\n"
            f"CHI_DECAY:   0.997\n"
            f"PROBES:      12 ACTIVE"
        )
        ax.text(0.98, 0.04, hud, ha='right', va='bottom',
                fontsize=8, color='#80c0ff', alpha=0.6,
                family='monospace', transform=ax.transAxes,
                bbox=dict(boxstyle='round,pad=0.5',
                          facecolor='#060a14',
                          edgecolor='#203050', alpha=0.75))

        # Title block
        ax.text(0.02, 0.96,
                f"SLIDE {si+1}/12",
                ha='left', va='top', fontsize=10,
                color='#6a7a90', family='monospace',
                transform=ax.transAxes)
        ax.text(0.02, 0.91,
                s["title"],
                ha='left', va='top', fontsize=16,
                fontweight='bold', color='#d0e8ff',
                family='sans-serif',
                transform=ax.transAxes)
        ax.text(0.02, 0.86,
                s["subtitle"],
                ha='left', va='top', fontsize=10,
                color='#8090a8', family='sans-serif',
                transform=ax.transAxes)

        # Description
        ax.text(0.02, 0.04,
                s["label"],
                ha='left', va='bottom', fontsize=9,
                color='#60c080', family='monospace',
                transform=ax.transAxes,
                bbox=dict(boxstyle='round,pad=0.5',
                          facecolor='#060a14',
                          edgecolor='#203050', alpha=0.75))

        # Watermark
        ax.text(0.50, 0.008,
                "BCM v19 | 6D Field Shape | "
                "Emerald Entities LLC \u2014 GIBUSH Systems | "
                f"{time.strftime('%Y-%m-%d')}",
                ha='center', va='bottom', fontsize=7,
                color='#304050', alpha=0.5,
                family='monospace', transform=ax.transAxes)

        # Progress bar
        bar_y = 0.018
        ax.plot([0.02, 0.48], [bar_y, bar_y],
                color='#152020', linewidth=3,
                transform=ax.transAxes,
                solid_capstyle='round')
        progress = (si + 1) / 12
        ax.plot([0.02, 0.02 + 0.46 * progress],
                [bar_y, bar_y],
                color=zone_col, linewidth=3,
                transform=ax.transAxes,
                solid_capstyle='round')

        plt.tight_layout(pad=0)

        if save_slides:
            out_path = os.path.join(img_dir,
                f"BCM_v19_6D_slide_{si+1:02d}_"
                f"{s.get('phase', 'frame')}.png")
            fig.savefig(out_path, dpi=200,
                        bbox_inches='tight', facecolor=BG)
            print(f"  Saved: {out_path}")

        print(f"  [{si+1}/12] {s['title']}")

    plt.show()
    print(f"\n{'='*60}")
    print(f"  6D CINEMATIC COMPLETE -- 12 slides")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v19 6D Field Shape Cinematic")
    parser.add_argument("--save", action="store_true",
                        help="Save slides as PNG files")
    parser.add_argument("--json", type=str, default=None,
                        help="Path to flight log JSON "
                             "for data-driven replay")
    args = parser.parse_args()

    json_path = args.json
    if json_path and '*' in json_path:
        matches = sorted(glob.glob(json_path))
        json_path = matches[-1] if matches else None

    build_cinematic(save_slides=args.save,
                    json_path=json_path)
