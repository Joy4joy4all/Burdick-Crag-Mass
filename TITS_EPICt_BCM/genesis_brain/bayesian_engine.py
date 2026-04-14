# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GIBUSH CORE - BAYESIAN HYPOTHESIS ENGINE
=========================================
MIT Engineering-Grade Bayesian Inference for Hypothesis Validation.

Mathematical Framework:
- Bayesian updating with conjugate priors
- Evidence strength quantification
- Multi-hypothesis tracking
- Convergence detection

Equations exposed for academic review and modification.

Emerald Entities LLC — GIBUSH Systems
USPTO Serial #99346684 | Class 009
"""

import json
import math
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict


# ============================================================================
# MATHEMATICAL CONSTANTS
# ============================================================================

# Prior probability for new hypotheses (uninformed prior)
DEFAULT_PRIOR = 0.5

# Evidence strength thresholds
EVIDENCE_STRONG = 0.8
EVIDENCE_MODERATE = 0.5
EVIDENCE_WEAK = 0.2

# Validation thresholds
VALIDATION_THRESHOLD = 0.85      # Hypothesis validated
INVALIDATION_THRESHOLD = 0.15   # Hypothesis invalidated
PIVOT_THRESHOLD = 0.35          # Consider pivoting

# Minimum tests for statistical significance
MIN_TESTS_FOR_SIGNIFICANCE = 5

# Valid Q-Cube coordinate values — reject anything outside these sets
VALID_Q_LAYERS  = {"L1", "L2", "L3"}
VALID_Q_OBJECTS = {"OA", "OB", "OC"}
VALID_Q_STACKS  = {"Sa", "Sb", "Sg", "Sd"}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class EvidenceType(Enum):
    """Classification of evidence strength"""
    STRONG_SUPPORT = "strong_support"       # Direct confirmation with data
    MODERATE_SUPPORT = "moderate_support"   # Indirect confirmation
    WEAK_SUPPORT = "weak_support"           # Anecdotal support
    NEUTRAL = "neutral"                     # No impact
    WEAK_CONTRADICT = "weak_contradict"     # Minor contradiction
    MODERATE_CONTRADICT = "moderate_contradict"  # Significant contradiction
    STRONG_CONTRADICT = "strong_contradict"     # Direct refutation with data


@dataclass
class Evidence:
    """Single piece of evidence for/against hypothesis"""
    evidence_id: str
    hypothesis_id: str
    test_id: str
    evidence_type: EvidenceType
    description: str
    source_role: str        # L1, L2, L3
    source_credibility: float  # 0-1
    timestamp: str
    raw_text: str = ""
    quantitative_data: Dict = field(default_factory=dict)
    # Q-Cube coordinates — where in the state space this evidence lives
    q_layer: str = "L2"    # L1 (Operator), L2 (Manager), L3 (Executive)
    q_object: str = "OC"   # OA (Upstream), OB (Transfer), OC (Downstream)
    q_stack: str = "Sa"    # Sa (Cross-Mill), Sb (Post-Investment), Sg (Baseline), Sd (Dual Impact)

    @property
    def cube_coord(self) -> str:
        """Returns coordinate key used to index cube_posteriors. Format: 'L1|OB|Sa'"""
        return f"{self.q_layer}|{self.q_object}|{self.q_stack}"
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['evidence_type'] = self.evidence_type.value
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Evidence':
        d['evidence_type'] = EvidenceType(d['evidence_type'])
        return cls(**d)


@dataclass 
class Hypothesis:
    """Tracked hypothesis with Bayesian state"""
    hypothesis_id: str
    project_id: str
    statement: str
    category: str
    created_at: str
    
    # Bayesian state
    prior: float = DEFAULT_PRIOR
    posterior: float = DEFAULT_PRIOR
    evidence_count: int = 0
    support_count: int = 0
    contradict_count: int = 0
    
    # Tracking
    update_history: List[Dict] = field(default_factory=list)
    status: str = "active"  # active, validated, invalidated, pivoted
    
    # Confidence intervals (Beta distribution parameters) — global fallback
    alpha: float = 1.0  # Prior successes
    beta: float = 1.0   # Prior failures

    # Q-Cube coordinate-indexed belief state
    # Key format: "L1|OB|Sa"  Value: posterior float
    cube_posteriors: Dict = field(default_factory=dict)
    # Per-coordinate Beta parameters for proper conjugate updating
    # Key format: "L1|OB|Sa"  Value: [alpha, beta]
    cube_beta_params: Dict = field(default_factory=dict)

    def get_cube_posterior(self, coord: str) -> float:
        """Return posterior for a cube coordinate. Defaults to global prior if unseen."""
        return self.cube_posteriors.get(coord, self.prior)

    def get_cube_beta(self, coord: str) -> Tuple[float, float]:
        """Return (alpha, beta) for a cube coordinate. Defaults to [1.0, 1.0] if unseen."""
        params = self.cube_beta_params.get(coord, [1.0, 1.0])
        return params[0], params[1]

    def dominant_coord(self) -> Optional[str]:
        """Return the cube coordinate with the highest posterior. The 'Way'."""
        if not self.cube_posteriors:
            return None
        return max(self.cube_posteriors, key=lambda k: self.cube_posteriors[k])

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> 'Hypothesis':
        return cls(**d)
    
    @property
    def confidence_interval_95(self) -> Tuple[float, float]:
        """Calculate 95% credible interval using Beta distribution"""
        from scipy import stats
        if self.alpha > 0 and self.beta > 0:
            return stats.beta.ppf([0.025, 0.975], self.alpha, self.beta)
        return (0.0, 1.0)
    
    @property
    def variance(self) -> float:
        """Variance of Beta distribution"""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))
    
    @property
    def is_significant(self) -> bool:
        """Check if we have enough evidence for statistical significance"""
        return self.evidence_count >= MIN_TESTS_FOR_SIGNIFICANCE


# ============================================================================
# BAYESIAN ENGINE
# ============================================================================

class BayesianHypothesisEngine:
    """
    MIT-Grade Bayesian Hypothesis Tracking Engine.
    
    Core Equations:
    ===============
    
    1. BAYES' THEOREM:
       P(H|E) = P(E|H) Ã— P(H) / P(E)
       
       Where:
       - P(H|E) = Posterior probability (what we want)
       - P(E|H) = Likelihood of evidence given hypothesis
       - P(H) = Prior probability
       - P(E) = Marginal likelihood
    
    2. BETA-BINOMIAL MODEL:
       Prior: Beta(Î±, Î²)
       Likelihood: Binomial(n, p)
       Posterior: Beta(Î± + successes, Î² + failures)
       
       We use this for conjugate updating.
    
    3. EVIDENCE STRENGTH MAPPING:
       strong_support â†’ success weight = 1.0
       moderate_support â†’ success weight = 0.7
       weak_support â†’ success weight = 0.3
       neutral â†’ no update
       weak_contradict â†’ failure weight = 0.3
       moderate_contradict â†’ failure weight = 0.7
       strong_contradict â†’ failure weight = 1.0
    
    4. SOURCE CREDIBILITY WEIGHTING:
       L1 (Operator) â†’ weight = 1.0 (closest to truth)
       L2 (Manager) â†’ weight = 0.8
       L3 (Executive) â†’ weight = 0.6
       External â†’ weight = 0.5
    
    5. INFORMATION GAIN (Shannon):
       IG = H(prior) - H(posterior)
       H(p) = -pÃ—log(p) - (1-p)Ã—log(1-p)
    """
    
    # Evidence type to weight mapping
    EVIDENCE_WEIGHTS = {
        EvidenceType.STRONG_SUPPORT: (1.0, 0.0),      # (success_weight, failure_weight)
        EvidenceType.MODERATE_SUPPORT: (0.7, 0.0),
        EvidenceType.WEAK_SUPPORT: (0.3, 0.0),
        EvidenceType.NEUTRAL: (0.0, 0.0),
        EvidenceType.WEAK_CONTRADICT: (0.0, 0.3),
        EvidenceType.MODERATE_CONTRADICT: (0.0, 0.7),
        EvidenceType.STRONG_CONTRADICT: (0.0, 1.0),
    }
    
    # Source role credibility
    SOURCE_CREDIBILITY = {
        'L1': 1.0,    # Operators - hands on equipment
        'L2': 0.8,    # Managers - see P&L
        'L3': 0.6,    # Executives - filtered info
        'external': 0.5,
        'unknown': 0.5
    }
    
    def __init__(self, project_id: str, data_dir: Path = None):
        self.project_id = project_id
        self.data_dir = data_dir or Path.home() / ".gibush" / "projects" / project_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.hypotheses_file = self.data_dir / "hypotheses.json"
        self.evidence_file = self.data_dir / "evidence.json"
        self.equations_file = self.data_dir / "equation_log.json"
        
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.evidence: Dict[str, Evidence] = {}
        self.equation_log: List[Dict] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load hypotheses and evidence from files"""
        if self.hypotheses_file.exists():
            with open(self.hypotheses_file) as f:
                data = json.load(f)
                self.hypotheses = {hid: Hypothesis.from_dict(h) for hid, h in data.items()}
        
        if self.evidence_file.exists():
            with open(self.evidence_file) as f:
                data = json.load(f)
                self.evidence = {eid: Evidence.from_dict(e) for eid, e in data.items()}
    
    def _save_data(self):
        """Save all data to files"""
        with open(self.hypotheses_file, 'w') as f:
            json.dump({hid: h.to_dict() for hid, h in self.hypotheses.items()}, f, indent=2)
        
        with open(self.evidence_file, 'w') as f:
            json.dump({eid: e.to_dict() for eid, e in self.evidence.items()}, f, indent=2)
    
    def _save_equation_log(self):
        """Save equation log for academic review"""
        with open(self.equations_file, 'w') as f:
            json.dump(self.equation_log, f, indent=2)
    
    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID"""
        import secrets
        return f"{prefix}{secrets.token_hex(6)}"
    
    # ========================================================================
    # CORE EQUATIONS (Exposed for MIT review)
    # ========================================================================
    
    @staticmethod
    def entropy(p: float) -> float:
        """
        Shannon Entropy: H(p) = -pÃ—logâ‚‚(p) - (1-p)Ã—logâ‚‚(1-p)
        
        Measures uncertainty in a binary distribution.
        H=0 when p=0 or p=1 (certain)
        H=1 when p=0.5 (maximum uncertainty)
        """
        if p <= 0 or p >= 1:
            return 0.0
        return -p * math.log2(p) - (1 - p) * math.log2(1 - p)
    
    @staticmethod
    def information_gain(prior: float, posterior: float) -> float:
        """
        Information Gain: IG = H(prior) - H(posterior)
        
        Positive IG = we learned something (reduced uncertainty)
        Negative IG = we became more uncertain (rare, indicates conflict)
        """
        return BayesianHypothesisEngine.entropy(prior) - BayesianHypothesisEngine.entropy(posterior)
    
    @staticmethod
    def beta_mean(alpha: float, beta: float) -> float:
        """
        Beta Distribution Mean: Î¼ = Î± / (Î± + Î²)
        
        This is our point estimate of the probability.
        """
        return alpha / (alpha + beta)
    
    @staticmethod
    def beta_variance(alpha: float, beta: float) -> float:
        """
        Beta Distribution Variance: ÏƒÂ² = Î±Î² / ((Î±+Î²)Â²(Î±+Î²+1))
        
        Decreases as we gather more evidence (Î± + Î² increases).
        """
        total = alpha + beta
        return (alpha * beta) / (total ** 2 * (total + 1))
    
    @staticmethod
    def beta_mode(alpha: float, beta: float) -> float:
        """
        Beta Distribution Mode: mode = (Î±-1) / (Î±+Î²-2) for Î±,Î² > 1
        
        Most likely value of the probability.
        """
        if alpha > 1 and beta > 1:
            return (alpha - 1) / (alpha + beta - 2)
        elif alpha <= 1 and beta > 1:
            return 0.0
        elif alpha > 1 and beta <= 1:
            return 1.0
        else:
            return 0.5  # Uniform
    
    @staticmethod
    def credible_interval(alpha: float, beta: float, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Bayesian Credible Interval using Beta distribution quantiles.
        
        Unlike frequentist CI, this directly gives probability bounds.
        """
        try:
            from scipy import stats
            tail = (1 - confidence) / 2
            lower = stats.beta.ppf(tail, alpha, beta)
            upper = stats.beta.ppf(1 - tail, alpha, beta)
            return (lower, upper)
        except ImportError:
            # Fallback: normal approximation
            mean = alpha / (alpha + beta)
            std = math.sqrt(BayesianHypothesisEngine.beta_variance(alpha, beta))
            z = 1.96  # 95% CI
            return (max(0, mean - z * std), min(1, mean + z * std))
    
    @staticmethod
    def bayes_factor(posterior: float, prior: float) -> float:
        """
        Bayes Factor: BF = P(H|E)/P(Â¬H|E) Ã· P(H)/P(Â¬H)
        
        Simplified: BF = (posterior/(1-posterior)) / (prior/(1-prior))
        
        BF > 10: Strong evidence for H
        BF > 3: Moderate evidence for H
        BF > 1: Weak evidence for H
        BF < 1: Evidence against H
        """
        if posterior >= 1 or prior >= 1 or posterior <= 0 or prior <= 0:
            return float('inf') if posterior > prior else 0.0
        
        posterior_odds = posterior / (1 - posterior)
        prior_odds = prior / (1 - prior)
        
        return posterior_odds / prior_odds if prior_odds > 0 else float('inf')
    
    # ========================================================================
    # HYPOTHESIS MANAGEMENT
    # ========================================================================
    
    def create_hypothesis(
        self,
        statement: str,
        category: str = "general",
        prior: float = DEFAULT_PRIOR
    ) -> Hypothesis:
        """
        Create new hypothesis with uninformed or specified prior.
        
        Args:
            statement: The hypothesis statement to test
            category: Grouping category
            prior: Initial probability estimate (default 0.5 = maximum uncertainty)
        """
        hypothesis_id = self._generate_id("HYP_")
        
        hypothesis = Hypothesis(
            hypothesis_id=hypothesis_id,
            project_id=self.project_id,
            statement=statement,
            category=category,
            created_at=datetime.now().isoformat(),
            prior=prior,
            posterior=prior,
            alpha=1.0,  # Uninformed Beta prior
            beta=1.0
        )
        
        self.hypotheses[hypothesis_id] = hypothesis
        self._save_data()
        
        # Log equation
        self.equation_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "CREATE_HYPOTHESIS",
            "hypothesis_id": hypothesis_id,
            "equation": f"Prior: Beta(Î±=1, Î²=1) â†’ P(H) = {prior:.4f}",
            "entropy": f"H(prior) = {self.entropy(prior):.4f} bits"
        })
        self._save_equation_log()
        
        return hypothesis
    
    def add_evidence(
        self,
        hypothesis_id: str,
        test_id: str,
        evidence_type: EvidenceType,
        description: str,
        source_role: str = "unknown",
        raw_text: str = "",
        quantitative_data: Dict = None,
        q_layer: str = "L2",
        q_object: str = "OC",
        q_stack: str = "Sa"
    ) -> Tuple[Evidence, Dict]:
        """
        Add evidence and perform Bayesian update.
        
        Returns: (evidence, update_info)
        
        Update Info contains:
        - prior: Previous probability
        - posterior: New probability
        - alpha_delta: Change in alpha
        - beta_delta: Change in beta
        - information_gain: Bits of information gained
        - bayes_factor: Strength of update
        """
        hypothesis = self.hypotheses.get(hypothesis_id)
        if not hypothesis:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")
        
        evidence_id = self._generate_id("EVD_")
        source_credibility = self.SOURCE_CREDIBILITY.get(source_role, 0.5)

        # Validate cube coordinates before anything is written
        if q_layer not in VALID_Q_LAYERS:
            raise ValueError(f"Invalid q_layer '{q_layer}'. Must be one of {VALID_Q_LAYERS}")
        if q_object not in VALID_Q_OBJECTS:
            raise ValueError(f"Invalid q_object '{q_object}'. Must be one of {VALID_Q_OBJECTS}")
        if q_stack not in VALID_Q_STACKS:
            raise ValueError(f"Invalid q_stack '{q_stack}'. Must be one of {VALID_Q_STACKS}")
        
        evidence = Evidence(
            evidence_id=evidence_id,
            hypothesis_id=hypothesis_id,
            test_id=test_id,
            evidence_type=evidence_type,
            description=description,
            source_role=source_role,
            source_credibility=source_credibility,
            timestamp=datetime.now().isoformat(),
            raw_text=raw_text,
            quantitative_data=quantitative_data or {},
            q_layer=q_layer,
            q_object=q_object,
            q_stack=q_stack
        )
        
        self.evidence[evidence_id] = evidence
        
        # Perform Bayesian update
        update_info = self._bayesian_update(hypothesis, evidence)
        
        self._save_data()
        
        return evidence, update_info
    
    def _bayesian_update(self, hypothesis: Hypothesis, evidence: Evidence) -> Dict:
        """
        Perform Bayesian update using Beta-Binomial conjugate model.
        
        EQUATIONS:
        ==========
        
        1. Get evidence weights based on type:
           (success_weight, failure_weight) = EVIDENCE_WEIGHTS[evidence_type]
        
        2. Apply source credibility:
           effective_success = success_weight Ã— source_credibility
           effective_failure = failure_weight Ã— source_credibility
        
        3. Update Beta parameters:
           Î±_new = Î±_old + effective_success
           Î²_new = Î²_old + effective_failure
        
        4. Calculate new posterior:
           P(H|E) = Î±_new / (Î±_new + Î²_new)
        
        5. Calculate information gain:
           IG = H(prior) - H(posterior)
        """
        # --- Global fallback (aggregate across all coordinates) ---
        prior = hypothesis.posterior
        old_alpha = hypothesis.alpha
        old_beta = hypothesis.beta

        # --- Cube coordinate for this evidence ---
        coord = evidence.cube_coord
        coord_old_alpha, coord_old_beta = hypothesis.get_cube_beta(coord)

        # Get evidence weights
        success_weight, failure_weight = self.EVIDENCE_WEIGHTS[evidence.evidence_type]

        # Apply source credibility
        effective_success = success_weight * evidence.source_credibility
        effective_failure = failure_weight * evidence.source_credibility

        # --- Global Beta update (backward compatible) ---
        new_alpha = old_alpha + effective_success
        new_beta = old_beta + effective_failure
        posterior = self.beta_mean(new_alpha, new_beta)

        # --- Coordinate-specific Beta update ---
        coord_new_alpha = coord_old_alpha + effective_success
        coord_new_beta = coord_old_beta + effective_failure
        coord_posterior = self.beta_mean(coord_new_alpha, coord_new_beta)

        # Write coordinate result back into hypothesis
        hypothesis.cube_posteriors[coord] = coord_posterior
        hypothesis.cube_beta_params[coord] = [coord_new_alpha, coord_new_beta]

        # Calculate metrics (against global for log consistency)
        ig = self.information_gain(prior, posterior)
        bf = self.bayes_factor(posterior, prior)
        variance = self.beta_variance(new_alpha, new_beta)
        ci_low, ci_high = self.credible_interval(new_alpha, new_beta)

        # Update global hypothesis state
        hypothesis.alpha = new_alpha
        hypothesis.beta = new_beta
        hypothesis.posterior = posterior
        hypothesis.evidence_count += 1
        
        if effective_success > 0:
            hypothesis.support_count += 1
        if effective_failure > 0:
            hypothesis.contradict_count += 1
        
        # Check status
        if posterior >= VALIDATION_THRESHOLD and hypothesis.is_significant:
            hypothesis.status = "validated"
        elif posterior <= INVALIDATION_THRESHOLD and hypothesis.is_significant:
            hypothesis.status = "invalidated"
        elif posterior <= PIVOT_THRESHOLD:
            hypothesis.status = "consider_pivot"
        
        # Record update
        update_record = {
            "timestamp": datetime.now().isoformat(),
            "evidence_id": evidence.evidence_id,
            "prior": prior,
            "posterior": posterior,
            "alpha": new_alpha,
            "beta": new_beta,
            "information_gain": ig,
            "bayes_factor": bf
        }
        hypothesis.update_history.append(update_record)
        
        # Create detailed update info
        update_info = {
            "prior": prior,
            "posterior": posterior,
            "alpha_old": old_alpha,
            "alpha_new": new_alpha,
            "alpha_delta": effective_success,
            "beta_old": old_beta,
            "beta_new": new_beta,
            "beta_delta": effective_failure,
            "information_gain": ig,
            "bayes_factor": bf,
            "variance": variance,
            "credible_interval_95": (ci_low, ci_high),
            "status": hypothesis.status,
            "equation_applied": f"Beta({old_alpha:.2f}, {old_beta:.2f}) + Evidence -> Beta({new_alpha:.2f}, {new_beta:.2f})",
            # Cube coordinate result
            "cube_coord": coord,
            "cube_posterior": coord_posterior,
            "cube_alpha": coord_new_alpha,
            "cube_beta": coord_new_beta,
            "dominant_coord": hypothesis.dominant_coord()
        }
        
        # Log equation details
        self.equation_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "BAYESIAN_UPDATE",
            "hypothesis_id": hypothesis.hypothesis_id,
            "evidence_id": evidence.evidence_id,
            "equations": {
                "prior": f"P(H) = {prior:.4f}",
                "likelihood_support": f"P(E|H) weight = {success_weight:.2f}",
                "likelihood_contra": f"P(E|Â¬H) weight = {failure_weight:.2f}",
                "credibility": f"Source credibility = {evidence.source_credibility:.2f}",
                "alpha_update": f"Î±: {old_alpha:.2f} + {effective_success:.2f} = {new_alpha:.2f}",
                "beta_update": f"Î²: {old_beta:.2f} + {effective_failure:.2f} = {new_beta:.2f}",
                "posterior": f"P(H|E) = Î±/(Î±+Î²) = {new_alpha:.2f}/{new_alpha + new_beta:.2f} = {posterior:.4f}",
                "information_gain": f"IG = H({prior:.4f}) - H({posterior:.4f}) = {ig:.4f} bits",
                "bayes_factor": f"BF = {bf:.2f}"
            }
        })
        self._save_equation_log()
        
        return update_info
    
    # ========================================================================
    # ANALYSIS METHODS
    # ========================================================================
    
    def get_hypothesis_status(self, hypothesis_id: str) -> Dict:
        """Get full status report for hypothesis"""
        h = self.hypotheses.get(hypothesis_id)
        if not h:
            return {}
        
        ci_low, ci_high = self.credible_interval(h.alpha, h.beta)
        
        return {
            "hypothesis_id": h.hypothesis_id,
            "statement": h.statement,
            "status": h.status,
            "posterior": h.posterior,
            "prior": h.prior,
            "evidence_count": h.evidence_count,
            "support_count": h.support_count,
            "contradict_count": h.contradict_count,
            "alpha": h.alpha,
            "beta": h.beta,
            "credible_interval_95": (ci_low, ci_high),
            "variance": self.beta_variance(h.alpha, h.beta),
            "is_significant": h.is_significant,
            "total_information_gain": sum(u.get("information_gain", 0) for u in h.update_history)
        }
    
    def get_all_hypotheses_summary(self) -> List[Dict]:
        """Get summary of all hypotheses"""
        return [self.get_hypothesis_status(hid) for hid in self.hypotheses]
    
    def get_recommended_actions(self) -> List[Dict]:
        """Get recommended next actions based on hypothesis states"""
        actions = []
        
        for h in self.hypotheses.values():
            if h.status == "active":
                variance = self.beta_variance(h.alpha, h.beta)
                
                if variance > 0.05:  # High uncertainty
                    actions.append({
                        "hypothesis_id": h.hypothesis_id,
                        "action": "GATHER_EVIDENCE",
                        "reason": f"High uncertainty (variance={variance:.3f})",
                        "priority": "high"
                    })
                elif h.evidence_count < MIN_TESTS_FOR_SIGNIFICANCE:
                    actions.append({
                        "hypothesis_id": h.hypothesis_id,
                        "action": "GATHER_EVIDENCE",
                        "reason": f"Insufficient data ({h.evidence_count}/{MIN_TESTS_FOR_SIGNIFICANCE} test_runs)",
                        "priority": "medium"
                    })
            
            elif h.status == "consider_pivot":
                actions.append({
                    "hypothesis_id": h.hypothesis_id,
                    "action": "CONSIDER_PIVOT",
                    "reason": f"Low probability ({h.posterior:.2%}) suggests hypothesis may be wrong",
                    "priority": "high"
                })
        
        return sorted(actions, key=lambda x: 0 if x["priority"] == "high" else 1)
    
    def export_equations_latex(self) -> str:
        """Export equations in LaTeX format for academic papers"""
        latex = r"""
\section{Bayesian Hypothesis Validation Framework}

\subsection{Core Equations}

\textbf{Bayes' Theorem:}
\begin{equation}
P(H|E) = \frac{P(E|H) \cdot P(H)}{P(E)}
\end{equation}

\textbf{Beta-Binomial Conjugate Model:}
\begin{align}
\text{Prior:} & \quad H \sim \text{Beta}(\alpha, \beta) \\
\text{Likelihood:} & \quad E|H \sim \text{Binomial}(n, p) \\
\text{Posterior:} & \quad H|E \sim \text{Beta}(\alpha + s, \beta + f)
\end{align}

where $s$ = weighted successes, $f$ = weighted failures.

\textbf{Posterior Mean (Point Estimate):}
\begin{equation}
\hat{P}(H|E) = \frac{\alpha}{\alpha + \beta}
\end{equation}

\textbf{Posterior Variance:}
\begin{equation}
\text{Var}(H|E) = \frac{\alpha \beta}{(\alpha + \beta)^2 (\alpha + \beta + 1)}
\end{equation}

\textbf{Information Gain (Shannon):}
\begin{equation}
IG = H(P_{\text{prior}}) - H(P_{\text{posterior}})
\end{equation}

where $H(p) = -p \log_2(p) - (1-p) \log_2(1-p)$

\textbf{Bayes Factor:}
\begin{equation}
BF = \frac{P(H|E) / P(\neg H|E)}{P(H) / P(\neg H)}
\end{equation}

\subsection{Evidence Weighting}

Source credibility weights:
\begin{itemize}
\item L1 (Operators): $w = 1.0$
\item L2 (Managers): $w = 0.8$
\item L3 (Executives): $w = 0.6$
\end{itemize}

\subsection{Validation Thresholds}

\begin{itemize}
\item Validated: $P(H|E) \geq 0.85$ with $n \geq 5$
\item Invalidated: $P(H|E) \leq 0.15$ with $n \geq 5$
\item Pivot recommended: $P(H|E) \leq 0.35$
\end{itemize}
"""
        return latex


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

_engines: Dict[str, BayesianHypothesisEngine] = {}

def get_bayesian_engine(project_id: str) -> BayesianHypothesisEngine:
    """Get or create Bayesian engine for project"""
    if project_id not in _engines:
        _engines[project_id] = BayesianHypothesisEngine(project_id)
    return _engines[project_id]


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("BAYESIAN HYPOTHESIS ENGINE TEST")
    print("=" * 70)
    
    engine = BayesianHypothesisEngine("TEST_PROJECT", Path("./test_bayesian"))
    
    # Create hypothesis
    h1 = engine.create_hypothesis(
        "Rock contamination causes >$300K annual equipment damage per mill",
        category="cost_validation"
    )
    print(f"\nCreated hypothesis: {h1.statement[:50]}...")
    print(f"  Prior: {h1.prior:.4f}")
    print(f"  Entropy: {engine.entropy(h1.prior):.4f} bits")
    
    # Add supporting evidence
    evidence1, update1 = engine.add_evidence(
        h1.hypothesis_id,
        "INT_001",
        EvidenceType.STRONG_SUPPORT,
        "Operator confirmed $450K spent on blow line repairs last year due to rock damage",
        source_role="L1",
        quantitative_data={"annual_cost": 450000, "currency": "USD"}
    )
    
    print(f"\nAfter strong L1 evidence:")
    print(f"  Prior â†’ Posterior: {update1['prior']:.4f} â†’ {update1['posterior']:.4f}")
    print(f"  Alpha: {update1['alpha_old']:.2f} â†’ {update1['alpha_new']:.2f}")
    print(f"  Information Gain: {update1['information_gain']:.4f} bits")
    print(f"  Bayes Factor: {update1['bayes_factor']:.2f}")
    
    # Add more evidence
    evidence2, update2 = engine.add_evidence(
        h1.hypothesis_id,
        "INT_002",
        EvidenceType.MODERATE_SUPPORT,
        "Manager reported equipment protection is in capital budget",
        source_role="L2"
    )
    
    print(f"\nAfter moderate L2 evidence:")
    print(f"  Posterior: {update2['posterior']:.4f}")
    print(f"  95% CI: [{update2['credible_interval_95'][0]:.4f}, {update2['credible_interval_95'][1]:.4f}]")
    
    # Add contradicting evidence
    evidence3, update3 = engine.add_evidence(
        h1.hypothesis_id,
        "INT_003",
        EvidenceType.MODERATE_CONTRADICT,
        "Executive says damage costs are overstated by operations",
        source_role="L3"
    )
    
    print(f"\nAfter contradicting L3 evidence:")
    print(f"  Posterior: {update3['posterior']:.4f}")
    print(f"  Status: {update3['status']}")
    
    # Full status
    print("\n" + "=" * 70)
    print("HYPOTHESIS STATUS REPORT")
    print("=" * 70)
    status = engine.get_hypothesis_status(h1.hypothesis_id)
    for k, v in status.items():
        print(f"  {k}: {v}")
    
    # Export LaTeX
    print("\n" + "=" * 70)
    print("LATEX EXPORT (first 500 chars)")
    print("=" * 70)
    print(engine.export_equations_latex()[:500])
