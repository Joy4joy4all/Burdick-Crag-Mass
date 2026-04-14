# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GIBUSH CORE - MODULE REGISTRY
==============================
Registry of safety/production modules and the problems they solve.

Philosophy:
- Modules are SOLUTIONS to VALIDATED PROBLEMS
- Safety and the person is SUPREME
- We don't sell modules - we solve problems
- EPV Doctrine: Guardian, not surveillance

Module Selection Flow:
1. Doctoral Engine validates a problem exists
2. Problem maps to capability requirements
3. Registry returns modules that provide those capabilities
4. User/team selects based on their context

Emerald Entities LLC — GIBUSH Systems
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum


class ModuleCategory(Enum):
    """Module classification - Safety is ALWAYS first"""
    SAFETY_LIFE = "safety_life"           # Life safety (highest priority)
    SAFETY_HEALTH = "safety_health"       # Health protection
    SAFETY_AWARENESS = "safety_awareness" # Situational awareness
    PRODUCTION_PROTECTION = "production_protection"  # Equipment/asset protection
    PRODUCTION_OPTIMIZATION = "production_optimization"  # Efficiency
    COMPLIANCE = "compliance"             # Regulatory compliance
    TRAINING = "training"                 # Education and training


class CapabilityType(Enum):
    """What a module CAN DO"""
    # Detection capabilities
    GAS_DETECTION = "gas_detection"
    PARTICULATE_DETECTION = "particulate_detection"
    TEMPERATURE_MONITORING = "temperature_monitoring"
    VIBRATION_MONITORING = "vibration_monitoring"
    ACOUSTIC_DETECTION = "acoustic_detection"
    CONTAMINATION_DETECTION = "contamination_detection"
    
    # Location capabilities
    PERSONNEL_TRACKING = "personnel_tracking"
    ASSET_TRACKING = "asset_tracking"
    ZONE_MONITORING = "zone_monitoring"
    GEOFENCING = "geofencing"
    
    # Communication capabilities
    MASS_NOTIFICATION = "mass_notification"
    TARGETED_ALERT = "targeted_alert"
    TWO_WAY_COMMUNICATION = "two_way_communication"
    PA_INTEGRATION = "pa_integration"
    
    # Safety capabilities
    MAN_DOWN_DETECTION = "man_down_detection"
    CONFINED_SPACE_MONITORING = "confined_space_monitoring"
    LOTO_VERIFICATION = "loto_verification"
    PERMIT_MANAGEMENT = "permit_management"
    MUSTER_ACCOUNTABILITY = "muster_accountability"
    
    # Response capabilities
    EMERGENCY_VECTORING = "emergency_vectoring"
    EVACUATION_ROUTING = "evacuation_routing"
    RESCUE_COORDINATION = "rescue_coordination"
    
    # Analysis capabilities
    TREND_ANALYSIS = "trend_analysis"
    PREDICTIVE_ANALYTICS = "predictive_analytics"
    EXPOSURE_TRACKING = "exposure_tracking"
    COMPLIANCE_REPORTING = "compliance_reporting"


class ProblemType(Enum):
    """Problems that doctoral engine can validate"""
    # Safety problems (SUPREME)
    DELAYED_GAS_ALERT = "delayed_gas_alert"
    UNKNOWN_PERSONNEL_LOCATION = "unknown_personnel_location"
    SLOW_MUSTER_ACCOUNTABILITY = "slow_muster_accountability"
    MAN_DOWN_UNDETECTED = "man_down_undetected"
    CONFINED_SPACE_RISK = "confined_space_risk"
    HEAT_STRESS_EXPOSURE = "heat_stress_exposure"
    CHEMICAL_OVEREXPOSURE = "chemical_overexposure"
    LOTO_VIOLATION = "loto_violation"
    CONTRACTOR_SAFETY_GAP = "contractor_safety_gap"
    EMERGENCY_COMMUNICATION_FAILURE = "emergency_communication_failure"
    VISITOR_SAFETY_GAP = "visitor_safety_gap"
    
    # Production problems
    EQUIPMENT_CONTAMINATION_DAMAGE = "equipment_contamination_damage"
    UNPLANNED_DOWNTIME = "unplanned_downtime"
    QUALITY_DEVIATION = "quality_deviation"
    MAINTENANCE_INEFFICIENCY = "maintenance_inefficiency"


@dataclass
class ModuleCapability:
    """A specific capability a module provides"""
    capability_type: CapabilityType
    strength: float  # 0-1, how well it provides this capability
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "capability_type": self.capability_type.value,
            "strength": self.strength,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'ModuleCapability':
        return cls(
            capability_type=CapabilityType(d["capability_type"]),
            strength=d["strength"],
            notes=d.get("notes", "")
        )


@dataclass
class Module:
    """
    A solution module that can be integrated into SPINE.
    
    Modules are NOT products we sell.
    Modules are SOLUTIONS to VALIDATED PROBLEMS.
    """
    module_id: str
    name: str
    category: ModuleCategory
    description: str
    
    # What it can do
    capabilities: List[ModuleCapability] = field(default_factory=list)
    
    # What problems it solves
    solves_problems: List[ProblemType] = field(default_factory=list)
    
    # Integration info
    integration_complexity: str = "medium"  # low, medium, high
    requires_infrastructure: List[str] = field(default_factory=list)
    
    # EPV compliance
    epv_compliant: bool = True
    epv_notes: str = ""
    
    # Vendor info (for reference, not for sales)
    example_vendors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "module_id": self.module_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "solves_problems": [p.value for p in self.solves_problems],
            "integration_complexity": self.integration_complexity,
            "requires_infrastructure": self.requires_infrastructure,
            "epv_compliant": self.epv_compliant,
            "epv_notes": self.epv_notes,
            "example_vendors": self.example_vendors
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Module':
        return cls(
            module_id=d["module_id"],
            name=d["name"],
            category=ModuleCategory(d["category"]),
            description=d["description"],
            capabilities=[ModuleCapability.from_dict(c) for c in d.get("capabilities", [])],
            solves_problems=[ProblemType(p) for p in d.get("solves_problems", [])],
            integration_complexity=d.get("integration_complexity", "medium"),
            requires_infrastructure=d.get("requires_infrastructure", []),
            epv_compliant=d.get("epv_compliant", True),
            epv_notes=d.get("epv_notes", ""),
            example_vendors=d.get("example_vendors", [])
        )


@dataclass
class ProblemDefinition:
    """
    Definition of a problem that can be validated through tests.
    
    Problems are REAL PAIN experienced by REAL PEOPLE.
    """
    problem_type: ProblemType
    name: str
    description: str
    category: ModuleCategory
    
    # Test Run indicators
    test_run_signals: List[str] = field(default_factory=list)
    validation_questions: List[str] = field(default_factory=list)
    
    # Required capabilities to solve
    required_capabilities: List[CapabilityType] = field(default_factory=list)
    
    # Impact assessment
    safety_impact: str = "medium"  # critical, high, medium, low
    business_impact: str = "medium"
    
    def to_dict(self) -> Dict:
        return {
            "problem_type": self.problem_type.value,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "test_run_signals": self.test_run_signals,
            "validation_questions": self.validation_questions,
            "required_capabilities": [c.value for c in self.required_capabilities],
            "safety_impact": self.safety_impact,
            "business_impact": self.business_impact
        }


class ModuleRegistry:
    """
    Registry of all available modules and problem definitions.
    
    This is the BRAIN that matches:
    VALIDATED PROBLEM → REQUIRED CAPABILITIES → AVAILABLE MODULES
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path.home() / ".gibush" / "registry"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.modules_file = self.data_dir / "modules.json"
        self.problems_file = self.data_dir / "problems.json"
        
        self.modules: Dict[str, Module] = {}
        self.problems: Dict[str, ProblemDefinition] = {}
        
        self._load_data()
        self._ensure_defaults()
    
    def _load_data(self):
        """Load registry data"""
        if self.modules_file.exists():
            with open(self.modules_file) as f:
                data = json.load(f)
                self.modules = {mid: Module.from_dict(m) for mid, m in data.items()}
        
        if self.problems_file.exists():
            with open(self.problems_file) as f:
                data = json.load(f)
                self.problems = {pid: ProblemDefinition(**{
                    **d,
                    "problem_type": ProblemType(d["problem_type"]),
                    "category": ModuleCategory(d["category"]),
                    "required_capabilities": [CapabilityType(c) for c in d.get("required_capabilities", [])]
                }) for pid, d in data.items()}
    
    def _save_data(self):
        """Save registry data"""
        with open(self.modules_file, 'w') as f:
            json.dump({mid: m.to_dict() for mid, m in self.modules.items()}, f, indent=2)
        
        with open(self.problems_file, 'w') as f:
            json.dump({pid: p.to_dict() for pid, p in self.problems.items()}, f, indent=2)
    
    def _ensure_defaults(self):
        """Ensure default modules and problems exist"""
        if not self.modules:
            self._create_default_modules()
        if not self.problems:
            self._create_default_problems()
    
    def _create_default_modules(self):
        """Create default module definitions"""
        
        # ====================================================================
        # SAFETY MODULES (Person is SUPREME)
        # ====================================================================
        
        self.modules["MOD_GAS_DETECTION"] = Module(
            module_id="MOD_GAS_DETECTION",
            name="Gas Detection System",
            category=ModuleCategory.SAFETY_LIFE,
            description="Fixed and portable gas detection for toxic/combustible atmospheres. "
                       "Provides real-time monitoring with SPINE integration for instant alerts.",
            capabilities=[
                ModuleCapability(CapabilityType.GAS_DETECTION, 1.0, "H2S, ClO2, SO2, CO, LEL"),
                ModuleCapability(CapabilityType.TREND_ANALYSIS, 0.7, "Historical exposure data"),
                ModuleCapability(CapabilityType.EXPOSURE_TRACKING, 0.8, "TWA/STEL calculations"),
            ],
            solves_problems=[
                ProblemType.DELAYED_GAS_ALERT,
                ProblemType.CHEMICAL_OVEREXPOSURE,
                ProblemType.CONFINED_SPACE_RISK
            ],
            integration_complexity="medium",
            requires_infrastructure=["4-20mA or Modbus connection", "SPINE backbone"],
            epv_compliant=True,
            epv_notes="Detection only - no productivity tracking",
            example_vendors=["MSA", "Honeywell", "Draeger", "Industrial Scientific"]
        )
        
        self.modules["MOD_RTLS"] = Module(
            module_id="MOD_RTLS",
            name="Real-Time Location System",
            category=ModuleCategory.SAFETY_LIFE,
            description="Personnel and asset tracking for safety applications. "
                       "EPV COMPLIANT: Used for RESCUE, not surveillance.",
            capabilities=[
                ModuleCapability(CapabilityType.PERSONNEL_TRACKING, 1.0, "Sub-meter accuracy"),
                ModuleCapability(CapabilityType.ZONE_MONITORING, 0.9, "Hazard zone awareness"),
                ModuleCapability(CapabilityType.MUSTER_ACCOUNTABILITY, 1.0, "Real-time headcount"),
                ModuleCapability(CapabilityType.MAN_DOWN_DETECTION, 0.8, "Motion/orientation sensing"),
                ModuleCapability(CapabilityType.EMERGENCY_VECTORING, 0.9, "Guide rescue to person"),
            ],
            solves_problems=[
                ProblemType.UNKNOWN_PERSONNEL_LOCATION,
                ProblemType.SLOW_MUSTER_ACCOUNTABILITY,
                ProblemType.MAN_DOWN_UNDETECTED,
                ProblemType.CONFINED_SPACE_RISK,
                ProblemType.VISITOR_SAFETY_GAP
            ],
            integration_complexity="high",
            requires_infrastructure=["UWB anchors or BLE beacons", "Badge infrastructure", "SPINE backbone"],
            epv_compliant=True,
            epv_notes="CRITICAL: Location data used for SAFETY ONLY. "
                     "No productivity tracking. No discipline. Guardian mode.",
            example_vendors=["Zebra", "Sewio", "Ubisense", "Quuppa"]
        )
        
        self.modules["MOD_MASS_NOTIFICATION"] = Module(
            module_id="MOD_MASS_NOTIFICATION",
            name="Mass Notification System",
            category=ModuleCategory.SAFETY_AWARENESS,
            description="Multi-channel emergency communication. "
                       "Reaches everyone on property through multiple paths.",
            capabilities=[
                ModuleCapability(CapabilityType.MASS_NOTIFICATION, 1.0, "All-hands broadcast"),
                ModuleCapability(CapabilityType.TARGETED_ALERT, 0.9, "Zone-specific messaging"),
                ModuleCapability(CapabilityType.PA_INTEGRATION, 0.8, "Existing PA systems"),
                ModuleCapability(CapabilityType.TWO_WAY_COMMUNICATION, 0.6, "Acknowledgment capable"),
            ],
            solves_problems=[
                ProblemType.EMERGENCY_COMMUNICATION_FAILURE,
                ProblemType.DELAYED_GAS_ALERT,
                ProblemType.VISITOR_SAFETY_GAP,
                ProblemType.CONTRACTOR_SAFETY_GAP
            ],
            integration_complexity="medium",
            requires_infrastructure=["IP network", "PA system", "SPINE backbone"],
            epv_compliant=True,
            epv_notes="Emergency use only - no routine surveillance",
            example_vendors=["[Partner TBD]", "Rave", "Everbridge", "Singlewire"]
        )
        
        self.modules["MOD_CONFINED_SPACE"] = Module(
            module_id="MOD_CONFINED_SPACE",
            name="Confined Space Monitoring",
            category=ModuleCategory.SAFETY_LIFE,
            description="Integrated monitoring for confined space entry. "
                       "Combines gas, location, and communication for entrant protection.",
            capabilities=[
                ModuleCapability(CapabilityType.CONFINED_SPACE_MONITORING, 1.0, "Full CSE protocol"),
                ModuleCapability(CapabilityType.GAS_DETECTION, 0.9, "Entry atmosphere"),
                ModuleCapability(CapabilityType.PERSONNEL_TRACKING, 0.8, "Entrant location"),
                ModuleCapability(CapabilityType.TWO_WAY_COMMUNICATION, 0.9, "Attendant-entrant"),
                ModuleCapability(CapabilityType.PERMIT_MANAGEMENT, 0.7, "Digital permits"),
            ],
            solves_problems=[
                ProblemType.CONFINED_SPACE_RISK,
                ProblemType.MAN_DOWN_UNDETECTED,
                ProblemType.CHEMICAL_OVEREXPOSURE
            ],
            integration_complexity="high",
            requires_infrastructure=["Portable monitors", "Communication system", "SPINE backbone"],
            epv_compliant=True,
            epv_notes="Life safety application - full monitoring justified",
            example_vendors=["Industrial Scientific", "MSA", "Blackline Safety"]
        )
        
        self.modules["MOD_LOTO"] = Module(
            module_id="MOD_LOTO",
            name="LOTO Verification System",
            category=ModuleCategory.SAFETY_LIFE,
            description="Electronic lockout/tagout verification and tracking. "
                       "Ensures energy isolation before work begins.",
            capabilities=[
                ModuleCapability(CapabilityType.LOTO_VERIFICATION, 1.0, "Electronic verification"),
                ModuleCapability(CapabilityType.PERMIT_MANAGEMENT, 0.9, "Work permits"),
                ModuleCapability(CapabilityType.COMPLIANCE_REPORTING, 0.8, "OSHA audit trail"),
                ModuleCapability(CapabilityType.ZONE_MONITORING, 0.6, "Work area awareness"),
            ],
            solves_problems=[
                ProblemType.LOTO_VIOLATION,
                ProblemType.CONTRACTOR_SAFETY_GAP,
                ProblemType.MAINTENANCE_INEFFICIENCY
            ],
            integration_complexity="medium",
            requires_infrastructure=["Smart locks or verification points", "SPINE backbone"],
            epv_compliant=True,
            epv_notes="Safety compliance system",
            example_vendors=["Brady", "Master Lock", "Sofis", "LOTO-aware"]
        )
        
        self.modules["MOD_HEAT_STRESS"] = Module(
            module_id="MOD_HEAT_STRESS",
            name="Heat Stress Monitoring",
            category=ModuleCategory.SAFETY_HEALTH,
            description="Physiological monitoring for heat exposure. "
                       "Protects workers in high-temperature environments.",
            capabilities=[
                ModuleCapability(CapabilityType.TEMPERATURE_MONITORING, 1.0, "Core body temp estimation"),
                ModuleCapability(CapabilityType.EXPOSURE_TRACKING, 0.9, "Cumulative heat dose"),
                ModuleCapability(CapabilityType.TARGETED_ALERT, 0.8, "Individual warnings"),
                ModuleCapability(CapabilityType.TREND_ANALYSIS, 0.7, "Acclimatization tracking"),
            ],
            solves_problems=[
                ProblemType.HEAT_STRESS_EXPOSURE
            ],
            integration_complexity="medium",
            requires_infrastructure=["Wearable sensors", "SPINE backbone"],
            epv_compliant=True,
            epv_notes="Health protection - voluntary monitoring recommended",
            example_vendors=["Kenzen", "SlateSafety", "Bodytrak"]
        )
        
        # ====================================================================
        # PRODUCTION MODULES (Safety still comes first)
        # ====================================================================
        
        self.modules["MOD_CONTAMINATION_DETECTION"] = Module(
            module_id="MOD_CONTAMINATION_DETECTION",
            name="Contamination Detection System",
            category=ModuleCategory.PRODUCTION_PROTECTION,
            description="Acoustic/sensor detection of rock and metal contamination. "
                       "USPTO Serial #99346684 - 3D triangulation technology.",
            capabilities=[
                ModuleCapability(CapabilityType.CONTAMINATION_DETECTION, 1.0, "Rock/metal in chip flow"),
                ModuleCapability(CapabilityType.ACOUSTIC_DETECTION, 1.0, "3D acoustic triangulation"),
                ModuleCapability(CapabilityType.PREDICTIVE_ANALYTICS, 0.7, "Damage prevention"),
                ModuleCapability(CapabilityType.TREND_ANALYSIS, 0.8, "Contamination patterns"),
            ],
            solves_problems=[
                ProblemType.EQUIPMENT_CONTAMINATION_DAMAGE,
                ProblemType.UNPLANNED_DOWNTIME,
                ProblemType.QUALITY_DEVIATION
            ],
            integration_complexity="medium",
            requires_infrastructure=["Sensor array", "SPINE backbone"],
            epv_compliant=True,
            epv_notes="Equipment protection - no personnel tracking",
            example_vendors=["Emerald Entities (patented)"]
        )
        
        self.modules["MOD_VIBRATION"] = Module(
            module_id="MOD_VIBRATION",
            name="Vibration Monitoring System",
            category=ModuleCategory.PRODUCTION_PROTECTION,
            description="Continuous vibration analysis for rotating equipment. "
                       "Predicts failures before catastrophic damage.",
            capabilities=[
                ModuleCapability(CapabilityType.VIBRATION_MONITORING, 1.0, "FFT analysis"),
                ModuleCapability(CapabilityType.PREDICTIVE_ANALYTICS, 0.9, "Failure prediction"),
                ModuleCapability(CapabilityType.TREND_ANALYSIS, 0.9, "Degradation tracking"),
            ],
            solves_problems=[
                ProblemType.UNPLANNED_DOWNTIME,
                ProblemType.MAINTENANCE_INEFFICIENCY
            ],
            integration_complexity="medium",
            requires_infrastructure=["Vibration sensors", "SPINE backbone"],
            epv_compliant=True,
            epv_notes="Equipment only - no personnel implications",
            example_vendors=["SKF", "Emerson", "Honeywell", "ABB"]
        )
        
        self._save_data()
    
    def _create_default_problems(self):
        """Create default problem definitions"""
        
        # ====================================================================
        # SAFETY PROBLEMS (Person is SUPREME)
        # ====================================================================
        
        self.problems["PROB_DELAYED_GAS"] = ProblemDefinition(
            problem_type=ProblemType.DELAYED_GAS_ALERT,
            name="Delayed Gas Alert Response",
            description="Time between gas detection and personnel notification exceeds safe limits. "
                       "Workers may be exposed before knowing hazard exists.",
            category=ModuleCategory.SAFETY_LIFE,
            test_run_signals=[
                "gas alarm went off but nobody knew",
                "didn't hear the alarm",
                "found out later there was a leak",
                "radio didn't work",
                "control room didn't call"
            ],
            validation_questions=[
                "What happens when a gas alarm triggers? Walk me through the notification process.",
                "How long does it typically take from alarm to everyone knowing?",
                "Tell me about a time when gas notification didn't work as expected.",
                "How do you find out about gas alarms in your area?"
            ],
            required_capabilities=[
                CapabilityType.GAS_DETECTION,
                CapabilityType.MASS_NOTIFICATION,
                CapabilityType.TARGETED_ALERT
            ],
            safety_impact="critical",
            business_impact="high"
        )
        
        self.problems["PROB_UNKNOWN_LOCATION"] = ProblemDefinition(
            problem_type=ProblemType.UNKNOWN_PERSONNEL_LOCATION,
            name="Unknown Personnel Location",
            description="Cannot determine where workers are located during emergency. "
                       "Rescue teams don't know where to search.",
            category=ModuleCategory.SAFETY_LIFE,
            test_run_signals=[
                "didn't know where he was",
                "searched everywhere",
                "couldn't find",
                "nobody knew which area",
                "radio silence"
            ],
            validation_questions=[
                "During an emergency, how do you know where everyone is?",
                "Tell me about a time you couldn't locate someone who should have been on site.",
                "How do you track contractors and visitors?",
                "What would help you find someone faster in an emergency?"
            ],
            required_capabilities=[
                CapabilityType.PERSONNEL_TRACKING,
                CapabilityType.ZONE_MONITORING,
                CapabilityType.EMERGENCY_VECTORING
            ],
            safety_impact="critical",
            business_impact="medium"
        )
        
        self.problems["PROB_SLOW_MUSTER"] = ProblemDefinition(
            problem_type=ProblemType.SLOW_MUSTER_ACCOUNTABILITY,
            name="Slow Muster Accountability",
            description="Emergency muster takes too long to achieve 100% headcount. "
                       "Cannot confirm all personnel safe in reasonable time.",
            category=ModuleCategory.SAFETY_LIFE,
            test_run_signals=[
                "took forever to count everyone",
                "paper lists",
                "people missing from list",
                "didn't know who was on site",
                "contractors not on roster"
            ],
            validation_questions=[
                "Walk me through your muster process. How long does it take?",
                "How do you account for contractors and visitors during muster?",
                "What happens when someone doesn't show up at the muster point?",
                "What's the longest a muster has ever taken?"
            ],
            required_capabilities=[
                CapabilityType.MUSTER_ACCOUNTABILITY,
                CapabilityType.PERSONNEL_TRACKING,
                CapabilityType.MASS_NOTIFICATION
            ],
            safety_impact="critical",
            business_impact="medium"
        )
        
        self.problems["PROB_MAN_DOWN"] = ProblemDefinition(
            problem_type=ProblemType.MAN_DOWN_UNDETECTED,
            name="Man Down Undetected",
            description="Worker incapacitated but not discovered for extended period. "
                       "Lone workers at highest risk.",
            category=ModuleCategory.SAFETY_LIFE,
            test_run_signals=[
                "found him hours later",
                "nobody knew he was down",
                "working alone",
                "didn't check in",
                "no way to know"
            ],
            validation_questions=[
                "How do you monitor lone workers?",
                "Tell me about any incidents where someone was injured and not found quickly.",
                "What's your check-in procedure for isolated areas?",
                "What would you want if you were working alone and got hurt?"
            ],
            required_capabilities=[
                CapabilityType.MAN_DOWN_DETECTION,
                CapabilityType.PERSONNEL_TRACKING,
                CapabilityType.TARGETED_ALERT
            ],
            safety_impact="critical",
            business_impact="low"
        )
        
        self._save_data()
    
    # ========================================================================
    # SOLUTION MATCHING
    # ========================================================================
    
    def get_modules_for_problem(self, problem_type: ProblemType) -> List[Module]:
        """
        Find modules that solve a validated problem.
        
        This is the core matching function:
        VALIDATED PROBLEM → MODULES THAT SOLVE IT
        """
        matching_modules = []
        
        for module in self.modules.values():
            if problem_type in module.solves_problems:
                matching_modules.append(module)
        
        # Sort by category (safety first) then by capability match
        def sort_key(m: Module):
            category_order = {
                ModuleCategory.SAFETY_LIFE: 0,
                ModuleCategory.SAFETY_HEALTH: 1,
                ModuleCategory.SAFETY_AWARENESS: 2,
                ModuleCategory.PRODUCTION_PROTECTION: 3,
                ModuleCategory.PRODUCTION_OPTIMIZATION: 4,
                ModuleCategory.COMPLIANCE: 5,
                ModuleCategory.TRAINING: 6
            }
            return category_order.get(m.category, 99)
        
        return sorted(matching_modules, key=sort_key)
    
    def get_modules_with_capability(self, capability: CapabilityType) -> List[Module]:
        """Find all modules that provide a specific capability"""
        matching = []
        for module in self.modules.values():
            for cap in module.capabilities:
                if cap.capability_type == capability:
                    matching.append((module, cap.strength))
                    break
        
        # Sort by capability strength
        return [m for m, _ in sorted(matching, key=lambda x: x[1], reverse=True)]
    
    def get_solution_recommendation(
        self, 
        validated_problems: List[ProblemType]
    ) -> Dict[str, any]:
        """
        Generate solution recommendation based on validated problems.
        
        Input: List of problems validated through doctoral test_runs
        Output: Recommended modules with rationale
        """
        # Collect all required capabilities
        required_capabilities: Set[CapabilityType] = set()
        problem_details = []
        
        for problem_type in validated_problems:
            for prob_def in self.problems.values():
                if prob_def.problem_type == problem_type:
                    required_capabilities.update(prob_def.required_capabilities)
                    problem_details.append({
                        "problem": prob_def.name,
                        "safety_impact": prob_def.safety_impact,
                        "required_capabilities": [c.value for c in prob_def.required_capabilities]
                    })
        
        # Find modules that cover these capabilities
        recommended_modules = []
        covered_capabilities = set()
        
        for module in self.modules.values():
            module_caps = {c.capability_type for c in module.capabilities}
            overlap = module_caps & required_capabilities
            
            if overlap:
                recommended_modules.append({
                    "module_id": module.module_id,
                    "name": module.name,
                    "category": module.category.value,
                    "covers_capabilities": [c.value for c in overlap],
                    "integration_complexity": module.integration_complexity,
                    "epv_compliant": module.epv_compliant
                })
                covered_capabilities.update(overlap)
        
        # Check for gaps
        gaps = required_capabilities - covered_capabilities
        
        return {
            "validated_problems": problem_details,
            "required_capabilities": [c.value for c in required_capabilities],
            "recommended_modules": recommended_modules,
            "capability_gaps": [c.value for c in gaps],
            "coverage_percent": len(covered_capabilities) / len(required_capabilities) * 100 if required_capabilities else 0
        }
    
    # ========================================================================
    # MODULE MANAGEMENT
    # ========================================================================
    
    def register_module(self, module: Module) -> bool:
        """Register a new module in the registry"""
        if module.module_id in self.modules:
            return False
        
        self.modules[module.module_id] = module
        self._save_data()
        return True
    
    def get_module(self, module_id: str) -> Optional[Module]:
        """Get module by ID"""
        return self.modules.get(module_id)
    
    def list_modules_by_category(self, category: ModuleCategory) -> List[Module]:
        """List all modules in a category"""
        return [m for m in self.modules.values() if m.category == category]
    
    def get_epv_compliant_modules(self) -> List[Module]:
        """Get all EPV-compliant modules (Guardian, not surveillance)"""
        return [m for m in self.modules.values() if m.epv_compliant]


# ============================================================================
# SINGLETON
# ============================================================================

_registry: Optional[ModuleRegistry] = None

def get_module_registry() -> ModuleRegistry:
    """Get global module registry instance"""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MODULE REGISTRY TEST")
    print("=" * 70)
    
    registry = ModuleRegistry(Path("./test_registry"))
    
    print(f"\nRegistered Modules: {len(registry.modules)}")
    for mod in registry.modules.values():
        print(f"  [{mod.category.value}] {mod.name}")
        print(f"    Solves: {[p.value for p in mod.solves_problems]}")
    
    print(f"\nDefined Problems: {len(registry.problems)}")
    
    # Test solution matching
    print("\n" + "=" * 70)
    print("SOLUTION RECOMMENDATION TEST")
    print("=" * 70)
    
    # Simulating validated problems from doctoral test_runs
    validated = [
        ProblemType.DELAYED_GAS_ALERT,
        ProblemType.UNKNOWN_PERSONNEL_LOCATION,
        ProblemType.SLOW_MUSTER_ACCOUNTABILITY
    ]
    
    recommendation = registry.get_solution_recommendation(validated)
    
    print(f"\nValidated Problems:")
    for p in recommendation["validated_problems"]:
        print(f"  - {p['problem']} (safety: {p['safety_impact']})")
    
    print(f"\nRequired Capabilities: {recommendation['required_capabilities']}")
    
    print(f"\nRecommended Modules:")
    for m in recommendation["recommended_modules"]:
        print(f"  - {m['name']} [{m['category']}]")
        print(f"    Covers: {m['covers_capabilities']}")
    
    print(f"\nCoverage: {recommendation['coverage_percent']:.1f}%")
    if recommendation["capability_gaps"]:
        print(f"Gaps: {recommendation['capability_gaps']}")
