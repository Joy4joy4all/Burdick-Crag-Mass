"""
Run Record — JSON Tracking Engine (Writer + Reader)
====================================================
Stephen Justin Burdick, 2026 — Emerald Entities LLC

Standardizes every solver run into a structured JSON record.
Every run gets: full pipeline description, parameters, results,
galaxy properties, and optional notes/parent tracking.

Usage (writer):
    from core.run_record import make_run_record, save_run_record, save_batch_records

Usage (reader):
    from core.run_record import load_all_records

Schema version: 1
"""

import os
import json
import uuid
import time
import numpy as np

SCHEMA_VERSION = 1


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def mass_bracket(v_max):
    """Classify galaxy by max observed velocity."""
    if v_max < 50:
        return "dwarf"
    elif v_max < 100:
        return "low"
    elif v_max < 150:
        return "mid"
    elif v_max < 200:
        return "high"
    else:
        return "massive"


def _safe_float(val, default=0.0):
    """Convert to float safely."""
    try:
        f = float(val)
        return f if np.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _detect_observable(solver_config):
    """
    Infer which observable (psi mapping) was used from solver config.
    The solver stores field_mode in its config dict.
    """
    mode = solver_config.get("field_mode", "unknown")
    mapping = {
        "rho_sq_poisson":     "Poisson(rho^2)",
        "neg_sigma":          "-sigma",
        "neg_rho":            "-rho",
        "sigma_times_rho":    "-(sigma*|rho|)",
        "poisson_rho_sq_grad": "Poisson(rho^2+grad^2)",
        "unknown":            "unknown",
    }
    return mapping.get(mode, mode)


def _build_chain_string(observable, lam):
    """Human-readable pipeline chain."""
    obs_map = {
        "Poisson(rho^2)":       "J → wave(λ) → ρ → ρ² → Poisson(ρ²) → Ψ → ∇Ψ → V",
        "-sigma":               "J → wave(λ) → ρ → Σ → -Σ → Ψ → ∇Ψ → V",
        "-rho":                 "J → wave(λ) → ρ → -ρ → Ψ → ∇Ψ → V",
        "-(sigma*|rho|)":       "J → wave(λ) → ρ → Σ·|ρ| → -Σ·|ρ| → Ψ → ∇Ψ → V",
        "Poisson(rho^2+grad^2)":"J → wave(λ) → ρ → ρ²+∇ρ² → Poisson → Ψ → ∇Ψ → V",
    }
    chain = obs_map.get(observable, f"J → wave(λ={lam}) → ρ → [?] → Ψ → V")
    return chain


# ─────────────────────────────────────────
# MAKE A RUN RECORD
# ─────────────────────────────────────────

def make_run_record(galaxy_data, solver_result, comp=None,
                    solver_config=None, notes="",
                    parent_run_id=None, changed_from_parent=None):
    """
    Build a complete, structured run record from solver outputs.

    Args:
        galaxy_data:     dict from sparc_ingest.load_galaxy()
        solver_result:   dict from SubstrateSolver.run()
        comp:            dict from rotation_compare.compare_rotation() — optional
        solver_config:   dict of solver parameters (grid, layers, lam, etc.)
                         Falls back to solver_result["config"] if None.
        notes:           free text — what was being tested, why
        parent_run_id:   run_id of previous run if iterating
        changed_from_parent: list of param names that changed

    Returns:
        dict — the full run record
    """
    cfg = solver_config or solver_result.get("config", {})
    lam = cfg.get("lam", cfg.get("lambda", 0.0))
    observable = _detect_observable(cfg)
    chain = _build_chain_string(observable, lam)

    v_max = float(np.max(galaxy_data["vobs"])) if len(galaxy_data["vobs"]) > 0 else 0.0
    r_max = float(np.max(galaxy_data["radii_kpc"])) if len(galaxy_data["radii_kpc"]) > 0 else 0.0
    n_pts = int(len(galaxy_data["radii_kpc"]))

    # ── Field results (always present) ──
    results = {
        "corr_full":      _safe_float(solver_result.get("corr_full")),
        "corr_inner":     _safe_float(solver_result.get("corr_radial_inner")),
        "corr_radial_full": _safe_float(solver_result.get("corr_radial_full")),
        "corr_lap":       _safe_float(solver_result.get("corr_lap")),
        "layer_coherence": _safe_float(solver_result.get("layer_coherence")),
        "psi_max":        _safe_float(solver_result.get("psi_max")),
        "rho_max":        _safe_float(solver_result.get("rho_max")),
        "elapsed":        _safe_float(solver_result.get("elapsed")),
    }

    # ── Rotation curve results (present if comp was run) ──
    if comp is not None:
        results.update({
            "rms_newton":         _safe_float(comp.get("rms_newton")),
            "rms_mond":           _safe_float(comp.get("rms_mond")),
            "rms_substrate":      _safe_float(comp.get("rms_substrate")),
            "corr_newton_shape":  _safe_float(comp.get("corr_newton")),
            "corr_mond_shape":    _safe_float(comp.get("corr_mond")),
            "corr_substrate_shape": _safe_float(comp.get("corr_substrate")),
            "outer_rms_newton":   _safe_float(comp.get("outer_rms_newton")),
            "outer_rms_mond":     _safe_float(comp.get("outer_rms_mond")),
            "outer_rms_substrate": _safe_float(comp.get("outer_rms_substrate")),
            "winner":             comp.get("winner", "UNKNOWN"),
            "outer_winner":       comp.get("outer_winner", "UNKNOWN"),
            "sub_vs_newton":      _safe_float(comp.get("sub_vs_newton")),
            "sub_vs_mond":        _safe_float(comp.get("sub_vs_mond")),
        })
    else:
        results.update({
            "rms_newton": None, "rms_mond": None, "rms_substrate": None,
            "winner": None, "outer_winner": None,
        })

    record = {
        "schema_version": SCHEMA_VERSION,
        "run_id":         str(uuid.uuid4()),
        "timestamp":      time.strftime("%Y-%m-%dT%H:%M:%S"),

        "galaxy": galaxy_data.get("name", "unknown"),

        "parameters": {
            "grid":      int(cfg.get("grid", 0)),
            "layers":    int(cfg.get("layers", 0)),
            "lambda":    float(lam),
            "gamma":     float(cfg.get("gamma", 0.05)),
            "entangle":  float(cfg.get("entangle", 0.02)),
            "c_wave":    float(cfg.get("c_wave", 1.0)),
            "settle":    int(cfg.get("settle", 0)),
            "measure":   int(cfg.get("measure", 0)),
        },

        "pipeline": {
            "source":        "baryonic_only (Vgas²+Vdisk²+Vbul²)/r",
            "engine":        "damped_wave_multilayer",
            "observable":    observable,
            "chain":         chain,
            "normalization": "per_galaxy_peak",
            "boundary":      "absorbing_edge_10",
        },

        "results": results,

        "galaxy_properties": {
            "v_max":        v_max,
            "r_max":        r_max,
            "n_points":     n_pts,
            "mass_bracket": mass_bracket(v_max),
        },

        "notes":               notes,
        "parent_run":          parent_run_id,
        "changed_from_parent": changed_from_parent or [],
    }

    return record


# ─────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────

def save_run_record(record, results_dir):
    """Save a single run record. Returns the file path."""
    os.makedirs(results_dir, exist_ok=True)
    galaxy = record.get("galaxy", "unknown")
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(results_dir, f"run_{galaxy}_{ts}.json")
    with open(path, "w") as f:
        json.dump(record, f, indent=2)
    return path


def save_batch_records(records, results_dir, notes=""):
    """
    Save a list of run records as a batch file.
    Also saves a batch-level summary alongside it.
    Returns the file path.
    """
    os.makedirs(results_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    # Batch file: array of full records
    path = os.path.join(results_dir, f"batch_{ts}.json")
    with open(path, "w") as f:
        json.dump(records, f, indent=2)

    # Summary alongside: quick stats without the full records
    summary = _build_batch_summary(records, notes)
    summary_path = os.path.join(results_dir, f"batch_{ts}_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    return path


def _build_batch_summary(records, notes=""):
    """Compute batch-level stats for the summary file."""
    total = len(records)
    with_rms = [r for r in records if r.get("results", {}).get("rms_newton") is not None]

    summary = {
        "schema_version":  SCHEMA_VERSION,
        "timestamp":       time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_galaxies":  total,
        "with_rotation":   len(with_rms),
        "notes":           notes,
        "parameters":      records[0]["parameters"] if records else {},
        "pipeline":        records[0]["pipeline"] if records else {},
    }

    if with_rms:
        winners = [r["results"]["winner"] for r in with_rms]
        outer_w = [r["results"]["outer_winner"] for r in with_rms]
        rms_n =   [r["results"]["rms_newton"]   for r in with_rms]
        rms_m =   [r["results"]["rms_mond"]     for r in with_rms]
        rms_s =   [r["results"]["rms_substrate"] for r in with_rms]

        summary["wins"] = {
            "SUBSTRATE": winners.count("SUBSTRATE"),
            "NEWTON":    winners.count("NEWTON"),
            "MOND":      winners.count("MOND"),
            "TIE":       winners.count("TIE"),
        }
        summary["outer_wins"] = {
            "SUBSTRATE": outer_w.count("SUBSTRATE"),
            "NEWTON":    outer_w.count("NEWTON"),
            "MOND":      outer_w.count("MOND"),
            "TIE":       outer_w.count("TIE"),
        }
        summary["avg_rms"] = {
            "newton":    float(np.mean(rms_n)),
            "mond":      float(np.mean(rms_m)),
            "substrate": float(np.mean(rms_s)),
        }

        # Wins by mass bracket
        brackets = ["dwarf", "low", "mid", "high", "massive"]
        bracket_stats = {}
        for b in brackets:
            subset = [r for r in with_rms
                      if r.get("galaxy_properties", {}).get("mass_bracket") == b]
            if subset:
                bw = [r["results"]["winner"] for r in subset]
                bracket_stats[b] = {
                    "n": len(subset),
                    "substrate_wins": bw.count("SUBSTRATE"),
                    "newton_wins":    bw.count("NEWTON"),
                    "mond_wins":      bw.count("MOND"),
                    "avg_rms_substrate": float(np.mean([r["results"]["rms_substrate"] for r in subset])),
                    "avg_rms_newton":    float(np.mean([r["results"]["rms_newton"]    for r in subset])),
                }
        summary["by_mass_bracket"] = bracket_stats

    corr_inners = [r["results"]["corr_inner"] for r in records
                   if r.get("results", {}).get("corr_inner") is not None]
    if corr_inners:
        summary["avg_corr_inner"] = float(np.mean(corr_inners))
        summary["pct_above_090"] = float(sum(1 for c in corr_inners if c > 0.90) / len(corr_inners))
        summary["pct_above_095"] = float(sum(1 for c in corr_inners if c > 0.95) / len(corr_inners))

    return summary


# ─────────────────────────────────────────
# LOAD ALL RECORDS
# ─────────────────────────────────────────

def load_all_records(results_dir):
    """
    Load every JSON file in results_dir.
    Handles both single run files and batch files (arrays).
    Skips summary files.
    Returns flat list of run records sorted by timestamp.
    """
    if not os.path.exists(results_dir):
        return []

    records = []
    for fname in os.listdir(results_dir):
        if not fname.endswith(".json"):
            continue
        if "_summary" in fname:
            continue  # skip summary files
        path = os.path.join(results_dir, fname)
        try:
            with open(path) as f:
                data = json.load(f)
            # Batch file = list; single run = dict
            if isinstance(data, list):
                # Legacy batch format (no schema_version): upgrade on the fly
                for entry in data:
                    records.append(_normalize_legacy(entry, fname))
            elif isinstance(data, dict):
                records.append(_normalize_legacy(data, fname))
        except Exception as e:
            pass  # silently skip corrupt files

    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records


def _normalize_legacy(entry, source_file):
    """
    Upgrade old batch entries (flat dict with just RMS fields)
    to the current schema so the reader always sees consistent structure.
    """
    # Already current schema
    if entry.get("schema_version") == SCHEMA_VERSION:
        entry["_source_file"] = source_file
        return entry

    # Legacy: flat dict like {"galaxy": "NGC2403", "rms_newton": 37.9, ...}
    galaxy = entry.get("galaxy", "unknown")
    v_max  = entry.get("v_max", 0.0)

    normalized = {
        "schema_version": 0,  # marks as legacy
        "run_id":    entry.get("run_id", str(uuid.uuid4())),
        "timestamp": entry.get("timestamp", ""),
        "galaxy":    galaxy,
        "parameters": {
            "grid":    entry.get("grid", None),
            "layers":  entry.get("layers", None),
            "lambda":  entry.get("lambda", None),
            "gamma":   None, "entangle": None, "c_wave": None,
            "settle":  None, "measure":  None,
        },
        "pipeline": {
            "observable": entry.get("observable", "unknown"),
            "chain":      entry.get("chain", "unknown"),
        },
        "results": {
            "corr_full":          entry.get("corr_full"),
            "corr_inner":         entry.get("corr_inner"),
            "rms_newton":         entry.get("rms_newton"),
            "rms_mond":           entry.get("rms_mond"),
            "rms_substrate":      entry.get("rms_substrate"),
            "corr_newton_shape":  entry.get("corr_newton_shape"),
            "corr_mond_shape":    entry.get("corr_mond_shape"),
            "corr_substrate_shape": entry.get("corr_substrate_shape"),
            "winner":             entry.get("winner"),
            "outer_winner":       entry.get("outer_winner"),
            "sub_vs_newton":      entry.get("sub_vs_newton"),
            "sub_vs_mond":        entry.get("sub_vs_mond"),
            "elapsed":            entry.get("elapsed"),
        },
        "galaxy_properties": {
            "v_max":        v_max,
            "r_max":        entry.get("r_max", 0.0),
            "n_points":     entry.get("n_points", 0),
            "mass_bracket": mass_bracket(v_max),
        },
        "notes": "",
        "_source_file": source_file,
        "_legacy": True,
    }
    return normalized
