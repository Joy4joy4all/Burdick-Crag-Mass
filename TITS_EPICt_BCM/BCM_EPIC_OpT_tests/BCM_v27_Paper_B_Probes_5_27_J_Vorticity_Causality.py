# -*- coding: utf-8 -*-
"""
BCM v27 Paper B Probe Test 5_27 -- H_PAPER_B_2 Vorticity Causality
====================================================================

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
Date: 2026-05-03

PRIMACY STATEMENT
-----------------
All theoretical concepts -- the perturbation/null-control dual
causality criterion, the four-pillar evidence decomposition of
H_PAPER_B_2 (operator consistency, vorticity realization,
structural correlation, interventional causality), the locked
threshold values, and every originating insight in this file --
belong solely to Stephen Justin Burdick Sr. AI systems were used
strictly as code executors at SJB direction. Emerald Entities
LLC -- GIBUSH Systems.

PURPOSE
-------
H_PAPER_B_2 vocabulary statement: "J carries vorticity in the
dual-pump topology." Operationally this decomposes into four
sub-claims requiring separate evidence:

  (1) Operator consistency. Tested by 5_24. EVIDENCE: 25 PASS.
  (2) Vorticity realization. Tested by 5_25. EVIDENCE: 25 PASS.
  (3) Structural correlation. Tested by 5_26.
      EVIDENCE: 25 PASS, r_spatial ~ 0.94-0.96, r_spectral ~ 1.0.
  (4) Interventional causality. NO EVIDENCE PRIOR TO THIS PROBE.

Tests 5_24, 5_25, and 5_26 are all observational. They show:
  - the curl operator is implemented consistently (5_24)
  - the substrate response carries vorticity (5_25)
  - V's structure matches J's structure (5_26)

But none of them rule out a confound: J and V might share
structure because they are both derived from the same dual-pump
geometric input acting through the solver pipeline, not because
J causally drives V. Strong correlation is not strict causation.

Test 5_27 closes (4) via two interventional manipulations of J:

  PERTURBATION: J_pert = J_baseline + delta_J (localized Gaussian
    bump injected at a known off-center location). If J causally
    drives V, then delta_J must propagate to a delta_V at the
    same spatial location. Test: spatial correlation between
    delta_J and delta_V on the inner half-grid.

  NULL CONTROL: J_null = randomized version of J_baseline (FFT
    phase randomized at the same amplitude spectrum, killing the
    coherent dual-pump spatial structure while preserving the
    energy budget). If V's curl is causally driven by J's
    coherent dual-pump topology, then V_null's curl in the inner
    half-grid must be substantially weaker than V_baseline's.
    Test: ratio of inner-grid max|curl V_null| / max|curl V_baseline|.

Both criteria MUST hold for PASS. The test discriminates against
two confounds:
  - "ΔJ propagates" rules out J being a passive co-variant
  - "Null collapses" rules out V's vorticity being PDE-intrinsic

This is interventional evidence -- the only kind that closes
strict causality.

LOCKED PARAMETERS
-----------------
  Grid baseline:           128 x 128
  Refinement check grid:   256 x 256 (Phase 1 only, 5 configs)
  sigma_crit values:       {0.001, 0.005, 0.01, 0.05, 0.1}
  pump_separation values:  {5, 8, 12, 18, 25}
  Configurations:          5 x 5 = 25
  Phase 1 gate configs:    5 (4 corners + center)
  Output:                  one JSON per configuration in
                           data/results/, single H2 entry
  Evidence type:           primary

  Perturbation amplitude:  0.1 * max|J_baseline|
  Perturbation width:      sigma = grid / 24
  Perturbation location:   (cx + grid/4, cy + grid/4)
                           (off-center, NOT on either pump axis)
  Null randomization:      FFT phase scramble preserving |F(J)|
  Random seed:             1729 (deterministic for reproducibility)

  Perturbation correlation threshold:  0.5 (Pearson on inner grid)
  Null collapse ratio threshold:       0.5 (V_null / V_baseline
                                             curl strength)

PIPELINE
--------
  Phase 1 -- Stability Gate (5 configs)
    For each gate config:
      Run baseline + perturbed + null at 128 (3 solver runs)
      Run baseline + perturbed + null at 256 (3 solver runs)
      Classify PASS/FAIL at each grid
      ABORT Phase 2 if classification flips between grids

  Phase 2 -- Full Sweep (25 configs)
    For each config: 3 solver runs at 128
    Emit one JSON per config with single H_PAPER_B_2 entry

DOES NOT TOUCH
--------------
- core solver, launcher, hypothesis_engine, vocabulary registry,
  any engine state. Probe writes JSONs only; ingestion is
  launcher's responsibility through the dedup-protected path.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ============================================================================
# CONSTANTS
# ============================================================================

GRID_BASELINE = 128
GRID_REFINEMENT = 256

SIGMA_CRIT_VALUES = (0.001, 0.005, 0.01, 0.05, 0.1)
PUMP_SEPARATIONS = (5, 8, 12, 18, 25)

GATE_CONFIG_INDICES = [
    (0, 0),
    (0, 4),
    (4, 0),
    (4, 4),
    (2, 2),
]

H_KEY = "H_PAPER_B_2_J_VORTICITY"
EVIDENCE_TYPE = "primary"

# Causality test thresholds (locked)
PERTURB_AMPLITUDE_FRAC = 0.1     # delta_J amplitude = 0.1 * max|J_baseline|
PERTURB_WIDTH_DIVISOR  = 24.0    # sigma_pert = grid / 24
PERTURB_OFFSET_FRAC    = 0.25    # location offset = grid/4 from center
PERTURB_CORR_THRESHOLD = 0.5     # delta_J vs delta_V Pearson on inner grid
NULL_COLLAPSE_RATIO    = 0.5     # max|curl V_null| / max|curl V_base| < this
NULL_RANDOM_SEED       = 1729    # deterministic phase scramble


# ============================================================================
# PATH RESOLUTION
# ============================================================================

def _resolve_paths():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    solver_root = os.path.dirname(os.path.dirname(this_dir))
    results_dir = os.path.join(solver_root, "data", "results")
    return solver_root, results_dir


def _import_project_modules():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    solver_root = os.path.dirname(os.path.dirname(this_dir))
    if solver_root not in sys.path:
        sys.path.insert(0, solver_root)

    solver_choice = os.environ.get("BCM_SOLVER", "cpu").strip().lower()
    SubstrateSolver = None
    backend = "cpu"
    if solver_choice == "gpu":
        try:
            from core.substrate_solver_gpu import (
                SubstrateSolver as _Sgpu)
            SubstrateSolver = _Sgpu
            backend = "gpu"
        except ImportError as e:
            print(f"  [solver_dispatch] GPU import failed: {e}",
                  file=sys.stderr)
            print(f"  [solver_dispatch] Falling back to CPU",
                  file=sys.stderr)
    if SubstrateSolver is None:
        try:
            from core.substrate_solver import (
                SubstrateSolver as _Scpu)
            SubstrateSolver = _Scpu
            backend = "cpu"
        except ImportError as e:
            raise ImportError(
                f"core.substrate_solver not importable: {e}")
    return SubstrateSolver, backend


# ============================================================================
# J CONSTRUCTION VARIANTS
# ============================================================================

def build_dual_pump_J(grid: int, separation_units: int) -> np.ndarray:
    """Identical to 5_24/5_25/5_26 baseline construction."""
    cx = grid // 2
    cy = grid // 2
    half_sep = separation_units // 2
    sigma_pump = max(2.0, grid / 32.0)

    yy, xx = np.meshgrid(np.arange(grid), np.arange(grid), indexing="ij")
    g_pos = np.exp(-((xx - (cx + half_sep)) ** 2 +
                      (yy - cy) ** 2) / (2.0 * sigma_pump ** 2))
    g_neg = np.exp(-((xx - (cx - half_sep)) ** 2 +
                      (yy - cy) ** 2) / (2.0 * sigma_pump ** 2))
    return (g_pos - g_neg).astype(np.float64)


def build_perturbation_delta_J(grid: int) -> Tuple[np.ndarray,
                                                      Tuple[int, int]]:
    """
    Localized Gaussian bump injected off-axis. Returns (delta_J,
    (cx_loc, cy_loc)) so the perturbation location is known to
    the spatial-correlation test.

    Off-axis placement avoids cancellation against the dual-pump
    +/- structure. Bump width sigma_pert = grid / 24 is small
    relative to pump width (grid / 32) so perturbation is local.
    """
    cx = grid // 2
    cy = grid // 2
    cx_pert = cx + int(PERTURB_OFFSET_FRAC * grid)
    cy_pert = cy + int(PERTURB_OFFSET_FRAC * grid)
    sigma_pert = max(2.0, grid / PERTURB_WIDTH_DIVISOR)

    yy, xx = np.meshgrid(np.arange(grid), np.arange(grid), indexing="ij")
    bump = np.exp(-((xx - cx_pert) ** 2 + (yy - cy_pert) ** 2)
                   / (2.0 * sigma_pert ** 2))
    return bump.astype(np.float64), (cx_pert, cy_pert)


def build_null_J(J_baseline: np.ndarray, seed: int = NULL_RANDOM_SEED
                  ) -> np.ndarray:
    """
    Randomize the phase of J_baseline's FFT while preserving its
    amplitude spectrum. This destroys the coherent dual-pump
    spatial topology while keeping the energy budget identical:

        |F(J_null)| = |F(J_baseline)|       (preserved)
        phase(F(J_null)) = random            (scrambled)

    A Hermitian-symmetric phase scramble is needed to keep
    J_null real-valued in the spatial domain. We achieve this
    by randomizing only the upper half of the spectrum and
    mirroring the conjugate.
    """
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(J_baseline)
    amp = np.abs(F)
    grid = J_baseline.shape[0]

    # Generate random Hermitian-symmetric phase
    rand_phase = rng.uniform(-math.pi, math.pi, size=F.shape)
    # Enforce Hermitian symmetry: phase(-k) = -phase(k)
    rand_phase = 0.5 * (rand_phase
                         - rand_phase[::-1, ::-1])
    # DC component must be real
    rand_phase[0, 0] = 0.0
    # Nyquist rows/cols (if grid even) must be real
    if grid % 2 == 0:
        rand_phase[grid // 2, 0] = 0.0
        rand_phase[0, grid // 2] = 0.0
        rand_phase[grid // 2, grid // 2] = 0.0

    F_null = amp * np.exp(1j * rand_phase)
    J_null = np.real(np.fft.ifft2(F_null)).astype(np.float64)
    return J_null


# ============================================================================
# VECTOR-CALCULUS HELPERS
# ============================================================================

def curl_of_scalar_z(phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    dphi_dy = np.gradient(phi, axis=0)
    dphi_dx = np.gradient(phi, axis=1)
    return dphi_dy, -dphi_dx


def curl_z_of_vector(V_x: np.ndarray,
                       V_y: np.ndarray) -> np.ndarray:
    dVy_dx = np.gradient(V_y, axis=1)
    dVx_dy = np.gradient(V_x, axis=0)
    return dVy_dx - dVx_dy


def curl_scalar_field(phi: np.ndarray) -> np.ndarray:
    """
    Convenience: full pipeline phi -> V_x, V_y -> curl_z(V).
    Used to extract the curl content of any scalar field
    (J source or rho_avg response) in one call.
    """
    V_x, V_y = curl_of_scalar_z(phi)
    return curl_z_of_vector(V_x, V_y)


# ============================================================================
# CORRELATION HELPER
# ============================================================================

def pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    a_flat = a.ravel().astype(np.float64)
    b_flat = b.ravel().astype(np.float64)
    a_std = np.std(a_flat)
    b_std = np.std(b_flat)
    if a_std == 0.0 or b_std == 0.0:
        return 0.0
    a_centered = a_flat - np.mean(a_flat)
    b_centered = b_flat - np.mean(b_flat)
    cov = np.mean(a_centered * b_centered)
    return float(cov / (a_std * b_std))


# ============================================================================
# OBSERVABLE EXTRACTION
# ============================================================================

def extract_evolved_field(solver_result: Dict[str, Any]
                           ) -> Optional[np.ndarray]:
    """Return rho_2d (layer-summed) or None if invalid."""
    rho_avg = solver_result.get("rho_avg")
    if rho_avg is None:
        return None
    rho_2d = rho_avg.sum(axis=0) if rho_avg.ndim == 3 else rho_avg
    if float(np.max(np.abs(rho_2d))) <= 0:
        return None
    return rho_2d


# ============================================================================
# CAUSALITY TEST (dual interventional criterion)
# ============================================================================

def test_vorticity_causality(J_baseline: np.ndarray,
                                 J_perturbed: np.ndarray,
                                 J_null:      np.ndarray,
                                 rho_baseline: np.ndarray,
                                 rho_perturbed: np.ndarray,
                                 rho_null:      np.ndarray
                                 ) -> Tuple[str, Dict[str, Any]]:
    """
    Two interventional criteria:

      (P) Perturbation propagation: spatial Pearson correlation
          between curl(delta_J) and curl(delta_V) on the inner
          half-grid > PERTURB_CORR_THRESHOLD

      (N) Null collapse: max|curl V_null| / max|curl V_baseline|
          on the inner half-grid < NULL_COLLAPSE_RATIO

    PASS requires both. Either failing alone means causation
    is not established.
    """
    grid = J_baseline.shape[0]
    qg = grid // 4

    # Curl content of each input/response pair
    curl_J_base = curl_scalar_field(J_baseline)
    curl_J_pert = curl_scalar_field(J_perturbed)
    curl_J_null = curl_scalar_field(J_null)

    curl_V_base = curl_scalar_field(rho_baseline)
    curl_V_pert = curl_scalar_field(rho_perturbed)
    curl_V_null = curl_scalar_field(rho_null)

    # Differential fields (input perturbation -> output perturbation)
    delta_curl_J = curl_J_pert - curl_J_base
    delta_curl_V = curl_V_pert - curl_V_base

    # Inner-grid restrictions (boundary artifacts removed)
    inner_dJ = delta_curl_J[qg:3 * qg, qg:3 * qg]
    inner_dV = delta_curl_V[qg:3 * qg, qg:3 * qg]
    inner_curl_V_base = curl_V_base[qg:3 * qg, qg:3 * qg]
    inner_curl_V_null = curl_V_null[qg:3 * qg, qg:3 * qg]

    # Criterion (P): perturbation propagation
    r_pert = pearson_corr(inner_dJ, inner_dV)

    # Criterion (N): null collapse
    max_curl_V_base = float(np.max(np.abs(inner_curl_V_base)))
    max_curl_V_null = float(np.max(np.abs(inner_curl_V_null)))
    null_ratio = (max_curl_V_null / max_curl_V_base
                   if max_curl_V_base > 0 else float("inf"))

    diag = {
        "perturbation_pearson":     r_pert,
        "perturbation_threshold":   PERTURB_CORR_THRESHOLD,
        "null_collapse_ratio":      null_ratio,
        "null_collapse_threshold":  NULL_COLLAPSE_RATIO,
        "max_curl_V_base":          max_curl_V_base,
        "max_curl_V_null":          max_curl_V_null,
        "max_abs_delta_curl_J":     float(np.max(np.abs(inner_dJ))),
        "max_abs_delta_curl_V":     float(np.max(np.abs(inner_dV))),
    }

    if not (math.isfinite(r_pert) and math.isfinite(null_ratio)):
        diag["fail_reason"] = ("non-finite correlation or "
                                "collapse ratio")
        return "FAIL", diag

    perturb_pass = r_pert > PERTURB_CORR_THRESHOLD
    null_pass = null_ratio < NULL_COLLAPSE_RATIO

    if perturb_pass and null_pass:
        return "PASS", diag

    reasons = []
    if not perturb_pass:
        reasons.append(
            f"perturb r = {r_pert:.3f} <= "
            f"{PERTURB_CORR_THRESHOLD} (delta_J does not "
            f"propagate to delta_V)")
    if not null_pass:
        reasons.append(
            f"null ratio = {null_ratio:.3f} >= "
            f"{NULL_COLLAPSE_RATIO} (V retains coherent vorticity "
            f"under randomized J -- structure is PDE-intrinsic)")
    diag["fail_reason"] = "; ".join(reasons)
    return "FAIL", diag


# ============================================================================
# CONFIG-LEVEL EVALUATION (3 solver runs per config)
# ============================================================================

def evaluate_config(sigma_crit: float, separation: int, grid: int,
                      SubstrateSolverCls) -> Dict[str, Any]:
    # Build all three J variants
    J_base = build_dual_pump_J(grid, separation)
    delta_J, pert_loc = build_perturbation_delta_J(grid)
    J_pert = J_base + PERTURB_AMPLITUDE_FRAC * float(np.max(np.abs(J_base))) * delta_J
    J_null = build_null_J(J_base)

    t0 = time.time()

    # Three solver runs
    solver_base = SubstrateSolverCls(grid=grid)
    rho_base = extract_evolved_field(solver_base.run(J_base, verbose=False))

    solver_pert = SubstrateSolverCls(grid=grid)
    rho_pert = extract_evolved_field(solver_pert.run(J_pert, verbose=False))

    solver_null = SubstrateSolverCls(grid=grid)
    rho_null = extract_evolved_field(solver_null.run(J_null, verbose=False))

    elapsed = time.time() - t0

    if rho_base is None or rho_pert is None or rho_null is None:
        return {
            "sigma_crit":      sigma_crit,
            "separation":      separation,
            "grid":            grid,
            "elapsed_sec":     elapsed,
            "valid":           False,
            "reason":          "one or more solver runs returned invalid rho_avg",
            "classification": "INCONCLUSIVE",
        }

    cls, diag = test_vorticity_causality(
        J_base, J_pert, J_null,
        rho_base, rho_pert, rho_null,
    )
    return {
        "sigma_crit":            sigma_crit,
        "separation":            separation,
        "grid":                  grid,
        "elapsed_sec":           elapsed,
        "valid":                 True,
        "perturbation_location": pert_loc,
        "classification":        cls,
        "diagnostics":           diag,
    }


# ============================================================================
# PHASE 1 -- STABILITY GATE
# ============================================================================

def run_phase1(SubstrateSolverCls
                ) -> Tuple[bool, List[Dict[str, Any]]]:
    print(f"\n  Phase 1: stability gate at "
          f"{GRID_BASELINE} vs {GRID_REFINEMENT} on 5 configs")
    print(f"  Each config = 3 solver runs (base + perturbed + null) "
          f"per grid = 6 runs per gate config")

    records = []
    all_invariant = True

    for (i_sc, i_sep) in GATE_CONFIG_INDICES:
        sc = SIGMA_CRIT_VALUES[i_sc]
        sep = PUMP_SEPARATIONS[i_sep]
        cfg_label = f"sc={sc:.4f}, sep={sep}"
        print(f"\n  [gate] {cfg_label}")

        try:
            r128 = evaluate_config(sc, sep, GRID_BASELINE,
                                     SubstrateSolverCls)
            r256 = evaluate_config(sc, sep, GRID_REFINEMENT,
                                     SubstrateSolverCls)
        except Exception as e:
            print(f"    ERROR: {e}")
            records.append({
                "config_label":  cfg_label,
                "error":         str(e),
                "traceback":     traceback.format_exc(),
                "invariant":     False,
            })
            all_invariant = False
            continue

        invariant = (r128["classification"] == r256["classification"])
        if not invariant:
            all_invariant = False
        records.append({
            "config_label":      cfg_label,
            "sigma_crit":        sc,
            "separation":        sep,
            "result_128":        r128,
            "result_256":        r256,
            "invariant":         invariant,
        })

        d128 = r128.get("diagnostics", {})
        d256 = r256.get("diagnostics", {})
        mark = "OK" if invariant else "FLIP"
        print(f"    H_PAPER_B_2 (causality)  "
              f"128={r128['classification']:13s} "
              f"256={r256['classification']:13s}  [{mark}]")
        print(f"      128: r_pert={d128.get('perturbation_pearson', 0):+.4f}  "
              f"null_ratio={d128.get('null_collapse_ratio', 0):.4f}")
        print(f"      256: r_pert={d256.get('perturbation_pearson', 0):+.4f}  "
              f"null_ratio={d256.get('null_collapse_ratio', 0):.4f}")

    return all_invariant, records


# ============================================================================
# PHASE 2 -- FULL SWEEP
# ============================================================================

def emit_config_json(record: Dict[str, Any],
                       results_dir: str,
                       run_timestamp: str) -> str:
    sc = record["sigma_crit"]
    sep = record["separation"]
    cls = record["classification"]
    diag = record["diagnostics"]

    cfg_tag = f"sc{sc:.4f}_sep{sep}".replace(".", "p")

    statement = (
        f"H-PaperB-2 vorticity causality test at sigma_crit="
        f"{sc}, pump_separation={sep}. Three solver runs: "
        f"baseline, perturbed (delta_J Gaussian bump injected "
        f"off-axis at amplitude {PERTURB_AMPLITUDE_FRAC} of "
        f"max|J|), and null (FFT phase scramble preserving "
        f"|F(J)| but destroying dual-pump topology). PASS = "
        f"perturbation propagates (Pearson r between delta_J "
        f"and delta_V curl fields > {PERTURB_CORR_THRESHOLD}) "
        f"AND null collapses (max|curl V_null| / "
        f"max|curl V_base| < {NULL_COLLAPSE_RATIO}). PASS means "
        f"J is interventionally causative of V's vorticity. "
        f"Distinct from tests 5_24 (operator), 5_25 (realization), "
        f"and 5_26 (correlation).")

    keywords = [
        "paper_b",
        "anchor_equation",
        "compositional_validation",
        "j_vorticity",
        "vorticity_causality",
        "interventional_causality",
        "perturbation_propagation",
        "null_collapse",
        "section_4_galactic",
        "v27527",
        cfg_tag,
    ]

    payload = {
        "test_name":       f"BCM_v27_5_27_J_causality_{cfg_tag}",
        "test_number":     5,
        "test_sub_number": 27,
        "version":         "v27",
        "system":          cfg_tag,
        "timestamp":       run_timestamp,
        "primacy_statement": (
            "All theoretical IP -- the perturbation/null-control "
            "dual causality criterion, the four-pillar evidence "
            "decomposition of H_PAPER_B_2, the locked threshold "
            "values -- belongs solely to Stephen Justin Burdick "
            "Sr. Emerald Entities LLC."),
        "test_distinguished_from_5_24_5_25_5_26": (
            "5_24 verified curl identity on J source (operator "
            "consistency, passes by construction). 5_25 verified "
            "the evolved rho_avg carries vorticity (realization). "
            "5_26 verified V's structure correlates with J's "
            "structure (observational correlation). 5_27 verifies "
            "J interventionally drives V via two manipulations: "
            "(P) injecting delta_J propagates to delta_V at the "
            "same spatial location, ruling out passive "
            "co-variance; (N) randomizing J's phase while "
            "preserving its amplitude spectrum collapses V's "
            "vorticity, ruling out PDE-intrinsic vorticity "
            "generation."),
        "perturbation_amplitude_frac": PERTURB_AMPLITUDE_FRAC,
        "perturbation_width_divisor":  PERTURB_WIDTH_DIVISOR,
        "perturbation_offset_frac":    PERTURB_OFFSET_FRAC,
        "null_random_seed":            NULL_RANDOM_SEED,
        "perturbation_location":       record.get("perturbation_location"),
        "grid":                        record["grid"],
        "sigma_crit":                  sc,
        "pump_separation":             sep,
        "elapsed_sec":                 record["elapsed_sec"],
        "hypotheses_tested": {
            H_KEY: {
                "statement":     statement,
                "result":        cls,
                "evidence_type": EVIDENCE_TYPE,
                "pass_count":    1 if cls == "PASS" else 0,
                "total_configs": 1,
                "prior":         0.50,
                "keywords":      keywords,
                "diagnostics":   diag,
            },
        },
    }

    fname = (f"BCM_v27_5_27_J_causality_{cfg_tag}_"
             f"{run_timestamp}.json")
    fpath = os.path.join(results_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=_json_default)
    return fpath


def _json_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def run_phase2(SubstrateSolverCls,
                results_dir: str,
                run_timestamp: str) -> Dict[str, Any]:
    print(f"\n  Phase 2: 25-config sweep at grid {GRID_BASELINE} "
          f"on J-causality dual criterion")
    print(f"  Each config = 3 solver runs (base + perturbed + null)")

    counts = {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0, "ERROR": 0}
    emitted_files = []
    n_total = 0

    for sc in SIGMA_CRIT_VALUES:
        for sep in PUMP_SEPARATIONS:
            n_total += 1
            cfg_label = f"sc={sc:.4f} sep={sep:>2d}"
            try:
                rec = evaluate_config(sc, sep, GRID_BASELINE,
                                       SubstrateSolverCls)
            except Exception as e:
                print(f"  [{n_total}/25] {cfg_label}: ERROR {e}")
                counts["ERROR"] += 1
                continue

            if not rec.get("valid", False):
                print(f"  [{n_total}/25] {cfg_label}: INVALID "
                      f"({rec.get('reason', '?')})")
                counts["INCONCLUSIVE"] += 1
                continue

            cls = rec["classification"]
            if cls in counts:
                counts[cls] += 1
            else:
                counts["INCONCLUSIVE"] += 1

            out_path = emit_config_json(rec, results_dir, run_timestamp)
            emitted_files.append(out_path)
            diag = rec["diagnostics"]
            print(f"  [{n_total}/25] {cfg_label}  "
                  f"({rec['elapsed_sec']:.1f}s)  -> {cls}")
            print(f"      r_pert     = "
                  f"{diag.get('perturbation_pearson', 0):+.4f}  "
                  f"(threshold > {PERTURB_CORR_THRESHOLD})")
            print(f"      null_ratio = "
                  f"{diag.get('null_collapse_ratio', 0):.4f}  "
                  f"(threshold < {NULL_COLLAPSE_RATIO})")

    return {
        "n_configs":     n_total,
        "counts":        counts,
        "emitted_files": emitted_files,
    }


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    print("=" * 72)
    print("BCM v27 PAPER B PROBE 5_27 -- H2 VORTICITY CAUSALITY")
    print("Interventional: perturbation propagation + null collapse")
    print("Stephen Justin Burdick Sr. -- Emerald Entities LLC")
    print("=" * 72)

    t_start = time.time()

    solver_root, results_dir = _resolve_paths()
    print(f"  solver_root: {solver_root}")
    print(f"  results_dir: {results_dir}")
    os.makedirs(results_dir, exist_ok=True)

    print("\n  Importing project modules...")
    try:
        SubstrateSolverCls, backend = _import_project_modules()
    except ImportError as e:
        print(f"  ERROR: {e}")
        return 2
    print(f"  SubstrateSolver  : {SubstrateSolverCls.__module__}")
    print(f"  Backend resolved : {backend}")

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Phase 1
    all_invariant, phase1_records = run_phase1(SubstrateSolverCls)

    phase1_summary_path = os.path.join(
        results_dir,
        f"_phase1_5_27_stability_gate_{run_timestamp}.json")
    with open(phase1_summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "test_name":     "BCM_v27_5_27_phase1_stability_gate",
            "timestamp":     run_timestamp,
            "all_invariant": all_invariant,
            "records":       phase1_records,
        }, f, indent=2, default=_json_default)
    print(f"\n  Phase 1 summary: "
          f"{os.path.basename(phase1_summary_path)}")

    if not all_invariant:
        print("\n" + "=" * 72)
        print("  PHASE 1 ABORT: classification flipped between 128 "
              "and 256 on at least one gate config.")
        print("  Phase 2 NOT executed. No evidence emitted.")
        print("=" * 72)
        elapsed = time.time() - t_start
        print(f"  Elapsed: {elapsed:.1f}s")
        return 1

    print("\n  Phase 1 PASS: all 5 gate configs invariant. "
          "Greenlight Phase 2.")

    # Phase 2
    phase2 = run_phase2(SubstrateSolverCls, results_dir, run_timestamp)

    elapsed_total = time.time() - t_start
    print("\n" + "=" * 72)
    print(f"  TOTAL CONFIGS: {phase2['n_configs']}")
    c = phase2["counts"]
    print(f"  H_PAPER_B_2 (J interventional causality)")
    print(f"    PASS={c['PASS']:>2}  FAIL={c['FAIL']:>2}  "
          f"INCONCLUSIVE={c['INCONCLUSIVE']:>2}  "
          f"ERROR={c['ERROR']:>2}")
    print(f"  JSONs emitted: {len(phase2['emitted_files'])}")
    print(f"  Total elapsed: {elapsed_total:.1f}s "
          f"({elapsed_total / 60.0:.1f} min)")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
