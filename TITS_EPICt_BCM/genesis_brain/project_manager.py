# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - PROJECT MANAGER
================================
Multi-project support for separate test_run campaigns.

Projects:
- BCM_SUBSTRATE: Equipment damage BCM tests (external)
- BCM_NAVIGATION: Worker safety perception tests (internal)

Each project has its own:
- Test Run database
- Q-Cube matrix
- Analysis outputs
- Hypothesis set
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class ProjectType(Enum):
    """Project classification"""
    ICORPS_EXTERNAL = "icorps_external"      # Customer discovery (Chip Blow Line)
    SPINE_INTERNAL = "spine_internal"         # Internal safety (Woodland crew)
    CUSTOM = "custom"


@dataclass
class ProjectConfig:
    """Project configuration"""
    project_id: str
    project_name: str
    project_type: ProjectType
    description: str
    created_date: str
    hypotheses: List[str] = field(default_factory=list)
    target_test_runs: int = 100
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['project_type'] = self.project_type.value
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'ProjectConfig':
        d['project_type'] = ProjectType(d['project_type'])
        return cls(**d)


class ProjectManager:
    """
    Manages multiple test_run projects with isolated data.
    
    Directory structure:
    BCM_TESTS/
    ├── projects.json                    # Project registry
    ├── BCM_SUBSTRATE/
    │   ├── config.json
    │   ├── test_database.json
    │   ├── hypotheses.json
    │   └── GENESIS_OUTPUT/
    └── BCM_NAVIGATION/
        ├── config.json
        ├── test_database.json
        ├── safety_modules.json          # Module importance checklist
        ├── epv_assessments.json         # EPV evaluations
        └── GENESIS_OUTPUT/
    """
    
    DEFAULT_PROJECTS = {
        'BCM_SUBSTRATE': ProjectConfig(
            project_id='BCM_SUBSTRATE',
            project_name='Chip Blow Line Classifier',
            project_type=ProjectType.ICORPS_EXTERNAL,
            description='BCM customer discovery for rock/metal detection in chip handling. '
                       'Value proposition: Equipment protection, reduced downtime, ROI.',
            created_date=datetime.now().isoformat(),
            hypotheses=[
                'Rock contamination causes >$300K annual equipment damage per mill',
                'No detection technology exists at truck dump/chip pile',
                'Mills will pay for detection if ROI proven within 12 months',
                'OEMs (Andritz, Valmet) are better channel than direct sales'
            ],
            target_test_runs=100
        ),
        'BCM_NAVIGATION': ProjectConfig(
            project_id='BCM_NAVIGATION',
            project_name='SPINE Safety Assessment',
            project_type=ProjectType.SPINE_INTERNAL,
            description='Internal Woodland Pulp safety perception tests. '
                       'EPV assessment of worker safety concerns tied to position/experience.',
            created_date=datetime.now().isoformat(),
            hypotheses=[
                'Workers feel most unsafe in areas with poor visibility/detection',
                'Years of experience correlates with specific hazard awareness',
                'Position in mill (area) determines primary safety concerns',
                'Rock/metal events create both equipment AND personnel safety risk'
            ],
            target_test_runs=150  # All personnel
        )
    }
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path.cwd() / "BCM_TESTS"
        self.base_dir.mkdir(exist_ok=True, parents=True)
        self.registry_file = self.base_dir / "projects.json"
        self.projects: Dict[str, ProjectConfig] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load or initialize project registry"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
                for pid, pdata in data.get('projects', {}).items():
                    self.projects[pid] = ProjectConfig.from_dict(pdata)
        else:
            # Initialize with default projects
            self.projects = self.DEFAULT_PROJECTS.copy()
            self._save_registry()
            # Create project directories
            for pid in self.projects:
                self._init_project_dir(pid)
    
    def _save_registry(self):
        """Save project registry"""
        data = {
            'projects': {pid: p.to_dict() for pid, p in self.projects.items()},
            'last_updated': datetime.now().isoformat()
        }
        with open(self.registry_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _init_project_dir(self, project_id: str):
        """Initialize project directory structure"""
        project_dir = self.base_dir / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (project_dir / "GENESIS_OUTPUT").mkdir(exist_ok=True)
        
        # Save project config
        config = self.projects[project_id]
        with open(project_dir / "config.json", 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        
        # Initialize empty test_run database
        db_file = project_dir / "test_database.json"
        if not db_file.exists():
            with open(db_file, 'w') as f:
                json.dump({'tests': [], 'cube_matrix': {}}, f, indent=2)
        
        # Initialize hypotheses
        hyp_file = project_dir / "hypotheses.json"
        if not hyp_file.exists():
            with open(hyp_file, 'w') as f:
                json.dump({
                    'hypotheses': [
                        {'id': i, 'text': h, 'prior': 0.5, 'status': 'testing'}
                        for i, h in enumerate(config.hypotheses)
                    ]
                }, f, indent=2)
        
        # SPINE-specific files
        if config.project_type == ProjectType.SPINE_INTERNAL:
            self._init_spine_files(project_dir)
    
    def _init_spine_files(self, project_dir: Path):
        """Initialize SPINE-specific data files"""
        
        # Safety modules checklist
        modules_file = project_dir / "safety_modules.json"
        if not modules_file.exists():
            modules = {
                'modules': BCM_NAVIGATION_MODULES,
                'description': 'Module importance checklist for SPINE safety assessment'
            }
            with open(modules_file, 'w') as f:
                json.dump(modules, f, indent=2)
        
        # EPV assessment template
        epv_file = project_dir / "epv_template.json"
        if not epv_file.exists():
            with open(epv_file, 'w') as f:
                json.dump(EPV_ASSESSMENT_TEMPLATE, f, indent=2)
    
    def get_project_dir(self, project_id: str) -> Path:
        """Get project directory path"""
        if project_id not in self.projects:
            raise ValueError(f"Unknown project: {project_id}")
        return self.base_dir / project_id
    
    def get_test_run_db(self, project_id: str) -> Path:
        """Get test_run database path for project"""
        return self.get_project_dir(project_id) / "test_database.json"
    
    def get_output_dir(self, project_id: str) -> Path:
        """Get output directory for project"""
        return self.get_project_dir(project_id) / "GENESIS_OUTPUT"
    
    def list_projects(self) -> List[Dict]:
        """List all projects with summary"""
        result = []
        for pid, config in self.projects.items():
            # Count test_runs
            db_file = self.get_test_run_db(pid)
            test_count = 0
            if db_file.exists():
                with open(db_file, 'r') as f:
                    data = json.load(f)
                    test_count = len(data.get('tests', []))
            
            result.append({
                'project_id': pid,
                'name': config.project_name,
                'type': config.project_type.value,
                'tests': test_count,
                'target': config.target_tests,
                'progress': f"{test_count}/{config.target_test_runs}"
            })
        return result
    
    def create_project(self, project_id: str, name: str, 
                      project_type: ProjectType, description: str,
                      hypotheses: List[str] = None) -> ProjectConfig:
        """Create a new project"""
        if project_id in self.projects:
            raise ValueError(f"Project already exists: {project_id}")
        
        config = ProjectConfig(
            project_id=project_id,
            project_name=name,
            project_type=project_type,
            description=description,
            created_date=datetime.now().isoformat(),
            hypotheses=hypotheses or []
        )
        
        self.projects[project_id] = config
        self._save_registry()
        self._init_project_dir(project_id)
        
        return config


# =============================================================================
# BCM NAVIGATION TEST SCHEMA
# =============================================================================

BCM_NAVIGATION_MODULES = [
    # AISOS CORE (highest priority)
    {'id': 'MOD_001', 'name': 'Gas Detection & Alarm', 'category': 'ATMOSPHERIC',
     'description': 'H2S, Cl2, SO2 monitoring and alarm response'},
    {'id': 'MOD_002', 'name': 'Personnel Tracking (RTLS)', 'category': 'ACCOUNTABILITY',
     'description': 'Real-time location of all workers in mill'},
    {'id': 'MOD_003', 'name': 'Emergency Muster', 'category': 'ACCOUNTABILITY',
     'description': 'Evacuation accountability and missing person detection'},
    {'id': 'MOD_004', 'name': 'Confined Space Entry', 'category': 'PERMIT',
     'description': 'Entry permits, atmospheric monitoring, rescue readiness'},
    {'id': 'MOD_005', 'name': 'Lockout/Tagout', 'category': 'ENERGY',
     'description': 'Energy isolation verification and audit'},
    
    # EQUIPMENT SAFETY
    {'id': 'MOD_010', 'name': 'Rock/Metal Detection', 'category': 'EQUIPMENT',
     'description': 'Contamination detection before equipment damage'},
    {'id': 'MOD_011', 'name': 'Equipment Health Monitoring', 'category': 'EQUIPMENT',
     'description': 'Vibration, temperature, wear indicators'},
    {'id': 'MOD_012', 'name': 'Blow Line Integrity', 'category': 'EQUIPMENT',
     'description': 'Pressure, flow, rupture detection'},
    
    # AREA-SPECIFIC
    {'id': 'MOD_020', 'name': 'Digester Area Safety', 'category': 'AREA',
     'description': 'High pressure, high temperature, H2S exposure'},
    {'id': 'MOD_021', 'name': 'Bleach Plant Safety', 'category': 'AREA',
     'description': 'Chlorine, ClO2, chemical exposure'},
    {'id': 'MOD_022', 'name': 'Recovery Boiler Safety', 'category': 'AREA',
     'description': 'Smelt-water explosion, high energy'},
    {'id': 'MOD_023', 'name': 'Chip Handling Safety', 'category': 'AREA',
     'description': 'Conveyors, dust, fire, rock damage'},
    {'id': 'MOD_024', 'name': 'Pulp Dryer Safety', 'category': 'AREA',
     'description': 'Fire, dust explosion, entanglement'},
    
    # COMMUNICATION
    {'id': 'MOD_030', 'name': 'Radio/Comm Coverage', 'category': 'COMMUNICATION',
     'description': 'RF coverage in all mill areas'},
    {'id': 'MOD_031', 'name': 'Alarm Audibility', 'category': 'COMMUNICATION',
     'description': 'Can workers hear alarms in their area?'},
    {'id': 'MOD_032', 'name': 'Visual Alert Coverage', 'category': 'COMMUNICATION',
     'description': 'Strobe/light coverage for high-noise areas'},
    
    # PPE & RESPONSE
    {'id': 'MOD_040', 'name': 'SCBA/Respirator Access', 'category': 'PPE',
     'description': 'Proximity and availability of respiratory protection'},
    {'id': 'MOD_041', 'name': 'Fire Extinguisher Access', 'category': 'PPE',
     'description': 'Fire response equipment proximity'},
    {'id': 'MOD_042', 'name': 'First Aid/AED Access', 'category': 'PPE',
     'description': 'Medical response equipment proximity'},
    {'id': 'MOD_043', 'name': 'Emergency Shower/Eyewash', 'category': 'PPE',
     'description': 'Chemical exposure response proximity'},
]


EPV_ASSESSMENT_TEMPLATE = {
    'description': 'EPV (Emotional, Physical, Vocational) Assessment Framework',
    'fields': {
        # IDENTITY
        'employee_id': {'type': 'string', 'description': 'Anonymous ID (not name)'},
        'position': {'type': 'enum', 'options': [
            'Operator', 'Machine Tender', 'Maintenance Tech', 'Electrician',
            'Instrument Tech', 'Supervisor', 'Superintendent', 'Manager',
            'Engineer', 'Contractor', 'Other'
        ]},
        'primary_area': {'type': 'enum', 'options': [
            'Chip Handling', 'Digester', 'Brown Stock', 'Bleach Plant',
            'Pulp Dryer', 'Recovery Boiler', 'Power House', 'Maintenance Shop',
            'Control Room', 'Yard/Woodroom', 'Water Treatment', 'Other'
        ]},
        'years_experience': {'type': 'int', 'description': 'Years at this mill'},
        'years_industry': {'type': 'int', 'description': 'Years in pulp/paper industry'},
        'shift': {'type': 'enum', 'options': ['Day', 'Swing', 'Night', 'Rotating']},
        
        # EMOTIONAL (E) - How they FEEL about safety
        'safety_confidence': {'type': 'scale_1_10', 
            'question': 'How confident are you that you will go home safe every day?'},
        'near_miss_frequency': {'type': 'enum', 'options': [
            'Never', 'Yearly', 'Monthly', 'Weekly', 'Daily'
        ], 'question': 'How often do you experience near-misses?'},
        'voice_heard': {'type': 'scale_1_10',
            'question': 'Do you feel your safety concerns are heard by management?'},
        'trust_systems': {'type': 'scale_1_10',
            'question': 'Do you trust the current safety systems to protect you?'},
        'fear_areas': {'type': 'text',
            'question': 'What area or situation makes you most uncomfortable?'},
        
        # PHYSICAL (P) - What they EXPERIENCE
        'incident_history': {'type': 'text',
            'question': 'Describe any safety incidents you have witnessed or experienced'},
        'equipment_concerns': {'type': 'text',
            'question': 'What equipment do you believe poses the greatest risk?'},
        'detection_gaps': {'type': 'text',
            'question': 'Where do you feel "blind" - no sensors, no visibility?'},
        'response_time': {'type': 'enum', 'options': [
            '<1 min', '1-5 min', '5-15 min', '>15 min', 'Unknown'
        ], 'question': 'If an alarm sounds, how quickly can you reach safety?'},
        
        # VOCATIONAL (V) - What they KNOW from experience
        'training_adequacy': {'type': 'scale_1_10',
            'question': 'How adequate is your safety training for your role?'},
        'procedure_followed': {'type': 'scale_1_10',
            'question': 'How consistently are safety procedures actually followed?'},
        'knowledge_gaps': {'type': 'text',
            'question': 'What safety knowledge do you wish you had?'},
        'improvement_suggestion': {'type': 'text',
            'question': 'If you could change ONE thing to make the mill safer, what would it be?'},
        
        # MODULE RANKING
        'module_rankings': {'type': 'ranking',
            'question': 'Rank the top 5 safety modules by importance to YOUR safety',
            'options': 'BCM_NAVIGATION_MODULES'}
    }
}


@dataclass
class SpineSafetyTest Run:
    """SPINE Safety Test Run record"""
    test_run_id: str
    test_run_date: str
    analyzer: str
    
    # Identity
    employee_id: str
    position: str
    primary_area: str
    years_experience: int
    years_industry: int
    shift: str
    
    # EPV Scores
    safety_confidence: int          # E: 1-10
    near_miss_frequency: str        # E
    voice_heard: int                # E: 1-10
    trust_systems: int              # E: 1-10
    fear_areas: str                 # E: free text
    
    incident_history: str           # P: free text
    equipment_concerns: str         # P: free text
    detection_gaps: str             # P: free text
    response_time: str              # P: enum
    
    training_adequacy: int          # V: 1-10
    procedure_followed: int         # V: 1-10
    knowledge_gaps: str             # V: free text
    improvement_suggestion: str     # V: free text
    
    # Module rankings (top 5 module IDs)
    module_rankings: List[str] = field(default_factory=list)
    
    # Computed
    epv_emotional_score: float = 0.0
    epv_physical_score: float = 0.0
    epv_vocational_score: float = 0.0
    
    def compute_epv_scores(self):
        """Compute EPV dimension scores"""
        # Emotional: average of scales + adjustment for frequency/fear
        e_scales = [self.safety_confidence, self.voice_heard, self.trust_systems]
        self.epv_emotional_score = sum(e_scales) / len(e_scales)
        
        # Adjust for near-miss frequency
        freq_penalty = {
            'Never': 0, 'Yearly': 0.5, 'Monthly': 1.0, 'Weekly': 2.0, 'Daily': 3.0
        }
        self.epv_emotional_score -= freq_penalty.get(self.near_miss_frequency, 0)
        self.epv_emotional_score = max(1, min(10, self.epv_emotional_score))
        
        # Physical: based on response time + detection gaps
        time_score = {
            '<1 min': 10, '1-5 min': 7, '5-15 min': 4, '>15 min': 2, 'Unknown': 1
        }
        self.epv_physical_score = time_score.get(self.response_time, 5)
        
        # Vocational: average of scales
        v_scales = [self.training_adequacy, self.procedure_followed]
        self.epv_vocational_score = sum(v_scales) / len(v_scales)
    
    def to_dict(self) -> Dict:
        self.compute_epv_scores()
        return asdict(self)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Initialize project manager
    pm = ProjectManager(Path("./TEST_PROJECTS"))
    
    print("GIBUSH Project Manager")
    print("=" * 60)
    print("\nProjects:")
    for p in pm.list_projects():
        print(f"  [{p['project_id']}] {p['name']}")
        print(f"      Type: {p['type']}")
        print(f"      Progress: {p['progress']}")
    
    print("\n\nSPINE Safety Modules:")
    print("-" * 60)
    for mod in BCM_NAVIGATION_MODULES[:5]:
        print(f"  {mod['id']}: {mod['name']} ({mod['category']})")
    print(f"  ... and {len(BCM_NAVIGATION_MODULES) - 5} more modules")
    
    print("\n\nEPV Assessment Fields:")
    print("-" * 60)
    for field_name, field_def in list(EPV_ASSESSMENT_TEMPLATE['fields'].items())[:5]:
        print(f"  {field_name}: {field_def.get('question', field_def.get('description', ''))[:50]}...")
