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

        # ── Notebook — Tab 1: Galactic Solver / Tab 2: Planetary / Tab 3: Stellar ──
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=4)

        # Tab 1 — Galactic Solver
        tab1 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab1, text="  GALACTIC SOLVER  ")

        # Tab 2 — Planetary Analysis
        tab2 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab2, text="  PLANETARY  ")

        # Tab 3 — Stellar Tachocline Analysis
        tab3 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab3, text="  STELLAR  ")

        # Build planetary tab content
        self._build_planetary_tab(tab2)

        # Build stellar tab content
        self._build_stellar_tab(tab3)

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

    # ══════════════════════════════════════════════════════════════
    #  TAB 3 — STELLAR TACHOCLINE ANALYSIS
    # ══════════════════════════════════════════════════════════════

    def _build_stellar_tab(self, parent):
        """Tab 3 — BCM Stellar Tachocline Wave Solver (13 stars)."""
        style_bg  = "#0a0c10"
        style_fg  = "#a0b0cc"
        style_acc = "#ffbb44"

        # ── Header ──
        hf = tk.Frame(parent, bg=style_bg)
        hf.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(hf, text="BCM STELLAR WAVE SOLVER",
                 font=("Georgia", 16), fg="#d0d8e8", bg=style_bg).pack(side="left")
        tk.Label(hf, text="Tachocline Resonance Hamiltonian — Select Star or Batch Run",
                 font=("Consolas", 10), fg="#6a7a90", bg=style_bg).pack(side="left", padx=(16, 0))

        # ── File Tree ──
        tf = ttk.LabelFrame(parent, text="FILE LOCATIONS")
        tf.pack(fill="x", padx=12, pady=4)
        tree_text = (
            'SUBSTRATE_SOLVER/\n'
            '|   BCM_stellar_wave.py            <- stellar tachocline solver\n'
            '|   BCM_stellar_overrides.py        <- stellar parameter overrides\n'
            '|   BCM_stellar_renderer.py         <- publication figure renderer\n'
            '|   launcher.py                     <- this GUI\n'
            '|\n'
            '+---data/\n'
            '    +---results/\n'
            '            BCM_stellar_batch.json           <- 13-star batch output\n'
            '            BCM_stellar_m_comparison.png     <- Hamiltonian vs Rossby\n'
            '            BCM_stellar_gallery.png          <- all spectra\n'
            '            BCM_tachocline_gate.png          <- convective gate diagram\n'
            '            BCM_Sun_stellar_wave.json        <- individual star runs\n'
        )
        tree_box = tk.Text(tf, height=12, bg="#0c0e14", fg="#70a0c0",
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
            "Sun", "Tabby", "Betelgeuse", "Proxima", "AB_Dor",
            "V374_Peg", "Tau_Boo", "Alpha_Cen_A", "Alpha_Cen_B",
            "EV_Lac", "Vega", "Sirius_A", "61_Cyg_A"]
        star_menu = ttk.Combobox(sel_f, textvariable=self.star_select_var,
                                  values=star_names, width=16,
                                  font=("Consolas", 11), state="readonly")
        star_menu.pack(side="left", padx=(0, 8))
        star_menu.bind("<<ComboboxSelected>>", self._on_star_select)

        self.star_info_var = tk.StringVar(value="Sun — G2V  m=4  Class I")
        tk.Label(sel_f, textvariable=self.star_info_var,
                 font=("Consolas", 9), fg=style_acc,
                 bg="#12151c").pack(side="left")

        # ── Star Parameters (read-only display) ──
        pf = ttk.LabelFrame(parent, text="STAR PARAMETERS")
        pf.pack(fill="x", padx=12, pady=4)

        self.star_spectral  = tk.StringVar(value="G2V")
        self.star_mass      = tk.StringVar(value="1.0")
        self.star_rotation  = tk.StringVar(value="25.38")
        self.star_conv_frac = tk.StringVar(value="0.287")
        self.star_m_obs     = tk.StringVar(value="4")
        self.star_B_tach    = tk.StringVar(value="1.0e-1")

        params = [
            ("Spectral type:",              self.star_spectral),
            ("Mass (M_sun):",               self.star_mass),
            ("Rotation period (days):",     self.star_rotation),
            ("Conv depth fraction:",        self.star_conv_frac),
            ("m observed:",                 self.star_m_obs),
            ("B tachocline (T):",           self.star_B_tach),
        ]
        for i, (label, var) in enumerate(params):
            tk.Label(pf, text=label, font=("Consolas", 10),
                     fg=style_fg, bg="#12151c").grid(
                         row=i, column=0, sticky="w", padx=10, pady=2)
            ttk.Entry(pf, textvariable=var, width=16).grid(
                row=i, column=1, padx=6, pady=2)

        # ── Run Options ──
        rf = ttk.LabelFrame(parent, text="RUN OPTIONS")
        rf.pack(fill="x", padx=12, pady=4)
        self.stellar_batch     = tk.BooleanVar(value=False)
        self.stellar_solve_lam = tk.BooleanVar(value=True)
        ttk.Checkbutton(rf, text="Batch run all 13 stars",
                        variable=self.stellar_batch).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(rf, text="Back-calculate λ_stellar from observed m",
                        variable=self.stellar_solve_lam).pack(anchor="w", padx=10, pady=2)

        # ── Run & Render Buttons ──
        bf = ttk.Frame(parent, style="Dark.TFrame")
        bf.pack(fill="x", padx=12, pady=6)
        ttk.Button(bf, text="▶  RUN STELLAR SOLVER",
                   style="Run.TButton",
                   command=self._run_stellar).pack(fill="x", padx=4, pady=2)
        ttk.Button(bf, text="⬡  Render Spectrum (selected star)",
                   command=lambda: self._run_stellar_renderer("--star", self.star_select_var.get())).pack(fill="x", padx=4, pady=2)
        ttk.Button(bf, text="⬡  Render Gallery (all stars)",
                   command=lambda: self._run_stellar_renderer("--gallery")).pack(fill="x", padx=4, pady=2)
        ttk.Button(bf, text="⬡  Render Hamiltonian vs Rossby Comparison",
                   command=lambda: self._run_stellar_renderer("--m-compare")).pack(fill="x", padx=4, pady=2)
        ttk.Button(bf, text="⬡  Render All Publication Figures",
                   command=lambda: self._run_stellar_renderer("--all")).pack(fill="x", padx=4, pady=2)

        # ── Output Log ──
        lf = ttk.LabelFrame(parent, text="STELLAR LOG")
        lf.pack(fill="both", expand=True, padx=12, pady=4)
        self.stellar_log_widget = tk.Text(lf, height=12, bg="#0c0e14", fg="#c0d8e8",
                                          font=("Consolas", 10), relief="flat",
                                          insertbackground="#c0d8e8")
        ss = ttk.Scrollbar(lf, orient="vertical", command=self.stellar_log_widget.yview)
        self.stellar_log_widget.configure(yscrollcommand=ss.set)
        self.stellar_log_widget.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        ss.pack(side="right", fill="y")
        self.stellar_log_widget.insert("end",
            "BCM Stellar Wave Solver ready.\n"
            "Resonance Hamiltonian: H(m) = (c_s - Ω·R/m)²\n"
            "Tachocline gate: fully convective → m=1\n"
            "Output JSON → data/results/BCM_stellar_batch.json\n"
            "─" * 55 + "\n")
        self.stellar_log_widget.config(state="disabled")

    def _stellar_log(self, msg):
        """Write to stellar tab log."""
        self.stellar_log_widget.config(state="normal")
        self.stellar_log_widget.insert("end", msg + "\n")
        self.stellar_log_widget.see("end")
        self.stellar_log_widget.config(state="disabled")
        self.root.update_idletasks()

    def _load_stellar_registry(self):
        """Load stellar registry from BCM_stellar_wave.py STELLAR_REGISTRY."""
        try:
            from BCM_stellar_wave import STELLAR_REGISTRY
            self._stellar_registry = STELLAR_REGISTRY
        except ImportError:
            self._stellar_registry = {}

    def _on_star_select(self, event=None):
        """Load selected star parameters into the fields."""
        name = self.star_select_var.get()
        p = self._stellar_registry.get(name, {})
        if not p:
            return
        self.star_spectral.set(p.get("spectral_type", "?"))
        self.star_mass.set(str(p.get("mass_solar", "?")))
        self.star_rotation.set(str(p.get("rotation_days", "?")))
        self.star_conv_frac.set(str(p.get("conv_depth_frac", "?")))
        self.star_m_obs.set(str(p.get("m_observed", "?")))
        self.star_B_tach.set(f"{p.get('B_tachocline_T', 0):.2e}")
        cls = p.get("bcm_class", "")[:40]
        m   = p.get("m_observed", "?")
        sp  = p.get("spectral_type", "")
        self.star_info_var.set(f"{name} — {sp}  m={m}  {cls}")
        self._stellar_log(f"  Loaded: {name}  {sp}  m_obs={m}  "
                          f"P_rot={p.get('rotation_days','?')} d  "
                          f"conv_frac={p.get('conv_depth_frac','?')}")

    def _run_stellar(self):
        """Run BCM_stellar_wave.py as subprocess and stream output to log."""
        import subprocess

        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "BCM_stellar_wave.py")
        if not os.path.exists(script):
            self._stellar_log("ERROR: BCM_stellar_wave.py not found in root dir.")
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

        self._stellar_log(f"Running: {' '.join(args)}")
        self._stellar_log("─" * 55)

        def _run():
            try:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        text=True,
                                        cwd=os.path.dirname(os.path.abspath(__file__)))
                for line in proc.stdout:
                    self.root.after(0, lambda l=line.rstrip(): self._stellar_log(l))
                proc.wait()
                self.root.after(0, lambda: self._stellar_log(
                    "─" * 55 + "\nDone. Check data/results/ for JSON and PNG output."))
            except Exception as e:
                self.root.after(0, lambda: self._stellar_log(f"ERROR: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _run_stellar_renderer(self, *renderer_args):
        """Run BCM_stellar_renderer.py with given args and stream output to log."""
        import subprocess

        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "BCM_stellar_renderer.py")
        if not os.path.exists(script):
            self._stellar_log("ERROR: BCM_stellar_renderer.py not found in root dir.")
            return

        args = [sys.executable, script] + list(renderer_args)

        self._stellar_log(f"Rendering: {' '.join(args)}")
        self._stellar_log("─" * 55)

        def _run():
            try:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        text=True,
                                        cwd=os.path.dirname(os.path.abspath(__file__)))
                for line in proc.stdout:
                    self.root.after(0, lambda l=line.rstrip(): self._stellar_log(l))
                proc.wait()
                self.root.after(0, lambda: self._stellar_log(
                    "─" * 55 + "\nRenderer done. PNGs saved to data/results/"))
            except Exception as e:
                self.root.after(0, lambda: self._stellar_log(f"ERROR: {e}"))

        threading.Thread(target=_run, daemon=True).start()

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

            # ── Apply BCM structural override ──
            from BCM_Substrate_overrides import apply_galaxy_override
            J, extra_params, applied = apply_galaxy_override(
                name, J_default, grid, vmax_kms=vmax, verbose=True)

            cls = self._bcm_galaxies.get(name, {}).get("class", "?")
            self.log(f"  [BCM] {name} Class {cls} — override={'YES' if applied else 'NO'}")

            run_lam = extra_params.get("lam", lam)

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

if __name__ == "__main__":
    root = tk.Tk()
    app = SolverGUI(root)
    root.mainloop()
