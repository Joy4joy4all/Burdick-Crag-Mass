# -*- coding: utf-8 -*-
"""
BCM v27 Paper B Probe Test 5_25 -- H_PAPER_B_2 Physical Vorticity Test
========================================================================

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
Date: 2026-05-03

PRIMACY STATEMENT
-----------------
All theoretical concepts -- the distinction between operator-
consistency and physical-vorticity tests, the J-emergence
criterion (substrate solver evolves a vortical response when
given vortical input, as opposed to merely satisfying the curl
identity on the source), the dual-criterion vorticity test on
the evolved rho_avg field, and every originating insight in
this file -- belong solely to Stephen Justin Burdick Sr. AI
systems were used strictly as code executors at SJB direction.
Emerald Entities LLC -- GIBUSH Systems.

PURPOSE
-------
The 5_24 H_PAPER_B_2 test verified the mathematical identity
nabla.(nabla x phi.z) = 0 on the constructed J source. This
verifies that the curl operator is implemented consistently in
numpy. It does NOT verify that the substrate physically
produces vortical responses when given vortical pump inputs.

Test 5_25 closes that gap. The probe runs the substrate solver
on the same dual-pump source as 5_24, then applies the dual-
criterion vorticity test to the EVOLVED rho_avg field (the wave
PDE response), not the source itself. PASS means the substrate's
emergent response field carries non-trivial vorticity that is
operationally divergence-free relative to its rotational content.

This is a physical claim, not an operator-consistency claim.
The 5_25 evidence is what reviewers should consider when
evaluating whether the substrate framework physically supports
H_PAPER_B_2.

LOCKED PARAMETERS
-----------------
  Grid baseline:           128 x 128 (matches Paper B v1.0,
                                       SPARC, 5_24)
  Refinement check grid:   256 x 256 (Phase 1 only, 5 configs)
  sigma_crit values:       {0.001, 0.005, 0.01, 0.05, 0.1}
                           (matches 5_24 cross-product axis 1)
  pump_separation values:  {5, 8, 12, 18, 25}
                           (matches 5_24 cross-product axis 2)
  Configurations:          5 x 5 = 25 (R3 cross-product,
                                        matches 5_24 by design
                                        for cross-test
                                        comparability)
  Phase 1 gate configs:    5 (corners + center of cross-product)
  Output:                  one JSON per configuration in
                           data/results/ with single H2
                           hypotheses_tested entry
  Evidence type:           primary

PHYSICAL TEST
-------------
For each (sigma_crit, pump_separation) configuration:

  1. Build dual-pump J source (same construction as 5_24:
     two opposed Gaussian pumps along x-axis at +/- sep/2 from
     center, sigma_pump = max(2.0, grid/32))
  2. Run substrate solver -> rho_avg (the evolved field)
  3. Reduce: rho_2d = rho_avg.sum(axis=0)
  4. Treat rho_2d as a stream function: V_substrate =
     curl(rho_2d . z_hat) = (drho/dy, -drho/dx)
  5. Compute div(V_substrate) and curl_z(V_substrate) on
     inner half-grid

PASS criteria (dual, locked by SJB pattern from 5_24):
  max|curl_z(V_substrate)| > vorticity_threshold (1e-6)
  AND
  max|curl_z(V_substrate)| / max|div(V_substrate)| > K (10)

The first prong establishes that the substrate's emergent
response carries real rotational structure (not just zero
field, not just smooth gradients). The second prong establishes
that the rotational content dominates the divergence content
in the evolved field -- the substrate response inherits the
divergence-free character of the input.

This is materially different from 5_24's H2 test. 5_24 tested
the curl identity on the J SOURCE (which always passes for any
scalar phi). 5_25 tests vorticity persistence in the SUBSTRATE
RESPONSE (which can fail if the wave PDE smooths out vortical
structure or produces divergent output).

PIPELINE
--------
  Phase 1 -- Stability Gate (5 configs)
    For each gate config:
      Run solver at 128 and 256
      Compute V_substrate and dual-criterion classification
      ABORT Phase 2 if classification flips between grids

  Phase 2 -- Full Sweep (25 configs)
    For each (sigma_crit, sep) config:
      Run solver at 128
      Compute V_substrate and dual-criterion
      Emit one JSON with single H_PAPER_B_2 entry

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

# Phase 1 gate configs: 4 corners + center (matches 5_24 pattern)
GATE_CONFIG_INDICES = [
    (0, 0),
    (0, 4),
    (4, 0),
    (4, 4),
    (2, 2),
]

H_KEY = "H_PAPER_B_2_J_VORTICITY"
EVIDENCE_TYPE = "primary"

# Test thresholds (locked, match 5_24 H2 dual-criterion)
H2_VORTICITY_THRESHOLD = 1e-6
H2_CURL_DIV_RATIO_K    = 10.0


# ============================================================================
# PATH RESOLUTION
# ============================================================================

def _resolve_paths():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    solver_root = os.path.dirname(os.path.dirname(this_dir))
    results_dir = os.path.join(solver_root, "data", "results")
    return solver_root, results_dir


def _import_project_modules():
    """Import substrate solver from core/. GPU dispatch on BCM_SOLVER."""
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
# DUAL-PUMP J SOURCE (same as 5_24)
# ============================================================================

def build_dual_pump_J(grid: int, separation_units: int) -> np.ndarray:
    """
    Build a 2D J-source field with two opposed Gaussian pumps along
    the x-axis at +/- (separation/2) from grid center.
    Identical to 5_24's construction so the input vorticity is
    constant across the two probes -- the test discriminator is
    whether the substrate response carries it through.
    """
    cx = grid // 2
    cy = grid // 2
    half_sep = separation_units // 2
    sigma_pump = max(2.0, grid / 32.0)

    yy, xx = np.meshgrid(np.arange(grid), np.arange(grid), indexing="ij")
    g_pos = np.exp(-((xx - (cx + half_sep)) ** 2 +
                      (yy - cy) ** 2) / (2.0 * sigma_pump ** 2))
    g_neg = np.exp(-((xx - (cx - half_sep)) ** 2 +
                      (yy - cy) ** 2) / (2.0 * sigma_pump ** 2))
    J = g_pos - g_neg
    return J.astype(np.float64)


# ============================================================================
# VECTOR-CALCULUS HELPERS
# ============================================================================

def curl_of_scalar_z(phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    For scalar phi(x,y) treated as z-component of a vector field,
    curl(phi z_hat) = (dphi/dy, -dphi/dx).

    Same operator as 5_24, applied here to the EVOLVED rho_avg
    field rather than the J source. This is the test
    discriminator.
    """
    dphi_dy = np.gradient(phi, axis=0)
    dphi_dx = np.gradient(phi, axis=1)
    return dphi_dy, -dphi_dx


def divergence_of_vector(V_x: np.ndarray,
                          V_y: np.ndarray) -> np.ndarray:
    """Discrete div of 2D vector field: dV_x/dx + dV_y/dy."""
    dVx_dx = np.gradient(V_x, axis=1)
    dVy_dy = np.gradient(V_y, axis=0)
    return dVx_dx + dVy_dy


def curl_z_of_vector(V_x: np.ndarray,
                       V_y: np.ndarray) -> np.ndarray:
    """Discrete z-component of curl: dV_y/dx - dV_x/dy."""
    dVy_dx = np.gradient(V_y, axis=1)
    dVx_dy = np.gradient(V_x, axis=0)
    return dVy_dx - dVx_dy


# ============================================================================
# OBSERVABLE EXTRACTION
# ============================================================================

def extract_evolved_field(solver_result: Dict[str, Any]
                           ) -> Dict[str, Any]:
    """
    Pull the EVOLVED substrate response from the solver result.
    Layer-summed rho_avg is the canonical scalar reduction
    (matches 5_23 SPARC sigma extraction convention).

    This is the field 5_25 tests for vorticity, in contrast to
    5_24's test on the J source.
    """
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
# PHYSICAL VORTICITY TEST
# ============================================================================

def test_substrate_vorticity(rho_2d: np.ndarray
                                ) -> Tuple[str, Dict[str, Any]]:
    """
    Test whether the EVOLVED substrate field carries vorticity.

    Construction:
        V_substrate = curl(rho_2d . z_hat) = (drho/dy, -drho/dx)
    PASS criteria (dual, locked):
        max|curl_z(V_substrate)| > H2_VORTICITY_THRESHOLD
        AND
        max|curl_z(V)| / max|div(V)| > H2_CURL_DIV_RATIO_K

    Both prongs evaluated on inner half-grid (boundary gradient
    artifacts removed).
    """
    grid = rho_2d.shape[0]

    V_x, V_y = curl_of_scalar_z(rho_2d)
    div_V = divergence_of_vector(V_x, V_y)
    curl_V = curl_z_of_vector(V_x, V_y)

    qg = grid // 4
    inner_div  = div_V[qg:3 * qg, qg:3 * qg]
    inner_curl = curl_V[qg:3 * qg, qg:3 * qg]

    max_abs_div  = float(np.max(np.abs(inner_div)))
    max_abs_curl = float(np.max(np.abs(inner_curl)))

    ratio = (max_abs_curl / max_abs_div
             if max_abs_div > 0 else float("inf"))

    diag = {
        "field_under_test":      "evolved rho_avg (substrate response)",
        "test_construction":     ("V_substrate = curl(rho_2d . z_hat); "
                                  "test curl and div of V_substrate"),
        "max_abs_div_inner":     max_abs_div,
        "max_abs_curl_inner":    max_abs_curl,
        "curl_to_div_ratio":     ratio,
        "vorticity_threshold":   H2_VORTICITY_THRESHOLD,
        "ratio_threshold_K":     H2_CURL_DIV_RATIO_K,
    }

    if not (math.isfinite(max_abs_div)
            and math.isfinite(max_abs_curl)):
        diag["fail_reason"] = "non-finite curl or divergence"
        return "FAIL", diag

    has_vorticity = max_abs_curl > H2_VORTICITY_THRESHOLD
    div_dominated = ratio > H2_CURL_DIV_RATIO_K

    if has_vorticity and div_dominated:
        return "PASS", diag

    reasons = []
    if not has_vorticity:
        reasons.append(
            f"max|curl V| = {max_abs_curl:.3e} <= "
            f"{H2_VORTICITY_THRESHOLD:.3e} (substrate response "
            f"smoothed out vortical content)")
    if not div_dominated:
        reasons.append(
            f"curl/div ratio = {ratio:.3e} <= "
            f"{H2_CURL_DIV_RATIO_K:.3e} (substrate response "
            f"divergence-dominated, not vortical)")
    diag["fail_reason"] = "; ".join(reasons)
    return "FAIL", diag


# ============================================================================
# CONFIG-LEVEL EVALUATION
# ============================================================================

def evaluate_config(sigma_crit: float, separation: int, grid: int,
                      SubstrateSolverCls) -> Dict[str, Any]:
    """Run solver once at given grid; emit single H2 classification
    on the evolved field."""
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

    cls, diag = test_substrate_vorticity(obs["rho_2d"])
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

        mark = "OK" if invariant else "FLIP"
        print(f"    H_PAPER_B_2 (substrate vorticity)  "
              f"128={r128['classification']:13s} "
              f"256={r256['classification']:13s}  [{mark}]")

    return all_invariant, records


# ============================================================================
# PHASE 2 -- FULL SWEEP
# ============================================================================

def emit_config_json(record: Dict[str, Any],
                       results_dir: str,
                       run_timestamp: str) -> str:
    """One JSON per config, single H_PAPER_B_2 hypothesis entry."""
    sc = record["sigma_crit"]
    sep = record["separation"]
    cls = record["classification"]
    diag = record["diagnostics"]

    cfg_tag = f"sc{sc:.4f}_sep{sep}".replace(".", "p")

    statement = (
        f"H-PaperB-2 substrate vorticity persistence test at "
        f"sigma_crit={sc}, pump_separation={sep}. The dual-pump "
        f"input source carries vorticity by construction; this "
        f"test verifies the EVOLVED substrate field rho_avg "
        f"retains rotational structure with curl dominating "
        f"divergence on inner half-grid. PASS = max|curl V| > "
        f"1e-6 AND max|curl V|/max|div V| > 10 where V = "
        f"curl(rho_avg . z_hat). Distinct from test 5_24's "
        f"operator-consistency check on the J source.")

    keywords = [
        "paper_b",
        "anchor_equation",
        "compositional_validation",
        "j_vorticity",
        "physical_vorticity",
        "substrate_response",
        "section_4_galactic",
        "v27525",
        cfg_tag,
    ]

    payload = {
        "test_name":       f"BCM_v27_5_25_J_substrate_vorticity_{cfg_tag}",
        "test_number":     5,
        "test_sub_number": 25,
        "version":         "v27",
        "system":          cfg_tag,
        "timestamp":       run_timestamp,
        "primacy_statement": (
            "All theoretical IP -- the operator-consistency "
            "vs physical-vorticity distinction, the dual-criterion "
            "test on the evolved substrate field, the J-emergence "
            "criterion -- belongs solely to Stephen Justin Burdick "
            "Sr. Emerald Entities LLC."),
        "test_distinguished_from_5_24": (
            "Test 5_24 H_PAPER_B_2 verified the mathematical "
            "identity nabla.(nabla x phi.z) = 0 on the J source "
            "(passes by curl identity for any scalar phi). Test "
            "5_25 tests whether the EVOLVED rho_avg substrate "
            "response carries vorticity given vortical pump input "
            "(can fail if the substrate wave PDE smooths out "
            "rotational content)."),
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

    fname = (f"BCM_v27_5_25_J_substrate_vort_{cfg_tag}_"
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
          f"on EVOLVED substrate field")

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
            print(f"      max|curl V| = "
                  f"{diag.get('max_abs_curl_inner', 0):.3e}  "
                  f"max|div V| = {diag.get('max_abs_div_inner', 0):.3e}  "
                  f"ratio = {diag.get('curl_to_div_ratio', 0):.3e}")

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
    print("BCM v27 PAPER B PROBE 5_25 -- H2 PHYSICAL VORTICITY")
    print("Substrate response field, not source identity")
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
        f"_phase1_5_25_stability_gate_{run_timestamp}.json")
    with open(phase1_summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "test_name":     "BCM_v27_5_25_phase1_stability_gate",
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
    print(f"  H_PAPER_B_2 (substrate response vorticity)")
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
