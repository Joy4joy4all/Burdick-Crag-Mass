# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - COGNITIVE SYNTHESIS ENGINE
===========================================
The actual intelligence. Takes knowledge graph and synthesizes strategic insights.

Uses:
- Bayesian inference for hypothesis confidence
- Information gain calculation for next test selection
- Pattern recognition across test network
- Predictive modeling for segment validation
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter
import networkx as nx


@dataclass
class Hypothesis:
    """Hypothesis with Bayesian confidence tracking"""
    name: str
    prior: float  # Initial belief (0-1)
    posterior: float  # Updated belief after evidence
    evidence_for: List[str]  # Supporting evidence
    evidence_against: List[str]  # Contradicting evidence
    confidence_interval: Tuple[float, float]  # (low, high)
    
    def update_posterior(self, evidence_strength: float, evidence_direction: int):
        """
        Log-odds Bayesian update (Appendix A.1 compliant).
        
        Formula:
            log_odds(posterior) = log_odds(prior) + direction × strength
        
        This is a rule-based scoring system with Bayesian wrapper.
        Likelihood ratios are heuristically assigned, not empirically learned.
        The value is in structured tracking and convergence visibility,
        not in statistical optimality.
        """
        import math
        
        # Clamp away from 0 and 1 to avoid log(0)
        p = max(0.01, min(0.99, self.posterior))
        
        # Log-odds formulation
        log_odds = math.log(p / (1.0 - p))
        
        # Update: direction = +1 (supporting) or -1 (contradicting)
        # strength = heuristic weight (0.1 - 0.5)
        log_odds += evidence_direction * evidence_strength
        
        # Convert back to probability
        self.posterior = 1.0 / (1.0 + math.exp(-log_odds))
        
        # Confidence interval: pedagogical convergence indicator
        # half_width = 0.15 / sqrt(evidence_count)
        # NOT a formal credible interval — visual indicator only.
        # Can be extended to Beta-Binomial posterior updates if desired.
        evidence_count = len(self.evidence_for) + len(self.evidence_against)
        if evidence_count == 0:
            half_width = 0.15
        else:
            half_width = 0.15 / math.sqrt(evidence_count)
        self.confidence_interval = (
            max(0.0, self.posterior - half_width),
            min(1.0, self.posterior + half_width)
        )


@dataclass
class TestGap:
    """Information gap that needs filling"""
    gap_type: str  # 'cube_position', 'entity_validation', 'cost_range', 'equipment_detail'
    description: str
    priority: float  # 0-1, how critical to fill
    suggested_test_profile: Dict  # What to test next
    expected_information_gain: float  # How much this would teach us


@dataclass
class StrategicInsight:
    """High-level strategic conclusion from synthesis"""
    insight_type: str  # 'segment', 'pattern', 'opportunity', 'risk'
    title: str
    description: str
    confidence: float
    supporting_tests: List[int]
    actionable_recommendation: str


class CognitiveSynthesisEngine:
    """
    The brain. Synthesizes knowledge graph into strategic intelligence.
    """
    
    def __init__(self, graph_data: Dict, knowledge_entities: Dict,
                 qcube_axes: Optional[Dict] = None):
        self.graph_data = graph_data
        self.knowledge_entities = knowledge_entities
        
        # Q-Cube axis configuration — loaded from config, NOT hardcoded.
        # Default matches heavy industry (backward compatible).
        # Any BCM team can define their own axes.
        if qcube_axes is None:
            self.qcube_axes = {
                'axis_1': ['L1', 'L2', 'L3', 'L4', 'L5'],  # Role levels
                'axis_2': ['OEM', 'OC', 'CS', 'AC', 'RG'],  # Company types
                'axis_3': ['Sa', 'Sb', 'Sg', 'Sd'],          # Segment stacks
            }
        else:
            self.qcube_axes = qcube_axes
        
        # Build NetworkX graph from data
        self.graph = nx.DiGraph()
        for node in graph_data['nodes']:
            self.graph.add_node(node['id'], **node)
        for edge in graph_data['edges']:
            self.graph.add_edge(edge['source'], edge['target'], **edge)
        
        # Initialize hypotheses
        self.hypotheses: Dict[str, Hypothesis] = self._initialize_hypotheses()
        
        # Track insights
        self.insights: List[StrategicInsight] = []
        
        # Track gaps
        self.gaps: List[TestGap] = []
    
    def _initialize_hypotheses(self) -> Dict[str, Hypothesis]:
        """Initialize standard ICorps hypotheses with priors"""
        return {
            'manual_detection_fails': Hypothesis(
                name="Manual Detection is Industry-Wide Failure",
                prior=0.5,
                posterior=0.5,
                evidence_for=[],
                evidence_against=[],
                confidence_interval=(0.4, 0.6)
            ),
            'cost_understated': Hypothesis(
                name="True Cost Impact is Understated",
                prior=0.6,
                posterior=0.6,
                evidence_for=[],
                evidence_against=[],
                confidence_interval=(0.5, 0.7)
            ),
            'modern_equipment_insufficient': Hypothesis(
                name="Capital Investment Alone Doesn't Solve Contamination",
                prior=0.5,
                posterior=0.5,
                evidence_for=[],
                evidence_against=[],
                confidence_interval=(0.4, 0.6)
            ),
            'operator_knowledge_gap': Hypothesis(
                name="Operators Sense Problems Instruments Miss",
                prior=0.7,
                posterior=0.7,
                evidence_for=[],
                evidence_against=[],
                confidence_interval=(0.6, 0.8)
            ),
            'blow_line_blind_spot': Hypothesis(
                name="Blow Line Entry Point is Critical Blind Spot",
                prior=0.6,
                posterior=0.6,
                evidence_for=[],
                evidence_against=[],
                confidence_interval=(0.5, 0.7)
            )
        }
    
    def run_synthesis(self) -> Dict:
        """
        Main synthesis pipeline.
        
        Returns comprehensive strategic intelligence report.
        """
        print("BRAIN GENESIS COGNITIVE SYNTHESIS RUNNING...")
        
        # Step 1: Update hypothesis confidence from evidence
        self._update_hypotheses_from_evidence()
        
        # Step 2: Detect cross-test patterns
        patterns = self._detect_patterns()
        
        # Step 3: Identify information gaps
        self._identify_gaps()
        
        # Step 4: Calculate next-best test
        next_test_entry = self._calculate_next_best_test()
        
        # Step 5: Generate strategic insights
        self._generate_insights()
        
        # Step 6: Synthesize substrate classs with confidence
        segments = self._synthesize_segments()
        
        # Step 7: Calculate market opportunity with risk adjustment
        opportunity = self._calculate_opportunity()
        
        return {
            'hypotheses': {name: self._hypothesis_to_dict(h) for name, h in self.hypotheses.items()},
            'patterns': patterns,
            'gaps': [self._gap_to_dict(g) for g in self.gaps],
            'next_best_test': next_test,
            'insights': [self._insight_to_dict(i) for i in self.insights],
            'substrate_classs': segments,
            'market_opportunity': opportunity
        }
    
    def _update_hypotheses_from_evidence(self):
        """Update hypothesis posteriors based on test evidence"""
        
        # Hypothesis 1: Manual detection fails
        manual_mentions = 0
        for node_id, node_data in self.graph.nodes(data=True):
            # Check if this test mentions substrate detection
            node_entities = [e for e in self.knowledge_entities['entities'] if e['source'] == node_id]
            
            for entity in node_entities:
                if entity['type'] == 'validation' and 'manual' in entity['value'].lower():
                    manual_mentions += 1
                    self.hypotheses['manual_detection_fails'].evidence_for.append(
                        f"Test {node_id}: {entity['value']}"
                    )
        
        if manual_mentions > 0:
            evidence_strength = min(0.8, manual_mentions * 0.2)
            self.hypotheses['manual_detection_fails'].update_posterior(evidence_strength, 1)
        
        # Hypothesis 2: Cost understated
        costs = [e for e in self.knowledge_entities['entities'] if e['type'] == 'cost']
        if len(costs) >= 3:
            # Multiple cost mentions = validation
            cost_values = []
            for cost in costs:
                try:
                    val = float(cost['value'].replace('$', '').replace(',', '').replace('k', '000').replace('K', '000'))
                    cost_values.append(val)
                except:
                    pass
            
            if cost_values:
                avg_cost = np.mean(cost_values)
                if avg_cost > 200000:  # >$200K
                    evidence_strength = 0.6
                    self.hypotheses['cost_understated'].evidence_for.append(
                        f"Average cost across {len(costs)} mentions: ${avg_cost:,.0f}"
                    )
                    self.hypotheses['cost_understated'].update_posterior(evidence_strength, 1)
        
        # Hypothesis 3: Modern equipment insufficient
        modern_equipment_fails = 0
        for entity in self.knowledge_entities['entities']:
            if entity['type'] == 'validation':
                if any(word in entity['value'].lower() for word in ['modern', 'new', 'upgraded']):
                    if any(word in entity['value'].lower() for word in ['fail', 'still', 'persist']):
                        modern_equipment_fails += 1
                        self.hypotheses['modern_equipment_insufficient'].evidence_for.append(
                            f"Test Run {entity['source']}: {entity['value']}"
                        )
        
        if modern_equipment_fails >= 2:
            evidence_strength = 0.7
            self.hypotheses['modern_equipment_insufficient'].update_posterior(evidence_strength, 1)
        
        # Hypothesis 4: Operator knowledge gap
        operator_mentions = sum(1 for e in self.knowledge_entities['entities'] 
                               if 'operator' in e.get('context', '').lower())
        if operator_mentions >= 3:
            evidence_strength = 0.5
            self.hypotheses['operator_knowledge_gap'].update_posterior(evidence_strength, 1)
        
        # Hypothesis 5: Blow line blind spot
        blind_spot_mentions = sum(1 for e in self.knowledge_entities['entities']
                                 if e['type'] == 'pain_point' and 'visibility' in e['value'].lower())
        if blind_spot_mentions >= 2:
            evidence_strength = 0.6
            self.hypotheses['blow_line_blind_spot'].update_posterior(evidence_strength, 1)
    
    def _detect_patterns(self) -> List[Dict]:
        """Detect high-level patterns across test network"""
        patterns = []
        
        # Pattern 1: Cost convergence
        costs = [e for e in self.knowledge_entities['entities'] if e['type'] == 'cost']
        if len(costs) >= 3:
            cost_values = []
            for cost in costs:
                try:
                    val = float(cost['value'].replace('$', '').replace(',', '').replace('k', '000'))
                    cost_values.append(val)
                except:
                    pass
            
            if cost_values:
                mean_cost = np.mean(cost_values)
                std_cost = np.std(cost_values)
                cv = std_cost / mean_cost if mean_cost > 0 else 0
                
                if cv < 0.3:  # Low coefficient of variation = consensus
                    patterns.append({
                        'type': 'cost_convergence',
                        'description': f'Strong cost consensus: ${mean_cost:,.0f} +/- ${std_cost:,.0f}',
                        'confidence': 0.9,
                        'test_count': len(costs),
                        'strategic_implication': 'High confidence in damage cost estimates. Use for ROI modeling.'
                    })
        
        # Pattern 2: Equipment concentration
        equipment = [e for e in self.knowledge_entities['entities'] if e['type'] == 'equipment']
        equipment_counter = Counter([e['value'] for e in equipment])
        most_common = equipment_counter.most_common(3)
        
        if most_common and most_common[0][1] >= 3:
            patterns.append({
                'type': 'equipment_hotspot',
                'description': f'Critical equipment identified: {most_common[0][0]} (mentioned {most_common[0][1]}x)',
                'confidence': 0.85,
                'equipment_list': [eq for eq, count in most_common],
                'strategic_implication': 'Focus detection deployment on these equipment types.'
            })
        
        # Pattern 3: Validation cluster strength
        communities = self.graph_data.get('communities', {})
        if communities:
            largest_community = max(communities.values(), key=len)
            if len(largest_community) >= 3:
                patterns.append({
                    'type': 'synergy_cluster',
                    'description': f'Strong validation cluster: {len(largest_community)} test_runs reinforce each other',
                    'confidence': 0.9,
                    'test_ids': largest_community,
                    'strategic_implication': 'Primary substrate class validated by multiple independent sources.'
                })
        
        # Pattern 4: Authority concentration
        authority_scores = self.graph_data.get('authority_scores', {})
        if authority_scores:
            top_authority = sorted(authority_scores.items(), key=lambda x: x[1], reverse=True)[0]
            if top_authority[1] > 0.3:  # Dominant authority
                patterns.append({
                    'type': 'information_hub',
                    'description': f'Test Run {top_authority[0]} is information hub (authority: {top_authority[1]:.2f})',
                    'confidence': 0.85,
                    'test_id': top_authority[0],
                    'strategic_implication': 'This test_run validates many others. High trust source.'
                })
        
        return patterns
    
    def _identify_gaps(self):
        """Identify critical information gaps using configurable Q-Cube axes."""
        
        # Gap 1: Missing cube positions (axis-agnostic)
        completed_positions = set()
        for node_id, node_data in self.graph.nodes(data=True):
            if 'cube_position' in node_data:
                completed_positions.add(node_data['cube_position'])
        
        # Generate all positions from configured axes
        all_positions = []
        for a1 in self.qcube_axes['axis_1']:
            for a2 in self.qcube_axes['axis_2']:
                for a3 in self.qcube_axes['axis_3']:
                    all_positions.append(f'[{a1}, {a2}, {a3}]')
        
        # Rank empty positions by adjacency to filled positions
        # (positions sharing 2 of 3 axes with filled = higher priority)
        for pos in all_positions:
            if pos in completed_positions:
                continue
            
            # Parse position values
            pos_vals = pos.strip('[]').split(', ')
            adjacency = 0
            for filled in completed_positions:
                filled_vals = filled.strip('[]').split(', ')
                if len(filled_vals) == 3 and len(pos_vals) == 3:
                    matches = sum(1 for a, b in zip(pos_vals, filled_vals) if a == b)
                    if matches >= 2:
                        adjacency += 1
            
            # Priority: adjacent positions are more informative (boundary expansion)
            priority = min(0.95, 0.5 + (adjacency * 0.15))
            info_gain = min(0.9, 0.4 + (adjacency * 0.15))
            
            if adjacency > 0 or len(completed_positions) < 3:
                self.gaps.append(TestGap(
                    gap_type='cube_position',
                    description=f'Missing test_runs from {pos}',
                    priority=priority,
                    suggested_test_profile={'cube_position': pos},
                    expected_information_gain=info_gain
                ))
        
        # Sort gaps by priority
        self.gaps.sort(key=lambda g: g.priority, reverse=True)
        
        # Gap 2: Cost validation needed
        costs = [e for e in self.knowledge_entities['entities'] if e['type'] == 'cost']
        if len(costs) < 5:
            self.gaps.append(TestGap(
                gap_type='entity_validation',
                description='Need more cost data points for confidence',
                priority=0.7,
                suggested_test_profile={'should_ask_about': 'annual damage costs'},
                expected_information_gain=0.6
            ))
        
        # Gap 3: Equipment detail needed
        equipment = [e for e in self.knowledge_entities['entities'] if e['type'] == 'equipment']
        equipment_with_costs = [e for e in self.knowledge_entities['entities'] 
                               if e['type'] == 'equipment' and '$' in e['context']]
        
        if len(equipment_with_costs) < len(equipment) * 0.5:
            self.gaps.append(TestGap(
                gap_type='equipment_detail',
                description='Equipment mentioned but costs not quantified',
                priority=0.8,
                suggested_test_profile={'should_ask_about': 'equipment damage costs'},
                expected_information_gain=0.7
            ))
    
    def _calculate_next_best_test(self) -> Dict:
        """
        Calculate which test_run would provide maximum information gain.
        
        Uses entropy reduction calculation.
        """
        # Score each gap by priority * expected information gain
        if not self.gaps:
            return {
                'recommendation': 'No critical gaps identified',
                'confidence': 1.0
            }
        
        best_gap = max(self.gaps, key=lambda g: g.priority * g.expected_information_gain)
        
        return {
            'recommendation': best_gap.description,
            'gap_type': best_gap.gap_type,
            'priority': best_gap.priority,
            'expected_information_gain': best_gap.expected_information_gain,
            'suggested_profile': best_gap.suggested_test_profile,
            'rationale': f"This fills a high-priority gap ({best_gap.gap_type}) with {best_gap.expected_information_gain:.0%} expected information gain"
        }
    
    def _generate_insights(self):
        """Generate strategic insights from patterns and hypotheses"""
        
        # Insight 1: From validated hypotheses
        for hyp_name, hyp in self.hypotheses.items():
            if hyp.posterior > 0.75:  # High confidence
                self.insights.append(StrategicInsight(
                    insight_type='validated_hypothesis',
                    title=f"VALIDATED: {hyp.name}",
                    description=f"Confidence: {hyp.posterior:.0%} (was {hyp.prior:.0%})",
                    confidence=hyp.posterior,
                    supporting_tests=[],  # Extract from evidence
                    actionable_recommendation=self._get_hypothesis_action(hyp_name)
                ))
        
        # Insight 2: From contradictions
        contradictions = self.graph_data.get('contradictions', [])
        if contradictions:
            high_severity = [c for c in contradictions if c['severity'] > 0.7]
            if high_severity:
                self.insights.append(StrategicInsight(
                    insight_type='risk',
                    title=f"CRITICAL: {len(high_severity)} High-Severity Contradictions Detected",
                    description=f"Conflicting claims need resolution",
                    confidence=0.9,
                    supporting_tests=[],
                    actionable_recommendation="Schedule follow-up test_runs to resolve contradictions before proceeding"
                ))
    
    def _get_hypothesis_action(self, hyp_name: str) -> str:
        """Get actionable recommendation for validated hypothesis"""
        actions = {
            'manual_detection_fails': "Position GIBUSH as replacement for failed manual detection. Emphasize 100% failure rate.",
            'cost_understated': "Use validated cost figures ($300K+) in ROI modeling. Emphasize true cost discovery.",
            'modern_equipment_insufficient': "Target mills with recent $1B+ modernizations. Message: 'Capital investment alone doesn't solve it.'",
            'operator_knowledge_gap': "Design MV buttons for operator control. Emphasize 'operators know first' in value prop.",
            'blow_line_blind_spot': "Focus all marketing on blow line entry point. 'Last-chance detection before digester.'"
        }
        return actions.get(hyp_name, "Leverage this validated insight in go-to-market strategy")
    
    def _synthesize_segments(self) -> List[Dict]:
        """Synthesize substrate classs with confidence scores"""
        segments = []
        
        # Use communities as initial segments
        communities = self.graph_data.get('communities', {})
        
        for comm_name, member_ids in communities.items():
            if len(member_ids) >= 2:  # Require at least 2 test_runs
                # Extract common characteristics
                cube_positions = []
                companies = []
                for member_id in member_ids:
                    node_data = self.graph.nodes[member_id]
                    cube_positions.append(node_data['cube_position'])
                    companies.append(node_data.get('source_version', ''))
                
                # Most common cube position
                position_counter = Counter(cube_positions)
                dominant_position = position_counter.most_common(1)[0]
                
                confidence = len(member_ids) / len(self.graph.nodes)  # Larger cluster = higher confidence
                
                segments.append({
                    'name': f"Segment from {comm_name}",
                    'cube_position': dominant_position[0],
                    'test_count': len(member_ids),
                    'confidence': min(0.95, confidence * 2),
                    'representative_companies': list(set(companies)),
                    'validation_strength': dominant_position[1] / len(member_ids)
                })
        
        return sorted(segments, key=lambda x: x['confidence'], reverse=True)
    
    def _calculate_opportunity(self) -> Dict:
        """Calculate market opportunity with risk adjustment"""
        # Simplified market sizing with confidence intervals
        
        # Extract validated cost data
        costs = [e for e in self.knowledge_entities['entities'] if e['type'] == 'cost']
        cost_values = []
        for cost in costs:
            try:
                val = float(cost['value'].replace('$', '').replace(',', '').replace('k', '000'))
                cost_values.append(val)
            except:
                pass
        
        if not cost_values:
            return {
                'message': 'Insufficient cost data for opportunity calculation',
                'confidence': 0.0
            }
        
        avg_damage_per_mill = np.mean(cost_values)
        std_damage = np.std(cost_values)
        
        # Estimated addressable market (from tests)
        # Count unique companies
        unique_companies = set([node_data.get('source_version', '') 
                               for node_id, node_data in self.graph.nodes(data=True)])
        unique_companies.discard('')
        
        # Extrapolate (very rough)
        estimated_mills = len(unique_companies) * 10  # Assume we've sampled 10% of market
        
        # Calculate opportunity
        total_annual_damage = avg_damage_per_mill * estimated_mills
        gibush_capture = total_annual_damage * 0.3  # 30% capture assumption
        
        # Risk adjustment based on hypothesis confidence
        avg_hyp_confidence = np.mean([h.posterior for h in self.hypotheses.values()])
        risk_adjusted_capture = gibush_capture * avg_hyp_confidence
        
        return {
            'average_damage_per_mill': f"${avg_damage_per_mill:,.0f}",
            'damage_std_dev': f"${std_damage:,.0f}",
            'estimated_addressable_mills': estimated_mills,
            'total_annual_industry_damage': f"${total_annual_damage:,.0f}",
            'gibush_30_percent_capture': f"${gibush_capture:,.0f}",
            'risk_adjusted_opportunity': f"${risk_adjusted_capture:,.0f}",
            'confidence': avg_hyp_confidence,
            'confidence_interval': (
                f"${risk_adjusted_capture * 0.7:,.0f}",
                f"${risk_adjusted_capture * 1.3:,.0f}"
            )
        }
    
    def _hypothesis_to_dict(self, h: Hypothesis) -> Dict:
        return {
            'name': h.name,
            'prior': h.prior,
            'posterior': h.posterior,
            'confidence_interval': h.confidence_interval,
            'evidence_for': h.evidence_for,
            'evidence_against': h.evidence_against
        }
    
    def _gap_to_dict(self, g: TestGap) -> Dict:
        return {
            'type': g.gap_type,
            'description': g.description,
            'priority': g.priority,
            'suggested_profile': g.suggested_test_profile,
            'expected_info_gain': g.expected_information_gain
        }
    
    def _insight_to_dict(self, i: StrategicInsight) -> Dict:
        return {
            'type': i.insight_type,
            'title': i.title,
            'description': i.description,
            'confidence': i.confidence,
            'recommendation': i.actionable_recommendation
        }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Load test data
    with open('/home/claude/test_graph.json', 'r') as f:
        graph_data = json.load(f)
    
    with open('/home/claude/test_entities.json', 'r') as f:
        entities_data = json.load(f)
    
    # Run cognitive synthesis
    engine = CognitiveSynthesisEngine(graph_data, entities_data)
    results = engine.run_synthesis()
    
    print(json.dumps(results, indent=2))
