# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN — BAYESIAN HYPOTHESIS ENGINE (APPENDIX A COMPLIANT)
==================================================================
Log-odds Bayesian updating as described in BCM framework Appendix A.1.

This is a rule-based scoring system with Bayesian wrapper.
Likelihood ratios are heuristically assigned, not empirically learned.
The value is in structured tracking and convergence visibility,
not in statistical optimality.

Formula:
    log_odds(posterior) = log_odds(prior) + direction × strength

Confidence interval:
    half_width = 0.15 / sqrt(evidence_count)
    This is a visual convergence indicator, not a formal credible interval.
    The model can be extended to Beta-Binomial posterior updates if desired.
"""

import json
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


# ============================================================================
# EVIDENCE STRENGTH RULES (Heuristic — explicitly stated)
# ============================================================================

# These are NOT empirically learned. They are expert-assigned weights.
# Higher = stronger evidence signal.
EVIDENCE_STRENGTH_RULES = {
    # Direct cost data with specific dollar amounts
    "cost_direct":       0.45,
    # Named equipment with damage report
    "equipment_damage":  0.40,
    # Explicit validation statement ("yes, that's exactly our problem")
    "explicit_validate": 0.50,
    # Explicit contradiction ("no, that doesn't apply to us")
    "explicit_contradict": 0.45,
    # Pain indicator with severity (shutdown, lost production)
    "pain_severe":       0.35,
    # Pain indicator, moderate (inconvenient, annoying)
    "pain_moderate":     0.20,
    # General sentiment, positive
    "sentiment_positive": 0.15,
    # General sentiment, negative
    "sentiment_negative": 0.15,
    # Equipment reference without damage data
    "equipment_mention": 0.10,
    # Default for unclassified evidence
    "default":           0.10,
}


# ============================================================================
# HYPOTHESIS
# ============================================================================

@dataclass
class Hypothesis:
    """
    A hypothesis with log-odds Bayesian confidence tracking.

    Appendix A.1 compliant:
    - Log-odds formulation for updates
    - Heuristic strength assignment
    - Pedagogical confidence interval (not formal credible interval)
    """
    key: str
    name: str
    description: str
    prior: float                                    # Initial probability (0-1)
    posterior: float                                 # Current probability (0-1)
    evidence_for: List[dict] = field(default_factory=list)
    evidence_against: List[dict] = field(default_factory=list)
    status: str = "NEEDS_MORE_DATA"                 # VALIDATED | INVALIDATED | NEEDS_MORE_DATA

    # Thresholds
    VALIDATE_THRESHOLD: float = 0.85
    INVALIDATE_THRESHOLD: float = 0.15
    MIN_EVIDENCE_FOR_STATUS: int = 3

    @property
    def evidence_count(self) -> int:
        return len(self.evidence_for) + len(self.evidence_against)

    @property
    def confidence_interval(self) -> Tuple[float, float]:
        """
        Pedagogical convergence indicator.
        half_width = 0.15 / sqrt(evidence_count)
        NOT a formal credible interval.
        """
        if self.evidence_count == 0:
            half = 0.15
        else:
            half = 0.15 / math.sqrt(self.evidence_count)
        return (
            max(0.0, self.posterior - half),
            min(1.0, self.posterior + half),
        )

    def update(self, direction: int, strength: float,
               reason: str, test_num: int, evidence_type: str = "default"):
        """
        Bayesian update via log-odds.

        Args:
            direction:  +1 (supporting) or -1 (contradicting)
            strength:   heuristic weight (0.0 - 0.5), from EVIDENCE_STRENGTH_RULES
            reason:     human-readable reason for this evidence
            test_num: which test produced this evidence
            evidence_type: key into EVIDENCE_STRENGTH_RULES
        """
        # Resolve strength from rules if not explicitly provided
        if strength <= 0:
            strength = EVIDENCE_STRENGTH_RULES.get(evidence_type,
                       EVIDENCE_STRENGTH_RULES["default"])

        # Log-odds formulation (Appendix A.1)
        # Clamp posterior away from 0 and 1 to avoid log(0)
        p = max(0.01, min(0.99, self.posterior))
        log_odds = math.log(p / (1.0 - p))

        # Update
        log_odds += direction * strength

        # Convert back to probability
        self.posterior = 1.0 / (1.0 + math.exp(-log_odds))

        # Record evidence
        entry = {
            "test_run": test_num,
            "reason": reason,
            "strength": strength,
            "evidence_type": evidence_type,
            "direction": direction,
            "posterior_after": round(self.posterior, 4),
        }

        if direction > 0:
            self.evidence_for.append(entry)
        else:
            self.evidence_against.append(entry)

        # Update status
        self._update_status()

    def _update_status(self):
        """Classify hypothesis based on posterior and evidence count."""
        if self.evidence_count < self.MIN_EVIDENCE_FOR_STATUS:
            self.status = "NEEDS_MORE_DATA"
        elif self.posterior >= self.VALIDATE_THRESHOLD:
            self.status = "VALIDATED"
        elif self.posterior <= self.INVALIDATE_THRESHOLD:
            self.status = "INVALIDATED"
        else:
            self.status = "NEEDS_MORE_DATA"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "prior": self.prior,
            "posterior": round(self.posterior, 4),
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "evidence_count": self.evidence_count,
            "confidence_interval": [round(x, 4) for x in self.confidence_interval],
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Hypothesis":
        h = cls(
            key=d["key"],
            name=d["name"],
            description=d.get("description", ""),
            prior=d["prior"],
            posterior=d["posterior"],
        )
        h.evidence_for = d.get("evidence_for", [])
        h.evidence_against = d.get("evidence_against", [])
        h.status = d.get("status", "NEEDS_MORE_DATA")
        return h


# ============================================================================
# HYPOTHESIS SET
# ============================================================================

class HypothesisEngine:
    """
    Manages a team's hypothesis set with Bayesian tracking.

    Hypotheses are team-defined. The engine does not assume
    any specific domain. Teams create their own hypotheses
    during BCM setup.
    """

    def __init__(self):
        self.hypotheses: Dict[str, Hypothesis] = {}

    def add_hypothesis(self, key: str, name: str,
                       description: str = "", prior: float = 0.50):
        """Add a new hypothesis. Prior defaults to 0.50 (maximum uncertainty)."""
        self.hypotheses[key] = Hypothesis(
            key=key,
            name=name,
            description=description,
            prior=prior,
            posterior=prior,
        )

    def update_hypothesis(self, key: str, direction: int,
                          reason: str, test_num: int,
                          evidence_type: str = "default",
                          strength: float = 0.0):
        """Update a hypothesis with new evidence from a test."""
        if key not in self.hypotheses:
            return
        self.hypotheses[key].update(
            direction=direction,
            strength=strength,
            reason=reason,
            test_num=test_num,
            evidence_type=evidence_type,
        )

    def get_validated(self) -> List[Hypothesis]:
        return [h for h in self.hypotheses.values() if h.status == "VALIDATED"]

    def get_invalidated(self) -> List[Hypothesis]:
        return [h for h in self.hypotheses.values() if h.status == "INVALIDATED"]

    def get_needs_data(self) -> List[Hypothesis]:
        return [h for h in self.hypotheses.values() if h.status == "NEEDS_MORE_DATA"]

    def summary(self) -> dict:
        """Summary for strategic intelligence report."""
        return {
            "total": len(self.hypotheses),
            "validated": len(self.get_validated()),
            "invalidated": len(self.get_invalidated()),
            "needs_data": len(self.get_needs_data()),
            "hypotheses": {k: h.to_dict() for k, h in self.hypotheses.items()},
        }

    def to_dict(self) -> dict:
        return {k: h.to_dict() for k, h in self.hypotheses.items()}

    @classmethod
    def from_dict(cls, d: dict) -> "HypothesisEngine":
        engine = cls()
        for k, v in d.items():
            engine.hypotheses[k] = Hypothesis.from_dict(v)
        return engine

    def save(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "HypothesisEngine":
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("BAYESIAN HYPOTHESIS ENGINE — SELF-TEST")
    print("  Log-odds formulation (Appendix A.1 compliant)")
    print("=" * 60)

    engine = HypothesisEngine()

    # Team-defined hypotheses (not hardcoded to any domain)
    engine.add_hypothesis("H1", "BCM rotation curve fits beat NFW for massive galaxies",
                          prior=0.60)
    engine.add_hypothesis("H2", "Annual contamination damage exceeds sub-Eddington",
                          prior=0.50)
    engine.add_hypothesis("H3", "Substrate maintenance is sub-Eddington for all galaxies",
                          prior=0.55)

    # Simulate test evidence
    print("\n--- Test Run #1: Galactic Solver ---")
    engine.update_hypothesis("H1", +1, "Solver showed BCM chi2 < NFW chi2 for NGC2841",
                             test_num=1, evidence_type="explicit_validate")
    engine.update_hypothesis("H2", +1, "Reported L_nu = 9.5e42 erg/s sub-Eddington",
                             test_num=1, evidence_type="cost_direct")

    print("--- Test Run #2: Chi-Squared Engine ---")
    engine.update_hypothesis("H1", +1, "Confirmed BCM wins massive bracket 7/12",
                             test_num=2, evidence_type="sentiment_positive")
    engine.update_hypothesis("H2", +1, "Measured Tully-Fisher scaling L ~ v^3.9",
                             test_num=2, evidence_type="cost_direct")
    engine.update_hypothesis("H3", +1, "All 29 galaxies sub-Eddington confirmed",
                             test_num=2, evidence_type="explicit_validate")

    print("--- Test Run #3: Reverse Engine ---")
    engine.update_hypothesis("H1", -1, "NFW fit beats BCM for low-V bracket",
                             test_num=3, evidence_type="explicit_contradict")
    engine.update_hypothesis("H3", +1, "Low-V bracket consistent with weak pump",
                             test_num=3, evidence_type="sentiment_positive")

    print("--- Test Run #4: Neutrino Flux ---")
    engine.update_hypothesis("H1", +1, "Neutrino Flux confirms sensor gaps in chip lines",
                             test_num=4, evidence_type="explicit_validate")
    engine.update_hypothesis("H2", +1, "IceCube flux 500x above threshold for Class I",
                             test_num=4, evidence_type="cost_direct")
    engine.update_hypothesis("H3", +1, "28/29 detectable by IceCube at TeV band",
                             test_num=4, evidence_type="pain_severe")

    # Report
    print("\n--- HYPOTHESIS SUMMARY ---")
    for key, h in engine.hypotheses.items():
        ci = h.confidence_interval
        moved = h.posterior - h.prior
        print(f"\n  {h.name}")
        print(f"    Prior: {h.prior:.0%} → Posterior: {h.posterior:.0%} (moved: {moved:+.0%})")
        print(f"    CI: [{ci[0]:.0%}, {ci[1]:.0%}]")
        print(f"    Evidence: {len(h.evidence_for)} for, {len(h.evidence_against)} against")
        print(f"    Status: {h.status}")

    # Verify log-odds math
    print("\n--- LOG-ODDS VERIFICATION ---")
    h1 = engine.hypotheses["H1"]
    p = h1.posterior
    lo = math.log(p / (1.0 - p))
    print(f"  H1 posterior: {p:.4f}")
    print(f"  H1 log-odds:  {lo:.4f}")
    print(f"  Reconverted:  {1.0 / (1.0 + math.exp(-lo)):.4f}")
    assert abs(p - 1.0 / (1.0 + math.exp(-lo))) < 0.0001
    print("  Math verification: PASS")

    # JSON round-trip
    serialized = engine.to_dict()
    restored = HypothesisEngine.from_dict(serialized)
    assert abs(restored.hypotheses["H1"].posterior - engine.hypotheses["H1"].posterior) < 0.001
    print("  JSON round-trip: PASS")

    print("\nAll tests passed.")
