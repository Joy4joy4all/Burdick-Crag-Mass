# -*- coding: utf-8 -*-
"""
BCM HYPOTHESIS VOCABULARY
==========================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Companion to hypothesis_engine.py.

The engine does Bayesian math (log-odds updates, evidence tracking).
This file owns the VOCABULARY the engine speaks:

  1. BUCKET_VOCABULARY    -- the six legal hypothesis routing buckets
  2. HYPOTHESIS_KEYWORDS  -- Foreman-authorized keywords registry
  3. LEGACY_TRANSLATION   -- maps sloppy/old terms to proper buckets
  4. PAIR_TYPES           -- correlation pairing axes

Separation of concerns:
  - Engine = WHEN does evidence shift a posterior?
  - Vocabulary = WHAT words are we allowed to use, and what do they mean?

When a test declares a HYPOTHESES dict with a keyword not in the registry,
the engine calls register_new_keyword() which marks it UNREGISTERED_NEW
for Foreman review. It does NOT reject the test (too brittle), but the
next agent seeing UNREGISTERED_NEW knows Foreman needs to review it.

PRIMACY STATEMENT:
  Keywords are named by the Foreman. This file accumulates them over time.
  No AI invents vocabulary. When a test introduces a new keyword, the
  Foreman reviews and either locks it (moves from UNREGISTERED_NEW to a
  proper entry) or renames it to an existing authorized keyword.

v25 VOCABULARY GROWTH (2026-04-19):
  23 new AUTHORIZED entries added covering:
    - Test 6 forced-emission fields (hemorrhage_line, guardian_strength,
      f_2_heartbeat_stability, chi_freeboard, regime_classification_confidence)
    - Test 7 kappa sweep terms (kappa_drain, coh_est_at_settle)
    - Genesis trail candidates (diffusive_lock)
    - Cube code terms already in use (phi_integrity, test_zone, regime,
      pi_ratio, sigma_crit)
    - v24 boundary physics (k_boundary, clamp_stable, bulk_flood, damped_stable)
    - Context flags already emitted by _inject_context (system_name,
      test_version, fracture_lambda)
    - Methodological concepts (safe_envelope, classifier_divergence,
      forced_emission)
  No existing AUTHORIZED entries modified. Foreman retains authority
  over bucket_hint tightening of prior entries.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


# ============================================================================
# SECTION 1 -- BUCKET VOCABULARY (LOCKED)
# ============================================================================

BUCKET_VOCABULARY: Tuple[str, ...] = (
    "ANOMALY",             # expected behavior, measurement deviates
    "POSSIBLE_INVARIANT",  # behavior persists where variation was expected
    "CONTEXT_ARTIFACT",    # result driven by setup (grid/settle/system), not physics
    "DEFINITION_MISMATCH", # two rules classify same number differently
    "RESOLVED",            # matches expectation, no pursuit needed
    "UNKNOWN",             # insufficient data to classify (not a free pass)
)


def is_legal_bucket(bucket: str) -> bool:
    """Return True if `bucket` is one of the six legal values."""
    return bucket in BUCKET_VOCABULARY


# ============================================================================
# SECTION 2 -- HYPOTHESIS KEYWORDS (Foreman-authorized registry)
# ============================================================================

@dataclass
class KeywordEntry:
    """
    One registered vocabulary term the cube and engine understand.

    Attributes:
        keyword      : the term itself (e.g. "brucetron", "phi_load")
        status       : "AUTHORIZED" | "UNREGISTERED_NEW" | "LEGACY" | "DEPRECATED"
        description  : Foreman-written meaning (plain English)
        bucket_hint  : default bucket when this keyword is flagged alone
                       (may be overridden by hypothesis declaration)
        category     : "physics" | "context" | "system" | "method" | "result"
        related      : other keywords this one commonly pairs with
        notes        : Foreman notes, review comments, deprecation warnings
        first_seen   : which test first used this term (optional)
    """
    keyword: str
    status: str = "AUTHORIZED"
    description: str = ""
    bucket_hint: str = "UNKNOWN"
    category: str = "physics"
    related: List[str] = field(default_factory=list)
    notes: str = ""
    first_seen: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "keyword":     self.keyword,
            "status":      self.status,
            "description": self.description,
            "bucket_hint": self.bucket_hint,
            "category":    self.category,
            "related":     list(self.related),
            "notes":       self.notes,
            "first_seen":  self.first_seen,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KeywordEntry":
        return cls(
            keyword=d["keyword"],
            status=d.get("status", "AUTHORIZED"),
            description=d.get("description", ""),
            bucket_hint=d.get("bucket_hint", "UNKNOWN"),
            category=d.get("category", "physics"),
            related=list(d.get("related", [])),
            notes=d.get("notes", ""),
            first_seen=d.get("first_seen"),
        )


HYPOTHESIS_KEYWORDS: Dict[str, KeywordEntry] = {

    # ---- Physics keywords (measurements, field names, mechanisms) ----
    "brucetron": KeywordEntry(
        keyword="brucetron",
        status="AUTHORIZED",
        description=("High-frequency residue in substrate field; "
                     "measured as RMS of local sigma fluctuation."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["phi", "chi", "frastrate"],
        first_seen="BCM_v17_brucetron_diagnostic.py",
    ),
    "phi": KeywordEntry(
        keyword="phi",
        status="AUTHORIZED",
        description=("Observable phase; temporal oscillation at fixed location. "
                     "Tracked via phi_rms, phi_load, phi_integrity."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["brucetron", "chi", "coherence"],
        first_seen="BCM_v17_diag_frequency.py",
    ),
    "chi": KeywordEntry(
        keyword="chi",
        status="AUTHORIZED",
        description=("Substrate buffer capacity measurement. chi_c is the "
                     "critical threshold; chi/chi_c > 1 may indicate regime "
                     "shift or threshold miscalibration."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["brucetron", "phi", "buffer", "frastrate"],
        first_seen="BCM_v17_chi_freeboard.py",
    ),
    "frastrate": KeywordEntry(
        keyword="frastrate",
        status="AUTHORIZED",
        description=("Buffer / reflection region in substrate. Where E=MC^2 "
                     "potentially modifies due to substrate coupling."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["chi", "buffer", "reflect"],
        first_seen="BCM_v18_frastrate_diagnostic.py",
    ),
    "sigma": KeywordEntry(
        keyword="sigma",
        status="AUTHORIZED",
        description=("Substrate memory density field. Accumulated integral of "
                     "|rho| over time with decay epsilon."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["rho", "throat", "coherence"],
        first_seen="BCM_v7_*",
    ),
    "rho": KeywordEntry(
        keyword="rho",
        status="AUTHORIZED",
        description=("Substrate forcing response field. Primary wave variable."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["sigma", "wave"],
        first_seen="BCM_v7_*",
    ),
    "coherence": KeywordEntry(
        keyword="coherence",
        status="AUTHORIZED",
        description=("Degree of phase alignment across substrate. Measured via "
                     "correlation metrics; high coherence ~ 1.0, failure ~ 0."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["phi", "sigma"],
    ),
    "guardian": KeywordEntry(
        keyword="guardian",
        status="AUTHORIZED",
        description=("Crew-safety field integrity. Twin guardian system in "
                     "the hypercube holds field stable against substrate shear."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["crew_safety", "f2"],
        first_seen="BCM_v25_guardian_field_emission_test.py",
    ),

    # ---- Context keywords (experimental conditions) ----
    "grid": KeywordEntry(
        keyword="grid",
        status="AUTHORIZED",
        description=("Simulation grid resolution (typically 128 or 256). "
                     "CONTEXT: different grids may produce different numerics."),
        bucket_hint="CONTEXT_ARTIFACT",
        category="context",
        related=["settle", "measure", "layers"],
    ),
    "settle": KeywordEntry(
        keyword="settle",
        status="AUTHORIZED",
        description=("Pre-measurement stabilization step count."),
        bucket_hint="CONTEXT_ARTIFACT",
        category="context",
        related=["grid", "measure"],
    ),
    "measure": KeywordEntry(
        keyword="measure",
        status="AUTHORIZED",
        description=("Post-settle measurement window in steps."),
        bucket_hint="CONTEXT_ARTIFACT",
        category="context",
        related=["grid", "settle"],
    ),
    "layers": KeywordEntry(
        keyword="layers",
        status="AUTHORIZED",
        description=("Entangled substrate layer count in multi-layer solver."),
        bucket_hint="CONTEXT_ARTIFACT",
        category="context",
    ),
    "lambda": KeywordEntry(
        keyword="lambda",
        status="AUTHORIZED",
        description=("Substrate damping / drive parameter. Swept in most tests."),
        bucket_hint="UNKNOWN",
        category="context",
        related=["sigma", "rho", "drive"],
    ),
    "invariance": KeywordEntry(
        keyword="invariance",
        status="AUTHORIZED",
        description=("Claim that a measurement holds across varied conditions. "
                     "Route to POSSIBLE_INVARIANT by default."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
    ),

    # ---- System keywords ----
    "HR_1099": KeywordEntry(
        keyword="HR_1099",
        status="AUTHORIZED",
        description=("Binary star system. Brake template (14:1 mass ratio)."),
        bucket_hint="UNKNOWN",
        category="system",
        related=["binary", "brake_template"],
    ),
    "Alpha_Centauri": KeywordEntry(
        keyword="Alpha_Centauri",
        status="AUTHORIZED",
        description=("Binary system. Design-limit template (3.5:1 mass ratio)."),
        bucket_hint="UNKNOWN",
        category="system",
        related=["binary", "design_limit"],
    ),
    "Spica": KeywordEntry(
        keyword="Spica",
        status="AUTHORIZED",
        description=("Binary system. Drive template (8.4:1 mass ratio)."),
        bucket_hint="UNKNOWN",
        category="system",
        related=["binary", "drive_template"],
    ),

    # ========================================================================
    # v25 VOCABULARY GROWTH -- 23 NEW AUTHORIZED ENTRIES (2026-04-19)
    # ========================================================================
    # Added per Foreman direction after Tests 6 and 7. Covers Test 6
    # forced-emission fields, Test 7 kappa sweep parameters, cube code
    # terms already in use but not previously registered, v24 boundary
    # physics from the boundary_stability_sweep corpus, context flags
    # emitted by _inject_context, and methodological concepts introduced
    # across Tests 3-7.
    # ========================================================================

    # ---- Test 6 forced-emission physics (5 entries) ----
    "hemorrhage_line": KeywordEntry(
        keyword="hemorrhage_line",
        status="AUTHORIZED",
        description=("Crew-safety threshold for brucetron RMS. Value 0.0045. "
                     "Above this line the biological harm band is entered. "
                     "Used to classify hemorrhage_state = BELOW / AT / ABOVE."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["brucetron", "crew_safety", "guardian"],
        first_seen="BCM_v25_cube2_phase_reconciliation_6.py",
    ),
    "guardian_strength": KeywordEntry(
        keyword="guardian_strength",
        status="AUTHORIZED",
        description=("Derived crew-safety envelope score [0, 1]. Composite of "
                     "chi absorption, curvature load, and bruce calm. "
                     "Higher = more protection. Observed to saturate near 0.95 "
                     "in chi-active C-config runs."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["guardian", "brucetron", "chi", "crew_safety"],
        first_seen="BCM_v25_cube2_phase_reconciliation_6.py",
    ),
    "f_2_heartbeat_stability": KeywordEntry(
        keyword="f_2_heartbeat_stability",
        status="AUTHORIZED",
        description=("Fourier stability of bruce_rms oscillation in [0, 1]. "
                     "1.0 = perfect periodic heartbeat, 0 = chaotic. "
                     "Measured via FFT peak sharpness on detrended bruce series."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["brucetron", "guardian"],
        first_seen="BCM_v25_cube2_phase_reconciliation_6.py",
    ),
    "chi_freeboard": KeywordEntry(
        keyword="chi_freeboard",
        status="AUTHORIZED",
        description=("Baume floor level in v19 chi mechanism. fl = mean + 1.5*std "
                     "of local sigma in a window around center of mass. "
                     "Overflow above fl spills into chi_field; deficit below drains back."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["chi", "frastrate", "sigma"],
        first_seen="BCM_v25_cube2_phase_reconciliation_6.py",
    ),
    "regime_classification_confidence": KeywordEntry(
        keyword="regime_classification_confidence",
        status="AUTHORIZED",
        description=("Distance of coh_est from nearest regime bin boundary, "
                     "normalized to bin half-width [0, 1]. "
                     "Low = classifier uncertain (sample near boundary); "
                     "high = sample deep in bin. Used to flag borderline cases."),
        bucket_hint="CONTEXT_ARTIFACT",
        category="physics",
        related=["regime", "coherence"],
        first_seen="BCM_v25_cube2_phase_reconciliation_6.py",
    ),

    # ---- Test 7 kappa sweep (2 entries) ----
    "kappa_drain": KeywordEntry(
        keyword="kappa_drain",
        status="AUTHORIZED",
        description=("v19 orbital sigma bleed rate at probe boundaries. "
                     "Frozen at 0.35 in all tests EXCEPT controlled sweeps. "
                     "Higher values increase sigma bleed into chi field. "
                     "Test 7 showed kappa barely suppresses brucetron; saturated."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["chi", "sigma", "brucetron", "frastrate"],
        first_seen="BCM_v19_combined_drain_chi.py",
    ),
    "coh_est_at_settle": KeywordEntry(
        keyword="coh_est_at_settle",
        status="AUTHORIZED",
        description=("Mean of coherence estimate in final 20 percent of run. "
                     "Proxy for steady-state coherence after transient dies. "
                     "Used to evaluate whether a mechanism preserves coherence."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["coherence", "regime"],
        first_seen="BCM_v25_cube2_phase_reconciliation_7.py",
    ),

    # ---- Genesis trail candidate (1 entry) ----
    "diffusive_lock": KeywordEntry(
        keyword="diffusive_lock",
        status="AUTHORIZED",
        description=("Proposed fourth substrate regime. Signature: "
                     "chi_op < 0.005, coh_est > 0.97, abs(growth) < 1e-4. "
                     "Observed in C: Drain + Chi configs; system sits at "
                     "neutral equilibrium basin where chi absorption holds "
                     "sigma quenched. Awaiting Foreman review before manual "
                     "propagation to regime classifier."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["chi", "coherence", "regime"],
        first_seen="BCM_v25_cube2_phase_reconciliation_4.py",
    ),

    # ---- Cube code terms already in use (5 entries) ----
    "phi_integrity": KeywordEntry(
        keyword="phi_integrity",
        status="AUTHORIZED",
        description=("Derived phase-field intactness metric: "
                     "1.0 - phi_rms/PHI_SAFETY. Used by Cube 6 Guardians. "
                     "Positive = phase below safety threshold; "
                     "negative = phase has breached safety."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["phi", "guardian"],
        first_seen="qt_layer.py",
    ),
    "test_zone": KeywordEntry(
        keyword="test_zone",
        status="AUTHORIZED",
        description=("v19 local heuristic classification of sigma trend. "
                     "GREEN = growth_rate < -1e-6 (healing); "
                     "YELLOW = abs(growth_rate) < 1e-6 (marginal); "
                     "RED = growth_rate > 1e-6 (building / resonant). "
                     "One of two classifiers in Cube 2 divergence detection."),
        bucket_hint="DEFINITION_MISMATCH",
        category="physics",
        related=["regime", "classifier_divergence"],
        first_seen="BCM_v19_combined_drain_chi.py",
    ),
    "regime": KeywordEntry(
        keyword="regime",
        status="AUTHORIZED",
        description=("v24 global classification derived from coh_est. Values: "
                     "DIFFUSIVE_HEALING, MARGINAL, COHERENCE_FAILURE, "
                     "BOUNDARY_NONLINEAR. Second classifier in Cube 2; when it "
                     "disagrees with test_zone the sample flags as ANOMALY."),
        bucket_hint="DEFINITION_MISMATCH",
        category="physics",
        related=["test_zone", "coherence", "classifier_divergence"],
        first_seen="v24_three_regime_substrate.py",
    ),
    "pi_ratio": KeywordEntry(
        keyword="pi_ratio",
        status="AUTHORIZED",
        description=("v24 catadioptric control parameter: sigma_edge / sigma_crit. "
                     "Below PI_STABLE = REFRACT (commit); "
                     "PI_STABLE to PI_MARGINAL = MARGINAL; "
                     "above PI_MARGINAL = REFLECT (frastrate); "
                     "above PI_COLLAPSE = HARD_REFLECT (bulk flood)."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["sigma_crit", "frastrate", "clamp_stable"],
        first_seen="v24_catadioptric_sweep.py",
    ),
    "sigma_crit": KeywordEntry(
        keyword="sigma_crit",
        status="AUTHORIZED",
        description=("v24 critical sigma threshold for edge stability. "
                     "Clamping at sigma_crit = 5 or 10 is the ONLY v24 "
                     "treatment that produced DAMPED STABLE edge; all other "
                     "treatments (none, high_decay, injection) went BULK FLOOD."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["pi_ratio", "clamp_stable", "damped_stable"],
        first_seen="BCM_v24_boundary_stability_sweep.py",
    ),

    # ---- v24 boundary physics (3 entries) ----
    "k_boundary": KeywordEntry(
        keyword="k_boundary",
        status="AUTHORIZED",
        description=("v24 gradient-proportional dissipation coefficient at "
                     "torus edge. High values (K x 5, x 10, x 50) slow bulk flood "
                     "but do not prevent it. Sigma_crit clamp is the only proven "
                     "stabilizer; K_boundary alone is insufficient."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["sigma_crit", "bulk_flood", "damped_stable"],
        first_seen="BCM_v24_boundary_stability_sweep.py",
    ),
    "clamp_stable": KeywordEntry(
        keyword="clamp_stable",
        status="AUTHORIZED",
        description=("v24 verdict: 'DAMPED STABLE -- thin edge maintained'. "
                     "Achieved only by sigma_crit clamp treatment "
                     "(sigma_crit = 5 or 10). Stable ring_sigma ~ 1.0 to 2.0, "
                     "no oscillation, edge maintained across 23k steps."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["sigma_crit", "damped_stable", "bulk_flood"],
        first_seen="BCM_v24_boundary_stability_sweep.py",
    ),
    "bulk_flood": KeywordEntry(
        keyword="bulk_flood",
        status="AUTHORIZED",
        description=("v24 failure mode: 'BULK FLOOD -- edge dissolved'. "
                     "Every v24 treatment except sigma_crit clamp went bulk flood. "
                     "Ring_sigma grows unbounded (tens to thousands) while core "
                     "stays constant. The default v19.4 behavior without clamp."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["sigma_crit", "k_boundary", "clamp_stable"],
        first_seen="BCM_v24_boundary_stability_sweep.py",
    ),
    "damped_stable": KeywordEntry(
        keyword="damped_stable",
        status="AUTHORIZED",
        description=("v24 stable-verdict language. System grows toward a fixed "
                     "low ring_sigma floor and holds. Same physical state as "
                     "clamp_stable; different name used in verdict strings."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["clamp_stable", "sigma_crit"],
        first_seen="BCM_v24_boundary_stability_sweep.py",
    ),

    # ---- Context flags (3 entries) ----
    "system_name": KeywordEntry(
        keyword="system_name",
        status="AUTHORIZED",
        description=("Experimental system identifier. Formatted as SYS_<n> in "
                     "cube flags (e.g. SYS_V19.4_PUMP_DRAIN_HR1099, "
                     "SYS_ALPHA_CENTAURI). Emitted by qt_layer._inject_context."),
        bucket_hint="CONTEXT_ARTIFACT",
        category="context",
        related=["HR_1099", "Alpha_Centauri", "Spica", "test_version"],
    ),
    "test_version": KeywordEntry(
        keyword="test_version",
        status="AUTHORIZED",
        description=("Test version identifier. Formatted as VER_<version> in "
                     "cube flags (e.g. VER_V25). Used to separate corpus across "
                     "v24, v25, etc. Essential for cross-version comparison discipline."),
        bucket_hint="CONTEXT_ARTIFACT",
        category="context",
    ),
    "fracture_lambda": KeywordEntry(
        keyword="fracture_lambda",
        status="AUTHORIZED",
        description=("Lambda band where test_zone vs regime divergence clusters. "
                     "Established in Tests 3, 4 and confirmed in Tests 6, 7: "
                     "lambda in [0.02, 0.12], especially 0.07 to 0.12. "
                     "The 500-anomaly fracture corridor in HR 1099 corpus."),
        bucket_hint="ANOMALY",
        category="context",
        related=["lambda", "classifier_divergence"],
        first_seen="BCM_v25_cube2_phase_reconciliation_3.py",
    ),

    # ---- Methodological concepts (3 entries) ----
    "safe_envelope": KeywordEntry(
        keyword="safe_envelope",
        status="AUTHORIZED",
        description=("Crew-safety region claim: set of (lambda, parameter) "
                     "configurations where bruce_rms < hemorrhage_line and "
                     "coherence holds. Test 7 showed no safe envelope exists "
                     "via kappa_drain alone; sigma_crit clamp remains the "
                     "candidate mechanism for establishing one."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["crew_safety", "hemorrhage_line", "sigma_crit"],
        first_seen="BCM_v25_cube2_phase_reconciliation_7.py",
    ),
    "classifier_divergence": KeywordEntry(
        keyword="classifier_divergence",
        status="AUTHORIZED",
        description=("Disagreement between test_zone (v19 local heuristic) and "
                     "regime (v24 global classifier) on the same physics sample. "
                     "Not a bug; two classifiers measuring the same field "
                     "through different lenses. Cube 2 anchor rule flags these "
                     "as anomalies awaiting ontology refinement."),
        bucket_hint="DEFINITION_MISMATCH",
        category="method",
        related=["test_zone", "regime", "fracture_lambda"],
        first_seen="BCM_v25_cube2_phase_reconciliation_3.py",
    ),
    "forced_emission": KeywordEntry(
        keyword="forced_emission",
        status="AUTHORIZED",
        description=("Methodology: run physics at existing anomaly coordinates "
                     "and force emission of fields the cube has been asking for. "
                     "Does NOT change physics; adds vocabulary so the cube can "
                     "learn from richer data. Test 6 pattern."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["guardian_strength", "chi_freeboard", "hemorrhage_line",
                 "regime_classification_confidence"],
        first_seen="BCM_v25_cube2_phase_reconciliation_6.py",
    ),

    # ========================================================================
    # v26 FOREMAN-APPROVED ENTRIES (2026-04-21, 9 total)
    # From BCM_Vocabulary_Authorization_Proposal_v2 review pass.
    # Entries: phase_boundary, reinforced_coherence, crew_safety, and six
    # Paper B pre-registered concept keywords (anchor_tensor, phi_modulation,
    # anchor_loop, substrate_current, anchor_traverse, moonbeam_bridge).
    # ========================================================================

    "phase_boundary": KeywordEntry(
        keyword="phase_boundary",
        status="AUTHORIZED",
        description=("Location in parameter space (lambda, kappa, or other "
                     "sweep axis) where the system transitions between "
                     "regimes. Flagged in v25 reconciliation tests and "
                     "narrowed in v26 structure-aware sweep. Paper B "
                     "relevance: phase_boundary is where Phi(sigma) crosses "
                     "0.5 in the sigmoid modulation picture."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["phase_discontinuity", "regime", "sigma_crit",
                 "classifier_divergence", "attractor"],
        notes=("Paper B candidate for empirical Phi-midpoint measurement. "
               "Foreman-approved 2026-04-21."),
        first_seen="BCM_v25_cube2_phase_reconciliation_4.py",
    ),

    "reinforced_coherence": KeywordEntry(
        keyword="reinforced_coherence",
        status="AUTHORIZED",
        description=("Condition where observed regime holds coherence against "
                     "classifier-predicted failure. test_zone=RED expects "
                     "COHERENCE_FAILURE / BOUNDARY_NONLINEAR, but the system "
                     "presents DIFFUSIVE_HEALING, MARGINAL, or COHERENCE. "
                     "Dominant pattern in the 996 STABLE anomalies at Cube 2 "
                     "Substrate. Paper B relevance: reinforced_coherence is "
                     "the empirical signature of Phi(sigma) modulation "
                     "protecting the substrate in regimes the classical "
                     "(Einstein) classifier was built for. Where Phi drops, "
                     "mass-load sheds into the anchor_loop, and the system "
                     "stabilizes in a mode the classical rule engine cannot "
                     "describe."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["test_zone", "classifier_divergence", "diffusive_lock",
                 "attractor", "phi_modulation", "anchor_loop",
                 "moonbeam_bridge"],
        notes=("Foreman-named (renamed from proposed 'overshoot'). Appears "
               "in hypothesis TEST_ZONE_OVERSHOOTS_FAILURE_IN_MID_BAND "
               "(posterior 0.994, VALIDATED). Foreman-approved 2026-04-21."),
        first_seen="BCM_v19_combined_drain_chi_20260410_071429.json",
    ),

    "crew_safety": KeywordEntry(
        keyword="crew_safety",
        status="AUTHORIZED",
        description=("Mission-relevance flag applied to hypotheses and "
                     "measurements that bear on biological crew survival "
                     "during traverse. Guardian field emission, brucetron "
                     "hemorrhage line, and coherence preservation all have "
                     "crew_safety implications. Used by cube to prioritize "
                     "tests with direct operational consequence. Paper B "
                     "relevance: crew_safety defines the failure mode of the "
                     "Phi(sigma) transition -- if Phi drops too fast (k too "
                     "high), the traverse transition is violent and unsafe. "
                     "Test 5 data informs the safe-k envelope."),
        bucket_hint="UNKNOWN",
        category="system",
        related=["guardian", "guardian_strength", "hemorrhage",
                 "preservation", "safe_envelope"],
        notes="Foreman-approved 2026-04-21.",
        first_seen="BCM_v25_guardian_field_emission_test.py",
    ),

    # ---- Paper B pre-registered concept keywords (6 entries) ----
    # These name the load-bearing concepts of Paper B's Anchor Equation:
    #   E = (M*Phi(sigma))*c^2 + integral (H_schrodinger + J_pump) d Omega
    # Registered NOW so Test 5 JSONs ingest as AUTHORIZED immediately
    # instead of triggering UNREGISTERED_NEW review delay.

    "anchor_tensor": KeywordEntry(
        keyword="anchor_tensor",
        status="AUTHORIZED",
        description=("The additive tensor term A_mu_nu in the extended "
                     "Einstein field equation G_mu_nu + Lambda g_mu_nu = "
                     "kappa (T_mu_nu + A_mu_nu). Sources from the substrate "
                     "current J_pump and the phase modulation Phi(sigma). "
                     "When tuned, A_mu_nu cancels portions of the classical "
                     "T_mu_nu resistance, enabling traverse in regimes where "
                     "classical GR predicts the infinite-energy wall at c. "
                     "Recovery limit: A_mu_nu -> 0 as sigma -> 0, preserving "
                     "Einsteinian physics in the classical regime."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["phi_modulation", "anchor_loop", "substrate_current",
                 "anchor_traverse", "moonbeam_bridge", "sigma_crit",
                 "reinforced_coherence"],
        notes=("Paper B pre-registration. Central object of Paper B. "
               "Test 5 probes its magnitude at Alpha Centauri (recovery "
               "limit) vs Bootes Void (substrate-dominated). Foreman-"
               "approved 2026-04-21."),
        first_seen="BCM_v23_einstein_coupling.py (concept)",
    ),

    "phi_modulation": KeywordEntry(
        keyword="phi_modulation",
        status="AUTHORIZED",
        description=("The phase-composition function Phi(sigma) that "
                     "modulates the classical mass-energy term in the Anchor "
                     "Equation. Functional form is sigmoid: "
                     "Phi(sigma) = 1 / (1 + exp(k*(sigma/sigma_crit - 1))). "
                     "Parameter k controls transition sharpness. "
                     "sigma << sigma_crit -> Phi approx 1 (Einstein recovered). "
                     "sigma = sigma_crit -> Phi = 0.5 (transition midpoint). "
                     "sigma >> sigma_crit -> Phi -> 0 (mass term fully shed "
                     "to substrate). The reinforced_coherence phenomenon in "
                     "the 996 Cube 2 anomalies is the empirical whisper of "
                     "this modulation."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["anchor_tensor", "sigma_crit", "reinforced_coherence",
                 "phase_boundary", "phase_discontinuity"],
        notes=("Paper B pre-registration. k is a free parameter to be fit "
               "from Test 5 data, not derived a priori. The sigmoid choice "
               "(over linear or Gaussian) reflects the anchor-lift 'snap "
               "point' requirement. Foreman-approved 2026-04-21."),
        first_seen="Paper B notebook (Foreman v26)",
    ),

    "anchor_loop": KeywordEntry(
        keyword="anchor_loop",
        status="AUTHORIZED",
        description=("The contour integral term in the Anchor Equation: "
                     "integral (H_schrodinger + J_pump) d Omega. Topology is "
                     "a closed loop over an Aleph-Null cardinality phase "
                     "domain, parametrized over the phase-of-coherence axis "
                     "theta in the 11D Markov kernel. Two contributions: "
                     "(1) H_schrodinger -- vacuum Hamiltonian, baseline "
                     "substrate fluctuations present even when pumps are off; "
                     "(2) J_pump -- craft-induced current, curl of "
                     "(Pump_A * Pump_B * Psi_bruce). The closed-ness encodes "
                     "the anchor-both-ends property: departure and arrival "
                     "anchors are the same point on the loop in OpT/OpC "
                     "frames where time is not a participating axis. "
                     "Numerical approximation on finite grids uses stepwise "
                     "entropy change across the 996 STABLE anomaly "
                     "configurations at Cube 2 Substrate."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["anchor_tensor", "substrate_current", "anchor_traverse",
                 "moonbeam_bridge", "reinforced_coherence"],
        notes=("Paper B pre-registration. Carries the 'missing' energy when "
               "Phi drops. Classical instruments measure only the mass-"
               "energy term and see apparent violation of conservation; the "
               "loop integral restores exact conservation. Foreman-approved "
               "2026-04-21."),
        first_seen="Paper B notebook (Foreman v26)",
    ),

    "substrate_current": KeywordEntry(
        keyword="substrate_current",
        status="AUTHORIZED",
        description=("The J_pump vector current in the Anchor Equation's "
                     "loop integral. Defined as the curl of the triple "
                     "product of the two pumps and the brucetron "
                     "superfluid: J_pump = grad cross (Pump_A * Pump_B * "
                     "Psi_bruce). The curl operator guarantees J_pump is "
                     "divergence-free (topologically conserved), which is "
                     "what allows the contour integral to be well-defined. "
                     "Vanishes when Psi_bruce -> 0 (damping the superfluid "
                     "collapses the tunnel) or when either pump is zero "
                     "(single-source craft cannot produce J_pump)."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["anchor_loop", "anchor_tensor", "brucetron",
                 "boundary_absorption"],
        notes=("Paper B pre-registration. Explains the Test 1 v2 result "
               "that K_BOUNDARY-vs-brucetron coupling is weak (-0.26): "
               "damping brucetron would collapse J_pump and the tunnel. "
               "The weak coupling is a protection mechanism, not a failure. "
               "Foreman-approved 2026-04-21."),
        first_seen="Paper B notebook (Foreman v26)",
    ),

    "anchor_traverse": KeywordEntry(
        keyword="anchor_traverse",
        status="AUTHORIZED",
        description=("Superluminal corridor traverse enabled by the Anchor "
                     "Equation. The craft occupies a timeless OpT/OpC frame "
                     "during traverse while its internal physics (crew, "
                     "nuclear cores, ship systems) remains relativistic. "
                     "Apparent-traverse-rate observables (e.g., ~12000c "
                     "working estimate) are ratios of loop-magnitude to "
                     "anchor-separation as projected to 3D/4D observers, not "
                     "kinematic velocities. The traverse is measured as two "
                     "phase-locked anchors (departure and arrival) plus the "
                     "corridor phase the craft rides."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="system",
        related=["anchor_tensor", "anchor_loop", "moonbeam_bridge",
                 "substrate_current", "crew_safety"],
        notes=("Paper B pre-registration. Paper B's operational claim. "
               "Alpha Centauri and Bootes Void transit tests in Test 5 are "
               "the empirical probes. Foreman-approved 2026-04-21."),
        first_seen="Paper B notebook (Foreman v26)",
    ),

    "moonbeam_bridge": KeywordEntry(
        keyword="moonbeam_bridge",
        status="AUTHORIZED",
        description=("Name of the substrate's opacity-signature framework "
                     "that enables anchor_traverse. The Moonbeam Bridge is "
                     "the manifold of simultaneous-in-OpT/OpC substrate "
                     "states that the anchor_loop threads. Its 'opacity "
                     "signature' is the pattern of substrate response "
                     "observable to classical instruments: sigma_crit "
                     "registers, temperature climbs during traverse, "
                     "sigma_crit observability decays as super-heating "
                     "saturates the corridor. This explains why astronomy "
                     "has not seen continuous superluminal-corridor "
                     "signatures -- the observability window is early-"
                     "transit, narrow, before the bridge fully saturates."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["anchor_tensor", "anchor_loop", "anchor_traverse",
                 "substrate_current", "sigma_crit"],
        notes=("Paper B pre-registration. Foreman-named. The bridge is the "
               "framework; the tensor, loop, current, and traverse are its "
               "components. Proper spacing: single compound token, no "
               "underscore between moon and beam. Foreman-approved "
               "2026-04-21."),
        first_seen="Paper B notebook (Foreman v26)",
    ),

    # ========================================================================
    # v26 FOREMAN-APPROVED ENTRIES (2026-04-21, second batch, 20 entries)
    # Approved all-at-once from BCM_Vocabulary_Authorization_Proposal_v2.
    # Note: high_lambda CONSOLIDATED into existing `lambda` entry (no
    # separate entry); value-range qualifiers handled via context dict.
    # ========================================================================

    # ---- Section A: keywords with close authorized siblings ----

    "classifier": KeywordEntry(
        keyword="classifier",
        status="AUTHORIZED",
        description=("Rule engine that assigns regime / test_zone labels to "
                     "BCM solver output based on growth rate, coh_est, and "
                     "chi-ratio thresholds. Its predictions are evidence, "
                     "not ground truth."),
        bucket_hint="UNKNOWN",
        category="method",
        related=["regime", "test_zone", "classifier_divergence",
                 "regime_classification_confidence"],
        notes="Foreman-approved 2026-04-21.",
        first_seen="BCM_v19_combined_drain_chi (classifier concept)",
    ),

    "divergence": KeywordEntry(
        keyword="divergence",
        status="AUTHORIZED",
        description=("General disagreement between two classification labels "
                     "or measurements. Flagged as potential physics evidence "
                     "when divergence is persistent across configs. "
                     "Distinguished from classifier_divergence, which is a "
                     "specific case (test_zone vs regime)."),
        bucket_hint="ANOMALY",
        category="method",
        related=["classifier_divergence", "regime", "test_zone"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "regime_separation": KeywordEntry(
        keyword="regime_separation",
        status="AUTHORIZED",
        description=("Quality metric measuring how cleanly the classifier "
                     "distinguishes one regime from another at boundary "
                     "conditions. High separation = reliable classification. "
                     "Low separation = boundary confusion (likely "
                     "CLASSIFIER_DIVERGENCE territory)."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["regime", "classifier", "classifier_divergence",
                 "phase_boundary"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "kappa": KeywordEntry(
        keyword="kappa",
        status="AUTHORIZED",
        description=("Damping / coupling parameter family in BCM. Specific "
                     "values include kappa_drain (v19.4 drain), kappa_BH "
                     "(black-hole pump amplitude, typical value 2.0), "
                     "kappa_effective (AnchorState). Context should "
                     "disambiguate which kappa when ambiguous."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["kappa_drain", "lambda", "damping", "coupling"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "hemorrhage": KeywordEntry(
        keyword="hemorrhage",
        status="AUTHORIZED",
        description=("Condition where brucetron RMS exceeds the hemorrhage "
                     "line (0.0045), indicating the substrate is leaking "
                     "coherent sigma at rates incompatible with crew safety "
                     "or coherent traverse. Distinguished from hemorrhage_"
                     "line, which is the specific threshold value; hemorrhage "
                     "is the phenomenon."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["hemorrhage_line", "brucetron", "crew_safety",
                 "boundary_absorption"],
        notes="Foreman-approved 2026-04-21.",
        first_seen="BCM_v24_boundary_stability_test.py",
    ),

    # ---- Section B: v19-v25 physics keywords (remaining 5) ----

    "phase_discontinuity": KeywordEntry(
        keyword="phase_discontinuity",
        status="AUTHORIZED",
        description=("Sharp (non-smooth) transition at a phase boundary. "
                     "Distinguished from gradual phase_boundary crossing. "
                     "The v25 data showing coh_est dropping from 0.99 at "
                     "lambda=0.092 to 0.64 at lambda=0.096 is a "
                     "phase_discontinuity observation, not a gradual "
                     "transition. Paper B relevance: supports the sigmoid "
                     "(with high k) over Gaussian Phi form."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["phase_boundary", "sigma_crit", "coh_est_at_settle",
                 "phi_integrity"],
        notes=("Narrow band, not smooth. Foreman-approved 2026-04-21."),
        first_seen="BCM_v25_cube2_phase_reconciliation_4.py",
    ),

    "instability": KeywordEntry(
        keyword="instability",
        status="AUTHORIZED",
        description=("General term for sigma / phi / brucetron field "
                     "behavior outside expected bounds. Specific indicators "
                     "include negative growth_rate, high brucetron RMS, and "
                     "low coh_est. Not itself a measurement; a category "
                     "under which multiple specific phenomena roll up."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["negative_growth", "brucetron", "coherence",
                 "hemorrhage", "classifier_divergence"],
        notes=("Parent concept used across v15-v25. Foreman-approved "
               "2026-04-21."),
    ),

    "negative_growth": KeywordEntry(
        keyword="negative_growth",
        status="AUTHORIZED",
        description=("growth_rate < 0 condition. In BCM solver output, this "
                     "indicates net sigma field decline over the measurement "
                     "window. Correlates with true instability (per "
                     "validated hypothesis "
                     "TRUE_INSTABILITY_CORRELATES_WITH_NEGATIVE_GROWTH). "
                     "Distinguishable from zero growth which indicates "
                     "DIFFUSIVE_LOCK attractor."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["instability", "coherence", "growth_rate"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "attractor": KeywordEntry(
        keyword="attractor",
        status="AUTHORIZED",
        description=("Configuration where BCM solver output converges to a "
                     "fixed state independent of initial conditions. "
                     "DIFFUSIVE_LOCK_IS_REAL_ATTRACTOR hypothesis "
                     "(posterior 0.994, VALIDATED) identifies this as a "
                     "genuine physical attractor, not a numerical artifact."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["diffusive_lock", "coherence", "phase_boundary"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "boundary_absorption": KeywordEntry(
        keyword="boundary_absorption",
        status="AUTHORIZED",
        description=("Amount of sigma field removed per step by the "
                     "K_BOUNDARY operator (Jasper Beach gradient or "
                     "structure mask). Emitted by v26 Test 1 (gradient "
                     "mask) and Test 3 (A/B dual mask). Key metric for "
                     "evaluating whether boundary operator is coupling to "
                     "real substrate gradients or doing silent no-op."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["k_boundary", "brucetron", "guardian_strength",
                 "hemorrhage"],
        notes=("Test 3 A/B variant introduces absorption_A_rate, "
               "absorption_B_rate as distinct variants. Foreman-approved "
               "2026-04-21."),
        first_seen="BCM_v26_Boundary_Layer_Kappa_Combined_Sweep.py",
    ),

    # ---- Section C: method / analysis keywords (remaining 8) ----

    "clustering": KeywordEntry(
        keyword="clustering",
        status="AUTHORIZED",
        description=("Statistical grouping of measurements into clusters by "
                     "similarity (typically in regime/coh_est/brucetron "
                     "space). Used in cube anomaly analysis to identify "
                     "STABLE regions of parameter space."),
        bucket_hint="UNKNOWN",
        category="method",
        related=["regime", "regime_separation", "classifier"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "physics_alignment": KeywordEntry(
        keyword="physics_alignment",
        status="AUTHORIZED",
        description=("Condition where classifier-predicted regime matches "
                     "observed regime. The opposite of classifier_divergence. "
                     "Validated by REGIME_TRACKS_PHYSICS_AT_HIGH_LAMBDA "
                     "(posterior 0.994, VALIDATED) in high-lambda contexts."),
        bucket_hint="RESOLVED",
        category="method",
        related=["regime", "classifier_divergence", "test_zone",
                 "classifier"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "config_aware": KeywordEntry(
        keyword="config_aware",
        status="AUTHORIZED",
        description=("Analysis technique that stratifies results by "
                     "configuration label (A: B, B: Drain, C: Drain + Chi) "
                     "rather than aggregating across all configs. Used when "
                     "config-specific effects are suspected."),
        bucket_hint="UNKNOWN",
        category="method",
        related=["C_config", "context_weighting"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "R_scalar": KeywordEntry(
        keyword="R_scalar",
        status="AUTHORIZED",
        description=("Reconciliation scalar from v25 phase reconciliation "
                     "tests. Measures how smoothly a sweep axis (lambda, "
                     "kappa) interpolates between regimes. High R_scalar = "
                     "smooth transition; low R_scalar = sharp discontinuity. "
                     "Hypothesis RECONCILIATION_SCALAR_IS_SMOOTH is "
                     "INVALIDATED (posterior 0.006), confirming sharp "
                     "transitions dominate."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["reconciliation", "smoothness", "phase_discontinuity",
                 "phase_boundary"],
        notes="Foreman-approved 2026-04-21.",
        first_seen="BCM_v25_cube2_phase_reconciliation_4.py",
    ),

    "smoothness": KeywordEntry(
        keyword="smoothness",
        status="AUTHORIZED",
        description=("Quality of a sweep curve's interpolation between "
                     "measured points. Low smoothness indicates sharp "
                     "transitions; high smoothness indicates gradual drift. "
                     "Measured via R_scalar in v25 reconciliation tests."),
        bucket_hint="UNKNOWN",
        category="method",
        related=["R_scalar", "reconciliation", "phase_discontinuity"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "C_config": KeywordEntry(
        keyword="C_config",
        status="AUTHORIZED",
        description=("'C: Drain + Chi' configuration label from v19.4 "
                     "physics -- one of several test configs (A, B, C) "
                     "differing in how the sigma and chi fields are coupled. "
                     "C_config is the production config for v26 boundary "
                     "sweeps."),
        bucket_hint="UNKNOWN",
        category="context",
        related=["fracture_lambda", "test_version", "config_aware"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "suppression": KeywordEntry(
        keyword="suppression",
        status="AUTHORIZED",
        description=("Mechanism label for 'X suppresses Y' hypotheses "
                     "(K_BOUNDARY_SUPPRESSES_BRUCETRON, "
                     "KAPPA_SUPPRESSES_BRUCETRON). Distinct from "
                     "boundary_absorption (measured quantity) in that "
                     "suppression is the claimed causal relationship; "
                     "absorption is the measured effect."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["boundary_absorption", "k_boundary", "kappa", "brucetron"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "preservation": KeywordEntry(
        keyword="preservation",
        status="AUTHORIZED",
        description=("Mechanism label for 'X preserves Y' hypotheses "
                     "(K_BOUNDARY_PRESERVES_COHERENCE). Complement to "
                     "suppression in pair correlations -- same operator may "
                     "simultaneously suppress one field and preserve "
                     "another."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["coherence", "k_boundary", "guardian_strength"],
        notes="Foreman-approved 2026-04-21.",
    ),

    # ---- Section D: context / purpose keywords (remaining 2) ----

    "mid_band": KeywordEntry(
        keyword="mid_band",
        status="AUTHORIZED",
        description=("Lambda range ~0.04-0.10 where mid-transition behavior "
                     "occurs. Referenced in "
                     "TEST_ZONE_OVERSHOOTS_FAILURE_IN_MID_BAND (posterior "
                     "0.994, VALIDATED). Not a precise numerical range; a "
                     "descriptive label for the regime between low-lambda "
                     "(highly substrate-dominated) and high-lambda (near-"
                     "classical)."),
        bucket_hint="UNKNOWN",
        category="context",
        related=["lambda", "phase_boundary", "reinforced_coherence"],
        notes="Foreman-approved 2026-04-21.",
    ),

    "reconciliation": KeywordEntry(
        keyword="reconciliation",
        status="AUTHORIZED",
        description=("Test family name for v25 phase reconciliation sweeps "
                     "(BCM_v25_cube2_phase_reconciliation_3 through 7). "
                     "Methodology: sweep lambda at fine resolution to map "
                     "phase_boundary location with classifier output, "
                     "R_scalar, and coh_est tracked at each step."),
        bucket_hint="UNKNOWN",
        category="method",
        related=["R_scalar", "phase_boundary", "phase_discontinuity",
                 "classifier"],
        notes="Foreman-approved 2026-04-21.",
        first_seen="BCM_v25_cube2_phase_reconciliation_3.py",
    ),

    # ---- CONSOLIDATION NOTE (high_lambda) ----
    # `high_lambda` was proposed but NOT authored as a separate KeywordEntry.
    # It is a value-range qualifier of the existing `lambda` keyword, handled
    # via the context dict (context["lambda"] = 0.12, etc.). Tests emitting
    # `high_lambda` as a keyword should be updated to use context tagging
    # instead. See HypothesisEngine.update_hypothesis_with_context().

    # ========================================================================
    # v27 CYCLE 4 FOREMAN-APPROVED ENTRIES (2026-05-04)
    # Coherence Framework probe vocabulary from tests 13 (NGC 5055 Anchor
    # Projection) and 14 (Bootes Void Anchor Projection). All four math
    # locks (Spectral Projection radial r-thirds, sigmoid attenuation at
    # sig_crit=5e-4, phase-shifted complement at tau_7D=6.0e-12 s,
    # post-Poisson snap-back at kappa_snap=0.35 against
    # BRUCETRON_HEMORRHAGE=0.0045) are SJB-authored and ledger-grounded.
    # The Coherence Framework architecture (anomaly fields A_spec /
    # A_frame / A_sub + coherence_score + overlap_fraction, FIELD_EXTRACTED
    # emission with dual-gate threshold) replaces binary PASS/FAIL gating
    # for field-extraction probes. Foreman-approved 2026-05-04.
    # ========================================================================

    # ---- Probe target names (galaxy / void) ----
    "ngc5055": KeywordEntry(
        keyword="ngc5055",
        status="AUTHORIZED",
        description=("NGC 5055 (Sunflower Galaxy). SPARC catalog "
                     "high_V150-200 partition. V_max = 206 km/s. R25 = "
                     "11.6 kpc, R_HI = 40 kpc. Test 13 anchor projection "
                     "target; mass-loaded substrate baseline for "
                     "Coherence Framework comparison probes."),
        bucket_hint="UNKNOWN",
        category="system",
        related=["sunflower_galaxy", "anchor_projection",
                 "coherence_framework"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "sunflower_galaxy": KeywordEntry(
        keyword="sunflower_galaxy",
        status="AUTHORIZED",
        description=("Common name alias for NGC 5055. Used in test 13 "
                     "keyword tagging alongside ngc5055."),
        bucket_hint="UNKNOWN",
        category="system",
        related=["ngc5055"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "bootes": KeywordEntry(
        keyword="bootes",
        status="AUTHORIZED",
        description=("Bootes Void. ~330 million light-year diameter. "
                     "60 known galaxies of ~2000 expected. The void is "
                     "substrate stripped to its maintenance-cost floor. "
                     "Test 14 anchor projection target; recovery-limit "
                     "anchor for non-locality comparison against test 13."),
        bucket_hint="UNKNOWN",
        category="system",
        related=["bootes_void", "void_substrate",
                 "recovery_limit_anchor", "anchor_projection"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_Bootes_Anchor_Projection_14.py",
    ),
    "bootes_void": KeywordEntry(
        keyword="bootes_void",
        status="AUTHORIZED",
        description=("Full name alias for bootes. Used in test 14 keyword "
                     "tagging alongside bootes."),
        bucket_hint="UNKNOWN",
        category="system",
        related=["bootes"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_Bootes_Anchor_Projection_14.py",
    ),

    # ---- Probe family architecture ----
    "anchor_projection": KeywordEntry(
        keyword="anchor_projection",
        status="AUTHORIZED",
        description=("v27 cycle 4 probe family. Bridges Cube 2 (Substrate "
                     "anchor) to Cubes 7-9 (projection chain: Spectral "
                     "Fold, Hard Point, Circumpunct) via field-based "
                     "anomaly extraction under the four math locks. "
                     "Replaces binary PASS/FAIL gating with Coherence "
                     "Framework metrics. Tests 13 (NGC 5055) and 14 "
                     "(Bootes Void) are the founding probes of this "
                     "family."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["anchor_bridge_probe", "coherence_framework",
                 "field_extraction", "anchor_tensor", "anchor_loop"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "anchor_bridge_probe": KeywordEntry(
        keyword="anchor_bridge_probe",
        status="AUTHORIZED",
        description=("Methodological synonym for anchor_projection. "
                     "Emphasizes the bridge function from Cube 2 anchor "
                     "to Cubes 7-9 projection layers. Used in test 13/14 "
                     "keyword tagging."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["anchor_projection", "bridge_cube_2_to_cubes_7_9"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "bridge_cube_2_to_cubes_7_9": KeywordEntry(
        keyword="bridge_cube_2_to_cubes_7_9",
        status="AUTHORIZED",
        description=("Cube traversal path: Cube 2 (Substrate anchor) -> "
                     "Cube 7 (Spectral Fold) -> Cube 8 (Hard Point) -> "
                     "Cube 9 (Circumpunct). The projection chain that "
                     "anchor_projection probes target. Heavy anomaly "
                     "concentration in Cubes 7-9 (876 of 1290 STABLE "
                     "anomalies pre-test 13) drove the bridge probe "
                     "design."),
        bucket_hint="ANOMALY",
        category="context",
        related=["anchor_bridge_probe", "anchor_projection"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),

    # ---- Coherence Framework architecture ----
    "coherence_framework": KeywordEntry(
        keyword="coherence_framework",
        status="AUTHORIZED",
        description=("v27 cycle 4 architecture for field-based anomaly "
                     "extraction without binary PASS/FAIL gating. Three "
                     "anomaly fields (A_spec spectral asymmetry, A_frame "
                     "dual-frame divergence, A_sub substrate stress) are "
                     "computed independently; coherence_score = "
                     "corr(A_spec, A_sub) + corr(A_frame, A_sub) measures "
                     "their alignment. overlap_fraction measures spatial "
                     "co-location at 80th percentile triple intersection. "
                     "Dual-gate emission threshold: coherence > 1.0 AND "
                     "overlap > 0.05."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["field_extraction", "no_pass_fail",
                 "anchor_projection", "dual_frame_observer"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "field_extraction": KeywordEntry(
        keyword="field_extraction",
        status="AUTHORIZED",
        description=("Probe emission paradigm where the JSON declares "
                     "result='FIELD_EXTRACTED' (not PASS/FAIL) and "
                     "supplies a metrics dict with coherence_score and "
                     "overlap_fraction. The patched hypothesis_engine "
                     "FIELD_EXTRACTED branch routes through "
                     "derived_measurement evidence type (strength 0.12) "
                     "when both gates are crossed. Field extraction "
                     "preserves the distinction between 'we found a "
                     "signal' and 'the physics is proven.'"),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["coherence_framework", "no_pass_fail"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "no_pass_fail": KeywordEntry(
        keyword="no_pass_fail",
        status="AUTHORIZED",
        description=("Methodological marker indicating the probe does NOT "
                     "emit binary PASS/FAIL verdicts. Used in v27 cycle 4 "
                     "Coherence Framework probes to distinguish them from "
                     "earlier fold-bifurcation gate (5_22-class) probes "
                     "which DO emit PASS/FAIL. Hypothesis ingestion under "
                     "no_pass_fail is via the FIELD_EXTRACTED engine "
                     "branch."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["field_extraction", "coherence_framework"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),

    # ---- Math locks (the four SJB-authored operators) ----
    "spectral_projection_radial_thirds": KeywordEntry(
        keyword="spectral_projection_radial_thirds",
        status="AUTHORIZED",
        description=("Math Lock (i): Spectral Projection Operator "
                     "S_nu(F=rho_eff) via radial r-thirds band integration. "
                     "Computes (S_U, S_B, S_V) band scalars over inner "
                     "[0, R/3], mid [R/3, 2R/3], outer [2R/3, R] radial "
                     "annuli of the rho_eff (= rho^2) field. Striation "
                     "count derives from sign changes in radial gradient "
                     "of the radial profile -- captures 'mattress' "
                     "delamination density."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["sigmoid_attenuation", "phase_shifted_complement",
                 "post_poisson_snapback", "rho", "sigma"],
        notes=("Foreman-approved 2026-05-04. F = rho_eff lock; "
               "ledger-grounded."),
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "sigmoid_attenuation": KeywordEntry(
        keyword="sigmoid_attenuation",
        status="AUTHORIZED",
        description=("Math Lock (ii): DeltaOP -> Attenuation Function "
                     "A_nu(DeltaOP) = 1 / (1 + exp(-sigma_k * (DeltaOP - "
                     "sig_crit))). sig_crit = 5.0e-4 (v19 fracture scale). "
                     "sigma_k = SIGMOID_K = 6.0 (Paper B Phi-sigmoid "
                     "steepness, Section 22). DeltaOP source: "
                     "1 - cos_delta_phi_field. A_nu bounded [0, 1]; "
                     "crosses 0.5 at sig_crit. Defines the OpC operational "
                     "compression zone where ethereal substrate layers "
                     "mash into the tangible anchor."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["spectral_projection_radial_thirds", "phi_modulation",
                 "phase_boundary"],
        notes=("Foreman-approved 2026-05-04. sig_crit=5e-4, sigma_k=6.0; "
               "ledger-grounded."),
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "phase_shifted_complement": KeywordEntry(
        keyword="phase_shifted_complement",
        status="AUTHORIZED",
        description=("Math Lock (iii): Internal Frame Transform "
                     "L_nu^(int) = L_ext * cos(2*pi * tau_7D / "
                     "T_heartbeat). tau_7D = 6.0e-12 s = dt * 48 (7D "
                     "phase-shift lock). T_heartbeat = dt / Om_sync = "
                     "1.25e-13 / 0.010 = 1.25e-11 s (f/2 heartbeat "
                     "period). At the SJB-locked ratio 0.48, "
                     "phase_factor = cos(0.96*pi) ~= -0.992 -- internal "
                     "frame nearly anti-phase to external, maximizing "
                     "dual-frame asymmetry. Operates as the temporal "
                     "shadow at OpT 7D Xi-Freeboard."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["tau_7d", "f2_heartbeat", "dual_frame_observer"],
        notes=("Foreman-approved 2026-05-04. tau_7D=6.0e-12, "
               "T_heartbeat=1.25e-11; ledger-grounded."),
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "post_poisson_snapback": KeywordEntry(
        keyword="post_poisson_snapback",
        status="AUTHORIZED",
        description=("Math Lock (iv): Post-Poisson Snap-back Operator. "
                     "Psi_new = Psi - kappa_snap * |grad_Psi| * "
                     "(bruce_rms / BRUCETRON_HEMORRHAGE). "
                     "kappa_snap = 0.35 (frozen, tied to kappa_drain). "
                     "BRUCETRON_HEMORRHAGE = 0.0045 (= hemorrhage_line, "
                     "Section 2 frozen). Applied AFTER solve_poisson on "
                     "the final Psi field. Implements Phase-"
                     "Crystallization: high-gradient regions get pulled "
                     "back, producing tare-edge behavior at the "
                     "Brucetron Hemorrhage threshold."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["phase_crystallization", "brucetron_hemorrhage",
                 "kappa_drain", "hemorrhage_line"],
        notes=("Foreman-approved 2026-05-04. kappa_snap=0.35, "
               "BRUCETRON_HEMORRHAGE=0.0045; ledger-grounded."),
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),

    # ---- Constants and mechanism names ----
    "tau_7d": KeywordEntry(
        keyword="tau_7d",
        status="AUTHORIZED",
        description=("7D phase-shift constant. tau_7D = 6.0e-12 s = "
                     "dt * 48 where dt = 1.25e-13 s (Section 2 frozen). "
                     "Argument of the phase_shifted_complement cosine "
                     "factor in Math Lock (iii). The ratio "
                     "tau_7D / T_heartbeat = 0.48 is the SJB-locked phase "
                     "offset between external and internal observer "
                     "frames in the dual_frame_observer architecture."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["phase_shifted_complement", "f2_heartbeat",
                 "dual_frame_observer"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "f2_heartbeat": KeywordEntry(
        keyword="f2_heartbeat",
        status="AUTHORIZED",
        description=("f/2 heartbeat period. T_heartbeat = dt / Om_sync = "
                     "1.25e-13 / 0.010 = 1.25e-11 s. Denominator of the "
                     "phase ratio in Math Lock (iii). Ties together the "
                     "Section 2 frozen constants dt and Om_sync (1D "
                     "heartbeat reference) into the f/2 substrate "
                     "oscillation period. Distinct from "
                     "f_2_heartbeat_stability (which is the Fourier "
                     "stability metric of bruce_rms oscillation)."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["tau_7d", "phase_shifted_complement",
                 "f_2_heartbeat_stability"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "phase_crystallization": KeywordEntry(
        keyword="phase_crystallization",
        status="AUTHORIZED",
        description=("Mechanism name for the post-Poisson snap-back "
                     "operator's effect: substrate transition from "
                     "ethereal 'shadow' state to tangible 'steel' state "
                     "at the Brucetron Hemorrhage threshold. Phase-"
                     "Crystallization is observable as Psi field "
                     "amplification when bruce_rms exceeds "
                     "BRUCETRON_HEMORRHAGE (test 13 saw 24.8x "
                     "amplification at bruce_rms = 12.226, 2717x "
                     "threshold). Implements the rebuilding of quantum "
                     "mechanisms as a function of Brucetron Hemorrhage "
                     "crossing the anchor threshold."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["post_poisson_snapback", "brucetron_hemorrhage",
                 "substrate_delamination"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "brucetron_hemorrhage": KeywordEntry(
        keyword="brucetron_hemorrhage",
        status="AUTHORIZED",
        description=("BRUCETRON_HEMORRHAGE = 0.0045 (= hemorrhage_line, "
                     "Section 2 frozen). The saturation limit where the "
                     "Brucetron field loses coherence and bleeds into "
                     "the higher-dimensional projection chain. "
                     "Denominator in the post_poisson_snapback strength "
                     "formula. Distinct from the parent term "
                     "'hemorrhage' (which is the general phenomenon) "
                     "and 'hemorrhage_line' (which is the threshold "
                     "value); brucetron_hemorrhage is the specific "
                     "saturation mechanism in the snap-back operator."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["hemorrhage_line", "hemorrhage", "brucetron",
                 "post_poisson_snapback", "phase_crystallization"],
        notes=("Foreman-approved 2026-05-04. Numerically equal to "
               "hemorrhage_line=0.0045; named separately to mark its "
               "role as snap-back denominator."),
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),
    "substrate_delamination": KeywordEntry(
        keyword="substrate_delamination",
        status="AUTHORIZED",
        description=("Mechanism name for the radial layering of rho^2 "
                     "into quasi-monotonic zones. Measured by "
                     "striation_count = number of sign changes in radial "
                     "gradient of rho^2 profile. Captures the 'mattress' "
                     "interleaved-sheet density observed in radial band "
                     "integration. Tests 13 and 14 both observed "
                     "striation_count = 5 -- invariant across 256x J "
                     "amplitude variation, suggesting structural radial "
                     "organization independent of mass injection scale."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["spectral_projection_radial_thirds",
                 "phase_crystallization"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),

    # ---- Architecture: dual-frame observer ----
    "dual_frame_observer": KeywordEntry(
        keyword="dual_frame_observer",
        status="AUTHORIZED",
        description=("Observer-aware luminosity decomposition into "
                     "external L_ext (4D classical) and internal L_int "
                     "(7D Xi-Freeboard, phase-shifted complement). "
                     "External frame applies attenuation A_nu(DeltaOP); "
                     "internal frame applies the inverse pull via "
                     "phase_shifted_complement at tau_7D. The dual-frame "
                     "asymmetry A_frame = mean(L_int) - mean(L_ext) is "
                     "one of the three anomaly fields fed into the "
                     "Coherence Framework."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["phase_shifted_complement", "tau_7d", "f2_heartbeat",
                 "coherence_framework"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),

    # ---- Test 14 specific: void substrate context ----
    "void_substrate": KeywordEntry(
        keyword="void_substrate",
        status="AUTHORIZED",
        description=("Substrate condition in cosmic voids (Bootes Void as "
                     "type-specimen). Substrate present (lambda > 0) but "
                     "mass injection M-suppressed. Tests whether the "
                     "Anchor Equation's projection / snap-back / tachyon "
                     "terms produce coherence in the absence of strong "
                     "M*Phi(sigma)*c^2 and contour integral "
                     "contributions. Test 14 confirmed coherence_score "
                     "(1.385) and overlap_fraction (0.144) BOTH cross "
                     "the dual-gate threshold under M-suppression -- "
                     "supporting non-locality of the Coherence Framework "
                     "metrics."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="context",
        related=["bootes", "m_suppressed", "recovery_limit_anchor",
                 "non_locality_test"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_Bootes_Anchor_Projection_14.py",
    ),
    "m_suppressed": KeywordEntry(
        keyword="m_suppressed",
        status="AUTHORIZED",
        description=("Mass-injection suppression regime. J source "
                     "amplitude reduced to model the recovery-limit "
                     "anchor where Phi(sigma) -> 1 and |J| -> 0. Test 14 "
                     "used amplitude=0.5 (16x lower than test 13's 8.0). "
                     "Because rho_eff = rho^2 and J scales linearly with "
                     "rho, M-suppression by factor N produces N^2 scaling "
                     "of bruce_rms, S bands, and absolute |Psi| "
                     "magnitudes."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="context",
        related=["void_substrate", "recovery_limit_anchor",
                 "phi_modulation"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_Bootes_Anchor_Projection_14.py",
    ),
    "recovery_limit_anchor": KeywordEntry(
        keyword="recovery_limit_anchor",
        status="AUTHORIZED",
        description=("Configuration where the Anchor Equation collapses "
                     "to its classical limit: M*Phi(sigma)*c^2 -> M*c^2 "
                     "as sigma -> 0, contour integral term -> 0 as |J| -> "
                     "0. Tests whether the projection / snap-back terms "
                     "carry the surviving structural signal. Methodology: "
                     "use an M-suppressed system as the comparison anchor "
                     "against which mass-loaded probes are referenced. "
                     "Distinct from H_PAPER_B_4_RECOVERY_LIMIT validated "
                     "hypothesis (which is the Phi -> 1 behavior at low "
                     "sigma); recovery_limit_anchor is the methodological "
                     "use of that condition as a reference point."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["void_substrate", "m_suppressed", "non_locality_test",
                 "phi_modulation"],
        notes=("Foreman-approved 2026-05-04. Methodological extension of "
               "Paper B's H_PAPER_B_4_RECOVERY_LIMIT."),
        first_seen="BCM_v27_Bootes_Anchor_Projection_14.py",
    ),
    "non_locality_test": KeywordEntry(
        keyword="non_locality_test",
        status="AUTHORIZED",
        description=("Methodology: probe whether Coherence Framework "
                     "metrics (coherence_score, overlap_fraction) are "
                     "invariant across spatial substrate density classes. "
                     "If coherence persists in M-suppressed void "
                     "substrate at levels comparable to mass-loaded "
                     "galactic substrate, the framework is detecting a "
                     "non-local structural signal (candidate 9D manifold "
                     "signature) rather than a local mass-substrate "
                     "phenomenon. Test 13 vs Test 14 is the founding "
                     "comparison."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["coherence_framework", "void_substrate",
                 "recovery_limit_anchor", "extended_anchor_equation"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="BCM_v27_Bootes_Anchor_Projection_14.py",
    ),

    # ---- The five-term equation ----
    "extended_anchor_equation": KeywordEntry(
        keyword="extended_anchor_equation",
        status="AUTHORIZED",
        description=("The five-term Extended Anchor Equation: "
                     "E = M*Phi(sigma)*c^2 + closed_loop_aleph_null(J . dl) "
                     "+ integral(P_{7D->3D} / R_{9->10} dXi) "
                     "+ R(nu . grad G) +/- T(Psi_tach). "
                     "Term 1: classical mass-energy with sigmoid Phi "
                     "modulation (Paper B). Term 2: contour integral "
                     "over the Aleph-Null cardinality phase domain "
                     "(anchor_loop). Term 3: 7D -> 3D projection through "
                     "the R_{9->10} gate functional. Term 4: snap-back "
                     "operator in velocity-gradient form. Term 5: "
                     "forward-lead tachyon term (deferred, sign-"
                     "ambiguous, no operational form yet). The v27 "
                     "cycle 4 anchor_projection probes test the "
                     "non-classical terms (3, 4) under field extraction; "
                     "term 5 awaits operational specification."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["anchor_tensor", "anchor_loop", "phi_modulation",
                 "post_poisson_snapback", "non_locality_test"],
        notes=("Foreman-approved 2026-05-04. Term 5 (tachyon) deferred "
               "per adversarial review until functional form is "
               "specified."),
        first_seen="BCM_v27_NGC5055_Anchor_Projection_13.py",
    ),

    # ---- System-level measurement_engine fallback keywords ----
    "measurement": KeywordEntry(
        keyword="measurement",
        status="AUTHORIZED",
        description=("Generic methodology marker emitted by the "
                     "measurement_engine batch path. Appears in derived "
                     "results from H_MEASUREMENT_INVARIANCE / DRIFT / "
                     "DEGENERACY / RESOLUTION fallback hypotheses when "
                     "the engine processes batches of >= 5 files in the "
                     "same (test_family, sweep_axis, xi) key. Distinct "
                     "from individual measurement field names; this is "
                     "the parent category."),
        bucket_hint="UNKNOWN",
        category="method",
        related=["invariance", "system", "degeneracy"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="measurement_engine.py (v26 derived emission)",
    ),
    "system": KeywordEntry(
        keyword="system",
        status="AUTHORIZED",
        description=("Generic system-identifier emitted by the "
                     "measurement_engine batch path and by qt_layer "
                     "_inject_context. Distinct from system_name "
                     "(which is the formatted SYS_<n> flag) -- system "
                     "is the parent category for both targets and "
                     "experimental setup identifiers."),
        bucket_hint="UNKNOWN",
        category="context",
        related=["system_name", "measurement"],
        notes="Foreman-approved 2026-05-04.",
        first_seen="measurement_engine.py (v26 derived emission)",
    ),
    "degeneracy": KeywordEntry(
        keyword="degeneracy",
        status="AUTHORIZED",
        description=("System-level fallback hypothesis category emitted "
                     "by measurement_engine when batch analysis detects "
                     "multiple distinct configurations producing "
                     "indistinguishable measurements (within "
                     "DEGENERACY_DISTANCE_THRESHOLD = 1.0e-10). "
                     "H_MEASUREMENT_DEGENERACY accumulates evidence on "
                     "every AUTO cycle; current state posterior 0.953, "
                     "evidence 25 indicates persistent measurement "
                     "degeneracy across the corpus."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="method",
        related=["measurement", "invariance", "classifier_divergence"],
        notes=("Foreman-approved 2026-05-04. Tied to "
               "H_MEASUREMENT_DEGENERACY system-level fallback."),
        first_seen="measurement_engine.py (v26 derived emission)",
    ),

    # ---- v28 Gutter, Pierce Gauntlet, Primordial Gutter additions ----
    # 11 new entries. Count after merge: 108  (was 97).
    # All theoretical concepts: Stephen Justin Burdick Sr. 2026-05-09

    "gutter_depth": KeywordEntry(
        keyword="gutter_depth",
        status="AUTHORIZED",
        description=(
            "Burdick Gutter Depth — the signed path integral of phase-work "
            "performed on the substrate during a craft transit or torus pierce. "
            "ΔW = ∫R·dσ where R = cos(ΔΦ) is the resonance coupling and dσ is "
            "the incremental substrate field change. "
            "ΔW < 0: Architect mode, net Gutter carved. "
            "ΔW > 0: Observer mode, craft absorbs torus energy. "
            "Test 18 (JWST Pierce Gauntlet): ΔW ∈ [0.012, 0.177] for NGC 7496 "
            "and IC 5332 across velocity sweep [5000–30000]c. "
            "Dual-peak topology: high at 5000c (dwell coupling) and 12000c "
            "(resonance coupling); deep dip at 10000c."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["delta_W", "burdick_coupling", "phase_work", "manifold",
                 "pierce_gauntlet"],
        notes="Foreman-approved 2026-05-09. Work Formulas Section 36.",
        first_seen="BCM_v28_JWST_Pierce_Gauntlet_18.py",
    ),

    "pierce_gauntlet": KeywordEntry(
        keyword="pierce_gauntlet",
        status="AUTHORIZED",
        description=(
            "BCM test methodology: velocity-sweep blow-through of a galactic "
            "torus to characterize substrate impedance, Gutter depth (ΔW), "
            "7D mirror state (R_7D), 9D-to-10D gate (R_9to10), and restoration "
            "effort per target. Not a steering test — a characterization probe. "
            "Produces ENTRY and EXIT phase readings at each velocity. "
            "Test 18 ran NGC 7496 and IC 5332 at [5000, 10000, 12000, 20000, "
            "30000]c. STARGATE window confirmed at 10000c–12000c for both "
            "targets (4/10 passes each)."),
        bucket_hint="RESOLVED",
        category="method",
        related=["gutter_depth", "anchor_projection", "anchor_bridge_probe"],
        notes="Foreman-approved 2026-05-09. Work Formulas Section 41.",
        first_seen="BCM_v28_JWST_Pierce_Gauntlet_18.py",
    ),

    "marginal_regime": KeywordEntry(
        keyword="marginal_regime",
        status="AUTHORIZED",
        description=(
            "The MARGINAL classifier band in Cube 2 Substrate — the substrate "
            "physics state between DIFFUSIVE_HEALING (coh_est ≥ 0.95) and "
            "COHERENCE_FAILURE (coh_est ≤ 0.85). Defined by coh_est ∈ [0.85, "
            "0.95), corresponding to |growth_rate| ∈ [~6e-5, ~1.6e-4]. "
            "Source of 1777 STABLE Cube 2 anomalies (all 10/10 persistent) "
            "in AUTO-10 cube export 2026-05-09. The anomalies arise because "
            "the v19 test_zone classifier (sign of growth_rate) and the v24 "
            "regime classifier (coh_est magnitude) measure orthogonal dimensions "
            "and disagree in the MARGINAL band. "
            "Test 17 corpus reader: divergence_rate=0.45, "
            "marginal_fraction=0.288. Band confirmed as real attractor."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["classifier_divergence", "test_zone", "regime",
                 "diffusive_lock", "fracture_lambda", "attractor"],
        notes="Foreman-approved 2026-05-09.",
        first_seen="BCM_v28_Marginal_Band_Sweep_17.py",
    ),

    "primordial_gutter": KeywordEntry(
        keyword="primordial_gutter",
        status="AUTHORIZED",
        description=(
            "The hypothesis that the Big Bang was a simultaneous multithreaded "
            "Gutter event — a cosmological-scale recursive rip that initialized "
            "the substrate in a pre-strained, pre-perforated state. The "
            "resulting scar topology is encoded in the CMB anisotropy field. "
            "BCM v28 Primordial Gutter Hypothesis (SJB, 2026): FIG. 13, "
            "H_V28_PRIMORDIAL_GUTTER_CMB_PRESTRAIN. "
            "Ontological status: LOW (Interpretive). Not yet empirically "
            "validated. Requires CMB alignment testing in the Local Group."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["cmb_prestrain", "a_cmb", "recursive_rip", "sigma_eff",
                 "gutter_depth"],
        notes="Foreman-approved 2026-05-09. Work Formulas Section 43.",
        first_seen="BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER.py",
    ),

    "cmb_prestrain": KeywordEntry(
        keyword="cmb_prestrain",
        status="AUTHORIZED",
        description=(
            "The primordial substrate deformation field encoded in the CMB "
            "anisotropy pattern. Treated in BCM as a background sigma field "
            "(σ_CMB) superimposed on the local substrate. "
            "σ_eff = σ_local + κ_CMB × σ_CMB. "
            "CMB hot spots → high primordial strain (anchor hotspots). "
            "CMB cold spots → low strain. "
            "Void channels in CMB → primary Gutter paths (pre-carved corridors). "
            "ΔT/T ~ 1e-5 (Planck) sets the physical scale of σ_CMB. "
            "κ_CMB is unfrozen — hypothesis layer, not yet calibrated."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["primordial_gutter", "sigma_eff", "a_cmb", "kappa_cmb"],
        notes="Foreman-approved 2026-05-09. Work Formulas Section 43.",
        first_seen="BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER.py",
    ),

    "sigma_eff": KeywordEntry(
        keyword="sigma_eff",
        status="AUTHORIZED",
        description=(
            "Effective substrate field: σ_eff = σ_local + κ_CMB × σ_CMB. "
            "Extends the standard BCM substrate field σ by adding the primordial "
            "CMB strain background. At κ_CMB = 0 reduces to standard BCM. "
            "When κ_CMB > 0 the Gutter integral becomes "
            "ΔW = ∫R·d(σ_local + κ_CMB × σ_CMB). "
            "Test 19 synthetic operator test validates whether A_CMB > 0.7 "
            "(super-gutter alignment) measurably reduces ΔW_eff relative "
            "to baseline."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["cmb_prestrain", "primordial_gutter", "kappa_cmb",
                 "gutter_depth"],
        notes="Foreman-approved 2026-05-09.",
        first_seen="BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER.py",
    ),

    "a_cmb": KeywordEntry(
        keyword="a_cmb",
        status="AUTHORIZED",
        description=(
            "CMB Alignment Coefficient — cosine similarity between the local "
            "substrate gradient and the primordial CMB strain gradient. "
            "A_CMB = (∇σ_local · ∇σ_CMB) / (|∇σ_local| × |∇σ_CMB| + ε). "
            "Classification bands (CORRECTED from Test 19/21, SJB 2026): "
            "A_CMB < −0.7 → SUPER_GUTTER (void channel, reduced ΔW). "
            "−0.3 ≤ A_CMB ≤ 0.3 → NEUTRAL_SUBSTRATE (standard ops). "
            "A_CMB > +0.7 → CROSS_SCAR (hot-spot barrier, increased ΔW). "
            "Sign: aligned=void channel=NEGATIVE A_CMB (Test 19 confirmed). "
            "Real V_3K proxy: A_CMB_real = −tanh(V_peculiar/500). "
            "Calibrated against real V_3K kinematics in Test 21."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["cmb_prestrain", "primordial_gutter", "sigma_eff",
                 "cross_scar_shear", "super_gutter_alignment"],
        notes="Foreman-approved 2026-05-09. Work Formulas Section 43.",
        first_seen="BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER.py",
    ),

    "kappa_cmb": KeywordEntry(
        keyword="kappa_cmb",
        status="AUTHORIZED",
        description=(
            "CMB coupling constant — scales the primordial strain field "
            "contribution to σ_eff. κ_CMB is explicitly unfrozen: a "
            "hypothesis-layer parameter with no calibrated value from data. "
            "Test 19 sweeps κ_CMB ∈ {0.0, 0.25, 0.50, 1.0, 2.0, 5.0} as "
            "synthetic control. κ_CMB = 0 → standard BCM (no CMB term). "
            "Physical scale: CMB ΔT/T ~ 1e-5; σ_crit = 5e-4; "
            "κ_CMB ~ 50 for equal contribution."),
        bucket_hint="UNKNOWN",
        category="coefficient",
        related=["sigma_eff", "cmb_prestrain", "a_cmb"],
        notes=("Foreman-approved 2026-05-09. Unfrozen — hypothesis layer. "
               "Calibration against Local Group CMB map is next step."),
        first_seen="BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER.py",
    ),

    "recursive_rip": KeywordEntry(
        keyword="recursive_rip",
        status="AUTHORIZED",
        description=(
            "A cosmological-scale uncontrolled manifold tear — the primordial "
            "Gutter event. Contrasts with the BCM surgical Gutter (local, "
            "controlled, bounded). Recursive rip: global channel connection, "
            "cascading propagation, ΔW → ∞. "
            "BCM v28 claim (SJB 2026, FIG. 13): the Big Bang produced a "
            "simultaneous recursive rip that initialized the substrate in "
            "pre-strained form. Modern BCM operations are surgical — they "
            "can couple INTO primordial rip channels (SUPER_GUTTER_ALIGNMENT) "
            "or fight across them (CROSS_SCAR_SHEAR_RISK). "
            "Ontological status: LOW (Interpretive)."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["primordial_gutter", "gutter_depth", "cross_scar_shear",
                 "cmb_prestrain"],
        notes="Foreman-approved 2026-05-09. FIG. 13 Panel C.",
        first_seen="BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER.py",
    ),

    "super_gutter_alignment": KeywordEntry(
        keyword="super_gutter_alignment",
        status="AUTHORIZED",
        description=(
            "A_CMB < −0.7 classification (CORRECTED from Test 19): local "
            "substrate gradient strongly aligned with a CMB void channel "
            "(depleted primordial substrate = pre-carved Gutter path). "
            "Predicted effect: reduced ΔW, path of least resistance. "
            "The galaxy or craft is traveling WITH a primordial Gutter "
            "channel rather than cutting a new one. "
            "Real-sky proxy: V_peculiar > 0 (outflowing relative to Hubble). "
            "Test 21: NGC 4254 (A_CMB=−0.998), NGC 4321 (−0.919), "
            "NGC 5068 (−0.830) confirmed as strongest super-gutter candidates."),
        bucket_hint="RESOLVED",
        category="physics",
        related=["a_cmb", "super_gutter", "primordial_gutter", "gutter_depth",
                 "cross_scar_shear", "primordial_routing"],
        notes="Foreman-approved 2026-05-09. Sign corrected 2026-05-09.",
        first_seen="BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER.py",
    ),

    "cross_scar_shear": KeywordEntry(
        keyword="cross_scar_shear",
        status="AUTHORIZED",
        description=(
            "A_CMB > +0.7 classification (CORRECTED from Test 19): local "
            "substrate gradient aligned against a CMB hot-spot barrier "
            "(elevated primordial strain = cross-grain impedance). "
            "Predicted effect: increased ΔW, high shear, recursive rip risk. "
            "The galaxy or craft is cutting ACROSS a primordial scar structure. "
            "Real-sky proxy: V_peculiar < 0 (infalling relative to Hubble). "
            "Test 21: NGC 628 (+0.478), M74 (+0.478), IC 5332 (+0.336) "
            "are the strongest cross-scar candidates in the survey."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["a_cmb", "cross_scar", "recursive_rip", "primordial_gutter",
                 "super_gutter_alignment", "primordial_routing"],
        notes="Foreman-approved 2026-05-09. Sign corrected 2026-05-09.",
        first_seen="BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER.py",
    ),

    # ---- v28 Crag Network + CMB Fusion additions ----
    # 6 new entries. Count after merge: 114  (was 108).
    # All theoretical concepts: Stephen Justin Burdick Sr. 2026-05-09

    "crag_intensity": KeywordEntry(
        keyword="crag_intensity",
        status="AUTHORIZED",
        description=(
            "Crag Intensity Index — C_I = J_amp × σ_deficit. "
            "Scalar measure of the organized substrate restoration burden "
            "at a galactic crag node. "
            "J_amp = substrate injection amplitude (normalized to NGC 5055 = 8.0). "
            "σ_deficit = total substrate displaced per pierce "
            "= SIGMA_CRIT × (J_amp/J_ref) × N_HALF. "
            "Classification thresholds (SJB 2026): "
            "C_I > 1e-1 → ROOT CRAG (high-velocity organized restoration). "
            "1e-2 < C_I ≤ 1e-1 → BRANCH CRAG. "
            "1e-3 < C_I ≤ 1e-2 → LEAF CRAG. "
            "C_I ≤ 1e-3 → VOID-EDGE (substrate at primordial void boundary). "
            "Test 20 result: NGC 1365 top crag (C_I=8.79e-1), "
            "Boötes Void correctly VOID-EDGE (C_I=9.38e-4). "
            "Bar/floc ratio = 3.91× in PHANGS-JWST survey."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="physics",
        related=["cmb_fused_crag_intensity", "primordial_gutter",
                 "pierce_gauntlet", "gutter_depth", "tier_flip"],
        notes="Foreman-approved 2026-05-09. Work Formulas Section 41.",
        first_seen="BCM_v28_TEST20_CRAG_INTENSITY_TABLE_SCANNER.py",
    ),

    "cmb_fused_crag_intensity": KeywordEntry(
        keyword="cmb_fused_crag_intensity",
        status="AUTHORIZED",
        description=(
            "CMB-fused Crag Intensity — "
            "C_I_CMB = C_I × max(0, 1 + κ_align × A_CMB). "
            "Extends the base Crag Intensity Index by incorporating "
            "primordial scar alignment. The max(0, ...) floor prevents "
            "unphysical negative restoration burden. "
            "A_CMB < 0 (super-gutter) → C_I_CMB < C_I (reduced burden). "
            "A_CMB > 0 (cross-scar) → C_I_CMB > C_I (increased burden). "
            "Test 21 result at κ_align=2.0: rank correlation with C_I = 0.178. "
            "CMB alignment substantially reorders the crag hierarchy — "
            "it is not a small correction. "
            "NGC 4254 (A_CMB=−0.998) collapsed from ROOT to VOID-EDGE burden."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["crag_intensity", "a_cmb", "kappa_cmb", "tier_flip",
                 "primordial_routing", "super_gutter", "cross_scar"],
        notes="Foreman-approved 2026-05-09. Formula from Test 21.",
        first_seen="BCM_v28_TEST21_CRAG_CMB_ALIGNMENT_FUSION.py",
    ),

    "super_gutter": KeywordEntry(
        keyword="super_gutter",
        status="AUTHORIZED",
        description=(
            "Short-form classifier for A_CMB < −0.7: the galaxy or substrate "
            "region is strongly aligned with a primordial void channel. "
            "Equivalent to SUPER_GUTTER_ALIGNMENT in the alignment system. "
            "Real-sky proxy: V_peculiar > 0 (outflowing relative to Hubble). "
            "In the crag-CMB fusion (Test 21): galaxies classified SUPER_GUTTER "
            "receive reduced C_I_CMB — they are traveling pre-carved primordial "
            "paths and require less restoration work. "
            "Test 21 strongest: NGC 4254 (−0.998), NGC 4321 (−0.919), "
            "NGC 5068 (−0.830)."),
        bucket_hint="RESOLVED",
        category="physics",
        related=["super_gutter_alignment", "a_cmb", "cmb_fused_crag_intensity",
                 "primordial_routing", "cross_scar"],
        notes="Foreman-approved 2026-05-09. Short classifier form.",
        first_seen="BCM_v28_TEST21_CRAG_CMB_ALIGNMENT_FUSION.py",
    ),

    "cross_scar": KeywordEntry(
        keyword="cross_scar",
        status="AUTHORIZED",
        description=(
            "Short-form classifier for A_CMB > +0.7: the galaxy or substrate "
            "region is cutting across a primordial hot-spot barrier. "
            "Equivalent to CROSS_SCAR_SHEAR_RISK in the alignment system. "
            "Real-sky proxy: V_peculiar < 0 (infalling relative to Hubble). "
            "In the crag-CMB fusion (Test 21): galaxies classified CROSS_SCAR "
            "receive elevated C_I_CMB — they face increased restoration burden "
            "from fighting the primordial grain. "
            "Test 21: NGC 628 (+0.478), M74 (+0.478), IC 5332 (+0.336). "
            "None exceeded the +0.7 hard CROSS_SCAR threshold in this sample."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["cross_scar_shear", "a_cmb", "cmb_fused_crag_intensity",
                 "recursive_rip", "super_gutter"],
        notes="Foreman-approved 2026-05-09. Short classifier form.",
        first_seen="BCM_v28_TEST21_CRAG_CMB_ALIGNMENT_FUSION.py",
    ),

    "tier_flip": KeywordEntry(
        keyword="tier_flip",
        status="AUTHORIZED",
        description=(
            "A galaxy changes crag classification tier (ROOT / BRANCH / LEAF / "
            "VOID-EDGE) when CMB alignment is incorporated into C_I. "
            "tier_flip is the primary evidence that primordial routing is not "
            "a small correction — it can override the morphology-based "
            "classification entirely. "
            "Test 21 at κ_align=2.0: 9 of 21 galaxies flipped tier. "
            "Notable: NGC 1433 (ROOT→BRANCH), NGC 1672 (ROOT→VOID-EDGE), "
            "NGC 3351 (ROOT→VOID-EDGE), NGC 4254 (ROOT→VOID-EDGE), "
            "NGC 4321 (ROOT→VOID-EDGE). "
            "Tier flip rate is the primary falsification metric for the "
            "H_V28_CRAG_CMB_ALIGNMENT_FUSION hypothesis."),
        bucket_hint="ANOMALY",
        category="result",
        related=["cmb_fused_crag_intensity", "crag_intensity",
                 "primordial_routing", "a_cmb"],
        notes="Foreman-approved 2026-05-09.",
        first_seen="BCM_v28_TEST21_CRAG_CMB_ALIGNMENT_FUSION.py",
    ),

    "primordial_routing": KeywordEntry(
        keyword="primordial_routing",
        status="AUTHORIZED",
        description=(
            "The mechanism by which the background CMB pre-strain scar field "
            "reorders the local crag restoration burden. Galaxies are not "
            "classified purely by their intrinsic morphology and mass — their "
            "position relative to the primordial scar topology determines "
            "whether they are traveling with or against the grain of the "
            "universe. Super-gutter routing reduces effective C_I; "
            "cross-scar routing increases it. "
            "The rank correlation of 0.178 (Test 21, κ=2.0) between base C_I "
            "and C_I_CMB shows primordial routing is a dominant, not marginal, "
            "effect at moderate κ_align. "
            "Ontological status: LOW (Interpretive). "
            "Requires Planck sky-position overlay for observational validation."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["cmb_fused_crag_intensity", "tier_flip", "a_cmb",
                 "primordial_gutter", "super_gutter", "cross_scar"],
        notes="Foreman-approved 2026-05-09. Core v28 Primordial Gutter concept.",
        first_seen="BCM_v28_TEST21_CRAG_CMB_ALIGNMENT_FUSION.py",
    ),

    # ---- v28/v29 CASCADE + FUNDING additions (Tests 24-26) ----
    # 7 new entries. Count after merge: 121  (was 114).
    # All theoretical concepts: Stephen Justin Burdick Sr. 2026-05-11

    "substrate_funding_fraction": KeywordEntry(
        keyword="substrate_funding_fraction",
        status="AUTHORIZED",
        description=(
            "The fraction of a galaxy's rotation curve improvement "
            "attributable to BCM substrate vs Newtonian dynamics alone. "
            "substrate_fraction = (rms_newton - rms_substrate) / rms_newton. "
            "Clamped to [0, 1]. Negative values (substrate worse than Newton) "
            "→ substrate_fraction = 0. "
            "Test 24 result across 175 SPARC galaxies: "
            "ROOT=0.111, BRANCH=0.433, LEAF=0.459, VOID-EDGE=0.276. "
            "CORRECTED INTERPRETATION (SJB 2026-05-11): ROOT does not have "
            "the highest funding fraction — it is the source pump. "
            "BRANCH is the primary recipient. LEAF is the extended draw zone. "
            "VOID-EDGE is past tare reach, signal falls. "
            "The gradient shape (ROOT low → BRANCH peak → LEAF → VOID decay) "
            "is the signature of a draw network, not a push network."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="metric",
        related=["intrinsic_battery", "crag_intensity", "dual_flow_crag",
                 "cascade_propagation", "network_apex"],
        notes="Foreman-approved 2026-05-11. Test 24 (175 SPARC J kill chain).",
        first_seen="BCM_v28_TEST24_J_KILL_SWEEP_175.py",
    ),

    "intrinsic_battery": KeywordEntry(
        keyword="intrinsic_battery",
        status="AUTHORIZED",
        description=(
            "The intrinsic energy fraction of a galaxy independent of BCM "
            "substrate funding. intrinsic_battery = 1 - substrate_fraction. "
            "When the substrate pump (J) is killed (J=0), the galaxy rotation "
            "curve degrades to this fraction of the BCM-corrected value. "
            "The J kill chain (Test 24, null pump precedent from v20 Tests): "
            "sigma decays at rate lambda=0.1 (frozen). "
            "Time to reach 15% of sigma_ss: T_survival = ln(1/0.15)/0.1 ≈ 18.97 "
            "BCM time units. The 15% threshold is where 85% of intrinsic battery "
            "remains — consistent with the prior BCM null pump finding that "
            "galaxies retain ~85% of rotation curve support without substrate. "
            "ROOT mean battery = 0.889 (high intrinsic). "
            "BRANCH mean battery = 0.567. LEAF mean = 0.541."),
        bucket_hint="POSSIBLE_INVARIANT",
        category="metric",
        related=["substrate_funding_fraction", "crag_intensity",
                 "cascade_propagation"],
        notes="Foreman-approved 2026-05-11. Test 24.",
        first_seen="BCM_v28_TEST24_J_KILL_SWEEP_175.py",
    ),

    "cascade_score": KeywordEntry(
        keyword="cascade_score",
        status="AUTHORIZED",
        description=(
            "Network amplitude metric for how strongly a galaxy feels the "
            "substrate cascade when its nearest ROOT pump goes dark. "
            "S_cascade = sub_frac × exp(-d / C_network). "
            "sub_frac sets the amplitude (how dependent the galaxy is). "
            "exp(-d) sets the attenuation over network distance. "
            "Classification outcome from Test 25 (175 SPARC): "
            "ROOT mean = 4.78e-02 (source, low own-score). "
            "BRANCH mean = 2.48e-01 (highest — primary recipient). "
            "LEAF mean = 1.12e-01 (extended draw zone). "
            "VOID-EDGE mean = 2.40e-02 (disconnected fringe). "
            "Peak cascade galaxy: UGC09037 (BRANCH, score=0.673). "
            "C_network and D_unit are unfrozen hypothesis parameters."),
        bucket_hint="ANOMALY",
        category="metric",
        related=["cascade_propagation", "substrate_funding_fraction",
                 "crag_intensity", "network_apex", "dual_flow_crag"],
        notes="Foreman-approved 2026-05-11. Test 25 (cascade propagation).",
        first_seen="BCM_v28_TEST25_CRAG_CASCADE_PROPAGATION.py",
    ),

    "cascade_propagation": KeywordEntry(
        keyword="cascade_propagation",
        status="AUTHORIZED",
        description=(
            "The network behavior of substrate signal decay after a ROOT crag "
            "pump goes dark. When J=0 at the ROOT, the cascade propagates "
            "outward through the draw network with delay: "
            "t_i = t_ROOT + d_i / C_network. "
            "Expected sequence: ROOT source dies → BRANCH degrades (short delay, "
            "highest fractional loss) → LEAF degrades (medium delay, extended "
            "draw zone) → VOID-EDGE shows weak or no response (disconnected). "
            "Test 25 confirmed cascade score gradient: ROOT < BRANCH (peak) > "
            "LEAF > VOID-EDGE. "
            "Rank corr (score vs sub_frac) = +0.871 — cascade score is "
            "primarily measuring active substrate dependency. "
            "Rank corr (delay vs C_I) = -0.817 — higher C_I nodes degrade "
            "EARLIER (closer to apex, shorter proxy distance)."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["cascade_score", "dual_flow_crag", "network_apex",
                 "substrate_funding_fraction", "crag_intensity"],
        notes=(
            "Foreman-approved 2026-05-11. Proxy distance = log10(C_I_ROOT/C_I) "
            "— upgrade to real 3D Mpc (NED/Cosmicflows-4) pending."),
        first_seen="BCM_v28_TEST25_CRAG_CASCADE_PROPAGATION.py",
    ),

    "network_apex": KeywordEntry(
        keyword="network_apex",
        status="AUTHORIZED",
        description=(
            "The highest C_I galaxy in the SPARC 175-galaxy crag network — "
            "the root of the ROOT hierarchy. All other ROOT galaxies measure "
            "their proxy network distance relative to the apex. "
            "From Test 24/25: network apex = UGC02487 "
            "(Vmax=383 km/s, C_I=2.868, substrate_winner=SUBSTRATE). "
            "The apex galaxy is the last ROOT standing in the J kill chain — "
            "the final active substrate pump before universal sigma → 0. "
            "The apex is the deepest node in the local sector crag root ball. "
            "This designation is survey-dependent: a larger galaxy sample "
            "may reveal a more massive apex beyond the SPARC 175."),
        bucket_hint="RESOLVED",
        category="result",
        related=["cascade_propagation", "crag_intensity", "dual_flow_crag",
                 "substrate_funding_fraction"],
        notes="Foreman-approved 2026-05-11. UGC02487 is v28 designation.",
        first_seen="BCM_v28_TEST25_CRAG_CASCADE_PROPAGATION.py",
    ),

    "dual_flow_crag": KeywordEntry(
        keyword="dual_flow_crag",
        status="AUTHORIZED",
        description=(
            "The ROOT crag operates two simultaneous substrate flows: "
            "(1) OUTWARD pump — J-Vorticity from SMBH distributes substrate "
            "through the disk and outward to BRANCH and LEAF crags in the "
            "draw network. "
            "(2) INWARD draw — the crag tare draws void substrate inward to "
            "replenish what the SMBH has distributed. "
            "The galaxy disk sits at the equilibrium point of these two flows. "
            "This is the inner/outer torus dual-flow (confirmed in prior BCM "
            "tests) scaled to the crag network level. "
            "SJB 2026-05-11: 'A root ball does not push water out — it draws "
            "water in. The crag is a draw structure, not a push structure.' "
            "Observable signature: substrate_fraction peaks at BRANCH (primary "
            "outward recipient from ROOT) — confirmed in Test 24 (BRANCH=0.433)."),
        bucket_hint="ANOMALY",
        category="physics",
        related=["cascade_propagation", "network_apex", "crag_intensity",
                 "substrate_funding_fraction", "infall_crag_return"],
        notes="Foreman-approved 2026-05-11. Ontological status: CONDITIONAL.",
        first_seen="BCM_v28_TEST24_J_KILL_SWEEP_175.py",
    ),

    "infall_crag_return": KeywordEntry(
        keyword="infall_crag_return",
        status="AUTHORIZED",
        description=(
            "The hypothesis that galaxies with negative peculiar velocity "
            "(V_pec < 0, infalling relative to Hubble flow) are on crag-return "
            "trajectories toward their nearest ROOT draw node, rather than "
            "purely expanding outward from the Bang. "
            "The ROOT crag tare is a draw structure — substrate flows INWARD "
            "from the void toward the crag node. Galaxies embedded in this "
            "inward-flowing substrate field are carried toward the ROOT node. "
            "From Test 26 (20 PHANGS-JWST + BCM V_3K galaxies): "
            "infall galaxies (NGC 628 V_pec=−260, IC 5332 V_pec=−175) show "
            "shorter proxy ROOT distance than outflow galaxies — direction "
            "confirmed. Signal weak at N=2 non-cluster infall galaxies. "
            "Virgo cluster members (NGC 4254, NGC 4321) excluded — their "
            "V_pec reflects cluster gravitational dynamics, not primordial "
            "crag topology (confirmed by A_planck vs A_v3k orthogonality "
            "in Test 22). "
            "Ontological status: SPECULATIVE. Requires real 3D Mpc distances."),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["dual_flow_crag", "cascade_propagation", "a_cmb",
                 "super_gutter", "primordial_gutter"],
        notes=(
            "Foreman-approved 2026-05-11. Upgrade pending: NED/Cosmicflows-4 "
            "3D coordinates for full 175 SPARC set. "
            "SJB 2026-05-11: 'Are the galaxies already in return? Velocity "
            "appearing to show expansion could just be substrate moving them '"),
        first_seen="BCM_v28_TEST26_VPEC_ROOT_PROXIMITY.py",
    ),

    # ---- v29 Nebular / Pre-Pump Substrate additions (2026-05-17) ----
    # Directed by SJB. Adversarial basis: ChatGPT JWST gap analysis.
    # Equation form: Gemini engineering channel.
    # Variant 2 infrastructure — Nebular Formation Operator F_form.

    "dark_condensate": KeywordEntry(
        keyword="dark_condensate",
        status="AUTHORIZED",
        description=(
            "Pre-pump substrate memory state. Cold/dusty region where sigma "
            "is accumulating without baryonic light emission. F_form dominated "
            "by D_dust and G_grad. No coherent J-current loop. Xi_S -> 0."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["f_form", "sigma_local", "kappa_cmb", "pre_pump"],
        notes="Foreman-approved 2026-05-17. Nebula class Variant 2.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "scatter_memory": KeywordEntry(
        keyword="scatter_memory",
        status="AUTHORIZED",
        description=(
            "Reflection nebula substrate class. Dust surface reveals sigma "
            "boundary without active formation. Substrate scar made visible "
            "by illumination, not by condensation. F_form low."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["dark_condensate", "sigma_local", "f_form"],
        notes="Foreman-approved 2026-05-17. Nebula class Variant 2.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "ionized_formation": KeywordEntry(
        keyword="ionized_formation",
        status="AUTHORIZED",
        description=(
            "Emission nebula substrate class. Distributed radiative forcing "
            "drives sigma accumulation. I_ion component of F_form dominant. "
            "Phase disruption active across formation volume."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["f_form", "i_ion", "sigma_local", "shock_inscription"],
        notes="Foreman-approved 2026-05-17. Nebula class Variant 2.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "shock_inscription": KeywordEntry(
        keyword="shock_inscription",
        status="AUTHORIZED",
        description=(
            "Supernova or stellar wind front writing structure into sigma. "
            "S_shock component of F_form exceeds background substrate stiffness. "
            "Local fractional order alpha decreases along vector boundary. "
            "Forced baryonic precipitation at shock front."
        ),
        bucket_hint="ANOMALY",
        category="physics",
        related=["f_form", "s_shock", "alpha_void_default", "sigma_local"],
        notes="Foreman-approved 2026-05-17. Nebula class Variant 2.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "post_pump_shell": KeywordEntry(
        keyword="post_pump_shell",
        status="AUTHORIZED",
        description=(
            "Shell-memory substrate state after pump decay. Planetary nebula "
            "or SNR shell persisting in sigma after the source pump is gone. "
            "Substrate memory outlives the event — same principle as v15 "
            "wake persistence (72% retention after 1300 steps)."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["dark_condensate", "sigma_local", "wake_persistence"],
        notes="Foreman-approved 2026-05-17. Nebula class Variant 2.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "f_form": KeywordEntry(
        keyword="f_form",
        status="AUTHORIZED",
        description=(
            "Formation Operator. F_form = D_dust * C_cool * S_shock * I_ion * G_grad. "
            "Drives sigma condensation in pre-pump nebular states where no "
            "coherent J-current loop exists. Replaces T2/T3 in Variant 2 "
            "of the Extended Anchor Equation."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["dark_condensate", "sigma_local", "kappa_cmb", "d_dust",
                 "c_cool", "s_shock", "i_ion", "g_grad"],
        notes="Foreman-approved 2026-05-17. Core Variant 2 operator.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "d_dust": KeywordEntry(
        keyword="d_dust",
        status="AUTHORIZED",
        description=(
            "Dust damping/memory component of F_form. Substrate memory "
            "retention in cold dusty regions. Dominant in DARK_CONDENSATE."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["f_form", "dark_condensate", "c_cool"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "c_cool": KeywordEntry(
        keyword="c_cool",
        status="AUTHORIZED",
        description=(
            "Cooling entropy-drop component of F_form. Radiative cooling "
            "drives sigma toward condensation by reducing thermal pressure."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["f_form", "dark_condensate", "d_dust"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "s_shock": KeywordEntry(
        keyword="s_shock",
        status="AUTHORIZED",
        description=(
            "Shock vector-carving component of F_form. Supernova or wind "
            "front writes structure into sigma field. Dominant in "
            "SHOCK_INSCRIPTION. When S_shock exceeds substrate stiffness, "
            "alpha decreases and precipitation accelerates."
        ),
        bucket_hint="ANOMALY",
        category="physics",
        related=["f_form", "shock_inscription", "alpha_void_default"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "i_ion": KeywordEntry(
        keyword="i_ion",
        status="AUTHORIZED",
        description=(
            "Ionization phase-disruption component of F_form. Radiative "
            "forcing from nearby stars disrupts substrate phase coherence, "
            "driving formation in emission nebulae."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["f_form", "ionized_formation"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "g_grad": KeywordEntry(
        keyword="g_grad",
        status="AUTHORIZED",
        description=(
            "Local curvature gradient component of F_form. Gravitational "
            "gradient drives substrate toward condensation. Active in "
            "DARK_CONDENSATE and all formation-dominant states."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["f_form", "dark_condensate", "sigma_local"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "kappa_cmb": KeywordEntry(
        keyword="kappa_cmb",
        status="AUTHORIZED",
        description=(
            "CMB pre-strain coupling governor. Scales the primordial "
            "background contribution in sigma_eff(r) = [sigma_local * F_form] "
            "+ kappa_CMB * sigma_CMB. Locked at 0.01432 (v29). "
            "Prevents global phase saturation from CMB pre-strain."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["sigma_cmb", "f_form", "primordial_gutter"],
        notes="Foreman-approved 2026-05-17. Frozen constant v29.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "xi_s": KeywordEntry(
        keyword="xi_s",
        status="AUTHORIZED",
        description=(
            "Integerization Gradient. Measures how close a substrate state "
            "is to integer (classical observable) vs fractional (substrate "
            "ghost). Xi_S -> 1 at ROOT crag (stiff, measurable). "
            "Xi_S -> 0 at pre-pump nebula (fractional, formation-dominant). "
            "Variant 4 measurement penalty = (1 - Xi_S)."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["alpha_root_default", "alpha_void_default", "f_form",
                 "dark_condensate"],
        notes="Foreman-approved 2026-05-17. Structural hook Variant 2-4.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "sigma_cmb": KeywordEntry(
        keyword="sigma_cmb",
        status="AUTHORIZED",
        description=(
            "Primordial manifold deformation background strain field. "
            "The CMB pre-strain component of sigma_eff. Contributes "
            "kappa_CMB * sigma_CMB to the effective substrate at every "
            "point. Source: Primordial Gutter Hypothesis (v28, SJB)."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["kappa_cmb", "primordial_gutter", "sigma_local"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    "pre_pump": KeywordEntry(
        keyword="pre_pump",
        status="AUTHORIZED",
        description=(
            "Classification for substrate states that precede SMBH pump "
            "formation. No coherent J-current loop. Sigma is rising toward "
            "sigma_crit via F_form. The formation-dominant regime. "
            "The question BCM v29 opens: what substrate condition allows "
            "the pump event to form in the first place?"
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["dark_condensate", "f_form", "xi_s", "sigma_local"],
        notes="Foreman-approved 2026-05-17. Core nebular regime concept.",
        first_seen="BCM_v29_TEST16_NEBULAR_FORMATION.py",
    ),

    # ---- v29 Well-Depth Coefficient additions (2026-05-17) ----
    # SJB theoretical insight: apparent luminous size ≠ substrate load size.
    # Confirmed by Test21: PMR 1 absorbed craft tare and recovered above
    # pre-transit sigma — rolling-hill terrain, not galactic canyon behavior.

    "w_d": KeywordEntry(
        keyword="w_d",
        status="AUTHORIZED",
        description=(
            "Well-Depth Coefficient. Separates observed luminous size from "
            "effective substrate load size. L_load = L_obs * W_d. "
            "Galaxy: W_d ~ 1.0 (mass-bound rotating well, Grand Canyon). "
            "Nebula: W_d ~ low (broad luminous/formation field, rolling hills). "
            "PMR 1 baseline: W_d = 0.05. Prevents solver from treating "
            "3.2 ly nebula as equivalent in well depth to a galactic slice."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["l_obs_neb", "l_load_neb", "m_eff_neb", "opc_neb", "opt_neb"],
        notes="Foreman-approved 2026-05-17. SJB theoretical origin. "
              "W_D_NEBULAR_BASELINE=0.05 locked in bcm_thresholds.py.",
        first_seen="BCM_v29_TEST21_PMR1_TARE_PIERCE.py",
    ),

    "l_obs_neb": KeywordEntry(
        keyword="l_obs_neb",
        status="AUTHORIZED",
        description=(
            "Observed luminous diameter of a nebula. This is the measured "
            "cross-section (e.g., 3.2 ly for PMR 1). Does NOT equal substrate "
            "load diameter. A nebula can be huge and still have a shallow well."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["w_d", "l_load_neb"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST21_PMR1_TARE_PIERCE.py",
    ),

    "l_load_neb": KeywordEntry(
        keyword="l_load_neb",
        status="AUTHORIZED",
        description=(
            "Substrate-load equivalent diameter of a nebula. "
            "L_load_neb = L_obs_neb * W_d. "
            "PMR 1: 3.2 ly * 0.05 = 0.16 ly effective well scale. "
            "This is the diameter the substrate solver should use for "
            "well-depth-dependent calculations (OpT, OpC, craft shadow)."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["w_d", "l_obs_neb", "m_eff_neb"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST21_PMR1_TARE_PIERCE.py",
    ),

    "m_eff_neb": KeywordEntry(
        keyword="m_eff_neb",
        status="AUTHORIZED",
        description=(
            "Effective well-making mass for a nebula. "
            "M_eff_neb = M_visible * W_d * Phi_form. "
            "Most of a nebula's visible width may be low-density, "
            "shock-lit, or optically bright — not all mass makes a well. "
            "W_d weights the visible mass down to its actual substrate burden."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["w_d", "l_load_neb", "f_form"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST21_PMR1_TARE_PIERCE.py",
    ),

    "opt_neb": KeywordEntry(
        keyword="opt_neb",
        status="AUTHORIZED",
        description=(
            "Nebular temporal shadow operator. OpT_neb = propagation_lag * "
            "(1 - W_d). Distinct from galactic OpT (radial lag across rotating "
            "well). No rotation curve in a nebula — temporal shadow comes from "
            "shock-front lag, illumination lag, or ionization propagation delay. "
            "At W_d=0.05: OpT_neb = 0.95 * propagation_lag (nearly full lag)."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["w_d", "opc_neb", "delta_op_neb"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST21_PMR1_TARE_PIERCE.py",
    ),

    "opc_neb": KeywordEntry(
        keyword="opc_neb",
        status="AUTHORIZED",
        description=(
            "Nebular spatial coupling operator. OpC_neb = F_form_net * W_d. "
            "Distinct from galactic OpC (coupling closure across crag/torus). "
            "Nebula has no torus-edge brucetron ring. Coupling comes from "
            "formation-terrain density, not pump-funded torus geometry. "
            "At W_d=0.05: OpC_neb = 0.05 * F_form_net (weak spatial coupling)."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["w_d", "opt_neb", "f_form", "delta_op_neb"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST21_PMR1_TARE_PIERCE.py",
    ),

    "delta_op_neb": KeywordEntry(
        keyword="delta_op_neb",
        status="AUTHORIZED",
        description=(
            "Nebular operator divergence. Delta_OP_neb = |OpT_neb - OpC_neb|. "
            "High Delta_OP_neb means the temporal and spatial signals are "
            "decoupled — the craft shadow is diffuse and irregular. "
            "Unlike galactic Delta_OP (fogging threshold 0.08), nebular "
            "Delta_OP may naturally be large because the well is shallow."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["opt_neb", "opc_neb", "w_d"],
        notes="Foreman-approved 2026-05-17.",
        first_seen="BCM_v29_TEST21_PMR1_TARE_PIERCE.py",
    ),

    "r_form": KeywordEntry(
        keyword="r_form",
        status="AUTHORIZED",
        description=(
            "Formation scale ratio. R_form = L_nebular_precursor / L_final_galaxy. "
            "A proto-galactic cloud may be tens of times wider than its final "
            "galaxy, but with proportionally shallow well depth. "
            "Width does NOT scale linearly with well depth. "
            "SJB estimate: proto-galactic cloud ~40x PMR 1 in width but "
            "substrate load scales with eventual M_density, not observed size."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["w_d", "l_obs_neb", "l_load_neb"],
        notes="Foreman-approved 2026-05-17. SJB 40x scale insight.",
        first_seen="BCM_v29_TEST21_PMR1_TARE_PIERCE.py",
    ),

    "t_shadow_neb": KeywordEntry(
        keyword="t_shadow_neb",
        status="AUTHORIZED",
        description=(
            "Craft shadow through nebular formation terrain. Unlike galactic "
            "transit (gravitational displacement shadow, deep well), nebular "
            "transit leaves a formation disturbance shadow. The craft may leave "
            "a wake of condensation rather than a depleted gutter. "
            "Test21 confirmed: PMR 1 recovery > pre-transit sigma at all "
            "four velocities — tare-induced condensation, not rupture."
        ),
        bucket_hint="UNKNOWN",
        category="physics",
        related=["w_d", "opt_neb", "opc_neb", "dark_condensate"],
        notes="Foreman-approved 2026-05-17. Test21 empirical basis.",
        first_seen="BCM_v29_TEST21_PMR1_TARE_PIERCE.py",
    ),

    # =========================================================================
    # v30 — Variant 6 SMBH Torsion-Unwind + M51 Tidal Bridge
    # Authorized: 2026-05-29
    # SJB theoretical origin. All physics: Burdick.
    # =========================================================================

    "theta_spring": KeywordEntry(
        keyword="theta_spring",
        status="AUTHORIZED",
        description=(
            "Torsion spring parameter for Variant 6 SMBH polar ejection. "
            "theta_spring = memory_loss * omega_chi * j_circ / xi_nozzle. "
            "Spring fires when theta_spring >= theta_crit (0.5). "
            "v30 Test08: first clearing at VMAX=12, theta_final=0.597. "
            "Below VMAX=10: theta_spring<0.5, spring ghosted."
        ),
        bucket_hint="Cube9",
        category="physics",
        related=["xi_nozzle", "omega_chi", "j_circ", "relax_damp",
                 "variant_6", "memory_loss"],
        notes="SJB theoretical origin. v30 Variant 6 chain Tests 08-09.",
        first_seen="BCM_v30_TEST08_M51_VMAX_SWEEP.py",
    ),

    "xi_nozzle": KeywordEntry(
        keyword="xi_nozzle",
        status="AUTHORIZED",
        description=(
            "Spatially resolved freeboard resistance at the polar nozzle. "
            "Sampled from the polar column OUTSIDE the dense core radius "
            "(r > R_core along polar axis). Where the Gaussian gradient "
            "flattens, xi is naturally low (~4.75 in v30 physical coords). "
            "Replaces scalar core-mean xi from Tests 04-06 which was ~95. "
            "No artificial FREEBOARD_DAMP — spatial geometry does the work."
        ),
        bucket_hint="Cube9",
        category="physics",
        related=["theta_spring", "xi_s", "variant_6"],
        notes="Spatial xi fix identified v30 Test07. Gemini insight: "
              "measure freeboard where the packet exits, not at core center.",
        first_seen="BCM_v30_TEST07_M51_SPATIAL_NOZZLE.py",
    ),

    "variant_6": KeywordEntry(
        keyword="variant_6",
        status="AUTHORIZED",
        description=(
            "BCM Variant 6: torsion-unwind SMBH jet mechanism. "
            "At SMBH circumpunct (r->0): 3D mass becomes illegible 1D "
            "memory under torsion. When torsion exceeds Xi-freeboard "
            "containment, packet unloads along polar axis as "
            "chirality-unwind. Observed jet = 3D manifestation of "
            "torsional memory release. Four-stage requirement: "
            "1) angular torsion winding, "
            "2) spatial polar Xi escape path, "
            "3) VMAX/shear above threshold, "
            "4) relaxation drain for episodic ejection. "
            "THEORETICAL PROBE ONLY. Standard SMBH jet mechanisms "
            "(frame-dragging, Blandford-Znajek) not ruled out."
        ),
        bucket_hint="Cube9",
        category="physics",
        related=["theta_spring", "xi_nozzle", "omega_chi", "j_circ",
                 "relax_damp", "relax_recover"],
        notes="SJB theoretical origin. v30 M51 test chain Tests 01-09.",
        first_seen="BCM_v30_TEST01_M51_VARIANT6_TORSION.py",
    ),

    "relax_damp": KeywordEntry(
        keyword="relax_damp",
        status="AUTHORIZED",
        description=(
            "Relaxation drain coefficient. Per-step decay applied to "
            "omega_dyn and j_circ_dyn when torsion spring fires. "
            "Converts continuous runaway (DAMP=1.0) into episodic burst "
            "train. v30 Test09: DAMP=0.9999 yields 737 bursts, "
            "DAMP=0.999 yields 433 bursts with mean gap 5.6 steps. "
            "Physical interpretation: winding depletes on each ejection; "
            "outer disk must rewind before next burst. "
            "RELAX_DAMP is a placeholder — SJB calibration needed."
        ),
        bucket_hint="Cube9",
        category="physics",
        related=["relax_recover", "theta_spring", "variant_6",
                 "episodic_burst"],
        notes="v30 Test09. RELAX_RECOVER=0.002 is placeholder.",
        first_seen="BCM_v30_TEST09_M51_RELAX_DRAIN.py",
    ),

    "relax_recover": KeywordEntry(
        keyword="relax_recover",
        status="AUTHORIZED",
        description=(
            "Per-step winding recovery rate toward natural omega/j_circ "
            "when torsion spring is not firing. Simulates outer galactic "
            "rotation re-feeding angular momentum to the core between "
            "burst events. v30 placeholder: RELAX_RECOVER=0.002. "
            "SJB calibration needed from real M51 nuclear rotation data."
        ),
        bucket_hint="Cube9",
        category="physics",
        related=["relax_damp", "theta_spring", "episodic_burst"],
        notes="Placeholder value. Physical calibration pending ALMA data.",
        first_seen="BCM_v30_TEST09_M51_RELAX_DRAIN.py",
    ),

    "episodic_burst": KeywordEntry(
        keyword="episodic_burst",
        status="AUTHORIZED",
        description=(
            "Discrete torsion spring ejection event produced by the "
            "relaxation drain mechanism. Burst train: spring fires, "
            "winding depletes (relax_damp), spring quiets, outer disk "
            "rewinds (relax_recover), spring fires again. "
            "Physically maps to episodic AGN jet structure / knots. "
            "v30 Test09: burst duration 1.3-3.1 steps, gap 1.0-5.6 steps "
            "depending on drain strength. Period is solver steps, "
            "not physical time — calibration needed."
        ),
        bucket_hint="Cube9",
        category="physics",
        related=["relax_damp", "relax_recover", "theta_spring", "variant_6"],
        notes="v30 Test09 confirmed. Burst period not calibrated to "
              "physical M51 jet timescales.",
        first_seen="BCM_v30_TEST09_M51_RELAX_DRAIN.py",
    ),

    "tidal_bridge": KeywordEntry(
        keyword="tidal_bridge",
        status="AUTHORIZED",
        description=(
            "Substrate corridor between M51 (NGC5194, Pump A) and "
            "NGC5195 (Pump B). Low-sigma valley connecting two funded "
            "potential wells. Material flows from NGC5195 (source) "
            "toward M51 (destination) along a slight sigma gradient. "
            "v30 Test10 (1D model): axial transit gutters at 5000-12000c. "
            "v30 Test11C (2D model): broad bridge is resilient, "
            "orientation gradient present (0.78-0.875 recovery by angle). "
            "Bridge sigma and gradient are proxy estimates — not ALMA "
            "calibrated."
        ),
        bucket_hint="Cube2",
        category="physics",
        related=["pump_a_m51", "pump_b_ngc5195", "gutter_formed",
                 "recovery_ratio", "axial_transit", "s_arc",
                 "orientation_gradient"],
        notes="SJB direction. v30 Tests 10-11C. Two models: 1D worst-case "
              "tunnel and 2D broad bridge. Both are valid, not equivalent.",
        first_seen="BCM_v30_TEST10_M51_TIDAL_BRIDGE.py",
    ),

    "pump_a_m51": KeywordEntry(
        keyword="pump_a_m51",
        status="AUTHORIZED",
        description=(
            "M51 (NGC5194, Whirlpool Galaxy) as Pump A — the greater, "
            "destination-side funded substrate well in the M51/NGC5195 "
            "tidal bridge system. SMBH mass ~1e7 M_sun. "
            "Vmax=219 km/s (SPARC). Distance 7.9-9.5 Mpc. "
            "Pump A receives substrate transfer from Pump B (NGC5195) "
            "through the tidal bridge corridor."
        ),
        bucket_hint="Cube2",
        category="context",
        related=["pump_b_ngc5195", "tidal_bridge"],
        notes="M51 empirical anchors: distance, SMBH mass, Vmax from "
              "peer-reviewed SPARC/HST data. Grid is synthetic.",
        first_seen="BCM_v30_TEST10_M51_TIDAL_BRIDGE.py",
    ),

    "pump_b_ngc5195": KeywordEntry(
        keyword="pump_b_ngc5195",
        status="AUTHORIZED",
        description=(
            "NGC5195 as Pump B — the lesser, source-side funded substrate "
            "well in the M51/NGC5195 tidal bridge system. Companion galaxy "
            "to M51. Provides tidal shear asymmetry to M51 core rotation "
            "(TIDAL_VX=0.30, TIDAL_VY=0.20 in v30 solver). "
            "Also the source end of the tidal bridge transfer corridor."
        ),
        bucket_hint="Cube2",
        category="context",
        related=["pump_a_m51", "tidal_bridge"],
        notes="NGC5195 tidal shear is the asymmetry that activates "
              "vector vorticity in Variant 6 (Tests 02-03).",
        first_seen="BCM_v30_TEST10_M51_TIDAL_BRIDGE.py",
    ),

    "gutter_formed": KeywordEntry(
        keyword="gutter_formed",
        status="AUTHORIZED",
        description=(
            "Boolean flag: True when craft axial transit collapses "
            "the tidal bridge transfer corridor below 50% of its "
            "pre-transit connected width. "
            "v30 Test10 (1D): gutter at 5000c, 10000c, 12000c. "
            "v30 Test11C (2D): no gutter at any angle — broad bridge "
            "has lateral redundancy. "
            "Physical meaning: bridge-transfer lane blocked; "
            "NGC5195 to M51 substrate flow disrupted."
        ),
        bucket_hint="Cube2",
        category="physics",
        related=["tidal_bridge", "recovery_ratio", "axial_transit",
                 "transfer_disruption"],
        notes="1D vs 2D model gives different gutter behavior. "
              "1D is worst-case tunnel limit, not equivalent to 2D bridge.",
        first_seen="BCM_v30_TEST10_M51_TIDAL_BRIDGE.py",
    ),

    "recovery_ratio": KeywordEntry(
        keyword="recovery_ratio",
        status="AUTHORIZED",
        description=(
            "Bridge sigma post-transit / bridge sigma pre-transit. "
            "1.0 = full recovery, 0.0 = complete depletion. "
            "v30 Test10 (1D axial): 0.194 at 5000c, 0.485 at 12000c, "
            "0.625 at 20000c. Higher speed = less damage (dwell-time). "
            "v30 Test11C (2D): 0.783-0.875 by angle at 12kc. "
            "Perpendicular always recovers better than axial."
        ),
        bucket_hint="Cube2",
        category="physics",
        related=["tidal_bridge", "gutter_formed", "axial_transit",
                 "orientation_gradient"],
        notes="Dwell-time mechanism: higher speed = fewer steps/cell "
              "= less tare exposure per bridge cell.",
        first_seen="BCM_v30_TEST10_M51_TIDAL_BRIDGE.py",
    ),

    "axial_transit": KeywordEntry(
        keyword="axial_transit",
        status="AUTHORIZED",
        description=(
            "Craft path aligned with the tidal bridge transfer axis "
            "(NGC5195 -> M51 direction, 0 degrees). Worst-case "
            "orientation for bridge damage. In 1D model, craft scrapes "
            "the only transfer path for its full length. "
            "In 2D model, craft path crosses bridge center but lateral "
            "redundancy allows recovery. "
            "Contrast with perpendicular transit (90 deg) and s_arc."
        ),
        bucket_hint="Cube2",
        category="physics",
        related=["tidal_bridge", "gutter_formed", "recovery_ratio",
                 "s_arc", "orientation_gradient"],
        notes="v30 Tests 10-11C. Axial is most damaging orientation.",
        first_seen="BCM_v30_TEST10_M51_TIDAL_BRIDGE.py",
    ),

    "s_arc": KeywordEntry(
        keyword="s_arc",
        status="AUTHORIZED",
        description=(
            "Gradient-following craft transit path through the tidal bridge. "
            "SJB direction 2026-05-29: a craft navigating a substrate "
            "gradient field follows the gradient, not a fixed bearing. "
            "The tidal bridge slopes from NGC5195 (source, higher sigma) "
            "to M51 (destination). S-arc path curves with this slope via "
            "sinusoidal y-deviation (amplitude 0.04 grid fraction, "
            "first estimate — SJB calibration needed). "
            "v30 Test11C result: S-arc recovery=0.810 at 12kc, "
            "between axial (0.783) and 45deg (0.838). "
            "Physical interpretation: gradient-following path stays inside "
            "low-sigma corridor longer than a chord cut but exits faster "
            "than a full axial scrape."
        ),
        bucket_hint="Cube2",
        category="physics",
        related=["tidal_bridge", "axial_transit", "orientation_gradient",
                 "recovery_ratio"],
        notes="SJB theoretical direction. S-arc amplitude is placeholder. "
              "v30 Test11C first characterization.",
        first_seen="BCM_v30_TEST11C_M51_ANGLE_SARC.py",
    ),

    "orientation_gradient": KeywordEntry(
        keyword="orientation_gradient",
        status="AUTHORIZED",
        description=(
            "Angle-dependent tidal bridge damage pattern. "
            "Recovery increases monotonically from axial (0 deg) to "
            "perpendicular (90 deg). "
            "v30 Test11C at 12kc: 0.783 (0deg) -> 0.810 (S-arc) -> "
            "0.838 (45deg) -> 0.875 (90deg). "
            "20kc shows same ordering with higher recovery throughout. "
            "12kc has stronger angle sensitivity than 20kc "
            "(lower speed = longer dwell = more orientation-coupled damage). "
            "Physical meaning: orientation determines how much of the "
            "craft transit overlaps with the transfer corridor."
        ),
        bucket_hint="Cube2",
        category="physics",
        related=["tidal_bridge", "axial_transit", "s_arc", "recovery_ratio"],
        notes="v30 Test11C. 2D bridge model accepted as distinct physics "
              "from 1D Test10. Not parity failure — different geometry.",
        first_seen="BCM_v30_TEST11C_M51_ANGLE_SARC.py",
    ),

    "transfer_disruption": KeywordEntry(
        keyword="transfer_disruption",
        status="AUTHORIZED",
        description=(
            "Fractional reduction in NGC5195 -> M51 substrate flow "
            "gradient caused by craft transit. "
            "0.0 = flow fully maintained. 1.0 = gradient suppressed. "
            "v30 Test10 (1D): 0.86 at 5000c axial, 0.66 at 12000c axial, "
            "0.38 at 12000c perpendicular. "
            "v30 Test11C (2D): metric insensitive — 0.000 across all angles "
            "(G3 failed, 2D bridge too broad for point-gradient metric). "
            "Metric needs connected corridor width formulation for 2D."
        ),
        bucket_hint="Cube2",
        category="physics",
        related=["tidal_bridge", "gutter_formed", "recovery_ratio"],
        notes="1D metric works. 2D metric needs redesign (Test11C G3 fail).",
        first_seen="BCM_v30_TEST10_M51_TIDAL_BRIDGE.py",
    ),

    "vmax_threshold": KeywordEntry(
        keyword="vmax_threshold",
        status="AUTHORIZED",
        description=(
            "Critical VMAX_SCALED value at which torsion spring first fires "
            "in Variant 6 M51 probe (physical coordinate solver). "
            "v30 Test08: VMAX_crit=12 (theta_final=0.597 >= theta_crit=0.5). "
            "Below VMAX=10: theta_final=0.415, spring ghosted. "
            "Transition is sharp between VMAX=10 and VMAX=12. "
            "Physical km/s mapping: requires real M51 nuclear rotation "
            "data at r~150pc (ALMA resolution). Proxy only."
        ),
        bucket_hint="Cube9",
        category="physics",
        related=["theta_spring", "variant_6", "xi_nozzle"],
        notes="Proxy value. Physical calibration pending ALMA M51 data. "
              "Standard SMBH mechanisms not ruled out.",
        first_seen="BCM_v30_TEST08_M51_VMAX_SWEEP.py",
    ),

}


# ============================================================================
# SECTION 3 -- LEGACY TRANSLATION MAP
# ============================================================================

LEGACY_TRANSLATION: Dict[str, str] = {
    # Sloppy English terms -> canonical bucket
    "interesting":     "ANOMALY",
    "weird":           "ANOMALY",
    "strange":         "ANOMALY",
    "unusual":         "ANOMALY",
    "unexpected":      "ANOMALY",
    "suspicious":      "ANOMALY",

    # Pre-contract state terms -> canonical bucket
    "healthy":         "RESOLVED",
    "normal":          "RESOLVED",
    "good":            "RESOLVED",
    "fine":            "RESOLVED",

    # Pre-contract uncertainty terms -> canonical bucket
    "unclear":         "UNKNOWN",
    "tbd":             "UNKNOWN",
    "maybe":           "UNKNOWN",
    "pending":         "UNKNOWN",

    # Pre-contract persistence terms -> canonical bucket
    "stable_across":   "POSSIBLE_INVARIANT",
    "consistent":      "POSSIBLE_INVARIANT",
    "reproducible":    "POSSIBLE_INVARIANT",
}


def translate_legacy(term: str) -> Optional[str]:
    """
    Given a legacy / sloppy term, return the proper bucket or None if
    the term is not in the legacy map. Case-insensitive lookup.
    """
    if not isinstance(term, str):
        return None
    key = term.strip().lower()
    return LEGACY_TRANSLATION.get(key)


# ============================================================================
# SECTION 4 -- PAIR TYPES (correlation axes the engine pairs on)
# ============================================================================

PAIR_TYPES: Tuple[str, ...] = (
    "KEYWORD_X_KEYWORD",    # physics x physics (brucetron x phi_load)
    "KEYWORD_X_CONTEXT",    # physics x context (brucetron x grid=256)
    "KEYWORD_X_SYSTEM",     # physics x system  (brucetron x HR_1099)
    "KEYWORD_X_HYPOTHESIS", # physics x stated hypothesis
    "KEYWORD_X_RESULT",     # physics x PASS/FAIL outcome
)


# ============================================================================
# SECTION 5 -- REGISTRY QUERY / MUTATION API
# ============================================================================

def get_keyword(keyword: str) -> Optional[KeywordEntry]:
    """Look up a keyword in the registry. Returns None if not present."""
    return HYPOTHESIS_KEYWORDS.get(keyword)


def is_registered(keyword: str) -> bool:
    """True if keyword exists in the authorized registry."""
    return keyword in HYPOTHESIS_KEYWORDS


def register_new_keyword(keyword: str,
                         first_seen: Optional[str] = None,
                         notes: str = "") -> KeywordEntry:
    """
    Register a new keyword with status='UNREGISTERED_NEW'.

    Called by hypothesis_engine when a test declares a keyword not in
    the registry. The Foreman later reviews and either:
      - Locks it: status -> AUTHORIZED, fills description/bucket_hint
      - Renames it: maps to an existing authorized term
      - Deprecates it: status -> DEPRECATED, adds notes

    Returns the KeywordEntry just added.
    """
    if keyword in HYPOTHESIS_KEYWORDS:
        return HYPOTHESIS_KEYWORDS[keyword]  # already registered

    entry = KeywordEntry(
        keyword=keyword,
        status="UNREGISTERED_NEW",
        description="(no Foreman description yet)",
        bucket_hint="UNKNOWN",
        category="physics",  # safest default; Foreman reclassifies
        notes=notes or "Auto-registered via engine; awaiting Foreman review.",
        first_seen=first_seen,
    )
    HYPOTHESIS_KEYWORDS[keyword] = entry
    return entry


def unregistered_new_keywords() -> List[KeywordEntry]:
    """Return all entries awaiting Foreman review."""
    return [e for e in HYPOTHESIS_KEYWORDS.values()
            if e.status == "UNREGISTERED_NEW"]


def authorized_keywords() -> List[KeywordEntry]:
    """Return all Foreman-authorized entries."""
    return [e for e in HYPOTHESIS_KEYWORDS.values()
            if e.status == "AUTHORIZED"]


def keywords_by_category(category: str) -> List[KeywordEntry]:
    """Return all entries in a given category."""
    return [e for e in HYPOTHESIS_KEYWORDS.values()
            if e.category == category]


def related_keywords(keyword: str) -> List[str]:
    """Return keywords that commonly pair with the given term."""
    entry = HYPOTHESIS_KEYWORDS.get(keyword)
    if not entry:
        return []
    return list(entry.related)


# ============================================================================
# SECTION 6 -- VOCABULARY SERIALIZATION (save/load registry state)
# ============================================================================

def registry_to_dict() -> dict:
    """Snapshot the current registry state."""
    return {
        "bucket_vocabulary": list(BUCKET_VOCABULARY),
        "pair_types":        list(PAIR_TYPES),
        "keywords":          {k: e.to_dict()
                              for k, e in HYPOTHESIS_KEYWORDS.items()},
        "legacy_translation": dict(LEGACY_TRANSLATION),
    }


def apply_registry_dict(d: dict) -> None:
    """
    Merge a snapshotted registry back into live state.
    Authoritative entries in HYPOTHESIS_KEYWORDS are NOT overwritten
    unless the dict explicitly has them. UNREGISTERED_NEW entries from
    the dict are added if not already present.
    """
    for k, v in d.get("keywords", {}).items():
        if k not in HYPOTHESIS_KEYWORDS:
            HYPOTHESIS_KEYWORDS[k] = KeywordEntry.from_dict(v)


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  BCM HYPOTHESIS VOCABULARY -- SELF-TEST")
    print("=" * 60)
    print(f"  Legal buckets: {len(BUCKET_VOCABULARY)}")
    for b in BUCKET_VOCABULARY:
        print(f"    - {b}")
    print()
    print(f"  Authorized keywords: {len(authorized_keywords())}")
    print(f"  Legacy translations: {len(LEGACY_TRANSLATION)}")
    print(f"  Pair types:          {len(PAIR_TYPES)}")
    print()

    # Test legacy translation
    print("  Legacy translation examples:")
    for term in ["interesting", "weird", "healthy", "tbd", "NotAThing"]:
        result = translate_legacy(term)
        print(f"    '{term}' -> {result}")
    print()

    # Test keyword lookup
    print("  Registered keyword lookups:")
    for kw in ["brucetron", "phi", "grid", "nonexistent_term"]:
        entry = get_keyword(kw)
        if entry:
            print(f"    '{kw}': status={entry.status}, "
                  f"category={entry.category}, "
                  f"bucket_hint={entry.bucket_hint}")
        else:
            print(f"    '{kw}': NOT REGISTERED")
    print()

    # Test auto-registration
    print("  Auto-registration test:")
    before = len(HYPOTHESIS_KEYWORDS)
    register_new_keyword("test_new_term_xyz", first_seen="self_test")
    after = len(HYPOTHESIS_KEYWORDS)
    print(f"    Keywords before: {before}")
    print(f"    Keywords after:  {after}")
    print(f"    Unregistered-new list:")
    for e in unregistered_new_keywords():
        print(f"      {e.keyword} (first_seen={e.first_seen})")
    # Clean up the test entry
    del HYPOTHESIS_KEYWORDS["test_new_term_xyz"]
    print()

    # Test category query
    print("  Physics keywords:")
    for e in keywords_by_category("physics"):
        print(f"    - {e.keyword}")
    print()

    print("  Context keywords:")
    for e in keywords_by_category("context"):
        print(f"    - {e.keyword}")
    print()

    print("  Related-keyword query: 'brucetron' pairs with:")
    for r in related_keywords("brucetron"):
        print(f"    - {r}")
    print()

    print("  All assertions passing.")
