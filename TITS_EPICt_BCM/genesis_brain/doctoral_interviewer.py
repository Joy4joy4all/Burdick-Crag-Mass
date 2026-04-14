# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
DOCTORAL ANALYZER - MIT-Level Adaptive Questioning Engine
=============================================================
Genesis Brain Module for GIBUSH BCM

Implements doctoral-level test methodology:
- Bayesian hypothesis updating per test
- Information-theoretic question selection (max entropy reduction)
- Semantic similarity clustering across tests
- Gap analysis for Q-Cube coverage
- Automatic pivot detection when evidence contradicts hypotheses

Architecture: Integrates with existing genesis_brain modules
Author: GIBUSH AI Engineering Team
"""

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Hypothesis:
    """A testable hypothesis with Bayesian confidence tracking"""
    id: str
    statement: str
    prior_probability: float = 0.5  # Initial belief (0-1)
    posterior_probability: float = 0.5  # Updated belief after evidence
    supporting_tests: List[int] = field(default_factory=list)
    contradicting_tests: List[int] = field(default_factory=list)
    evidence_strength: float = 0.0  # Cumulative evidence weight
    status: str = "TESTING"  # TESTING, VALIDATED, INVALIDATED, PIVOTED
    pivot_to: Optional[str] = None  # New hypothesis if pivoted
    
    def update_belief(self, likelihood_ratio: float, test_num: int, supports: bool):
        """Bayesian update: P(H|E) = P(E|H) * P(H) / P(E)"""
        # Simplified Bayesian update using likelihood ratio
        prior_odds = self.posterior_probability / (1 - self.posterior_probability + 1e-10)
        posterior_odds = prior_odds * likelihood_ratio
        self.posterior_probability = posterior_odds / (1 + posterior_odds)
        
        if supports:
            self.supporting_tests.append(test_num)
            self.evidence_strength += math.log(likelihood_ratio + 1e-10)
        else:
            self.contradicting_tests.append(test_num)
            self.evidence_strength -= math.log(likelihood_ratio + 1e-10)
        
        # Auto-update status based on confidence
        if self.posterior_probability > 0.85 and len(self.supporting_tests) >= 3:
            self.status = "VALIDATED"
        elif self.posterior_probability < 0.15 and len(self.contradicting_tests) >= 2:
            self.status = "INVALIDATED"


@dataclass
class QuestionCandidate:
    """A potential test parameter with information value"""
    question: str
    target_hypothesis: str
    information_gain: float  # Expected entropy reduction
    q_cube_coverage: List[str]  # Which cube positions this targets
    equipment_focus: List[str]  # Equipment categories targeted
    cost_discovery_potential: float  # Likelihood of extracting $ figures
    priority_score: float = 0.0  # Composite ranking score
    priority: str = "MEDIUM"  # Human-readable priority label
    rationale: str = ""  # Why this question was generated


@dataclass
class TestIntelligence:
    """Pre-test intelligence package"""
    test_num: int
    target_person: str
    target_company: str
    
    # Bayesian state
    active_hypotheses: List[Hypothesis] = field(default_factory=list)
    
    # Gap analysis
    q_cube_gaps: List[str] = field(default_factory=list)  # Positions needing coverage
    equipment_gaps: List[str] = field(default_factory=list)  # Equipment without cost data
    
    # Recommended questions (ranked by information value)
    recommended_questions: List[QuestionCandidate] = field(default_factory=list)
    
    # Contradictions to probe
    contradictions: List[str] = field(default_factory=list)
    
    # Cross-test patterns
    synergy_opportunities: List[str] = field(default_factory=list)


# ============================================================================
# DOCTORAL ANALYZER ENGINE
# ============================================================================

class DoctoralAnalyzer:
    """
    MIT-level adaptive test engine.
    
    Generates intelligent test parameters based on:
    1. Current hypothesis confidence levels
    2. Q-Cube coverage gaps
    3. Equipment cost data gaps
    4. Cross-test pattern detection
    5. Contradiction resolution needs
    """
    
    # Core hypotheses for BCM_SUBSTRATE project
    BCM_SUBSTRATE_HYPOTHESES = [
        Hypothesis("H1", "Manual rock detection at chip mills has >90% failure rate"),
        Hypothesis("H2", "Mills pay premiums for 'clean' chips without verification capability"),
        Hypothesis("H3", "CTS roller damage costs exceed $100K/year at typical mills"),
        Hypothesis("H4", "Screen basket replacement cycles are driven by contamination events"),
        Hypothesis("H5", "Operators can sense problems before instruments detect them"),
        Hypothesis("H6", "Budget authority for contamination prevention is fragmented"),
        Hypothesis("H7", "OEMs (Andritz, Valmet) are better customers than mills"),
        Hypothesis("H8", "Bark blow lines have equal or greater contamination impact"),
        Hypothesis("H9", "Seasonal factors (mud season) significantly affect contamination"),
        Hypothesis("H10", "Insurance/investors would value contamination monitoring data"),
    ]
    
    # Core hypotheses for BCM_NAVIGATION project
    BCM_NAVIGATION_HYPOTHESES = [
        Hypothesis("S1", "H2S detection response time requirements are not met by current systems"),
        Hypothesis("S2", "RTLS personnel tracking adoption is blocked by privacy concerns"),
        Hypothesis("S3", "Incident near-miss reporting is underutilized due to blame culture"),
        Hypothesis("S4", "Emergency evacuation coordination lacks real-time visibility"),
        Hypothesis("S5", "Confined space monitoring has critical gaps in continuous sensing"),
        Hypothesis("S6", "Chemical exposure limits are exceeded without operator awareness"),
        Hypothesis("S7", "Safety training effectiveness cannot be measured with current tools"),
        Hypothesis("S8", "Contractor safety compliance is poorly monitored"),
        Hypothesis("S9", "Equipment lockout/tagout procedures have verification gaps"),
        Hypothesis("S10", "Safety investment ROI is difficult to quantify for budget approval"),
    ]
    
    # ══════════════════════════════════════════════════════════════
    # Q-CUBE HYPERCUBE — 10 LENS DEFINITIONS (per QCUBE_HYPERCUBE_DOCTRINE_v1.md)
    # ══════════════════════════════════════════════════════════════
    
    # Foundation Lenses (1-3)
    Q_LAYERS = {"L1": "Operator", "L2": "Manager", "L3": "Executive"}
    Q_OBJECTS = {"OA": "Upstream", "OB": "Transfer Point", "OC": "Downstream"}
    Q_STACKS = {"Sα": "Cross-Mill", "Sβ": "Post-Investment", "Sγ": "Baseline Void", "Sδ": "Dual Impact"}
    
    # Analytical Lenses (4-6)
    Q_AWARENESS = {"A1": "Unaware", "A2": "Aware-Accepted", "A3": "Aware-Suffering", "A4": "Aware-Acting"}
    Q_EVIDENCE = {"V1": "Anecdotal", "V2": "Experiential", "V3": "Quantified", "V4": "Documented"}
    Q_TIMEHORIZON = {"T1": "Chronic", "T2": "Episodic", "T3": "Acute", "T4": "Latent"}
    
    # Innovation Lenses (7-10) — Team GIBUSH Originals
    Q_CASCADE = {"C1": "Direct", "C2": "One Handoff", "C3": "Two Handoffs", 
                 "C4": "Three Handoffs", "C5": "Four Handoffs", "C6": "Full Cascade"}
    Q_NORMALIZATION = {"N1": "Recognized Hazard", "N2": "Tolerated Risk",
                       "N3": "Accepted Practice", "N4": "Invisible Normal"}
    Q_COUNTERFLOW = {"Fm": "Material Only", "F$": "Money Only", 
                     "Fi": "Information Only", "Fg": "Gap Position"}
    Q_TRIBALKNOWLEDGE = {"K1": "Institutional", "K2": "Procedural", 
                         "K3": "Tribal", "K4": "Lost"}
    
    # Equipment categories for gap analysis
    EQUIPMENT_CATEGORIES = {
        "CHIP_HANDLING": ["Chip Conveyor", "Chip Bins", "Screw Conveyors", "Pneumatic Blow Lines"],
        "SCREENING": ["CTS Rollers", "Primary Knotters", "Screen Baskets", "Vibrating Screens"],
        "DIGESTER": ["Feed Screws", "High Pressure Feeders", "Blow Valves", "Blow Tank"],
        "WASHING": ["Brown Stock Washers", "Pressure Screens", "Centrifugal Cleaners"],
        "PUMPING": ["MC Pumps", "HC Pumps", "Stock Pumps", "Pump Impellers"],
        "BARK": ["Debarker Chains", "Bark Conveyors", "Bark Blow Lines", "Hog Fuel Feed"],
        "RECOVERY": ["Recovery Boiler Grates", "Pre-Tube Pipes", "Economizer Tubes"],
    }
    
    def __init__(self, project: str = "BCM_SUBSTRATE"):
        """
        Initialize doctoral analyzer for specific project.
        
        Args:
            project: "BCM_SUBSTRATE" or "BCM_NAVIGATION"
        """
        self.project = project
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.test_run_history: List[Dict] = []
        self.equipment_mentions: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "costs": [], "tests": []})
        self.q_cube_coverage: Dict[str, List[int]] = defaultdict(list)
        
        # Initialize project-specific hypotheses
        if project == "BCM_SUBSTRATE":
            for h in self.BCM_SUBSTRATE_HYPOTHESES:
                self.hypotheses[h.id] = Hypothesis(h.id, h.statement)
        else:
            for h in self.BCM_NAVIGATION_HYPOTHESES:
                self.hypotheses[h.id] = Hypothesis(h.id, h.statement)
    
    def load_test_database(self, db_path: Path) -> int:
        """
        Load existing test_run database and update hypothesis states.
        
        Returns: Number of tests loaded
        """
        if not db_path.exists():
            return 0
        
        with open(db_path, 'r') as f:
            data = json.load(f)
        
        self.test_run_history = data.get('tests', [])
        
        # Process each test_run for hypothesis updates
        for test_entry in self.test_run_history:
            self._process_test_run_evidence(test_run)
        
        # Update Q-Cube coverage
        cube_matrix = data.get('cube_matrix', {})
        for position, test_nums in cube_matrix.items():
            self.q_cube_coverage[position] = test_nums
        
        return len(self.test_run_history)
    
    def _process_test_run_evidence(self, test_entry: Dict):
        """Extract evidence from test_run and update hypotheses"""
        results = test_entry.get('results', '').lower()
        action = test_entry.get('action_iterate', '').lower()
        test_num = test_entry.get('test_num', 0)
        
        # Extract equipment mentions and costs
        for category, equipment_list in self.EQUIPMENT_CATEGORIES.items():
            for equip in equipment_list:
                if equip.lower() in results:
                    self.equipment_mentions[equip]["count"] += 1
                    self.equipment_mentions[equip]["tests"].append(test_num)
                    
                    # Extract cost figures
                    cost_pattern = r'\$[\d,]+(?:k|K)?|\d+(?:,\d+)?\s*(?:thousand|million|k|K)'
                    costs = re.findall(cost_pattern, results)
                    for cost in costs:
                        self.equipment_mentions[equip]["costs"].append(cost)
        
        # Update hypothesis beliefs based on keywords
        evidence_keywords = {
            "H1": {"supports": ["100% fail", "all got through", "manual catch"], "contradicts": ["effective detection", "catches most"]},
            "H2": {"supports": ["paid premium", "no verification", "visual only"], "contradicts": ["verified quality", "certification works"]},
            "H3": {"supports": ["$100k", "$300k", "roller damage", "cts damage"], "contradicts": ["minimal damage", "low cost"]},
            "H4": {"supports": ["screen basket", "$45k", "basket replacement"], "contradicts": ["baskets last", "normal wear"]},
            "H5": {"supports": ["feel", "sense", "hear", "notice"], "contradicts": ["didn't notice", "no warning"]},
            "H6": {"supports": ["no budget", "budget frozen", "can't approve"], "contradicts": ["budget available", "approved"]},
            "H7": {"supports": ["oem", "andritz", "valmet", "integrate"], "contradicts": ["direct to mill", "mill buys"]},
            "H8": {"supports": ["bark blow", "bark line", "bark damage"], "contradicts": ["bark fine", "no bark issues"]},
            "H9": {"supports": ["mud season", "seasonal", "spring", "winter"], "contradicts": ["year-round same", "no seasonal"]},
            "H10": {"supports": ["insurance", "investor", "prove", "data"], "contradicts": ["don't care", "no interest"]},
        }
        
        for hyp_id, keywords in evidence_keywords.items():
            if hyp_id not in self.hypotheses:
                continue
            
            supports = any(kw in results or kw in action for kw in keywords["supports"])
            contradicts = any(kw in results or kw in action for kw in keywords["contradicts"])
            
            if supports and not contradicts:
                self.hypotheses[hyp_id].update_belief(2.0, test_num, True)
            elif contradicts and not supports:
                self.hypotheses[hyp_id].update_belief(0.5, test_num, False)
    
    def calculate_information_gain(self, question: str, target_hypothesis: str) -> float:
        """
        Calculate expected information gain for a question.
        
        Uses entropy reduction formula:
        IG = H(prior) - E[H(posterior)]
        """
        if target_hypothesis not in self.hypotheses:
            return 0.0
        
        hyp = self.hypotheses[target_hypothesis]
        p = hyp.posterior_probability
        
        # Current entropy
        if p == 0 or p == 1:
            current_entropy = 0
        else:
            current_entropy = -p * math.log2(p) - (1-p) * math.log2(1-p)
        
        # Expected posterior entropy (assuming moderate evidence)
        # If we get supporting evidence (50% chance), posterior moves toward 1
        # If we get contradicting evidence (50% chance), posterior moves toward 0
        p_support = min(0.95, p * 1.5)
        p_contradict = max(0.05, p * 0.5)
        
        entropy_support = -p_support * math.log2(p_support + 1e-10) - (1-p_support) * math.log2(1-p_support + 1e-10)
        entropy_contradict = -p_contradict * math.log2(p_contradict + 1e-10) - (1-p_contradict) * math.log2(1-p_contradict + 1e-10)
        
        expected_posterior_entropy = 0.5 * entropy_support + 0.5 * entropy_contradict
        
        return max(0, current_entropy - expected_posterior_entropy)
    
    def identify_q_cube_gaps(self) -> List[str]:
        """
        Identify gaps across ALL 10 LENSES of the Q-Cube Hypercube.
        
        Scans foundation 3 (position gaps) + analytical 3 (evidence gaps) + 
        innovation 4 (original framework gaps).
        """
        gaps = []
        
        # ── FOUNDATION GAPS: Position coverage ──
        for layer in self.Q_LAYERS:
            for obj in self.Q_OBJECTS:
                for stack in self.Q_STACKS:
                    position = f"[{layer}, {obj}, {stack}]"
                    coverage = len(self.q_cube_coverage.get(position, []))
                    
                    if coverage == 0:
                        gaps.append(f"CRITICAL GAP: {position} - {self.Q_LAYERS[layer]} at {self.Q_OBJECTS[obj]} ({self.Q_STACKS[stack]}) - NO DATA")
                    elif coverage < 2:
                        gaps.append(f"WEAK: {position} - Only {coverage} test_run(s)")
        
        # ── ANALYTICAL LENS GAPS: Evidence quality ──
        lens_coverage = {
            'awareness': {k: 0 for k in self.Q_AWARENESS},
            'evidence': {k: 0 for k in self.Q_EVIDENCE},
            'timehorizon': {k: 0 for k in self.Q_TIMEHORIZON},
        }
        
        for iv in self.test_run_history:
            a = iv.get('q_awareness', '')
            if a in lens_coverage['awareness']:
                lens_coverage['awareness'][a] += 1
            v = iv.get('q_evidence', '')
            if v in lens_coverage['evidence']:
                lens_coverage['evidence'][v] += 1
            t = iv.get('q_timehorizon', '')
            if t in lens_coverage['timehorizon']:
                lens_coverage['timehorizon'][t] += 1
        
        for lens_name, coverage in lens_coverage.items():
            for code, count in coverage.items():
                if count == 0:
                    label = getattr(self, f'Q_{lens_name.upper()}', {}).get(code, code)
                    gaps.append(f"ANALYTICAL GAP [{lens_name}]: {code} ({label}) - NO test_runs")
        
        # ── INNOVATION LENS GAPS: Original framework coverage ──
        innovation_coverage = {
            'cascade': {k: 0 for k in self.Q_CASCADE},
            'normalization': {k: 0 for k in self.Q_NORMALIZATION},
            'counterflow': {k: 0 for k in self.Q_COUNTERFLOW},
            'tribalknowledge': {k: 0 for k in self.Q_TRIBALKNOWLEDGE},
        }
        
        for iv in self.test_run_history:
            c = iv.get('q_cascade', '')
            if c in innovation_coverage['cascade']:
                innovation_coverage['cascade'][c] += 1
            n = iv.get('q_normalization', '')
            if n in innovation_coverage['normalization']:
                innovation_coverage['normalization'][n] += 1
            f = iv.get('q_counterflow', '')
            if f in innovation_coverage['counterflow']:
                innovation_coverage['counterflow'][f] += 1
            k = iv.get('q_tribalknowledge', '')
            if k in innovation_coverage['tribalknowledge']:
                innovation_coverage['tribalknowledge'][k] += 1
        
        for lens_name, coverage in innovation_coverage.items():
            for code, count in coverage.items():
                if count == 0:
                    label_dict = {
                        'cascade': self.Q_CASCADE,
                        'normalization': self.Q_NORMALIZATION,
                        'counterflow': self.Q_COUNTERFLOW,
                        'tribalknowledge': self.Q_TRIBALKNOWLEDGE,
                    }
                    label = label_dict[lens_name].get(code, code)
                    gaps.append(f"INNOVATION GAP [{lens_name}]: {code} ({label}) - NO test_runs")
        
        return gaps
    
    def identify_equipment_gaps(self) -> List[str]:
        """Identify equipment without cost data"""
        gaps = []
        
        for category, equipment_list in self.EQUIPMENT_CATEGORIES.items():
            for equip in equipment_list:
                data = self.equipment_mentions.get(equip, {"count": 0, "costs": []})
                
                if data["count"] == 0:
                    gaps.append(f"NO MENTION: {equip} ({category})")
                elif len(data["costs"]) == 0:
                    gaps.append(f"NO COST DATA: {equip} - mentioned {data['count']}x but no $ figures")
        
        return gaps
    
    def detect_contradictions(self) -> List[str]:
        """Find contradictions between test_runs that need resolution"""
        contradictions = []
        
        for hyp_id, hyp in self.hypotheses.items():
            if hyp.supporting_tests and hyp.contradicting_tests:
                contradictions.append(
                    f"CONTRADICTION on {hyp_id}: '{hyp.statement}' - "
                    f"Supported by test_runs {hyp.supporting_tests}, "
                    f"Contradicted by {hyp.contradicting_tests}. "
                    f"Current confidence: {hyp.posterior_probability:.1%}"
                )
        
        return contradictions
    
    def generate_adaptive_questions(self, 
                                     target_layer: str = None,
                                     target_object: str = None,
                                     target_company: str = None,
                                     max_questions: int = 10) -> List[QuestionCandidate]:
        """
        Generate ranked questions optimized for information gain.
        
        Args:
            target_layer: Optional Q-Layer focus (L1, L2, L3)
            target_object: Optional Q-Object focus (OA, OB, OC)
            target_company: Company name for context
            max_questions: Maximum questions to return
        
        Returns:
            List of QuestionCandidate sorted by priority_score
        """
        candidates = []
        
        # 1. Questions for uncertain hypotheses (max information gain)
        for hyp_id, hyp in self.hypotheses.items():
            if hyp.status != "TESTING":
                continue
            
            # Higher priority for hypotheses near 50% (most uncertain)
            uncertainty = 1 - abs(hyp.posterior_probability - 0.5) * 2
            info_gain = self.calculate_information_gain("", hyp_id)
            
            question = self._generate_hypothesis_question(hyp, target_layer)
            
            candidates.append(QuestionCandidate(
                question=question,
                target_hypothesis=hyp_id,
                information_gain=info_gain,
                q_cube_coverage=[],
                equipment_focus=[],
                cost_discovery_potential=0.3,
                priority_score=info_gain * uncertainty,
                priority="HIGH" if info_gain > 0.5 else "MEDIUM",
                rationale=f"Hypothesis {hyp_id} at {hyp.posterior_probability:.0%} confidence — max entropy reduction target"
            ))
        
        # 2. Questions for equipment cost gaps
        equipment_gaps = self.identify_equipment_gaps()
        for gap in equipment_gaps[:5]:  # Top 5 gaps
            if "NO COST DATA" in gap:
                equip_name = gap.split(":")[1].split("-")[0].strip()
                
                question = f"What is the annual damage/replacement cost for {equip_name}? How often does contamination cause failures?"
                
                candidates.append(QuestionCandidate(
                    question=question,
                    target_hypothesis="COST_DISCOVERY",
                    information_gain=0.8,
                    q_cube_coverage=[],
                    equipment_focus=[equip_name],
                    cost_discovery_potential=0.9,
                    priority_score=0.85,
                    priority="HIGH",
                    rationale=f"Equipment {equip_name} mentioned but no cost data — quantified pain = defensible BMC"
                ))
        
        # 3. Questions for Q-Cube gaps
        cube_gaps = self.identify_q_cube_gaps()
        for gap in cube_gaps[:3]:  # Top 3 gaps
            if "CRITICAL GAP" in gap:
                position = gap.split(":")[1].split("-")[0].strip()
                
                question = self._generate_cube_gap_question(position, target_layer)
                
                candidates.append(QuestionCandidate(
                    question=question,
                    target_hypothesis="CUBE_COVERAGE",
                    information_gain=0.7,
                    q_cube_coverage=[position],
                    equipment_focus=[],
                    cost_discovery_potential=0.5,
                    priority_score=0.75,
                    priority="MEDIUM",
                    rationale=f"Q-Cube position {position} has zero coverage — blind spot in test_run data"
                ))
        
        # 4. Questions for contradiction resolution
        contradictions = self.detect_contradictions()
        for contradiction in contradictions[:2]:
            hyp_id = contradiction.split(":")[0].split()[-1]
            
            question = f"We've heard conflicting views on this. From your experience: {self.hypotheses.get(hyp_id, Hypothesis('', '')).statement}. What's your take?"
            
            candidates.append(QuestionCandidate(
                question=question,
                target_hypothesis=hyp_id,
                information_gain=0.9,
                q_cube_coverage=[],
                equipment_focus=[],
                cost_discovery_potential=0.4,
                priority_score=0.95,  # High priority for contradiction resolution
                priority="CRITICAL",
                rationale=f"Hypothesis {hyp_id} has conflicting evidence — resolution determines pivot/validate"
            ))
        
        # 5. Innovation lens gap questions (10-lens hypercube coverage)
        all_gaps = self.identify_q_cube_gaps()
        innovation_gaps = [g for g in all_gaps if 'INNOVATION GAP' in g or 'ANALYTICAL GAP' in g]
        for gap in innovation_gaps[:5]:
            # Parse gap: "INNOVATION GAP [cascade]: C1 (Direct) - NO test_runs"
            parts = gap.split(']:', 1)
            lens_name = parts[0].split('[')[-1] if '[' in parts[0] else 'unknown'
            code = parts[1].strip().split(' ')[0] if len(parts) > 1 else ''
            
            question = self._generate_lens_gap_question(lens_name, code)
            if question:
                candidates.append(QuestionCandidate(
                    question=question,
                    target_hypothesis="LENS_COVERAGE",
                    information_gain=0.6,
                    q_cube_coverage=[],
                    equipment_focus=[],
                    cost_discovery_potential=0.3,
                    priority_score=0.65,
                    priority="MEDIUM",
                    rationale=f"Hypercube lens gap: {lens_name} {code} — no test_runs in this analytical position"
                ))
        
        # Sort by priority score and return top N
        candidates.sort(key=lambda x: x.priority_score, reverse=True)
        return candidates[:max_questions]
    
    def _generate_hypothesis_question(self, hyp: Hypothesis, target_layer: str = None) -> str:
        """Generate targeted question for specific hypothesis"""
        
        # Layer-appropriate framing
        if target_layer == "L3":
            prefix = "From a strategic perspective, "
        elif target_layer == "L2":
            prefix = "In your role managing operations, "
        else:
            prefix = "On the floor, "
        
        # Hypothesis-specific questions
        question_templates = {
            "H1": f"{prefix}how effective is manual rock detection at your facility? What percentage would you estimate gets through?",
            "H2": f"{prefix}when you procure chips, can you verify the 'clean' certification? What's the actual verification process?",
            "H3": f"{prefix}what's the annual cost of CTS roller damage at your facility? How does that compare to your expectations?",
            "H4": f"{prefix}how often do you replace screen baskets, and what triggers replacement - scheduled PM or contamination damage?",
            "H5": f"{prefix}do operators sense problems before instruments detect them? Can you give me a specific example?",
            "H6": f"{prefix}if you needed to approve a $50K contamination prevention system, what's the budget approval process?",
            "H7": f"{prefix}would you prefer to buy detection technology directly or have it integrated by equipment OEMs like Andritz?",
            "H8": f"{prefix}how does contamination impact in bark blow lines compare to chip lines? Which causes more damage?",
            "H9": f"{prefix}does mud season significantly change your contamination problems? What's the seasonal pattern?",
            "H10": f"{prefix}would investors or insurance companies value contamination monitoring data? Would it affect premiums?",
        }
        
        return question_templates.get(hyp.id, f"Tell me about your experience with: {hyp.statement}")
    
    def _generate_cube_gap_question(self, position: str, target_layer: str = None) -> str:
        """Generate question to fill Q-Cube coverage gap"""
        
        # Parse position like "[L2, OB, SÎ²]"
        parts = position.strip("[]").split(", ")
        if len(parts) != 3:
            return "Tell me about contamination challenges at your facility."
        
        layer, obj, stack = parts
        
        layer_context = {
            "L1": "from an operator's daily experience",
            "L2": "from a management/production perspective", 
            "L3": "from a strategic/executive view"
        }
        
        object_context = {
            "OA": "with upstream suppliers and incoming material",
            "OB": "at transfer points like blow lines",
            "OC": "in downstream equipment like digesters"
        }
        
        stack_context = {
            "Sα": "patterns you see across multiple mills",
            "Sβ": "problems that persist despite modern equipment",
            "Sγ": "baseline data gaps in new systems",
            "Sδ": "issues affecting multiple product lines"
        }
        
        return f"Can you describe {layer_context.get(layer, '')} {object_context.get(obj, '')}? Specifically interested in {stack_context.get(stack, '')}."
    
    def _generate_lens_gap_question(self, lens_name: str, code: str) -> str:
        """Generate question to fill innovation/analytical lens gap."""
        
        lens_questions = {
            # Cascade Depth gaps
            'cascade': {
                'C1': "Can you describe a contamination problem where the same person who creates it also suffers the damage?",
                'C2': "Where does contamination pass through exactly one handoff before causing damage?",
                'C3': "Can you trace a contamination event through two ownership changes?",
                'C4': "How many parties does contamination pass through before it damages your equipment?",
                'C5': "Has contamination ever traveled through 4+ companies before reaching you?",
                'C6': "Can you describe a case where contamination was completely untraceable to its source?",
            },
            # Normalization of Deviance gaps
            'normalization': {
                'N1': "What contamination practices does your facility have zero tolerance for?",
                'N2': "What contamination risks does your team tolerate because they seem low-frequency?",
                'N3': "Are there contamination practices everyone knows about but considers 'just how we do it'?",
                'N4': "What would you NOT consider contamination that an outsider might?",
            },
            # Counter-Flow gaps
            'counterflow': {
                'Fm': "Do you see the physical contamination but have no visibility into what it costs downstream?",
                'F$': "Do you see the cost impact but can't trace it back to specific contamination sources?",
                'Fi': "Do you have data/reports about contamination but never see it physically?",
                'Fg': "Where do you feel you're in the dark — you know there's a problem but can't see the full picture?",
            },
            # Tribal Knowledge gaps
            'tribalknowledge': {
                'K1': "Is your contamination knowledge captured in formal systems like CMMS or SAP?",
                'K2': "How do you train new people about contamination — is it in written procedures?",
                'K3': "Is there anyone at your facility whose contamination knowledge would be lost if they retired tomorrow?",
                'K4': "Has your facility lost critical contamination knowledge through retirements or layoffs?",
            },
            # Awareness gaps
            'awareness': {
                'A1': "Have you encountered situations where contamination was happening but nobody realized it?",
                'A2': "What contamination issues does your team know about but consider acceptable?",
                'A3': "What contamination problem is causing you the most pain right now?",
                'A4': "What solutions have you tried or are you testing to address contamination?",
            },
            # Evidence gaps
            'evidence': {
                'V1': "Can you tell me a story about a contamination event you witnessed?",
                'V2': "How often do you personally deal with contamination issues?",
                'V3': "Can you put a dollar figure on contamination damage at your facility?",
                'V4': "Do you have maintenance logs or records that document contamination events?",
            },
            # Time Horizon gaps
            'timehorizon': {
                'T1': "Is contamination a constant, every-shift issue or more sporadic?",
                'T2': "Does contamination follow seasonal patterns at your facility?",
                'T3': "Can you describe the worst single contamination event you've experienced?",
                'T4': "Has routine inspection ever revealed contamination damage nobody knew about?",
            },
        }
        
        questions = lens_questions.get(lens_name, {})
        return questions.get(code, '')
    
    def generate_test_intelligence(self, 
                                          test_num: int,
                                          target_person: str,
                                          target_company: str,
                                          target_layer: str = "L2") -> TestIntelligence:
        """
        Generate comprehensive pre-test intelligence package.
        
        This is the main entry point for the doctoral analyzer.
        """
        intel = TestIntelligence(
            test_num=test_num,
            target_person=target_person,
            target_company=target_company
        )
        
        # Active hypotheses (still being tested)
        intel.active_hypotheses = [
            h for h in self.hypotheses.values() 
            if h.status == "TESTING"
        ]
        
        # Gap analysis
        intel.q_cube_gaps = self.identify_q_cube_gaps()[:5]
        intel.equipment_gaps = self.identify_equipment_gaps()[:10]
        
        # Contradictions
        intel.contradictions = self.detect_contradictions()
        
        # Generate adaptive questions
        intel.recommended_questions = self.generate_adaptive_questions(
            target_layer=target_layer,
            target_company=target_company,
            max_questions=10
        )
        
        # Identify synergy opportunities
        intel.synergy_opportunities = self._identify_synergy_opportunities(target_company)
        
        return intel
    
    def _identify_synergy_opportunities(self, target_company: str) -> List[str]:
        """Find patterns from similar companies/roles"""
        opportunities = []
        
        company_lower = target_company.lower()
        
        # Find test_runs from same company
        same_company = [
            i for i in self.test_run_history
            if i.get('source_version', '').lower() == company_lower
        ]
        
        if same_company:
            opportunities.append(
                f"Previous tests at {target_company}: {len(same_company)} - "
                f"Test Runees: {', '.join(i.get('script_name', '') for i in same_company)}"
            )
        
        # Find synergy clusters (cube positions with multiple test_runs)
        for position, test_nums in self.q_cube_coverage.items():
            if len(test_nums) >= 3:
                opportunities.append(
                    f"Strong synergy at {position}: {len(test_nums)} test_runs - "
                    f"Look for pattern confirmation"
                )
        
        return opportunities
    
    def get_hypothesis_status_report(self) -> Dict:
        """Generate summary of all hypothesis states"""
        return {
            "total": len(self.hypotheses),
            "validated": sum(1 for h in self.hypotheses.values() if h.status == "VALIDATED"),
            "invalidated": sum(1 for h in self.hypotheses.values() if h.status == "INVALIDATED"),
            "testing": sum(1 for h in self.hypotheses.values() if h.status == "TESTING"),
            "hypotheses": [
                {
                    "id": h.id,
                    "statement": h.statement,
                    "confidence": f"{h.posterior_probability:.1%}",
                    "status": h.status,
                    "supporting": len(h.supporting_tests),
                    "contradicting": len(h.contradicting_tests)
                }
                for h in self.hypotheses.values()
            ]
        }
    
    def export_state(self, filepath: Path):
        """Export analyzer state for persistence"""
        state = {
            "project": self.project,
            "timestamp": datetime.now().isoformat(),
            "hypotheses": {
                h_id: {
                    "statement": h.statement,
                    "prior": h.prior_probability,
                    "posterior": h.posterior_probability,
                    "supporting": h.supporting_tests,
                    "contradicting": h.contradicting_tests,
                    "status": h.status
                }
                for h_id, h in self.hypotheses.items()
            },
            "equipment_mentions": dict(self.equipment_mentions),
            "q_cube_coverage": dict(self.q_cube_coverage)
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    def import_state(self, filepath: Path):
        """Import analyzer state from file"""
        if not filepath.exists():
            return
        
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.project = state.get("project", self.project)
        
        for h_id, h_data in state.get("hypotheses", {}).items():
            if h_id in self.hypotheses:
                self.hypotheses[h_id].posterior_probability = h_data.get("posterior", 0.5)
                self.hypotheses[h_id].supporting_tests = h_data.get("supporting", [])
                self.hypotheses[h_id].contradicting_tests = h_data.get("contradicting", [])
                self.hypotheses[h_id].status = h_data.get("status", "TESTING")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_analyzer(project: str = "BCM_SUBSTRATE", db_path: Path = None) -> DoctoralAnalyzer:
    """
    Factory function to create and initialize a doctoral analyzer.
    
    Args:
        project: "BCM_SUBSTRATE" or "BCM_NAVIGATION"
        db_path: Optional path to test_run database
    
    Returns:
        Initialized DoctoralAnalyzer instance
    """
    analyzer = DoctoralAnalyzer(project)
    
    if db_path and db_path.exists():
        analyzer.load_test_database(db_path)
    
    return analyzer


def generate_test_run_packet(analyzer: DoctoralAnalyzer,
                               test_num: int,
                               person: str,
                               company: str,
                               layer: str = "L2") -> Dict:
    """
    Generate complete test_run preparation packet.
    
    Returns dict suitable for JSON serialization or document generation.
    """
    intel = analyzer.generate_test_intelligence(
        test_num=test_num,
        target_person=person,
        target_company=company,
        target_layer=layer
    )
    
    return {
        "test_num": intel.test_num,
        "target": f"{intel.target_person} at {intel.target_company}",
        "hypothesis_status": analyzer.get_hypothesis_status_report(),
        "q_cube_gaps": intel.q_cube_gaps,
        "equipment_gaps": intel.equipment_gaps,
        "contradictions": intel.contradictions,
        "recommended_questions": [
            {
                "question": q.question,
                "priority": f"{q.priority_score:.2f}",
                "targets_hypothesis": q.target_hypothesis,
                "information_gain": f"{q.information_gain:.2f}",
                "cost_discovery": f"{q.cost_discovery_potential:.0%}"
            }
            for q in intel.recommended_questions
        ],
        "synergy_opportunities": intel.synergy_opportunities
    }


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == "__main__":
    # Example usage
    analyzer = create_analyzer("BCM_SUBSTRATE")
    
    # Generate intelligence for test_run 14
    packet = generate_test_run_packet(
        analyzer,
        test_num=14,
        person="Vin Webster",
        company="Georgia-Pacific Palatka",
        layer="L3"
    )
    
    print(json.dumps(packet, indent=2))
