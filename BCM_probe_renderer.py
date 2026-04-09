# -*- coding: utf-8 -*-
"""
BCM Probe Renderer
====================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Standalone visualization for the BCM v16 tunnel cycling
probe system. Companion to BCM_v16_tunnel_probes.py.

Shows:
  - Live probe cycling animation (12 probes through craft)
  - Navigator decision state (PROCEED/CAUTION/AVOID)
  - Hypothesis posterior bars
  - Tax curve visualization
  - Substrate field with hazards and probe positions
  - Probe fleet status table

Usage:
    python BCM_probe_renderer.py
    python BCM_probe_renderer.py --json data/results/BCM_v16_tunnel_probes_*.json
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import json
import os
import sys
import math
import argparse
import glob

# -----------------------------------------
# COLOR PALETTE
# -----------------------------------------

BG_DARK     = "#080a0e"
BG_MID      = "#0c0e14"
BG_PANEL    = "#10131a"
ACCENT      = "#ff9944"
GOLD        = "#ffbb44"
GREEN       = "#40ee70"
RED         = "#ff5555"
TEAL        = "#40ccaa"
WHITE       = "#e0e8f0"
DIM         = "#3a4a60"
PROBE_COL   = "#60aaff"
CRAFT_COL   = "#ff9944"
DANGER_COL  = "#ff4444"
SAFE_COL    = "#44ff88"


class ProbeRenderer:
    """Standalone probe visualization window."""

    def __init__(self, root, json_path=None):
        self.root = root
        self.root.title("BCM PROBE RENDERER -- Tunnel Cycling Observer")
        self.root.geometry("1200x800")
        self.root.configure(bg=BG_DARK)
        self.root.minsize(900, 600)

        self.data = None
        self.anim_step = 0
        self.anim_running = False

        self._build_ui()

        if json_path:
            self._load_json(json_path)
        else:
            self._try_load_latest()

    def _build_ui(self):
        # Header
        hf = tk.Frame(self.root, bg=BG_DARK)
        hf.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(hf, text="TITS PROBE RENDERER",
                 font=("Georgia", 16), fg=ACCENT, bg=BG_DARK).pack(side="left")
        tk.Label(hf, text="Tunnel Cycling Observer -- Emerald Entities LLC",
                 font=("Consolas", 9), fg=DIM, bg=BG_DARK).pack(side="left", padx=(16, 0))

        # Main split
        main = tk.Frame(self.root, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=10, pady=4)

        # Left: field canvas + probe animation
        left = tk.Frame(main, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=True)

        self.field_canvas = tk.Canvas(left, bg=BG_MID,
                                       highlightthickness=0)
        self.field_canvas.pack(fill="both", expand=True, padx=(0, 4))
        self._canvas_w = 600
        self._canvas_h = 500
        self.field_canvas.bind("<Configure>", self._on_resize)

        # Animation controls
        ctrl = tk.Frame(left, bg=BG_DARK)
        ctrl.pack(fill="x", pady=4)
        self.play_btn = tk.Button(ctrl, text="\u25B6 Play",
                                   font=("Consolas", 10),
                                   bg="#1a1e2a", fg=GREEN,
                                   command=self._toggle_anim)
        self.play_btn.pack(side="left", padx=4)
        self.step_label = tk.Label(ctrl, text="Step: 0",
                                    font=("Consolas", 10),
                                    fg=WHITE, bg=BG_DARK)
        self.step_label.pack(side="left", padx=8)
        self.decision_label = tk.Label(ctrl, text="Decision: ---",
                                        font=("Consolas", 12, "bold"),
                                        fg=SAFE_COL, bg=BG_DARK)
        self.decision_label.pack(side="right", padx=8)

        # Right: panels
        right = tk.Frame(main, bg=BG_DARK, width=380)
        right.pack(side="right", fill="y", padx=(4, 0))
        right.pack_propagate(False)

        # Hypothesis bars
        hyp_f = tk.LabelFrame(right, text="HYPOTHESES",
                               font=("Consolas", 10, "bold"),
                               fg=ACCENT, bg=BG_PANEL)
        hyp_f.pack(fill="x", padx=4, pady=4)
        self.hyp_canvas = tk.Canvas(hyp_f, bg=BG_PANEL,
                                     height=180, highlightthickness=0)
        self.hyp_canvas.pack(fill="x", padx=4, pady=4)

        # Fleet status
        fleet_f = tk.LabelFrame(right, text="PROBE FLEET",
                                 font=("Consolas", 10, "bold"),
                                 fg=ACCENT, bg=BG_PANEL)
        fleet_f.pack(fill="x", padx=4, pady=4)
        self.fleet_text = tk.Text(fleet_f, height=14, bg=BG_MID,
                                   fg=WHITE, font=("Consolas", 8),
                                   relief="flat")
        self.fleet_text.pack(fill="x", padx=4, pady=4)

        # Results summary
        res_f = tk.LabelFrame(right, text="RESULTS",
                               font=("Consolas", 10, "bold"),
                               fg=ACCENT, bg=BG_PANEL)
        res_f.pack(fill="both", expand=True, padx=4, pady=4)
        self.result_text = tk.Text(res_f, height=10, bg=BG_MID,
                                    fg=ACCENT, font=("Consolas", 9),
                                    relief="flat")
        self.result_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _on_resize(self, event):
        self._canvas_w = event.width
        self._canvas_h = event.height
        if self.data and not self.anim_running:
            self._draw_frame(self.anim_step)

    def _try_load_latest(self):
        """Try to load the most recent tunnel probes JSON."""
        base = os.path.dirname(os.path.abspath(__file__))
        pattern = os.path.join(base, "data", "results",
                               "BCM_v16_tunnel_probes_*.json")
        files = sorted(glob.glob(pattern))
        if files:
            self._load_json(files[-1])
        else:
            self.result_text.insert("1.0",
                "No probe results found.\n"
                "Run BCM_v16_tunnel_probes.py first,\n"
                "or pass --json <path> to load results.")

    def _load_json(self, path):
        """Load probe results from JSON."""
        try:
            with open(path, "r") as f:
                self.data = json.load(f)

            r = self.data.get("result", {})
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0",
                f"File: {os.path.basename(path)}\n"
                f"Grid: {self.data.get('grid', '?')}\n"
                f"Steps: {self.data.get('steps', '?')}\n"
                f"Alive: {'YES' if r.get('alive') else 'NO'}\n"
                f"Drift: {r.get('drift', 0):.2f} px\n"
                f"Omega sep: {r.get('omega_sep', 0):.2f} px\n"
                f"Coherence: {r.get('coherence', 0):.4f}\n"
                f"Readings: {r.get('total_readings', 0)}\n"
                f"Cycles: {r.get('total_cycles', 0)}\n"
                f"Roche: {r.get('roche_violations', 0)}\n"
                f"Transitions: {r.get('transitions', 0)}\n"
                f"Decision: {r.get('decision', '?')}\n")

            # Fleet status
            self.fleet_text.delete("1.0", "end")
            self.fleet_text.insert("1.0",
                f"{'PID':>4} {'Cycles':>7} {'Reads':>6} "
                f"{'Roche':>6} {'State':>10}\n")
            self.fleet_text.insert("end",
                f"{'-'*4} {'-'*7} {'-'*6} {'-'*6} {'-'*10}\n")
            for p in self.data.get("probes", []):
                self.fleet_text.insert("end",
                    f"{p['pid']:>4} {p.get('cycles', 0):>7} "
                    f"{p.get('total_reads', 0):>6} "
                    f"{p.get('roche_violations', 0):>6} "
                    f"{p.get('state', '?'):>10}\n")

            # Draw initial frame
            self._draw_frame(0)
            self._draw_hypotheses(0)

        except Exception as e:
            self.result_text.insert("1.0", f"Load error: {e}")

    def _draw_frame(self, frame_idx):
        """Draw the substrate field with probe positions."""
        c = self.field_canvas
        c.delete("all")
        w, h = self._canvas_w, self._canvas_h

        if not self.data:
            return

        timeline = self.data.get("timeline", [])
        if not timeline:
            return

        idx = min(frame_idx, len(timeline) - 1)
        entry = timeline[idx]

        craft_x = entry.get("x", 0)
        grid = self.data.get("grid", 256)

        # Scale factors
        sx = w / grid
        sy = (h - 40) / grid

        # Draw hazard zones (from data)
        # Shallow grave at grid/3, deep at grid/2
        g1x = grid // 3
        g2x = grid // 2
        gy = grid // 2

        # Shallow grave circle
        c.create_oval(
            g1x * sx - 12 * sx, gy * sy - 12 * sy,
            g1x * sx + 12 * sx, gy * sy + 12 * sy,
            outline=DANGER_COL, width=1, dash=(3, 3))
        c.create_text(g1x * sx, gy * sy - 16 * sy,
                       text="SHALLOW", font=("Consolas", 7),
                       fill=DANGER_COL)

        # Deep grave circle
        c.create_oval(
            g2x * sx - 18 * sx, gy * sy - 18 * sy,
            g2x * sx + 18 * sx, gy * sy + 18 * sy,
            outline=RED, width=2, dash=(3, 3))
        c.create_text(g2x * sx, gy * sy - 22 * sy,
                       text="DEEP GRAVE", font=("Consolas", 8),
                       fill=RED)

        # Omega anchor
        omega_x = grid // 8
        c.create_text(omega_x * sx, gy * sy + 14,
                       text="OMEGA", font=("Consolas", 7),
                       fill=DIM)
        c.create_oval(omega_x * sx - 4, gy * sy - 4,
                       omega_x * sx + 4, gy * sy + 4,
                       fill="", outline=DIM, width=1, dash=(2,2))

        # -- DUMBBELL CRAFT (A/B ratio visible in size) --
        # B = funnel (wide collection), A = slit (focused ejection)
        # Tunnel narrows B->A like a Venturi tube
        ratio = 4.0
        cx = craft_x * sx
        cy = gy * sy
        separation = 22 * sx

        # Pump A (forward, large) -- primary star
        pump_a_r = 12
        ax = cx + separation * 0.6
        c.create_oval(ax - pump_a_r, cy - pump_a_r,
                       ax + pump_a_r, cy + pump_a_r,
                       fill="", outline=GREEN, width=2)
        c.create_oval(ax - pump_a_r + 3, cy - pump_a_r + 3,
                       ax + pump_a_r - 3, cy + pump_a_r - 3,
                       fill=GREEN, outline="", stipple="gray50")
        c.create_text(ax, cy, text="A",
                       font=("Consolas", 9, "bold"), fill=WHITE)

        # A ejection slit (narrow nozzle on forward face)
        slit_w = 3
        slit_h = pump_a_r * 0.5
        slit_x = ax + pump_a_r
        c.create_rectangle(slit_x, cy - slit_h,
                            slit_x + slit_w, cy + slit_h,
                            fill=GREEN, outline=WHITE, width=1)
        # Ejection lines from slit
        for dy in [-slit_h * 0.5, 0, slit_h * 0.5]:
            c.create_line(slit_x + slit_w, cy + dy,
                           slit_x + slit_w + 12, cy + dy * 0.3,
                           fill=GREEN, width=1, dash=(2, 2))

        # Pump B (aft, small) -- secondary star
        pump_b_r = int(pump_a_r / ratio) + 2
        bx = cx - separation * 0.4
        c.create_oval(bx - pump_b_r, cy - pump_b_r,
                       bx + pump_b_r, cy + pump_b_r,
                       fill="", outline=TEAL, width=2)
        c.create_oval(bx - pump_b_r + 2, cy - pump_b_r + 2,
                       bx + pump_b_r - 2, cy + pump_b_r - 2,
                       fill=TEAL, outline="", stipple="gray50")
        c.create_text(bx, cy, text="B",
                       font=("Consolas", 7), fill=WHITE)

        # B collection funnel (wide mouth narrowing to tunnel)
        funnel_mouth = pump_b_r * 2.5  # wide opening
        funnel_depth = 14
        funnel_x = bx - pump_b_r
        # Funnel shape: wide V narrowing to tunnel width
        c.create_line(funnel_x - funnel_depth, cy - funnel_mouth,
                       funnel_x, cy - 3,
                       fill=TEAL, width=1)
        c.create_line(funnel_x - funnel_depth, cy + funnel_mouth,
                       funnel_x, cy + 3,
                       fill=TEAL, width=1)
        # Funnel mouth arc
        c.create_line(funnel_x - funnel_depth, cy - funnel_mouth,
                       funnel_x - funnel_depth, cy + funnel_mouth,
                       fill=TEAL, width=1, dash=(3, 2))
        # Vortex spiral hint inside funnel
        for i in range(3):
            t = (i + 1) / 4.0
            fr = funnel_mouth * (1 - t)
            fx = funnel_x - funnel_depth * (1 - t)
            c.create_oval(fx - 1, cy - fr, fx + 1, cy + fr,
                           outline=TEAL, width=1, dash=(1, 2))

        # L1 tunnel (Venturi -- wider at B, narrower at A)
        tunnel_b_width = 4   # wide end at B
        tunnel_a_width = 2   # narrow end at A
        c.create_polygon(
            bx + pump_b_r, cy - tunnel_b_width,
            ax - pump_a_r, cy - tunnel_a_width,
            ax - pump_a_r, cy + tunnel_a_width,
            bx + pump_b_r, cy + tunnel_b_width,
            fill="", outline=DIM, width=1)

        # L1 point (center of tunnel)
        l1x = (bx + ax) / 2
        c.create_oval(l1x - 2, cy - 2, l1x + 2, cy + 2,
                       fill=RED, outline=RED)

        # Craft label with ratio
        c.create_text(cx, cy - pump_a_r - 10,
                       text=f"CRAFT  {ratio:.0f}:1",
                       font=("Consolas", 8), fill=WHITE)

        # Direction arrow (forward)
        arrow_x = slit_x + slit_w + 14
        c.create_line(arrow_x, cy, arrow_x + 15, cy,
                       fill=GREEN, width=2, arrow="last")

        # Animated probe positions (12 probes)
        step = entry.get("step", 0)
        for pid in range(1, 13):
            cycle_len = 55
            offset = (pid - 1) * 5
            eff_step = step - offset
            if eff_step < 0:
                continue

            cycle_step = eff_step % cycle_len

            if cycle_step < 5:
                # Transit: inside tunnel
                t = cycle_step / 5
                px = bx + t * (ax - bx)
                py = cy
                col = TEAL
            elif cycle_step < 45:
                # Ejected: on arc
                arc_step = cycle_step - 5
                t_arc = arc_step / 40.0
                max_r = 40.0 * sx
                if t_arc < 0.5:
                    r = max_r * (t_arc * 2)
                else:
                    r = max_r * (2 - t_arc * 2)

                base_angle = pid * 0.5 + (eff_step // cycle_len) * 0.3
                angle = base_angle + t_arc * 2 * math.pi
                px = ax + r * math.cos(angle)
                py = cy + r * math.sin(angle)
                col = PROBE_COL
            else:
                # Falling back to B
                t_fall = (cycle_step - 45) / 10.0
                px = ax + (1 - t_fall) * 20 * sx
                py = cy
                col = DIM

            # Clamp to canvas
            px = max(2, min(w - 2, px))
            py = max(2, min(h - 42, py))

            c.create_oval(px - 3, py - 3, px + 3, py + 3,
                           fill=col, outline=col)

        # Decision bar
        decision = entry.get("decision", "---")
        dec_col = SAFE_COL if decision == "PROCEED" else \
                  GOLD if decision == "CAUTION" else \
                  RED if decision == "AVOID" else DIM

        c.create_rectangle(0, h - 30, w, h,
                            fill=BG_PANEL, outline="")
        c.create_text(w // 2, h - 15,
                       text=f"Step {step}  |  {decision}  |  "
                            f"Safe={entry.get('safe_p', 0):.3f}  "
                            f"Grave={entry.get('grave_p', 0):.3f}  "
                            f"Warnings={entry.get('warnings', 0)}",
                       font=("Consolas", 9), fill=dec_col)

        self.step_label.config(text=f"Step: {step}")
        self.decision_label.config(text=f"Decision: {decision}",
                                    fg=dec_col)

    def _draw_hypotheses(self, frame_idx):
        """Draw hypothesis posterior bars."""
        c = self.hyp_canvas
        c.delete("all")

        if not self.data:
            return

        timeline = self.data.get("timeline", [])
        if not timeline:
            return

        idx = min(frame_idx, len(timeline) - 1)
        entry = timeline[idx]

        hyps = [
            ("Safe ahead", entry.get("safe_p", 0.5)),
            ("Grave ahead", entry.get("grave_p", 0.3)),
        ]

        bar_w = 250
        bar_h = 20
        x0 = 100
        y0 = 20

        for i, (name, post) in enumerate(hyps):
            y = y0 + i * 40

            col = SAFE_COL if post > 0.7 else \
                  GOLD if post > 0.4 else \
                  RED if post > 0.2 else DIM

            c.create_text(x0 - 8, y + bar_h // 2,
                           text=name, anchor="e",
                           font=("Consolas", 9), fill=WHITE)
            c.create_rectangle(x0, y, x0 + bar_w, y + bar_h,
                                outline=DIM, fill=BG_MID)
            fill_w = int(bar_w * min(1, post))
            c.create_rectangle(x0, y, x0 + fill_w, y + bar_h,
                                outline="", fill=col)
            c.create_text(x0 + bar_w + 8, y + bar_h // 2,
                           text=f"{post:.3f}", anchor="w",
                           font=("Consolas", 9), fill=col)

        # Coherence
        coh = entry.get("coherence", 0)
        y = y0 + len(hyps) * 40
        c.create_text(x0 - 8, y + bar_h // 2,
                       text="Coherence", anchor="e",
                       font=("Consolas", 9), fill=WHITE)
        c.create_rectangle(x0, y, x0 + bar_w, y + bar_h,
                            outline=DIM, fill=BG_MID)
        fill_w = int(bar_w * min(1, coh))
        coh_col = GREEN if coh > 0.5 else GOLD if coh > 0.3 else RED
        c.create_rectangle(x0, y, x0 + fill_w, y + bar_h,
                            outline="", fill=coh_col)
        c.create_text(x0 + bar_w + 8, y + bar_h // 2,
                       text=f"{coh:.3f}", anchor="w",
                       font=("Consolas", 9), fill=coh_col)

    def _toggle_anim(self):
        """Toggle animation playback."""
        if self.anim_running:
            self.anim_running = False
            self.play_btn.config(text="\u25B6 Play")
        else:
            self.anim_running = True
            self.play_btn.config(text="\u23F8 Pause")
            self._animate()

    def _animate(self):
        """Advance one animation frame."""
        if not self.anim_running or not self.data:
            return

        timeline = self.data.get("timeline", [])
        if not timeline:
            return

        self._draw_frame(self.anim_step)
        self._draw_hypotheses(self.anim_step)

        self.anim_step += 1
        if self.anim_step >= len(timeline):
            self.anim_step = 0

        self.root.after(200, self._animate)


def main():
    parser = argparse.ArgumentParser(
        description="BCM Probe Renderer")
    parser.add_argument("--json", type=str, default=None,
                        help="Path to probe results JSON")
    args = parser.parse_args()

    root = tk.Tk()
    app = ProbeRenderer(root, json_path=args.json)
    root.mainloop()


if __name__ == "__main__":
    main()
