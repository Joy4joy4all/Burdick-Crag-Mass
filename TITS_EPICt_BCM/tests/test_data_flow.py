#!/usr/bin/env python3
"""
GENESIS DATA FLOW VALIDATION TEST
==================================
Tests complete pipeline from interviews → Genesis → outputs → packet generation

Validates:
1. Interview database integrity
2. Equipment config loading
3. Genesis extraction accuracy
4. Graph building
5. Cognitive synthesis
6. Output file generation
7. Packet intelligence loading

NO STUBS. REAL DATA ONLY.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add current dir to path
sys.path.insert(0, str(Path.cwd()))

from genesis_brain import (
    KnowledgeExtractor,
    InterviewGraphBuilder,
    CognitiveSynthesisEngine,
    GenesisOrchestrator
)


class DataFlowValidator:
    """Validates entire Genesis data pipeline"""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
        
    def log(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        
        if not passed:
            self.errors.append(test_name)
    
    def test_interview_database(self) -> bool:
        """Test 1: Interview database exists and is valid"""
        print("\n" + "="*80)
        print("TEST 1: INTERVIEW DATABASE VALIDATION")
        print("="*80)
        
        try:
            db_file = Path("FUSION_INTERVIEWS/interview_database.json")
            
            # Check file exists
            if not db_file.exists():
                self.log("Database file exists", False, f"File not found: {db_file}")
                return False
            
            self.log("Database file exists", True, str(db_file))
            
            # Load and validate structure
            with open(db_file, 'r') as f:
                data = json.load(f)
            
            if 'interviews' not in data:
                self.log("Database structure valid", False, "Missing 'interviews' key")
                return False
            
            interviews = data['interviews']
            self.log("Database structure valid", True, f"{len(interviews)} interviews found")
            
            # Validate each interview has required fields
            required_fields = ['interview_num', 'person', 'company', 'hypotheses', 'results']
            missing_fields = []
            
            for interview in interviews:
                for field in required_fields:
                    if field not in interview:
                        missing_fields.append(f"Interview #{interview.get('interview_num', '?')}: missing '{field}'")
            
            if missing_fields:
                self.log("Interview fields complete", False, "\n    ".join(missing_fields))
                return False
            
            self.log("Interview fields complete", True, "All required fields present")
            
            # Check for text content
            empty_interviews = []
            for interview in interviews:
                text = f"{interview.get('hypotheses', '')} {interview.get('results', '')}"
                if len(text.strip()) < 50:
                    empty_interviews.append(f"Interview #{interview['interview_num']}: insufficient content ({len(text)} chars)")
            
            if empty_interviews:
                self.log("Interview content adequate", False, "\n    ".join(empty_interviews))
            else:
                total_chars = sum(len(f"{i.get('hypotheses', '')} {i.get('results', '')}") for i in interviews)
                self.log("Interview content adequate", True, f"Total: {total_chars:,} characters")
            
            return len(missing_fields) == 0 and len(empty_interviews) == 0
            
        except Exception as e:
            self.log("Database loading", False, str(e))
            return False
    
    def test_equipment_config(self) -> bool:
        """Test 2: Equipment config exists and is valid"""
        print("\n" + "="*80)
        print("TEST 2: EQUIPMENT CONFIGURATION VALIDATION")
        print("="*80)
        
        try:
            config_file = Path("config/equipment_config.json")
            
            if not config_file.exists():
                self.log("Equipment config exists", False, "config/equipment_config.json not found")
                return False
            
            self.log("Equipment config exists", True)
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Check structure
            if 'equipment_keywords' not in config:
                self.log("Config structure valid", False, "Missing 'equipment_keywords'")
                return False
            
            equipment_count = len(config['equipment_keywords'])
            self.log("Config structure valid", True, f"{equipment_count} equipment types defined")
            
            # Validate format
            invalid_entries = []
            for keyword, value in config['equipment_keywords'].items():
                if not isinstance(value, list) or len(value) != 2:
                    invalid_entries.append(f"{keyword}: {value}")
            
            if invalid_entries:
                self.log("Equipment format valid", False, "\n    ".join(invalid_entries))
                return False
            
            self.log("Equipment format valid", True, "All entries properly formatted [name, confidence]")
            
            return True
            
        except Exception as e:
            self.log("Equipment config loading", False, str(e))
            return False
    
    def test_knowledge_extraction(self) -> Tuple[bool, Dict]:
        """Test 3: Knowledge extractor works with real data"""
        print("\n" + "="*80)
        print("TEST 3: KNOWLEDGE EXTRACTION")
        print("="*80)
        
        try:
            # Load interviews
            with open("FUSION_INTERVIEWS/interview_database.json", 'r') as f:
                data = json.load(f)
            interviews = data['interviews']
            
            # Create extractor with config
            extractor = KnowledgeExtractor(equipment_config_file="config/equipment_config.json")
            
            # Extract from all interviews
            all_entities = []
            for interview in interviews:
                text = f"{interview.get('hypotheses', '')} {interview.get('results', '')} {interview.get('action_iterate', '')}"
                entities = extractor.extract_from_interview(interview['interview_num'], text)
                all_entities.extend(entities)
            
            total_entities = len(all_entities)
            self.log("Entities extracted", total_entities > 0, f"Extracted {total_entities} entities")
            
            # Validate entity types
            entity_types = {}
            for entity in all_entities:
                etype = entity.entity_type.value
                entity_types[etype] = entity_types.get(etype, 0) + 1
            
            expected_types = ['equipment', 'cost', 'pain_point']
            missing_types = [t for t in expected_types if t not in entity_types]
            
            if missing_types:
                self.log("Entity type coverage", False, f"Missing types: {missing_types}")
            else:
                type_summary = ", ".join([f"{k}: {v}" for k, v in entity_types.items()])
                self.log("Entity type coverage", True, type_summary)
            
            # Check confidence scores
            low_confidence = [e for e in all_entities if e.confidence < 0.5]
            avg_confidence = sum(e.confidence for e in all_entities) / len(all_entities)
            
            self.log("Entity confidence", avg_confidence >= 0.7, f"Average: {avg_confidence:.2f}")
            
            # Check equipment extraction specifically
            equipment_entities = [e for e in all_entities if e.entity_type.value == 'equipment']
            unique_equipment = set(e.value for e in equipment_entities)
            
            self.log("Equipment extraction", len(equipment_entities) > 0, 
                    f"{len(equipment_entities)} mentions, {len(unique_equipment)} unique types")
            
            return len(missing_types) == 0, {
                'total_entities': total_entities,
                'entity_types': entity_types,
                'avg_confidence': avg_confidence,
                'equipment_count': len(equipment_entities)
            }
            
        except Exception as e:
            self.log("Knowledge extraction", False, str(e))
            return False, {}
    
    def test_graph_building(self) -> Tuple[bool, Dict]:
        """Test 4: Graph builder creates valid network"""
        print("\n" + "="*80)
        print("TEST 4: GRAPH BUILDING")
        print("="*80)
        
        try:
            # Load interviews
            with open("FUSION_INTERVIEWS/interview_database.json", 'r') as f:
                data = json.load(f)
            interviews = data['interviews']
            
            # Build graph
            graph_builder = InterviewGraphBuilder()
            
            # Add nodes
            for interview in interviews:
                graph_builder.add_interview_node(
                    interview['interview_num'],
                    interview.get('person', ''),
                    interview.get('company', ''),
                    interview.get('q_layer', 'L2'),
                    interview.get('q_object', 'OC'),
                    interview.get('q_stack', ['Sa']),
                    []
                )
            
            node_count = len(graph_builder.nodes)
            self.log("Nodes created", node_count == len(interviews), f"{node_count} nodes")
            
            # Build edges
            graph_builder.build_edges()
            edge_count = len(graph_builder.edges)
            
            self.log("Edges created", edge_count > 0, f"{edge_count} edges")
            
            # Check edge types
            edge_types = {}
            for edge in graph_builder.edges:
                edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
            
            type_summary = ", ".join([f"{k}: {v}" for k, v in edge_types.items()])
            self.log("Edge types", 'validates' in edge_types or 'contradicts' in edge_types, type_summary)
            
            # Check communities
            communities = graph_builder.detect_synergy_communities()
            self.log("Communities detected", len(communities) > 0, f"{len(communities)} communities")
            
            return True, {
                'nodes': node_count,
                'edges': edge_count,
                'edge_types': edge_types,
                'communities': len(communities)
            }
            
        except Exception as e:
            self.log("Graph building", False, str(e))
            return False, {}
    
    def test_genesis_orchestrator(self) -> bool:
        """Test 5: Full Genesis orchestrator pipeline"""
        print("\n" + "="*80)
        print("TEST 5: GENESIS ORCHESTRATOR (FULL PIPELINE)")
        print("="*80)
        
        try:
            # Load interviews
            with open("FUSION_INTERVIEWS/interview_database.json", 'r') as f:
                data = json.load(f)
            interviews = data['interviews']
            
            # Run orchestrator
            output_dir = Path("GENESIS_OUTPUT_TEST")
            output_dir.mkdir(exist_ok=True, parents=True)
            
            orchestrator = GenesisOrchestrator(
                output_dir=output_dir,
                equipment_config=Path("config/equipment_config.json")
            )
            
            print("    Running full analysis...")
            result = orchestrator.run_full_analysis(interviews)
            
            self.log("Orchestrator completed", True, "Analysis finished without errors")
            
            # Check return value
            self.log("Return dict valid", 'total_entities' in result and 'success' in result,
                    f"Entities: {result.get('total_entities', 0)}")
            
            # Check output files
            expected_files = [
                'knowledge_entities.json',
                'interview_graph.json',
                'strategic_intelligence.json'
            ]
            
            missing_files = []
            for filename in expected_files:
                filepath = output_dir / filename
                if not filepath.exists():
                    missing_files.append(filename)
            
            if missing_files:
                self.log("Output files created", False, f"Missing: {missing_files}")
            else:
                self.log("Output files created", True, f"{len(expected_files)} files generated")
            
            # Validate strategic intelligence structure
            intel_file = output_dir / "strategic_intelligence.json"
            if intel_file.exists():
                with open(intel_file, 'r') as f:
                    intel = json.load(f)
                
                required_keys = ['hypotheses', 'patterns', 'gaps', 'customer_segments', 'market_opportunity']
                missing_keys = [k for k in required_keys if k not in intel]
                
                if missing_keys:
                    self.log("Intelligence structure", False, f"Missing: {missing_keys}")
                else:
                    self.log("Intelligence structure", True, "All required sections present")
            
            return len(missing_files) == 0
            
        except Exception as e:
            self.log("Genesis orchestrator", False, str(e))
            import traceback
            print(traceback.format_exc())
            return False
    
    def test_packet_intelligence(self) -> bool:
        """Test 6: Interview packet can load intelligence"""
        print("\n" + "="*80)
        print("TEST 6: PACKET INTELLIGENCE LOADING")
        print("="*80)
        
        try:
            # Simulate _load_genesis_intelligence method
            intel = {
                'available': False,
                'interview_count': 0,
                'equipment_mentions': {},
                'gaps': [],
                'hypotheses': {},
                'contradictions': []
            }
            
            # Check if Genesis output exists
            intel_file = Path("GENESIS_OUTPUT/strategic_intelligence.json")
            if not intel_file.exists():
                self.log("Genesis output available", False, "No prior Genesis analysis found")
                return False
            
            with open(intel_file, 'r') as f:
                data = json.load(f)
            
            intel['available'] = True
            self.log("Genesis output available", True)
            
            # Load graph for interview count
            graph_file = Path("GENESIS_OUTPUT/interview_graph.json")
            if graph_file.exists():
                with open(graph_file, 'r') as f:
                    graph = json.load(f)
                intel['interview_count'] = len(graph.get('nodes', []))
                self.log("Interview count loaded", True, f"{intel['interview_count']} interviews")
            
            # Load hypotheses
            for hyp_key, hyp_data in data.get('hypotheses', {}).items():
                intel['hypotheses'][hyp_data['name']] = {
                    'confidence': int(hyp_data['posterior'] * 100)
                }
            
            self.log("Hypotheses loaded", len(intel['hypotheses']) > 0, 
                    f"{len(intel['hypotheses'])} hypotheses")
            
            # Load gaps
            gaps = data.get('gaps', [])
            intel['gaps'] = [gap['description'] for gap in gaps[:3]]
            
            self.log("Gaps identified", len(intel['gaps']) > 0, 
                    f"{len(intel['gaps'])} critical gaps")
            
            # Load contradictions
            if graph_file.exists():
                contradiction_count = sum(1 for edge in graph.get('edges', []) 
                                        if edge.get('type') == 'contradicts')
                intel['contradictions'] = [f"Contradiction {i}" for i in range(contradiction_count)]
            
            self.log("Contradictions loaded", True, 
                    f"{len(intel['contradictions'])} contradictions")
            
            return True
            
        except Exception as e:
            self.log("Packet intelligence loading", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*80)
        print("GENESIS DATA FLOW VALIDATION TEST SUITE")
        print("="*80)
        print(f"Testing data pipeline integrity...\n")
        
        # Run tests in order
        test1 = self.test_interview_database()
        test2 = self.test_equipment_config()
        test3_pass, test3_data = self.test_knowledge_extraction()
        test4_pass, test4_data = self.test_graph_building()
        test5 = self.test_genesis_orchestrator()
        test6 = self.test_packet_intelligence()
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        
        print(f"\nTests Passed: {passed}/{total}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        if self.errors:
            print(f"\nFailed Tests:")
            for error in self.errors:
                print(f"  - {error}")
        
        # Data flow metrics
        if test3_data:
            print(f"\nData Flow Metrics:")
            print(f"  Total Entities Extracted: {test3_data.get('total_entities', 0)}")
            print(f"  Average Confidence: {test3_data.get('avg_confidence', 0):.2%}")
            print(f"  Equipment Mentions: {test3_data.get('equipment_count', 0)}")
        
        if test4_data:
            print(f"  Graph Nodes: {test4_data.get('nodes', 0)}")
            print(f"  Graph Edges: {test4_data.get('edges', 0)}")
            print(f"  Communities: {test4_data.get('communities', 0)}")
        
        print("\n" + "="*80)
        
        return passed == total


def main():
    """Main entry point"""
    validator = DataFlowValidator()
    all_passed = validator.run_all_tests()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
