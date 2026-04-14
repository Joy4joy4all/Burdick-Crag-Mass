# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Q-CUBE CONFIGURABLE AXIS ENGINE
=================================
The Q-Cube maps tests across three configurable axes.
Axes are defined in JSON config — NOT hardcoded.

Each BCM team defines their own axes during onboarding.
The gap analysis algorithm is axis-agnostic.

DEFAULT CONFIGS PROVIDED:
  - heavy_industry (GIBUSH default)
  - biotech (example)
  - saas (example)
  - custom (team-defined)
"""

import json
import os
import math
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field
from collections import Counter


# ============================================================================
# AXIS DEFINITION
# ============================================================================

@dataclass
class QCubeAxis:
    """One axis of the Q-Cube."""
    name: str                  # e.g., "Role Level"
    key: str                   # e.g., "role_level"  (used in code)
    values: List[str]          # e.g., ["L1", "L2", "L3", "L4", "L5"]
    labels: Dict[str, str]     # e.g., {"L1": "Operator", "L2": "Supervisor", ...}
    description: str = ""      # For UI tooltips


@dataclass
class QCubeConfig:
    """Full Q-Cube configuration — three axes."""
    name: str                  # e.g., "Heavy Industry"
    description: str
    axis_1: QCubeAxis
    axis_2: QCubeAxis
    axis_3: QCubeAxis

    @property
    def total_positions(self) -> int:
        return len(self.axis_1.values) * len(self.axis_2.values) * len(self.axis_3.values)

    def all_positions(self) -> List[Tuple[str, str, str]]:
        """Generate every possible position in the cube."""
        positions = []
        for a1 in self.axis_1.values:
            for a2 in self.axis_2.values:
                for a3 in self.axis_3.values:
                    positions.append((a1, a2, a3))
        return positions

    def position_label(self, pos: Tuple[str, str, str]) -> str:
        """Human-readable label for a position."""
        a1_label = self.axis_1.labels.get(pos[0], pos[0])
        a2_label = self.axis_2.labels.get(pos[1], pos[1])
        a3_label = self.axis_3.labels.get(pos[2], pos[2])
        return f"[{a1_label}, {a2_label}, {a3_label}]"

    def position_key(self, pos: Tuple[str, str, str]) -> str:
        """Short key for a position: [L2, OC, Sa]"""
        return f"[{pos[0]}, {pos[1]}, {pos[2]}]"

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict."""
        def axis_dict(ax: QCubeAxis) -> dict:
            return {
                "name": ax.name,
                "key": ax.key,
                "values": ax.values,
                "labels": ax.labels,
                "description": ax.description,
            }
        return {
            "name": self.name,
            "description": self.description,
            "axis_1": axis_dict(self.axis_1),
            "axis_2": axis_dict(self.axis_2),
            "axis_3": axis_dict(self.axis_3),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QCubeConfig":
        """Load from JSON dict."""
        def make_axis(ad: dict) -> QCubeAxis:
            return QCubeAxis(
                name=ad["name"],
                key=ad["key"],
                values=ad["values"],
                labels=ad.get("labels", {}),
                description=ad.get("description", ""),
            )
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            axis_1=make_axis(d["axis_1"]),
            axis_2=make_axis(d["axis_2"]),
            axis_3=make_axis(d["axis_3"]),
        )


# ============================================================================
# DEFAULT CONFIGURATIONS
# ============================================================================

def heavy_industry_config() -> QCubeConfig:
    """GIBUSH default: kraft mill contamination detection."""
    return QCubeConfig(
        name="Heavy Industry",
        description="Kraft mill and heavy industrial customer discovery",
        axis_1=QCubeAxis(
            name="Role Level",
            key="role_level",
            values=["L1", "L2", "L3", "L4", "L5"],
            labels={
                "L1": "Operator",
                "L2": "Supervisor/Foreman",
                "L3": "Manager/Engineer",
                "L4": "Director/VP",
                "L5": "Executive/C-Suite",
            },
            description="Organizational role level of test_source",
        ),
        axis_2=QCubeAxis(
            name="Company Type",
            key="company_type",
            values=["OEM", "OC", "CS", "AC", "RG"],
            labels={
                "OEM": "Reverse Engine",
                "OC": "Galactic Solver/Owner",
                "CS": "Neutrino Flux/Integrator",
                "AC": "Academic/Research",
                "RG": "Regulator/Standards",
            },
            description="Type of organization test_source works for",
        ),
        axis_3=QCubeAxis(
            name="Segment Stack",
            key="segment_stack",
            values=["Sa", "Sb", "Sg", "Sd"],
            labels={
                "Sa": "Alpha (Chip Handling)",
                "Sb": "Beta (Recovery/Chemical)",
                "Sg": "Gamma (Downstream)",
                "Sd": "Delta (Multi-Product)",
            },
            description="Market segment / process area",
        ),
    )


def biotech_config() -> QCubeConfig:
    """Example config for biotech BCM team."""
    return QCubeConfig(
        name="Biotech / Pharma",
        description="Drug development and life sciences customer discovery",
        axis_1=QCubeAxis(
            name="Stakeholder Role",
            key="stakeholder_role",
            values=["CL", "RS", "RG", "PA", "PY"],
            labels={
                "CL": "Clinician",
                "RS": "Researcher/Scientist",
                "RG": "Regulator (FDA/EMA)",
                "PA": "Patient Advocate",
                "PY": "Payer/Insurance",
            },
            description="Stakeholder type in drug development lifecycle",
        ),
        axis_2=QCubeAxis(
            name="Organization Type",
            key="org_type",
            values=["PH", "BT", "CRO", "HO", "AG"],
            labels={
                "PH": "Big Pharma",
                "BT": "Biotech Startup",
                "CRO": "Contract Research Org",
                "HO": "Hospital/Health System",
                "AG": "Gov Agency / Regulator",
            },
            description="Type of organization",
        ),
        axis_3=QCubeAxis(
            name="Development Stage",
            key="dev_stage",
            values=["PC", "P1", "P2", "P3", "PM"],
            labels={
                "PC": "Preclinical",
                "P1": "Phase I",
                "P2": "Phase II",
                "P3": "Phase III",
                "PM": "Post-Market",
            },
            description="Stage in drug development pipeline",
        ),
    )


def saas_config() -> QCubeConfig:
    """Example config for SaaS / software BCM team."""
    return QCubeConfig(
        name="SaaS / Software",
        description="Software product customer discovery",
        axis_1=QCubeAxis(
            name="Buyer Role",
            key="buyer_role",
            values=["EU", "CH", "BO", "IT", "EX"],
            labels={
                "EU": "End User",
                "CH": "Champion/Advocate",
                "BO": "Budget Owner",
                "IT": "IT/Security",
                "EX": "Executive Sponsor",
            },
            description="Role in buying decision",
        ),
        axis_2=QCubeAxis(
            name="Company Size",
            key="company_size",
            values=["ST", "SM", "MM", "EN"],
            labels={
                "ST": "Startup (<50)",
                "SM": "SMB (50-500)",
                "MM": "Mid-Market (500-5K)",
                "EN": "Enterprise (5K+)",
            },
            description="Company size by employee count",
        ),
        axis_3=QCubeAxis(
            name="Vertical",
            key="vertical",
            values=["FT", "HT", "ET", "DT", "MF"],
            labels={
                "FT": "FinTech",
                "HT": "HealthTech",
                "ET": "EdTech",
                "DT": "DevTools",
                "MF": "Manufacturing",
            },
            description="Industry vertical",
        ),
    )


BUILTIN_CONFIGS = {
    "heavy_industry": heavy_industry_config,
    "biotech": biotech_config,
    "saas": saas_config,
}


# ============================================================================
# Q-CUBE GAP ANALYSIS ENGINE (AXIS-AGNOSTIC)
# ============================================================================

@dataclass
class QCubeGap:
    """A gap in test_run coverage."""
    position: Tuple[str, str, str]
    position_key: str
    position_label: str
    priority: float              # 0.0 - 1.0
    information_gain: float      # estimated info gain
    reason: str


class QCubeEngine:
    """
    Axis-agnostic gap analysis.
    Works with ANY QCubeConfig — heavy industry, biotech, SaaS, custom.
    """

    def __init__(self, config: QCubeConfig):
        self.config = config
        self.filled_positions: Dict[str, List[int]] = {}  # pos_key -> [test_nums]

    def register_test_run(self, test_num: int,
                           axis_1_val: str, axis_2_val: str, axis_3_val: str):
        """Register a test at a position."""
        pos_key = f"[{axis_1_val}, {axis_2_val}, {axis_3_val}]"
        if pos_key not in self.filled_positions:
            self.filled_positions[pos_key] = []
        self.filled_positions[pos_key].append(test_num)

    def coverage_percentage(self) -> float:
        """What percentage of the cube is covered by at least one test_run."""
        total = self.config.total_positions
        if total == 0:
            return 0.0
        filled = len(self.filled_positions)
        return (filled / total) * 100.0

    def coverage_map(self) -> Dict[str, dict]:
        """Full map of every position: filled or empty."""
        result = {}
        for pos in self.config.all_positions():
            key = self.config.position_key(pos)
            label = self.config.position_label(pos)
            tests = self.filled_positions.get(key, [])
            result[key] = {
                "position": pos,
                "key": key,
                "label": label,
                "filled": len(test_runs) > 0,
                "test_count": len(test_runs),
                "tests": tests,
            }
        return result

    def find_gaps(self, validated_positions: Optional[Set[str]] = None,
                  contradicted_positions: Optional[Set[str]] = None) -> List[QCubeGap]:
        """
        Find empty positions ranked by estimated information gain.

        Proximity to validated and contradicted positions increases priority.
        This is axis-agnostic — works regardless of what axes represent.
        """
        validated_positions = validated_positions or set()
        contradicted_positions = contradicted_positions or set()
        all_positions = self.config.all_positions()
        gaps = []

        for pos in all_positions:
            key = self.config.position_key(pos)
            if key in self.filled_positions:
                continue  # Already covered

            # Calculate information gain based on adjacency
            # Positions that share 2 of 3 axis values with filled positions
            # are higher priority (boundary expansion)
            adjacency_score = self._adjacency_score(pos)

            # Proximity to validated = moderate priority (confirm breadth)
            # Proximity to contradicted = HIGH priority (find boundaries)
            validation_proximity = self._proximity_to_set(pos, validated_positions)
            contradiction_proximity = self._proximity_to_set(pos, contradicted_positions)

            info_gain = (
                0.3 * adjacency_score +
                0.3 * validation_proximity +
                0.4 * contradiction_proximity  # Contradictions are most informative
            )

            # Priority: how urgently this gap should be filled
            priority = min(1.0, info_gain)

            reason_parts = []
            if adjacency_score > 0.5:
                reason_parts.append("adjacent to covered positions")
            if contradiction_proximity > 0.5:
                reason_parts.append("near contradicted evidence")
            if validation_proximity > 0.5:
                reason_parts.append("extends validated coverage")
            if not reason_parts:
                reason_parts.append("unexplored region")

            gaps.append(QCubeGap(
                position=pos,
                position_key=key,
                position_label=self.config.position_label(pos),
                priority=priority,
                information_gain=info_gain,
                reason="; ".join(reason_parts),
            ))

        # Sort by priority descending
        gaps.sort(key=lambda g: g.priority, reverse=True)
        return gaps

    def _adjacency_score(self, pos: Tuple[str, str, str]) -> float:
        """How many filled positions share 2 of 3 axes with this position."""
        adjacent_count = 0
        for filled_key in self.filled_positions:
            # Parse filled key back to tuple
            filled_vals = filled_key.strip("[]").split(", ")
            if len(filled_vals) != 3:
                continue
            matches = sum(1 for a, b in zip(pos, filled_vals) if a == b)
            if matches >= 2:
                adjacent_count += 1

        # Normalize: more adjacency = higher score, diminishing returns
        if adjacent_count == 0:
            return 0.0
        return min(1.0, adjacent_count / 3.0)

    def _proximity_to_set(self, pos: Tuple[str, str, str],
                          position_set: Set[str]) -> float:
        """How close is this position to a set of known positions."""
        if not position_set:
            return 0.0
        best_match = 0
        for ref_key in position_set:
            ref_vals = ref_key.strip("[]").split(", ")
            if len(ref_vals) != 3:
                continue
            matches = sum(1 for a, b in zip(pos, ref_vals) if a == b)
            best_match = max(best_match, matches)
        return best_match / 3.0

    def to_dict(self) -> dict:
        """Serialize state for persistence."""
        return {
            "config": self.config.to_dict(),
            "filled_positions": self.filled_positions,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QCubeEngine":
        """Load from persisted state."""
        config = QCubeConfig.from_dict(d["config"])
        engine = cls(config)
        engine.filled_positions = d.get("filled_positions", {})
        return engine


# ============================================================================
# CONFIG FILE I/O
# ============================================================================

def save_qcube_config(config: QCubeConfig, filepath: str):
    """Save Q-Cube config to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)


def load_qcube_config(filepath: str) -> QCubeConfig:
    """Load Q-Cube config from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return QCubeConfig.from_dict(json.load(f))


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Q-CUBE CONFIG ENGINE — SELF-TEST")
    print("=" * 60)

    for name, factory in BUILTIN_CONFIGS.items():
        config = factory()
        engine = QCubeEngine(config)
        print(f"\n--- {config.name} ---")
        print(f"  Axis 1: {config.axis_1.name} ({len(config.axis_1.values)} values)")
        print(f"  Axis 2: {config.axis_2.name} ({len(config.axis_2.values)} values)")
        print(f"  Axis 3: {config.axis_3.name} ({len(config.axis_3.values)} values)")
        print(f"  Total positions: {config.total_positions}")
        print(f"  Coverage: {engine.coverage_percentage():.1f}%")

    # Simulate tests on heavy industry
    print("\n--- HEAVY INDUSTRY GAP ANALYSIS ---")
    config = heavy_industry_config()
    engine = QCubeEngine(config)
    engine.register_test_run(1, "L1", "OC", "Sa")
    engine.register_test_run(2, "L2", "OC", "Sa")
    engine.register_test_run(3, "L3", "OEM", "Sa")
    engine.register_test_run(4, "L2", "CS", "Sb")
    print(f"  Registered 4 test_runs")
    print(f"  Coverage: {engine.coverage_percentage():.1f}%")

    gaps = engine.find_gaps(
        validated_positions={"[L1, OC, Sa]", "[L2, OC, Sa]"},
        contradicted_positions=set(),
    )
    print(f"  Top 5 gaps:")
    for gap in gaps[:5]:
        print(f"    {gap.position_key} ({gap.position_label}) "
              f"priority={gap.priority:.2f} — {gap.reason}")

    # JSON round-trip
    serialized = engine.to_dict()
    restored = QCubeEngine.from_dict(serialized)
    assert restored.coverage_percentage() == engine.coverage_percentage()
    print("\n  JSON round-trip: PASS")
    print("\nAll tests passed.")
