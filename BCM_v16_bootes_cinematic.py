# -*- coding: utf-8 -*-
"""
BCM v16 -- Bootes Void Cinematic Renderer
============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Produces slide captures showing transition phases across
the Bootes Void. Each frame is a different state of the
craft as it transits interstellar void with tunnel cycling
probes active.

Slides:
  1. DEPARTURE     - craft in funded space, all probes nominal
  2. VOID ENTRY    - funded bubble contracts, lambda rises
  3. TORUS FIELD   - craft's funded zone as torus cross-section
  4. DEEP VOID     - maximum isolation, reactor-only illumination
  5. GRAVE DETECT  - probes detect dead galaxy substrate
  6. HYPERCUBE     - tesseract probe paths during avoidance
  7. CHI TRANSIT   - 4D bypass through chi field
  8. OBSERVER      - probes measuring their own perturbation
  9. RE-EMERGENCE  - sensors recalibrating to funded space
 10. ARRIVAL       - craft coherent, void crossed

The observer paradox: the probes change the substrate they
measure. Each slide shows what TITS sees vs what is real.
The difference is the observer's fingerprint.

Usage:
    python BCM_v16_bootes_cinematic.py
    python BCM_v16_bootes_cinematic.py --save
"""

import numpy as np
import os
import time
import math
import argparse


def build_cinematic(save_slides=False):
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch, Wedge
    from matplotlib.patches import Polygon as MplPolygon
    from matplotlib import cm

    base = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(base, "data", "images")
    os.makedirs(img_dir, exist_ok=True)

    # -- SLIDE DEFINITIONS --
    slides = [
        {
            "title": "DEPARTURE -- Funded Space",
            "subtitle": "Craft coherent. 12 probes cycling. Navigator: PROCEED",
            "phase": "departure",
            "craft_x": 0.15, "lambda_bg": 0.02,
            "probe_range": 0.12, "decision": "PROCEED",
            "coherence": 0.95, "grave_p": 0.01,
            "label": "Lambda low. Substrate funded by local stars.\n"
                     "All probes returning nominal. Full visibility.",
        },
        {
            "title": "VOID ENTRY -- Transition Zone",
            "subtitle": "Lambda rising. Funded bubble contracting.",
            "phase": "void_entry",
            "craft_x": 0.25, "lambda_bg": 0.05,
            "probe_range": 0.10, "decision": "PROCEED",
            "coherence": 0.82, "grave_p": 0.05,
            "label": "Substrate tax increasing. Probe arc range\n"
                     "shrinking. TITS resolution degrading.",
        },
        {
            "title": "TORUS FIELD -- Craft Funded Zone",
            "subtitle": "The craft's reactor is the only light source.",
            "phase": "torus",
            "craft_x": 0.35, "lambda_bg": 0.08,
            "probe_range": 0.08, "decision": "CAUTION",
            "coherence": 0.71, "grave_p": 0.12,
            "label": "Funded zone visible as torus around craft.\n"
                     "Probes see only what the reactor pays to illuminate.",
        },
        {
            "title": "DEEP VOID -- Maximum Isolation",
            "subtitle": "No external funding. Reactor is the mission clock.",
            "phase": "deep_void",
            "craft_x": 0.42, "lambda_bg": 0.10,
            "probe_range": 0.06, "decision": "CAUTION",
            "coherence": 0.63, "grave_p": 0.18,
            "label": "Lambda at baseline. Every pixel of visibility\n"
                     "costs reactor fuel. Sensors see 60px ahead.",
        },
        {
            "title": "GRAVE DETECT -- Dead Galaxy Substrate",
            "subtitle": "Probe P11 detected density anomaly 220 steps ahead.",
            "phase": "grave_detect",
            "craft_x": 0.50, "lambda_bg": 0.10,
            "probe_range": 0.06, "decision": "AVOID",
            "coherence": 0.57, "grave_p": 0.92,
            "label": "Forward probes report lambda < 0.04.\n"
                     "Navigator flips to AVOID. Grave posterior: 0.92.\n"
                     "Mass pickup risk: 38x if transit attempted.",
        },
        {
            "title": "HYPERCUBE -- Tesseract Probe Avoidance",
            "subtitle": "Probe paths shift to 4D vertex rotation during course change.",
            "phase": "hypercube",
            "craft_x": 0.52, "lambda_bg": 0.10,
            "probe_range": 0.06, "decision": "AVOID",
            "coherence": 0.55, "grave_p": 0.87,
            "label": "Tesseract rotation shifts probe orbital polygons.\n"
                     "New vertices sample the alternate heading.\n"
                     "Course change latency: 3 probe cycles.",
        },
        {
            "title": "CHI TRANSIT -- 4D Bypass Corridor",
            "subtitle": "Chi field bridges 3D funded and 4D bulk states.",
            "phase": "chi_transit",
            "craft_x": 0.58, "lambda_bg": 0.10,
            "probe_range": 0.05, "decision": "TUNNEL",
            "coherence": 0.52, "grave_p": 0.70,
            "label": "Chi is the only field that doesn't go dark\n"
                     "when the reactor dims. Navigator reads chi\n"
                     "because chi exists in both 3D and 4D.",
        },
        {
            "title": "OBSERVER PARADOX -- Perturbation Fingerprint",
            "subtitle": "The probe changes the substrate it measures.",
            "phase": "observer",
            "craft_x": 0.65, "lambda_bg": 0.09,
            "probe_range": 0.07, "decision": "CAUTION",
            "coherence": 0.58, "grave_p": 0.45,
            "label": "After 642 cycles, 25,965 probe interactions\n"
                     "have perturbed the substrate. The perturbation\n"
                     "IS data. Dead graves respond differently than void.",
        },
        {
            "title": "RE-EMERGENCE -- Sensor Recalibration",
            "subtitle": "Entering funded space. Reality may have bifurcated.",
            "phase": "reemergence",
            "craft_x": 0.78, "lambda_bg": 0.05,
            "probe_range": 0.10, "decision": "PROCEED",
            "coherence": 0.75, "grave_p": 0.08,
            "label": "Lambda dropping. External funding detected.\n"
                     "TITS must recalibrate -- the reality the craft\n"
                     "left may not be the reality it re-enters.",
        },
        {
            "title": "ARRIVAL -- Void Crossed",
            "subtitle": "Craft coherent. Omega anchor separation confirmed.",
            "phase": "arrival",
            "craft_x": 0.88, "lambda_bg": 0.02,
            "probe_range": 0.12, "decision": "PROCEED",
            "coherence": 0.90, "grave_p": 0.01,
            "label": "Transit complete. The ship thinks.\n"
                     "The thinking kept it alive.\n"
                     "Omega separation: 100.2 px. Transport is real.",
        },
    ]

    print(f"\n{'='*60}")
    print(f"  BCM v16 -- BOOTES VOID CINEMATIC")
    print(f"  10 transition phase slides")
    print(f"  Observer paradox interstellar transit")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*60}")

    for si, slide in enumerate(slides):
        fig, ax = plt.subplots(1, 1, figsize=(16, 9), facecolor='black')
        ax.set_facecolor('black')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.axis('off')

        # -- BACKGROUND: substrate field gradient --
        lam_bg = slide["lambda_bg"]
        # Dark = high lambda (void), lighter = low lambda (funded)
        for ix in range(100):
            x_frac = ix / 100.0
            # Lambda varies across field
            dist_from_craft = abs(x_frac - slide["craft_x"])
            local_lam = lam_bg + 0.05 * dist_from_craft
            # Brightness inversely proportional to lambda
            brightness = max(0, 0.15 - local_lam) * 3
            color = (0.02 + brightness * 0.1,
                     0.04 + brightness * 0.3,
                     0.06 + brightness * 0.15)
            ax.axvspan(ix/100, (ix+1)/100, color=color, alpha=0.8)

        cx = slide["craft_x"]
        cy = 0.5

        # -- FUNDED BUBBLE (torus cross-section) --
        bubble_r = slide["probe_range"] + 0.03
        bubble = Circle((cx, cy), bubble_r, fill=False,
                         edgecolor='#204030', linewidth=1,
                         linestyle='--', alpha=0.4)
        ax.add_patch(bubble)

        # Torus glow (for torus phase, extra rings)
        if slide["phase"] == "torus":
            for r_frac in [0.6, 0.8, 1.0, 1.2]:
                ring = Circle((cx, cy), bubble_r * r_frac,
                               fill=False, edgecolor='#30ff60',
                               linewidth=0.5, alpha=0.15)
                ax.add_patch(ring)

        # -- DUMBBELL CRAFT --
        sep = 0.04
        pump_a_r = 0.018
        pump_b_r = 0.007

        ax_pos = cx + sep * 0.6
        bx_pos = cx - sep * 0.4

        # Pump A (forward, large, green)
        pa = Circle((ax_pos, cy), pump_a_r, fill=True,
                      facecolor='#103018', edgecolor='#40ee70',
                      linewidth=2, alpha=0.9)
        ax.add_patch(pa)
        ax.text(ax_pos, cy, 'A', ha='center', va='center',
                fontsize=9, fontweight='bold', color='white')

        # A ejection slit
        slit_x = ax_pos + pump_a_r
        ax.plot([slit_x, slit_x + 0.008], [cy - 0.004, cy - 0.001],
                color='#40ee70', linewidth=1, alpha=0.7)
        ax.plot([slit_x, slit_x + 0.008], [cy + 0.004, cy + 0.001],
                color='#40ee70', linewidth=1, alpha=0.7)
        ax.plot([slit_x, slit_x], [cy - 0.004, cy + 0.004],
                color='#40ee70', linewidth=2)

        # Pump B (aft, small, teal)
        pb = Circle((bx_pos, cy), pump_b_r, fill=True,
                      facecolor='#081820', edgecolor='#40ccaa',
                      linewidth=1.5, alpha=0.9)
        ax.add_patch(pb)
        ax.text(bx_pos, cy, 'B', ha='center', va='center',
                fontsize=7, color='white')

        # B collection funnel
        funnel_x = bx_pos - pump_b_r
        funnel_w = 0.02
        funnel_mouth = 0.025
        ax.plot([funnel_x - funnel_w, funnel_x],
                [cy - funnel_mouth, cy - 0.003],
                color='#40ccaa', linewidth=1)
        ax.plot([funnel_x - funnel_w, funnel_x],
                [cy + funnel_mouth, cy + 0.003],
                color='#40ccaa', linewidth=1)
        ax.plot([funnel_x - funnel_w, funnel_x - funnel_w],
                [cy - funnel_mouth, cy + funnel_mouth],
                color='#40ccaa', linewidth=1, linestyle='--')

        # Venturi tunnel (wide at B, narrow at A)
        tunnel_pts = np.array([
            [bx_pos + pump_b_r, cy - 0.005],
            [ax_pos - pump_a_r, cy - 0.002],
            [ax_pos - pump_a_r, cy + 0.002],
            [bx_pos + pump_b_r, cy + 0.005],
        ])
        tunnel = MplPolygon(tunnel_pts, fill=False,
                             edgecolor='#3a4a60', linewidth=0.8)
        ax.add_patch(tunnel)

        # L1 point
        l1x = (bx_pos + ax_pos) / 2
        ax.plot(l1x, cy, 'o', color='#ff4444', markersize=3)

        # -- PROBES (12, cycling through tesseract paths) --
        probe_r = slide["probe_range"]
        n_probes = 12
        rng = np.random.RandomState(42 + si)

        for pid in range(n_probes):
            # Semi-random polygonal arc from A
            angle = pid * (2 * math.pi / n_probes) + si * 0.3
            r = probe_r * (0.4 + 0.6 * rng.random())
            px = ax_pos + r * math.cos(angle)
            py = cy + r * math.sin(angle)

            if 0.02 < px < 0.98 and 0.05 < py < 0.95:
                # Probe dot
                probe_col = '#ff4444' if slide["phase"] == "grave_detect" and pid > 8 else '#60aaff'
                ax.plot(px, py, 'o', color=probe_col,
                        markersize=3, alpha=0.7)
                # Faint line to A (return path)
                ax.plot([px, ax_pos], [py, cy],
                        color=probe_col, linewidth=0.3, alpha=0.2)

        # -- GRAVE (for detect/hypercube/chi phases) --
        if slide["phase"] in ("grave_detect", "hypercube", "chi_transit"):
            grave_x = cx + 0.15
            grave_r = 0.06
            grave = Circle((grave_x, cy), grave_r, fill=True,
                            facecolor='#200808', edgecolor='#ff4444',
                            linewidth=1, linestyle='--', alpha=0.6)
            ax.add_patch(grave)
            ax.text(grave_x, cy, 'GRAVE', ha='center', va='center',
                    fontsize=8, color='#ff4444', alpha=0.7)

        # -- HYPERCUBE overlay --
        if slide["phase"] == "hypercube":
            # Tesseract projection around craft
            hc = 0.08
            outer = [[cx-hc, cy-hc], [cx+hc, cy-hc],
                     [cx+hc, cy+hc], [cx-hc, cy+hc], [cx-hc, cy-hc]]
            inner_off = 0.03
            inner = [[cx-hc+inner_off, cy-hc+inner_off],
                     [cx+hc-inner_off, cy-hc+inner_off],
                     [cx+hc-inner_off, cy+hc-inner_off],
                     [cx-hc+inner_off, cy+hc-inner_off],
                     [cx-hc+inner_off, cy-hc+inner_off]]
            for pts, a in [(outer, 0.3), (inner, 0.2)]:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                ax.plot(xs, ys, color='#ff9944', linewidth=0.8, alpha=a)
            # Connecting edges
            for i in range(4):
                ax.plot([outer[i][0], inner[i][0]],
                        [outer[i][1], inner[i][1]],
                        color='#ff9944', linewidth=0.5, alpha=0.2)

        # -- CHI FIELD overlay --
        if slide["phase"] == "chi_transit":
            # Chi waves (concentric from craft, extending into 4D)
            for r_frac in [0.04, 0.07, 0.10, 0.14]:
                chi_ring = Circle((cx, cy), r_frac, fill=False,
                                   edgecolor='#aa44ff', linewidth=0.8,
                                   alpha=0.3, linestyle=':')
                ax.add_patch(chi_ring)
            ax.text(cx, cy + 0.17, 'CHI FIELD',
                    ha='center', fontsize=8, color='#aa44ff', alpha=0.5)

        # -- OBSERVER PARADOX overlay --
        if slide["phase"] == "observer":
            # Perturbation ripples from probe positions
            for pid in range(4):
                angle = pid * math.pi / 2
                px = ax_pos + 0.06 * math.cos(angle)
                py = cy + 0.06 * math.sin(angle)
                for rr in [0.01, 0.02, 0.03]:
                    ripple = Circle((px, py), rr, fill=False,
                                     edgecolor='#ffcc00', linewidth=0.5,
                                     alpha=0.2)
                    ax.add_patch(ripple)

        # -- HUD --
        # Decision indicator
        dec = slide["decision"]
        dec_col = '#44ff88' if dec == "PROCEED" else \
                  '#ffbb44' if dec in ("CAUTION", "TUNNEL") else '#ff4444'
        ax.text(0.98, 0.96, dec, ha='right', va='top',
                fontsize=20, fontweight='bold', color=dec_col,
                alpha=0.8, transform=ax.transAxes)

        # Status HUD
        hud = (
            f"COHERENCE: {slide['coherence']:.2f}\n"
            f"GRAVE P:   {slide['grave_p']:.2f}\n"
            f"LAMBDA:    {slide['lambda_bg']:.2f}\n"
            f"RANGE:     {slide['probe_range']*1000:.0f} px\n"
            f"PROBES:    12 ACTIVE"
        )
        ax.text(0.98, 0.04, hud, ha='right', va='bottom',
                fontsize=9, color='#80c0ff', alpha=0.6,
                family='monospace', transform=ax.transAxes,
                bbox=dict(boxstyle='round,pad=0.5',
                          facecolor='#0a0e18', edgecolor='#203050',
                          alpha=0.7))

        # Title
        ax.text(0.02, 0.96,
                f"SLIDE {si+1}/10",
                ha='left', va='top', fontsize=10,
                color='#6a7a90', family='monospace',
                transform=ax.transAxes)
        ax.text(0.02, 0.91,
                slide["title"],
                ha='left', va='top', fontsize=16,
                fontweight='bold', color='#d0e8ff',
                family='sans-serif', transform=ax.transAxes)
        ax.text(0.02, 0.86,
                slide["subtitle"],
                ha='left', va='top', fontsize=10,
                color='#8090a8', family='sans-serif',
                transform=ax.transAxes)

        # Description
        ax.text(0.02, 0.04,
                slide["label"],
                ha='left', va='bottom', fontsize=9,
                color='#60c080', family='monospace',
                transform=ax.transAxes,
                bbox=dict(boxstyle='round,pad=0.5',
                          facecolor='#0a0e18', edgecolor='#203050',
                          alpha=0.7))

        # Watermark
        ax.text(0.50, 0.01,
                "BCM v16 | Emerald Entities LLC -- GIBUSH Systems | "
                f"{time.strftime('%Y-%m-%d')}",
                ha='center', va='bottom', fontsize=7,
                color='#304050', alpha=0.5, family='monospace',
                transform=ax.transAxes)

        # Progress bar at bottom
        bar_y = 0.015
        ax.plot([0.02, 0.48], [bar_y, bar_y],
                color='#203030', linewidth=3, transform=ax.transAxes,
                solid_capstyle='round')
        progress = (si + 1) / len(slides)
        ax.plot([0.02, 0.02 + 0.46 * progress], [bar_y, bar_y],
                color=dec_col, linewidth=3, transform=ax.transAxes,
                solid_capstyle='round')

        plt.tight_layout(pad=0)

        if save_slides:
            out_path = os.path.join(img_dir,
                f"BCM_bootes_slide_{si+1:02d}_{slide['phase']}.png")
            fig.savefig(out_path, dpi=200, bbox_inches='tight',
                        facecolor='black')
            print(f"  Saved: {out_path}")

        print(f"  [{si+1}/10] {slide['title']}")

    plt.show()
    print(f"\n{'='*60}")
    print(f"  CINEMATIC COMPLETE -- 10 slides")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v16 Bootes Void Cinematic")
    parser.add_argument("--save", action="store_true",
                        help="Save slides as PNG files")
    args = parser.parse_args()

    build_cinematic(save_slides=args.save)
