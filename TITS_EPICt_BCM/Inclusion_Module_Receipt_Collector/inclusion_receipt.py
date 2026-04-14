#!/usr/bin/env python3
"""
INCLUSION MODULE RECEIPT COLLECTOR
================================================================
Location: TITS_GIBUSH_AISOS_SPINE_ICORPS/Inclusion_Module_Receipt_Collector/

TRIAD POSITION: Stream 2 Receiver — catches Inclusion entries from CaaS,
converts them to interview-format records, feeds them into the Fusion
Interview Collector's All Interviews display.

MASTER LENS CLASSIFICATION:
  ML1 — Entrepreneurial Lead (EL)   → Business/market observations
  ML2 — Technical Lead (TL)         → Equipment/sensor/process observations
  ML3 — Industry Mentor (IM)        → Cross-industry pattern observations

FLOW:
  CaaS Module [📝 GIVE FEEDBACK]
    → inclusion_hot_button.py writes to:
        FUSION_INTERVIEWS/<project>/inclusion_log.json
        FUSION_INTERVIEWS/<project>/interviewed/inclusion_*.json
    → THIS MODULE reads inclusion_log.json
    → Converts entries to interview-compatible format
    → Tags with Master Lens (ML1/ML2/ML3)
    → Fusion Interview Collector reads via get_inclusion_interviews()
    → Populates All Interviews tab: INCLUSION section

SaaS PASS TEAM (future — Immulsion):
  Same pattern. SaaS recipients submit observations.
  Tagged ML4 (Pilot Recipient). Appears as 4th section in All Interviews.

HIERARCHY:
  THE PERSON > TITS > GIBUSH > AISOS/SPINE > CaaS/SaaS > HONUS

In Memory of Kasie Malcolm and Allen Hornberger.
© 2026 Stephen J. Burdick Sr. — All Rights Reserved.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# ── PATHS ──
_TITS_ROOT = Path(r"C:\TITS\TITS_GIBUSH_AISOS_SPINE")
_ICORPS_ROOT = _TITS_ROOT / "TITS_GIBUSH_AISOS_SPINE_ICORPS"
# Canonical: collector uses FUSION_Projects/project_caas_deployed/
# We MUST read from the same folder or data never arrives.
_FUSION_ROOT = _ICORPS_ROOT / "FUSION_Projects" / "project_caas_deployed"
if not _FUSION_ROOT.exists():
    _FUSION_ROOT = _ICORPS_ROOT / "FUSION_INTERVIEWS"  # legacy fallback
_RECEIPT_DIR = _ICORPS_ROOT / "Inclusion_Module_Receipt_Collector"


# ══════════════════════════════════════════════════════════════
# MASTER LENS DEFINITIONS
# ══════════════════════════════════════════════════════════════

MASTER_LENS = {
    "EL": {
        "lens_id": "ML1",
        "lens_name": "Master Lens 1 — Entrepreneurial",
        "focus": "Business/market observations, customer pain, value proposition evidence",
        "color": "#FFD700",  # Gold
    },
    "TL": {
        "lens_id": "ML2",
        "lens_name": "Master Lens 2 — Technical",
        "focus": "Equipment/sensor/process observations, detection gaps, calibration notes",
        "color": "#00FFFF",  # Cyan
    },
    "IM": {
        "lens_id": "ML3",
        "lens_name": "Master Lens 3 — Industry Mentor",
        "focus": "Cross-industry patterns, similar deployments, standards compliance",
        "color": "#FF69B4",  # Pink
    },
    "OPERATOR": {
        "lens_id": "ML0",
        "lens_name": "Master Lens 0 — Operator Ground Truth",
        "focus": "Direct equipment interaction, shift observations, near-miss reports",
        "color": "#00FF00",  # Green
    },
    "ML4_SNIPPET": {
        "lens_id": "ML4",
        "lens_name": "Master Lens 4 - Snippet Insight",
        "focus": "Gathered intelligence, anonymous sources, conference notes, vendor whispers",
        "color": "#9933EA",
    },
}

# Future: Immulsion (SaaS recipient)
# "PILOT": {
#     "lens_id": "ML4",
#     "lens_name": "Master Lens 4 — Pilot Recipient",
#     "focus": "Deployment validation, real-world performance, adoption feedback",
#     "color": "#9933EA",  # Purple
# },


# ══════════════════════════════════════════════════════════════
# RECEIPT COLLECTOR — Reads inclusion logs, converts to interview format
# ══════════════════════════════════════════════════════════════

class InclusionReceiptCollector:
    """
    Reads all inclusion_log.json files across projects.
    Converts each entry to interview-compatible format with Master Lens tag.
    The Fusion Interview Collector calls get_inclusion_interviews() to
    populate the All Interviews tab.
    """

    def __init__(self):
        self.receipts: List[dict] = []
        self.by_project: Dict[str, List[dict]] = {}
        self.by_lens: Dict[str, List[dict]] = {}

    def scan_all_projects(self) -> int:
        """
        Scan all project folders for inclusion_log.json.
        Returns total number of inclusion entries found.
        """
        self.receipts = []
        self.by_project = {}
        self.by_lens = {}

        if not _FUSION_ROOT.exists():
            print(f"  [INCLUSION_RECEIPT] FUSION_INTERVIEWS not found")
            return 0

        for d in sorted(_FUSION_ROOT.iterdir()):
            if not d.is_dir() or d.name.startswith(("_", ".")):
                continue

            log_file = d / "inclusion_log.json"
            if not log_file.exists():
                continue

            try:
                data = json.loads(log_file.read_text(encoding='utf-8'))
                entries = data.get('entries', [])
                project_id = d.name

                for entry in entries:
                    record = self._convert_to_interview(entry, project_id)
                    self.receipts.append(record)

                    # Index by project
                    self.by_project.setdefault(project_id, []).append(record)

                    # Index by lens
                    lens = record.get('master_lens', 'ML0')
                    self.by_lens.setdefault(lens, []).append(record)

                if entries:
                    print(f"  [INCLUSION_RECEIPT] {project_id}: {len(entries)} entries")

            except Exception as e:
                print(f"  [INCLUSION_RECEIPT] Error reading {log_file}: {e}")

        print(f"  [INCLUSION_RECEIPT] Total: {len(self.receipts)} entries "
              f"from {len(self.by_project)} projects")
        return len(self.receipts)

    def _convert_to_interview(self, entry: dict, project_id: str) -> dict:
        """
        Convert an inclusion entry to interview-compatible format.
        This is what the Fusion Interview Collector reads.
        """
        role = entry.get('observer_role', 'OPERATOR')
        # ML4 snippets use master_lens field directly
        if entry.get('entry_type') == 'snippet' or entry.get('master_lens') == 'ML4':
            lens_info = MASTER_LENS.get('ML4_SNIPPET', MASTER_LENS.get('OPERATOR', {}))
        else:
            lens_info = MASTER_LENS.get(role, MASTER_LENS['OPERATOR'])

        # Build interview number: ML1-001, ML2-002, etc.
        inc_id = entry.get('inclusion_id', '')
        seq = inc_id.split('-')[-1] if inc_id else '0'

        interview_num = f"{lens_info['lens_id']}-{seq}"

        # Parse timestamp for date
        ts = entry.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(ts)
            date_str = dt.strftime("%b %d, %Y")
        except Exception:
            date_str = ts[:10] if ts else ""

        # Build Q-Cube position from observation context
        # Inclusion entries get a special stack position: Sι (iota = inclusion)
        q_layer = "L2" if role == "TL" else "L3" if role in ("EL", "IM") else "L1"
        q_object = "OC"  # Observation from CaaS context
        q_stack = "Sι"   # Iota = Inclusion stream

        return {
            # Interview-compatible fields
            "interview_num": interview_num,
            "date": date_str,
            "person": entry.get('observer_name', 'Anonymous'),
            "company": "Internal (CaaS Deployed)",
            "title": f"{role} — {lens_info['lens_name']}",
            "customer_type": f"Inclusion/{role}",
            "q_layer": q_layer,
            "q_object": q_object,
            "q_stack": q_stack,
            "cube_position": f"[{q_layer}, {q_object}, {q_stack}]",

            # Interview content (mapped from inclusion fields)
            "results": entry.get('observation', ''),
            "experiments": f"Observed while running: {entry.get('source_module', '')}",
            "hypotheses": entry.get('hypothesis_impact', ''),
            "hypotheses_validation": "",
            "action_iterate": "",
            "experiments_answers": {},
            "equipment_discussed": [{
                "equipment": entry.get('source_module', ''),
                "notes": entry.get('observation', ''),
            }],

            # Inclusion-specific metadata
            "source": "INCLUSION",
            "master_lens": lens_info['lens_id'],
            "master_lens_name": lens_info['lens_name'],
            "lens_color": lens_info['color'],
            "inclusion_id": entry.get('inclusion_id', ''),
            "source_module": entry.get('source_module', ''),
            "project_id": project_id,
            "observation_type": entry.get('observation_type', ''),
            "severity": entry.get('severity', 'NOTICE'),
            "safety_signal": entry.get('safety_signal', False),
            "champion_gate": entry.get('champion_gate', False),
            "original_timestamp": ts,
        }

    def get_inclusion_interviews(self, project_id: str = None) -> List[dict]:
        """
        Get inclusion entries as interview-format records.
        If project_id is given, filter to that project.
        Otherwise return all.

        Called by fusion_interview_collector.py to populate All Interviews.
        """
        if not self.receipts:
            self.scan_all_projects()

        if project_id:
            return self.by_project.get(project_id, [])
        return self.receipts

    def get_by_lens(self, lens_id: str) -> List[dict]:
        """Get entries filtered by Master Lens (ML1, ML2, ML3)."""
        if not self.receipts:
            self.scan_all_projects()
        return self.by_lens.get(lens_id, [])

    def get_summary(self) -> dict:
        """Summary for display in collector UI."""
        if not self.receipts:
            self.scan_all_projects()

        summary = {
            "total": len(self.receipts),
            "by_project": {k: len(v) for k, v in self.by_project.items()},
            "by_lens": {},
            "safety_signals": sum(1 for r in self.receipts if r.get('safety_signal')),
        }

        for lens_id, entries in self.by_lens.items():
            lens_info = next(
                (v for v in MASTER_LENS.values() if v['lens_id'] == lens_id),
                {"lens_name": lens_id}
            )
            summary["by_lens"][lens_id] = {
                "name": lens_info.get('lens_name', lens_id),
                "count": len(entries),
            }


        # TCM: Tendency Conscious Matrix
        tcm = {}
        for r in self.receipts:
            if r.get('entry_type') == 'snippet' or 'difficulty_score' in r:
                topic = r.get('topic', r.get('observation_type', 'Unknown'))
                diff = r.get('difficulty_score', 0)
                if diff > 0:
                    tcm.setdefault(topic, {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
                    tcm[topic][diff] = tcm[topic].get(diff, 0) + 1
        summary["tcm"] = tcm
        summary["tcm_signals"] = []
        for topic, scores in tcm.items():
            hard = scores.get(4, 0) + scores.get(5, 0)
            easy = scores.get(1, 0) + scores.get(2, 0)
            total = sum(scores.values())
            if total >= 2 and hard > easy:
                summary["tcm_signals"].append({
                    "topic": topic, "pattern": "HIGH_RESISTANCE",
                    "hard_count": hard, "easy_count": easy, "total": total,
                })
        return summary

    def save_consolidated(self, project_id: str) -> Path:
        """
        Save consolidated inclusion interviews to a file the
        Fusion Interview Collector can easily load.
        """
        entries = self.get_inclusion_interviews(project_id)
        if not entries:
            return None

        project_dir = _FUSION_ROOT / project_id
        out_file = project_dir / "inclusion_interviews.json"

        data = {
            "source": "Inclusion_Module_Receipt_Collector",
            "stream": "INCLUSION",
            "project_id": project_id,
            "master_rule": "The Person is the Highest Responsibility",
            "generated": datetime.now().isoformat(),
            "count": len(entries),
            "master_lens_legend": {
                k: v for k, v in MASTER_LENS.items()
            },
            "interviews": entries,
        }

        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"  [INCLUSION_RECEIPT] Consolidated: {out_file} ({len(entries)} entries)")
        return out_file


# ══════════════════════════════════════════════════════════════
# INTEGRATION API — For fusion_interview_collector.py
# ══════════════════════════════════════════════════════════════

# Singleton instance for the collector to import
_collector_instance = None

def get_receipt_collector() -> InclusionReceiptCollector:
    """Get or create the singleton InclusionReceiptCollector."""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = InclusionReceiptCollector()
    return _collector_instance


def get_inclusion_for_project(project_id: str) -> List[dict]:
    """
    Convenience function for the Fusion Interview Collector.

    Usage in fusion_interview_collector.py:
        from Inclusion_Module_Receipt_Collector.inclusion_receipt import (
            get_inclusion_for_project
        )
        inclusion_interviews = get_inclusion_for_project("CHIP_BLOW_LINE")
        # Returns list of interview-format dicts with Master Lens tags
    """
    collector = get_receipt_collector()
    return collector.get_inclusion_interviews(project_id)


def get_inclusion_summary() -> dict:
    """Convenience function for summary display."""
    collector = get_receipt_collector()
    return collector.get_summary()


# ══════════════════════════════════════════════════════════════
# STANDALONE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  INCLUSION MODULE RECEIPT COLLECTOR")
    print("  Stream 2 of Intelligence Triad")
    print("  The Person is the Highest Responsibility")
    print("=" * 70)

    collector = InclusionReceiptCollector()
    total = collector.scan_all_projects()

    if total == 0:
        print("\n  No inclusion entries found yet.")
        print("  Deploy a CaaS module, click 📝 GIVE FEEDBACK to create entries.")
        print("  They will appear here as Master Lens tagged interviews.")
    else:
        summary = collector.get_summary()
        print(f"\n  TOTAL ENTRIES: {summary['total']}")
        print(f"  SAFETY SIGNALS: {summary['safety_signals']}")

        print(f"\n  BY PROJECT:")
        for pid, count in summary['by_project'].items():
            print(f"    {pid}: {count} entries")

        print(f"\n  BY MASTER LENS:")
        for lid, info in summary['by_lens'].items():
            print(f"    {lid} ({info['name']}): {info['count']} entries")

        # Show entries
        print(f"\n  ALL INCLUSION INTERVIEWS:")
        print(f"  {'#':<12} {'Date':<14} {'Person':<18} {'Lens':<8} {'Type':<22} {'Sev':<10}")
        print(f"  {'─'*12} {'─'*14} {'─'*18} {'─'*8} {'─'*22} {'─'*10}")

        for r in collector.receipts:
            print(f"  {r['interview_num']:<12} "
                  f"{r['date']:<14} "
                  f"{r['person']:<18} "
                  f"{r['master_lens']:<8} "
                  f"{r['observation_type']:<22} "
                  f"{r['severity']:<10}")
            if r.get('safety_signal'):
                print(f"  {'':>12} ⚠ SAFETY SIGNAL")

        # Save consolidated
        for pid in summary['by_project']:
            collector.save_consolidated(pid)

    print(f"\n  MASTER LENS LEGEND:")
    for role, info in MASTER_LENS.items():
        print(f"    {info['lens_id']} ({role}): {info['focus']}")

    print("\n  In Memory of Kasie Malcolm and Allen Hornberger.")
    print("=" * 70)
