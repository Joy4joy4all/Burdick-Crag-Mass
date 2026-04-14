# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN — FEATURE FLAGS
===============================
Per-team feature toggles controlled by foremans.

The Genesis Brain is optional, configurable, and can operate
in advisory-only mode. Teams may use all features, selected
features, or none at all. Foremans may enable or disable
specific capabilities per test_batch.

No component of the tool constrains how Substrate Analysis is taught
or how tests are run.

PRESETS:
  FULL          — All features enabled
  ADVISORY_ONLY — All features on, but tool only suggests (never auto-acts)
  MINIMAL       — Tracking only, no AI generation
  DISABLED      — Control group (all off)
"""

import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FeatureFlags:
    """
    Per-team feature toggles.
    Stored as JSON in team's project folder.
    Foreman Terminal writes. Team interface reads.
    """
    hypothesis_tracking: bool = True      # Bayesian hypothesis updates
    gap_analysis: bool = True             # Q-Cube gap detection
    compound_tests: bool = True       # AI-generated test parameters
    knowledge_extraction: bool = True     # Auto-extract cost/equipment/pain
    strategic_reports: bool = True        # Generate intelligence reports
    advisory_only: bool = False           # If True: tool suggests, never auto-acts

    # ── PRESETS ──

    @classmethod
    def preset_full(cls) -> "FeatureFlags":
        """All features enabled, full automation."""
        return cls()

    @classmethod
    def preset_advisory(cls) -> "FeatureFlags":
        """All features on, but tool only suggests."""
        return cls(advisory_only=True)

    @classmethod
    def preset_minimal(cls) -> "FeatureFlags":
        """Just tracking. No AI generation."""
        return cls(
            compound_tests=False,
            strategic_reports=False,
            advisory_only=True,
        )

    @classmethod
    def preset_disabled(cls) -> "FeatureFlags":
        """Control group. All off."""
        return cls(
            hypothesis_tracking=False,
            gap_analysis=False,
            compound_tests=False,
            knowledge_extraction=False,
            strategic_reports=False,
            advisory_only=True,
        )

    # ── QUERY ──

    def is_enabled(self, feature: str) -> bool:
        """Check if a specific feature is enabled."""
        return getattr(self, feature, False)

    def mode_name(self) -> str:
        """Human-readable mode description."""
        if not self.hypothesis_tracking:
            return "Disabled (Control)"
        if self.advisory_only and not self.compound_tests:
            return "Minimal"
        if self.advisory_only:
            return "Advisory Only"
        return "Full"

    # ── PERSISTENCE ──

    def to_dict(self) -> dict:
        return {
            "hypothesis_tracking": self.hypothesis_tracking,
            "gap_analysis": self.gap_analysis,
            "compound_tests": self.compound_tests,
            "knowledge_extraction": self.knowledge_extraction,
            "strategic_reports": self.strategic_reports,
            "advisory_only": self.advisory_only,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FeatureFlags":
        valid_keys = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in valid_keys})

    def save(self, filepath: str):
        """Save to JSON file in team's project folder."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "FeatureFlags":
        """Load from JSON. Returns FULL preset if file doesn't exist."""
        p = Path(filepath)
        if not p.exists():
            return cls.preset_full()
        with open(p, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# ── PRESET REGISTRY ──

PRESETS = {
    "Full": FeatureFlags.preset_full,
    "Advisory Only": FeatureFlags.preset_advisory,
    "Minimal (Tracking Only)": FeatureFlags.preset_minimal,
    "Disabled (Control Group)": FeatureFlags.preset_disabled,
}


# ── SELF-TEST ──

if __name__ == "__main__":
    print("=" * 50)
    print("FEATURE FLAGS — SELF-TEST")
    print("=" * 50)

    for name, factory in PRESETS.items():
        flags = factory()
        print(f"\n  {name}:")
        print(f"    mode_name() = {flags.mode_name()}")
        print(f"    hypothesis_tracking = {flags.hypothesis_tracking}")
        print(f"    compound_tests  = {flags.compound_tests}")
        print(f"    advisory_only       = {flags.advisory_only}")

    # JSON round-trip
    original = FeatureFlags.preset_advisory()
    original.save("/tmp/test_flags.json")
    loaded = FeatureFlags.load("/tmp/test_flags.json")
    assert loaded.advisory_only == True
    assert loaded.hypothesis_tracking == True
    assert loaded.mode_name() == "Advisory Only"
    print("\n  JSON round-trip: PASS")

    # Missing file = FULL preset
    missing = FeatureFlags.load("/tmp/nonexistent_flags.json")
    assert missing.mode_name() == "Full"
    print("  Missing file fallback: PASS")

    print("\nAll tests passed.")
