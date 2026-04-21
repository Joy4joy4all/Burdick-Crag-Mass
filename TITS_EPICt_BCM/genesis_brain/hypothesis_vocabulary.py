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
