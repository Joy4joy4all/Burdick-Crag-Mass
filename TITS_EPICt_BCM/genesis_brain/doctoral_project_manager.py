# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GIBUSH CORE - UNIFIED PROJECT MANAGER
======================================
Project lifecycle management for the GIBUSH doctoral engine.

New User Flow:
1. CREATE PROJECT → Define what problem you're trying to solve
2. DEFINE HYPOTHESES → What do you believe to be true?
3. PLAN TESTS → What needs to be tested?
4. RUN TESTS → Doctoral engine guides parameters
5. VALIDATE HYPOTHESES → Bayesian engine confirms/denies
6. GET RECOMMENDATIONS → Module registry suggests solutions

Philosophy:
- Safety and the person is SUPREME
- Modules solve VALIDATED problems
- Data drives decisions, not vendors
- EPV Doctrine: Guardian, not surveillance

Emerald Entities LLC — GIBUSH Systems
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import secrets

# Core imports
from .auth_manager import AuthManager, User, UserRole, get_auth_manager
from .bayesian_engine import (
    BayesianHypothesisEngine, 
    Hypothesis, 
    Evidence, 
    EvidenceType,
    get_bayesian_engine
)
from .module_registry import (
    ModuleRegistry, 
    Module, 
    ProblemType, 
    CapabilityType,
    ModuleCategory,
    get_module_registry
)


class ProjectType(Enum):
    """Project classification"""
    SAFETY_INTERNAL = "safety_internal"      # Internal safety assessment
    SAFETY_EXTERNAL = "safety_external"      # External safety validation
    PRODUCTION_ICORPS = "production_icorps"  # BCM customer discovery
    CUSTOM = "custom"                        # User-defined


class ProjectStatus(Enum):
    """Project lifecycle status"""
    DRAFT = "draft"                  # Being configured
    ACTIVE = "active"                # Tests in progress
    ANALYSIS = "analysis"            # Tests complete, analyzing
    VALIDATED = "validated"          # Hypotheses validated
    SOLUTION_DESIGN = "solution_design"  # Selecting modules
    COMPLETE = "complete"            # Project finished
    ARCHIVED = "archived"            # No longer active


@dataclass
class TestPlan:
    """Planned test"""
    plan_id: str
    project_id: str
    test_number: int
    target_role: str              # L1, L2, L3
    target_title: str             # Job title
    target_department: str        # Department/area
    target_name: str = ""         # Actual person (if known)
    hypotheses_to_test: List[str] = field(default_factory=list)
    suggested_questions: List[str] = field(default_factory=list)
    status: str = "planned"       # planned, scheduled, completed, skipped
    scheduled_date: str = ""
    completed_date: str = ""
    test_id: str = ""        # Link to completed test
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'TestPlan':
        return cls(**d)


@dataclass
class CompletedTest:
    """Completed test record"""
    test_id: str
    project_id: str
    plan_id: str
    conducted_by: str             # User ID
    conducted_at: str
    
    # Test source info
    test_source_name: str
    test_source_title: str
    test_source_role: str         # L1, L2, L3
    test_source_department: str
    test_source_tenure_years: float = 0
    
    # Content
    raw_notes: str = ""
    key_insights: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    quotes: List[str] = field(default_factory=list)
    
    # Evidence gathered (links to Bayesian engine)
    evidence_ids: List[str] = field(default_factory=list)
    
    # Equipment/cost mentions
    equipment_mentioned: List[str] = field(default_factory=list)
    cost_data: Dict = field(default_factory=dict)
    
    # Metadata
    duration_minutes: int = 0
    quality_score: float = 0.0    # 0-1, self-assessed
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'CompletedTest':
        return cls(**d)


@dataclass
class Project:
    """
    GIBUSH Project - A problem being solved through doctoral test_runs.
    """
    project_id: str
    team_id: str
    created_by: str               # User ID
    created_at: str
    
    # Identity
    name: str
    description: str
    project_type: ProjectType
    status: ProjectStatus = ProjectStatus.DRAFT
    
    # Test Run planning
    target_tests: int = 100
    test_plans: List[str] = field(default_factory=list)  # Plan IDs
    completed_tests: List[str] = field(default_factory=list)  # Test Run IDs
    
    # Hypotheses (links to Bayesian engine)
    hypothesis_ids: List[str] = field(default_factory=list)
    
    # Problem focus
    target_problems: List[str] = field(default_factory=list)  # ProblemType values
    
    # Results
    validated_problems: List[str] = field(default_factory=list)
    recommended_modules: List[str] = field(default_factory=list)
    
    # Metadata
    updated_at: str = ""
    completed_at: str = ""
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['project_type'] = self.project_type.value
        d['status'] = self.status.value
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Project':
        d['project_type'] = ProjectType(d['project_type'])
        d['status'] = ProjectStatus(d['status'])
        return cls(**d)
    
    @property
    def progress_percent(self) -> float:
        """Test Run completion percentage"""
        if self.target_test_runs == 0:
            return 0
        return len(self.completed_test_runs) / self.target_test_runs * 100


class UnifiedProjectManager:
    """
    Central manager for GIBUSH projects.
    
    Coordinates:
    - Project creation and lifecycle
    - Test Run planning and execution
    - Bayesian hypothesis validation
    - Module solution recommendations
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path.home() / ".gibush"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.projects_dir = self.data_dir / "projects"
        self.projects_dir.mkdir(exist_ok=True)
        
        self.projects_index = self.data_dir / "projects_index.json"
        
        # Connected services
        self.auth = get_auth_manager()
        self.registry = get_module_registry()
        
        # Loaded projects
        self.projects: Dict[str, Project] = {}
        self.test_plans: Dict[str, TestPlan] = {}
        self.tests: Dict[str, CompletedTest] = {}
        
        self._load_index()
    
    def _load_index(self):
        """Load project index"""
        if self.projects_index.exists():
            with open(self.projects_index) as f:
                index = json.load(f)
                for pid in index.get("project_ids", []):
                    self._load_project(pid)
    
    def _save_index(self):
        """Save project index"""
        with open(self.projects_index, 'w') as f:
            json.dump({"project_ids": list(self.projects.keys())}, f, indent=2)
    
    def _load_project(self, project_id: str):
        """Load a project and its data"""
        project_dir = self.projects_dir / project_id
        
        # Load project config
        config_file = project_dir / "project.json"
        if config_file.exists():
            with open(config_file) as f:
                self.projects[project_id] = Project.from_dict(json.load(f))
        
        # Load test_run plans
        plans_file = project_dir / "test_plans.json"
        if plans_file.exists():
            with open(plans_file) as f:
                data = json.load(f)
                for plan_id, plan_data in data.items():
                    self.test_plans[plan_id] = TestPlan.from_dict(plan_data)
        
        # Load completed tests
        tests_file = project_dir / "test_runs.json"
        if tests_file.exists():
            with open(tests_file) as f:
                data = json.load(f)
                for int_id, int_data in data.items():
                    self.tests[int_id] = CompletedTest.from_dict(int_data)
    
    def _save_project(self, project_id: str):
        """Save project and related data"""
        project = self.projects.get(project_id)
        if not project:
            return
        
        project_dir = self.projects_dir / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Save project config
        with open(project_dir / "project.json", 'w') as f:
            json.dump(project.to_dict(), f, indent=2)
        
        # Save test_run plans for this project
        plans = {pid: p.to_dict() for pid, p in self.test_plans.items() 
                 if p.project_id == project_id}
        with open(project_dir / "test_plans.json", 'w') as f:
            json.dump(plans, f, indent=2)
        
        # Save test_runs for this project
        test_runs = {iid: i.to_dict() for iid, i in self.tests.items()
                     if i.project_id == project_id}
        with open(project_dir / "test_runs.json", 'w') as f:
            json.dump(test_runs, f, indent=2)
    
    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID"""
        return f"{prefix}{secrets.token_hex(6)}"
    
    # ========================================================================
    # PROJECT CREATION (New User Entry Point)
    # ========================================================================
    
    def create_project(
        self,
        user: User,
        name: str,
        description: str,
        project_type: ProjectType,
        target_tests: int = 100,
        target_problems: List[ProblemType] = None,
        initial_hypotheses: List[str] = None
    ) -> Tuple[bool, str, Optional[Project]]:
        """
        Create a new GIBUSH project.
        
        This is the entry point for new users.
        
        Args:
            user: The user creating the project
            name: Project name
            description: What problem are we solving?
            project_type: Classification
            target_tests: How many test_runs to conduct
            target_problems: Which problems are we investigating?
            initial_hypotheses: Starting hypotheses to test
        
        Returns: (success, message, project)
        """
        # Permission check
        if not self.auth.can_create_project(user):
            return False, "User does not have permission to create projects", None
        
        # Validate
        if not name or len(name) < 3:
            return False, "Project name must be at least 3 characters", None
        
        if target_test_runs < 5:
            return False, "Minimum 5 test_runs required for statistical significance", None
        
        # Create project
        project_id = self._generate_id("PRJ_")
        
        project = Project(
            project_id=project_id,
            team_id=user.team_id,
            created_by=user.user_id,
            created_at=datetime.now().isoformat(),
            name=name,
            description=description,
            project_type=project_type,
            target_test_runs=target_test_runs,
            target_problems=[p.value for p in (target_problems or [])],
            updated_at=datetime.now().isoformat()
        )
        
        self.projects[project_id] = project
        
        # Create Bayesian engine for this project
        bayesian = get_bayesian_engine(project_id)
        
        # Add initial hypotheses
        if initial_hypotheses:
            for hypothesis_text in initial_hypotheses:
                h = bayesian.create_hypothesis(hypothesis_text)
                project.hypothesis_ids.append(h.hypothesis_id)
        
        # Associate project with team
        team = self.auth.get_team(user.team_id)
        if team:
            team.project_ids.append(project_id)
            self.auth._save_teams()
        
        self._save_project(project_id)
        self._save_index()
        
        return True, f"Project '{name}' created successfully", project
    
    def create_project_from_template(
        self,
        user: User,
        template: str,
        name: str,
        description: str = ""
    ) -> Tuple[bool, str, Optional[Project]]:
        """
        Create project from a standard template.
        
        Templates:
        - SAFETY_INTERNAL: Internal safety assessment (like BCM_NAVIGATION)
        - PRODUCTION_ICORPS: External customer discovery (like BCM_SUBSTRATE)
        """
        templates = {
            "SAFETY_INTERNAL": {
                "project_type": ProjectType.SAFETY_INTERNAL,
                "target_test_runs": 100,
                "target_problems": [
                    ProblemType.DELAYED_GAS_ALERT,
                    ProblemType.UNKNOWN_PERSONNEL_LOCATION,
                    ProblemType.SLOW_MUSTER_ACCOUNTABILITY,
                    ProblemType.MAN_DOWN_UNDETECTED,
                    ProblemType.CONFINED_SPACE_RISK,
                    ProblemType.LOTO_VIOLATION,
                    ProblemType.CONTRACTOR_SAFETY_GAP
                ],
                "hypotheses": [
                    "Workers feel most unsafe in areas with poor gas detection coverage",
                    "Current muster procedures take >10 minutes to achieve 100% accountability",
                    "Contractors are not adequately informed of site-specific hazards",
                    "Man-down events have gone undetected for extended periods",
                    "Emergency communication does not reach all personnel reliably"
                ]
            },
            "PRODUCTION_ICORPS": {
                "project_type": ProjectType.PRODUCTION_ICORPS,
                "target_test_runs": 100,
                "target_problems": [
                    ProblemType.EQUIPMENT_CONTAMINATION_DAMAGE,
                    ProblemType.UNPLANNED_DOWNTIME
                ],
                "hypotheses": [
                    "Rock/metal contamination causes >$300K annual equipment damage per mill",
                    "No effective detection technology exists at truck dump or chip pile",
                    "Mills would pay for detection if ROI proven within 12 months",
                    "OEMs are better sales channel than direct to mills"
                ]
            }
        }
        
        if template not in templates:
            return False, f"Unknown template: {template}. Available: {list(templates.keys())}", None
        
        t = templates[template]
        
        return self.create_project(
            user=user,
            name=name,
            description=description or f"{template} project",
            project_type=t["project_type"],
            target_test_runs=t["target_test_runs"],
            target_problems=t["target_problems"],
            initial_hypotheses=t["hypotheses"]
        )
    
    # ========================================================================
    # TEST PLANNING
    # ========================================================================
    
    def add_test_plan(
        self,
        project_id: str,
        target_role: str,
        target_title: str,
        target_department: str,
        target_name: str = "",
        hypotheses_to_test: List[str] = None
    ) -> Tuple[bool, str, Optional[TestPlan]]:
        """
        Add a test to the project plan.
        """
        project = self.projects.get(project_id)
        if not project:
            return False, "Project not found", None
        
        # Get next test number
        existing_plans = [p for p in self.test_plans.values() if p.project_id == project_id]
        test_number = len(existing_plans) + 1
        
        plan_id = self._generate_id("PLN_")
        
        plan = TestPlan(
            plan_id=plan_id,
            project_id=project_id,
            test_number=test_number,
            target_role=target_role,
            target_title=target_title,
            target_department=target_department,
            target_name=target_name,
            hypotheses_to_test=hypotheses_to_test or []
        )
        
        # Generate suggested questions based on hypotheses
        bayesian = get_bayesian_engine(project_id)
        for hyp_id in hypotheses_to_test or []:
            h = bayesian.hypotheses.get(hyp_id)
            if h:
                plan.suggested_questions.append(
                    f"Regarding: {h.statement[:50]}... - What is your experience with this?"
                )
        
        self.test_plans[plan_id] = plan
        project.test_plans.append(plan_id)
        
        self._save_project(project_id)
        
        return True, "Test Run plan added", plan
    
    def bulk_add_test_plans(
        self,
        project_id: str,
        plans: List[Dict]
    ) -> int:
        """
        Add multiple test_run plans at once.
        
        Each plan dict should have: target_role, target_title, target_department
        """
        added = 0
        for plan_data in plans:
            success, _, _ = self.add_test_plan(
                project_id=project_id,
                target_role=plan_data.get("target_role", "L1"),
                target_title=plan_data.get("target_title", ""),
                target_department=plan_data.get("target_department", ""),
                target_name=plan_data.get("target_name", "")
            )
            if success:
                added += 1
        
        return added
    
    # ========================================================================
    # TEST EXECUTION
    # ========================================================================
    
    def record_test_run(
        self,
        plan_id: str,
        conducted_by: str,
        test_source_name: str,
        test_source_title: str,
        test_source_role: str,
        test_source_department: str,
        raw_notes: str,
        key_insights: List[str] = None,
        pain_points: List[str] = None,
        quotes: List[str] = None,
        equipment_mentioned: List[str] = None,
        cost_data: Dict = None,
        duration_minutes: int = 30
    ) -> Tuple[bool, str, Optional[CompletedTest]]:
        """
        Record a completed test.
        """
        plan = self.test_plans.get(plan_id)
        if not plan:
            return False, "Test Run plan not found", None
        
        project = self.projects.get(plan.project_id)
        if not project:
            return False, "Project not found", None
        
        test_id = self._generate_id("INT_")
        
        test_entry = CompletedTest(
            test_id=test_id,
            project_id=plan.project_id,
            plan_id=plan_id,
            conducted_by=conducted_by,
            conducted_at=datetime.now().isoformat(),
            test_source_name=test_source_name,
            test_source_title=test_source_title,
            test_source_role=test_source_role,
            test_source_department=test_source_department,
            raw_notes=raw_notes,
            key_insights=key_insights or [],
            pain_points=pain_points or [],
            quotes=quotes or [],
            equipment_mentioned=equipment_mentioned or [],
            cost_data=cost_data or {},
            duration_minutes=duration_minutes
        )
        
        self.tests[test_id] = test_run
        
        # Update plan status
        plan.status = "completed"
        plan.completed_date = datetime.now().isoformat()
        plan.test_id = test_id
        
        # Update project
        project.completed_test_runs.append(test_id)
        project.updated_at = datetime.now().isoformat()
        
        # Check if we should advance project status
        if project.status == ProjectStatus.DRAFT:
            project.status = ProjectStatus.ACTIVE
        
        self._save_project(plan.project_id)
        
        return True, "Test Run recorded", test_run
    
    def add_evidence_from_test_run(
        self,
        test_id: str,
        hypothesis_id: str,
        evidence_type: EvidenceType,
        description: str,
        raw_text: str = "",
        quantitative_data: Dict = None
    ) -> Tuple[bool, str]:
        """
        Add evidence from a test to a hypothesis.
        
        This triggers Bayesian update.
        """
        test_entry = self.tests.get(test_id)
        if not test_entry:
            return False, "Test Run not found"
        
        bayesian = get_bayesian_engine(test_run.project_id)
        
        evidence, update_info = bayesian.add_evidence(
            hypothesis_id=hypothesis_id,
            test_id=test_id,
            evidence_type=evidence_type,
            description=description,
            source_role=test_run.test_source_role,
            raw_text=raw_text,
            quantitative_data=quantitative_data
        )
        
        # Link evidence to test_run
        test_run.evidence_ids.append(evidence.evidence_id)
        self._save_project(test_run.project_id)
        
        return True, f"Evidence added. Posterior: {update_info['posterior']:.2%}"
    
    # ========================================================================
    # ANALYSIS & RECOMMENDATIONS
    # ========================================================================
    
    def get_project_status(self, project_id: str) -> Dict:
        """Get comprehensive project status"""
        project = self.projects.get(project_id)
        if not project:
            return {}
        
        bayesian = get_bayesian_engine(project_id)
        
        # Hypothesis status
        hypotheses = []
        for hyp_id in project.hypothesis_ids:
            status = bayesian.get_hypothesis_status(hyp_id)
            if status:
                hypotheses.append(status)
        
        # Test Run progress
        completed = len(project.completed_test_runs)
        planned = len(project.test_plans)
        
        return {
            "project_id": project.project_id,
            "name": project.name,
            "status": project.status.value,
            "progress": {
                "completed_test_runs": completed,
                "planned_test_runs": planned,
                "target_test_runs": project.target_test_runs,
                "percent_complete": project.progress_percent
            },
            "hypotheses": hypotheses,
            "validated_count": len([h for h in hypotheses if h.get("status") == "validated"]),
            "invalidated_count": len([h for h in hypotheses if h.get("status") == "invalidated"]),
            "recommended_actions": bayesian.get_recommended_actions()
        }
    
    def get_solution_recommendations(self, project_id: str) -> Dict:
        """
        Get module recommendations based on validated problems.
        
        This is the OUTPUT of the doctoral engine:
        VALIDATED PROBLEMS → RECOMMENDED MODULES
        """
        project = self.projects.get(project_id)
        if not project:
            return {}
        
        bayesian = get_bayesian_engine(project_id)
        
        # Find validated hypotheses
        validated_problems = []
        for hyp_id in project.hypothesis_ids:
            h = bayesian.hypotheses.get(hyp_id)
            if h and h.status == "validated":
                # Map hypothesis to problem type (simplified)
                for prob_type in ProblemType:
                    if prob_type.value in project.target_problems:
                        validated_problems.append(prob_type)
        
        # Get module recommendations
        recommendation = self.registry.get_solution_recommendation(validated_problems)
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "tests_completed": len(project.completed_test_runs),
            "recommendation": recommendation
        }
    
    # ========================================================================
    # PROJECT LISTING
    # ========================================================================
    
    def list_projects(self, team_id: str = None) -> List[Dict]:
        """List all projects, optionally filtered by team"""
        results = []
        for project in self.projects.values():
            if team_id and project.team_id != team_id:
                continue
            results.append({
                "project_id": project.project_id,
                "name": project.name,
                "status": project.status.value,
                "type": project.project_type.value,
                "progress": project.progress_percent,
                "tests": f"{len(project.completed_test_runs)}/{project.target_test_runs}"
            })
        return results
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        return self.projects.get(project_id)


# ============================================================================
# SINGLETON
# ============================================================================

_manager: Optional[UnifiedProjectManager] = None

def get_project_manager() -> UnifiedProjectManager:
    """Get global project manager instance"""
    global _manager
    if _manager is None:
        _manager = UnifiedProjectManager()
    return _manager


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("UNIFIED PROJECT MANAGER TEST")
    print("=" * 70)
    
    # Setup test environment
    from pathlib import Path
    import shutil
    
    test_dir = Path("./test_gibush")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    # Initialize with test directory
    from auth_manager import AuthManager
    auth = AuthManager(test_dir / "auth")
    
    # Create admin user
    auth.setup_initial_admin("admin", "admin@test.com", "adminpass123")
    admin = auth.get_user_by_username("admin")
    
    # Create team
    _, _, team = auth.create_team("Test Team", "Test Org", admin.user_id)
    
    # Create project manager
    manager = UnifiedProjectManager(test_dir)
    manager.auth = auth
    
    print("\n1. Creating project from template...")
    success, msg, project = manager.create_project_from_template(
        user=admin,
        template="SAFETY_INTERNAL",
        name="Woodland Pulp Safety Assessment",
        description="Internal safety validation for Woodland Pulp LLC"
    )
    print(f"   {msg}")
    print(f"   Project ID: {project.project_id}")
    print(f"   Hypotheses: {len(project.hypothesis_ids)}")
    
    print("\n2. Adding test_run plans...")
    plans = [
        {"target_role": "L1", "target_title": "Digester Operator", "target_department": "Kraft Mill"},
        {"target_role": "L1", "target_title": "BPO Senior", "target_department": "Bleach Plant"},
        {"target_role": "L2", "target_title": "Kraft Mill Superintendent", "target_department": "Operations"},
        {"target_role": "L3", "target_title": "Operations Manager", "target_department": "Management"},
    ]
    added = manager.bulk_add_test_plans(project.project_id, plans)
    print(f"   Added {added} test_run plans")
    
    print("\n3. Recording a test...")
    plan = list(manager.test_plans.values())[0]
    success, msg, test_entry = manager.record_test_run(
        plan_id=plan.plan_id,
        conducted_by=admin.user_id,
        test_source_name="John Smith",
        test_source_title="Digester Operator Senior",
        test_source_role="L1",
        test_source_department="Kraft Mill",
        raw_notes="Gas alarms - we don't always hear them. Last week H2S spiked and I didn't know for 2 minutes.",
        key_insights=["Gas notification delayed", "Radio dead zones exist"],
        pain_points=["Can't hear alarms in noisy areas", "No visual alerts"],
        quotes=["I didn't know there was a leak until someone ran over"],
        duration_minutes=25
    )
    print(f"   {msg}")
    
    print("\n4. Adding evidence from test_run...")
    bayesian = get_bayesian_engine(project.project_id)
    hyp_id = project.hypothesis_ids[0]  # First hypothesis
    
    success, msg = manager.add_evidence_from_test_run(
        test_id=test_run.test_id,
        hypothesis_id=hyp_id,
        evidence_type=EvidenceType.STRONG_SUPPORT,
        description="Operator confirmed 2-minute delay in gas notification",
        raw_text="I didn't know there was a leak until someone ran over"
    )
    print(f"   {msg}")
    
    print("\n5. Project Status:")
    status = manager.get_project_status(project.project_id)
    print(f"   Progress: {status['progress']['percent_complete']:.1f}%")
    print(f"   Hypotheses tracked: {len(status['hypotheses'])}")
    for h in status['hypotheses'][:2]:
        print(f"     - {h['statement'][:50]}... → {h['posterior']:.2%}")
    
    print("\n6. Solution Recommendations:")
    recs = manager.get_solution_recommendations(project.project_id)
    print(f"   Coverage: {recs['recommendation']['coverage_percent']:.1f}%")
    print(f"   Recommended modules:")
    for m in recs['recommendation']['recommended_modules'][:3]:
        print(f"     - {m['name']}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
