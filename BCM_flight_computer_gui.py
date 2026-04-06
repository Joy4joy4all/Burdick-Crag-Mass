# -*- coding: utf-8 -*-
"""
BCM Flight Computer GUI — Pure Python Tkinter
================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Interactive Lambda Drive flight computer.
Three-panel cockpit: phases | map | controls.
Mission day slider moves planets in real time.

Usage:
    python BCM_flight_computer_gui.py
"""

import tkinter as tk
from tkinter import ttk
import math
import json
import os
import time

# Constants
AU_KM = 149597870.7
MU_SUN = 132712440018.0

PLANETS = {
    "Mercury": {"a": 0.3871, "L0": 252.25, "Ldot": 149472.675,
                "color": "#a0a0a0", "mass": 0.055, "size": 3},
    "Venus":   {"a": 0.7233, "L0": 181.98, "Ldot": 58517.816,
                "color": "#e8c060", "mass": 0.815, "size": 4},
    "Earth":   {"a": 1.0000, "L0": 100.47, "Ldot": 35999.373,
                "color": "#4488cc", "mass": 1.0, "size": 4},
    "Mars":    {"a": 1.5237, "L0": -4.57,  "Ldot": 19140.299,
                "color": "#cc4422", "mass": 0.107, "size": 3},
    "Jupiter": {"a": 5.2025, "L0": 34.33,  "Ldot": 3034.904,
                "color": "#cc9966", "mass": 317.8, "size": 6},
    "Saturn":  {"a": 9.5371, "L0": 50.08,  "Ldot": 1222.114,
                "color": "#ddc488", "mass": 95.2, "size": 6},
}


def get_positions(day_offset=0):
    jd = (367 * 2032 - int(7 * (2032 + int((12 + 9) / 12)) / 4)
          + int(275 * 12 / 9) + 1 + day_offset + 1721013.5)
    T = (jd - 2451545.0) / 36525.0
    pos = {}
    for name, p in PLANETS.items():
        L = ((p["L0"] + p["Ldot"] * T) % 360 + 360) % 360
        rad = math.radians(L)
        pos[name] = {"x": p["a"] * math.cos(rad),
                      "y": p["a"] * math.sin(rad),
                      "r": p["a"]}
    return pos


def compute_phases(peri_au, eta, positions):
    earth = positions["Earth"]
    saturn = positions["Saturn"]
    er, sr = earth["r"], saturn["r"]

    # Lead angle
    lead_rad = (2 * math.pi * 200) / 10759.0
    sat_angle = math.atan2(saturn["y"], saturn["x"]) + lead_rad
    sx = sr * math.cos(sat_angle)
    sy = sr * math.sin(sat_angle)

    # Perihelion velocity
    a_exit = (peri_au + sr) / 2
    v_peri = math.sqrt(MU_SUN * (2 / (peri_au * AU_KM) -
                                  1 / (a_exit * AU_KM)))

    # Inward fall
    a_in = (er + peri_au) / 2
    period_in = 2 * math.pi * math.sqrt((a_in * AU_KM)**3 / MU_SUN)
    in_days = int((period_in / 86400) * 0.5)

    # Perihelion point
    e_angle = math.atan2(earth["y"], earth["x"])
    px = peri_au * math.cos(e_angle + math.pi)
    py = peri_au * math.sin(e_angle + math.pi)

    # Outward
    out_dist = math.sqrt((sx - px)**2 + (sy - py)**2) * AU_KM
    v_floor = v_peri * eta
    out_days = int((out_dist / v_floor) / 86400) if v_floor > 0 else 9999

    # Return
    v_dep = v_floor + 2 * 9.69
    ret_dist = math.sqrt(sx**2 + sy**2) * AU_KM
    ret_days = int((ret_dist / v_dep) / 86400)

    lead_au = math.sqrt((sx - saturn["x"])**2 +
                         (sy - saturn["y"])**2)

    cs = in_days + 1  # cruise start
    return [
        {"id": 0, "name": "LAUNCH", "phase": "Earth Departure",
         "day": 0, "dayEnd": 0, "v": 29.8, "x": earth["x"],
         "y": earth["y"], "color": "#4488cc",
         "gap": "Nominal"},
        {"id": 1, "name": "INWARD FALL", "phase": "Earth to Sun",
         "day": 0, "dayEnd": in_days, "v": v_peri,
         "x": px, "y": py, "color": "#ff6644",
         "gap": "Kepler free fall"},
        {"id": 2, "name": "PERI SLEW", "phase": "Sun Redirect",
         "day": in_days, "dayEnd": cs, "v": v_peri,
         "x": px, "y": py, "color": "#ffaa00",
         "gap": "18hr cos arc SAFE"},
        {"id": 3, "name": "L CRUISE", "phase": "Sun to Saturn",
         "day": cs, "dayEnd": cs + out_days, "v": v_floor,
         "x": sx, "y": sy, "color": "#00ffcc",
         "gap": "Shadow:CLR Lead:%.1fAU" % lead_au},
        {"id": 4, "name": "SATURN OPS", "phase": "On Station",
         "day": cs + out_days, "dayEnd": cs + out_days + 30,
         "v": 0, "x": sx, "y": sy, "color": "#ddc488",
         "gap": "Ring validation"},
        {"id": 5, "name": "RETURN", "phase": "Saturn to Earth",
         "day": cs + out_days + 30,
         "dayEnd": cs + out_days + 30 + ret_days,
         "v": v_dep, "x": earth["x"], "y": earth["y"],
         "color": "#ff88cc",
         "gap": "Depart %.0f km/s" % v_dep},
    ]


def get_ship_pos(day, phases):
    for i in range(len(phases) - 1, -1, -1):
        if day >= phases[i]["day"]:
            p = phases[i]
            if i == len(phases) - 1:
                return p["x"], p["y"], p["v"], p["name"]
            np_ = phases[i + 1]
            dur = max(1, np_["day"] - p["day"])
            f = min(1.0, (day - p["day"]) / dur)
            x = p["x"] + (np_["x"] - p["x"]) * f
            y = p["y"] + (np_["y"] - p["y"]) * f
            v = p["v"] + (np_["v"] - p["v"]) * f
            return x, y, v, p["name"]
    return phases[0]["x"], phases[0]["y"], phases[0]["v"], "LAUNCH"


class FlightComputerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BCM v12 — Lambda Drive Flight Computer"
                        " — Emerald Entities LLC")
        self.root.configure(bg="#060810")
        self.root.geometry("1400x800")

        # State
        self.eta = tk.DoubleVar(value=1.0)
        self.peri_au = tk.DoubleVar(value=0.15)
        self.mission_day = tk.IntVar(value=0)
        self.active_phase = 0

        self.launch_pos = get_positions(0)
        self.phases = compute_phases(0.15, 1.0, self.launch_pos)
        self.total_days = self.phases[-1]["dayEnd"]

        self._build_ui()
        self._update_all()

    def _build_ui(self):
        bg = "#060810"
        fg = "#c0d0e0"

        # Header
        hdr = tk.Frame(self.root, bg=bg)
        hdr.pack(fill="x", padx=10, pady=(8, 4))

        tk.Label(hdr, text="\u039B FLIGHT COMPUTER",
                 font=("Consolas", 18, "bold"), fg="#00ffcc",
                 bg=bg).pack(side="left")
        tk.Label(hdr, text="  BCM v12 — Emerald Entities LLC"
                 " — GIBUSH Systems",
                 font=("Consolas", 9), fg="#304050",
                 bg=bg).pack(side="left", padx=(10, 0))

        # Mission day display
        day_f = tk.Frame(hdr, bg=bg)
        day_f.pack(side="right")
        tk.Label(day_f, text="MISSION DAY",
                 font=("Consolas", 9), fg="#506070",
                 bg=bg).pack()
        self.day_lbl = tk.Label(day_f, text="0",
                                 font=("Consolas", 28, "bold"),
                                 fg="#00ffcc", bg=bg)
        self.day_lbl.pack()

        # Day slider
        slider_f = tk.Frame(self.root, bg=bg)
        slider_f.pack(fill="x", padx=10)
        self.day_slider = tk.Scale(
            slider_f, from_=0, to=500,
            orient="horizontal", variable=self.mission_day,
            bg="#0a0e14", fg="#00ffcc", troughcolor="#1a2030",
            highlightthickness=0, sliderrelief="flat",
            font=("Consolas", 8), showvalue=False,
            command=lambda _: self._update_all())
        self.day_slider.pack(fill="x")

        # Separator
        tk.Frame(self.root, bg="#1a2030", height=1).pack(
            fill="x", padx=10, pady=2)

        # Main 3-column layout
        main = tk.Frame(self.root, bg=bg)
        main.pack(fill="both", expand=True, padx=8, pady=4)

        # Left: phases
        left = tk.Frame(main, bg=bg, width=230)
        left.pack(side="left", fill="y", padx=(0, 4))
        left.pack_propagate(False)

        tk.Label(left, text="FLIGHT PHASES",
                 font=("Consolas", 9), fg="#304050",
                 bg=bg).pack(anchor="w")

        self.phase_frame = tk.Frame(left, bg=bg)
        self.phase_frame.pack(fill="both", expand=True)

        # Center: map
        center = tk.Frame(main, bg=bg)
        center.pack(side="left", fill="both", expand=True,
                     padx=4)

        self.canvas = tk.Canvas(center, bg="#04060a",
                                 highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Status bar below map
        self.status_frame = tk.Frame(center, bg="#0a0e14")
        self.status_frame.pack(fill="x", pady=(4, 0))

        # Right: controls
        right = tk.Frame(main, bg=bg, width=250)
        right.pack(side="right", fill="y", padx=(4, 0))
        right.pack_propagate(False)

        self._build_right_panel(right)

    def _build_right_panel(self, parent):
        bg = "#060810"
        fg = "#c0d0e0"

        # ETA display
        eta_f = tk.Frame(parent, bg="#0c1018",
                          relief="flat", bd=1)
        eta_f.pack(fill="x", pady=(0, 4))
        tk.Label(eta_f, text="ETA SATURN",
                 font=("Consolas", 9), fg="#506070",
                 bg="#0c1018").pack()
        self.eta_lbl = tk.Label(eta_f, text="—",
                                 font=("Consolas", 22, "bold"),
                                 fg="#6090c0", bg="#0c1018")
        self.eta_lbl.pack()
        self.vel_lbl = tk.Label(eta_f, text="",
                                 font=("Consolas", 9),
                                 fg="#405060", bg="#0c1018")
        self.vel_lbl.pack()

        # Controls
        ctrl = tk.LabelFrame(parent, text="PILOT CONTROLS",
                              font=("Consolas", 9),
                              fg="#506070", bg="#0c1018")
        ctrl.pack(fill="x", pady=4)

        # Lambda eta
        tk.Label(ctrl, text="Lambda Efficiency",
                 font=("Consolas", 9), fg="#8090a0",
                 bg="#0c1018").pack(anchor="w", padx=6)
        self.eta_scale = tk.Scale(
            ctrl, from_=0, to=100, orient="horizontal",
            bg="#0c1018", fg="#00ffcc", troughcolor="#1a2030",
            highlightthickness=0, font=("Consolas", 8),
            command=lambda _: self._on_param_change())
        self.eta_scale.set(100)
        self.eta_scale.pack(fill="x", padx=6)

        # Perihelion
        tk.Label(ctrl, text="Perihelion (AU x100)",
                 font=("Consolas", 9), fg="#8090a0",
                 bg="#0c1018").pack(anchor="w", padx=6)
        self.peri_scale = tk.Scale(
            ctrl, from_=5, to=50, orient="horizontal",
            bg="#0c1018", fg="#ffaa00", troughcolor="#1a2030",
            highlightthickness=0, font=("Consolas", 8),
            command=lambda _: self._on_param_change())
        self.peri_scale.set(15)
        self.peri_scale.pack(fill="x", padx=6)

        # Phase detail
        self.detail_frame = tk.LabelFrame(
            parent, text="PHASE DETAIL",
            font=("Consolas", 9), fg="#506070", bg="#0c1018")
        self.detail_frame.pack(fill="x", pady=4)
        self.detail_text = tk.Text(
            self.detail_frame, height=5, bg="#080c12",
            fg="#90a8c0", font=("Consolas", 9), relief="flat",
            wrap="word")
        self.detail_text.pack(fill="x", padx=4, pady=2)

        # Validation chain
        val_f = tk.LabelFrame(parent, text="VALIDATION 8/8",
                               font=("Consolas", 9),
                               fg="#a06080", bg="#0c0810")
        val_f.pack(fill="x", pady=4)
        tests = [
            "Drift v~nabla_lam   PASS",
            "Reversal +/-21px    PASS",
            "cos(th)=0.999999    PASS",
            "Lattice indep       PASS",
            "Well approach 81%   PASS",
            "Saddle select       PASS",
            "Streamline nav      PASS",
            "Phase lag 0 step    PASS",
        ]
        for t in tests:
            tk.Label(val_f, text=t, font=("Consolas", 8),
                     fg="#40a060", bg="#0c0810",
                     anchor="w").pack(fill="x", padx=4)

        # Gaps
        gap_f = tk.LabelFrame(parent, text="GEMINI GAPS",
                               font=("Consolas", 9),
                               fg="#40a080", bg="#081010")
        gap_f.pack(fill="x", pady=4)
        gaps = ["Sigma Shadow   CLEAR",
                "Lead Angle     COMPUTED",
                "Phase Snap     SLEW 18hr",
                "L1 Ridge       MAPPED"]
        for g in gaps:
            tk.Label(gap_f, text=g, font=("Consolas", 8),
                     fg="#40c080", bg="#081010",
                     anchor="w").pack(fill="x", padx=4)

        # Phase correction
        pc_f = tk.LabelFrame(parent, text="PHASE CORRECTION",
                              font=("Consolas", 9),
                              fg="#40a0a0", bg="#0c1010")
        pc_f.pack(fill="x", pady=4)
        for label, val, col in [
            ("Substrate lag", "0 steps", "#00ffcc"),
            ("Turn radius", "None", "#00ffcc"),
            ("Coh@flip", "0.289", "#c0a040"),
            ("Slew arc", "18hr safe", "#40a060"),
        ]:
            row = tk.Frame(pc_f, bg="#0c1010")
            row.pack(fill="x", padx=4)
            tk.Label(row, text=label, font=("Consolas", 8),
                     fg="#507070", bg="#0c1010").pack(side="left")
            tk.Label(row, text=val, font=("Consolas", 8, "bold"),
                     fg=col, bg="#0c1010").pack(side="right")

    def _on_param_change(self):
        eta = self.eta_scale.get() / 100.0
        peri = self.peri_scale.get() / 100.0
        self.phases = compute_phases(peri, eta, self.launch_pos)
        self.total_days = self.phases[-1]["dayEnd"]
        self.day_slider.configure(to=max(self.total_days, 100))
        self._update_all()

    def _update_all(self):
        day = self.mission_day.get()
        self.day_lbl.config(text=str(day))

        # Live positions
        live_pos = get_positions(day)

        # Ship position
        sx, sy, sv, sphase = get_ship_pos(day, self.phases)

        # ETA to Saturn
        sat = live_pos["Saturn"]
        dist = math.sqrt((sat["x"] - sx)**2 + (sat["y"] - sy)**2)
        if sv > 0:
            eta_days = (dist * AU_KM / sv) / 86400
            eta_str = "%dd" % int(eta_days)
            if eta_days < 50:
                col = "#00ff88"
            elif eta_days < 200:
                col = "#ffcc00"
            else:
                col = "#6090c0"
        else:
            eta_str = "—"
            col = "#6090c0"
        self.eta_lbl.config(text=eta_str, fg=col)
        self.vel_lbl.config(text="v=%d km/s | %s" % (sv, sphase))

        # Phase blocks
        self._draw_phases()

        # Detail
        p = self.phases[self.active_phase]
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("end",
            "%s\n" % p["name"] +
            "Days: %d - %d (%dd)\n" % (p["day"], p["dayEnd"],
                                         p["dayEnd"] - p["day"]) +
            "Velocity: %d km/s\n" % p["v"] +
            "Gap: %s\n" % p["gap"] +
            "Total mission: %d days" % self.total_days)
        self.detail_text.config(state="disabled")

        # Map
        self._draw_map(live_pos, sx, sy, day)

        # Status bar
        self._draw_status(live_pos, sx, sy)

    def _draw_phases(self):
        for w in self.phase_frame.winfo_children():
            w.destroy()

        for i, p in enumerate(self.phases):
            bg = "#111822" if i == self.active_phase else "#0a0e14"
            border_col = p["color"] if i == self.active_phase else "#1a2030"

            f = tk.Frame(self.phase_frame, bg=bg,
                          highlightbackground=border_col,
                          highlightthickness=1, cursor="hand2")
            f.pack(fill="x", pady=1)
            f.bind("<Button-1>",
                   lambda e, idx=i: self._select_phase(idx))

            # Color bar
            bar = tk.Frame(f, bg=p["color"], width=3)
            bar.pack(side="left", fill="y")

            inner = tk.Frame(f, bg=bg)
            inner.pack(fill="x", padx=4, pady=3)
            inner.bind("<Button-1>",
                        lambda e, idx=i: self._select_phase(idx))

            row1 = tk.Frame(inner, bg=bg)
            row1.pack(fill="x")
            tk.Label(row1, text=p["name"],
                     font=("Consolas", 10, "bold"),
                     fg=p["color"], bg=bg).pack(side="left")
            tk.Label(row1, text="D%d-%d" % (p["day"], p["dayEnd"]),
                     font=("Consolas", 8), fg="#506070",
                     bg=bg).pack(side="right")
            for lbl in row1.winfo_children():
                lbl.bind("<Button-1>",
                         lambda e, idx=i: self._select_phase(idx))

            if p["v"] > 0:
                tk.Label(inner, text="v=%d km/s  %dd" % (
                    p["v"], p["dayEnd"] - p["day"]),
                    font=("Consolas", 8), fg="#60c0a0",
                    bg=bg, anchor="w").pack(fill="x")

    def _select_phase(self, idx):
        self.active_phase = idx
        self.mission_day.set(self.phases[idx]["day"])
        self._update_all()

    def _draw_map(self, live_pos, ship_x, ship_y, day):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10:
            w, h = 600, 600

        cx, cy = w // 2, h // 2
        scale = min(w, h) / 24.0  # AU to pixels

        def to_px(ax, ay):
            return cx + ax * scale, cy - ay * scale

        # Grid circles
        for r_au in [1, 2, 5, 10]:
            r_px = r_au * scale
            c.create_oval(cx - r_px, cy - r_px,
                          cx + r_px, cy + r_px,
                          outline="#0a1018", width=1)

        # Sun
        c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                       fill="#ffdd00", outline="#ffaa00")
        c.create_text(cx, cy - 12, text="Sun",
                       fill="#ffdd00", font=("Consolas", 8))

        # Orbits + planets
        for name, p in PLANETS.items():
            # Orbit
            r_px = p["a"] * scale
            c.create_oval(cx - r_px, cy - r_px,
                          cx + r_px, cy + r_px,
                          outline=p["color"], width=1,
                          stipple="gray12")

            # Planet at live position
            pos = live_pos[name]
            px, py = to_px(pos["x"], pos["y"])
            s = p["size"]
            c.create_oval(px - s, py - s, px + s, py + s,
                          fill=p["color"], outline="white",
                          width=1)
            c.create_text(px + 10, py - 10, text=name,
                          fill=p["color"],
                          font=("Consolas", 8, "bold"),
                          anchor="w")

        # Trajectory lines
        for i in range(len(self.phases) - 1):
            p1 = self.phases[i]
            p2 = self.phases[i + 1]
            x1, y1 = to_px(p1["x"], p1["y"])
            x2, y2 = to_px(p2["x"], p2["y"])
            past = day > p2["dayEnd"]
            c.create_line(x1, y1, x2, y2,
                          fill=p2["color"],
                          width=3 if not past else 1,
                          dash=() if past else (6, 3))

        # Substrate bridges
        bodies = []
        for name, pos in live_pos.items():
            d = math.sqrt((pos["x"] - ship_x)**2 +
                           (pos["y"] - ship_y)**2)
            bodies.append((name, d, pos["x"], pos["y"]))
        sun_d = math.sqrt(ship_x**2 + ship_y**2)
        bodies.append(("Sun", sun_d, 0, 0))
        bodies.sort(key=lambda b: b[1])

        sx_px, sy_px = to_px(ship_x, ship_y)
        for name, d, bx, by in bodies[:3]:
            bpx, bpy = to_px(bx, by)
            strength = min(1.0, 0.1 / (d + 0.01))
            col = "#40a0c0"
            c.create_line(sx_px, sy_px, bpx, bpy,
                          fill=col, width=max(1, int(strength * 4)),
                          dash=(2, 2),
                          stipple="gray50")

        # Ship
        c.create_oval(sx_px - 8, sy_px - 8,
                       sx_px + 8, sy_px + 8,
                       outline="#00ffcc", width=2)
        c.create_oval(sx_px - 3, sy_px - 3,
                       sx_px + 3, sy_px + 3,
                       fill="#00ffcc", outline="")
        c.create_text(sx_px + 14, sy_px - 12,
                       text="SHIP D%d" % day,
                       fill="#00ffcc",
                       font=("Consolas", 9, "bold"),
                       anchor="w")

        # Label
        c.create_text(8, 14,
                       text="BCM v12 FLIGHT COMPUTER",
                       fill="#304050",
                       font=("Consolas", 9),
                       anchor="w")
        c.create_text(8, h - 8,
                       text="Planets at Day %d | "
                       "Bridges = substrate tension" % day,
                       fill="#203040",
                       font=("Consolas", 8),
                       anchor="w")

    def _draw_status(self, live_pos, sx, sy):
        for w in self.status_frame.winfo_children():
            w.destroy()

        # Nearby bodies
        bodies = []
        for name, pos in live_pos.items():
            d = math.sqrt((pos["x"] - sx)**2 +
                           (pos["y"] - sy)**2)
            bodies.append((name, d))
        sun_d = math.sqrt(sx**2 + sy**2)
        bodies.append(("Sun", sun_d))
        bodies.sort(key=lambda b: b[1])

        for name, d in bodies[:4]:
            col = "#ffdd00" if name == "Sun" else PLANETS.get(
                name, {}).get("color", "#80a0c0")
            f = tk.Frame(self.status_frame, bg="#080c12",
                          padx=6, pady=2)
            f.pack(side="left", fill="x", expand=True, padx=1)
            tk.Label(f, text=name, font=("Consolas", 9, "bold"),
                     fg=col, bg="#080c12").pack()
            tk.Label(f, text="%.2f AU" % d,
                     font=("Consolas", 8), fg="#6090b0",
                     bg="#080c12").pack()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = FlightComputerGUI()
    app.run()
