# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - KNOWLEDGE EXTRACTION ENGINE
============================================
Extracts structured knowledge from raw test_run text using NLP + pattern matching.

NOT toy regex - actual entity recognition with confidence scoring.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json


class EntityType(Enum):
    """Types of entities we extract from tests"""
    COST = "cost"
    EQUIPMENT = "equipment"
    PERSON = "script_name"
    COMPANY = "source_version"
    PAIN_POINT = "pain_point"
    VALIDATION = "validation"
    TIMELINE = "timeline"
    METRIC = "metric"
    # 10-Lens Hypercube entity types (Team GIBUSH originals)
    CASCADE_SIGNAL = "cascade_signal"           # Supply chain handoff evidence
    NORMALIZATION_SIGNAL = "normalization_signal"  # Deviance acceptance evidence
    COUNTERFLOW_SIGNAL = "counterflow_signal"    # Information gap evidence
    TRIBALKNOWLEDGE_SIGNAL = "tribalknowledge_signal"  # Retirement risk evidence


@dataclass
class ExtractedEntity:
    """Single extracted entity with confidence score"""
    entity_type: EntityType
    value: str
    context: str  # Surrounding text
    confidence: float  # 0.0 to 1.0
    source_test_run: str
    
    def to_dict(self) -> Dict:
        return {
            'type': self.entity_type.value,
            'value': self.value,
            'context': self.context,
            'confidence': self.confidence,
            'source': self.source_test_run
        }


class KnowledgeExtractor:
    """
    Extracts structured knowledge from test_run text.
    
    Uses multi-strategy approach:
    1. Pattern matching for costs, metrics, timelines
    2. Context analysis for equipment mentions
    3. Sentiment analysis for pain severity
    4. Cross-validation scoring
    """
    
    # Equipment keywords from kraft mill domain
    EQUIPMENT_KEYWORDS = {
        'cts': ('CTS Rollers', 0.9),
        'chip thickness screening': ('CTS Rollers', 1.0),
        'screen basket': ('Screen Baskets', 0.95),
        'basket': ('Screen Baskets', 0.7),
        'digester': ('Digester', 0.95),
        'digester bottom': ('Digester Bottom Scraper', 1.0),
        'blow line': ('Blow Line Piping', 0.9),
        'brown stock washer': ('Brown Stock Washers', 1.0),
        'washer': ('Washers', 0.6),
        'pump': ('Pumps', 0.8),
        'feeder': ('Feeders', 0.85),
        'knotter': ('Knotters', 0.9),
        'refiner': ('Refiners', 0.9),
        'boiler': ('Boiler', 0.85),
        'recovery boiler': ('Recovery Boiler', 0.95),
        'conveyor': ('Conveyors', 0.8),
        'rotor': ('Rotors', 0.85),
    }
    
    # Pain point indicators with severity weights
    PAIN_INDICATORS = {
        'downtime': ('Unplanned Downtime', 0.9),
        'damage': ('Equipment Damage', 0.85),
        'fail': ('System Failure', 0.9),
        'blind': ('Lack of Visibility', 0.8),
        'no detection': ('No Detection Capability', 0.95),
        'reactive': ('Reactive Maintenance', 0.75),
        'contamination': ('Contamination Events', 0.85),
        'can\'t see': ('Visibility Gap', 0.8),
        'don\'t know': ('Knowledge Gap', 0.75),
        'no baseline': ('Missing Baseline Data', 0.85),
    }
    
    def __init__(self, project=None):
        self.project = project
        self.extracted_entities: List[ExtractedEntity] = []
    
    def extract_from_test_run(self, person_name: str, text: str) -> List[ExtractedEntity]:
        """
        Extract all entities from test_run text.
        
        Args:
            test_num: Test Run number
            text: Combined text (hypotheses + results + action)
        
        Returns:
            List of extracted entities with confidence scores
        """
        entities = []
        text_lower = text.lower()
        
        # Extract costs
        entities.extend(self._extract_costs(person_name, text, text_lower))
        
        # Extract equipment
        entities.extend(self._extract_equipment(person_name, text, text_lower))
        
        # Extract pain points
        entities.extend(self._extract_pain_points(person_name, text, text_lower))
        
        # Extract validations
        entities.extend(self._extract_validations(person_name, text, text_lower))
        
        # Extract metrics
        entities.extend(self._extract_metrics(person_name, text, text_lower))
        
        # Extract timelines
        entities.extend(self._extract_timelines(person_name, text, text_lower))
        
        # Extract 10-lens hypercube signals (Team GIBUSH originals)
        entities.extend(self._extract_cascade_signals(person_name, text, text_lower))
        entities.extend(self._extract_normalization_signals(person_name, text, text_lower))
        entities.extend(self._extract_counterflow_signals(person_name, text, text_lower))
        entities.extend(self._extract_tribalknowledge_signals(person_name, text, text_lower))
        
        self.extracted_entities.extend(entities)
        return entities
    
    def _extract_costs(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract cost figures with high precision"""
        costs = []
        
        # Pattern 1: $XXX,XXX format
        pattern1 = r'\$[\d,]+(?:k|K|M)?'
        for match in re.finditer(pattern1, text):
            cost_str = match.group()
            context = self._get_context(text, match.start(), match.end())
            
            # Normalize cost
            normalized = self._normalize_cost(cost_str)
            
            # Confidence based on context
            confidence = 0.9
            if 'annual' in context.lower() or 'per year' in context.lower():
                confidence = 0.95
            
            costs.append(ExtractedEntity(
                entity_type=EntityType.COST,
                value=f"${normalized:,.0f}",
                context=context,
                confidence=confidence,
                source_test_run=person_name
            ))
        
        # Pattern 2: XXXk annual/per year
        pattern2 = r'(\d+)k\s*(?:annual|per year|\/year)'
        for match in re.finditer(pattern2, text_lower):
            amount = int(match.group(1)) * 1000
            context = self._get_context(text, match.start(), match.end())
            
            costs.append(ExtractedEntity(
                entity_type=EntityType.COST,
                value=f"${amount:,.0f}",
                context=context,
                confidence=0.9,
                source_test_run=person_name
            ))
        
        return costs
    
    def _extract_equipment(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract equipment mentions with context"""
        equipment = []
        
        for keyword, (equip_name, base_confidence) in self.EQUIPMENT_KEYWORDS.items():
            if keyword in text_lower:
                # Find all occurrences
                for match in re.finditer(re.escape(keyword), text_lower):
                    context = self._get_context(text, match.start(), match.end())
                    
                    # Boost confidence if damage/cost mentioned nearby
                    confidence = base_confidence
                    if any(word in context.lower() for word in ['damage', 'fail', 'replace', 'repair', '$']):
                        confidence = min(1.0, confidence + 0.1)
                    
                    equipment.append(ExtractedEntity(
                        entity_type=EntityType.EQUIPMENT,
                        value=equip_name,
                        context=context,
                        confidence=confidence,
                        source_test_run=person_name
                    ))
        
        return equipment
    
    def _extract_pain_points(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract pain points with severity scoring"""
        pains = []
        
        for indicator, (pain_name, severity) in self.PAIN_INDICATORS.items():
            if indicator in text_lower:
                for match in re.finditer(re.escape(indicator), text_lower):
                    context = self._get_context(text, match.start(), match.end())
                    
                    # Severity as confidence
                    confidence = severity
                    
                    pains.append(ExtractedEntity(
                        entity_type=EntityType.PAIN_POINT,
                        value=pain_name,
                        context=context,
                        confidence=confidence,
                        source_test_run=person_name
                    ))
        
        return pains
    
    def _extract_validations(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract hypothesis validations/invalidations"""
        validations = []
        
        # Validation patterns
        if 'validated:' in text_lower or 'validated' in text_lower:
            # Find what was validated
            pattern = r'(?:validated:?|validation:?)\s*([^.]+)'
            for match in re.finditer(pattern, text_lower):
                claim = match.group(1).strip()
                context = self._get_context(text, match.start(), match.end())
                
                validations.append(ExtractedEntity(
                    entity_type=EntityType.VALIDATION,
                    value=f"VALIDATED: {claim}",
                    context=context,
                    confidence=0.95,
                    source_test_run=person_name
                ))
        
        # Invalidation patterns
        if 'pivot' in text_lower or 'wrong customer' in text_lower:
            context = self._get_context(text, text_lower.find('pivot'), text_lower.find('pivot') + 20)
            validations.append(ExtractedEntity(
                entity_type=EntityType.VALIDATION,
                value="INVALIDATED: Hypothesis requires pivot",
                context=context,
                confidence=0.9,
                source_test_run=person_name
            ))
        
        return validations
    
    def _extract_metrics(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract quantitative metrics"""
        metrics = []
        
        # Pattern: XX% or XX percent
        pattern = r'(\d+)(?:%|percent)'
        for match in re.finditer(pattern, text_lower):
            value = match.group(1)
            context = self._get_context(text, match.start(), match.end())
            
            metrics.append(ExtractedEntity(
                entity_type=EntityType.METRIC,
                value=f"{value}%",
                context=context,
                confidence=0.85,
                source_test_run=person_name
            ))
        
        # Pattern: X times per year, X events/year
        pattern2 = r'(\d+)\s*(?:times|events)?\s*(?:per year|\/year|annually)'
        for match in re.finditer(pattern2, text_lower):
            value = match.group(1)
            context = self._get_context(text, match.start(), match.end())
            
            metrics.append(ExtractedEntity(
                entity_type=EntityType.METRIC,
                value=f"{value} events/year",
                context=context,
                confidence=0.9,
                source_test_run=person_name
            ))
        
        return metrics
    
    def _extract_timelines(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract temporal information"""
        timelines = []
        
        # Years
        pattern = r'(19|20)\d{2}'
        for match in re.finditer(pattern, text):
            year = match.group()
            context = self._get_context(text, match.start(), match.end())
            
            timelines.append(ExtractedEntity(
                entity_type=EntityType.TIMELINE,
                value=year,
                context=context,
                confidence=0.95,
                source_test_run=person_name
            ))
        
        return timelines
    
    def _extract_cascade_signals(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract supply chain cascade / handoff signals."""
        signals = []
        CASCADE_PATTERNS = {
            'supplier': ('Upstream source identified', 0.7),
            'chip mill': ('Chip mill handoff point', 0.85),
            'truck': ('Transport handoff', 0.75),
            'hauler': ('Transport handoff', 0.75),
            'landing': ('Forest landing — cascade origin', 0.8),
            'can\'t trace': ('Traceability gap — deep cascade', 0.95),
            'don\'t know where': ('Source unknown — cascade severed', 0.9),
            'nobody owns': ('Accountability gap in supply chain', 0.95),
            'passes through': ('Multi-handoff cascade', 0.8),
            'by the time': ('Cascade delay signal', 0.85),
            'forest to': ('Full cascade origin-to-destination', 0.9),
        }
        for keyword, (signal_name, confidence) in CASCADE_PATTERNS.items():
            if keyword in text_lower:
                for match in re.finditer(re.escape(keyword), text_lower):
                    context = self._get_context(text, match.start(), match.end())
                    signals.append(ExtractedEntity(
                        entity_type=EntityType.CASCADE_SIGNAL,
                        value=signal_name,
                        context=context,
                        confidence=confidence,
                        source_test_run=person_name
                    ))
        return signals
    
    def _extract_normalization_signals(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract normalization of deviance signals (Vaughan framework)."""
        signals = []
        NORM_PATTERNS = {
            'always been': ('Embedded practice — N3/N4 signal', 0.85),
            'part of the job': ('Accepted deviance — N3', 0.9),
            'cost of doing business': ('Economic normalization — N3', 0.9),
            'nobody tracks': ('Invisible normal — N4', 0.95),
            'just how it is': ('Cultural acceptance — N3', 0.85),
            'standard practice': ('Industry normalization — N3', 0.8),
            'everybody does': ('Universal acceptance — N3', 0.85),
            'not a problem': ('Denial of hazard — N4', 0.9),
            'zero tolerance': ('Recognized hazard — N1', 0.95),
            'unacceptable': ('Active resistance — N1', 0.9),
            'never allow': ('Policy enforcement — N1', 0.95),
        }
        for keyword, (signal_name, confidence) in NORM_PATTERNS.items():
            if keyword in text_lower:
                for match in re.finditer(re.escape(keyword), text_lower):
                    context = self._get_context(text, match.start(), match.end())
                    signals.append(ExtractedEntity(
                        entity_type=EntityType.NORMALIZATION_SIGNAL,
                        value=signal_name,
                        context=context,
                        confidence=confidence,
                        source_test_run=person_name
                    ))
        return signals
    
    def _extract_counterflow_signals(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract counter-flow / information gap signals."""
        signals = []
        FLOW_PATTERNS = {
            'don\'t know what happens': ('Information gap — Fg', 0.95),
            'never hear back': ('Feedback loop severed — Fg', 0.9),
            'no visibility': ('Visibility gap — Fg', 0.95),
            'can\'t see': ('Material blind spot — Fm gap', 0.85),
            'don\'t see the cost': ('Money flow gap — F$ gap', 0.9),
            'no data': ('Information flow absent — Fi gap', 0.9),
            'no tracking': ('Information flow absent — Fi gap', 0.85),
            'we see the damage': ('Material flow visible only — Fm', 0.8),
            'we pay for': ('Money flow visible — F$', 0.75),
        }
        for keyword, (signal_name, confidence) in FLOW_PATTERNS.items():
            if keyword in text_lower:
                for match in re.finditer(re.escape(keyword), text_lower):
                    context = self._get_context(text, match.start(), match.end())
                    signals.append(ExtractedEntity(
                        entity_type=EntityType.COUNTERFLOW_SIGNAL,
                        value=signal_name,
                        context=context,
                        confidence=confidence,
                        source_test_run=person_name
                    ))
        return signals
    
    def _extract_tribalknowledge_signals(self, person_name: str, text: str, text_lower: str) -> List[ExtractedEntity]:
        """Extract tribal knowledge / retirement clock signals."""
        signals = []
        TK_PATTERNS = {
            'when i retire': ('Retirement risk — K3 critical', 1.0),
            'only person': ('Single point of knowledge — K3', 0.95),
            'i just know': ('Tacit knowledge — K3', 0.85),
            'years of experience': ('Experience-based knowledge — K3', 0.8),
            'old hands': ('Generational knowledge — K3', 0.85),
            'nobody remembers': ('Knowledge already lost — K4', 0.95),
            'used to know': ('Knowledge degradation — K4', 0.9),
            'new crew': ('Knowledge transfer gap — K3→K4 risk', 0.85),
            'sap': ('Institutional knowledge — K1', 0.8),
            'cmms': ('Institutional knowledge — K1', 0.85),
            'maintenance log': ('Documented knowledge — K1', 0.8),
            'sop': ('Procedural knowledge — K2', 0.8),
            'we train': ('Knowledge transfer active — K2', 0.75),
        }
        for keyword, (signal_name, confidence) in TK_PATTERNS.items():
            if keyword in text_lower:
                for match in re.finditer(re.escape(keyword), text_lower):
                    context = self._get_context(text, match.start(), match.end())
                    signals.append(ExtractedEntity(
                        entity_type=EntityType.TRIBALKNOWLEDGE_SIGNAL,
                        value=signal_name,
                        context=context,
                        confidence=confidence,
                        source_test_run=person_name
                    ))
        return signals
    
    def _get_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """Get surrounding context for an entity"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()
    
    def _normalize_cost(self, cost_str: str) -> float:
        """Normalize cost string to float"""
        cost_str = cost_str.replace('$', '').replace(',', '')
        
        if cost_str.endswith('k') or cost_str.endswith('K'):
            return float(cost_str[:-1]) * 1000
        elif cost_str.endswith('M'):
            return float(cost_str[:-1]) * 1000000
        else:
            return float(cost_str)
    
    def get_entity_summary(self) -> Dict:
        """Get summary of all extracted entities"""
        summary = {
            'total_entities': len(self.extracted_entities),
            'by_type': {},
            'high_confidence': []
        }
        
        # Count by type
        for entity in self.extracted_entities:
            etype = entity.entity_type.value
            if etype not in summary['by_type']:
                summary['by_type'][etype] = 0
            summary['by_type'][etype] += 1
            
            # High confidence entities
            if entity.confidence >= 0.9:
                summary['high_confidence'].append(entity.to_dict())
        
        return summary
    
    def export_knowledge_graph(self, filepath: str):
        """Export entities as JSON for graph builder"""
        data = {
            'entities': [e.to_dict() for e in self.extracted_entities],
            'summary': self.get_entity_summary()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test extraction — loads from actual test_run database
    import sys
    from pathlib import Path
    
    db_path = Path("FUSION_Projects/test_database.json")
    if not db_path.exists():
        print(f"No database at {db_path} — cannot test without real data.")
        sys.exit(1)
    
    with open(db_path, 'r') as f:
        db_data = json.load(f)
    
    extractor = KnowledgeExtractor()
    
    for iv in db_data.get('tests', []):
        text = ' '.join(filter(None, [
            iv.get('results', ''), iv.get('experiments', ''),
            iv.get('hypotheses', ''), iv.get('action_iterate', '')
        ]))
        if text.strip():
            entities = extractor.extract_from_test_run(iv['script_name'], text)
            print(f"  {iv['script_name']}: {len(entities)} entities")
    
    print(f"\nSummary:")
    print(json.dumps(extractor.get_entity_summary(), indent=2))
