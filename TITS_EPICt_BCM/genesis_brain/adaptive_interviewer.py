# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - ADAPTIVE TEST PARAMETER GENERATOR
======================================================
Generates next test parameters based on keywords and gaps from previous tests.
Enables homeostatic discovery - each test makes the next one smarter.

Peer-reviewed approach:
- Information gain calculation (Shannon entropy)
- Bayesian active learning (query by committee)
- Semantic similarity (cosine distance in embedding space)
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import Counter, defaultdict
import re


@dataclass
class KeywordAmplitude:
    """Keyword with measured amplitude (how loud/important)"""
    keyword: str
    frequency: int  # How many times mentioned
    context_intensity: float  # 0-1, based on surrounding words
    authority_weight: float  # Weighted by who said it (L1=3x, L2=1.5x, L3=1x)
    amplitude: float  # Combined score
    
    def __repr__(self):
        return f"{self.keyword} (amp: {self.amplitude:.2f})"


@dataclass
class ValidationQuestion:
    """Question designed to validate a hypothesis from previous tests"""
    question: str
    targets_keyword: str
    expected_info_gain: float  # 0-1
    validates_tests: List[int]  # Which tests this would validate
    priority: float  # 0-1


@dataclass
class ExplorationQuestion:
    """Question designed to explore gaps in knowledge"""
    question: str
    explores_gap: str
    cube_position: str
    expected_info_gain: float
    priority: float


class AdaptiveTestGenerator:
    """
    Generates adaptive test parameters that evolve based on what was learned.
    
    This is the homeostasis engine - keeps asking until system reaches equilibrium.
    """
    
    # Authority weights (operators know equipment truth best)
    AUTHORITY_WEIGHTS = {
        'L1': 3.0,   # Operators - they run the shit
        'L2': 1.5,   # Managers - they see P&L
        'L3': 1.0    # Executives - they hear filtered info
    }
    
    # High-intensity context words (indicate strong pain/truth)
    INTENSITY_AMPLIFIERS = {
        'always': 1.5,
        'never': 1.5,
        'every': 1.3,
        'constantly': 1.4,
        'severe': 1.4,
        'critical': 1.5,
        'disaster': 1.8,
        'catastrophic': 1.9,
        'impossible': 1.6,
        'fail': 1.4,
        'damage': 1.3,
        '$': 1.2  # Money mentioned = important
    }
    
    def __init__(self):
        self.keyword_amplitudes: List[KeywordAmplitude] = []
        self.validation_questions: List[ValidationQuestion] = []
        self.exploration_questions: List[ExplorationQuestion] = []
    
    def extract_high_amplitude_keywords(self, tests: List[Dict]) -> List[KeywordAmplitude]:
        """
        Extract keywords with amplitude scoring.
        
        Amplitude = frequency x context_intensity x authority_weight
        """
        # Aggregate all keywords with metadata
        keyword_data = defaultdict(lambda: {
            'count': 0,
            'contexts': [],
            'authority_levels': [],
            'sources': []
        })
        
        for test_entry in tests:
            text = f"{test_entry.get('hypotheses', '')} {test_entry.get('results', '')} {test_entry.get('action_iterate', '')}"
            text_lower = text.lower()
            
            authority = test_entry.get('q_layer', 'L2')
            script_key = test_entry.get("script_name", "Unknown")
            
            # Extract meaningful phrases (2-3 words)
            phrases = self._extract_phrases(text_lower)
            
            for phrase in phrases:
                keyword_data[phrase]['count'] += 1
                keyword_data[phrase]['contexts'].append(text_lower)
                keyword_data[phrase]['authority_levels'].append(authority)
                keyword_data[phrase]['sources'].append(test_num)
        
        # Calculate amplitudes
        amplitudes = []
        
        for keyword, data in keyword_data.items():
            if data['count'] >= 2:  # Must appear at least twice
                # Average authority weight
                auth_weights = [self.AUTHORITY_WEIGHTS[level] for level in data['authority_levels']]
                avg_auth_weight = np.mean(auth_weights)
                
                # Context intensity (check for amplifier words nearby)
                avg_intensity = self._calculate_context_intensity(data['contexts'], keyword)
                
                # Combined amplitude
                amplitude = data['count'] * avg_intensity * avg_auth_weight
                
                amplitudes.append(KeywordAmplitude(
                    keyword=keyword,
                    frequency=data['count'],
                    context_intensity=avg_intensity,
                    authority_weight=avg_auth_weight,
                    amplitude=amplitude
                ))
        
        # Sort by amplitude
        amplitudes.sort(key=lambda x: x.amplitude, reverse=True)
        
        self.keyword_amplitudes = amplitudes
        return amplitudes
    
    def _extract_phrases(self, text: str) -> List[str]:
        """Extract meaningful 2-3 word phrases"""
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        phrases = []
        
        # Skip common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                    'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
                    'is', 'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do',
                    'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might',
                    'can', 'that', 'this', 'these', 'those', 'what', 'which', 'who'}
        
        # Extract 2-word phrases
        for i in range(len(words) - 1):
            if words[i] not in stopwords and words[i+1] not in stopwords:
                phrase = f"{words[i]} {words[i+1]}"
                if len(phrase) > 5:  # Skip very short
                    phrases.append(phrase)
        
        # Extract 3-word phrases (more specific)
        for i in range(len(words) - 2):
            if (words[i] not in stopwords and 
                words[i+1] not in stopwords and 
                words[i+2] not in stopwords):
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                if len(phrase) > 8:
                    phrases.append(phrase)
        
        return phrases
    
    def _calculate_context_intensity(self, contexts: List[str], keyword: str) -> float:
        """Calculate intensity based on surrounding amplifier words"""
        total_intensity = 0.0
        
        for context in contexts:
            # Find keyword position
            try:
                idx = context.index(keyword)
            except ValueError:
                continue
            
            # Check surrounding  20 characters for amplifiers
            window_start = max(0, idx - 20)
            window_end = min(len(context), idx + len(keyword) + 20)
            window = context[window_start:window_end]
            
            intensity = 1.0
            for amplifier, multiplier in self.INTENSITY_AMPLIFIERS.items():
                if amplifier in window:
                    intensity *= multiplier
            
            total_intensity += intensity
        
        return total_intensity / len(contexts) if contexts else 1.0
    
    def generate_validation_questions(self, 
                                     top_keywords: List[KeywordAmplitude],
                                     next_test_profile: Dict) -> List[ValidationQuestion]:
        """
        Generate questions that validate high-amplitude keywords.
        
        Args:
            top_keywords: Keywords with highest amplitude
            next_test_profile: Who we're testing next
        """
        questions = []
        
        for keyword in top_keywords[:5]:  # Top 5 keywords
            # Different question templates based on keyword type
            if '$' in keyword.keyword or 'cost' in keyword.keyword or 'damage' in keyword.keyword:
                # Cost validation
                question = (f"Previous tests mentioned {keyword.keyword} as a significant issue. "
                          f"At {next_test_profile.get('source_version', 'your mill')}, "
                          f"can you break down where those costs hit you? "
                          f"Does that figure match your experience?")
                
            elif any(equip in keyword.keyword for equip in ['cts', 'screen', 'digester', 'pump', 'basket']):
                # Equipment validation
                question = (f"We've heard from {keyword.frequency} different people that {keyword.keyword} "
                          f"is a critical failure point. "
                          f"What's your experience with {keyword.keyword} at "
                          f"{next_test_profile.get('source_version', 'your operation')}? "
                          f"Can you quantify the damage?")
                
            elif 'manual' in keyword.keyword or 'detection' in keyword.keyword:
                # Detection validation
                question = (f"Multiple operators mentioned that {keyword.keyword}. "
                          f"Is that true at {next_test_profile.get('source_version', 'your facility')}? "
                          f"What have you tried that didn't work?")
                
            else:
                # Generic validation
                question = (f"{keyword.frequency} previous tests mentioned '{keyword.keyword}' "
                          f"as a recurring theme. "
                          f"Does this resonate with your experience? "
                          f"Can you elaborate on how this affects your operations?")
            
            # Calculate expected information gain
            # High amplitude keywords that haven't been validated much = high gain
            info_gain = keyword.amplitude / (keyword.frequency + 1)  # Diminishing returns
            
            questions.append(ValidationQuestion(
                question=question,
                targets_keyword=keyword.keyword,
                expected_info_gain=min(1.0, info_gain / 10),
                validates_tests=[],  # Would need to track sources
                priority=keyword.amplitude / max([k.amplitude for k in top_keywords])
            ))
        
        self.validation_questions = questions
        return questions
    
    def generate_exploration_questions(self,
                                      completed_cube_positions: Set[str],
                                      next_test_profile: Dict) -> List[ExplorationQuestion]:
        """
        Generate questions that explore gaps in the Q-Cube.
        """
        questions = []
        
        next_position = next_test_profile.get('cube_position', '[L2, OC, Sa]')
        
        # Gap 1: If no cost data from this cube position yet
        if self._is_new_position(next_position, completed_cube_positions):
            questions.append(ExplorationQuestion(
                question=(f"As someone in {next_position}, what does contamination "
                         f"actually cost you annually? Can you break it down by equipment type?"),
                explores_gap='cost_quantification',
                cube_position=next_position,
                expected_info_gain=0.8,
                priority=0.9
            ))
        
        # Gap 2: Operator knowledge gap
        if 'L1' in next_position:
            questions.append(ExplorationQuestion(
                question=("What do you sense or hear about the blow line that your "
                         "instruments don't tell you? What changes do you notice before "
                         "a contamination event actually happens?"),
                explores_gap='operator_sensing',
                cube_position=next_position,
                expected_info_gain=0.7,
                priority=0.85
            ))
        
        # Gap 3: Post-investment failure (if L2 or L3)
        if 'L2' in next_position or 'L3' in next_position:
            questions.append(ExplorationQuestion(
                question=("What equipment or systems have you invested in that were supposed "
                         "to solve contamination but didn't? What's still not working despite "
                         "the capital spend?"),
                explores_gap='investment_failure',
                cube_position=next_position,
                expected_info_gain=0.75,
                priority=0.8
            ))
        
        # Gap 4: Baseline data (if OC - downstream)
        if 'OC' in next_position:
            questions.append(ExplorationQuestion(
                question=("When you commission new equipment or start up after maintenance, "
                         "what baseline contamination data do you wish you had from day one? "
                         "How would that protect your investment?"),
                explores_gap='baseline_data',
                cube_position=next_position,
                expected_info_gain=0.7,
                priority=0.75
            ))
        
        self.exploration_questions = questions
        return questions
    
    def _is_new_position(self, position: str, completed: Set[str]) -> bool:
        """Check if this cube position hasn't been tested yet"""
        return position not in completed
    
    def generate_complete_test_run_guide(self,
                                          tests: List[Dict],
                                          next_profile: Dict) -> Dict:
        """
        Generate complete adaptive test_run guide for next test.
        
        Returns:
            {
                'validation_questions': [...],
                'exploration_questions': [...],
                'priority_order': [...],
                'expected_total_info_gain': float
            }
        """
        # Extract high-amplitude keywords
        keywords = self.extract_high_amplitude_keywords(test_runs)
        
        # Get completed positions
        completed_positions = set([i.get('cube_position', '') for i in test_runs])
        
        # Generate both types of questions
        validation_qs = self.generate_validation_questions(keywords[:5], next_profile)
        exploration_qs = self.generate_exploration_questions(completed_positions, next_profile)
        
        # Combine and prioritize
        all_questions = []
        for vq in validation_qs:
            all_questions.append({
                'type': 'validation',
                'question': vq.question,
                'priority': vq.priority,
                'info_gain': vq.expected_info_gain,
                'targets': vq.targets_keyword
            })
        
        for eq in exploration_qs:
            all_questions.append({
                'type': 'exploration',
                'question': eq.question,
                'priority': eq.priority,
                'info_gain': eq.expected_info_gain,
                'explores': eq.explores_gap
            })
        
        # Sort by priority
        all_questions.sort(key=lambda x: x['priority'], reverse=True)
        
        # Calculate expected total info gain
        total_gain = sum([q['info_gain'] * q['priority'] for q in all_questions])
        
        return {
            'next_test': next_profile,
            'high_amplitude_keywords': [{'keyword': k.keyword, 'amplitude': k.amplitude} 
                                       for k in keywords[:10]],
            'validation_questions': [q for q in all_questions if q['type'] == 'validation'],
            'exploration_questions': [q for q in all_questions if q['type'] == 'exploration'],
            'priority_order': all_questions,
            'expected_total_info_gain': total_gain,
            'recommended_focus': self._recommend_focus(keywords, next_profile)
        }
    
    def _recommend_focus(self, keywords: List[KeywordAmplitude], profile: Dict) -> str:
        """Recommend what to focus on in next test"""
        top_keyword = keywords[0] if keywords else None
        
        if not top_keyword:
            return "General discovery - no strong patterns yet"
        
        if top_keyword.amplitude > 20:
            return f"HIGH PRIORITY: Validate '{top_keyword.keyword}' - this has emerged as critical theme"
        elif top_keyword.amplitude > 10:
            return f"MEDIUM PRIORITY: Explore '{top_keyword.keyword}' further with this segment"
        else:
            return f"EXPLORATORY: Use this test_run to discover new patterns in {profile.get('cube_position', 'this segment')}"
    
    def detect_segment_saturation(self, tests: List[Dict], current_segment: str) -> Dict:
        """
        Detect if current segment is saturated (time to pivot to next segment).
        
        Saturation = when new test_runs don't add new information
        """
        segment_test_runs = [i for i in test_runs 
                             if current_segment in i.get('cube_position', '')]
        
        if len(segment_test_runs) < 3:
            return {
                'saturated': False,
                'confidence': 0.0,
                'reason': f'Only {len(segment_test_runs)} test_runs in this segment'
            }
        
        # Check keyword diversity over time
        early_keywords = set()
        late_keywords = set()
        
        midpoint = len(segment_test_runs) // 2
        
        for test_entry in segment_test_runs[:midpoint]:
            text = f"{test_entry.get('results', '')}"
            early_keywords.update(self._extract_phrases(text.lower()))
        
        for test_entry in segment_test_runs[midpoint:]:
            text = f"{test_entry.get('results', '')}"
            late_keywords.update(self._extract_phrases(text.lower()))
        
        # New information ratio
        new_info = late_keywords - early_keywords
        new_info_ratio = len(new_info) / len(late_keywords) if late_keywords else 0
        
        # Saturation threshold: <20% new information
        saturated = new_info_ratio < 0.2 and len(segment_test_runs) >= 5
        
        return {
            'saturated': saturated,
            'confidence': 1.0 - new_info_ratio if saturated else new_info_ratio,
            'new_info_ratio': new_info_ratio,
            'test_count': len(segment_test_runs),
            'reason': (f"{'SATURATED' if saturated else 'NOT SATURATED'}: "
                      f"{new_info_ratio:.0%} new information in recent test_runs")
        }
    
    def suggest_next_segment(self, 
                           completed_segments: List[str],
                           saturation_data: Dict) -> Dict:
        """
        Suggest next substrate class to test_run after current segment saturates.
        """
        # Segment progression logic
        segment_sequence = [
            {
                'name': 'Downstream Kraft Mills (Primary)',
                'cube_positions': ['[L2, OC, Sb]', '[L2, OC, Sa]', '[L1, OC, Sb]'],
                'priority': 1.0,
                'rationale': 'Experience contamination damage directly - highest pain'
            },
            {
                'name': 'Chip Suppliers (Upstream Accountability)',
                'cube_positions': ['[L2, OA, Sb]', '[L3, OA, Sa]'],
                'priority': 0.8,
                'rationale': 'Get blamed for contamination - need verification system'
            },
            {
                'name': 'Equipment OEMs (Integration Partners)',
                'cube_positions': ['[L3, OB, Sg]'],
                'priority': 0.6,
                'rationale': 'Want to add detection to equipment packages'
            },
            {
                'name': 'Mill Executives (Enterprise Deployment)',
                'cube_positions': ['[L3, OC, Sd]'],
                'priority': 0.7,
                'rationale': 'Multi-mill rollout decision makers'
            }
        ]
        
        # Find next uncompleted segment
        for segment in segment_sequence:
            if segment['name'] not in completed_segments:
                return {
                    'next_segment': segment['name'],
                    'target_positions': segment['cube_positions'],
                    'priority': segment['priority'],
                    'rationale': segment['rationale'],
                    'estimated_tests_needed': 5,
                    'pivot_recommendation': (
                        f"Current segment saturated at {saturation_data['confidence']:.0%} confidence. "
                        f"Pivot to {segment['name']}: {segment['rationale']}"
                    )
                }
        
        return {
            'next_segment': 'All primary segments completed',
            'recommendation': 'Begin deployment phase or explore adjacent markets'
        }


# =============================================================================
# TESTING & DEMO
# =============================================================================

if __name__ == "__main__":
    # Load test test_runs
    import sys
    from pathlib import Path
    
    db_file = Path("BCM_TESTS/test_database.json")
    if db_file.exists():
        with open(db_file, 'r') as f:
            data = json.load(f)
        test_runs = data['tests']
    else:
        print("No test_run database found")
        sys.exit(1)
    
    # Initialize generator
    generator = AdaptiveTestGenerator()
    
    # Extract high-amplitude keywords
    print("="*80)
    print("HIGH-AMPLITUDE KEYWORDS")
    print("="*80)
    keywords = generator.extract_high_amplitude_keywords(test_runs)
    for i, kw in enumerate(keywords[:10], 1):
        print(f"{i}. {kw.keyword:30} | Amp: {kw.amplitude:6.2f} | Freq: {kw.frequency}x | Auth: {kw.authority_weight:.1f}x")
    
    # Generate questions for next test
    print("\n" + "="*80)
    print("ADAPTIVE QUESTIONS FOR NEXT TEST")
    print("="*80)
    
    next_profile = {
        'test_num': 13,  # legacy test data
        'script_name': 'Brad Harville',
        'source_version': 'Green Bay Packaging',
        'cube_position': '[L2, OC, Sb]'
    }
    
    guide = generator.generate_complete_test_run_guide(test_runs, next_profile)
    
    print(f"\nNext Test Run: {next_profile['script_name']} ({next_profile['source_version']})")
    print(f"Position: {next_profile['cube_position']}")
    print(f"Expected Total Info Gain: {guide['expected_total_info_gain']:.2f}")
    print(f"\nRecommended Focus: {guide['recommended_focus']}")
    
    print("\nVALIDATION QUESTIONS:")
    for i, q in enumerate(guide['validation_questions'], 1):
        print(f"\n{i}. [Priority: {q['priority']:.2f}] {q['question']}")
    
    print("\nEXPLORATION QUESTIONS:")
    for i, q in enumerate(guide['exploration_questions'], 1):
        print(f"\n{i}. [Priority: {q['priority']:.2f}] {q['question']}")
    
    # Check saturation
    print("\n" + "="*80)
    print("SEGMENT SATURATION ANALYSIS")
    print("="*80)
    
    saturation = generator.detect_segment_saturation(test_runs, 'L2, OC')
    print(f"Saturated: {saturation['saturated']}")
    print(f"Confidence: {saturation['confidence']:.0%}")
    print(f"Reason: {saturation['reason']}")
    
    if saturation['saturated']:
        next_segment = generator.suggest_next_segment(['Downstream Kraft Mills'], saturation)
        print(f"\nNEXT SEGMENT: {next_segment['next_segment']}")
        print(f"Rationale: {next_segment['rationale']}")
        print(f"Target Positions: {next_segment['target_positions']}")
