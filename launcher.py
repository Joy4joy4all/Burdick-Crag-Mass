# -*- coding: utf-8 -*-
"""
SUBSTRATE SOLVER — Observatory Launcher
Stephen Justin Burdick, 2026 — Emerald Entities LLC

Live observation GUI with progress bar, real-time heatmap,
dynamic canvas, error dialogs, and SPARC batch runner.

Usage: python launcher.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import numpy as np
import time
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.rotation_compare import compare_rotation, print_comparison, reset_calibration, get_calibration_stats
from core.substrate_solver import SubstrateSolver, gaussian_source, point_source
try:
    from Burdick_Crag_Mass_Genesis_Renderer import GenesisRenderer
    _GENESIS_AVAILABLE = True
except ImportError:
    _GENESIS_AVAILABLE = False


class SolverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SUBSTRATE SOLVER — Circumpunct Coherence Engine")
        self.root.geometry("1400x1000")
        self.root.configure(bg="#0a0c10")
        self.root.minsize(800, 600)
        self.root.state("zoomed")
        self.running = False
        self.results_history = []
        self._last_rho_avg = None
        self._last_galaxy  = ""
        self.galaxy_catalog = {}
        self.last_selected_galaxy = None
        self._last_psi = None
        self._last_phi = None
        self._last_label = ""
        self._canvas_w = 500
        self._canvas_h = 380
        self._build_ui()
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.log("SUBSTRATE SOLVER initialized.")
        self.log("Space is not a container. Space is a maintenance cost.")
        self.log("─" * 55)

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Title.TLabel", font=("Georgia", 18), foreground="#d0d8e8", background="#0a0c10")
        style.configure("Sub.TLabel", font=("Consolas", 10), foreground="#6a7a90", background="#0a0c10")
        style.configure("TLabel", font=("Consolas", 11), foreground="#a0b0cc", background="#12151c")
        style.configure("TFrame", background="#12151c")
        style.configure("Dark.TFrame", background="#0a0c10")
        style.configure("TButton", font=("Consolas", 11), padding=4)
        style.configure("Run.TButton", font=("Consolas", 13, "bold"), padding=6)
        style.configure("TLabelframe", background="#12151c", foreground="#7a9abb")
        style.configure("TLabelframe.Label", font=("Consolas", 11, "bold"), foreground="#7a9abb", background="#12151c")
        style.configure("green.Horizontal.TProgressbar", troughcolor="#0c1018", background="#40aa60")

        # Header
        header = ttk.Frame(self.root, style="Dark.TFrame")
        header.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(header, text="SUBSTRATE SOLVER", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Circumpunct Coherence Engine  —  Burdick 2026", style="Sub.TLabel").pack(side="left", padx=(20, 0))

        # Progress bar
        pf = ttk.Frame(self.root, style="Dark.TFrame")
        pf.pack(fill="x", padx=12, pady=(0, 4))
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(pf, variable=self.progress_var, maximum=100, style="green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", side="left", expand=True, padx=(0, 8))
        self.progress_label = ttk.Label(pf, text="Ready", style="Sub.TLabel", width=30)
        self.progress_label.pack(side="right")

        # ── Notebook — Tab 1: Galactic Solver / Tab 2: Planetary ──
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=4)

        # Tab 1 — Galactic Solver
        tab1 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab1, text="  GALACTIC SOLVER  ")

        # Tab 2 — Planetary Analysis
        tab2 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab2, text="  PLANETARY  ")

        # Tab 3 — Stellar Wave Analysis
        tab3 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab3, text="  STELLAR  ")

        # Tab 4 — Black Hole Inspiral
        tab4 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab4, text="  BLACK HOLES  ")

        # Tab 5 — Lambda Drive Navigation
        tab5 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab5, text="  \u039B DRIVE  ")

        # Tab 6 — TITS Probe Navigator
        tab6 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab6, text="  TITS PROBES  ")

        # Tab 7 — Test Runner (all versions)
        tab7 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab7, text="  TEST RUNNER  ")

        # Tab 8 — EPIC Collector (substrate test ingestion)
        tab8 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab8, text="  EPIC COLLECTOR  ")

        # Build planetary tab content
        self._build_planetary_tab(tab2)

        # Build stellar tab content
        self._build_stellar_tab(tab3)

        # Build black hole tab content
        self._build_blackhole_tab(tab4)

        # Build lambda drive tab content
        self._build_lambda_tab(tab5)

        # Build TITS probe tab content
        self._build_probe_tab(tab6)

        # Build test runner tab content
        self._build_test_runner_tab(tab7)

        # Build EPIC collector tab content
        self._build_epic_tab(tab8)

        # Main split (Tab 1 content)
        main = tab1

        # ── Scrollable left panel ──
        left_container = tk.Frame(main, bg="#0a0c10", width=420)
        left_container.pack(side="left", fill="y", padx=(0,6))
        left_container.pack_propagate(False)

        left_canvas = tk.Canvas(left_container, bg="#0a0c10",
                                highlightthickness=0, width=400)
        left_vscroll = ttk.Scrollbar(left_container, orient="vertical",
                                     command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_vscroll.set)
        left_vscroll.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)

        left = tk.Frame(left_canvas, bg="#0a0c10")
        left_frame_id = left_canvas.create_window((0,0), window=left, anchor="nw")

        def _resize_left(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        def _resize_canvas(event):
            left_canvas.itemconfig(left_frame_id, width=event.width)
        left.bind("<Configure>", _resize_left)
        left_canvas.bind("<Configure>", _resize_canvas)

        def _on_wheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        left_canvas.bind("<MouseWheel>", _on_wheel)
        left.bind("<MouseWheel>", _on_wheel)

        # ── Right panel ──
        right = ttk.Frame(main, style="Dark.TFrame")
        right.pack(side="left", fill="both", expand=True)

        self._build_controls(left)
        self._build_output(right)

        # Bind mousewheel to all child widgets in left panel
        def _bind_wheel(widget):
            widget.bind("<MouseWheel>", _on_wheel)
            for child in widget.winfo_children():
                _bind_wheel(child)
        self.root.after(200, lambda: _bind_wheel(left))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, style="Sub.TLabel").pack(fill="x", padx=12, pady=(0, 6))

    def _build_planetary_tab(self, parent):
        """Tab 2 — BCM Planetary Scale Analysis (Saturn hexagon)."""
        style_bg  = "#0a0c10"
        style_fg  = "#a0b0cc"
        style_acc = "#ffbb44"
        style_grn = "#40ee70"

        # ── Header ──
        hf = tk.Frame(parent, bg=style_bg)
        hf.pack(fill="x", padx=12, pady=(10,4))
        tk.Label(hf, text="BCM PLANETARY WAVE SOLVER",
                 font=("Georgia", 16), fg="#d0d8e8", bg=style_bg).pack(side="left")
        tk.Label(hf, text="Solar System Substrate Scale-Invariance — Select Planet",
                 font=("Consolas", 10), fg="#6a7a90", bg=style_bg).pack(side="left", padx=(16,0))

        # ── File Tree ──
        tf = ttk.LabelFrame(parent, text="FILE LOCATIONS")
        tf.pack(fill="x", padx=12, pady=4)
        tree_text = 'C:/TITS/SUBSTRATE_SOLVER/\n|   BCM_planetary_wave.py          <- planetary solver script\n|   launcher.py                    <- this GUI\n|   BCM_Substrate_overrides.py     <- galaxy override system\n|\n+---data/\n    +---hi_maps/                   <- HI FITS files (NGC2976, NGC7793, UGC04305)\n    +---sparc_raw/                 <- 175 SPARC .dat files (subdirs by mass)\n    +---results/                   <- ALL JSON output goes here\n            BCM_NGC3953_ClassVI_BarDipole_Confirmed.json\n            BCM_NGC7793_ClassVB_SubstrateTheft_Confirmed.json\n            BCM_NGC2841_ClassI_Control_Baseline.json\n            BCM_Saturn_planetary_wave.json     <- planetary run output\n            batch_20260327_140314.json         <- 175-galaxy batch\n'
        tree_box = tk.Text(tf, height=14, bg="#0c0e14", fg="#70a0c0",
                           font=("Consolas", 9), relief="flat", state="normal")
        tree_box.insert("1.0", tree_text)
        tree_box.config(state="disabled")
        tree_box.pack(fill="x", padx=6, pady=4)

        # ── Planet Selector ──
        self._planet_registry = {}
        self._load_planet_registry()

        sf = ttk.LabelFrame(parent, text="SELECT PLANET")
        sf.pack(fill="x", padx=12, pady=4)
        sel_f = tk.Frame(sf, bg="#12151c")
        sel_f.pack(fill="x", padx=6, pady=4)

        self.planet_select_var = tk.StringVar(value="Saturn")
        planet_names = list(self._planet_registry.keys()) if self._planet_registry else [
            "Mercury","Venus","Earth","Mars",
            "Jupiter","Saturn","Uranus","Neptune"]
        planet_menu = ttk.Combobox(sel_f, textvariable=self.planet_select_var,
                                    values=planet_names, width=14,
                                    font=("Consolas", 11), state="readonly")
        planet_menu.pack(side="left", padx=(0,8))
        planet_menu.bind("<<ComboboxSelected>>", self._on_planet_select)

        self.planet_info_var = tk.StringVar(value="Saturn — m=6 hexagonal lock")
        tk.Label(sel_f, textvariable=self.planet_info_var,
                 font=("Consolas", 9), fg="#ffbb44",
                 bg="#12151c").pack(side="left")

        # ── Planet Parameters ──
        pf = ttk.LabelFrame(parent, text="PLANET PARAMETERS")
        pf.pack(fill="x", padx=12, pady=4)

        self.sat_omega    = tk.StringVar(value="1.638e-4")
        self.sat_B        = tk.StringVar(value="5.5e-5")
        self.sat_sigma    = tk.StringVar(value="1.3e6")
        self.sat_depth    = tk.StringVar(value="5.12e7")
        self.sat_rossby   = tk.StringVar(value="3.0e6")
        self.sat_m_obs    = tk.StringVar(value="6")

        params = [
            ("Ω  rotation (rad/s):",    self.sat_omega),
            ("B  dynamo field (T):",     self.sat_B),
            ("σ  conductivity (S/m):",   self.sat_sigma),
            ("Depth pump layer (m):",    self.sat_depth),
            ("L  Rossby radius (m):",    self.sat_rossby),
            ("m  observed mode:",        self.sat_m_obs),
        ]
        for i, (label, var) in enumerate(params):
            tk.Label(pf, text=label, font=("Consolas", 10),
                     fg=style_fg, bg="#12151c").grid(
                         row=i, column=0, sticky="w", padx=10, pady=2)
            ttk.Entry(pf, textvariable=var, width=14).grid(
                row=i, column=1, padx=6, pady=2)

        # ── Run Options ──
        rf = ttk.LabelFrame(parent, text="RUN OPTIONS")
        rf.pack(fill="x", padx=12, pady=4)
        self.planet_solve_lam  = tk.BooleanVar(value=True)
        self.planet_decay      = tk.BooleanVar(value=True)
        ttk.Checkbutton(rf, text="Back-calculate λ_planetary from m=6",
                        variable=self.planet_solve_lam).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(rf, text="Storm decay analysis (χ from Cassini data)",
                        variable=self.planet_decay).pack(anchor="w", padx=10, pady=2)

        # ── Run Button ──
        bf = ttk.Frame(parent, style="Dark.TFrame")
        bf.pack(fill="x", padx=12, pady=6)
        ttk.Button(bf, text="▶  RUN PLANETARY SOLVER",
                   style="Run.TButton",
                   command=self._run_planetary).pack(fill="x", padx=4, pady=2)
        ttk.Button(bf, text="⬡  Open Planetary Renderer",
                   command=self._open_planetary_renderer).pack(fill="x", padx=4, pady=2)

        # ── Output Log ──
        lf = ttk.LabelFrame(parent, text="PLANETARY LOG")
        lf.pack(fill="both", expand=True, padx=12, pady=4)
        self.planet_log = tk.Text(lf, height=12, bg="#0c0e14", fg="#c0d8e8",
                                  font=("Consolas", 10), relief="flat",
                                  insertbackground="#c0d8e8")
        ps = ttk.Scrollbar(lf, orient="vertical", command=self.planet_log.yview)
        self.planet_log.configure(yscrollcommand=ps.set)
        self.planet_log.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        ps.pack(side="right", fill="y")
        self.planet_log.insert("end",
            "BCM Planetary Wave Solver ready.\n"
            "Saturn North Polar Hexagon — m=6 scale-invariance test.\n"
            "Output JSON → data/results/BCM_Saturn_planetary_wave.json\n"
            "─" * 55 + "\n")
        self.planet_log.config(state="disabled")

    def _planet_log(self, msg):
        """Write to planetary tab log."""
        self.planet_log.config(state="normal")
        self.planet_log.insert("end", msg + "\n")
        self.planet_log.see("end")
        self.planet_log.config(state="disabled")
        self.root.update_idletasks()

    def _run_planetary(self):
        """Run BCM_planetary_wave.py as subprocess and stream output to log."""
        import subprocess, threading

        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "BCM_planetary_wave.py")
        if not os.path.exists(script):
            self._planet_log("ERROR: BCM_planetary_wave.py not found in root dir.")
            self._planet_log(f"Expected: {script}")
            return

        args = [sys.executable, script]
        # Pass selected planet and registry path
        planet = self.planet_select_var.get()
        if planet:
            args += ["--planet", planet]
        reg = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "data", "results", "BCM_solar_system_registry.json")
        if os.path.exists(reg):
            args += ["--registry", reg]
        if self.planet_solve_lam.get():
            args.append("--solve-lambda")
        if self.planet_decay.get():
            args.append("--decay-analysis")

        self._planet_log(f"Running: {' '.join(args)}")
        self._planet_log("─" * 55)

        def _run():
            try:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        text=True,
                                        cwd=os.path.dirname(os.path.abspath(__file__)))
                for line in proc.stdout:
                    self.root.after(0, lambda l=line.rstrip(): self._planet_log(l))
                proc.wait()
                self.root.after(0, lambda: self._planet_log(
                    "─" * 55 + "\nDone. Check data/results/ for JSON output."))
            except Exception as e:
                self.root.after(0, lambda: self._planet_log(f"ERROR: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _load_planet_registry(self):
        """Load solar system registry JSON if available."""
        base = os.path.dirname(os.path.abspath(__file__))
        reg_path = os.path.join(base, "data", "results",
                                "BCM_solar_system_registry.json")
        if os.path.exists(reg_path):
            try:
                with open(reg_path) as f:
                    data = json.load(f)
                self._planet_registry = data.get("planets", {})
            except Exception:
                self._planet_registry = {}

    def _on_planet_select(self, event=None):
        """Load selected planet parameters into the fields."""
        name = self.planet_select_var.get()
        p = self._planet_registry.get(name, {})
        if not p:
            return

        # Update parameter fields
        self.sat_omega.set(f"{abs(p.get('omega_rad_s', 1.638e-4)):.4e}")
        self.sat_B.set(f"{p.get('B_field_tesla', 5.5e-5):.3e}")
        self.sat_sigma.set(f"{p.get('sigma_sm', 1.3e6):.3e}")
        depth_m = p.get('pump_depth_km', 15000) * 1000
        self.sat_depth.set(f"{depth_m:.3e}")
        # Rossby radius approximation: 5% of polar radius
        R_m = p.get('radius_km', 58232) * 1000 * 0.95
        L_R = max(R_m * 0.05, 1e5)
        self.sat_rossby.set(f"{L_R:.3e}")
        self.sat_m_obs.set(str(p.get('m_observed', 0)))

        # Update info label
        cls = p.get('bcm_class', '')[:40]
        m   = p.get('m_observed', '?')
        self.planet_info_var.set(f"{name} — m={m}  {cls}")
        self._planet_log(f"  Loaded: {name}  m_obs={m}  "
                         f"Ω={abs(p.get('omega_rad_s',0)):.3e} rad/s")

    def _open_planetary_renderer(self):
        """Open BCM Planetary Renderer — loads last planet run."""
        try:
            from BCM_planetary_renderer import PlanetaryRenderer
            base = os.path.dirname(os.path.abspath(__file__))
            results_dir = os.path.join(base, "data", "results")
            # Check last_run pointer first
            json_path = None
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
            # Fallback
            if not json_path:
                planet = self.planet_select_var.get()
                fallback = os.path.join(results_dir, f"BCM_{planet}_planetary_wave.json")
                json_path = fallback if os.path.exists(fallback) else None
            PlanetaryRenderer(self.root, json_path)
        except ImportError:
            self._planet_log("ERROR: BCM_planetary_renderer.py not found in root dir.")
        except Exception as e:
            self._planet_log(f"Renderer error: {e}")

    # ──────────────────────────────────────────────────
    # TAB 3 — STELLAR WAVE SOLVER
    # ──────────────────────────────────────────────────

    def _build_stellar_tab(self, parent):
        """Tab 3 — BCM Stellar Wave Analysis (tachocline substrate scale-invariance)."""
        style_bg  = "#0a0c10"
        style_fg  = "#a0b0cc"
        style_acc = "#ffbb44"

        # ── Scrollable container for stellar tab ──
        scroll_canvas = tk.Canvas(parent, bg=style_bg, highlightthickness=0)
        scroll_vbar = ttk.Scrollbar(parent, orient="vertical",
                                     command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scroll_vbar.set)
        scroll_vbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        sf = tk.Frame(scroll_canvas, bg=style_bg)
        sf_id = scroll_canvas.create_window((0, 0), window=sf, anchor="nw")

        def _sf_resize(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        def _sc_resize(event):
            scroll_canvas.itemconfig(sf_id, width=event.width)
        sf.bind("<Configure>", _sf_resize)
        scroll_canvas.bind("<Configure>", _sc_resize)

        def _sf_wheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_canvas.bind("<MouseWheel>", _sf_wheel)
        sf.bind("<MouseWheel>", _sf_wheel)

        # All stellar content goes in sf (scrollable frame)
        parent = sf

        # ── Header ──
        hf = tk.Frame(parent, bg=style_bg)
        hf.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(hf, text="BCM STELLAR WAVE SOLVER",
                 font=("Georgia", 16), fg="#d0d8e8", bg=style_bg).pack(side="left")
        tk.Label(hf, text="Tachocline Substrate Scale-Invariance — Select Star",
                 font=("Consolas", 10), fg="#6a7a90", bg=style_bg).pack(side="left", padx=(16, 0))

        # ── File Tree ──
        tf = ttk.LabelFrame(parent, text="FILE LOCATIONS")
        tf.pack(fill="x", padx=12, pady=4)
        tree_text = (
            'C:/TITS/SUBSTRATE_SOLVER/\n'
            '|   BCM_stellar_wave.py           <- stellar solver script\n'
            '|   launcher.py                   <- this GUI\n'
            '|\n'
            '+---data/\n'
            '    +---results/\n'
            '            BCM_stellar_registry.json        <- star parameter database\n'
            '            BCM_Sun_stellar_wave.json        <- per-star output\n'
            '            BCM_stellar_batch.json           <- batch summary\n'
            '            BCM_stellar_last_run.json        <- last run pointer\n'
        )
        tree_box = tk.Text(tf, height=10, bg="#0c0e14", fg="#70a0c0",
                           font=("Consolas", 9), relief="flat", state="normal")
        tree_box.insert("1.0", tree_text)
        tree_box.config(state="disabled")
        tree_box.pack(fill="x", padx=6, pady=4)

        # ── Star Selector ──
        self._stellar_registry = {}
        self._load_stellar_registry()

        sf = ttk.LabelFrame(parent, text="SELECT STAR")
        sf.pack(fill="x", padx=12, pady=4)
        sel_f = tk.Frame(sf, bg="#12151c")
        sel_f.pack(fill="x", padx=6, pady=4)

        self.star_select_var = tk.StringVar(value="Sun")
        star_names = list(self._stellar_registry.keys()) if self._stellar_registry else [
            "Sun", "Tabby", "Proxima", "EV_Lac", "HR_1099"]
        star_menu = ttk.Combobox(sel_f, textvariable=self.star_select_var,
                                 values=star_names, width=14,
                                 font=("Consolas", 11), state="readonly")
        star_menu.pack(side="left", padx=(0, 8))
        star_menu.bind("<<ComboboxSelected>>", self._on_star_select)

        self.star_info_var = tk.StringVar(value="Sun — G2V — m=4 solar wind")
        tk.Label(sel_f, textvariable=self.star_info_var,
                 font=("Consolas", 9), fg=style_acc,
                 bg="#12151c").pack(side="left")

        # ── Star Parameters (read-only display) ──
        pf = ttk.LabelFrame(parent, text="STAR PARAMETERS")
        pf.pack(fill="x", padx=12, pady=4)

        self.star_spectral   = tk.StringVar(value="G2V")
        self.star_mass       = tk.StringVar(value="1.0")
        self.star_radius     = tk.StringVar(value="695700")
        self.star_rotation   = tk.StringVar(value="25.38")
        self.star_B_tach     = tk.StringVar(value="1.0e-1")
        self.star_sigma      = tk.StringVar(value="1.0e4")
        self.star_v_conv     = tk.StringVar(value="300.0")
        self.star_m_obs      = tk.StringVar(value="4")

        params = [
            ("Spectral type:",            self.star_spectral),
            ("Mass (M☉):",                self.star_mass),
            ("Radius (km):",              self.star_radius),
            ("Rotation (days):",          self.star_rotation),
            ("B tachocline (T):",         self.star_B_tach),
            ("σ tachocline (S/m):",       self.star_sigma),
            ("v_conv (m/s):",             self.star_v_conv),
            ("m observed:",               self.star_m_obs),
        ]
        for i, (label, var) in enumerate(params):
            tk.Label(pf, text=label, font=("Consolas", 10),
                     fg=style_fg, bg="#12151c").grid(
                         row=i, column=0, sticky="w", padx=10, pady=2)
            ttk.Entry(pf, textvariable=var, width=14).grid(
                row=i, column=1, padx=6, pady=2)

        # ── Run Options ──
        rf = ttk.LabelFrame(parent, text="RUN OPTIONS")
        rf.pack(fill="x", padx=12, pady=4)
        self.stellar_solve_lam = tk.BooleanVar(value=True)
        self.stellar_batch     = tk.BooleanVar(value=False)
        ttk.Checkbutton(rf, text="Back-calculate λ_stellar from observed m",
                        variable=self.stellar_solve_lam).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(rf, text="Run full stellar batch (all stars in registry)",
                        variable=self.stellar_batch).pack(anchor="w", padx=10, pady=2)

        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        # Binary pair selector and orbital phase
        bin_f = tk.Frame(rf, bg="#12151c")
        bin_f.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(bin_f, text="Binary Pair:",
                 font=("Consolas", 10), fg="#a0b0cc",
                 bg="#12151c").pack(side="left")
        self._binary_pairs = []
        try:
            from BCM_stellar_overrides import BINARY_REGISTRY
            self._binary_pairs = list(BINARY_REGISTRY.keys())
        except ImportError:
            pass
        self.binary_select_var = tk.StringVar(
            value=self._binary_pairs[0] if self._binary_pairs else "")
        binary_menu = ttk.Combobox(bin_f, textvariable=self.binary_select_var,
                                    values=self._binary_pairs, width=14,
                                    font=("Consolas", 10), state="readonly")
        binary_menu.pack(side="left", padx=(6, 8))

        tk.Label(bin_f, text="Phase:",
                 font=("Consolas", 10), fg="#a0b0cc",
                 bg="#12151c").pack(side="left")
        self.orbital_phase_var = tk.DoubleVar(value=0.5)
        ttk.Spinbox(bin_f, from_=0.0, to=1.0, increment=0.1,
                    textvariable=self.orbital_phase_var, width=5,
                    font=("Consolas", 10)).pack(side="left", padx=(4, 4))
        tk.Label(bin_f, text="(0=peri 1=apo)",
                 font=("Consolas", 8), fg="#6a7a90",
                 bg="#12151c").pack(side="left")

        # Solver parameters for stellar/binary runs
        sp_f = tk.Frame(rf, bg="#12151c")
        sp_f.pack(fill="x", padx=10, pady=(4, 2))
        tk.Label(sp_f, text="Grid:", font=("Consolas", 10),
                 fg="#a0b0cc", bg="#12151c").pack(side="left")
        self.stellar_grid_var = tk.IntVar(value=64)
        ttk.Spinbox(sp_f, from_=32, to=256, increment=32,
                    textvariable=self.stellar_grid_var, width=5,
                    font=("Consolas", 10)).pack(side="left", padx=(4, 8))
        tk.Label(sp_f, text="Settle:", font=("Consolas", 10),
                 fg="#a0b0cc", bg="#12151c").pack(side="left")
        self.stellar_settle_var = tk.IntVar(value=15000)
        ttk.Spinbox(sp_f, from_=5000, to=50000, increment=5000,
                    textvariable=self.stellar_settle_var, width=7,
                    font=("Consolas", 10)).pack(side="left", padx=(4, 8))
        tk.Label(sp_f, text="Measure:", font=("Consolas", 10),
                 fg="#a0b0cc", bg="#12151c").pack(side="left")
        self.stellar_measure_var = tk.IntVar(value=5000)
        ttk.Spinbox(sp_f, from_=1000, to=20000, increment=1000,
                    textvariable=self.stellar_measure_var, width=6,
                    font=("Consolas", 10)).pack(side="left", padx=(4, 4))
        # === END ADDITION ===

        # ── Run Button ──
        bf = ttk.Frame(parent, style="Dark.TFrame")
        bf.pack(fill="x", padx=12, pady=6)
        ttk.Button(bf, text="▶  RUN STELLAR SOLVER",
                   style="Run.TButton",
                   command=self._run_stellar).pack(fill="x", padx=4, pady=2)
        # === BCM MASTER BUILD ADDITION v2.2 | 2026-04-03 EST ===
        ttk.Button(bf, text="★  Open Stellar Renderer",
                   command=self._open_stellar_renderer).pack(fill="x", padx=4, pady=2)
        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        ttk.Button(bf, text="⬡  Run Binary Substrate Bridge",
                   command=self._run_binary).pack(fill="x", padx=4, pady=2)
        # === BCM MASTER BUILD ADDITION v9 | 2026-04-04 EST ===
        ttk.Button(bf, text="◆  Render 3D Binary Field",
                   command=self._run_3d_renderer).pack(fill="x", padx=4, pady=2)

        # ── Output Log ──
        lf = ttk.LabelFrame(parent, text="STELLAR LOG")
        lf.pack(fill="both", expand=True, padx=12, pady=4)
        self.stellar_log = tk.Text(lf, height=12, bg="#0c0e14", fg="#c0d8e8",
                                   font=("Consolas", 10), relief="flat",
                                   insertbackground="#c0d8e8")
        ss = ttk.Scrollbar(lf, orient="vertical", command=self.stellar_log.yview)
        self.stellar_log.configure(yscrollcommand=ss.set)
        self.stellar_log.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        ss.pack(side="right", fill="y")
        self.stellar_log.insert("end",
            "BCM Stellar Wave Solver ready.\n"
            "Tachocline substrate scale-invariance test.\n"
            "Output JSON → data/results/BCM_<star>_stellar_wave.json\n"
            "─" * 55 + "\n")
        self.stellar_log.config(state="disabled")

        # Bind mousewheel to all children for scrolling
        def _bind_stellar_wheel(widget):
            widget.bind("<MouseWheel>", _sf_wheel)
            for child in widget.winfo_children():
                _bind_stellar_wheel(child)
        self.root.after(200, lambda: _bind_stellar_wheel(sf))

    def _stellar_log_msg(self, msg):
        """Write to stellar tab log."""
        self.stellar_log.config(state="normal")
        self.stellar_log.insert("end", msg + "\n")
        self.stellar_log.see("end")
        self.stellar_log.config(state="disabled")
        self.root.update_idletasks()

    def _load_stellar_registry(self):
        """Load stellar registry JSON if available."""
        base = os.path.dirname(os.path.abspath(__file__))
        reg_path = os.path.join(base, "data", "results",
                                "BCM_stellar_registry.json")
        if os.path.exists(reg_path):
            try:
                with open(reg_path) as f:
                    data = json.load(f)
                self._stellar_registry = data.get("stars", {})
            except Exception:
                self._stellar_registry = {}

    def _on_star_select(self, event=None):
        """Load selected star parameters into the fields."""
        name = self.star_select_var.get()
        s = self._stellar_registry.get(name, {})
        if not s:
            return

        self.star_spectral.set(s.get("spectral_type", ""))
        self.star_mass.set(f"{s.get('mass_solar', 0)}")
        self.star_radius.set(f"{s.get('radius_km', 0):.0f}")
        self.star_rotation.set(f"{s.get('rotation_days', 0)}")
        self.star_B_tach.set(f"{s.get('B_tachocline_T', 0):.3e}")
        self.star_sigma.set(f"{s.get('sigma_tach_sm', 0):.3e}")
        self.star_v_conv.set(f"{s.get('v_conv_ms', 0):.1f}")
        self.star_m_obs.set(str(s.get("m_observed", 0)))

        cls = s.get("bcm_class", "")[:40]
        m   = s.get("m_observed", "?")
        self.star_info_var.set(f"{name} — {s.get('spectral_type','')} — m={m}  {cls}")
        self._stellar_log_msg(f"  Loaded: {name}  m_obs={m}  "
                              f"B_tach={s.get('B_tachocline_T',0):.3e} T  "
                              f"rot={s.get('rotation_days',0)} d")

    def _run_stellar(self):
        """Run BCM_stellar_wave.py as subprocess and stream output to log."""
        self._binary_data = None  # clear binary mode
        import subprocess

        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "BCM_stellar_wave.py")
        if not os.path.exists(script):
            self._stellar_log_msg("ERROR: BCM_stellar_wave.py not found in root dir.")
            self._stellar_log_msg(f"Expected: {script}")
            return

        args = [sys.executable, script]

        if self.stellar_batch.get():
            args.append("--batch")
        else:
            star = self.star_select_var.get()
            if star:
                args += ["--star", star]

        if self.stellar_solve_lam.get():
            args.append("--solve-lambda")

        self._stellar_log_msg(f"Running: {' '.join(args)}")
        self._stellar_log_msg("─" * 55)

        def _run():
            try:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        text=True,
                                        cwd=os.path.dirname(os.path.abspath(__file__)))
                for line in proc.stdout:
                    self.root.after(0, lambda l=line.rstrip(): self._stellar_log_msg(l))
                proc.wait()
                self.root.after(0, lambda: self._stellar_log_msg(
                    "─" * 55 + "\nDone. Check data/results/ for JSON output."))
            except Exception as e:
                self.root.after(0, lambda: self._stellar_log_msg(f"ERROR: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    # === BCM MASTER BUILD ADDITION v2.2 | 2026-04-03 EST ===
    def _open_stellar_renderer(self):
        """Open BCM Stellar Renderer — loads last stellar run or binary result."""
        try:
            from BCM_stellar_renderer import StellarRenderer
            # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
            # Check for binary data first
            if hasattr(self, '_binary_data') and self._binary_data:
                # Close live window if still open
                if hasattr(self, '_binary_win') and self._binary_win:
                    try:
                        self._binary_win.destroy()
                    except Exception:
                        pass
                    self._binary_win = None
                StellarRenderer(self.root,
                                binary_data=self._binary_data)
                return
            # === END ADDITION ===
            base = os.path.dirname(os.path.abspath(__file__))
            results_dir = os.path.join(base, "data", "results")
            json_path = None
            last_run = os.path.join(results_dir, "BCM_stellar_last_run.json")
            if os.path.exists(last_run):
                try:
                    with open(last_run) as f:
                        lr = json.load(f)
                    candidate = os.path.join(results_dir, lr.get("last_file", ""))
                    if os.path.exists(candidate):
                        json_path = candidate
                except Exception:
                    pass
            if not json_path:
                star = self.star_select_var.get()
                fallback = os.path.join(results_dir,
                                        f"BCM_{star}_stellar_wave.json")
                json_path = fallback if os.path.exists(fallback) else None
            StellarRenderer(self.root, json_path=json_path,
                            star_name=self.star_select_var.get())
        except ImportError:
            self._stellar_log_msg(
                "ERROR: BCM_stellar_renderer.py not found in root dir.")
        except Exception as e:
            self._stellar_log_msg(f"Renderer error: {e}")

    # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
    def _run_binary(self):
        """Run binary substrate bridge with live wave propagation window."""
        pair_name = self.binary_select_var.get()
        if not pair_name:
            self._stellar_log_msg("ERROR: No binary pair selected.")
            return

        phase = self.orbital_phase_var.get()
        grid = self.stellar_grid_var.get()
        settle = self.stellar_settle_var.get()
        measure = self.stellar_measure_var.get()

        self._stellar_log_msg(f"\n{'═'*55}")
        self._stellar_log_msg(f"  BINARY SUBSTRATE BRIDGE — {pair_name}")
        self._stellar_log_msg(f"  grid={grid}  settle={settle}  measure={measure}  phase={phase:.2f}")
        self._stellar_log_msg(f"{'═'*55}")

        # ── Open live animation window ──
        self._binary_win = tk.Toplevel(self.root)
        self._binary_win.title(f"BCM BINARY WAVE PROPAGATION — {pair_name}")
        self._binary_win.geometry("900x750")
        self._binary_win.configure(bg="#080a0e")

        # Header
        hf = tk.Frame(self._binary_win, bg="#080a0e")
        hf.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(hf, text=f"BINARY SUBSTRATE BRIDGE — {pair_name}",
                 font=("Georgia", 14), fg="#e0e8f0",
                 bg="#080a0e").pack(side="left")
        self._binary_status = tk.StringVar(value="Initializing...")
        tk.Label(hf, textvariable=self._binary_status,
                 font=("Consolas", 10), fg="#6a7a90",
                 bg="#080a0e").pack(side="right")

        # Canvas for live wave view
        self._binary_canvas = tk.Canvas(self._binary_win,
            bg="#080a0e", highlightthickness=0)
        self._binary_canvas.pack(fill="both", expand=True, padx=8, pady=4)
        self._binary_cw = 880
        self._binary_ch = 660
        self._binary_canvas.bind("<Configure>", self._on_binary_resize)

        # Store pump info for overlay (set after source build)
        self._binary_pump_info = None

        def _run():
            try:
                from BCM_stellar_overrides import (run_binary, BINARY_REGISTRY,
                                                    build_binary_source)
                pair = BINARY_REGISTRY.get(pair_name)
                if not pair:
                    self.root.after(0, lambda: self._stellar_log_msg(
                        f"ERROR: '{pair_name}' not in BINARY_REGISTRY"))
                    return

                self.root.after(0, lambda: self._stellar_log_msg(
                    f"  {pair.get('description', '')}"))
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"  Class: {pair.get('bcm_class', '')}"))
                self.root.after(0, lambda: self._stellar_log_msg("─" * 55))

                # Build source first to get pump locations
                J_pre, info_pre = build_binary_source(pair, grid=grid,
                                                       orbital_phase=phase)
                self._binary_pump_info = info_pre
                self.root.after(0, lambda: self._binary_status.set(
                    f"Solving... grid={grid} settle={settle}"))

                # Draw initial source field before solver starts
                self.root.after(0, lambda j=J_pre.copy():
                    self._draw_binary_live(
                        j.reshape(1, grid, grid), 0, settle + measure))

                # Live callback — draws rho on the binary canvas
                def _binary_live_cb(step, total, rho, sigma):
                    if step % 500 == 0:
                        self.root.after(0, lambda r=rho.copy(), s=step, t=total:
                            self._draw_binary_live(r, s, t))

                result, J, info = run_binary(
                    pair_name, grid=grid,
                    orbital_phase=phase,
                    settle=settle,
                    measure=measure,
                    verbose=False,
                    callback=_binary_live_cb)

                # Final frame with phase field
                self.root.after(0, lambda: self._draw_binary_final(result, info))

                # Log results
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"  Pump A: {info['star_A']}  amp={info['amp_A']:.1f}"))
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"  Pump B: {info['star_B']}  amp={info['amp_B']:.1f}"))
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"  Separation: {info['sep_AU']:.1f} AU  "
                    f"({info['sep_frac']:.2f} grid frac)"))

                if 'L1_cos_mean' in info:
                    self.root.after(0, lambda: self._stellar_log_msg(
                        f"\n  BRIDGE DIAGNOSTICS:"))
                    self.root.after(0, lambda: self._stellar_log_msg(
                        f"    L1 cos(Δφ) mean: {info['L1_cos_mean']:+.4f}"))
                    self.root.after(0, lambda: self._stellar_log_msg(
                        f"    L1 curl max:     {info['L1_curl_max']:.6f}"))

                corr = result.get("corr_full", 0)
                cdp = result.get("cos_delta_phi", 0)
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"\n  Solver: Ψ~Φ={corr:+.4f}  "
                    f"cos_delta_phi={cdp:+.4f}"))
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"  Elapsed: {result.get('elapsed',0):.1f}s"))

                # Save binary result JSON
                base = os.path.dirname(os.path.abspath(__file__))
                results_dir = os.path.join(base, "data", "results")
                os.makedirs(results_dir, exist_ok=True)
                out_path = os.path.join(results_dir,
                    f"BCM_binary_{pair_name}_{time.strftime('%Y%m%d_%H%M%S')}.json")
                save_data = {
                    "pair": pair_name,
                    "info": {k: v for k, v in info.items()
                             if not isinstance(v, np.ndarray)},
                    "corr_full": float(corr),
                    "cos_delta_phi": float(cdp),
                    "elapsed": result.get("elapsed", 0),
                }
                with open(out_path, 'w') as f:
                    json.dump(save_data, f, indent=2)
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"  Saved: {out_path}"))

                # Store binary data for renderer
                self._binary_data = {
                    'J': J,
                    'cpf': result.get('cos_delta_phi_field'),
                    'dpf': result.get('delta_phi_field'),
                    'rho_avg': result.get('rho_avg'),
                    'info': info,
                    'pair_name': pair_name,
                }

                self.root.after(0, lambda: self._stellar_log_msg(
                    f"\n{'═'*55}\n  BINARY RUN COMPLETE — Click ★ Renderer to view\n{'═'*55}"))

            except ImportError as e:
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"ERROR: {e}"))
                self.root.after(0, lambda: self._binary_status.set(
                    f"IMPORT ERROR — check BCM_stellar_overrides.py"))
            except Exception as e:
                import traceback
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"ERROR: {e}\n{traceback.format_exc()}"))
                self.root.after(0, lambda: self._binary_status.set(
                    f"ERROR: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    # === BCM MASTER BUILD ADDITION v9 | 2026-04-04 EST ===
    def _run_3d_renderer(self):
        """Run 3D azimuthal revolution renderer for the selected binary."""
        pair_name = self.binary_select_var.get()
        if not pair_name:
            self._stellar_log_msg("ERROR: No binary pair selected.")
            return

        phase = self.orbital_phase_var.get()
        grid = self.stellar_grid_var.get()
        settle = self.stellar_settle_var.get()
        measure = self.stellar_measure_var.get()

        self._stellar_log_msg(f"\n{'═'*55}")
        self._stellar_log_msg(f"  3D RENDERER — {pair_name}  phase={phase:.2f}")
        self._stellar_log_msg(f"  grid={grid}  (running solver + revolution...)")
        self._stellar_log_msg(f"{'═'*55}")

        def _run():
            try:
                from BCM_3d_renderer import render_3d
                render_3d(pair_name=pair_name, phase=phase, grid=grid,
                          field_type="sigma", settle=settle,
                          measure=measure, n_theta=48)
                self.root.after(0, lambda: self._stellar_log_msg(
                    "  3D render complete."))
            except ImportError:
                self.root.after(0, lambda: self._stellar_log_msg(
                    "ERROR: BCM_3d_renderer.py not found in root dir."))
            except Exception as e:
                self.root.after(0, lambda: self._stellar_log_msg(
                    f"  3D render error: {e}"))

        threading.Thread(target=_run, daemon=True).start()
    # === END ADDITION ===

    # === BCM v11 BLACK HOLE TAB ===
    def _build_blackhole_tab(self, parent):
        """Tab 4 — BCM Binary Black Hole Inspiral (GW150914 analog)."""
        style_bg  = "#0a0c10"
        style_fg  = "#a0b0cc"
        style_acc = "#ff6644"

        scroll_canvas = tk.Canvas(parent, bg=style_bg, highlightthickness=0)
        scroll_vbar = ttk.Scrollbar(parent, orient="vertical",
                                     command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scroll_vbar.set)
        scroll_vbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        sf = tk.Frame(scroll_canvas, bg=style_bg)
        sf_id = scroll_canvas.create_window((0, 0), window=sf, anchor="nw")

        def _sf_resize(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        def _sc_resize(event):
            scroll_canvas.itemconfig(sf_id, width=event.width)
        sf.bind("<Configure>", _sf_resize)
        scroll_canvas.bind("<Configure>", _sc_resize)

        def _sf_wheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_canvas.bind("<MouseWheel>", _sf_wheel)
        sf.bind("<MouseWheel>", _sf_wheel)

        parent = sf

        # Header
        hf = tk.Frame(parent, bg=style_bg)
        hf.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(hf, text="BCM BLACK HOLE INSPIRAL",
                 font=("Georgia", 16), fg="#ff8844", bg=style_bg).pack(side="left")
        tk.Label(hf, text="GW150914 Analog — Binary Merger Sweep",
                 font=("Consolas", 10), fg="#6a7a90", bg=style_bg).pack(side="left", padx=(16, 0))

        # GW150914 info
        info_f = ttk.LabelFrame(parent, text="GW150914 — FIRST GRAVITATIONAL WAVE DETECTION")
        info_f.pack(fill="x", padx=12, pady=4)
        info_text = (
            "Date: September 14, 2015 (LIGO Hanford + Livingston)\n"
            "Black Hole A: 36 solar masses    Black Hole B: 29 solar masses\n"
            "Mass Ratio: 1.24:1    Final Mass: 62 solar masses\n"
            "Mass Radiated: 3 solar masses (gravitational waves)\n"
            "Distance: 1.3 billion light years    Signal: 0.2 seconds\n"
            "Frequency at merger: ~250 Hz    Velocity: ~0.6c"
        )
        info_box = tk.Text(info_f, height=6, bg="#0c0e14", fg="#70a0c0",
                           font=("Consolas", 9), relief="flat")
        info_box.insert("1.0", info_text)
        info_box.config(state="disabled")
        info_box.pack(fill="x", padx=6, pady=4)

        # Controls
        cf = ttk.LabelFrame(parent, text="INSPIRAL PARAMETERS")
        cf.pack(fill="x", padx=12, pady=4)
        ctrl_f = tk.Frame(cf, bg="#12151c")
        ctrl_f.pack(fill="x", padx=6, pady=4)

        self.bh_grid_var = tk.IntVar(value=128)
        self.bh_amp_a_var = tk.DoubleVar(value=50.0)
        self.bh_amp_b_var = tk.DoubleVar(value=43.0)
        self.bh_steps_var = tk.IntVar(value=15)
        self.bh_sep_start_var = tk.DoubleVar(value=0.60)
        self.bh_sep_end_var = tk.DoubleVar(value=0.04)
        self.bh_settle_var = tk.IntVar(value=15000)
        self.bh_measure_var = tk.IntVar(value=5000)

        row1 = tk.Frame(ctrl_f, bg="#12151c")
        row1.pack(fill="x", pady=2)
        for lbl, var, w in [("Grid:", self.bh_grid_var, 6),
                              ("Amp A:", self.bh_amp_a_var, 6),
                              ("Amp B:", self.bh_amp_b_var, 6),
                              ("Steps:", self.bh_steps_var, 4)]:
            tk.Label(row1, text=lbl, font=("Consolas", 9),
                     fg=style_fg, bg="#12151c").pack(side="left", padx=(8, 2))
            tk.Entry(row1, textvariable=var, width=w,
                     font=("Consolas", 10), bg="#1a1e2a", fg="#e0e8f0",
                     insertbackground="#e0e8f0").pack(side="left")

        row2 = tk.Frame(ctrl_f, bg="#12151c")
        row2.pack(fill="x", pady=2)
        for lbl, var, w in [("Sep start:", self.bh_sep_start_var, 5),
                              ("Sep end:", self.bh_sep_end_var, 5),
                              ("Settle:", self.bh_settle_var, 7),
                              ("Measure:", self.bh_measure_var, 6)]:
            tk.Label(row2, text=lbl, font=("Consolas", 9),
                     fg=style_fg, bg="#12151c").pack(side="left", padx=(8, 2))
            tk.Entry(row2, textvariable=var, width=w,
                     font=("Consolas", 10), bg="#1a1e2a", fg="#e0e8f0",
                     insertbackground="#e0e8f0").pack(side="left")

        # Buttons
        bf = tk.Frame(parent, bg=style_bg)
        bf.pack(fill="x", padx=12, pady=6)

        ttk.Button(bf, text="\u2B24  Run Inspiral Sweep",
                   command=self._run_bh_inspiral).pack(fill="x", padx=4, pady=2)

        ttk.Button(bf, text="\u25C6  Render 3D Inspiral Sequence",
                   command=self._run_bh_renderer).pack(fill="x", padx=4, pady=2)

        # Log
        log_f = ttk.LabelFrame(parent, text="INSPIRAL LOG")
        log_f.pack(fill="both", expand=True, padx=12, pady=4)
        self._bh_log = tk.Text(log_f, height=20, bg="#06080c", fg="#80b8d0",
                                font=("Consolas", 9), relief="flat",
                                wrap="word")
        self._bh_log.pack(fill="both", expand=True, padx=4, pady=4)
        self._bh_log_msg("BCM v11 Black Hole Inspiral — ready.")
        self._bh_log_msg("GW150914 analog: 50.0/43.0 = 1.16:1 (observed 1.24:1)")

    def _bh_log_msg(self, msg):
        """Write to black hole tab log."""
        self._bh_log.insert("end", msg + "\n")
        self._bh_log.see("end")

    def _run_bh_inspiral(self):
        """Run binary inspiral sweep from Black Holes tab."""
        grid = self.bh_grid_var.get()
        amp_A = self.bh_amp_a_var.get()
        amp_B = self.bh_amp_b_var.get()
        steps = self.bh_steps_var.get()
        sep_start = self.bh_sep_start_var.get()
        sep_end = self.bh_sep_end_var.get()
        settle = self.bh_settle_var.get()
        measure = self.bh_measure_var.get()

        self._bh_log_msg(f"\n{'='*55}")
        self._bh_log_msg(f"  INSPIRAL SWEEP — grid={grid}  "
                          f"ratio={amp_A/amp_B:.2f}:1")
        self._bh_log_msg(f"  sep: {sep_start:.2f} -> {sep_end:.2f}  "
                          f"({steps} steps)")
        self._bh_log_msg(f"{'='*55}")

        def _run():
            try:
                from BCM_inspiral_sweep import run_inspiral_sweep
                result = run_inspiral_sweep(
                    grid=grid, amp_A=amp_A, amp_B=amp_B,
                    sep_start=sep_start, sep_end=sep_end,
                    steps=steps, settle=settle, measure=measure)
                if result:
                    n = result.get("n_runs", 0)
                    self.root.after(0, lambda: self._bh_log_msg(
                        f"  Sweep complete. {n} runs saved."))
            except ImportError:
                self.root.after(0, lambda: self._bh_log_msg(
                    "ERROR: BCM_inspiral_sweep.py not found."))
            except Exception as e:
                self.root.after(0, lambda: self._bh_log_msg(
                    f"  Inspiral error: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _run_bh_renderer(self):
        """Run 3D inspiral renderer (4 key frames)."""
        grid = self.bh_grid_var.get()
        settle = self.bh_settle_var.get()
        measure = self.bh_measure_var.get()

        self._bh_log_msg(f"\n{'='*55}")
        self._bh_log_msg(f"  3D INSPIRAL RENDERER — 4 key frames")
        self._bh_log_msg(f"  grid={grid}  (inspiral -> snap -> "
                          f"foreclosure -> merger)")
        self._bh_log_msg(f"{'='*55}")

        def _run():
            try:
                from BCM_inspiral_renderer import run_inspiral_sequence
                run_inspiral_sequence(grid=grid, settle=settle,
                                      measure=measure)
                self.root.after(0, lambda: self._bh_log_msg(
                    "  3D inspiral render complete."))
            except ImportError:
                self.root.after(0, lambda: self._bh_log_msg(
                    "ERROR: BCM_inspiral_renderer.py not found."))
            except Exception as e:
                self.root.after(0, lambda: self._bh_log_msg(
                    f"  3D render error: {e}"))

        threading.Thread(target=_run, daemon=True).start()
    # === END BLACK HOLE TAB ===

    # === BCM v12 LAMBDA DRIVE TAB ===
    def _build_lambda_tab(self, parent):
        """Tab 5 — BCM Lambda Drive Substrate Navigation."""
        style_bg  = "#0a0c10"
        style_fg  = "#a0b0cc"
        style_acc = "#44ff88"

        scroll_canvas = tk.Canvas(parent, bg=style_bg, highlightthickness=0)
        scroll_vbar = ttk.Scrollbar(parent, orient="vertical",
                                     command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scroll_vbar.set)
        scroll_vbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        sf = tk.Frame(scroll_canvas, bg=style_bg)
        sf_id = scroll_canvas.create_window((0, 0), window=sf, anchor="nw")

        def _sf_resize(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        def _sc_resize(event):
            scroll_canvas.itemconfig(sf_id, width=event.width)
        sf.bind("<Configure>", _sf_resize)
        scroll_canvas.bind("<Configure>", _sc_resize)

        def _sf_wheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_canvas.bind("<MouseWheel>", _sf_wheel)
        sf.bind("<MouseWheel>", _sf_wheel)

        parent = sf

        # Header
        hf = tk.Frame(parent, bg=style_bg)
        hf.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(hf, text="\u039B DRIVE — SUBSTRATE NAVIGATION",
                 font=("Georgia", 16), fg="#44ff88", bg=style_bg).pack(side="left")
        tk.Label(hf, text="SMBH Coherency Lambda Drive — Solar System Transit",
                 font=("Consolas", 10), fg="#6a7a90", bg=style_bg).pack(side="left", padx=(16, 0))

        # Concept
        concept_f = ttk.LabelFrame(parent, text="DRIVE CONCEPT")
        concept_f.pack(fill="x", padx=12, pady=4)
        concept_text = (
            "The Lambda Drive modulates local substrate decay rate (\u03BB)\n"
            "to create asymmetric sigma gradients. Lower \u03BB ahead deepens\n"
            "substrate memory; higher \u03BB behind shallows it. The substrate's\n"
            "own maintenance flow carries the ship along the gradient.\n"
            "\n"
            "Sun Slingshot: Fall inward to perihelion (free acceleration),\n"
            "lambda-redirect at closest approach, ride exit gradient to Saturn.\n"
            "Tangential capture at destination — Saturn's well is the brake."
        )
        concept_box = tk.Text(concept_f, height=8, bg="#0c0e14", fg="#60c080",
                               font=("Consolas", 9), relief="flat")
        concept_box.insert("1.0", concept_text)
        concept_box.config(state="disabled")
        concept_box.pack(fill="x", padx=6, pady=4)

        # Mission Parameters
        pf = ttk.LabelFrame(parent, text="MISSION PARAMETERS")
        pf.pack(fill="x", padx=12, pady=4)
        ctrl_f = tk.Frame(pf, bg="#12151c")
        ctrl_f.pack(fill="x", padx=6, pady=4)

        self.ld_launch_var = tk.StringVar(value="2032-12-01")
        self.ld_perihelion_var = tk.DoubleVar(value=0.15)
        self.ld_points_var = tk.IntVar(value=100)

        row1 = tk.Frame(ctrl_f, bg="#12151c")
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="Launch date:", font=("Consolas", 9),
                 fg=style_fg, bg="#12151c").pack(side="left", padx=(8, 2))
        tk.Entry(row1, textvariable=self.ld_launch_var, width=12,
                 font=("Consolas", 10), bg="#1a1e2a", fg="#e0e8f0",
                 insertbackground="#e0e8f0").pack(side="left")
        tk.Label(row1, text="Perihelion (AU):", font=("Consolas", 9),
                 fg=style_fg, bg="#12151c").pack(side="left", padx=(16, 2))
        tk.Entry(row1, textvariable=self.ld_perihelion_var, width=6,
                 font=("Consolas", 10), bg="#1a1e2a", fg="#e0e8f0",
                 insertbackground="#e0e8f0").pack(side="left")
        tk.Label(row1, text="Points:", font=("Consolas", 9),
                 fg=style_fg, bg="#12151c").pack(side="left", padx=(16, 2))
        tk.Entry(row1, textvariable=self.ld_points_var, width=5,
                 font=("Consolas", 10), bg="#1a1e2a", fg="#e0e8f0",
                 insertbackground="#e0e8f0").pack(side="left")

        # Lambda modulation
        lf = ttk.LabelFrame(parent, text="\u039B MODULATION")
        lf.pack(fill="x", padx=12, pady=4)
        lam_f = tk.Frame(lf, bg="#12151c")
        lam_f.pack(fill="x", padx=6, pady=4)

        self.ld_lam_base_var = tk.DoubleVar(value=0.10)
        self.ld_lam_fore_var = tk.DoubleVar(value=0.05)
        self.ld_lam_aft_var = tk.DoubleVar(value=0.20)
        self.ld_grid_var = tk.IntVar(value=128)

        row2 = tk.Frame(lam_f, bg="#12151c")
        row2.pack(fill="x", pady=2)
        for lbl, var, w in [("\u03BB base:", self.ld_lam_base_var, 5),
                              ("\u03BB fore:", self.ld_lam_fore_var, 5),
                              ("\u03BB aft:", self.ld_lam_aft_var, 5),
                              ("Grid:", self.ld_grid_var, 5)]:
            tk.Label(row2, text=lbl, font=("Consolas", 9),
                     fg=style_fg, bg="#12151c").pack(side="left", padx=(8, 2))
            tk.Entry(row2, textvariable=var, width=w,
                     font=("Consolas", 10), bg="#1a1e2a", fg="#e0e8f0",
                     insertbackground="#e0e8f0").pack(side="left")

        # Buttons
        bf = tk.Frame(parent, bg=style_bg)
        bf.pack(fill="x", padx=12, pady=6)

        ttk.Button(bf, text="\u2B24  Plot Saturn Mission (2D Map)",
                   command=self._run_ld_navigator).pack(fill="x", padx=4, pady=2)

        ttk.Button(bf, text="\u25C6  Run \u039B Drive Transit Simulation",
                   command=self._run_ld_transit).pack(fill="x", padx=4, pady=2)

        # Log
        log_f = ttk.LabelFrame(parent, text="\u039B DRIVE LOG")
        log_f.pack(fill="both", expand=True, padx=12, pady=4)
        self._ld_log = tk.Text(log_f, height=18, bg="#06080c", fg="#60c080",
                                font=("Consolas", 9), relief="flat",
                                wrap="word")
        self._ld_log.pack(fill="both", expand=True, padx=4, pady=4)
        self._ld_log_msg("\u039B DRIVE — Substrate Navigation ready.")
        self._ld_log_msg("Default mission: Sun slingshot to Saturn, Dec 2032")
        self._ld_log_msg("SPECULATIVE — theoretical extrapolation from BCM")

    def _ld_log_msg(self, msg):
        """Write to lambda drive tab log."""
        self._ld_log.insert("end", msg + "\n")
        self._ld_log.see("end")

    def _run_ld_navigator(self):
        """Run solar system navigator — 2D mission map."""
        launch = self.ld_launch_var.get()
        perihelion = self.ld_perihelion_var.get()
        points = self.ld_points_var.get()

        self._ld_log_msg(f"\n{'='*50}")
        self._ld_log_msg(f"  SOLAR NAVIGATOR — {launch}")
        self._ld_log_msg(f"  Perihelion: {perihelion} AU  Points: {points}")
        self._ld_log_msg(f"{'='*50}")

        parts = launch.split("-")

        def _run():
            try:
                from BCM_solar_navigator import run_navigator
                result = run_navigator(
                    launch_year=int(parts[0]),
                    launch_month=int(parts[1]),
                    launch_day=int(parts[2]),
                    perihelion_au=perihelion,
                    n_points=points)
                if result:
                    v = result.get("peak_velocity_kms", 0)
                    d = result.get("transit_days", 0)
                    self.root.after(0, lambda: self._ld_log_msg(
                        f"  Peak: {v:.0f} km/s  Transit: {d:.0f} days"))
            except ImportError:
                self.root.after(0, lambda: self._ld_log_msg(
                    "ERROR: BCM_solar_navigator.py not found."))
            except Exception as e:
                self.root.after(0, lambda: self._ld_log_msg(
                    f"  Navigator error: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _run_ld_transit(self):
        """Run lambda drive transit simulation."""
        grid = self.ld_grid_var.get()
        lam_base = self.ld_lam_base_var.get()
        lam_fore = self.ld_lam_fore_var.get()
        lam_aft = self.ld_lam_aft_var.get()

        self._ld_log_msg(f"\n{'='*50}")
        self._ld_log_msg(f"  \u039B DRIVE TRANSIT — grid={grid}")
        self._ld_log_msg(f"  \u03BB base={lam_base}  fore={lam_fore}  "
                          f"aft={lam_aft}")
        self._ld_log_msg(f"{'='*50}")

        def _run():
            try:
                from BCM_lambda_drive import run_lambda_drive
                result = run_lambda_drive(
                    grid=grid, lam_base=lam_base,
                    lam_fore=lam_fore, lam_aft=lam_aft,
                    n_transit_steps=20)
                if result:
                    c = "YES" if result.get("coherent") else "CHECK"
                    self.root.after(0, lambda: self._ld_log_msg(
                        f"  Transit complete. Coherence: {c}"))
            except ImportError:
                self.root.after(0, lambda: self._ld_log_msg(
                    "ERROR: BCM_lambda_drive.py not found."))
            except Exception as e:
                self.root.after(0, lambda: self._ld_log_msg(
                    f"  Transit error: {e}"))

        threading.Thread(target=_run, daemon=True).start()
    # === END LAMBDA DRIVE TAB ===

    # === TAB 6: TITS PROBE NAVIGATOR ===

    def _build_probe_tab(self, parent):
        """Tab 6 — TITS Tunnel Cycling Probe Navigator."""
        style_bg  = "#0a0c10"
        style_fg  = "#a0b0cc"
        style_acc = "#ff9944"

        scroll_canvas = tk.Canvas(parent, bg=style_bg, highlightthickness=0)
        scroll_vbar = ttk.Scrollbar(parent, orient="vertical",
                                     command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scroll_vbar.set)
        scroll_vbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        sf = tk.Frame(scroll_canvas, bg=style_bg)
        sf_id = scroll_canvas.create_window((0, 0), window=sf, anchor="nw")

        def _sf_resize(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        def _sc_resize(event):
            scroll_canvas.itemconfig(sf_id, width=event.width)
        sf.bind("<Configure>", _sf_resize)
        scroll_canvas.bind("<Configure>", _sc_resize)

        def _sf_wheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_canvas.bind("<MouseWheel>", _sf_wheel)
        sf.bind("<MouseWheel>", _sf_wheel)

        parent = sf

        # Header
        hf = tk.Frame(parent, bg=style_bg)
        hf.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(hf, text="TITS PROBE NAVIGATOR",
                 font=("Georgia", 16), fg=style_acc, bg=style_bg).pack(side="left")
        tk.Label(hf, text="Tunnel Cycling Observer Perturbation Model",
                 font=("Consolas", 10), fg="#6a7a90", bg=style_bg).pack(side="left", padx=(16, 0))

        # Concept
        concept_f = ttk.LabelFrame(parent, text="OBSERVER ARCHITECTURE")
        concept_f.pack(fill="x", padx=12, pady=4)
        concept_text = (
            "12 probes cycle THROUGH the craft via L1 tunnel:\n"
            "  B (weak pump) INGESTS \u2192 tunnel transit \u2192 A (strong pump) EJECTS\n"
            "  \u2192 ride Alfven lines outward \u2192 polygonal arc \u2192 sample substrate\n"
            "  \u2192 fall back to B collector vortex \u2192 repeat\n"
            "\n"
            "CRAFT GEOMETRY (dumbbell):\n"
            "  B = funnel (wide vortex mouth, collects from any return angle)\n"
            "  A = slit nozzle (focused ejection along Alfven lines)\n"
            "  Tunnel = Venturi tube (wide at B, narrow at A, accelerates)\n"
            "  Ratio 4:1 visible in pump sizes (A large, B small)\n"
            "\n"
            "Every probe exits forward (A pump). Every reading is\n"
            "forward-biased. The geometry does the weighting.\n"
            "\n"
            "TITS: Tensor Imagery Trasference Sensory (Stephen, TM)\n"
            "Origin: Genesis Brain interview model (TITS_GIBUSH_AISOS_SPINE)"
        )
        concept_box = tk.Text(concept_f, height=17, bg="#0c0e14", fg="#ff9944",
                               font=("Consolas", 9), relief="flat")
        concept_box.insert("1.0", concept_text)
        concept_box.config(state="disabled")
        concept_box.pack(fill="x", padx=6, pady=4)

        # Parameters
        pf = ttk.LabelFrame(parent, text="PROBE PARAMETERS")
        pf.pack(fill="x", padx=12, pady=4)
        ctrl_f = tk.Frame(pf, bg="#12151c")
        ctrl_f.pack(fill="x", padx=6, pady=4)

        self.probe_grid_var = tk.IntVar(value=256)
        self.probe_steps_var = tk.IntVar(value=3000)

        row1 = tk.Frame(ctrl_f, bg="#12151c")
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="Grid:", font=("Consolas", 9),
                 fg=style_fg, bg="#12151c").pack(side="left", padx=(8, 2))
        tk.Entry(row1, textvariable=self.probe_grid_var, width=5,
                 font=("Consolas", 10), bg="#1a1e2a", fg="#e0e8f0",
                 insertbackground="#e0e8f0").pack(side="left")
        tk.Label(row1, text="Steps:", font=("Consolas", 9),
                 fg=style_fg, bg="#12151c").pack(side="left", padx=(16, 2))
        tk.Entry(row1, textvariable=self.probe_steps_var, width=6,
                 font=("Consolas", 10), bg="#1a1e2a", fg="#e0e8f0",
                 insertbackground="#e0e8f0").pack(side="left")

        # Buttons
        bf = tk.Frame(parent, bg=style_bg)
        bf.pack(fill="x", padx=12, pady=6)

        ttk.Button(bf, text="\u2B24  Run Tunnel Cycling Probes",
                   command=self._run_probe_tunnel).pack(fill="x", padx=4, pady=2)

        ttk.Button(bf, text="\u25C6  Run Probe BoM & Tax Curve",
                   command=self._run_probe_bom).pack(fill="x", padx=4, pady=2)

        ttk.Button(bf, text="\u2726  Run Harpoon + Probes Integration",
                   command=self._run_probe_harpoon).pack(fill="x", padx=4, pady=2)

        ttk.Button(bf, text="\u25CE  Open Probe Renderer",
                   command=self._launch_probe_renderer).pack(fill="x", padx=4, pady=2)

        ttk.Button(bf, text="\u2605  Bootes Void Cinematic (10 slides)",
                   command=self._run_bootes_cinematic).pack(fill="x", padx=4, pady=2)

        # Log
        log_f = ttk.LabelFrame(parent, text="PROBE LOG")
        log_f.pack(fill="both", expand=True, padx=12, pady=4)
        self._probe_log = tk.Text(log_f, height=20, bg="#06080c", fg="#ff9944",
                                    font=("Consolas", 9), relief="flat",
                                    wrap="word")
        self._probe_log.pack(fill="both", expand=True, padx=4, pady=4)
        self._probe_log_msg("TITS PROBE NAVIGATOR ready.")
        self._probe_log_msg("12 tunnel-cycling probes. Bayesian navigator.")
        self._probe_log_msg("Architecture: Genesis Brain interview model")
        self._probe_log_msg("The ship thinks. The thinking keeps it alive.")

    def _probe_log_msg(self, msg):
        """Write to probe tab log."""
        self._probe_log.insert("end", msg + "\n")
        self._probe_log.see("end")

    def _run_probe_tunnel(self):
        """Run tunnel cycling probe test."""
        grid = self.probe_grid_var.get()
        steps = self.probe_steps_var.get()
        self._probe_log_msg(f"\n{'='*50}")
        self._probe_log_msg(f"  TUNNEL CYCLING PROBES")
        self._probe_log_msg(f"  Grid: {grid}  Steps: {steps}")
        self._probe_log_msg(f"{'='*50}")

        def _run():
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "BCM_v16_tunnel_probes.py",
                     "--grid", str(grid), "--steps", str(steps)],
                    capture_output=True, text=True, timeout=300)
                for line in result.stdout.split("\n"):
                    if line.strip():
                        self.root.after(0, lambda l=line: self._probe_log_msg(l))
                if result.returncode != 0:
                    self.root.after(0, lambda: self._probe_log_msg(
                        f"ERROR: {result.stderr}"))
            except FileNotFoundError:
                self.root.after(0, lambda: self._probe_log_msg(
                    "ERROR: BCM_v16_tunnel_probes.py not found."))
            except Exception as e:
                self.root.after(0, lambda: self._probe_log_msg(
                    f"  Error: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _run_probe_bom(self):
        """Run probe BoM and tax curve test."""
        grid = self.probe_grid_var.get()
        self._probe_log_msg(f"\n{'='*50}")
        self._probe_log_msg(f"  PROBE BoM & TAX CURVE — Grid: {grid}")
        self._probe_log_msg(f"{'='*50}")

        def _run():
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "BCM_v16_probe_bom.py",
                     "--grid", str(grid)],
                    capture_output=True, text=True, timeout=300)
                for line in result.stdout.split("\n"):
                    if line.strip():
                        self.root.after(0, lambda l=line: self._probe_log_msg(l))
            except FileNotFoundError:
                self.root.after(0, lambda: self._probe_log_msg(
                    "ERROR: BCM_v16_probe_bom.py not found."))
            except Exception as e:
                self.root.after(0, lambda: self._probe_log_msg(
                    f"  Error: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _run_probe_harpoon(self):
        """Run harpoon + probe integration test."""
        grid = self.probe_grid_var.get()
        steps = self.probe_steps_var.get()
        self._probe_log_msg(f"\n{'='*50}")
        self._probe_log_msg(f"  HARPOON + PROBES — Grid: {grid} Steps: {steps}")
        self._probe_log_msg(f"{'='*50}")

        def _run():
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "BCM_v16_harpoon_probe.py",
                     "--grid", str(grid), "--steps", str(steps)],
                    capture_output=True, text=True, timeout=300)
                for line in result.stdout.split("\n"):
                    if line.strip():
                        self.root.after(0, lambda l=line: self._probe_log_msg(l))
            except FileNotFoundError:
                self.root.after(0, lambda: self._probe_log_msg(
                    "ERROR: BCM_v16_harpoon_probe.py not found."))
            except Exception as e:
                self.root.after(0, lambda: self._probe_log_msg(
                    f"  Error: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _launch_probe_renderer(self):
        """Launch standalone probe renderer."""
        self._probe_log_msg("  Launching probe renderer...")

        def _run():
            try:
                import subprocess
                subprocess.Popen([sys.executable, "BCM_probe_renderer.py"])
            except FileNotFoundError:
                self.root.after(0, lambda: self._probe_log_msg(
                    "ERROR: BCM_probe_renderer.py not found."))
            except Exception as e:
                self.root.after(0, lambda: self._probe_log_msg(
                    f"  Renderer error: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _run_bootes_cinematic(self):
        """Launch Bootes Void cinematic slide renderer."""
        self._probe_log_msg(f"\n{'='*50}")
        self._probe_log_msg(f"  BOOTES VOID CINEMATIC -- 10 slides")
        self._probe_log_msg(f"  Saving to data/images/")
        self._probe_log_msg(f"{'='*50}")

        def _run():
            try:
                import subprocess
                subprocess.Popen([sys.executable,
                    "BCM_v16_bootes_cinematic.py", "--save"])
                self.root.after(0, lambda: self._probe_log_msg(
                    "  Cinematic launched. Check data/images/ for slides."))
            except FileNotFoundError:
                self.root.after(0, lambda: self._probe_log_msg(
                    "ERROR: BCM_v16_bootes_cinematic.py not found."))
            except Exception as e:
                self.root.after(0, lambda: self._probe_log_msg(
                    f"  Cinematic error: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    # === END TITS PROBE TAB ===

    def _on_binary_resize(self, event):
        self._binary_cw = event.width
        self._binary_ch = event.height

    def _draw_binary_live(self, rho, step, total):
        """Draw live wave propagation frame on binary canvas."""
        if not hasattr(self, '_binary_canvas'):
            return
        try:
            c = self._binary_canvas
            c.delete("all")
            w, h = self._binary_cw, self._binary_ch

            field = np.abs(rho[0]) if len(rho.shape) == 3 else np.abs(rho)
            ny, nx = field.shape
            fm = np.max(field)
            if fm <= 0:
                fm = 1.0

            # Draw field as heatmap
            cw_px = w / nx
            ch_px = (h - 60) / ny
            sx = max(1, nx // 80)
            sy = max(1, ny // 80)

            for iy in range(0, ny, sy):
                for ix in range(0, nx, sx):
                    v = field[iy, ix] / fm
                    # Emerald substrate palette
                    r_c = int(min(255, 20 + v * 60))
                    g_c = int(min(255, 30 + v * 225))
                    b_c = int(min(255, 20 + v * 40))
                    col = f"#{r_c:02x}{g_c:02x}{b_c:02x}"
                    x0 = ix * cw_px
                    y0 = iy * ch_px
                    c.create_rectangle(x0, y0,
                        (ix + sx) * cw_px, (iy + sy) * ch_px,
                        fill=col, outline="")

            # Pump markers
            if self._binary_pump_info:
                info = self._binary_pump_info
                pA = info.get('pump_A', (nx//4, ny//2))
                pB = info.get('pump_B', (3*nx//4, ny//2))
                l1 = info.get('L1', (nx//2, ny//2))

                ax = pA[0] * cw_px
                ay = pA[1] * ch_px
                bx = pB[0] * cw_px
                by = pB[1] * ch_px
                lx = l1[0] * cw_px
                ly = l1[1] * ch_px

                # Star A
                c.create_oval(ax - 8, ay - 8, ax + 8, ay + 8,
                              fill="#ff9944", outline="white", width=1)
                c.create_text(ax, ay - 14,
                    text=info.get('star_A', 'A'),
                    fill="white", font=("Consolas", 8, "bold"))

                # Star B
                c.create_oval(bx - 6, by - 6, bx + 6, by + 6,
                              fill="#44aaff", outline="white", width=1)
                c.create_text(bx, by - 14,
                    text=info.get('star_B', 'B'),
                    fill="white", font=("Consolas", 8, "bold"))

                # L1
                c.create_polygon(lx, ly - 6, lx + 5, ly,
                                 lx, ly + 6, lx - 5, ly,
                                 fill="#ffbb44", outline="white")

                # Bridge line
                c.create_line(ax, ay, bx, by,
                    fill="#60aaff", width=1, dash=(3, 6))

                # Alfven resonance rings — mode structure overlay
                for pump_xy, m_mode, color in [
                    ((ax, ay), info.get('m_pred_A', 4), "#40ee70"),
                    ((bx, by), info.get('m_pred_B', 4), "#60aaff")]:
                    px, py = pump_xy
                    m = max(1, m_mode)
                    well_r = cw_px * grid * 0.08 * 2.5  # pump influence radius
                    for i in range(1, m + 1):
                        ring_r = well_r * i / m
                        if ring_r > 4:
                            c.create_oval(
                                px - ring_r, py - ring_r,
                                px + ring_r, py + ring_r,
                                outline=color, dash=(2, 4), width=1)

                # Inner infinity — lemniscate (light version for live view)
                import math
                mid_x = (ax + bx) / 2
                mid_y = (ay + by) / 2
                half_sep = abs(bx - ax) / 2
                if half_sep > 10:
                    n_pts = 80
                    lem_pts = []
                    for i in range(n_pts + 1):
                        t = i / n_pts * 2 * math.pi
                        sin_t = math.sin(t)
                        cos_t = math.cos(t)
                        denom = 1 + sin_t * sin_t
                        x = half_sep * 1.05 * cos_t / denom + mid_x
                        y = half_sep * 0.55 * sin_t * cos_t / denom + mid_y
                        lem_pts.extend([x, y])
                    if len(lem_pts) >= 4:
                        c.create_line(*lem_pts,
                            fill="#ffbb44", width=1, smooth=True, dash=(4, 4))

            # Status bar
            pct = step / total * 100 if total > 0 else 0
            settle = self.stellar_settle_var.get()
            phase_txt = "SETTLING" if step < settle else "MEASURING"
            c.create_text(w // 2, h - 25,
                text=f"{phase_txt}  step {step}/{total}  ({pct:.0f}%)  "
                     f"|ρ|_max={fm:.2f}",
                fill="#e0e8f0", font=("Consolas", 11, "bold"))
            c.create_text(w // 2, h - 8,
                text="BCM v7 Binary Wave Propagation — "
                     "Emerald Entities LLC — GIBUSH",
                fill="#3a4a60", font=("Consolas", 8))

            self._binary_status.set(
                f"Step {step}/{total}  ({pct:.0f}%)")
        except Exception:
            pass  # window may have been closed

    def _draw_binary_final(self, result, info):
        """Draw final frame on binary canvas — last rho frame + diagnostics overlay."""
        if not hasattr(self, '_binary_canvas'):
            return
        try:
            c = self._binary_canvas
            c.delete("all")
            w, h = self._binary_cw, self._binary_ch

            # Use rho_avg layer 0 — same rendering as live view
            rho_avg = result.get('rho_avg')
            if rho_avg is None:
                return
            field = np.abs(rho_avg[0]) if len(rho_avg.shape) == 3 else np.abs(rho_avg)
            ny, nx = field.shape
            fm = np.max(field)
            if fm <= 0:
                fm = 1.0

            cw_px = w / nx
            ch_px = (h - 80) / ny
            sx = max(1, nx // 100)
            sy = max(1, ny // 100)

            for iy in range(0, ny, sy):
                for ix in range(0, nx, sx):
                    v = field[iy, ix] / fm
                    r_c = int(min(255, 20 + v * 60))
                    g_c = int(min(255, 30 + v * 225))
                    b_c = int(min(255, 20 + v * 40))
                    col = f"#{r_c:02x}{g_c:02x}{b_c:02x}"
                    x0 = ix * cw_px
                    y0 = iy * ch_px
                    c.create_rectangle(x0, y0,
                        (ix + sx) * cw_px, (iy + sy) * ch_px,
                        fill=col, outline="")

            # Pump markers + L1
            pA = info.get('pump_A', (nx//4, ny//2))
            pB = info.get('pump_B', (3*nx//4, ny//2))
            l1 = info.get('L1', (nx//2, ny//2))

            ax, ay = pA[0]*cw_px, pA[1]*ch_px
            bx, by = pB[0]*cw_px, pB[1]*ch_px
            lx, ly = l1[0]*cw_px, l1[1]*ch_px

            # Corona glow
            for ri in range(20, 6, -2):
                alpha = max(0, 1.0 - (ri-8)/14.0)
                gc = int(alpha * 50)
                c.create_oval(ax-ri, ay-ri, ax+ri, ay+ri,
                    outline=f"#{gc+20:02x}{gc:02x}08", fill="")
                c.create_oval(bx-ri, by-ri, bx+ri, by+ri,
                    outline=f"#08{gc:02x}{gc+20:02x}", fill="")

            c.create_oval(ax-10, ay-10, ax+10, ay+10,
                          fill="#ff9944", outline="white", width=2)
            c.create_text(ax, ay-18, text=info.get('star_A','A'),
                fill="white", font=("Consolas", 9, "bold"))

            c.create_oval(bx-8, by-8, bx+8, by+8,
                          fill="#44aaff", outline="white", width=2)
            c.create_text(bx, by-18, text=info.get('star_B','B'),
                fill="white", font=("Consolas", 9, "bold"))

            c.create_polygon(lx, ly-8, lx+6, ly, lx, ly+8, lx-6, ly,
                             fill="#ffbb44", outline="white", width=1)
            c.create_text(lx, ly-14, text="L1",
                fill="#ffbb44", font=("Consolas", 9, "bold"))

            c.create_line(ax, ay, bx, by,
                fill="#60aaff", width=1, dash=(4, 8))

            # Alfven resonance rings — mode structure overlay
            for pump_xy, m_mode, color in [
                ((ax, ay), info.get('m_pred_A', 4), "#40ee70"),
                ((bx, by), info.get('m_pred_B', 4), "#60aaff")]:
                px, py = pump_xy
                m = max(1, m_mode)
                well_r = cw_px * ny * 0.08 * 2.5
                for i in range(1, m + 1):
                    ring_r = well_r * i / m
                    if ring_r > 4:
                        c.create_oval(
                            px - ring_r, py - ring_r,
                            px + ring_r, py + ring_r,
                            outline=color, dash=(2, 4), width=1)

            # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
            # Substrate Topology Overlay — Burdick's Triple Structure
            # 1. Outer torus — 360° maintenance field envelope per star
            # 2. Inner infinity — figure-8 lemniscate through L1
            # 3. L1 swirl — circulation indicator at the throat
            import math

            mid_x = (ax + bx) / 2
            mid_y = (ay + by) / 2
            half_sep = abs(bx - ax) / 2

            # 1. Outer torus loops — full substrate envelope
            for pump_xy, amp, color in [
                ((ax, ay), info.get('amp_A', 8), "#40ee7040"),
                ((bx, by), info.get('amp_B', 4), "#60aaff40")]:
                px, py = pump_xy
                torus_r = half_sep * 0.85 * (amp / max(info.get('amp_A', 8), 1))
                torus_r = max(torus_r, half_sep * 0.3)
                # Draw as multiple fading ovals
                for ri_off in range(3):
                    r = torus_r + ri_off * 4
                    alpha_hex = max(20, 60 - ri_off * 15)
                    c.create_oval(px - r, py - r, px + r, py + r,
                        outline=color[:7], dash=(6, 4), width=1)

            # 2. Inner infinity — lemniscate of Bernoulli
            # Substrate flow path through both lobes via L1
            n_pts = 120
            lemniscate_pts = []
            a_lem = half_sep * 1.05  # slightly wider than separation
            h_lem = half_sep * 0.55  # height of each lobe
            for i in range(n_pts + 1):
                t = i / n_pts * 2 * math.pi
                sin_t = math.sin(t)
                cos_t = math.cos(t)
                denom = 1 + sin_t * sin_t
                x = a_lem * cos_t / denom + mid_x
                y = h_lem * sin_t * cos_t / denom + mid_y
                lemniscate_pts.extend([x, y])

            if len(lemniscate_pts) >= 4:
                c.create_line(*lemniscate_pts,
                    fill="#ffbb44", width=2, smooth=True)
                # Second trace slightly offset for depth
                lemniscate_pts2 = []
                for i in range(n_pts + 1):
                    t = i / n_pts * 2 * math.pi + 0.05
                    sin_t = math.sin(t)
                    cos_t = math.cos(t)
                    denom = 1 + sin_t * sin_t
                    x = a_lem * 0.92 * cos_t / denom + mid_x
                    y = h_lem * 0.92 * sin_t * cos_t / denom + mid_y
                    lemniscate_pts2.extend([x, y])
                c.create_line(*lemniscate_pts2,
                    fill="#ffbb44", width=1, dash=(3, 5), smooth=True)

            # 3. L1 swirl — circulation at the throat
            # Archimedean spiral showing substrate pooling
            spiral_pts = []
            n_spiral = 60
            for i in range(n_spiral):
                t = i / n_spiral * 3 * math.pi
                r = 3 + t * 2.5
                x = lx + r * math.cos(t)
                y = ly + r * math.sin(t)
                spiral_pts.extend([x, y])
            if len(spiral_pts) >= 4:
                c.create_line(*spiral_pts,
                    fill="#ff9944", width=1, smooth=True)

            # Topology label
            c.create_text(mid_x, mid_y - half_sep * 0.65,
                text="∞ SUBSTRATE BRIDGE",
                fill="#ffbb44", font=("Consolas", 9, "bold"))
            # === END ADDITION ===

            # Diagnostics overlay — bottom panel
            cos_l1 = info.get('L1_cos_mean', 0)
            curl_l1 = info.get('L1_curl_max', 0)
            verdict = "COHERENT BRIDGE" if cos_l1 > 0.99 else (
                "PARTIAL BRIDGE" if cos_l1 > 0.9 else "DECOHERENT")
            v_color = "#40ee70" if cos_l1 > 0.99 else (
                "#ffbb44" if cos_l1 > 0.9 else "#ff5555")

            # Dark panel at bottom
            panel_y = h - 75
            c.create_rectangle(0, panel_y, w, h,
                fill="#080a0e", outline="")

            c.create_text(w // 2, panel_y + 12,
                text=f"COMPLETE — {info.get('star_A','A')} + {info.get('star_B','B')}  |  "
                     f"sep={info.get('sep_AU',0):.1f} AU  "
                     f"e={info.get('eccentricity',0):.3f}  "
                     f"phase={info.get('orbital_phase',0):.2f}",
                fill="#e0e8f0", font=("Consolas", 10, "bold"))

            c.create_text(w // 2, panel_y + 32,
                text=f"L1 cos(Δφ) = {cos_l1:+.6f}   "
                     f"curl = {curl_l1:.2e}   "
                     f">>> {verdict}",
                fill=v_color, font=("Consolas", 11, "bold"))

            vortex_txt = ("SUBSTRATE POOLING" if curl_l1 > 0.001
                          else "Laminar bridge (no vorticity)")
            c.create_text(w // 2, panel_y + 50,
                text=f">>> {vortex_txt}   |   "
                     f"BCM v7 Binary Substrate Bridge — "
                     f"Emerald Entities LLC — GIBUSH",
                fill="#3a4a60", font=("Consolas", 8))

            self._binary_status.set(
                f"COMPLETE — {verdict}  L1={cos_l1:+.4f}")
        except Exception:
            pass

    def _build_controls(self, parent):
        # BCM STRUCTURAL OVERRIDES (top — always visible)
        self._bcm_galaxies = {
            "NGC3953": {"class":"VI",  "label":"NGC3953  Class VI  Bar-Channeled",
                        "source":"bar_dipole","bar_angle":10.0,"bar_len":0.35,"bar_wid":0.06,"liner":0.75},
            "NGC7793": {"class":"V-B", "label":"NGC7793  Class V-B [2D THINGS]", "source":"hi_fits"},
            "NGC2976": {"class":"V-A", "label":"NGC2976  Class V-A [2D THINGS]", "source":"hi_fits"},
            "UGC04305":{"class":"II",  "label":"UGC04305 Holmberg II [2D THINGS]","source":"hi_fits"},
            "NGC0801": {"class":"IV",  "label":"NGC0801  Class IV  Bow Pending",  "source":"classic_fallback"},
            "NGC2841": {"class":"I",   "label":"NGC2841  Class I   Control",       "source":"classic"},
        }
        v8f = ttk.LabelFrame(parent, text="BCM STRUCTURAL OVERRIDES")
        v8f.pack(fill="x", padx=5, pady=4)
        bcm_lb_frame = ttk.Frame(v8f)
        bcm_lb_frame.pack(fill="x", padx=5, pady=3)
        self.bcm_listbox = tk.Listbox(bcm_lb_frame, height=6, width=38,
                                      bg="#0c0e14", fg="#ffbb44",
                                      font=("Consolas", 9),
                                      selectbackground="#2a3a10",
                                      selectforeground="#ffffff",
                                      exportselection=False)
        for name, cfg in self._bcm_galaxies.items():
            self.bcm_listbox.insert("end", cfg["label"])
        self.bcm_listbox.pack(fill="x")
        self.bcm_status_var = tk.StringVar(value="Select galaxy — BCM override")
        ttk.Label(v8f, textvariable=self.bcm_status_var,
                  font=("Consolas", 8), foreground="#ffbb44").pack(fill="x", padx=5)
        bcm_btn_f = ttk.Frame(v8f)
        bcm_btn_f.pack(fill="x", padx=5, pady=3)
        ttk.Button(bcm_btn_f, text="▶ Run BCM Selected",
                   command=self._run_bcm_selected).pack(side="left", padx=2)
        ttk.Button(bcm_btn_f, text="Run BCM All",
                   command=self._run_bcm_all).pack(side="left", padx=2)

        # SOURCE
        sf = ttk.LabelFrame(parent, text="SOURCE")
        sf.pack(fill="x", padx=5, pady=4)
        self.source_var = tk.StringVar(value="gaussian")
        for v, l in [("gaussian","Gaussian Blob"),("point_mass","Point Mass"),("sparc","SPARC Galaxy")]:
            ttk.Radiobutton(sf, text=l, variable=self.source_var, value=v, command=self._on_source_change).pack(anchor="w", padx=10, pady=1)

        # SPARC panel
        self.sparc_frame = ttk.LabelFrame(sf, text="DATA READER")
        self.sparc_path_var = tk.StringVar(value="")
        dr = ttk.Frame(self.sparc_frame)
        dr.pack(fill="x", padx=5, pady=2)
        self.data_dir_var = tk.StringVar(value=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sparc_raw"))
        ttk.Entry(dr, textvariable=self.data_dir_var, width=18).pack(side="left", padx=2)
        ttk.Button(dr, text="Dir", command=self._set_data_dir).pack(side="left", padx=2)
        ttk.Button(dr, text="Scan", command=self._scan_galaxies).pack(side="left", padx=2)
        lf = ttk.Frame(self.sparc_frame)
        lf.pack(fill="both", padx=5, pady=2)
        self.galaxy_listbox = tk.Listbox(lf, height=5, width=28, bg="#0c0e14", fg="#90c0e0", font=("Consolas", 10), selectbackground="#2a4a70", selectforeground="#ffffff", exportselection=False)
        gs = ttk.Scrollbar(lf, orient="vertical", command=self.galaxy_listbox.yview)
        self.galaxy_listbox.configure(yscrollcommand=gs.set)
        self.galaxy_listbox.pack(side="left", fill="both", expand=True)
        gs.pack(side="right", fill="y")
        self.galaxy_listbox.bind('<<ListboxSelect>>', self._on_galaxy_select)
        self.galaxy_info_var = tk.StringVar(value="")
        ttk.Label(self.sparc_frame, textvariable=self.galaxy_info_var, font=("Consolas", 9), foreground="#70a0c0").pack(fill="x", padx=5, pady=1)
        sb = ttk.Frame(self.sparc_frame)
        sb.pack(fill="x", padx=5, pady=3)
        ttk.Button(sb, text="Run Selected", command=self._run_selected_galaxy).pack(side="left", padx=2)
        ttk.Button(sb, text="Run All", command=self._run_all_galaxies).pack(side="left", padx=2)

        # ENGINE
        ef = ttk.LabelFrame(parent, text="ENGINE")
        ef.pack(fill="x", padx=5, pady=4)
        self.grid_var = tk.IntVar(value=64)
        self.layers_var = tk.IntVar(value=6)
        self.settle_var = tk.IntVar(value=12000)
        self.measure_var = tk.IntVar(value=3000)
        for l, v, r in [("Grid:", self.grid_var, 0), ("Layers:", self.layers_var, 1), ("Settle:", self.settle_var, 2), ("Measure:", self.measure_var, 3)]:
            ttk.Label(ef, text=l).grid(row=r, column=0, sticky="w", padx=10, pady=2)
            ttk.Entry(ef, textvariable=v, width=10).grid(row=r, column=1, padx=5, pady=2)
        pf2 = ttk.Frame(ef)
        pf2.grid(row=4, column=0, columnspan=2, pady=4)
        for t, a in [("Quick",(64,6,8000,2000)),("Standard",(128,6,15000,4000)),("Deep",(128,42,25000,5000)),("72 Names",(128,72,25000,5000))]:
            ttk.Button(pf2, text=t, command=lambda x=a: self._preset(*x)).pack(side="left", padx=2)

        # PHYSICS
        pf3 = ttk.LabelFrame(parent, text="PHYSICS")
        pf3.pack(fill="x", padx=5, pady=4)
        self.gamma_var = tk.DoubleVar(value=0.05)
        self.entangle_var = tk.DoubleVar(value=0.02)
        self.cwave_var = tk.DoubleVar(value=1.0)
        for l, v, r in [("γ (damping):", self.gamma_var, 0), ("Entangle:", self.entangle_var, 1), ("C_wave:", self.cwave_var, 2)]:
            ttk.Label(pf3, text=l).grid(row=r, column=0, sticky="w", padx=10, pady=2)
            ttk.Entry(pf3, textvariable=v, width=10).grid(row=r, column=1, padx=5, pady=2)

        # REGIME
        rf = ttk.LabelFrame(parent, text="REGIME")
        rf.pack(fill="x", padx=5, pady=4)
        self.crag_var = tk.BooleanVar(value=False)
        self.crag_kappa_var = tk.DoubleVar(value=2.0)
        cr = ttk.Frame(rf)
        cr.pack(fill="x", padx=10, pady=(4,2))
        ttk.Checkbutton(cr, text="Crag Mass (BCM)", variable=self.crag_var).pack(side="left")
        ttk.Label(cr, text="  k=").pack(side="left")
        ttk.Entry(cr, textvariable=self.crag_kappa_var, width=5).pack(side="left")
        self.regime_var = tk.StringVar(value="both")
        for v, l in [("both","Both (Control + Real)"),("control","Control only (λ→0)"),("real","Real only (λ≠0)")]:
            ttk.Radiobutton(rf, text=l, variable=self.regime_var, value=v).pack(anchor="w", padx=10, pady=1)
        self.lambda_ctrl_var = tk.DoubleVar(value=0.0001)
        self.lambda_real_var = tk.DoubleVar(value=0.1)
        lr = ttk.Frame(rf)
        lr.pack(fill="x", padx=10, pady=3)
        ttk.Label(lr, text="λ ctrl:").pack(side="left")
        ttk.Entry(lr, textvariable=self.lambda_ctrl_var, width=8).pack(side="left", padx=4)
        ttk.Label(lr, text="λ real:").pack(side="left", padx=(8,0))
        ttk.Entry(lr, textvariable=self.lambda_real_var, width=8).pack(side="left", padx=4)

        # BUTTONS
        bf = ttk.Frame(parent, style="Dark.TFrame")
        bf.pack(fill="x", padx=5, pady=8)
        self.run_btn = ttk.Button(bf, text="▶  RUN SOLVER", style="Run.TButton", command=self._run_solver)
        self.run_btn.pack(fill="x", padx=4, pady=2)
        ttk.Button(bf, text="Export Results", command=self._export_results).pack(fill="x", padx=4, pady=2)
        ttk.Button(bf, text="Clear Log", command=self._clear_log).pack(fill="x", padx=4, pady=2)
        ttk.Button(bf, text="⬡ Genesis Renderer", command=self._open_genesis).pack(fill="x", padx=4, pady=2)

        # (BCM panel is built at the top of _build_controls — no duplicate here)

    def _build_output(self, parent):
        cf = ttk.LabelFrame(parent, text="FIELD VISUALIZATION")
        cf.pack(fill="x", padx=5, pady=4)
        self.canvas = tk.Canvas(cf, height=380, bg="#080a0e", highlightthickness=0)
        self.canvas.pack(fill="x", padx=5, pady=5)
        sf = ttk.Frame(cf)
        sf.pack(fill="x", padx=5, pady=(0, 5))
        self.live_stats_var = tk.StringVar(value="")
        ttk.Label(sf, textvariable=self.live_stats_var, font=("Consolas", 11), foreground="#80c0e0").pack(fill="x")

        rf = ttk.LabelFrame(parent, text="RESULTS")
        rf.pack(fill="x", padx=5, pady=4)
        self.results_text = tk.Text(rf, height=5, bg="#0c0e14", fg="#e0f0ff", font=("Consolas", 12), insertbackground="#e0f0ff", selectbackground="#2a4060")
        self.results_text.pack(fill="x", padx=5, pady=5)
        self.results_text.config(state="disabled")

        lf = ttk.LabelFrame(parent, text="LOG")
        lf.pack(fill="both", expand=True, padx=5, pady=4)
        self.log_text = scrolledtext.ScrolledText(lf, height=10, bg="#0c0e14", fg="#c0d8e8", font=("Consolas", 11), insertbackground="#c0d8e8", selectbackground="#2a4060")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        # ── Color tags for result lines ──
        self.log_text.tag_config("win_sub",    foreground="#40ee70", font=("Consolas", 11, "bold"))
        self.log_text.tag_config("win_sub_big",foreground="#00ff88", font=("Consolas", 11, "bold"))
        self.log_text.tag_config("win_newt",   foreground="#ffbb44", font=("Consolas", 11))
        self.log_text.tag_config("win_mond",   foreground="#ff5555", font=("Consolas", 11))
        self.log_text.tag_config("win_tie",    foreground="#888888", font=("Consolas", 11))
        self.log_text.tag_config("galaxy_hdr", foreground="#90c8ff", font=("Consolas", 11, "bold"))
        self.log_text.tag_config("field_good", foreground="#60aaff", font=("Consolas", 10))
        self.log_text.tag_config("dim",        foreground="#556677", font=("Consolas", 10))

    # ═══════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════

    def log(self, msg, tag=None):
        self.log_text.config(state="normal")
        start = self.log_text.index("end-1c")
        self.log_text.insert("end", msg + "\n")
        if tag:
            end = self.log_text.index("end-1c")
            self.log_text.tag_add(tag, start, end)
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.root.update_idletasks()

    def log_galaxy_header(self, idx, total, name):
        """Colored galaxy header line in batch."""
        msg = f"\n  [{idx}/{total}] {name}"
        self.log(msg, tag="galaxy_hdr")

    def log_result(self, rms_newton, rms_mond, rms_sub, winner, corr_full, corr_inner):
        """
        Color-coded result line. Tag based on winner and margin.
        Big green  = sub wins by >10 km/s
        Green      = sub wins
        Gold       = newton wins
        Red        = mond wins
        Gray       = tie
        """
        delta = rms_newton - rms_sub
        rms_line = (f"    N={rms_newton:.1f}  M={rms_mond:.1f}  "
                    f"S={rms_sub:.1f}  Δ={delta:+.1f}  Winner: {winner}")
        if winner == "SUBSTRATE":
            tag = "win_sub_big" if delta > 10 else "win_sub"
        elif winner == "NEWTON":
            tag = "win_newt"
        elif winner == "MOND":
            tag = "win_mond"
        else:
            tag = "win_tie"
        self.log(rms_line, tag=tag)
        field_line = (f"    Ψ~Φ={corr_full:+.4f}  inner={corr_inner:+.4f}")
        self.log(field_line, tag="field_good")

    def set_result(self, text):
        self.results_text.config(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", text)
        self.results_text.config(state="disabled")

    def _preset(self, g, l, s, m):
        self.grid_var.set(g); self.layers_var.set(l); self.settle_var.set(s); self.measure_var.set(m)
        self.log(f"  Preset: grid={g} layers={l} settle={s}")

    def _clear_log(self):
        self.log_text.config(state="normal"); self.log_text.delete("1.0", "end"); self.log_text.config(state="disabled")

    def _on_canvas_resize(self, event):
        self._canvas_w = event.width; self._canvas_h = event.height
        if self._last_psi is not None:
            self._draw_field(self._last_psi, self._last_phi, self._last_label)

    # ═══════════════════════════════════════
    # SPARC DATA
    # ═══════════════════════════════════════

    def _on_source_change(self):
        if self.source_var.get() == "sparc":
            self.sparc_frame.pack(fill="both", padx=10, pady=3)
            if not self.galaxy_catalog: self._scan_galaxies()
        else:
            self.sparc_frame.pack_forget()

    def _set_data_dir(self):
        p = filedialog.askdirectory(title="Select data dir", initialdir=self.data_dir_var.get())
        if p: self.data_dir_var.set(p); self._scan_galaxies()

    def _scan_galaxies(self):
        dd = self.data_dir_var.get()
        self.galaxy_listbox.delete(0, "end"); self.galaxy_catalog.clear()
        if not os.path.exists(dd): self.galaxy_info_var.set("Dir not found"); return
        all_dats = []
        for root, dirs, files in os.walk(dd):
            for f in files:
                if f.endswith('.dat'):
                    all_dats.append((f, os.path.join(root, f)))
        dats = sorted(all_dats, key=lambda x: x[0])
        if not dats: self.galaxy_info_var.set("No .dat files"); return
        count = 0
        for f, p in dats:
            try:
                with open(p,'r') as fh:
                    lines = [l.strip() for l in fh if l.strip() and not l.startswith('#')]
                if len(lines) < 3: continue
                radii, vobs = [], []
                for line in lines:
                    vals = line.split()
                    if len(vals)>=2: radii.append(float(vals[0])); vobs.append(float(vals[1]))
                name = f.replace("_rotmod.dat","").replace(".dat","")
                rm, vm = max(radii) if radii else 0, max(vobs) if vobs else 0
                self.galaxy_catalog[name] = {"path":p,"file":f,"n_points":len(lines),"r_max":rm,"v_max":vm}
                self.galaxy_listbox.insert("end", f"{name:<14} V={vm:>5.0f}  R={rm:>5.1f}  {len(lines)}pt")
                count += 1
            except: continue
        self.galaxy_info_var.set(f"{count} galaxies loaded")
        self.log(f"  Scanned: {count} galaxies")
        if self.last_selected_galaxy:
            names = list(self.galaxy_catalog.keys())
            if self.last_selected_galaxy in names:
                idx = names.index(self.last_selected_galaxy)
                self.galaxy_listbox.selection_set(idx); self.galaxy_listbox.see(idx)

    def _on_galaxy_select(self, event):
        n = self._get_selected_galaxy()
        if n and n in self.galaxy_catalog:
            self.last_selected_galaxy = n
            i = self.galaxy_catalog[n]
            self.galaxy_info_var.set(f"{n}: {i['n_points']}pt  V={i['v_max']:.0f}  R={i['r_max']:.1f} kpc")

    def _get_selected_galaxy(self):
        sel = self.galaxy_listbox.curselection()
        if not sel: return None
        return self.galaxy_listbox.get(sel[0]).split()[0].strip()

    def _run_selected_galaxy(self):
        n = self._get_selected_galaxy()
        if not n or n not in self.galaxy_catalog:
            messagebox.showwarning("No Selection", "Select a galaxy first."); return
        self.source_var.set("sparc"); self.sparc_path_var.set(self.galaxy_catalog[n]["path"])
        self._run_solver()

    def _run_all_galaxies(self):
        if not self.galaxy_catalog: messagebox.showwarning("No Data", "Scan first."); return
        if self.running: return
        self.running = True; self.run_btn.config(state="disabled")
        threading.Thread(target=self._batch_thread, daemon=True).start()

    # ═══════════════════════════════════════
    # VISUALIZATION
    # ═══════════════════════════════════════

    def _draw_field(self, psi, phi, label=""):
        self._last_psi = psi; self._last_phi = phi; self._last_label = label
        self.canvas.delete("all")
        w, h = self._canvas_w, self._canvas_h
        if psi is None: return

        ny, nx = psi.shape; cy, cx = ny//2, nx//2; mr = min(cx,cy)-8
        if mr < 3: return
        pp = np.zeros(mr); pf = np.zeros(mr); ct = np.zeros(mr)
        for iy in range(ny):
            for ix in range(nx):
                ri = int(np.sqrt((ix-cx)**2+(iy-cy)**2))
                if ri < mr: pp[ri] += psi[iy,ix]; pf[ri] += phi[iy,ix]; ct[ri] += 1
        m = ct > 0; pp[m] /= ct[m]; pf[m] /= ct[m]
        pm1, pm2 = np.max(np.abs(pp)), np.max(np.abs(pf))
        if pm1 > 0: pp /= pm1
        if pm2 > 0: pf /= pm2
        n = len(pp)
        if n < 2: return

        # Correlation
        n30 = min(30, n)
        try: corr_val = np.corrcoef(pp[1:n30], pf[1:n30])[0,1]
        except: corr_val = 0.0

        ml, mrg, mt, mb = 60, 30, 40, 40
        pw, ph2 = w-ml-mrg, h-mt-mb
        if pw < 50 or ph2 < 50: return

        self.canvas.create_rectangle(ml, mt, w-mrg, h-mb, fill="#0c1018", outline="#2a3548")
        for i in range(5):
            y = mt + i*ph2/4
            self.canvas.create_line(ml, y, w-mrg, y, fill="#1a2535", dash=(2,4))
            self.canvas.create_text(ml-8, y, text=f"{1.0-i*0.5:.1f}", fill="#e0e8f0", font=("Consolas",11), anchor="e")

        # Substrate
        pts = [(ml+(i/n)*pw, max(mt, min(h-mb, mt+(1.0-(-pp[i]))*ph2))) for i in range(n)]
        if len(pts)>1: self.canvas.create_line(*[c for p in pts for c in p], fill="#60aaff", width=3, smooth=True)

        # Newton
        pts2 = [(ml+(i/n)*pw, max(mt, min(h-mb, mt+(1.0-(-pf[i]))*ph2))) for i in range(n)]
        if len(pts2)>1: self.canvas.create_line(*[c for p in pts2 for c in p], fill="#ffbb44", width=3, smooth=True, dash=(8,4))

        # Legend
        lx = ml+12
        self.canvas.create_line(lx, mt+14, lx+25, mt+14, fill="#60aaff", width=3)
        self.canvas.create_text(lx+30, mt+14, text="Ψ (Substrate)", fill="#ffffff", font=("Consolas",12,"bold"), anchor="w")
        self.canvas.create_line(lx, mt+32, lx+25, mt+32, fill="#ffbb44", width=3, dash=(8,4))
        self.canvas.create_text(lx+30, mt+32, text="Φ (Newton)", fill="#ffffff", font=("Consolas",12,"bold"), anchor="w")

        if label:
            self.canvas.create_text(w-mrg-10, mt+14, text=label, fill="#ffffff", font=("Consolas",14,"bold"), anchor="e")

        cc = "#40ee70" if corr_val>0.95 else "#90cc40" if corr_val>0.85 else "#ccaa30" if corr_val>0.70 else "#cc4040"
        self.canvas.create_text(w-mrg-10, mt+36, text=f"r = {corr_val:+.4f}", fill=cc, font=("Consolas",13,"bold"), anchor="e")
        self.canvas.create_text(w//2, h-10, text="radius", fill="#e0e8f0", font=("Consolas",12))
        self.canvas.create_text(18, h//2, text="potential", fill="#e0e8f0", font=("Consolas",12), angle=90)

    def _draw_live(self, rho, step, total):
        self.canvas.delete("all")
        w, h = self._canvas_w, self._canvas_h
        field = np.abs(rho[0]) if len(rho.shape)==3 else np.abs(rho)
        ny, nx = field.shape
        cw, ch = w/nx, (h-50)/ny
        fm = np.max(field)
        if fm <= 0: fm = 1.0
        sx, sy = max(1, nx//80), max(1, ny//80)
        for iy in range(0, ny, sy):
            for ix in range(0, nx, sx):
                v = field[iy,ix]/fm
                b = int(min(255, 60+v*195)); g = int(min(255, v*80)); r = int(min(255, v*30))
                self.canvas.create_rectangle(ix*cw, iy*ch, (ix+sx)*cw, (iy+sy)*ch, fill=f"#{r:02x}{g:02x}{b:02x}", outline="")
        pct = step/total*100 if total>0 else 0
        phase = "Settling" if step < self.settle_var.get() else "Measuring"
        self.canvas.create_text(w//2, h-25, text=f"{phase}  step {step}/{total}  ({pct:.0f}%)  |ρ|_max={fm:.2f}", fill="#ffffff", font=("Consolas",11,"bold"))

    # ═══════════════════════════════════════
    # SOLVER
    # ═══════════════════════════════════════


    def _draw_rotation(self, comp, galaxy_name=""):
        """Three-line rotation curve: V_obs vs V_newton vs V_substrate."""
        self._last_psi = None
        self.canvas.delete("all")
        w, h = self._canvas_w, self._canvas_h
        r = comp["r_kpc"]; vo = comp["v_obs"]; vn = comp["v_newton"]; vs = comp["v_substrate"]
        n = len(r)
        if n < 2: return
        ml, mrg, mt, mb = 60, 30, 40, 45
        pw, ph2 = w-ml-mrg, h-mt-mb
        if pw < 50 or ph2 < 50: return
        r_max = max(np.max(r), 0.1); v_max = max(np.max(vo), np.max(vn), np.max(vs), 1) * 1.1
        self.canvas.create_rectangle(ml, mt, w-mrg, h-mb, fill="#0c1018", outline="#2a3548")
        for i in range(5):
            y = mt + i*ph2/4; self.canvas.create_line(ml, y, w-mrg, y, fill="#1a2535", dash=(2,4))
            self.canvas.create_text(ml-8, y, text=f"{v_max*(1-i/4):.0f}", fill="#e0e8f0", font=("Consolas",10), anchor="e")
        def xy(rv, vv): return max(ml,min(w-mrg, ml+(rv/r_max)*pw)), max(mt,min(h-mb, mt+(1-vv/v_max)*ph2))
        pts_o = [xy(r[i],vo[i]) for i in range(n)]
        pts_n = [xy(r[i],vn[i]) for i in range(n)]
        pts_s = [xy(r[i],vs[i]) for i in range(n)]
        if len(pts_o)>1: self.canvas.create_line(*[c for p in pts_o for c in p], fill="#ffffff", width=3, smooth=True)
        if len(pts_n)>1: self.canvas.create_line(*[c for p in pts_n for c in p], fill="#ffbb44", width=2, smooth=True, dash=(6,4))
        # MOND (red)
        v_mond = comp.get("v_mond")
        if v_mond is not None:
            pts_m = [xy(r[i],v_mond[i]) for i in range(n)]
            if len(pts_m)>1: self.canvas.create_line(*[c for p in pts_m for c in p], fill="#ff5555", width=2, smooth=True, dash=(4,3))
        if len(pts_s)>1: self.canvas.create_line(*[c for p in pts_s for c in p], fill="#60aaff", width=2, smooth=True)
        lx = ml+12
        self.canvas.create_line(lx,mt+10,lx+25,mt+10,fill="#ffffff",width=3)
        self.canvas.create_text(lx+30,mt+10,text="V_obs",fill="#ffffff",font=("Consolas",10,"bold"),anchor="w")
        self.canvas.create_line(lx,mt+24,lx+25,mt+24,fill="#ffbb44",width=2,dash=(6,4))
        self.canvas.create_text(lx+30,mt+24,text="V_newton",fill="#ffbb44",font=("Consolas",9),anchor="w")
        self.canvas.create_line(lx,mt+38,lx+25,mt+38,fill="#ff5555",width=2,dash=(4,3))
        self.canvas.create_text(lx+30,mt+38,text="V_MOND",fill="#ff5555",font=("Consolas",9),anchor="w")
        self.canvas.create_line(lx,mt+52,lx+25,mt+52,fill="#60aaff",width=2)
        self.canvas.create_text(lx+30,mt+52,text="V_substrate",fill="#60aaff",font=("Consolas",9),anchor="w")
        if galaxy_name: self.canvas.create_text(w-mrg-10,mt+12,text=galaxy_name,fill="#ffffff",font=("Consolas",14,"bold"),anchor="e")
        wn = comp["winner"]
        wc = "#40ee70" if wn=="SUBSTRATE" else "#ff5555" if wn=="MOND" else "#ffbb44" if wn=="NEWTON" else "#888888"
        self.canvas.create_text(w-mrg-10,mt+32,text=f"Winner: {wn}",fill=wc,font=("Consolas",12,"bold"),anchor="e")
        svn = comp.get("sub_vs_newton", 0); svm = comp.get("sub_vs_mond", 0)
        self.canvas.create_text(w-mrg-10,mt+48,text=f"vs Newton: {svn:+.1f}",fill="#ffbb44",font=("Consolas",10),anchor="e")
        self.canvas.create_text(w-mrg-10,mt+62,text=f"vs MOND: {svm:+.1f}",fill="#ff5555",font=("Consolas",10),anchor="e")
        self.canvas.create_text(w//2,h-8,text="radius (kpc)",fill="#e0e8f0",font=("Consolas",11))
        self.canvas.create_text(18,h//2,text="V (km/s)",fill="#e0e8f0",font=("Consolas",11),angle=90)

    def _open_genesis(self):
        if not _GENESIS_AVAILABLE:
            from tkinter import messagebox
            messagebox.showwarning("Genesis Renderer",
                "Burdick_Crag_Mass_Genesis_Renderer.py not found.")
            return
        if self._last_rho_avg is None:
            from tkinter import messagebox
            messagebox.showinfo("Genesis Renderer", "Run solver first to generate field data.")
            return
        GenesisRenderer(self.root, self._last_rho_avg,
                        self._last_galaxy,
                        n_layers=self._last_rho_avg.shape[0])

    def _get_bcm_source(self, name, J_default, grid, vmax):
        """Apply v8 structural override source for a specific galaxy."""
        cfg = self._bcm_galaxies.get(name, {})
        src = cfg.get("source", "classic")
        extra_lam = None

        if src == "bar_dipole":
            from core.substrate_solver import linear_dipole_source
            amp = float(np.max(J_default)) if np.max(J_default) > 0 else 8.0
            amp *= cfg.get("liner", 1.0)
            J = linear_dipole_source(grid=grid, amplitude=amp,
                                     bar_length_frac=cfg.get("bar_len", 0.35),
                                     bar_width_frac=cfg.get("bar_wid", 0.06),
                                     bar_angle_deg=cfg.get("bar_angle", 0.0))
            self.log(f"    [BCM] Bar dipole: angle={cfg['bar_angle']}°  liner={cfg.get('liner',1):.2f}")
            return J, extra_lam

        elif src == "void_depleted":
            J = J_default.copy()
            cx = cy = grid // 2
            r_max_kpc = max(10.0, vmax * 0.15)
            kpc_per_grid = r_max_kpc / (grid // 2)
            vr_grid = int(15.0 / kpc_per_grid)
            iy_arr, ix_arr = np.mgrid[0:grid, 0:grid]
            vx_g = int(cx + 10.0 / kpc_per_grid)
            vy_g = int(cy - 5.0 / kpc_per_grid)
            r_void = np.sqrt((ix_arr-vx_g)**2 + (iy_arr-vy_g)**2)
            depletion = cfg.get("depletion", 0.65) * np.exp(
                -r_void**2 / (2.0*(vr_grid*0.5)**2))
            J *= (1.0 - np.clip(depletion, 0, 0.95))
            self.log(f"    [BCM] Void depletion: {cfg.get('depletion',0.65):.0%}")
            return J, extra_lam

        elif src == "ram_pressure":
            cx = cy = grid // 2
            angle = np.radians(cfg.get("angle", 135.0))
            iy_arr, ix_arr = np.mgrid[0:grid, 0:grid]
            proj = ((ix_arr-cx)*np.cos(angle) + (iy_arr-cy)*np.sin(angle))
            proj_n = proj / (grid // 2)
            ll, lt = cfg.get("lam_lead", 0.18), cfg.get("lam_trail", 0.04)
            lam_mid = (ll + lt) / 2.0
            extra_lam = float(lam_mid + (ll-lt)/2.0 * np.mean(proj_n))
            extra_lam = max(0.001, min(1.0, extra_lam))
            self.log(f"    [BCM] Ram pressure λ_eff={extra_lam:.3f}")
            return J_default, extra_lam

        elif src == "hi_fits":
            hi_dir   = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "data", "hi_maps")
            fits_path = os.path.join(hi_dir, f"{name}_mom0.fits")
            if os.path.exists(fits_path):
                try:
                    from astropy.io import fits as _afits
                    from scipy.ndimage import zoom as _zoom
                    with _afits.open(fits_path) as hdul:
                        mom0 = hdul[0].data.squeeze()
                        mom0 = np.nan_to_num(mom0, nan=0.0)
                        mom0 = np.maximum(mom0, 0.0)
                        factor = grid / max(mom0.shape)
                        J_2d   = _zoom(mom0, factor)
                        if J_2d.shape[0] != grid:
                            J_2d = _zoom(J_2d, grid / J_2d.shape[0])
                        amp = float(np.max(J_default)) if np.max(J_default) > 0 else 8.0
                        if np.max(J_2d) > 0:
                            J_2d *= amp / np.max(J_2d)
                        self.log(f"    [BCM] 2D HI FITS: {name}  shape={mom0.shape}")
                        return J_2d.astype(np.float64), extra_lam
                except Exception as e:
                    self.log(f"    [BCM] FITS load failed {name}: {e} — classic fallback")
            else:
                self.log(f"    [BCM] FITS not found: {fits_path} — classic fallback")
            return J_default, extra_lam

        else:
            self.log(f"    [BCM] Classic source (no override)")
            return J_default, extra_lam

    def _run_bcm_galaxy(self, name, info):
        """Run one BCM structural override galaxy."""
        grid    = self.grid_var.get()
        layers  = self.layers_var.get()
        settle  = self.settle_var.get()
        measure = self.measure_var.get()
        gamma   = self.gamma_var.get()
        entangle= self.entangle_var.get()
        c_wave  = self.cwave_var.get()
        lam     = self.lambda_real_var.get()

        try:
            from core.sparc_ingest import load_galaxy
            gal     = load_galaxy(info["path"], grid)
            J_default = gal["source_field"]
            vmax    = info["v_max"]

            # === BCM MASTER BUILD ADDITION v2.2 | 2026-03-30 EST ===
            # Outer-slope derived lam — data-driven, not galaxy-specific tuning
            _v = gal["vobs"]
            _r = gal["radii_kpc"]
            _k = max(1, len(_v) // 5)
            _slope = (_v[-1] - _v[-_k]) / (_r[-1] - _r[-_k]) if (_r[-1] - _r[-_k]) > 0 else 0.0
            _norm_slope = _slope / max(abs(_v)) if max(abs(_v)) > 0 else 0.0
            _lam_data = float(np.clip(0.1 * (1 - 0.5 * _norm_slope), 0.02, 0.2))
            # === END ADDITION ===

            # ── Apply BCM structural override ──
            from BCM_Substrate_overrides import apply_galaxy_override
            J, extra_params, applied = apply_galaxy_override(
                name, J_default, grid, vmax_kms=vmax, verbose=True)

            cls = self._bcm_galaxies.get(name, {}).get("class", "?")
            self.log(f"  [BCM] {name} Class {cls} — override={'YES' if applied else 'NO'}")

            extra_params["outer_slope"] = round(float(_slope), 6)
            run_lam = extra_params.get("lam", _lam_data)

            solver = SubstrateSolver(grid=grid, layers=layers, lam=run_lam,
                                     gamma=gamma, entangle=entangle,
                                     c_wave=c_wave, settle=settle, measure=measure)

            def _cb(step, total, rho, sigma):
                if step % 2000 == 0:
                    self.root.after(0, lambda r=rho.copy(), s=step, t=total:
                                    self._draw_live(r, s, t))

            r = solver.run(J, verbose=False, callback=_cb,
                           galaxy_name=name if self.crag_var.get() else None,
                           vmax_kms=vmax,
                           use_crag=self.crag_var.get(),
                           crag_kappa=self.crag_kappa_var.get())

            self._last_rho_avg = r.get("rho_avg", None)
            self._last_galaxy  = f"{name}_bcm"

            from core.rotation_compare import compare_rotation
            comp = compare_rotation(r, gal)
            self.log(f"    N={comp['rms_newton']:.1f}  M={comp['rms_mond']:.1f}"
                     f"  S={comp['rms_substrate']:.1f}  delta={comp['sub_vs_newton']:+.1f}"
                     f"  Winner: {comp['winner']}")

            self.root.after(0, lambda c=comp, nm=name: self._draw_rotation(c, nm+"[BCM]"))
            self.bcm_status_var.set(f"{name} done — Winner: {comp['winner']}")

            # ── Tag override info into extra_params for the save record ──
            cls = self._bcm_galaxies.get(name, {}).get("class", "?")
            extra_params["bcm_class"] = f"Class {cls}"
            extra_params["override_applied"] = applied

            # ── Prompt to name and save run JSON ──
            _comp = comp
            _ep   = dict(extra_params)
            _g, _l, _la = grid, layers, lam
            _ga, _en, _cw, _se, _me = gamma, entangle, c_wave, settle, measure
            self.root.after(300, lambda: self._save_bcm_run(
                name, _comp, _ep, _g, _l, _la, _ga, _en, _cw, _se, _me))

        except Exception as e:
            import traceback
            self.root.after(0, lambda err=str(e): self.log(f"  [BCM] ERROR: {err}"))
            self.root.after(0, lambda tb=traceback.format_exc(): self.log(tb))

    def _save_bcm_run(self, name, comp, extra_params, grid, layers, lam,
                      gamma, entangle, c_wave, settle, measure):
        """Prompt for run name and save BCM result JSON to data/results/."""
        import tkinter.simpledialog as sd
        default = f"BCM_{name}_{time.strftime('%Y%m%d_%H%M%S')}"
        run_name = sd.askstring(
            "Save BCM Run",
            f"Name this run — {name}:",
            initialvalue=default,
            parent=self.root
        )
        if not run_name:
            self.log(f"  [BCM] Save cancelled — {name}")
            return

        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "results")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{run_name}.json")

        record = {
            "run_name":  run_name,
            "galaxy":    name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "bcm_class": extra_params.get("bcm_class", "?"),
            "override_applied": extra_params.get("override_applied", False),
            "dat_found": extra_params.get("dat_found", None),
            "outer_slope": extra_params.get("outer_slope", None),
            "parameters": {
                "grid":     grid,
                "layers":   layers,
                "lam":      extra_params.get("lam", lam),
                "gamma":    gamma,
                "entangle": entangle,
                "c_wave":   c_wave,
                "settle":   settle,
                "measure":  measure,
            },
            "results": {
                "rms_newton":     round(comp["rms_newton"], 4),
                "rms_mond":       round(comp["rms_mond"], 4),
                "rms_substrate":  round(comp["rms_substrate"], 4),
                "winner":         comp["winner"],
                "outer_winner":   comp["outer_winner"],
                "sub_vs_newton":  round(comp["sub_vs_newton"], 4),
                "sub_vs_mond":    round(comp["sub_vs_mond"], 4),
                "corr_newton":    round(comp["corr_newton"], 6),
                "corr_mond":      round(comp["corr_mond"], 6),
                "corr_substrate": round(comp["corr_substrate"], 6),
                # === BCM MASTER BUILD ADDITION v2.2 | 2026-03-30 EST ===
                "cos_delta_phi":    comp.get("cos_delta_phi",    None),
                "delta_phi":        comp.get("delta_phi",        None),
                "decoupling_ratio": comp.get("decoupling_ratio", None),
                "substrate_excess": comp.get("substrate_excess", None),
                # === END ADDITION ===

            },
        }

        with open(out_path, 'w') as f:
            json.dump(record, f, indent=2)
        self.log(f"  [BCM] Saved: {out_path}")
        self.bcm_status_var.set(f"Saved: {run_name}.json")

    def _find_dat(self, name):
        """Find a galaxy .dat — checks catalog first, then walks all sparc_raw subdirs."""
        if name in self.galaxy_catalog:
            return self.galaxy_catalog[name]["path"]
        dd = self.data_dir_var.get()
        for root, dirs, files in os.walk(dd):
            for f in files:
                if f == f"{name}_rotmod.dat" or f == f"{name}.dat":
                    return os.path.join(root, f)
        return None

    def _read_vmax(self, dat_path):
        """Read peak observed velocity from a .dat file."""
        try:
            with open(dat_path) as fh:
                lines = [l for l in fh if l.strip() and not l.startswith('#')]
            vobs = [float(l.split()[1]) for l in lines if len(l.split()) >= 2]
            return max(vobs) if vobs else 200.0
        except Exception:
            return 200.0

    def _run_bcm_selected(self):
        sel = self.bcm_listbox.curselection()
        if not sel:
            self.bcm_status_var.set("Select a galaxy in the BCM list")
            return
        name = list(self._bcm_galaxies.keys())[sel[0]]
        dat_path = self._find_dat(name)
        if not dat_path:
            self.log(f"  [BCM] NOT FOUND: {name}_rotmod.dat (searched all subdirs)")
            self.bcm_status_var.set(f"NOT FOUND: {name}_rotmod.dat")
            return
        info = {"path": dat_path, "v_max": self._read_vmax(dat_path)}
        self.log(f"  [BCM] Selected: {name}  V={info['v_max']:.0f} km/s")
        self.bcm_status_var.set(f"Running {name}...")
        import threading
        threading.Thread(target=self._run_bcm_galaxy,
                         args=(name, info), daemon=True).start()

    def _run_bcm_all(self):
        if self.running: return
        self.running = True
        self.run_btn.config(state="disabled")
        import threading
        def _t():
            try:
                for name in self._bcm_galaxies:
                    self.root.after(0, lambda n=name:
                        self.bcm_status_var.set(f"Running {n}..."))
                    dat_path = self._find_dat(name)
                    if not dat_path:
                        self.log(f"  [BCM] SKIP {name} — dat not found in any subdir")
                        continue
                    info = {"path": dat_path, "v_max": self._read_vmax(dat_path)}
                    self._run_bcm_galaxy(name, info)
                self.root.after(0, lambda: self.bcm_status_var.set("BCM All complete"))
            finally:
                self.running = False
                self.root.after(0, lambda: self.run_btn.config(state="normal"))
        threading.Thread(target=_t, daemon=True).start()

    def _run_solver(self):
        if self.running: return
        self.running = True; self.run_btn.config(state="disabled")
        self.progress_var.set(0); self._last_psi = None
        threading.Thread(target=self._solver_thread, daemon=True).start()

    def _solver_thread(self):
        try:
            grid = self.grid_var.get(); layers = self.layers_var.get()
            settle = self.settle_var.get(); measure = self.measure_var.get()
            gamma = self.gamma_var.get(); entangle = self.entangle_var.get()
            c_wave = self.cwave_var.get(); total_steps = settle + measure

            reset_calibration()
            src = self.source_var.get(); src_name = src
            if src == "gaussian": J = gaussian_source(grid); src_name = f"Gaussian ({grid}x{grid})"
            elif src == "point_mass": J = point_source(grid); src_name = f"Point Mass ({grid}x{grid})"
            elif src == "sparc":
                sp = self.sparc_path_var.get()
                if not sp or not os.path.exists(sp):
                    self.root.after(0, lambda: messagebox.showwarning("No File", "Select a galaxy.")); return
                from core.sparc_ingest import load_galaxy
                gal = load_galaxy(sp, grid); J = gal["source_field"]
                src_name = f"{gal['name']} ({len(gal['radii_kpc'])}pt)"
            else: J = gaussian_source(grid)

            self.log(f"\nSource: {src_name}")
            regime = self.regime_var.get(); runs = []
            if regime in ("both","control"): runs.append(("CONTROL λ→0", self.lambda_ctrl_var.get()))
            if regime in ("both","real"): runs.append(("REAL λ≠0", self.lambda_real_var.get()))

            result_lines = []
            for label, lam in runs:
                self.log(f"{'─'*55}\n  {label}  λ={lam}\n  grid={grid} layers={layers} settle={settle} measure={measure}\n{'─'*55}")

                def live_cb(step, total, rho, sigma):
                    pct = step/total*100 if total>0 else 0
                    phase = "Settling" if step < settle else "Measuring"
                    self.root.after(0, lambda p=pct, ph=phase, s=step, t=total:
                        (self.progress_var.set(p), self.progress_label.config(text=f"{ph} {s}/{t} ({p:.0f}%)")))
                    if step % 2000 == 0:
                        self.root.after(0, lambda r=rho.copy(), s=step, t=total: self._draw_live(r, s, t))
                    if step % 3000 == 0:
                        rm, sm = np.max(np.abs(rho)), np.max(sigma)
                        ph = "[M]" if step >= settle else ""
                        self.root.after(0, lambda rm=rm, sm=sm, s=step, p=ph:
                            self.log(f"    step {s:6d}  |ρ|={rm:.2f}  Σ={sm:.1f} {p}"))

                solver = SubstrateSolver(grid=grid, layers=layers, lam=lam, gamma=gamma, entangle=entangle, c_wave=c_wave, settle=settle, measure=measure)
                result = solver.run(J, verbose=False, callback=live_cb)

                cf, cl = result["corr_full"], result["corr_lap"]
                ri, rf2 = result["corr_radial_inner"], result["corr_radial_full"]
                lc, el = result["layer_coherence"], result["elapsed"]

                self.log(f"\n  RESULTS ({el:.1f}s):\n  Ψ vs Φ full:      {cf:+.6f}\n  ∇²Ψ vs ρ:         {cl:+.6f}\n  Radial inner:     {ri:+.6f}\n  Radial full:      {rf2:+.6f}\n  Layer coherence:  {lc:+.6f}")
                result_lines.append(f"{label}: Ψ~Φ={cf:+.4f}  inner={ri:+.4f}  ({el:.1f}s)")

                self.root.after(0, lambda p=result["psi"], n=result["phi_newton"], lb=label: self._draw_field(p, n, lb))
                self.root.after(0, lambda c=cf, r=ri, l=lc: self.live_stats_var.set(f"Ψ~Φ: {c:+.4f}  |  inner: {r:+.4f}  |  layers: {l:+.4f}"))

                # Rotation curve comparison (SPARC galaxies only)
                if src == "sparc" and 'gal' in dir():
                    try:
                        comp = compare_rotation(result, gal)
                        print_comparison(comp, gal["name"])
                        self.log(f"\n  ROTATION CURVE TEST:")
                        self.log(f"    Newton  RMS: {comp['rms_newton']:.2f} km/s  r={comp['corr_newton']:+.4f}")
                        self.log(f"    MOND    RMS: {comp['rms_mond']:.2f} km/s  r={comp['corr_mond']:+.4f}")
                        self.log(f"    Substr  RMS: {comp['rms_substrate']:.2f} km/s  r={comp['corr_substrate']:+.4f}")
                        self.log(f"    Sub vs Newton: {comp['sub_vs_newton']:+.2f} km/s")
                        self.log(f"    Sub vs MOND:   {comp['sub_vs_mond']:+.2f} km/s")
                        self.log(f"    Winner: {comp['winner']}  (outer: {comp['outer_winner']})")
                        self.root.after(0, lambda c=comp, nm=gal["name"]: self._draw_rotation(c, nm))
                    except Exception as ex:
                        self.log(f"    Comparison error: {ex}")

                self._last_rho_avg = result.get("rho_avg", None)
                self._last_galaxy  = src_name
                self.results_history.append({"label":label, "source":src_name, "config":result["config"], "corr_full":float(cf), "corr_inner":float(ri), "elapsed":el, "timestamp":time.strftime("%Y-%m-%d %H:%M:%S")})

            self.root.after(0, lambda: self.set_result("\n".join(result_lines)))
            self.root.after(0, lambda: (self.progress_var.set(100), self.progress_label.config(text="Done")))
            self.log(f"\n{'─'*55}\n  Complete. {len(runs)} regime(s) tested.")

        except Exception as e:
            import traceback; tb = traceback.format_exc()
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.log(tb))
        finally:
            self.running = False
            self.root.after(0, lambda: self.run_btn.config(state="normal"))
            self.root.after(0, lambda: self.status_var.set("Ready"))

    def _batch_thread(self):
        try:
            grid, layers = self.grid_var.get(), self.layers_var.get()
            settle, measure = self.settle_var.get(), self.measure_var.get()
            gamma, entangle, c_wave = self.gamma_var.get(), self.entangle_var.get(), self.cwave_var.get()
            lam = self.lambda_real_var.get()
            names = list(self.galaxy_catalog.keys())
            self.log(f"\n{'═'*55}\n  BATCH: {len(names)} galaxies  λ={lam}\n{'═'*55}")
            batch = []
            for idx, name in enumerate(names):
                info = self.galaxy_catalog[name]
                self.root.after(0, lambda n=name, i=idx: (self.status_var.set(f"[{i+1}/{len(names)}] {n}"), self.progress_var.set(i/len(names)*100)))
                self.log_galaxy_header(idx+1, len(names), name)
                try:
                    from core.sparc_ingest import load_galaxy
                    gal = load_galaxy(info["path"], grid)
                    J = gal["source_field"]
                    solver = SubstrateSolver(grid=grid, layers=layers, lam=lam, gamma=gamma, entangle=entangle, c_wave=c_wave, settle=settle, measure=measure)
                    def _batch_cb(step, total, rho, sigma):
                        if step % 2000 == 0:
                            self.root.after(0, lambda r=rho.copy(), s=step, t=total: self._draw_live(r, s, t))
                    r = solver.run(
                        J, verbose=False, callback=_batch_cb,
                        galaxy_name=name if self.crag_var.get() else None,
                        vmax_kms=info["v_max"],
                        use_crag=self.crag_var.get(),
                        crag_kappa=self.crag_kappa_var.get()
                    )
                    cf = r["corr_full"]; ci = r["corr_radial_inner"]
                    self.log(f"    Ψ~Φ={cf:+.4f}  inner={ci:+.4f}  ({r['elapsed']:.1f}s)")

                    # Three-way comparison: Newton vs MOND vs Substrate
                    entry = {"galaxy":name, "corr_full":float(cf), "corr_inner":float(ci), "v_max":info["v_max"], "elapsed":r["elapsed"]}
                    try:
                        comp = compare_rotation(r, gal)
                        entry["rms_newton"] = float(comp["rms_newton"])
                        entry["rms_mond"] = float(comp["rms_mond"])
                        entry["rms_substrate"] = float(comp["rms_substrate"])
                        entry["corr_newton_shape"] = float(comp["corr_newton"])
                        entry["corr_mond_shape"] = float(comp["corr_mond"])
                        entry["corr_substrate_shape"] = float(comp["corr_substrate"])
                        entry["winner"] = comp["winner"]
                        entry["outer_winner"] = comp["outer_winner"]
                        entry["sub_vs_newton"] = float(comp["sub_vs_newton"])
                        entry["sub_vs_mond"] = float(comp["sub_vs_mond"])
                        wn = comp["winner"]
                        self.log_result(
                            comp["rms_newton"], comp["rms_mond"], comp["rms_substrate"],
                            wn, r["corr_full"], r["corr_radial_inner"]
                        )
                        self.root.after(0, lambda c=comp, nm=name: self._draw_rotation(c, nm))
                    except Exception as ex:
                        self.log(f"    Compare: {ex}")
                        self.root.after(0, lambda p=r["psi"], n=r["phi_newton"], nm=name: self._draw_field(p, n, nm))

                    self._last_rho_avg = r.get("rho_avg", None)
                    self._last_galaxy  = name
                    batch.append(entry)
                except Exception as e: self.log(f"    ERROR: {e}")
            if batch:
                ac, ai = np.mean([r["corr_full"] for r in batch]), np.mean([r["corr_inner"] for r in batch])
                self.log(f"\n{'═'*55}")
                self.log(f"  BATCH DONE: {len(batch)} galaxies")
                self.log(f"  Avg Ψ~Φ: {ac:+.4f}  inner: {ai:+.4f}")

                # Three-way summary
                has_rms = [r for r in batch if "rms_newton" in r]
                if has_rms:
                    avg_rn = np.mean([r["rms_newton"] for r in has_rms])
                    avg_rm = np.mean([r["rms_mond"] for r in has_rms])
                    avg_rs = np.mean([r["rms_substrate"] for r in has_rms])
                    sub_wins = sum(1 for r in has_rms if r.get("winner") == "SUBSTRATE")
                    mond_wins = sum(1 for r in has_rms if r.get("winner") == "MOND")
                    newt_wins = sum(1 for r in has_rms if r.get("winner") == "NEWTON")
                    ties = sum(1 for r in has_rms if r.get("winner") == "TIE")
                    self.log(f"\n  THREE-WAY RMS (avg km/s):")
                    self.log(f"    Newton:    {avg_rn:.2f}")
                    self.log(f"    MOND:      {avg_rm:.2f}")
                    self.log(f"    Substrate: {avg_rs:.2f}")
                    self.log(f"\n  WINS: Substrate={sub_wins}  MOND={mond_wins}  Newton={newt_wins}  Tie={ties}")
                    self.root.after(0, lambda: self.set_result(
                        f"Batch: {len(batch)} galaxies\n"
                        f"Avg RMS — N:{avg_rn:.1f}  M:{avg_rm:.1f}  S:{avg_rs:.1f}\n"
                        f"Wins — Sub:{sub_wins}  MOND:{mond_wins}  Newt:{newt_wins}  Tie:{ties}"))
                else:
                    self.root.after(0, lambda: self.set_result(f"Batch: {len(batch)} galaxies\nAvg Ψ~Φ: {ac:+.4f}\nAvg inner: {ai:+.4f}"))

                # Calibration spread analysis
                cal = get_calibration_stats()
                if cal:
                    self.log(f"\n  CALIBRATION ANALYSIS:")
                    self.log(f"    C_cal mean:   {cal['mean']:.4f}")
                    self.log(f"    C_cal std:    {cal['std']:.4f}")
                    self.log(f"    C_cal CV:     {cal['cv']:.2%}")
                    self.log(f"    C_cal range:  {cal['min']:.4f} - {cal['max']:.4f}")
                    if cal['cv'] < 0.3:
                        self.log(f"    >>> LOW SPREAD — universal constant viable")
                    elif cal['cv'] < 0.6:
                        self.log(f"    >>> MODERATE SPREAD — partially universal")
                    else:
                        self.log(f"    >>> HIGH SPREAD — per-galaxy scaling needed")
                self.log(f"{'═'*55}")
                od = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "results")
                os.makedirs(od, exist_ok=True)
                op = os.path.join(od, f"batch_{time.strftime('%Y%m%d_%H%M%S')}.json")
                with open(op,'w') as f: json.dump(batch, f, indent=2)
                self.log(f"  Saved: {op}")
        except Exception as e:
            import traceback
            self.root.after(0, lambda: messagebox.showerror("Batch Error", str(e)))
            self.root.after(0, lambda: self.log(traceback.format_exc()))
        finally:
            self.running = False
            self.root.after(0, lambda: self.run_btn.config(state="normal"))
            self.root.after(0, lambda: self.status_var.set("Ready"))
            self.root.after(0, lambda: (self.progress_var.set(100), self.progress_label.config(text="Complete")))

    def _export_results(self):
        if not self.results_history: messagebox.showinfo("No Results", "Run solver first."); return
        p = filedialog.asksaveasfilename(title="Save", defaultextension=".json", filetypes=[("JSON","*.json")], initialdir=os.path.join(os.path.dirname(__file__),"data","results"), initialfile=f"results_{time.strftime('%Y%m%d_%H%M%S')}.json")
        if p:
            with open(p,'w') as f: json.dump(self.results_history, f, indent=2)
            self.log(f"  Exported: {p}")

    # ═══════════════════════════════════════════════════════
    # TAB 7 — TEST RUNNER (directory-scanned, date-sorted)
    # ═══════════════════════════════════════════════════════
    # Drop a .py in BCM_EPIC_OpT_tests/ → hit Refresh → run.
    # No hardcoded registry. The directory IS the registry.
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _parse_test_info(filename):
        """Extract version and display name from filename."""
        import re
        base = filename.replace(".py", "")

        # BCM_v{N}_name or BCM_V{N}_name pattern
        m = re.match(r"BCM_[vV](\d+)_(.+)", base)
        if m:
            return f"v{m.group(1)}", m.group(2).replace("_", " ").title()

        # test_name pattern (foundation tests)
        m = re.match(r"test_(.+)", base)
        if m:
            return "foundation", m.group(1).replace("_", " ").title()

        # Known pre-v14 scripts (no version in filename)
        LEGACY_MAP = {
            "BCM_phase_lock": "v10",
            "BCM_3d_renderer": "v7",
            "BCM_tcf_analyzer": "v9",
            "BCM_tunnel_timeseries": "v8",
            "BCM_colonization_sweep_reverse": "v8",
            "BCM_colonization_sweep": "v8",
            "BCM_stellar_wave": "v4",
            "BCM_stellar_renderer": "v4",
            "BCM_planetary_wave": "v2",
            "BCM_phase_sweep": "v3",
            "BCM_planetary_renderer": "v2",
            "BCM_fetch_hi_maps": "v1",
            "BCM_drift_test": "v12",
            "BCM_lambda_drive": "v12",
            "BCM_solar_navigator": "v12",
            "BCM_inspiral_sweep": "v11",
            "BCM_inspiral_renderer": "v11",
            "BCM_cavitation_sweep": "v6",
            "BCM_dual_pump_matrix": "v13",
            "BCM_binary_drive": "v13",
            "BCM_alpha_centauri": "v7",
            "BCM_spine": "v13",
            "BCM_ghost_packet": "v14",
            "BCM_propulsion_regulator": "v14",
            "BCM_lagrange_scan": "v14",
            "BCM_freeze_sweep": "v13",
            "BCM_rigid_body": "v13",
            "BCM_pure_gradient": "v12",
            "BCM_saddle_field_test": "v12",
            "BCM_phase_lag_test": "v12",
            "BCM_phase_block": "v10",
            "BCM_self_funded_ship": "v13",
            "BCM_funded_corridors": "v13",
            "BCM_galactic_current": "v6",
            "BCM_energy_audit": "v15",
            "BCM_navigator": "v12",
            "BCM_flight_computer": "v12",
            "BCM_flight_computer_gui": "v12",
            "BCM_substrate_model": "v5",
            "BCM_tao_analysis": "v5",
            "BCM_ai_engine": "v12",
            "BCM_vector_alignment_test": "v12",
            "BCM_chi_squared_engine": "v22",
            "BCM_EPIC_OpT_test_deck": "tools",
        }
        if base in LEGACY_MAP:
            ver = LEGACY_MAP[base]
            name = base.replace("BCM_", "").replace("_", " ").title()
            return ver, name

        # Fallback: BCM_name → "other"
        m = re.match(r"BCM_(.+)", base)
        if m:
            return "other", m.group(1).replace("_", " ").title()

        return "other", base.replace("_", " ").title()

    def _scan_test_scripts(self):
        """Scan BCM_EPIC_OpT_tests/ for .py files, sorted by version then date."""
        root_dir = os.path.dirname(os.path.abspath(__file__))
        test_dir = os.path.join(root_dir,
            "TITS_EPICt_BCM", "BCM_EPIC_OpT_tests")
        if not os.path.isdir(test_dir):
            return [], test_dir
        scripts = []
        for fname in os.listdir(test_dir):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(test_dir, fname)
            mtime = os.path.getmtime(fpath)
            version, display_name = self._parse_test_info(fname)
            scripts.append((version, display_name, fname, mtime))
        # Version sort order
        def _vkey(v):
            if v == "foundation": return 0
            if v == "tools": return 1
            if v.startswith("v"):
                try: return int(v[1:]) + 10
                except ValueError: return 999
            return 1000
        scripts.sort(key=lambda x: (_vkey(x[0]), x[1].lower()))
        return scripts, test_dir

    def _build_test_runner_tab(self, parent):
        """Tab 7 — Test Runner. Scans directory, Refresh button, --quick toggle."""
        style_bg  = "#0a0c10"
        style_acc = "#44ddff"

        # ── Header with Refresh + --quick ──
        hf = tk.Frame(parent, bg=style_bg)
        hf.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(hf, text="TEST RUNNER",
                 font=("Georgia", 16), fg=style_acc, bg=style_bg
                 ).pack(side="left")
        tk.Label(hf, text="Directory Scan \u2014 One Click",
                 font=("Consolas", 10), fg="#6a7a90", bg=style_bg
                 ).pack(side="left", padx=(16, 0))

        self._test_quick_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(hf, text="--quick",
                        variable=self._test_quick_var
                        ).pack(side="right", padx=8)
        tk.Button(hf, text="Refresh",
                  font=("Consolas", 9), bg="#1a1e2a",
                  fg="#a0b0cc", relief="flat",
                  command=self._refresh_test_buttons
                  ).pack(side="right", padx=4)
        self._test_count_var = tk.StringVar(value="")
        tk.Label(hf, textvariable=self._test_count_var,
                 font=("Consolas", 9), fg="#6a7a90",
                 bg=style_bg).pack(side="right", padx=4)

        # ── PanedWindow: left=buttons, right=log ──
        pw = tk.PanedWindow(parent, orient="horizontal",
                            bg=style_bg, sashwidth=4,
                            sashrelief="flat")
        pw.pack(fill="both", expand=True, padx=12, pady=4)

        # ── LEFT PANEL: scrollable test buttons ──
        left_frame = tk.Frame(pw, bg=style_bg)
        pw.add(left_frame, width=380, minsize=250)

        self._test_canvas = tk.Canvas(
            left_frame, bg=style_bg, highlightthickness=0)
        left_vbar = ttk.Scrollbar(
            left_frame, orient="vertical",
            command=self._test_canvas.yview)
        self._test_canvas.configure(
            yscrollcommand=left_vbar.set)
        left_vbar.pack(side="right", fill="y")
        self._test_canvas.pack(
            side="left", fill="both", expand=True)

        self._test_btn_frame = tk.Frame(
            self._test_canvas, bg=style_bg)
        self._test_btn_id = self._test_canvas.create_window(
            (0, 0), window=self._test_btn_frame, anchor="nw")

        def _bf_resize(event):
            self._test_canvas.configure(
                scrollregion=self._test_canvas.bbox("all"))
        def _lc_resize(event):
            self._test_canvas.itemconfig(
                self._test_btn_id, width=event.width)
        self._test_btn_frame.bind("<Configure>", _bf_resize)
        self._test_canvas.bind("<Configure>", _lc_resize)

        # Robust scroll: bind globally when mouse enters canvas area
        def _on_enter(event):
            self._test_canvas.bind_all("<MouseWheel>",
                lambda e: self._test_canvas.yview_scroll(
                    int(-1 * (e.delta / 120)), "units"))
        def _on_leave(event):
            self._test_canvas.unbind_all("<MouseWheel>")
        left_frame.bind("<Enter>", _on_enter)
        left_frame.bind("<Leave>", _on_leave)

        # ── RIGHT PANEL: output log ──
        right_frame = tk.Frame(pw, bg=style_bg)
        pw.add(right_frame, minsize=400)

        log_header = tk.Frame(right_frame, bg=style_bg)
        log_header.pack(fill="x", padx=4, pady=(4, 2))
        tk.Label(log_header, text="OUTPUT",
                 font=("Consolas", 11, "bold"),
                 fg=style_acc, bg=style_bg).pack(side="left")
        tk.Button(log_header, text="Clear",
                  font=("Consolas", 9), bg="#1a1e2a",
                  fg="#a0b0cc", relief="flat",
                  command=lambda: self._test_log.delete(
                      "1.0", "end")
                  ).pack(side="right", padx=4)

        self._test_log = tk.Text(
            right_frame, bg="#06080c", fg="#44ddff",
            font=("Consolas", 9), relief="flat", wrap="word")
        test_scroll = ttk.Scrollbar(
            right_frame, orient="vertical",
            command=self._test_log.yview)
        self._test_log.configure(
            yscrollcommand=test_scroll.set)
        test_scroll.pack(side="right", fill="y")
        self._test_log.pack(fill="both", expand=True,
                            padx=4, pady=4)

        self._test_log_msg(
            "TEST RUNNER ready. Select a test from the left panel.")
        self._test_log_msg(
            "Each button runs the script and streams output here.")
        self._test_log_msg(
            "Stephen Justin Burdick Sr. \u2014 GIBUSH Systems")
        self._test_log_msg("\u2500" * 50)

        # ── Initial scan ──
        self.root.after(300, self._refresh_test_buttons)

    def _refresh_test_buttons(self):
        """Scan test directory and rebuild button list."""
        style_bg = "#0a0c10"
        style_acc = "#44ddff"

        # Clear existing buttons
        for widget in self._test_btn_frame.winfo_children():
            widget.destroy()

        scripts, test_dir = self._scan_test_scripts()
        self._test_count_var.set(f"{len(scripts)} tests")

        if not scripts:
            tk.Label(self._test_btn_frame,
                     text=f"No .py files found in\n{test_dir}",
                     font=("Consolas", 9), fg="#555555",
                     bg=style_bg).pack(padx=10, pady=20)
            return

        current_version = None
        for version, name, script, mtime in scripts:
            if version != current_version:
                current_version = version
                vf = tk.Frame(self._test_btn_frame, bg=style_bg)
                vf.pack(fill="x", padx=4, pady=(10, 2))
                tk.Label(vf,
                         text=f"\u2501\u2501 {version} \u2501\u2501",
                         font=("Consolas", 10, "bold"),
                         fg="#ff9944", bg=style_bg
                         ).pack(anchor="w")

            btn = tk.Button(
                self._test_btn_frame,
                text=f"  \u25B6  {name}",
                font=("Consolas", 9),
                bg="#12151c", fg="#a0b0cc",
                activebackground="#1a2030",
                activeforeground=style_acc,
                relief="flat", anchor="w",
                command=lambda s=script, n=name:
                    self._run_test_script(s, [], n))
            btn.pack(fill="x", padx=8, pady=1)

    def _test_log_msg(self, msg):
        """Write to test runner log."""
        self._test_log.insert("end", msg + "\n")
        self._test_log.see("end")

    def _run_test_script(self, script, extra_args, name):
        """Run any test script as subprocess, stream to log."""
        import subprocess

        root_dir = os.path.dirname(os.path.abspath(__file__))
        test_dir = os.path.join(root_dir,
            "TITS_EPICt_BCM", "BCM_EPIC_OpT_tests")

        # Check EPIC test folder first, fall back to root
        script_path = os.path.join(test_dir, script)
        if not os.path.exists(script_path):
            script_path = os.path.join(root_dir, script)

        if not os.path.exists(script_path):
            self._test_log_msg(f"\n  ERROR: {script} not found.")
            self._test_log_msg(
                f"  Checked: {test_dir}")
            self._test_log_msg(
                f"  Checked: {root_dir}")
            return

        # Build args — add --quick if checkbox is checked
        run_args = list(extra_args)
        if hasattr(self, '_test_quick_var') and self._test_quick_var.get():
            if "--quick" not in run_args:
                run_args.append("--quick")

        self._test_log_msg(f"\n{'='*50}")
        self._test_log_msg(f"  RUNNING: {name}")
        self._test_log_msg(f"  Script:  {script}")
        if run_args:
            self._test_log_msg(
                f"  Args:    {' '.join(run_args)}")
        self._test_log_msg(f"{'='*50}")

        args = [sys.executable, script_path] + run_args

        def _run():
            try:
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                proc = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=root_dir,
                    env=env,
                    bufsize=1)
                for line in iter(proc.stdout.readline, ''):
                    if line.strip():
                        self.root.after(
                            0,
                            lambda l=line.rstrip():
                                self._test_log_msg(l))
                proc.wait()
                rc = proc.returncode
                self.root.after(0, lambda: self._test_log_msg(
                    f"\n  EXIT CODE: {rc}"
                    f" {'(OK)' if rc == 0 else '(FAILED)'}"))
                self.root.after(0, lambda: self._test_log_msg(
                    "\u2500" * 50))
            except Exception as e:
                self.root.after(0, lambda: self._test_log_msg(
                    f"  ERROR: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    # ═══════════════════════════════════════════════════════
    # TAB 8 — EPIC COLLECTOR (substrate test ingestion)
    # ═══════════════════════════════════════════════════════
    # Ingestion hub: list JSON results, auto-tag Q-Cube,
    # show coverage, launch full PySide6 collector.
    # ═══════════════════════════════════════════════════════

    # Q-Cube axes (mirrors qcube_config.py substrate_physics_config)
    _QCUBE_SCALES = {"L1": "Galactic", "L2": "Stellar",
                     "L3": "Planetary", "L4": "Craft"}
    _QCUBE_CATS   = {"OA": "SMBH Pump", "OB": "Substrate Field",
                     "OC": "Boundary Layer", "OD": "Dimensional Gate",
                     "OE": "Crew Safety", "OF": "Navigation"}
    _QCUBE_CLASS  = {"\u03b1": "I-Massive", "\u03b2": "II-Residual",
                     "\u03b3": "III-Mid", "\u03b4": "IV-Decline",
                     "\u03b5": "V-Environ", "\u03b6": "VI-Barred"}

    # Lightweight auto-tag keywords (no PySide6 needed)
    _TAG_SCALE = {
        "L1": ["galaxy","galactic","chi2","batch","reverse","neutrino",
               "NGC","UGC","ESO","DDO","rms_newton","winner"],
        "L2": ["stellar","binary","tachocline","star","spectrum",
               "HR_1099","Spica","Alpha_Cen","Sirius"],
        "L3": ["planetary","planet","Saturn","hexagon","Jupiter",
               "Earth","Neptune","solar_system"],
        "L4": ["tunnel","probe","gate","transit","corridor",
               "flight","arrival","bootes","graveyard","brucetron",
               "chi_freeboard","kill","inspiral","craft"],
    }
    _TAG_CAT = {
        "OA": ["kappa","crag","neutrino","L_nu","nu_b","pump","eddington"],
        "OB": ["sigma","lambda","lam","alpha","memory","coherence",
               "wave","substrate","phase","cos_delta_phi","corr_full"],
        "OC": ["boundary","gradient","snap","torus","Jasper","phi_safety"],
        "OD": ["OpT","OpC","R_7D","R_9to10","STARGATE","gate","7D","9D"],
        "OE": ["guardian","chi","freeboard","brucetron","safety","crew"],
        "OF": ["probe","corridor","flight","navigator","arrival",
               "graveyard","tunnel","GO","NO-GO","zone"],
    }

    def _auto_tag_file(self, filepath):
        """Lightweight auto-tag from JSON filename + keys (including nested)."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return {"scale": "", "category": "", "class": ""}

        # Collect keys — including one level of nesting
        keys = set()
        if isinstance(data, list) and data:
            for entry in data[:5]:
                if isinstance(entry, dict):
                    keys.update(entry.keys())
        elif isinstance(data, dict):
            keys.update(data.keys())
            # Nested: check "results", "info", "config" etc.
            for v in data.values():
                if isinstance(v, dict):
                    keys.update(v.keys())
                elif isinstance(v, list) and v:
                    for item in v[:3]:
                        if isinstance(item, dict):
                            keys.update(item.keys())

        # Also collect string values (galaxy names, test types)
        vals = set()
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, str) and len(v) < 40:
                    vals.add(v)
            # Galaxy names from nested results
            for item in data.get("results", [])[:5]:
                if isinstance(item, dict):
                    g = item.get("galaxy", "")
                    if g:
                        vals.add(g)

        all_text = " ".join(keys) + " " + " ".join(vals) + " " + os.path.basename(filepath)
        text_lower = all_text.lower()

        # Score each tag
        def _best(tag_dict):
            scores = {k: sum(1 for kw in kws if kw.lower() in text_lower)
                      for k, kws in tag_dict.items()}
            return max(scores, key=scores.get) if any(scores.values()) else ""
        return {
            "scale": _best(self._TAG_SCALE),
            "category": _best(self._TAG_CAT),
            "class": "\u03b1",  # default — refine when galaxy detected
        }

    def _build_epic_tab(self, parent):
        """Tab 8 — EPIC Collector: persistent ingestion + Q-Cube coverage."""
        style_bg  = "#0a0c10"
        style_acc = "#9933ee"

        # ── Persistence: load saved ingestion state ──
        self._epic_ingested = {}       # {fname: {tags, ingested_at}}
        self._epic_qcube_positions = {} # {pos_key: [fnames]}
        self._epic_state_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "results", "_epic_ingestion_state.json")
        self._load_epic_state()

        # ── Header ──
        hf = tk.Frame(parent, bg=style_bg)
        hf.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(hf, text="EPIC COLLECTOR",
                 font=("Georgia", 16), fg=style_acc, bg=style_bg
                 ).pack(side="left")
        tk.Label(hf, text="Substrate Test Ingestion \u2014 Q-Cube Coverage",
                 font=("Consolas", 10), fg="#6a7a90", bg=style_bg
                 ).pack(side="left", padx=(16, 0))

        # ── Three-column PanedWindow ──
        pw = tk.PanedWindow(parent, orient="horizontal",
                            bg=style_bg, sashwidth=4,
                            sashrelief="flat")
        pw.pack(fill="both", expand=True, padx=12, pady=4)

        # ══ COLUMN 1: Source Pool (all JSON, date-sorted) ══
        col1 = tk.Frame(pw, bg=style_bg)
        pw.add(col1, width=340, minsize=220)

        c1h = tk.Frame(col1, bg=style_bg)
        c1h.pack(fill="x", padx=4, pady=(4, 2))
        tk.Label(c1h, text="SOURCE POOL",
                 font=("Consolas", 10, "bold"),
                 fg="#44ddff", bg=style_bg).pack(side="left")
        self._epic_count_var = tk.StringVar(value="")
        tk.Label(c1h, textvariable=self._epic_count_var,
                 font=("Consolas", 8), fg="#6a7a90",
                 bg=style_bg).pack(side="left", padx=6)
        tk.Button(c1h, text="Refresh", font=("Consolas", 8),
                  bg="#1a1e2a", fg="#a0b0cc", relief="flat",
                  command=self._refresh_epic_results
                  ).pack(side="right")

        self._epic_results_list = tk.Listbox(
            col1, bg="#0c0e14", fg="#44ddff",
            font=("Consolas", 8), relief="flat",
            selectbackground="#9933ee",
            selectforeground="#ffd700",
            activestyle="none")
        s1 = ttk.Scrollbar(col1, orient="vertical",
                           command=self._epic_results_list.yview)
        self._epic_results_list.configure(yscrollcommand=s1.set)
        s1.pack(side="right", fill="y")
        self._epic_results_list.pack(fill="both", expand=True,
                                      padx=4, pady=4)
        self._epic_results_list.bind(
            "<<ListboxSelect>>", self._on_epic_select)

        # Auto-tag + ingest buttons below source list
        tag_f = tk.Frame(col1, bg=style_bg)
        tag_f.pack(fill="x", padx=4, pady=2)
        self._epic_tag_var = tk.StringVar(value="Select file \u2192 auto-tag")
        tk.Label(tag_f, textvariable=self._epic_tag_var,
                 font=("Consolas", 9), fg="#cc88ff",
                 bg="#0c0e14", justify="left",
                 anchor="w").pack(fill="x", padx=2, pady=2)
        tk.Button(tag_f,
                  text="\u25B6  INGEST SELECTED \u2192",
                  font=("Consolas", 10, "bold"),
                  bg="#1a3020", fg="#40ee70",
                  activebackground="#2a4838",
                  relief="flat", pady=4,
                  command=self._ingest_selected
                  ).pack(fill="x", pady=2)

        # ══ COLUMN 2: Ingested (persistent, survives restart) ══
        col2 = tk.Frame(pw, bg=style_bg)
        pw.add(col2, width=340, minsize=220)

        c2h = tk.Frame(col2, bg=style_bg)
        c2h.pack(fill="x", padx=4, pady=(4, 2))
        self._epic_ingested_count = tk.StringVar(value="0 ingested")
        tk.Label(c2h, text="INGESTED",
                 font=("Consolas", 10, "bold"),
                 fg="#40ee70", bg=style_bg).pack(side="left")
        tk.Label(c2h, textvariable=self._epic_ingested_count,
                 font=("Consolas", 8), fg="#6a7a90",
                 bg=style_bg).pack(side="left", padx=6)

        self._epic_ingested_list = tk.Listbox(
            col2, bg="#0c0e14", fg="#40ee70",
            font=("Consolas", 8), relief="flat",
            selectbackground="#cc3333",
            selectforeground="#ffffff",
            activestyle="none")
        s2 = ttk.Scrollbar(col2, orient="vertical",
                           command=self._epic_ingested_list.yview)
        self._epic_ingested_list.configure(yscrollcommand=s2.set)
        s2.pack(side="right", fill="y")
        self._epic_ingested_list.pack(fill="both", expand=True,
                                       padx=4, pady=4)

        # Delete + rebuild buttons
        del_f = tk.Frame(col2, bg=style_bg)
        del_f.pack(fill="x", padx=4, pady=2)
        tk.Button(del_f,
                  text="\u2716  DELETE SELECTED",
                  font=("Consolas", 10),
                  bg="#2a1010", fg="#ff4444",
                  activebackground="#3a1818",
                  relief="flat", pady=4,
                  command=self._delete_ingested
                  ).pack(fill="x", pady=2)
        tk.Button(del_f,
                  text="\u21bb  REFRESH Q-CUBE",
                  font=("Consolas", 9),
                  bg="#1a1e2a", fg="#a0b0cc",
                  relief="flat", pady=3,
                  command=self._rebuild_qcube
                  ).pack(fill="x", pady=2)
        tk.Button(del_f,
                  text="\u2699  LAUNCH FULL COLLECTOR",
                  font=("Consolas", 9),
                  bg="#1a1030", fg="#cc88ff",
                  relief="flat", pady=3,
                  command=self._launch_epic_collector
                  ).pack(fill="x", pady=2)

        # ══ COLUMN 3: Q-Cube Coverage ══
        col3 = tk.Frame(pw, bg=style_bg)
        pw.add(col3, minsize=300)

        tk.Label(col3, text="Q-CUBE COVERAGE (144 positions)",
                 font=("Consolas", 10, "bold"),
                 fg="#44ddff", bg=style_bg
                 ).pack(fill="x", padx=4, pady=(4, 2))

        self._epic_coverage_text = tk.Text(
            col3, bg="#0c0e14", fg="#44ddff",
            font=("Consolas", 9), relief="flat",
            wrap="word")
        s3 = ttk.Scrollbar(col3, orient="vertical",
                           command=self._epic_coverage_text.yview)
        self._epic_coverage_text.configure(yscrollcommand=s3.set)
        s3.pack(side="right", fill="y")
        self._epic_coverage_text.pack(fill="both", expand=True,
                                       padx=4, pady=4)

        # ── EPIC Log (bottom) ──
        lf = ttk.LabelFrame(parent, text="EPIC LOG")
        lf.pack(fill="x", padx=12, pady=(0, 4))
        self._epic_log = tk.Text(
            lf, height=3, bg="#0c0e14", fg="#cc88ff",
            font=("Consolas", 9), relief="flat", wrap="word")
        self._epic_log.pack(fill="x", padx=4, pady=4)

        self._epic_log_msg("EPIC COLLECTOR ready. "
                           "Every test run is an interview "
                           "with the substrate.")
        self._epic_log_msg("\u2500" * 50)

        # ── Initial load ──
        self.root.after(500, self._refresh_epic_results)
        self.root.after(600, self._populate_ingested_list)
        self.root.after(700, self._update_coverage_display)

    # ── Persistence ──

    def _save_epic_state(self):
        """Save ingestion state to JSON for persistence."""
        try:
            os.makedirs(os.path.dirname(self._epic_state_path),
                        exist_ok=True)
            state = {
                "ingested": {k: v for k, v in
                             self._epic_ingested.items()},
                "qcube_positions": self._epic_qcube_positions,
            }
            with open(self._epic_state_path, 'w',
                       encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self._epic_log_msg(f"  Save error: {e}")

    def _load_epic_state(self):
        """Load ingestion state from JSON on startup."""
        if os.path.exists(self._epic_state_path):
            try:
                with open(self._epic_state_path, 'r',
                           encoding='utf-8') as f:
                    state = json.load(f)
                self._epic_ingested = state.get("ingested", {})
                self._epic_qcube_positions = state.get(
                    "qcube_positions", {})
            except Exception:
                self._epic_ingested = {}
                self._epic_qcube_positions = {}

    def _populate_ingested_list(self):
        """Fill ingested listbox from persistent state."""
        self._epic_ingested_list.delete(0, "end")
        for fname in sorted(self._epic_ingested.keys()):
            self._epic_ingested_list.insert("end", fname)
        self._epic_ingested_count.set(
            f"{len(self._epic_ingested)} ingested")

    # ── Core actions ──

    def _epic_log_msg(self, msg):
        """Write to EPIC tab log."""
        self._epic_log.insert("end", msg + "\n")
        self._epic_log.see("end")

    def _on_epic_select(self, event=None):
        """Auto-tag selected JSON file."""
        sel = self._epic_results_list.curselection()
        if not sel:
            return
        fname = self._epic_results_list.get(sel[0])
        root_dir = os.path.dirname(os.path.abspath(__file__))
        fpath = os.path.join(root_dir, "data", "results", fname)
        if not os.path.exists(fpath):
            self._epic_tag_var.set("File not found")
            return
        tags = self._auto_tag_file(fpath)
        s = tags.get("scale", "?")
        c = tags.get("category", "?")
        cl = tags.get("class", "?")
        status = "\u2713 INGESTED" if fname in self._epic_ingested else ""
        self._epic_tag_var.set(
            f"[{s}, {c}, {cl}] "
            f"{self._QCUBE_SCALES.get(s,'?')} | "
            f"{self._QCUBE_CATS.get(c,'?')} | "
            f"{self._QCUBE_CLASS.get(cl,'?')}  {status}")

    def _ingest_selected(self):
        """Ingest selected file — persistent."""
        sel = self._epic_results_list.curselection()
        if not sel:
            return
        fname = self._epic_results_list.get(sel[0])
        if fname in self._epic_ingested:
            self._epic_log_msg(f"  Already ingested: {fname}")
            return
        root_dir = os.path.dirname(os.path.abspath(__file__))
        fpath = os.path.join(root_dir, "data", "results", fname)
        if not os.path.exists(fpath):
            self._epic_log_msg(f"  ERROR: {fname} not found")
            return
        tags = self._auto_tag_file(fpath)
        pos_key = f"[{tags['scale']}, {tags['category']}, {tags['class']}]"
        self._epic_ingested[fname] = {
            "tags": tags,
            "pos_key": pos_key,
            "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if pos_key not in self._epic_qcube_positions:
            self._epic_qcube_positions[pos_key] = []
        self._epic_qcube_positions[pos_key].append(fname)
        self._save_epic_state()
        self._populate_ingested_list()
        self._on_epic_select()
        self._update_coverage_display()
        self._epic_log_msg(
            f"  INGESTED: {fname} \u2192 {pos_key}")

    def _delete_ingested(self):
        """Remove selected file from ingestion — persistent."""
        sel = self._epic_ingested_list.curselection()
        if not sel:
            return
        fname = self._epic_ingested_list.get(sel[0])
        if fname in self._epic_ingested:
            info = self._epic_ingested.pop(fname)
            pos_key = info.get("pos_key", "")
            if pos_key in self._epic_qcube_positions:
                flist = self._epic_qcube_positions[pos_key]
                if fname in flist:
                    flist.remove(fname)
                if not flist:
                    del self._epic_qcube_positions[pos_key]
            self._save_epic_state()
            self._populate_ingested_list()
            self._update_coverage_display()
            self._epic_log_msg(
                f"  DELETED: {fname} from {pos_key}")

    def _rebuild_qcube(self):
        """Rebuild Q-Cube positions from scratch using ingested files."""
        root_dir = os.path.dirname(os.path.abspath(__file__))
        self._epic_qcube_positions = {}
        removed = []
        for fname, info in list(self._epic_ingested.items()):
            fpath = os.path.join(root_dir, "data", "results", fname)
            if not os.path.exists(fpath):
                removed.append(fname)
                continue
            tags = self._auto_tag_file(fpath)
            pos_key = f"[{tags['scale']}, {tags['category']}, {tags['class']}]"
            info["tags"] = tags
            info["pos_key"] = pos_key
            if pos_key not in self._epic_qcube_positions:
                self._epic_qcube_positions[pos_key] = []
            self._epic_qcube_positions[pos_key].append(fname)
        for fname in removed:
            del self._epic_ingested[fname]
        self._save_epic_state()
        self._populate_ingested_list()
        self._update_coverage_display()
        self._epic_log_msg(
            f"  Q-CUBE REBUILT: {len(self._epic_ingested)} files, "
            f"{len(self._epic_qcube_positions)} positions"
            + (f" ({len(removed)} removed — file missing)"
               if removed else ""))

    def _launch_epic_collector(self):
        """Launch BCM_EPIC_OpT_test_collector.py as separate PySide6 process."""
        import subprocess
        root_dir = os.path.dirname(os.path.abspath(__file__))
        epic_dir = os.path.join(root_dir, "TITS_EPICt_BCM")
        script = os.path.join(epic_dir,
                              "BCM_EPIC_OpT_test_collector.py")
        if not os.path.exists(script):
            self._epic_log_msg(
                f"  ERROR: Collector not found")
            return
        self._epic_log_msg("  Launching EPIC Collector...")
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            subprocess.Popen([sys.executable, script],
                             cwd=epic_dir, env=env)
            self._epic_log_msg("  Collector launched.")
        except Exception as e:
            self._epic_log_msg(f"  LAUNCH ERROR: {e}")

    def _refresh_epic_results(self):
        """Scan data/results/ for JSON files, sorted by date (newest first)."""
        self._epic_results_list.delete(0, "end")
        root_dir = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(root_dir, "data", "results")
        if not os.path.isdir(results_dir):
            self._epic_count_var.set("not found")
            return
        json_files = [f for f in os.listdir(results_dir)
                      if f.endswith(".json")
                      and not f.startswith("_")]
        json_files.sort(
            key=lambda f: os.path.getmtime(
                os.path.join(results_dir, f)),
            reverse=True)
        self._epic_count_var.set(f"{len(json_files)}")
        for fname in json_files:
            self._epic_results_list.insert("end", fname)

    def _update_coverage_display(self):
        """Show Q-Cube coverage summary."""
        self._epic_coverage_text.delete("1.0", "end")
        total_possible = (len(self._QCUBE_SCALES) *
                          len(self._QCUBE_CATS) *
                          len(self._QCUBE_CLASS))
        filled = len(self._epic_qcube_positions)
        pct = (filled / total_possible * 100) if total_possible > 0 else 0

        lines = [
            f"COVERAGE: {filled} / {total_possible} positions "
            f"({pct:.1f}%)",
            f"INGESTED: {len(self._epic_ingested)} files",
            "",
            f"{'Scale':<12} {'Category':<18} {'Class':<12} {'Tests':>5}",
            "\u2500" * 50,
        ]

        # Show filled positions
        if self._epic_qcube_positions:
            for pos_key, files in sorted(
                    self._epic_qcube_positions.items()):
                lines.append(f"  {pos_key:<40} {len(files):>3}")
        else:
            lines.append("  (no positions filled yet)")
            lines.append("")
            lines.append("  Select a JSON result and click INGEST")
            lines.append("  to start building Q-Cube coverage.")

        # Show gap hints
        lines.append("")
        lines.append("\u2500" * 50)
        lines.append("CATEGORY COVERAGE:")
        for cat_key, cat_name in self._QCUBE_CATS.items():
            count = sum(1 for k in self._epic_qcube_positions
                        if cat_key in k)
            bar = "\u2588" * count + "\u2591" * (5 - min(count, 5))
            lines.append(f"  {cat_key} {cat_name:<18} {bar} {count}")

        self._epic_coverage_text.insert("1.0", "\n".join(lines))


if __name__ == "__main__":
    root = tk.Tk()
    app = SolverGUI(root)
    root.mainloop()
