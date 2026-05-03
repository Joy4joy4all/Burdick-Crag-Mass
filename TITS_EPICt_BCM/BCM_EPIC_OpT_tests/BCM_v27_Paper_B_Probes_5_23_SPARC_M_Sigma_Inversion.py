# -*- coding: utf-8 -*-
"""
BCM v27 Paper B Probe Test 5_23 -- SPARC M-Sigma Inversion
============================================================

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
Date: 2026-05-02

PRIMACY STATEMENT
-----------------
All theoretical concepts, the Anchor Equation, the M-sigma inversion
hypothesis (H_PAPER_B_5), the strict-local-monotonicity PASS
definition, the percentile-extrema stability gate, the 1% mass
perturbation via baryonic V-component scaling, the cross-grid
refinement check, the per-galaxy R3-independent event emission
protocol, and every originating insight in this file belong solely
to Stephen Justin Burdick Sr. AI systems were used strictly as
computational processing tools and code executors at the direction
of SJB. No AI system contributed theoretical concepts. Emerald
Entities LLC -- GIBUSH Systems.

PURPOSE
-------
Step 3 of the v27 H_PAPER_B_5 evidence-density program. The
post-bridge-probe pre-SPARC reproducible baseline showed
H_PAPER_B_5 at 1 event, posterior 0.60, NEEDS_MORE_DATA. This
probe scales H_PAPER_B_5 evidence by feeding 175 SPARC galaxies
through the strict-local-monotonicity test, each galaxy
contributing one R3-independent evidence event.

LOCKED PARAMETERS
-----------------
  Grid baseline:          128 x 128  (matches Paper B v1.0)
  Refinement check grid:  256 x 256  (2x baseline)
  Mass perturbation:      +/- 1% (M -> M(1 +/- 0.01))
  V-component scaling:    sqrt(1 +/- 0.01) (since V^2 ~ M)
  PASS rule:              strict local monotonicity --
                          (sigma_plus, sigma_baseline, sigma_minus)
                          must be sign-consistent
  FAIL rule:              sign flip, NaN, or zero gradient
  Evidence type:          primary (strength 0.50)
  Source mode:            classic (V_bar^2/r) -- load_galaxy default
  Sigma extraction:       max(|sum_layers(rho_avg)|) -- same scalar
                          the solver itself emits internally
  Stability gate:         5 galaxies at mass percentiles
                          {0, 25, 50, 75, 100}
                          ABORT Phase 2 if PASS/FAIL classification
                          flips between 128^2 and 256^2 on any
                          stability-gate galaxy
  Output:                 one JSON per galaxy in
                          data/sparc_results/

PIPELINE
--------
  Phase 1 -- Stability Gate
    1. Load all SPARC .dat files in data/sparc_raw/
    2. For each, compute M proxy = max(V_bar^2) * r_max
    3. Sort, select indices at percentiles {0, 25, 50, 75, 100}
    4. For each of the 5 galaxies:
         a. Build J at grid=128 (V_components unscaled, +1%, -1%)
            -> 3 J fields
         b. Run solver on each, extract scalar sigma
         c. Classify monotonicity at 128
         d. Repeat at grid=256
         e. Compare 128 vs 256 classification
    5. If any classification flips between grids -> ABORT
       (emit diagnostic JSON to data/sparc_results/_phase1_aborted_*.json,
        do not run Phase 2)

  Phase 2 -- Full SPARC Run (only if Phase 1 PASS)
    1. Iterate all 175 SPARC galaxies at grid=128
    2. Per galaxy: 3 solver runs (baseline, +1%, -1%)
    3. Classify strict monotonicity
    4. Emit one JSON per galaxy with one hypotheses_tested entry
       declaring H_PAPER_B_5_M_SIGMA_INVERSION

DOES NOT TOUCH
--------------
- core solver
- launcher
- hypothesis_engine
- bcm_tensor_hypothesis
- vocabulary registry
- any engine state (write-only outputs)
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

M_PERTURBATION = 0.01           # +/- 1% in M
V_SCALE_PLUS = math.sqrt(1.0 + M_PERTURBATION)   # ~1.004988
V_SCALE_MINUS = math.sqrt(1.0 - M_PERTURBATION)  # ~0.994987

PERCENTILE_INDICES_FRAC = [0.00, 0.25, 0.50, 0.75, 1.00]

H_PAPER_B_5_KEY = "H_PAPER_B_5_M_SIGMA_INVERSION"

EVIDENCE_TYPE = "primary"

SOURCE_MODE = "classic"   # load_galaxy default; matches sparc_ingest


# ============================================================================
# PATH RESOLUTION
# ============================================================================

def _resolve_paths():
    """
    Climb two directory levels from this file to reach solver root,
    then resolve sparc_raw/ and sparc_results/ directories.
    Standard pattern for tests in TITS_EPICt_BCM/BCM_EPIC_OpT_tests/.
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))
    solver_root = os.path.dirname(os.path.dirname(this_dir))
    sparc_raw = os.path.join(solver_root, "data", "sparc_raw")
    sparc_results = os.path.join(solver_root, "data", "sparc_results")
    return solver_root, sparc_raw, sparc_results


# ============================================================================
# IMPORTS FROM PROJECT (deferred so test fails clean if env wrong)
# ============================================================================

def _import_project_modules():
    """
    Import sparc_ingest and SubstrateSolver from core/.

    Path discipline: this file lives at
      solver_root/TITS_EPICt_BCM/BCM_EPIC_OpT_tests/BCM_v27_Paper_B_Probes_5_23_*.py
    Climb two directories to reach solver_root, then prepend to
    sys.path so 'from core.X' resolves the same way the launcher
    and test_crag_calibration.py do.

    BCM_SOLVER env var dispatch is inlined here (was previously
    delegated to solver_select.py, which is not present in this
    deployment tree). BCM_SOLVER=gpu attempts core.substrate_solver_gpu;
    on import failure or any other value, falls back to
    core.substrate_solver (CPU).
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))
    solver_root = os.path.dirname(os.path.dirname(this_dir))
    if solver_root not in sys.path:
        sys.path.insert(0, solver_root)

    # Import sparc_ingest from core/
    try:
        from core import sparc_ingest as si
    except ImportError as e:
        # Some deployments may have sparc_ingest at the solver root
        # rather than under core/. Try that fallback explicitly.
        try:
            sys.path.insert(0, solver_root)
            import sparc_ingest as si  # noqa: F401
        except ImportError:
            raise ImportError(
                f"sparc_ingest not importable from core/ or "
                f"solver root: {e}. Solver root tried: "
                f"{solver_root}"
            )

    # Import SubstrateSolver -- GPU if requested and available, else CPU
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
            print(f"  [solver_dispatch] GPU requested but import "
                  f"failed: {e}", file=sys.stderr)
            print(f"  [solver_dispatch] Falling back to CPU solver",
                  file=sys.stderr)
    if SubstrateSolver is None:
        try:
            from core.substrate_solver import (
                SubstrateSolver as _Scpu)
            SubstrateSolver = _Scpu
            backend = "cpu"
        except ImportError as e:
            raise ImportError(
                f"core.substrate_solver not importable: {e}. "
                f"Solver root tried: {solver_root}"
            )

    return si, SubstrateSolver, backend


# ============================================================================
# MASS PROXY (no SPARC table needed)
# ============================================================================

def compute_mass_proxy(rotation_data: Dict[str, np.ndarray]) -> float:
    """
    Compute a baryonic mass proxy from the rotation curve alone.
    M ~ V^2 * R / G in cgs; for ranking purposes we use the
    dimensionless proxy max(V_bar^2) * r_max.

    Pure ranking metric. Not a calibrated mass.
    """
    radii = rotation_data.get("radius_kpc")
    vgas = rotation_data.get("Vgas")
    vdisk = rotation_data.get("Vdisk")
    vbul = rotation_data.get("Vbul")
    if (radii is None or len(radii) == 0
            or vgas is None or vdisk is None or vbul is None):
        return 0.0
    v_bar_sq = vgas ** 2 + vdisk ** 2 + vbul ** 2
    if len(v_bar_sq) == 0:
        return 0.0
    return float(np.max(v_bar_sq) * radii[-1])


# ============================================================================
# V-COMPONENT PERTURBATION
# ============================================================================

def perturb_rotation_data(rotation_data: Dict[str, np.ndarray],
                           v_scale: float) -> Dict[str, np.ndarray]:
    """
    Scale V_gas, V_disk, V_bul by v_scale. Does NOT modify Vobs
    (Vobs only enters discrepancy diagnostics, not J construction).

    Returns a NEW dict; does not mutate the input.
    """
    out = dict(rotation_data)
    for key in ("Vgas", "Vdisk", "Vbul"):
        if key in out and isinstance(out[key], np.ndarray):
            out[key] = out[key] * v_scale
    return out


# ============================================================================
# SCALAR SIGMA EXTRACTION
# ============================================================================

def extract_scalar_sigma(solver_result: Dict[str, Any]) -> float:
    """
    Locked rule for scalar sigma extraction: max-abs of layer-summed
    rho_avg. Same scalar the solver internally tracks at line 288
    of substrate_solver.py (rho_sub_max).

    rho_avg is the mass-density field that emerges from the wave
    equation under J source. In BCM framework terminology this is
    the substrate response field that maps from input M to output sigma.
    """
    rho_avg = solver_result.get("rho_avg")
    if rho_avg is None:
        return float("nan")
    try:
        layer_sum = np.abs(rho_avg.sum(axis=0))
        return float(np.max(layer_sum))
    except Exception:
        return float("nan")


# ============================================================================
# MONOTONICITY CLASSIFIER
# ============================================================================

def classify_monotonicity(sigma_minus: float,
                           sigma_baseline: float,
                           sigma_plus: float) -> Tuple[str, Dict[str, Any]]:
    """
    Strict local monotonicity test:
      PASS  if (sigma_plus, sigma_baseline, sigma_minus) is monotonic
              and sign of (sigma_plus - sigma_baseline) matches
              sign of (sigma_baseline - sigma_minus)
      FAIL  if sign flip OR any value NaN/inf OR derivative zero
      INCONCLUSIVE if numerical degeneracy (all three values within
                   floating-point noise floor of each other)
    """
    diag = {
        "sigma_minus":    sigma_minus,
        "sigma_baseline": sigma_baseline,
        "sigma_plus":     sigma_plus,
    }
    # NaN / inf check
    for k, v in (("sigma_minus", sigma_minus),
                  ("sigma_baseline", sigma_baseline),
                  ("sigma_plus", sigma_plus)):
        if not math.isfinite(v):
            diag["fail_reason"] = f"{k} non-finite ({v})"
            return "FAIL", diag

    delta_plus = sigma_plus - sigma_baseline
    delta_minus = sigma_baseline - sigma_minus
    diag["delta_plus"] = delta_plus
    diag["delta_minus"] = delta_minus

    # Numerical degeneracy guard. If both deltas are below the
    # floor of typical solver-noise (1e-10 relative to baseline),
    # the test is meaningless.
    floor = max(abs(sigma_baseline), 1e-12) * 1e-10
    if abs(delta_plus) < floor and abs(delta_minus) < floor:
        diag["fail_reason"] = (
            f"both deltas below noise floor ({floor:.3e})")
        return "INCONCLUSIVE", diag

    # Sign consistency: dsigma/dM must have the same sign on both sides
    sign_plus = np.sign(delta_plus)
    sign_minus = np.sign(delta_minus)
    diag["sign_plus"] = float(sign_plus)
    diag["sign_minus"] = float(sign_minus)

    if sign_plus == 0 or sign_minus == 0:
        diag["fail_reason"] = "zero gradient on one side"
        return "FAIL", diag
    if sign_plus != sign_minus:
        diag["fail_reason"] = (
            f"sign flip: dsigma/dM(+) = {sign_plus}, "
            f"dsigma/dM(-) = {sign_minus}")
        return "FAIL", diag

    diag["monotonic_direction"] = (
        "increasing" if sign_plus > 0 else "decreasing")
    return "PASS", diag


# ============================================================================
# SINGLE-GALAXY EVALUATION
# ============================================================================

def run_solver_for_J(SubstrateSolverCls, J: np.ndarray,
                      grid: int) -> Dict[str, Any]:
    """
    Build a fresh solver at the requested grid and run it on J.
    Verbose disabled to keep runtime logging compact.
    """
    solver = SubstrateSolverCls(grid=grid)
    return solver.run(J, verbose=False)


def evaluate_galaxy(galaxy_dat_path: str,
                     grid: int,
                     si_module,
                     SubstrateSolverCls) -> Dict[str, Any]:
    """
    Run baseline / +dM / -dM solver pass for one galaxy at one grid.
    Returns scalar sigma triple plus monotonicity classification.
    """
    rot = si_module.load_rotation_curve(galaxy_dat_path)
    galaxy_name = os.path.basename(galaxy_dat_path).split("_")[0]

    # Build three J fields (baseline, +dM, -dM) at requested grid
    rot_plus  = perturb_rotation_data(rot, V_SCALE_PLUS)
    rot_minus = perturb_rotation_data(rot, V_SCALE_MINUS)

    J_baseline = si_module.build_source_field(
        rot, grid=grid, scale_factor=1.0, source_mode=SOURCE_MODE)
    J_plus  = si_module.build_source_field(
        rot_plus,  grid=grid, scale_factor=1.0, source_mode=SOURCE_MODE)
    J_minus = si_module.build_source_field(
        rot_minus, grid=grid, scale_factor=1.0, source_mode=SOURCE_MODE)

    t0 = time.time()
    res_baseline = run_solver_for_J(SubstrateSolverCls, J_baseline, grid)
    res_plus     = run_solver_for_J(SubstrateSolverCls, J_plus, grid)
    res_minus    = run_solver_for_J(SubstrateSolverCls, J_minus, grid)
    elapsed = time.time() - t0

    sigma_baseline = extract_scalar_sigma(res_baseline)
    sigma_plus     = extract_scalar_sigma(res_plus)
    sigma_minus    = extract_scalar_sigma(res_minus)

    classification, diag = classify_monotonicity(
        sigma_minus, sigma_baseline, sigma_plus)

    return {
        "galaxy_name":     galaxy_name,
        "dat_path":        galaxy_dat_path,
        "grid":            grid,
        "elapsed_sec":     elapsed,
        "sigma_baseline":  sigma_baseline,
        "sigma_plus":      sigma_plus,
        "sigma_minus":     sigma_minus,
        "classification":  classification,
        "diagnostics":     diag,
    }


# ============================================================================
# PHASE 1 -- STABILITY GATE
# ============================================================================

def select_percentile_galaxies(galaxy_paths_with_mass: List[Tuple[str, float]]
                                ) -> List[Tuple[str, float, int, float]]:
    """
    Sort galaxies by M proxy ascending, select indices at the
    locked percentile fractions.

    Returns list of (path, mass, percentile_index, percentile_value).
    """
    sorted_g = sorted(galaxy_paths_with_mass, key=lambda x: x[1])
    n = len(sorted_g)
    if n == 0:
        return []
    selected = []
    seen_indices = set()
    for frac in PERCENTILE_INDICES_FRAC:
        idx = min(int(round(frac * (n - 1))), n - 1)
        # Avoid duplicates if catalog is small
        while idx in seen_indices and idx < n - 1:
            idx += 1
        seen_indices.add(idx)
        path, mass = sorted_g[idx]
        selected.append((path, mass, idx, frac))
    return selected


def run_phase1_stability_gate(galaxy_paths_with_mass: List[Tuple[str, float]],
                               si_module, SubstrateSolverCls
                               ) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Run the 5 percentile-extrema galaxies at both 128 and 256.
    Compare PASS/FAIL classification across grids.

    Returns (all_invariant, per_galaxy_records).
    all_invariant=True if all 5 galaxies have identical PASS/FAIL/INCONCLUSIVE
    classification at both grids.
    """
    selected = select_percentile_galaxies(galaxy_paths_with_mass)
    print(f"\n  Phase 1: stability gate on {len(selected)} galaxies")
    print(f"  Percentiles: {PERCENTILE_INDICES_FRAC}")
    print(f"  Grids:       {GRID_BASELINE} vs {GRID_REFINEMENT}")

    records = []
    all_invariant = True
    for (path, mass, idx, frac) in selected:
        gname = os.path.basename(path).split("_")[0]
        print(f"\n  [{frac:.2f} pct, idx {idx}] {gname}  M_proxy={mass:.3e}")

        try:
            r128 = evaluate_galaxy(path, GRID_BASELINE,
                                    si_module, SubstrateSolverCls)
            r256 = evaluate_galaxy(path, GRID_REFINEMENT,
                                    si_module, SubstrateSolverCls)
        except Exception as e:
            tb = traceback.format_exc()
            records.append({
                "galaxy_name":   gname,
                "percentile":    frac,
                "error":         str(e),
                "traceback":     tb,
                "invariant":     False,
            })
            all_invariant = False
            print(f"    ERROR evaluating {gname}: {e}")
            continue

        invariant = (r128["classification"] == r256["classification"])
        if not invariant:
            all_invariant = False
        records.append({
            "galaxy_name":      gname,
            "percentile":       frac,
            "percentile_index": idx,
            "M_proxy":          mass,
            "result_128":       r128,
            "result_256":       r256,
            "invariant":        invariant,
        })
        marker = "OK" if invariant else "FLIP"
        print(f"    128={r128['classification']}  "
              f"256={r256['classification']}  [{marker}]")

    return all_invariant, records


# ============================================================================
# PHASE 2 -- FULL SPARC RUN
# ============================================================================

def emit_galaxy_json(galaxy_record: Dict[str, Any],
                      sparc_results_dir: str,
                      timestamp: str) -> str:
    """
    Write one JSON per galaxy. The hypotheses_tested block contains
    exactly one entry: H_PAPER_B_5_M_SIGMA_INVERSION for this galaxy.
    R3-clean: each galaxy is one independent physical system.
    """
    gname = galaxy_record["galaxy_name"]
    cls = galaxy_record["classification"]

    statement = (
        f"H-PaperB-5 M-sigma local monotonicity at SPARC galaxy "
        f"{gname}. Mass perturbed +/- 1% via baryonic V-component "
        f"scaling sqrt(1 +/- 0.01); strict-monotonicity test on "
        f"scalar sigma = max|sum_layers(rho_avg)| at grid 128^2.")

    keywords = [
        "paper_b",
        "m_sigma_inversion",
        "anchor_equation",
        "sparc",
        "section_4_galactic",
        "compositional_validation",
        gname,
    ]

    payload = {
        "test_name":      f"BCM_v27_SPARC_M_sigma_{gname}",
        "test_number":    5,
        "test_sub_number": 23,
        "version":        "v27",
        "system":         gname,
        "timestamp":      timestamp,
        "primacy_statement": (
            "All theoretical IP -- the M-sigma inversion hypothesis, "
            "the strict-local-monotonicity PASS definition, the 1% "
            "mass perturbation protocol -- belongs solely to "
            "Stephen Justin Burdick Sr. Emerald Entities LLC."),
        "grid":              galaxy_record["grid"],
        "M_perturbation":    M_PERTURBATION,
        "v_scale_plus":      V_SCALE_PLUS,
        "v_scale_minus":     V_SCALE_MINUS,
        "source_mode":       SOURCE_MODE,
        "sigma_extraction":  "max(|sum_layers(rho_avg)|)",
        "elapsed_sec":       galaxy_record["elapsed_sec"],
        "sigma_baseline":    galaxy_record["sigma_baseline"],
        "sigma_plus":        galaxy_record["sigma_plus"],
        "sigma_minus":       galaxy_record["sigma_minus"],
        "monotonicity_diagnostics": galaxy_record["diagnostics"],
        "hypotheses_tested": {
            H_PAPER_B_5_KEY: {
                "statement":     statement,
                "result":        cls,    # PASS | FAIL | INCONCLUSIVE
                "evidence_type": EVIDENCE_TYPE,
                "pass_count":    1 if cls == "PASS" else 0,
                "total_configs": 1,
                "prior":         0.50,
                "keywords":      keywords,
            },
        },
    }

    fname = (f"BCM_v27_SPARC_M_sigma_{gname}_{timestamp}.json")
    fpath = os.path.join(sparc_results_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=_json_default)
    return fpath


def _json_default(obj):
    """Handle numpy types in json.dump."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def run_phase2_full(galaxy_paths: List[str],
                     si_module,
                     SubstrateSolverCls,
                     sparc_results_dir: str,
                     run_timestamp: str
                     ) -> Dict[str, Any]:
    """
    Iterate all SPARC galaxies at GRID_BASELINE. One JSON per galaxy.
    """
    print(f"\n  Phase 2: full SPARC run on {len(galaxy_paths)} galaxies "
          f"at grid {GRID_BASELINE}^2")

    n_pass = 0
    n_fail = 0
    n_inconclusive = 0
    n_error = 0
    emitted_files = []

    for i, path in enumerate(galaxy_paths):
        gname = os.path.basename(path).split("_")[0]
        progress = f"[{i+1}/{len(galaxy_paths)}]"
        try:
            rec = evaluate_galaxy(
                path, GRID_BASELINE, si_module, SubstrateSolverCls)
        except Exception as e:
            n_error += 1
            print(f"  {progress} {gname}: ERROR {e}")
            continue

        cls = rec["classification"]
        if cls == "PASS":
            n_pass += 1
        elif cls == "FAIL":
            n_fail += 1
        else:
            n_inconclusive += 1

        out_path = emit_galaxy_json(rec, sparc_results_dir, run_timestamp)
        emitted_files.append(out_path)
        print(f"  {progress} {gname:14s}  {cls:13s}  "
              f"({rec['elapsed_sec']:.1f}s)  -> "
              f"{os.path.basename(out_path)}")

    return {
        "n_galaxies":      len(galaxy_paths),
        "n_pass":          n_pass,
        "n_fail":          n_fail,
        "n_inconclusive":  n_inconclusive,
        "n_error":         n_error,
        "emitted_files":   emitted_files,
    }


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    print("=" * 72)
    print("BCM v27 PAPER B PROBE 5_23 -- SPARC M-SIGMA INVERSION")
    print("Step 3 of H_PAPER_B_5 evidence-density program")
    print("Stephen Justin Burdick Sr. -- Emerald Entities LLC")
    print("=" * 72)

    t_start = time.time()

    # Paths
    solver_root, sparc_raw, sparc_results = _resolve_paths()
    print(f"  solver_root:   {solver_root}")
    print(f"  sparc_raw:     {sparc_raw}")
    print(f"  sparc_results: {sparc_results}")

    if not os.path.isdir(sparc_raw):
        print(f"\n  ERROR: SPARC raw data directory not found: {sparc_raw}")
        print(f"  Run setup_sparc.py to download SPARC rotation curves.")
        return 2

    os.makedirs(sparc_results, exist_ok=True)

    # Imports
    print("\n  Importing project modules...")
    try:
        si, SubstrateSolverCls, backend = _import_project_modules()
    except ImportError as e:
        print(f"  ERROR: {e}")
        return 2
    print(f"  sparc_ingest         : {si.__name__}")
    print(f"  SubstrateSolver      : {SubstrateSolverCls.__module__}")
    print(f"  Backend resolved     : {backend}")
    print(f"  BCM_SOLVER env var   : "
          f"{os.environ.get('BCM_SOLVER', 'unset (CPU default)')}")

    # Catalog
    # SPARC raw data lives in mass-bin subdirectories under sparc_raw/
    # (dwarf_V0-50/, low_V50-100/, mid_V100-150/, high_V150-200/,
    # massive_V200plus/). Walk recursively to pick up all *_rotmod.dat
    # files regardless of which subdirectory they live in.
    print(f"\n  Scanning {sparc_raw} recursively for *_rotmod.dat ...")
    all_files = []
    subdir_counts: Dict[str, int] = {}
    for dirpath, _dirnames, filenames in os.walk(sparc_raw):
        for f in filenames:
            if f.endswith("_rotmod.dat"):
                all_files.append(os.path.join(dirpath, f))
                rel = os.path.relpath(dirpath, sparc_raw)
                subdir_counts[rel] = subdir_counts.get(rel, 0) + 1
    if not all_files:
        # Fallback: accept any .dat (in case the file naming convention
        # changed in a future SPARC release)
        for dirpath, _dirnames, filenames in os.walk(sparc_raw):
            for f in filenames:
                if f.endswith(".dat"):
                    all_files.append(os.path.join(dirpath, f))
                    rel = os.path.relpath(dirpath, sparc_raw)
                    subdir_counts[rel] = subdir_counts.get(rel, 0) + 1
    all_files.sort()
    print(f"  Found {len(all_files)} galaxy file(s)")
    for rel, count in sorted(subdir_counts.items()):
        print(f"    {rel}: {count}")
    if len(all_files) == 0:
        print("  ERROR: no SPARC galaxy files found")
        return 2

    # Mass proxies for percentile selection
    print("\n  Computing baryonic mass proxies for percentile selection...")
    paths_with_mass = []
    for path in all_files:
        try:
            rot = si.load_rotation_curve(path)
            mass = compute_mass_proxy(rot)
            if mass > 0:
                paths_with_mass.append((path, mass))
        except Exception as e:
            print(f"    SKIP {os.path.basename(path)}: {e}")
    print(f"  {len(paths_with_mass)} galaxies retained for ranking")

    if len(paths_with_mass) < 5:
        print(f"  ERROR: need at least 5 galaxies for stability gate, "
              f"have {len(paths_with_mass)}")
        return 2

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Phase 1
    all_invariant, phase1_records = run_phase1_stability_gate(
        paths_with_mass, si, SubstrateSolverCls)

    # Emit phase 1 summary regardless of outcome
    phase1_summary_path = os.path.join(
        sparc_results,
        f"_phase1_stability_gate_{run_timestamp}.json")
    with open(phase1_summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "test_name":  "BCM_v27_SPARC_M_sigma_phase1_stability_gate",
            "timestamp":  run_timestamp,
            "all_invariant": all_invariant,
            "records":    phase1_records,
        }, f, indent=2, default=_json_default)
    print(f"\n  Phase 1 summary written: "
          f"{os.path.basename(phase1_summary_path)}")

    if not all_invariant:
        print("\n" + "=" * 72)
        print("  PHASE 1 ABORT: PASS/FAIL classification flipped between "
              "128^2 and 256^2 on at least one stability-gate galaxy.")
        print("  Phase 2 NOT executed. No H_PAPER_B_5 evidence emitted.")
        print("  See phase 1 summary for diagnostics.")
        print("=" * 72)
        elapsed_total = time.time() - t_start
        print(f"  Total elapsed: {elapsed_total:.1f}s")
        return 1

    print("\n  Phase 1 PASS: all 5 percentile galaxies invariant under "
          "grid refinement. Greenlight Phase 2.")

    # Phase 2: full run
    only_paths = [p for (p, _m) in paths_with_mass]
    phase2_summary = run_phase2_full(
        only_paths, si, SubstrateSolverCls,
        sparc_results, run_timestamp)

    elapsed_total = time.time() - t_start
    print("\n" + "=" * 72)
    print(f"  TOTAL: {phase2_summary['n_galaxies']} galaxies")
    print(f"    PASS:         {phase2_summary['n_pass']}")
    print(f"    FAIL:         {phase2_summary['n_fail']}")
    print(f"    INCONCLUSIVE: {phase2_summary['n_inconclusive']}")
    print(f"    ERROR:        {phase2_summary['n_error']}")
    print(f"  JSONs emitted: {len(phase2_summary['emitted_files'])}")
    print(f"  Total elapsed: {elapsed_total:.1f}s "
          f"({elapsed_total/60.0:.1f} min)")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
