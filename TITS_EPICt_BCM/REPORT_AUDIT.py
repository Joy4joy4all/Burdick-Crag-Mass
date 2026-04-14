# -*- coding: utf-8 -*-
"""
DOC READER AI REPORT AUDIT — What's Working, What's Broken, What's Missing
=============================================================================
C:\\TITS\\TITS_Production\\gibush_epic\\REPORT_AUDIT.py

Reviewed 3 Validation AI reports + JSON summaries against test_intelligence.py
and substrate_class_profile.py capabilities.
"""

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  PART 1: WHAT THE REPORTS SHOW TODAY                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Current AI Report has 7 sections:
#   1. Test Run Summary (results, hypotheses, action items) — passthrough from .docx
#   2. Equipment Discussed — from checkbox parsing
#   3. Cost Data Captured — from cost table parsing
#   4. Experiment Answers — Q&A pairs
#   5. Pain Indicators — keyword extraction
#   6. Metrics: This vs Previous — equipment count avg, completeness score
#   7. Genesis Intelligence Context — hypothesis % from genesis_intel passthrough


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  PART 2: PROBLEMS FOUND IN THE 3 REPORTS                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

PROBLEMS = {
    "P1_FERREL_UNFILLED": {
        "report": "AI_Report_Test Run_7_Ferrel_Fowler",
        "problem": "Results = '[FILL DURING TEST]', Action = '[FILL AFTER TEST]'",
        "cause": "Doc reader processed an UNFILLED template. is_completed check passed "
                 "because hypothesis_validation text exists (it was pre-populated in template).",
        "impact": "Garbage in, garbage out. This 'test_run' pollutes the database "
                  "with placeholder text that keyword scanners treat as real data.",
        "fix": "is_completed should check that results != placeholder text. "
               "Add PLACEHOLDER_STRINGS = ['[FILL DURING TEST]', '[FILL AFTER TEST]'] "
               "and reject if results matches any.",
    },

    "P2_HYPOTHESES_FROZEN": {
        "report": "ALL THREE",
        "problem": "Hypothesis percentages are IDENTICAL in Ferrel (#7) and Tanner (#11) reports:\n"
                   "  Manual Detection: 95%, True Cost: 67%, Capital Investment: 98%\n"
                   "  These should be DIFFERENT because Tanner's test_run changed the evidence.",
        "cause": "genesis_intel is loaded ONCE from _load_genesis_intelligence() at template gen time. "
                 "The report just displays whatever genesis_intel had. It does NOT recalculate "
                 "AFTER incorporating this test_run's new data.",
        "impact": "Every report shows the BEFORE state. You never see the AFTER state — "
                  "the whole point of tracking hypothesis confidence over time.",
        "fix": "After processing test_run, call test_intelligence.py.calculate() "
               "with the UPDATED database (including this new test). "
               "Report should show BEFORE vs AFTER delta.",
    },

    "P3_TANNER_EQUIPMENT_ZERO": {
        "report": "AI_Report_Test Run_11_Tanner_White",
        "problem": "equipment_discussed = [] (0 items) but cost_data has 3 items "
                   "(Press Felts, Press Roll, Fourdrinier Wire).",
        "cause": "PacketParser only looks at equipment CHECKBOXES (marked with ☐/☑). "
                 "Tanner's test_run discussed equipment in RESULTS TEXT and COST TABLE "
                 "but didn't check the checkbox list. Parser missed them.",
        "impact": "Equipment damage ranking never sees Tanner's paper machine equipment. "
                  "Those items don't exist in substrate_config_chip.json — they're paper machine "
                  "equipment that should be in a separate config.",
        "fix": "Two fixes: (1) Parser should extract equipment from cost_data table too. "
               "(2) Paper machine equipment now exists in substrate_config (v3.0.0 expansion) "
               "so future templates will have those checkboxes.",
    },

    "P4_COST_DATA_STRINGS": {
        "report": "AI_Report_Test Run_11_Tanner_White",
        "problem": "Cost data stored as strings:\n"
                   "  Annual Damage = '$$15,000 (est per felt)'\n"
                   "  Failure Freq = 'Holes from pitch'\n"
                   "These are NOTES, not numbers.",
        "cause": "PacketParser._extract_cost_table() reads the raw cell text. "
                 "No numeric extraction. Passes strings through to JSON summary.",
        "impact": "test_intelligence.py damage_score calculation chokes on strings. "
                  "Dollar calibration sees $0 total because nothing parses to float.",
        "fix": "Extract numeric values from cost strings. "
               "Already handled in knowledge_extractor.py fix (cost_val float conversion). "
               "Need same treatment in PacketParser cost extraction.",
    },

    "P5_NO_COMPOUND_INTELLIGENCE": {
        "report": "ALL THREE",
        "problem": "Section 7 shows genesis_intel passthrough — static hypothesis %. "
                   "Missing: VP confidence, equipment damage ranking, cube density, "
                   "budget signals, contradictions, dollar calibration.",
        "cause": "ReportGenerator.generate() only uses genesis_intel dict from "
                 "_load_genesis_intelligence() which reads a static JSON file. "
                 "test_intelligence.py compound state never wired to reports.",
        "impact": "Reports don't show the REAL intelligence state. "
                  "No VP tracking, no equipment priority, no cube gaps, no contradictions.",
        "fix": "Wire test_intelligence.py into ReportGenerator. "
               "Report Section 7 becomes compound intelligence dashboard.",
    },
}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  PART 3: WHAT'S MISSING — SHOULD GENERATE PER TEST                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

MISSING_PER_TEST = {
    "M1_VP_DELTA": {
        "what": "Value Proposition confidence BEFORE vs AFTER this test_run",
        "example": "VP1 Damage Prevention: 80% → 95% (+15%) ← this test_run VALIDATED\n"
                   "VP4 Chemical Optimization: 33% → 33% (unchanged) ← not discussed\n"
                   "VP6 Pitch Contamination: 33% → 50% (+17%) ← Tanner's pitch evidence",
        "source": "test_intelligence.py calculate() run twice: "
                  "once WITHOUT this test_run, once WITH.",
        "priority": "HIGH — this is the compound interest visible to the researcher",
    },

    "M2_HYPOTHESIS_DELTA": {
        "what": "Hypothesis status BEFORE vs AFTER",
        "example": "H3 Modern Equipment Fails: TESTING (66%) → VALIDATED (100%) ← Ferrel confirmed\n"
                   "H4 Operator Senses: UNTESTED (0%) → UNTESTED (0%) ← still no data",
        "source": "test_intelligence.py hypotheses section",
        "priority": "HIGH — BCM requires tracking hypothesis evolution",
    },

    "M3_EQUIPMENT_RANKING_DELTA": {
        "what": "Equipment damage ranking shift after this test_run",
        "example": "BEFORE: #1 CTS Rollers ($160K/yr), #2 Screen Baskets ($45K/yr)\n"
                   "AFTER:  #1 Chipper Knives ($200K/yr) ← NEW from Ferrel, #2 CTS Rollers",
        "source": "test_intelligence.py equipment_ranked",
        "priority": "MEDIUM — shows how priority list evolves",
    },

    "M4_CUBE_DENSITY_DELTA": {
        "what": "Q-Cube coverage before vs after",
        "example": "BEFORE: L1=2, L2=5, L3=2 | Gaps: [L1,OA], [L3,OB]\n"
                   "AFTER:  L1=2, L2=6, L3=2 | Gap filled: none | Still need: [L1,OA]",
        "source": "test_intelligence.py cube_density",
        "priority": "MEDIUM — shows test_run targeting effectiveness",
    },

    "M5_BMC_IMPACT": {
        "what": "Which BMC blocks this test_run provided evidence for",
        "example": "Ferrel Fowler impacted:\n"
                   "  [Substrate Classs] L2 Decision-Maker at chip producer ← NEW segment type\n"
                   "  [Value Propositions] VP1 Damage Prevention ← rocks destroy knives 1x/day\n"
                   "  [Revenue Streams] no new evidence\n"
                   "  [Channels] direct outreach to foremen works ← evidence for sales channel",
        "source": "Map test_run keywords to BMC blocks. "
                  "substrate_class_profile.py already has keyword dictionaries per segment.",
        "priority": "HIGH — BCM panel wants to see BMC evolution per test",
    },

    "M6_CUSTOMER_SEGMENT_UPDATE": {
        "what": "Customer segment profile cumulative update",
        "example": "After Ferrel (#7):\n"
                   "  L2 Decision-Maker evidence: 6 tests (was 5)\n"
                   "  NEW keyword captured: 'general foreman' → L2 subcategory\n"
                   "  NEW company type: 'chip producer' (vs pulp mill, paper mill)\n"
                   "  Budget signal: no AMO path mentioned (BLOCKER signal)",
        "source": "test_intelligence.py cube_density + substrate_class_profile.py",
        "priority": "HIGH — segment definition should sharpen with each test",
    },

    "M7_CONTRADICTION_DETECTION": {
        "what": "New contradictions introduced by this test_run",
        "example": "Ferrel says 'no one cares in the woods' (operator apathy)\n"
                   "Rocky #5 said 'operators sense problems' (operator awareness)\n"
                   "→ CONTRADICTION: Operator awareness varies by mill position\n"
                   "→ NEXT TEST should probe: 'woods crew vs mill crew awareness'",
        "source": "test_intelligence.py contradiction detection",
        "priority": "MEDIUM — drives next test_run targeting",
    },

    "M8_PROVENANCE_STAMP": {
        "what": "Intelligence state snapshot at time of template generation",
        "example": "Template generated: 2026-02-15 14:00\n"
                   "Intelligence state at generation:\n"
                   "  VP1: 80%, VP2: 66%, VP3: 100%\n"
                   "  Equipment #1: CTS Rollers\n"
                   "  Cube gaps: [L1,OA], [L3,OB]\n"
                   "  Total damage documented: $460K\n"
                   "\n"
                   "Current intelligence state (after this test_run processed):\n"
                   "  VP1: 95% (+15%), VP2: 66% (unchanged), VP3: 100%\n"
                   "  Equipment #1: Chipper Knives (CHANGED from CTS Rollers)\n"
                   "  Cube gaps: [L1,OA] (filled [L3,OB])\n"
                   "  Total damage documented: $660K (+$200K)",
        "source": "Save intelligence snapshot to JSON when template is generated. "
                  "Compare against current state when report is generated.",
        "priority": "LOW — nice-to-have audit trail, not blocking",
    },
}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  PART 4: PROPOSED NEW REPORT STRUCTURE                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Current: 7 sections (basic passthrough)
# Proposed: 12 sections (compound intelligence)

NEW_REPORT_STRUCTURE = """
================================================================================
COMPOUND INTELLIGENCE REPORT — Test Run #7: Ferrel Fowler
Generated: 2026-02-16 04:17:36
Company: Coastal Fiber L.L.C., Oregon
Cube Position: [L2, OC, Sa] — Manager at Downstream Receiver
================================================================================

SECTION 1: TEST SUMMARY
  (same as current — results, hypotheses, action)

SECTION 2: EQUIPMENT DISCUSSED + DAMAGE DATA
  (merged equipment + costs, with new schema: $/event × events/yr = annual)

SECTION 3: EXPERIMENT ANSWERS
  (same as current)

SECTION 4: COMPLETENESS SCORE
  (same as current — 7-point checklist)

SECTION 5: VALUE PROPOSITION DELTA  ← NEW
  VP1 Damage Prevention:    80% → 95% (+15%)  ← THIS TEST VALIDATED
  VP2 Planned Maintenance:  66% → 66% (unchanged)
  VP3 Operator Visibility:  100% (already validated)
  VP4 Chemical Optimization: 33% → 33% (unchanged)
  VP5 Supplier Accountability: 66% → 66% (unchanged)
  VP6 Pitch Contamination:  33% → 33% (unchanged)

SECTION 6: HYPOTHESIS DELTA  ← NEW
  H1 Manual Detection Fails:   VALIDATED (100%) — no change
  H2 Cost Understated:          VALIDATED (100%) — no change
  H3 Modern Equipment Fails:    TESTING → VALIDATED ← Ferrel: "rocks destroy knives 1x/day"
  H4 Operator Senses:           UNTESTED → TESTING  ← Ferrel: "no one cares in the woods"
  H5 Blow Line Blind Spot:      VALIDATED (100%) — no change

SECTION 7: EQUIPMENT DAMAGE RANKING DELTA  ← NEW
  BEFORE                          AFTER
  #1 CTS Rollers ($160K/yr)       #1 Chipper Knives ($200K/yr) ← NEW
  #2 Screen Baskets ($45K/yr)     #2 CTS Rollers ($160K/yr)
  #3 Feed Screw ($67K/yr)         #3 Screen Baskets ($45K/yr)

  Total documented damage: $460K → $660K (+$200K from this test_run)

SECTION 8: CUBE DENSITY  ← NEW
  Layer distribution: L1=2, L2=6(+1), L3=2
  Gaps remaining: [L1,OA], [L3,OB]
  This test_run: L2 at OC — confirms buyer segment dominance

SECTION 9: BMC IMPACT  ← NEW
  Blocks this test_run provided evidence for:
  [Substrate Classs] +1 L2 Decision-Maker at chip producer
  [Value Propositions] VP1 Damage Prevention — rocks destroy knives daily
  [Key Activities] manual chipper knife replacement — pain point
  [Cost Structure] no new $ data (MISSED — follow up)

SECTION 10: CUSTOMER SEGMENT UPDATE  ← NEW
  L2 evidence now: 6 tests (was 5)
  New subcategory: "chip producer foreman" (distinct from "pulp mill manager")
  Budget signal: NO AMO path mentioned — potential blocker
  Recommended: next L2 test_run should probe budget path

SECTION 11: CONTRADICTIONS  ← NEW
  NEW: Ferrel "no one cares in the woods" vs Rocky "operators sense problems"
  → Operator awareness varies by position (woods vs mill floor)
  → NEXT TEST SHOULD ASK: "Do woods crews care about chip quality?"

SECTION 12: NEXT TEST RECOMMENDATIONS  ← NEW
  Priority target: [L1, OA] — zero tests (critical gap)
  VP needing data: VP4 Chemical Optimization (33%, need 2 more)
  Dollar gap: $0 captured from chip producers — Ferrel didn't give $
  Contradiction to resolve: operator awareness woods vs mill

================================================================================
"""


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  PART 5: BUILD ORDER                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

BUILD_ORDER = [
    "STEP 1: Fix is_completed to reject placeholder text (30 min)",
    "   → Prevents Ferrel-type garbage entries",
    "",
    "STEP 2: Wire test_intelligence.py into doc_reader.py (1 hr)",
    "   → calculate() BEFORE and AFTER this test_run",
    "   → Pass both states to ReportGenerator",
    "",
    "STEP 3: Rewrite ReportGenerator.generate() with 12-section structure (2 hr)",
    "   → VP delta, hypothesis delta, equipment ranking delta",
    "   → Cube density, BMC impact, customer segment, contradictions",
    "",
    "STEP 4: Wire substrate_class_profile.py cumulative update (1 hr)",
    "   → After each test, regenerate segment profile",
    "   → Include in report Section 10",
    "",
    "STEP 5: BMC block impact mapping (1 hr)",
    "   → Map test_run keywords to BMC blocks",
    "   → Include in report Section 9",
    "",
    "STEP 6: Auto-generate updated BMC PPTX if significant change (1 hr)",
    "   → If VP status changes or new segment type, flag for BMC update",
    "   → Optional auto-regenerate BMC v4.x",
]
