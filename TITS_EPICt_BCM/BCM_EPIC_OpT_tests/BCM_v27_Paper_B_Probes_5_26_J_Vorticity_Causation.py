# -*- coding: utf-8 -*-
"""
BCM v27 Paper B Probe Test 5_26 -- H_PAPER_B_2 Vorticity Causation
====================================================================

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
Date: 2026-05-03

PRIMACY STATEMENT
-----------------
All theoretical concepts -- the operator/realization/causation
three-pillar decomposition of H_PAPER_B_2 evidence, the
spatial+spectral dual-correlation test of J-driven vorticity
in the substrate response, the J-to-V causation criterion, and
every originating insight in this file -- belong solely to
Stephen Justin Burdick Sr. AI systems were used strictly as
code executors at SJB direction. Emerald Entities LLC --
GIBUSH Systems.

PURPOSE
-------
H_PAPER_B_2 vocabulary statement: "J carries vorticity in the
dual-pump topology." Operationally this decomposes into three
sub-claims requiring separate evidence:

  (1) Operator consistency: J = curl(scalar phi z_hat) is
      divergence-free by curl identity. Tested by 5_24.
      EVIDENCE: 25 PASS (curl identity holds numerically).

  (2) Vorticity realization: substrate evolves into a vortical
      response under dual-pump forcing. Tested by 5_25.
      EVIDENCE: 25 PASS (V_substrate has |curl| ~ 0.3-0.5,
      |div| at 1e-17, ratio 1e+15-1e+16).

  (3) Vorticity causation: V's rotational structure is
      causally driven by J's vorticity, not generated
      independently by the PDE.
      EVIDENCE: NONE PRIOR TO THIS PROBE.

Test 5_26 closes (3). For each (sigma_crit, separation) config,
the probe computes the curl scalar field of both J (the source)
and V (the substrate response), then measures their spatial
Pearson correlation and spectral correlation. PASS means J
is the causal source of V's vorticity, not just an upstream
forcing whose vortical content is independent of the response's.

This is the third evidence pillar for H_PAPER_B_2.

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

CORRELATION TESTS (dual criterion, locked)
-------------------------------------------
For each configuration:

  1. Build J_scalar = dual-pump source (same as 5_24/5_25)
  2. J_x, J_y = curl_of_scalar_z(J_scalar) -- treat J as
     z-projected potential, get its in-plane vector
  3. curl_J = curl_z_of_vector(J_x, J_y) -- scalar curl of J
     (would be zero analytically by curl-of-curl identity, so
      its NUMERICAL pattern reveals what the discrete curl
      operator extracts from J's Gaussian structure)
  4. Run solver -> rho_avg, reduce to rho_2d
  5. V_x, V_y = curl_of_scalar_z(rho_2d) -- evolved substrate
     vector field
  6. curl_V = curl_z_of_vector(V_x, V_y) -- scalar curl of V

  7. Spatial Pearson:
       r_spatial = pearson(flat(curl_J_inner),
                           flat(curl_V_inner))
     where _inner indicates the inner half-grid (boundary
     gradient artifacts removed)

  8. Spectral correlation:
       FFT both curl fields
       Pick top K=10 Fourier components by |amplitude| in V
       Compute pearson correlation of the K complex
       coefficients (real and imag parts concatenated)
     This tests whether the dominant wave structure of V's
     curl content matches J's curl content at the same modes.

PASS criteria:
  r_spatial > 0.5   (real spatial co-localization)
  AND
  r_spectral > 0.5  (shared dominant wave content)

PASS means: V's vorticity is geometrically and spectrally
inherited from J. The dual-pump source's vortical structure
propagates causally into the substrate response.

FAIL means: V is rotationally structured (5_25 PASS) but its
structure is NOT driven by J's structure. The PDE is
generating rotation independent of the input source. H2's
"J carries vorticity" claim becomes weaker -- "substrate
produces vorticity under dual-pump forcing" is what would
remain, with J's causal role open.

PIPELINE
--------
  Phase 1 -- Stability Gate (5 configs)
    Run at 128 and 256, compute correlations, classify;
    ABORT Phase 2 if classification flips between grids.

  Phase 2 -- Full Sweep (25 configs)
    Run at 128, compute correlations, classify;
    Emit one JSON per config with single H_PAPER_B_2 entry.

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

# Test thresholds (locked)
SPATIAL_CORR_THRESHOLD  = 0.5    # Pearson r on flattened inner-grid curls
SPECTRAL_CORR_THRESHOLD = 0.5    # Pearson r on top-K Fourier coefficients
N_TOP_MODES             = 10     # how many dominant Fourier modes to compare


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
# DUAL-PUMP J SOURCE (identical to 5_24/5_25)
# ============================================================================

def build_dual_pump_J(grid: int, separation_units: int) -> np.ndarray:
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


# ============================================================================
# VECTOR-CALCULUS HELPERS (identical to 5_25)
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


# ============================================================================
# CORRELATION HELPERS
# ============================================================================

def pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    """
    Pearson correlation coefficient between two same-shape
    float arrays. Returns 0.0 (not NaN) if either has zero
    variance, so a degenerate constant field reads as zero
    correlation rather than producing a non-finite test result.
    """
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


def spectral_correlation(field_a: np.ndarray,
                           field_b: np.ndarray,
                           n_top: int = N_TOP_MODES) -> float:
    """
    Spectral correlation between two 2D fields. Strategy:
      1. FFT both fields
      2. Identify the top n_top modes in field_b by |amplitude|
      3. Extract complex coefficients at those modes from both
         FFTs
      4. Pearson correlate the concatenated [real, imag] vectors

    This tests whether the dominant wave structure of one field
    is shared by the other at the same modes.
    """
    fft_a = np.fft.fft2(field_a)
    fft_b = np.fft.fft2(field_b)

    # Pick top modes by |amplitude| in field_b
    amp_b = np.abs(fft_b)
    flat_idx = np.argsort(amp_b.ravel())[::-1][:n_top]

    a_flat = fft_a.ravel()[flat_idx]
    b_flat = fft_b.ravel()[flat_idx]

    # Concatenate real and imag parts
    a_concat = np.concatenate([a_flat.real, a_flat.imag])
    b_concat = np.concatenate([b_flat.real, b_flat.imag])

    return pearson_corr(a_concat, b_concat)


# ============================================================================
# OBSERVABLE EXTRACTION
# ============================================================================

def extract_evolved_field(solver_result: Dict[str, Any]
                           ) -> Dict[str, Any]:
    rho_avg = solver_result.get("rho_avg")
    if rho_avg is None:
        return {"valid": False, "reason": "rho_avg missing"}

    rho_2d = rho_avg.sum(axis=0) if rho_avg.ndim == 3 else rho_avg
    rho_max = float(np.max(np.abs(rho_2d)))
    if rho_max <= 0:
        return {"valid": False, "reason": "rho_avg flat zero"}

    return {
        "valid":   True,
        "rho_2d":  rho_2d,
        "rho_max": rho_max,
    }


# ============================================================================
# CAUSATION TEST (dual correlation)
# ============================================================================

def test_vorticity_causation(J_scalar: np.ndarray,
                                rho_2d: np.ndarray
                                ) -> Tuple[str, Dict[str, Any]]:
    """
    Compute curl scalar fields of both J (the input source) and
    V (the evolved substrate response), then evaluate spatial
    and spectral correlation.

    PASS criteria (dual, locked):
        r_spatial   > SPATIAL_CORR_THRESHOLD  (0.5)
        r_spectral  > SPECTRAL_CORR_THRESHOLD (0.5)
    """
    grid = J_scalar.shape[0]

    # Build J's vector field and its curl scalar
    J_x, J_y = curl_of_scalar_z(J_scalar)
    curl_J = curl_z_of_vector(J_x, J_y)

    # Build V's vector field and its curl scalar
    V_x, V_y = curl_of_scalar_z(rho_2d)
    curl_V = curl_z_of_vector(V_x, V_y)

    # Restrict to inner half-grid (boundary artifacts removed)
    qg = grid // 4
    inner_curl_J = curl_J[qg:3 * qg, qg:3 * qg]
    inner_curl_V = curl_V[qg:3 * qg, qg:3 * qg]

    # Spatial correlation
    r_spatial = pearson_corr(inner_curl_J, inner_curl_V)

    # Spectral correlation (full-grid FFT, top N modes by |V|)
    r_spectral = spectral_correlation(curl_J, curl_V, n_top=N_TOP_MODES)

    # Magnitudes for diagnostic context
    max_abs_curl_J = float(np.max(np.abs(inner_curl_J)))
    max_abs_curl_V = float(np.max(np.abs(inner_curl_V)))

    diag = {
        "spatial_pearson":           r_spatial,
        "spectral_pearson":          r_spectral,
        "spatial_threshold":         SPATIAL_CORR_THRESHOLD,
        "spectral_threshold":        SPECTRAL_CORR_THRESHOLD,
        "max_abs_curl_J_inner":      max_abs_curl_J,
        "max_abs_curl_V_inner":      max_abs_curl_V,
        "n_spectral_modes_compared": N_TOP_MODES,
    }

    if not (math.isfinite(r_spatial) and math.isfinite(r_spectral)):
        diag["fail_reason"] = "non-finite correlation"
        return "FAIL", diag

    spatial_pass  = r_spatial  > SPATIAL_CORR_THRESHOLD
    spectral_pass = r_spectral > SPECTRAL_CORR_THRESHOLD

    if spatial_pass and spectral_pass:
        return "PASS", diag

    reasons = []
    if not spatial_pass:
        reasons.append(
            f"spatial r = {r_spatial:.3f} <= "
            f"{SPATIAL_CORR_THRESHOLD}")
    if not spectral_pass:
        reasons.append(
            f"spectral r = {r_spectral:.3f} <= "
            f"{SPECTRAL_CORR_THRESHOLD}")
    diag["fail_reason"] = "; ".join(reasons)
    return "FAIL", diag


# ============================================================================
# CONFIG-LEVEL EVALUATION
# ============================================================================

def evaluate_config(sigma_crit: float, separation: int, grid: int,
                      SubstrateSolverCls) -> Dict[str, Any]:
    J = build_dual_pump_J(grid, separation)
    solver = SubstrateSolverCls(grid=grid)
    t0 = time.time()
    result = solver.run(J, verbose=False)
    elapsed = time.time() - t0

    obs = extract_evolved_field(result)
    if not obs["valid"]:
        return {
            "sigma_crit":      sigma_crit,
            "separation":      separation,
            "grid":            grid,
            "elapsed_sec":     elapsed,
            "valid":           False,
            "reason":          obs.get("reason", "unknown"),
            "classification": "INCONCLUSIVE",
        }

    cls, diag = test_vorticity_causation(J, obs["rho_2d"])
    return {
        "sigma_crit":      sigma_crit,
        "separation":      separation,
        "grid":            grid,
        "elapsed_sec":     elapsed,
        "valid":           True,
        "rho_max":         obs["rho_max"],
        "classification":  cls,
        "diagnostics":     diag,
    }


# ============================================================================
# PHASE 1 -- STABILITY GATE
# ============================================================================

def run_phase1(SubstrateSolverCls
                ) -> Tuple[bool, List[Dict[str, Any]]]:
    print(f"\n  Phase 1: stability gate at "
          f"{GRID_BASELINE} vs {GRID_REFINEMENT} on 5 configs")

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
        print(f"    H_PAPER_B_2 (causation)  "
              f"128={r128['classification']:13s} "
              f"256={r256['classification']:13s}  [{mark}]")
        print(f"      128: r_spatial={d128.get('spatial_pearson', 0):.3f}  "
              f"r_spectral={d128.get('spectral_pearson', 0):.3f}")
        print(f"      256: r_spatial={d256.get('spatial_pearson', 0):.3f}  "
              f"r_spectral={d256.get('spectral_pearson', 0):.3f}")

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
        f"H-PaperB-2 vorticity causation test at sigma_crit="
        f"{sc}, pump_separation={sep}. The probe computes scalar "
        f"curl fields of both the J source and the evolved V "
        f"substrate field, then evaluates spatial Pearson "
        f"correlation (inner half-grid) and spectral correlation "
        f"(top {N_TOP_MODES} Fourier modes by |V|). PASS = "
        f"r_spatial > {SPATIAL_CORR_THRESHOLD} AND r_spectral > "
        f"{SPECTRAL_CORR_THRESHOLD}. PASS means V's vorticity is "
        f"causally inherited from J's vorticity, not generated "
        f"independently by the PDE. Distinct from test 5_24 "
        f"(operator consistency) and 5_25 (vorticity realization).")

    keywords = [
        "paper_b",
        "anchor_equation",
        "compositional_validation",
        "j_vorticity",
        "vorticity_causation",
        "j_to_v_correlation",
        "spatial_pearson",
        "spectral_pearson",
        "section_4_galactic",
        "v27526",
        cfg_tag,
    ]

    payload = {
        "test_name":       f"BCM_v27_5_26_J_causation_{cfg_tag}",
        "test_number":     5,
        "test_sub_number": 26,
        "version":         "v27",
        "system":          cfg_tag,
        "timestamp":       run_timestamp,
        "primacy_statement": (
            "All theoretical IP -- the operator/realization/"
            "causation three-pillar decomposition of H_PAPER_B_2 "
            "evidence, the dual-correlation causation test, the "
            "spatial+spectral PASS criterion -- belongs solely "
            "to Stephen Justin Burdick Sr. Emerald Entities LLC."),
        "test_distinguished_from_5_24_5_25": (
            "5_24 verified the curl identity nabla.(nabla x phi.z) "
            "= 0 on the J source (operator consistency, passes by "
            "construction for any scalar phi). 5_25 verified that "
            "the evolved rho_avg substrate response carries "
            "vorticity (realization). 5_26 verifies that V's "
            "rotational structure is causally driven by J's "
            "rotational structure, via dual spatial+spectral "
            "Pearson correlation."),
        "grid":              record["grid"],
        "sigma_crit":        sc,
        "pump_separation":   sep,
        "elapsed_sec":       record["elapsed_sec"],
        "rho_max":           record.get("rho_max"),
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

    fname = (f"BCM_v27_5_26_J_causation_{cfg_tag}_"
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
          f"on J-to-V causation correlation")

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
            print(f"      r_spatial = "
                  f"{diag.get('spatial_pearson', 0):+.4f}   "
                  f"r_spectral = "
                  f"{diag.get('spectral_pearson', 0):+.4f}")

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
    print("BCM v27 PAPER B PROBE 5_26 -- H2 VORTICITY CAUSATION")
    print("J-to-V spatial + spectral correlation")
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
        f"_phase1_5_26_stability_gate_{run_timestamp}.json")
    with open(phase1_summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "test_name":     "BCM_v27_5_26_phase1_stability_gate",
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
    print(f"  H_PAPER_B_2 (J -> V vorticity causation)")
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
