#!/usr/bin/env python3
"""
INTERVIEW INTELLIGENCE ENGINE - Compound Interest AI
=====================================================
C:\\TITS\\TITS_Production\\gibush_icorps\\interview_intelligence.py

Each interview makes the next one smarter. This file:
  1. Reads ALL completed interviews from InterviewDatabase
  2. Calculates: VP confidence, cube density, equipment damage ranking,
     hypothesis validation, budget signals, contradictions
  3. For each PENDING interview, generates a compound intelligence brief:
     - Targeted questions (calibrated to what's validated/weak)
     - Equipment checklist (ranked by damage frequency * cost)
     - Contradictions to resolve
     - Specific dollar probes ("4 mills report $300K. What's yours?")
  4. Replaces _load_genesis_intelligence() in generate_interview_template()

INTEGRATION (in fusion_interview_collector.py):
    # Replace the old genesis intelligence call:
    # OLD: genesis_intel = self._load_genesis_intelligence()
    # NEW:
    from interview_intelligence import InterviewIntelligence
    intel_engine = InterviewIntelligence(self.database)
    brief = intel_engine.generate_brief(interview_data)
    # brief dict has everything the template needs

Also generates updated Excel-compatible plans with smart questions.

Author: GIBUSH AI Engineering
Version: 1.0.0
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict


# ============================================================================
# Q-CUBE DEFINITIONS (must match fusion_interview_collector.py)
# ============================================================================

QCUBE_LAYERS = {
    "L1": "Operator Care - Daily pain, hands-on experience",
    "L2": "Manager Care - Production responsibility, P&L ownership",
    "L3": "Executive Care - Strategic risk, enterprise protection",
}

QCUBE_OBJECTS = {
    "OA": "Upstream Supplier - Chip mills, timber (get blamed)",
    "OB": "Transfer Point - Blow line, bark line (blind spot)",
    "OC": "Downstream Receiver - Kraft mill, digester (gets damaged)",
}

# LAYER FOCUS - CORRECTED (was swapped in original code L1<->L3)
LAYER_FOCUS = {
    "L1": {
        "role": "Operator",
        "focus": "Hands-on equipment experience, daily pain points, operator workarounds",
        "asks": "Which equipment breaks down? How do you detect problems? What do instruments miss?",
    },
    "L2": {
        "role": "Manager",
        "focus": "Equipment budgets, maintenance costs, process improvement decisions, AMO authority",
        "asks": "What are annual damage costs? What budget path exists? What ROI do you need?",
    },
    "L3": {
        "role": "Executive",
        "focus": "Strategic risk, capital allocation, ROI requirements, vendor relationships",
        "asks": "What budget would you allocate? Who makes final decisions? What's enterprise risk?",
    },
}

OBJECT_FOCUS = {
    "OA": {
        "role": "Upstream Supplier",
        "focus": "Chip quality, debarking, screening before shipment",
        "asks": "What contamination do you see leaving your facility? What would verification data mean?",
    },
    "OB": {
        "role": "Transfer Point",
        "focus": "Blow line, chip handling, the blind spot between screening and digester",
        "asks": "What visibility do you have at the blow line? What gets through your screens?",
    },
    "OC": {
        "role": "Downstream Receiver",
        "focus": "Receiving damage, maintenance burden, accepted damage model",
        "asks": "What's your annual damage cost? What equipment suffers most? How do you detect contamination?",
    },
}


# ============================================================================
# VP THEMES - Definitions for scoring
# ============================================================================

VP_DEFINITIONS = {
    "VP1_DAMAGE_PREVENTION": {
        "claim": "Real-time detection prevents $100K-$1M+ damage events",
        "keywords": ["damage event", "$100k", "rock event", "shutdown",
                     "digester", "screen basket", "damage point",
                     "100% of rocks", "catastrophic", "$300k", "$500k",
                     "unplanned downtime", "equipment damage"],
        "counter": ["not worth", "too expensive", "wouldn't pay",
                    "not a problem", "don't see damage"],
        "threshold": 3,  # interviews to validate
    },
    "VP2_PLANNED_MAINTENANCE": {
        "claim": "Converts reactive maintenance to planned maintenance",
        "keywords": ["reactive", "accepted damage", "planned", "PM",
                     "all wear", "not built for rock", "chip line repair",
                     "emergency", "20 cts rollers", "equipment wear"],
        "counter": ["already planned", "maintenance is fine"],
        "threshold": 3,
    },
    "VP3_OPERATOR_VISIBILITY": {
        "claim": "Gives operators real-time visibility they don't have",
        "keywords": ["will try anything", "would adopt", "readings",
                     "go look", "real-time", "visibility", "measurement",
                     "for sure mt", "nothing on the piles"],
        "counter": ["don't need", "too complex", "won't use"],
        "threshold": 3,
    },
    "VP4_CHEMICAL_OPTIMIZATION": {
        "claim": "Quality stabilization saves $500K/yr in chemical costs",
        "keywords": ["$500k", "chemical savings", "dosing", "off-quality",
                     "consistency", "quality stabilization"],
        "counter": ["chemicals fine", "not related"],
        "threshold": 3,
    },
    "VP5_SUPPLIER_ACCOUNTABILITY": {
        "claim": "Digital contamination log enables vendor accountability",
        "keywords": ["vendor", "supplier", "docking", "certified clean",
                     "verification", "premium pricing", "flying blind",
                     "procurement"],
        "counter": ["can't prove", "vendor won't accept"],
        "threshold": 3,
    },
    "VP6_PITCH_CONTAMINATION": {
        "claim": "Upstream pitch/contaminant tracing to paper machine",
        "keywords": ["pitch", "talc", "forming fabric", "microplastic",
                     "felt", "clothing", "paper machine", "deposit"],
        "counter": [],
        "threshold": 3,
    },
}

# Budget signal keywords
BUDGET_PATH_KW = ["amo budget", "amo best", "maintenance budget",
                  "operating budget", "authorize", "would buy",
                  "worth it", "immediately", "roi"]
BUDGET_BLOCK_KW = ["no money", "no budget", "won't invest",
                   "severely constrained", "budget constrained",
                   "not justified", "no money in making pulp"]


# ============================================================================
# INTERVIEW INTELLIGENCE ENGINE
# ============================================================================

class InterviewIntelligence:
    """
    Compound interest AI: each interview makes the next one smarter.

    Usage:
        engine = InterviewIntelligence(database)
        brief = engine.generate_brief(pending_interview_dict)
        summary = engine.get_state_summary()
    """

    def __init__(self, database=None):
        self.interviews: List[dict] = []  # completed interviews as dicts
        self.state: Dict = {}  # calculated state

        if database is not None:
            self.load(database)
            self.calculate()

    # ------------------------------------------------------------------
    # LOADING
    # ------------------------------------------------------------------

    def load(self, database):
        """Load from InterviewDatabase or list of dicts."""
        if isinstance(database, list):
            self.interviews = database
        elif hasattr(database, "interviews"):
            self.interviews = []
            for iv in database.interviews:
                if hasattr(iv, "to_dict"):
                    self.interviews.append(iv.to_dict())
                elif isinstance(iv, dict):
                    self.interviews.append(iv)

    def load_json(self, filepath: str):
        """Load from JSON database file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "interviews" in data:
            self.interviews = data["interviews"]
        elif isinstance(data, list):
            self.interviews = data

    # ------------------------------------------------------------------
    # CALCULATE - Build the intelligence state from all interviews
    # ------------------------------------------------------------------

    def calculate(self) -> Dict:
        """
        Calculate complete intelligence state from all completed interviews.
        Call this after loading data and before generating briefs.
        """
        # Filter to interviews with actual results
        active = [
            iv for iv in self.interviews
            if iv.get("results", "")
            and not str(iv["results"]).startswith("[PENDING")
        ]

        n = len(active)
        if n == 0:
            self.state = {"interview_count": 0, "ready": False}
            return self.state

        # --- 1. VP Confidence Scoring ---
        vp_scores = {}
        for vp_id, vp_def in VP_DEFINITIONS.items():
            supporting = []
            contradicting = []
            for iv in active:
                text = (iv.get("results", "") + " " + iv.get("action_iterate", "")).lower()
                has_support = any(kw in text for kw in vp_def["keywords"])
                has_counter = any(kw in text for kw in vp_def["counter"])
                if has_support and not has_counter:
                    supporting.append(iv.get("person", ""))
                elif has_counter:
                    contradicting.append(iv.get("person", ""))

            support_count = len(supporting)
            contra_count = len(contradicting)
            confidence = min(100, int((support_count / max(vp_def["threshold"], 1)) * 100))

            if contra_count > support_count:
                status = "INVALIDATED"
            elif support_count >= vp_def["threshold"]:
                status = "VALIDATED"
            elif support_count >= 1:
                status = "TESTING"
            else:
                status = "NO DATA"

            vp_scores[vp_id] = {
                "claim": vp_def["claim"],
                "supporting": supporting,
                "contradicting": contradicting,
                "support_count": support_count,
                "contra_count": contra_count,
                "confidence": confidence,
                "status": status,
                "needs_more": support_count < vp_def["threshold"],
                "gap": max(0, vp_def["threshold"] - support_count),
            }

        # --- 2. Cube Density ---
        layer_counts = Counter(iv.get("q_layer", "") for iv in active if iv.get("q_layer"))
        object_counts = Counter(iv.get("q_object", "") for iv in active if iv.get("q_object"))
        primary_layer = layer_counts.most_common(1)[0][0] if layer_counts else "L2"
        primary_object = object_counts.most_common(1)[0][0] if object_counts else "OC"

        # Cube gap analysis: which positions have zero interviews?
        cube_gaps = []
        for layer in ["L1", "L2", "L3"]:
            for obj in ["OA", "OB", "OC"]:
                count = sum(
                    1 for iv in active
                    if iv.get("q_layer") == layer and iv.get("q_object") == obj
                )
                if count == 0:
                    cube_gaps.append(f"[{layer}, {obj}]")

        # --- 3. Equipment Damage Ranking ---
        equipment_stats = defaultdict(lambda: {
            "count": 0, "total_annual": 0,
            "interviews": [], "annual_damages": [],
            "costs_per_event": [], "frequencies": [],
        })
        for iv in active:
            for ei in iv.get("equipment_impacts", []):
                if isinstance(ei, dict):
                    name = ei.get("equipment", "Unknown")
                    # New schema: cost_per_event * frequency = annual_damage
                    cost_per_event = ei.get("cost_per_event", ei.get("cost", 0))
                    frequency = ei.get("frequency", 1)
                    annual_damage = ei.get("annual_damage", cost_per_event * frequency)

                    equipment_stats[name]["count"] += 1
                    equipment_stats[name]["total_annual"] += annual_damage
                    equipment_stats[name]["interviews"].append(iv.get("person", ""))
                    if annual_damage > 0:
                        equipment_stats[name]["annual_damages"].append(annual_damage)
                    if cost_per_event > 0:
                        equipment_stats[name]["costs_per_event"].append(cost_per_event)
                    if frequency > 0:
                        equipment_stats[name]["frequencies"].append(frequency)

        # Sort by damage_score = count * avg_cost (compound signal)
        for name, stats in equipment_stats.items():
            stats["avg_annual"] = stats["total_annual"] / max(stats["count"], 1)
            stats["avg_cost_per_event"] = (
                sum(stats["costs_per_event"]) / len(stats["costs_per_event"])
                if stats["costs_per_event"] else 0
            )
            stats["avg_frequency"] = (
                sum(stats["frequencies"]) / len(stats["frequencies"])
                if stats["frequencies"] else 0
            )
            # damage_score = avg annual damage (the REAL number)
            stats["damage_score"] = stats["avg_annual"]
            # backward compat
            stats["avg_cost"] = stats["avg_annual"]

        equipment_ranked = sorted(
            equipment_stats.items(),
            key=lambda x: x[1]["damage_score"],
            reverse=True,
        )

        # --- 4. Budget Signal Analysis ---
        budget_paths = []
        budget_blockers = []
        for iv in active:
            text = iv.get("results", "").lower()
            if any(kw in text for kw in BUDGET_PATH_KW):
                budget_paths.append({
                    "person": iv.get("person", ""),
                    "signal": [kw for kw in BUDGET_PATH_KW if kw in text][0],
                })
            if any(kw in text for kw in BUDGET_BLOCK_KW):
                budget_blockers.append({
                    "person": iv.get("person", ""),
                    "signal": [kw for kw in BUDGET_BLOCK_KW if kw in text][0],
                })

        # --- 5. Contradiction Detection ---
        contradictions = []
        # Budget contradiction: someone says path exists, someone says no money
        if budget_paths and budget_blockers:
            contradictions.append({
                "type": "BUDGET",
                "for": [f"#{p['num']} {p['person']}: '{p['signal']}'" for p in budget_paths[:2]],
                "against": [f"#{b['num']} {b['person']}: '{b['signal']}'" for b in budget_blockers[:2]],
                "probe": "Some managers found AMO budget paths. Others say no money in pulp. Which is your reality?",
            })

        # VP contradictions: same VP has both supporting and contradicting
        for vp_id, vp in vp_scores.items():
            if vp["support_count"] >= 2 and vp["contra_count"] >= 1:
                contradictions.append({
                    "type": f"VP ({vp_id})",
                    "for": [f"#{n}" for n in vp["supporting"][:3]],
                    "against": [f"#{n}" for n in vp["contradicting"][:2]],
                    "probe": f"Regarding: {vp['claim']} - we have mixed signals. What's your experience?",
                })

        # --- 6. Hypothesis Validation ---
        hypotheses = {
            "H1_MANUAL_DETECTION_FAILS": {
                "name": "Manual rock detection is industry-wide failure",
                "keywords": ["manual", "100%", "go look", "nothing", "visual inspection"],
            },
            "H2_COST_UNDERSTATED": {
                "name": "True contamination cost is understated",
                "keywords": ["$300k", "$500k", "$100k", "hidden cost", "warranty gap",
                             "understated", "lead time"],
            },
            "H3_MODERN_EQUIPMENT_FAILS": {
                "name": "Capital investment alone doesn't solve contamination",
                "keywords": ["modern equipment", "still", "new equipment",
                             "1b", "billion", "modernization"],
            },
            "H4_OPERATOR_SENSES": {
                "name": "Operators sense problems instruments miss",
                "keywords": ["operator", "sense", "hear", "feel", "know before",
                             "experience"],
            },
            "H5_BLOW_LINE_BLIND_SPOT": {
                "name": "Blow line entry is critical blind spot",
                "keywords": ["blind", "visibility", "blow line", "between screening",
                             "last chance", "transfer point"],
            },
        }

        hyp_status = {}
        for hyp_id, hyp_def in hypotheses.items():
            supporting = []
            for iv in active:
                text = (iv.get("results", "") + " " + iv.get("hypotheses", "")).lower()
                if any(kw in text for kw in hyp_def["keywords"]):
                    supporting.append(iv.get("person", ""))
            count = len(supporting)
            hyp_status[hyp_id] = {
                "name": hyp_def["name"],
                "supporting": supporting,
                "count": count,
                "confidence": min(100, int(count / 3 * 100)),
                "status": "VALIDATED" if count >= 3 else "TESTING" if count >= 1 else "UNTESTED",
                "needs_more": count < 3,
            }

        # --- 7. Dollar Calibration (what $ figures do we have?) ---
        dollar_points = []
        for iv in active:
            for ei in iv.get("equipment_impacts", []):
                if isinstance(ei, dict):
                    cost_per_event = ei.get("cost_per_event", ei.get("cost", 0))
                    frequency = ei.get("frequency", 1)
                    annual = ei.get("annual_damage", cost_per_event * frequency)
                    if annual > 0:
                        dollar_points.append({
                            "person": iv.get("person", ""),
                            "equipment": ei.get("equipment", ""),
                            "cost_per_event": cost_per_event,
                            "frequency": frequency,
                            "annual_damage": annual,
                        })

        total_damage = sum(d["annual_damage"] for d in dollar_points)
        company_count = len(set(iv.get("company", "") for iv in active if iv.get("company")))

        # --- 8. Companies covered ---
        companies_seen = sorted(set(iv.get("company", "") for iv in active if iv.get("company")))

        # --- Build state ---
        self.state = {
            "ready": True,
            "interview_count": n,
            "sparks_count": sum(1 for iv in active if iv.get("source", "") != "fusion"),
            "fusion_count": sum(1 for iv in active if iv.get("source", "") == "fusion"),
            "company_count": company_count,
            "companies": companies_seen,
            "vp_scores": vp_scores,
            "layer_density": dict(layer_counts),
            "object_density": dict(object_counts),
            "primary_layer": primary_layer,
            "primary_object": primary_object,
            "cube_gaps": cube_gaps,
            "equipment_ranked": equipment_ranked,
            "budget_paths": budget_paths,
            "budget_blockers": budget_blockers,
            "contradictions": contradictions,
            "hypotheses": hyp_status,
            "dollar_points": dollar_points,
            "total_damage_documented": total_damage,
        }

        return self.state

    # ------------------------------------------------------------------
    # GENERATE BRIEF - compound intelligence for one pending interview
    # ------------------------------------------------------------------

    def generate_brief(self, pending: dict) -> dict:
        """
        Generate compound intelligence brief for a pending interview.

        Args:
            pending: dict with keys from Excel plan:
                num, name, title, company, type,
                hypothesis, questions, q_layer, q_object, q_stack

        Returns:
            dict with all intelligence the template generator needs.
        """
        if not self.state.get("ready"):
            return self._empty_brief(pending)

        s = self.state
        n = s["interview_count"]
        q_layer = pending.get("q_layer", "L2")
        q_object = pending.get("q_object", "OC")

        # --- Layer + Object focus (CORRECTED labels) ---
        layer_info = LAYER_FOCUS.get(q_layer, LAYER_FOCUS["L2"])
        object_info = OBJECT_FOCUS.get(q_object, OBJECT_FOCUS["OC"])

        # --- Mission statement ---
        mission = (
            f"FOCUS: {layer_info['focus']}\n"
            f"POSITION: {layer_info['role']} at {object_info['role']}\n"
            f"KEY ASKS: {layer_info['asks']}\n"
            f"OBJECT FOCUS: {object_info['asks']}"
        )

        # --- Compound questions (calibrated to current state) ---
        compound_questions = []

        # Q1: Dollar calibration (always ask, calibrated to what we know)
        if s["total_damage_documented"] > 0:
            avg_damage = s["total_damage_documented"] / max(s["company_count"], 1)
            compound_questions.append(
                f"DOLLAR CALIBRATION: {n} interviews across {s['company_count']} "
                f"companies report ${s['total_damage_documented']/1000:.0f}K total documented "
                f"damage (avg ${avg_damage/1000:.0f}K/company). "
                f"At {pending.get('company', 'your facility')}, what are your "
                f"annual contamination damage costs?"
            )
        else:
            compound_questions.append(
                "DOLLAR DISCOVERY: What is your annual cost of contamination damage? "
                "Include: equipment repairs, downtime, chemical waste, labor."
            )

        # Q2: Weakest VP (target for validation)
        weakest_vp = None
        for vp_id, vp in sorted(s["vp_scores"].items(),
                                 key=lambda x: x[1]["confidence"]):
            if vp["needs_more"] and vp["support_count"] >= 1:
                weakest_vp = vp
                break

        if weakest_vp:
            compound_questions.append(
                f"VP VALIDATION ({weakest_vp['status']}, {weakest_vp['confidence']}% confidence, "
                f"need {weakest_vp['gap']} more): "
                f"\"{weakest_vp['claim']}\" - "
                f"{weakest_vp['support_count']} interviews support this. "
                f"What's your experience?"
            )

        # Q3: Contradiction resolution (if any)
        for contradiction in s["contradictions"][:1]:
            compound_questions.append(
                f"CONTRADICTION TO RESOLVE ({contradiction['type']}): "
                f"{contradiction['probe']}"
            )

        # Q4: Cube gap fill (if this person fills a gap)
        position = f"[{q_layer}, {q_object}]"
        if position in s["cube_gaps"]:
            compound_questions.append(
                f"CUBE GAP: We have ZERO interviews at position {position}. "
                f"This person fills a critical gap. Ask broadly about their "
                f"perspective on contamination impacts."
            )

        # Q5: Equipment-specific (top damage item they haven't confirmed)
        if s["equipment_ranked"]:
            top_equip = s["equipment_ranked"][0]
            equip_name = top_equip[0]
            equip_data = top_equip[1]
            freq_str = f", ~{equip_data['avg_frequency']:.0f}x/yr" if equip_data.get("avg_frequency", 0) > 0 else ""
            compound_questions.append(
                f"TOP EQUIPMENT PROBE: {equip_name} is our #1 damage item "
                f"({equip_data['count']} interviews, ${equip_data['avg_annual']/1000:.0f}K/yr avg{freq_str}). "
                f"How often does {equip_name} fail from contamination at your mill? What does each event cost?"
            )

        # Q6: Layer-specific compound question
        if q_layer == "L2" and s["budget_paths"]:
            path_names = [f"#{p['num']}" for p in s["budget_paths"][:3]]
            compound_questions.append(
                f"BUDGET PATH VALIDATION: Interviews {', '.join(path_names)} "
                f"found AMO budget paths for contamination tech. "
                f"What's YOUR budget authority for maintenance technology?"
            )
        elif q_layer == "L1":
            compound_questions.append(
                "OPERATOR KNOWLEDGE: What do you notice BEFORE instruments "
                "detect a problem? What sounds, vibrations, or visual cues "
                "tell you contamination is coming through?"
            )
        elif q_layer == "L3":
            compound_questions.append(
                f"STRATEGIC ALLOCATION: With ${s['total_damage_documented']/1000:.0f}K "
                f"documented damage across {s['company_count']} companies, "
                f"what level of investment would you authorize to prevent this?"
            )

        # --- Equipment checklist (ranked by damage score) ---
        equipment_checklist = []
        for equip_name, stats in s["equipment_ranked"][:10]:
            priority = "HIGH" if stats["damage_score"] > 100000 else "MEDIUM" if stats["damage_score"] > 25000 else "LOW"
            freq_str = f"{stats['avg_frequency']:.0f}x/yr" if stats.get("avg_frequency", 0) > 0 else "?"
            equipment_checklist.append({
                "name": equip_name,
                "priority": priority,
                "mentions": stats["count"],
                "avg_annual": f"${stats['avg_annual']/1000:.0f}K/yr" if stats["avg_annual"] > 0 else "Unknown",
                "avg_cost_per_event": f"${stats['avg_cost_per_event']/1000:.0f}K" if stats.get("avg_cost_per_event", 0) > 0 else "?",
                "avg_frequency": freq_str,
                "interviews": stats["interviews"],
            })

        # --- Updated hypotheses (auto-validated) ---
        updated_hypotheses = []
        for hyp_id, hyp in s["hypotheses"].items():
            if hyp["needs_more"]:
                updated_hypotheses.append(
                    f"{hyp['name']} [{hyp['status']} - {hyp['confidence']}% - "
                    f"need {3 - hyp['count']} more interviews]"
                )
            else:
                updated_hypotheses.append(
                    f"{hyp['name']} [VALIDATED - {hyp['confidence']}% - "
                    f"{hyp['count']} interviews]"
                )

        # --- VP summary for template header ---
        vp_summary = []
        for vp_id, vp in sorted(s["vp_scores"].items(),
                                 key=lambda x: x[1]["confidence"],
                                 reverse=True):
            icon = "V" if vp["status"] == "VALIDATED" else "?" if vp["status"] == "TESTING" else "X"
            vp_summary.append(
                f"[{icon}] {vp['claim']} "
                f"({vp['confidence']}%, {vp['support_count']} interviews)"
            )

        return {
            "available": True,
            "interview_count": n,
            "mission": mission,
            "compound_questions": compound_questions,
            "equipment_checklist": equipment_checklist,
            "equipment_count": len(s["equipment_ranked"]),
            "updated_hypotheses": updated_hypotheses,
            "vp_summary": vp_summary,
            "contradictions": s["contradictions"],
            "budget_paths": s["budget_paths"],
            "budget_blockers": s["budget_blockers"],
            "cube_gaps": s["cube_gaps"],
            "total_damage": s["total_damage_documented"],
            "company_count": s["company_count"],
            "layer_density": s["layer_density"],
            "primary_layer": s["primary_layer"],
            # Keep backward compat with old genesis_intel format
            "gaps": [f"Cube gap: {g}" for g in s["cube_gaps"][:3]],
            "hypotheses": {
                h["name"]: {
                    "confidence": h["confidence"],
                    "needs_more": h["needs_more"],
                    "probe_question": f"Evidence for: {h['name']}?",
                }
                for h in s["hypotheses"].values()
            },
            "equipment_mentions": {
                name: {"count": stats["count"],
                       "avg_cost": f"${stats['avg_annual']/1000:.0f}K/yr"
                               if stats["avg_annual"] > 0 else "Unknown"}
                for name, stats in s["equipment_ranked"][:5]
            },
        }

    def _empty_brief(self, pending: dict) -> dict:
        """Return brief for when no prior interviews exist."""
        q_layer = pending.get("q_layer", "L2")
        q_object = pending.get("q_object", "OC")
        layer_info = LAYER_FOCUS.get(q_layer, LAYER_FOCUS["L2"])
        object_info = OBJECT_FOCUS.get(q_object, OBJECT_FOCUS["OC"])

        return {
            "available": False,
            "interview_count": 0,
            "mission": (
                f"FOCUS: {layer_info['focus']}\n"
                f"This is an early interview. Discover pain, equipment damage costs, "
                f"and current approach to contamination detection."
            ),
            "compound_questions": [
                "DISCOVERY: What is your biggest contamination challenge?",
                "DOLLAR DISCOVERY: What are your annual contamination damage costs?",
                "DETECTION: How do you currently detect contamination? What gets through?",
            ],
            "equipment_checklist": [],
            "updated_hypotheses": [
                "Manual detection fails industry-wide [UNTESTED]",
                "True contamination cost is understated [UNTESTED]",
                "Modern equipment doesn't solve contamination [UNTESTED]",
            ],
            "vp_summary": [],
            "contradictions": [],
            "budget_paths": [],
            "budget_blockers": [],
            "cube_gaps": [],
            "total_damage": 0,
            "company_count": 0,
            "layer_density": {},
            "primary_layer": "",
            "gaps": ["All cube positions need data"],
            "hypotheses": {},
            "equipment_mentions": {},
        }

    # ------------------------------------------------------------------
    # STATE SUMMARY (for dashboard display)
    # ------------------------------------------------------------------

    def get_state_summary(self) -> str:
        """Return plain text summary for GUI display."""
        if not self.state.get("ready"):
            return "No interviews loaded. Run calculate() first."

        s = self.state
        lines = [
            "=" * 60,
            "INTERVIEW INTELLIGENCE STATE",
            f"  {s['interview_count']} interviews "
            f"({s['sparks_count']} Sparks + {s['fusion_count']} Fusion)",
            f"  {s['company_count']} companies: {', '.join(s['companies'])}",
            f"  Total documented damage: ${s['total_damage_documented']/1000:.0f}K",
            "=" * 60, "",
            "--- VP CONFIDENCE ---",
        ]

        for vp_id, vp in sorted(s["vp_scores"].items(),
                                  key=lambda x: x[1]["confidence"], reverse=True):
            bar = "#" * (vp["confidence"] // 10) + "." * (10 - vp["confidence"] // 10)
            lines.append(
                f"  [{bar}] {vp['confidence']:3d}% {vp['status']:12s} "
                f"{vp['claim'][:50]}"
            )

        lines.extend(["", "--- CUBE DENSITY ---"])
        for layer in ["L1", "L2", "L3"]:
            count = s["layer_density"].get(layer, 0)
            marker = " << PRIMARY BUYER" if layer == s["primary_layer"] else ""
            lines.append(f"  {layer}: {count} interviews{marker}")

        lines.extend(["", "--- EQUIPMENT DAMAGE RANKING (annual_damage = $/event × freq/yr) ---"])
        for name, stats in s["equipment_ranked"][:5]:
            freq_str = f"{stats['avg_frequency']:.0f}x/yr" if stats.get("avg_frequency", 0) > 0 else "?x/yr"
            cpe_str = f"${stats['avg_cost_per_event']/1000:.0f}K/event" if stats.get("avg_cost_per_event", 0) > 0 else "?"
            lines.append(
                f"  #{stats['count']:2d} mentions | {cpe_str:>12s} × {freq_str:>6s} "
                f"= ${stats['avg_annual']/1000:6.0f}K/yr | {name}"
            )

        if s["contradictions"]:
            lines.extend(["", "--- CONTRADICTIONS ---"])
            for c in s["contradictions"]:
                lines.append(f"  [{c['type']}] {c['probe'][:60]}")

        if s["cube_gaps"]:
            lines.extend(["", "--- CUBE GAPS (no interviews) ---"])
            for gap in s["cube_gaps"]:
                lines.append(f"  {gap}")

        lines.extend(["", "--- HYPOTHESES ---"])
        for hyp_id, hyp in s["hypotheses"].items():
            lines.append(
                f"  {hyp['confidence']:3d}% {hyp['status']:10s} {hyp['name']}"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # GENERATE UPDATED EXCEL PLAN (smart questions for all pending)
    # ------------------------------------------------------------------

    def update_excel_plan(self, current_plan: list) -> list:
        """
        Take the current Excel plan and return updated version with
        compound intelligence questions injected for pending interviews.

        Args:
            current_plan: list of dicts from excel_interview_loader

        Returns:
            Updated plan with 'smart_questions' and 'smart_hypothesis' added
        """
        if not self.state.get("ready"):
            return current_plan

        completed_names = set(iv.get("person", "").strip().lower() for iv in self.interviews
                            if iv.get("results", ""))

        updated = []
        for plan_entry in current_plan:
            entry = dict(plan_entry)  # copy
            entry_name = entry.get("name", "").strip().lower()
            if entry_name not in completed_names:
                brief = self.generate_brief(entry)
                # Add smart questions
                entry["smart_questions"] = "\n".join(
                    f"Q{i+1}. {q}" for i, q in enumerate(brief["compound_questions"])
                )
                # Add updated hypotheses
                entry["smart_hypothesis"] = "\n".join(brief["updated_hypotheses"])
            updated.append(entry)

        return updated


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    import sys

    # Find data file
    json_paths = [
        Path("ICORPS_Sparks_interview_database_deck.json"),
        Path("gibush_icorps/ICORPS_Sparks_interview_database_deck.json"),
        Path(__file__).parent / "ICORPS_Sparks_interview_database_deck.json",
    ]

    data_file = None
    for p in json_paths:
        if p.exists():
            data_file = p
            break

    if len(sys.argv) > 1:
        data_file = Path(sys.argv[1])

    if data_file and data_file.exists():
        print(f"Loading: {data_file}")
        engine = InterviewIntelligence()
        engine.load_json(str(data_file))
        engine.calculate()

        # Print state summary
        print(engine.get_state_summary())

        # Generate a sample brief for a hypothetical next interview
        print("\n" + "=" * 60)
        print("SAMPLE BRIEF: Next L2/OC interview at SAPPI")
        print("=" * 60)
        sample = {
            "num": 14,
            "name": "Sample Manager",
            "title": "Production Manager",
            "company": "SAPPI",
            "type": "Decision-Maker",
            "q_layer": "L2",
            "q_object": "OC",
            "q_stack": "Sa",
            "hypothesis": "Standard hypotheses",
            "questions": "Standard questions",
        }
        brief = engine.generate_brief(sample)
        print(f"\nMISSION:\n{brief['mission']}")
        print(f"\nCOMPOUND QUESTIONS ({len(brief['compound_questions'])}):")
        for i, q in enumerate(brief["compound_questions"], 1):
            print(f"  Q{i}. {q}")
        print(f"\nEQUIPMENT CHECKLIST ({len(brief['equipment_checklist'])} items):")
        for eq in brief["equipment_checklist"][:5]:
            print(f"  [{eq['priority']}] {eq['name']} "
                  f"({eq['mentions']} mentions, {eq.get('avg_cost_per_event', '?')}/event "
                  f"× {eq.get('avg_frequency', '?')} = {eq.get('avg_annual', '?')})")
        print(f"\nUPDATED HYPOTHESES:")
        for h in brief["updated_hypotheses"]:
            print(f"  {h}")
        print(f"\nVP SUMMARY:")
        for vp in brief["vp_summary"]:
            print(f"  {vp}")
    else:
        print("Usage: python interview_intelligence.py [database.json]")
