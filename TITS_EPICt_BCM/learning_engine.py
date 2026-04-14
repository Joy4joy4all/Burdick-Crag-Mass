# -*- coding: utf-8 -*-
"""
learning_engine.py — ML Intelligence Engine for Learning Assistant

Extracts patterns, generates questions, and tracks hypotheses
using real sklearn ML (TF-IDF, cosine similarity, clustering)
plus doctoral_analyzer and knowledge_extractor when available.

Zero hardcoded keywords. Everything derived from actual test data.

Part of GIBUSH FUSION Test Collector platform.
"""

import numpy as np
from collections import Counter
from typing import List, Dict, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Optional engines — graceful fallback if not present
try:
    from doctoral_analyzer import DoctoralAnalyzer
    DOCTORAL_AVAILABLE = True
except ImportError:
    DOCTORAL_AVAILABLE = False

try:
    from knowledge_extractor import KnowledgeExtractor
    KNOWLEDGE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_AVAILABLE = False


# ============================================================================
# HELPERS
# ============================================================================

def _get_all_text(test_run) -> str:
    """Combine ALL test_run text fields into one searchable corpus."""
    parts = []
    for field in ('results', 'experiments', 'hypotheses', 'action_iterate'):
        val = getattr(test_run, field, '')
        if val:
            parts.append(val)
    if hasattr(test_run, 'substrate_impacts') and test_run.substrate_impacts:
        for impact in test_run.substrate_impacts:
            notes = impact.get('notes', '')
            if notes:
                parts.append(notes)
    return ' '.join(parts)


def _safe_float(val, default=0.0) -> float:
    """Coerce any value to float safely."""
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


# ============================================================================
# PATTERN DETECTION — Patterns Detected tab
# ============================================================================

def detect_patterns(database, get_active_project=None) -> str:
    """
    Detect cross-test patterns using real ML:
    - TF-IDF + cosine similarity for resonance pairs
    - Knowledge extractor for entity co-occurrence
    - 10-lens coverage analysis
    
    Returns formatted string for display.
    """
    output = []
    output.append("=" * 80)
    output.append("CROSS-TEST PATTERNS (ML-Detected)")
    output.append("=" * 80)
    output.append("")

    tests = database.test_runs
    if len(tests) < 2:
        output.append("Need at least 2 tests for pattern detection.")
        return "\n".join(output)

    corpus = [_get_all_text(i) for i in test_runs]
    corpus = [t if t.strip() else "(no data)" for t in corpus]

    # ── 1. TF-IDF RESONANCE ──
    try:
        vectorizer = TfidfVectorizer(
            max_features=200, stop_words='english',
            min_df=1, max_df=0.95, ngram_range=(1, 2)
        )
        tfidf = vectorizer.fit_transform(corpus)
        sim_matrix = cosine_similarity(tfidf)
        feature_names = vectorizer.get_feature_names_out()

        output.append("PATTERN: TEST RESONANCE (cosine similarity)")
        output.append("-" * 80)

        pairs = []
        for i in range(len(tests)):
            for j in range(i + 1, len(tests)):
                pairs.append((sim_matrix[i, j], i, j))
        pairs.sort(reverse=True)

        for sim, i, j in pairs[:5]:
            if sim > 0.05:
                output.append(
                    f"  ⬢ #{test_runs[i].test_num} ({test_runs[i].person}) ↔ "
                    f"#{test_runs[j].test_num} ({test_runs[j].person})  "
                    f"sim={sim:.3f}"
                )
                vec_i = tfidf[i].toarray().flatten()
                vec_j = tfidf[j].toarray().flatten()
                shared_scores = np.minimum(vec_i, vec_j)
                top_shared = np.argsort(shared_scores)[-5:][::-1]
                shared_terms = [feature_names[k] for k in top_shared if shared_scores[k] > 0]
                if shared_terms:
                    output.append(f"    Shared themes: {', '.join(shared_terms)}")
        output.append("")

        # Corpus-wide dominant themes
        output.append("PATTERN: DOMINANT THEMES (TF-IDF corpus-wide)")
        output.append("-" * 80)

        corpus_tfidf = tfidf.mean(axis=0).A1
        top_indices = np.argsort(corpus_tfidf)[-15:][::-1]

        for idx in top_indices:
            score = corpus_tfidf[idx]
            if score > 0.01:
                term = feature_names[idx]
                doc_freq = sum(1 for row in range(tfidf.shape[0]) if tfidf[row, idx] > 0)
                output.append(
                    f"  ⬢ \"{term}\"  weight={score:.3f}  "
                    f"({doc_freq}/{len(tests)} tests)"
                )
        output.append("")

    except Exception as e:
        output.append(f"  TF-IDF analysis: {e}")
        output.append("")

    # ── 2. EQUIPMENT CO-OCCURRENCE ──
    equipment_costs = {}
    for test_entry in test_runs:
        if hasattr(test_run, 'substrate_impacts') and test_run.substrate_impacts:
            for impact in test_run.substrate_impacts:
                equip_name = impact.get('equipment', '')
                cost = _safe_float(impact.get('cost', 0))
                if equip_name:
                    if equip_name not in equipment_costs:
                        equipment_costs[equip_name] = {
                            'total_cost': 0.0, 'tests': [], 'count': 0
                        }
                    equipment_costs[equip_name]['total_cost'] += cost
                    equipment_costs[equip_name]['tests'].append(
                        f"#{test_run.test_num}")
                    equipment_costs[equip_name]['count'] += 1

    if equipment_costs:
        output.append("PATTERN: EQUIPMENT IMPACT ACCUMULATION")
        output.append("-" * 80)
        sorted_eq = sorted(equipment_costs.items(),
                           key=lambda x: x[1]['total_cost'], reverse=True)
        total_all = 0.0
        for equip, data in sorted_eq[:8]:
            output.append(f"  ⬢ {equip}")
            output.append(
                f"    Total: ${data['total_cost']:,.0f}/yr  "
                f"Sources: {', '.join(data['tests'])} ({data['count']}x)"
            )
            total_all += data['total_cost']
        output.append(
            f"\n  TOTAL QUANTIFIED: ${total_all:,.0f}/year "
            f"across {len(equipment_costs)} equipment types"
        )
        output.append("")

    # ── 3. KNOWLEDGE EXTRACTOR SIGNALS ──
    if KNOWLEDGE_AVAILABLE:
        try:
            extractor = KnowledgeExtractor()
            signal_counts = {}

            for test_entry in test_runs:
                text = _get_all_text(test_run)
                if not text.strip():
                    continue
                entities = extractor.extract(text)
                for category, items in entities.items():
                    if items:
                        signal_counts[category] = signal_counts.get(category, 0) + len(items)

            if signal_counts:
                output.append("PATTERN: KNOWLEDGE EXTRACTION SIGNALS")
                output.append("-" * 80)
                for cat, count in sorted(signal_counts.items(), key=lambda x: -x[1]):
                    bar = "█" * min(count, 20)
                    output.append(f"  {cat:25s} {bar} ({count} signals)")
                output.append("")
        except Exception as e:
            output.append(f"  Knowledge extraction: {e}")
            output.append("")

    # ── 4. 10-LENS COVERAGE ──
    _append_lens_coverage(output, tests)

    return "\n".join(output)


# ============================================================================
# QUESTION GENERATION — Recommended Questions tab
# ============================================================================

def generate_questions(database, test_plan: list,
                       get_active_project=None) -> str:
    """
    Generate recommended questions using real ML:
    - Doctoral analyzer info-gain questions
    - TF-IDF gap analysis for under-explored terms
    - 10-lens blind spot targeting
    - Per-test_run prep from similarity matching
    
    Returns formatted string for display.
    """
    output = []
    output.append("=" * 80)
    output.append("RECOMMENDED QUESTIONS (ML-Generated)")
    output.append("=" * 80)
    output.append("")

    tests = database.test_runs
    if not test_runs:
        output.append("No tests to analyze.")
        return "\n".join(output)

    # ── Completion filter: match by number AND by name ──
    # Bug fix: same person can have different numbers across Baseline/Validation/SPINE.
    # Ray might be #18 in plan but #57 in database. Match both ways.
    completed_nums = {i.test_num for i in test_runs}
    completed_names = set()
    for i in test_runs:
        if hasattr(i, 'script_name') and i.person:
            # Normalize: lowercase, strip quotes/punctuation, collapse whitespace
            import re as _re
            name = _re.sub(r'["\'\(\)\[\]]', '', i.person.strip().lower())
            name = ' '.join(name.split())  # collapse whitespace
            completed_names.add(name)
            # Also add last-name for cross-reference matches
            parts = name.split()
            if len(parts) >= 2:
                completed_names.add(parts[-1])   # last name only (first name too aggressive)

    def _normalize_name(raw: str) -> str:
        """Strip quotes, parens, collapse whitespace, lowercase."""
        import re as _re
        clean = _re.sub(r'["\'\(\)\[\]]', '', raw.strip().lower())
        return ' '.join(clean.split())

    def _is_completed(plan_entry):
        """Check if plan entry is completed — by name (primary)."""
        plan_name = _normalize_name(plan_entry.get('name', ''))
        if plan_name in completed_names:
            return True
        # Check last name match (more unique than first name)
        parts = plan_name.split()
        if len(parts) >= 2:
            if parts[-1] in completed_names:
                return True
        return False

    pending = [ip for ip in test_plan if not _is_completed(ip)]
    done_count = len(test_plan) - len(pending)

    # Progress header
    output.append(f"TEST PROGRESS: {done_count}/{len(test_plan)} completed, "
                  f"{len(pending)} remaining")
    output.append("=" * 80)
    output.append("")

    # ── 1. DOCTORAL ANALYZER ──
    if DOCTORAL_AVAILABLE:
        try:
            project = get_active_project() if get_active_project else "BCM_SUBSTRATE"
            analyzer = DoctoralAnalyzer(project=project)
            doctoral_qs = analyzer.generate_adaptive_questions(database, tests)

            if doctoral_qs:
                output.append("INFO-GAIN QUESTIONS (doctoral_analyzer — Shannon entropy)")
                output.append("-" * 80)
                output.append("Ranked by information gain — highest uncertainty reduction first:")
                output.append("")

                for i, q in enumerate(doctoral_qs[:10], 1):
                    if isinstance(q, dict):
                        ig = _safe_float(q.get('information_gain', 0))
                        question = q.get('question', '')
                        priority = q.get('priority', '')
                        rationale = q.get('rationale', '')
                    else:
                        ig = _safe_float(getattr(q, 'information_gain', 0))
                        question = getattr(q, 'question', '')
                        priority = getattr(q, 'priority', '')
                        rationale = getattr(q, 'rationale', '')

                    output.append(f"  {i}. [{priority}] IG={ig:.3f}bits")
                    output.append(f"     {question}")
                    if rationale:
                        output.append(f"     Why: {rationale}")
                    output.append("")
                output.append("")
        except Exception as e:
            output.append(f"  Doctoral analyzer: {e}")
            output.append("")

    # ── 2. TF-IDF GAP ANALYSIS ──
    try:
        corpus = [_get_all_text(i) for i in test_runs]
        corpus = [t if t.strip() else "(no data)" for t in corpus]

        vectorizer = TfidfVectorizer(
            max_features=100, stop_words='english',
            min_df=1, max_df=0.95, ngram_range=(1, 2)
        )
        tfidf = vectorizer.fit_transform(corpus)
        feature_names = vectorizer.get_feature_names_out()

        output.append("VALIDATION GAPS (high-signal, low-coverage terms)")
        output.append("-" * 80)
        output.append("Terms with strong weight but few sources — need more test_runs:")
        output.append("")

        gaps = []
        for idx, term in enumerate(feature_names):
            avg_weight = tfidf[:, idx].mean()
            doc_count = sum(1 for row in range(tfidf.shape[0]) if tfidf[row, idx] > 0)
            if avg_weight > 0.02 and doc_count < max(2, len(tests) * 0.4):
                gaps.append((avg_weight, doc_count, term))

        gaps.sort(reverse=True)

        for weight, count, term in gaps[:8]:
            output.append(
                f"  ⬢ \"{term}\" — weight={weight:.3f}, "
                f"only {count}/{len(tests)} test_runs"
            )
            output.append(
                f"    → Ask next test_source: "
                f"\"What is your experience with {term}?\""
            )
            output.append("")

        if not gaps:
            output.append("  Good coverage — no major single-source terms detected.")
            output.append("")

    except Exception as e:
        output.append(f"  TF-IDF gap analysis: {e}")
        output.append("")

    # ── 3. 10-LENS BLIND SPOTS ──
    _append_lens_blind_spots(output, tests)

    # ── 4. ALL REMAINING TESTS ──
    if pending:
        output.append(f"ALL REMAINING TESTS ({len(pending)} of {len(test_plan)})")
        output.append("-" * 80)

        for p in pending:
            output.append(
                f"\n  #{p['num']}: {p['name']} ({p['source_version']}) — {p['type']}"
            )

            best_sim = None
            for completed in test_runs:
                if (completed.company and p.get('source_version') and
                    completed.company.lower()[:4] == p['source_version'].lower()[:4]):
                    best_sim = completed
                    break

            if best_sim:
                output.append(
                    f"    Similar completed: #{best_sim.test_num} "
                    f"({best_sim.person}, {best_sim.company})"
                )
                output.append(
                    f"    → Validate/contradict what #{best_sim.test_num} said"
                )
            else:
                output.append(
                    f"    No same-company tests yet — exploratory mode"
                )

            if p.get('questions'):
                qs = [q.strip() for q in p['questions'].split('\n') if q.strip()]
                if qs:
                    output.append(f"    Planned: {qs[0][:80]}...")

        output.append("")

    return "\n".join(output)


# ============================================================================
# HYPOTHESIS TRACKING — Updated Hypotheses tab
# ============================================================================

def track_hypotheses(database, test_plan: list) -> str:
    """
    Track hypothesis validation using Bayesian evidence scoring:
    - TF-IDF + cosine similarity per hypothesis vs test_runs
    - Beta(α,β) confidence model
    - Pulls hypotheses from plan + completed tests (not hardcoded)
    
    Returns formatted string for display.
    """
    output = []
    output.append("=" * 80)
    output.append("HYPOTHESIS VALIDATION (Bayesian Evidence)")
    output.append("=" * 80)
    output.append("")

    tests = database.test_runs
    if not test_runs:
        output.append("No tests to evaluate hypotheses against.")
        return "\n".join(output)

    # ── 1. EXTRACT UNIQUE HYPOTHESES ──
    hypotheses = {}

    for plan in test_plan:
        h_text = plan.get('hypothesis', '').strip()
        if h_text and len(h_text) > 10:
            h_key = h_text[:80]
            if h_key not in hypotheses:
                hypotheses[h_key] = {
                    'text': h_text,
                    'planned_for': [],
                    'tested_by': [],
                }
            hypotheses[h_key]['planned_for'].append(plan['num'])

    for test_entry in test_runs:
        if test_run.hypotheses and len(test_run.hypotheses.strip()) > 10:
            h_text = test_run.hypotheses.strip()
            h_key = h_text[:80]
            if h_key not in hypotheses:
                hypotheses[h_key] = {
                    'text': h_text,
                    'planned_for': [],
                    'tested_by': [],
                }
            hypotheses[h_key]['tested_by'].append(test_run.person)

    if not hypotheses:
        output.append("No hypotheses found in test_run plan or completed tests.")
        output.append("Add hypotheses to your test_run plan Excel to enable tracking.")
        return "\n".join(output)

    # ── 2. TF-IDF SCORING ──
    sim_matrix = None
    try:
        corpus = [_get_all_text(i) for i in test_runs]
        corpus = [t if t.strip() else "(no data)" for t in corpus]

        h_texts = [h['text'] for h in hypotheses.values()]
        all_docs = corpus + h_texts

        vectorizer = TfidfVectorizer(
            max_features=150, stop_words='english',
            min_df=1, max_df=0.95
        )
        tfidf = vectorizer.fit_transform(all_docs)

        test_run_vecs = tfidf[:len(corpus)]
        hypothesis_vecs = tfidf[len(corpus):]

        sim_matrix = cosine_similarity(hypothesis_vecs, test_run_vecs)

    except Exception as e:
        output.append(f"  (TF-IDF scoring unavailable: {e})")
        output.append("")

    # ── 3. DISPLAY HYPOTHESIS STATUS ──
    for h_idx, (h_key, h_data) in enumerate(hypotheses.items()):
        output.append(f"HYPOTHESIS: {h_data['text'][:120]}")
        output.append("-" * 80)

        planned = h_data['planned_for']
        tested = h_data['tested_by']

        if planned:
            output.append(
                f"  Planned for: {', '.join(f'#{n}' for n in planned[:6])}"
            )
        if tested:
            output.append(
                f"  Tested by: {', '.join(str(n) for n in tested[:6])}"
            )

        if sim_matrix is not None and h_idx < sim_matrix.shape[0]:
            sims = sim_matrix[h_idx]

            strong = sum(1 for s in sims if s > 0.15)
            moderate = sum(1 for s in sims if 0.05 < s <= 0.15)
            weak = sum(1 for s in sims if s <= 0.05)

            max_sim = float(np.max(sims))

            # Bayesian Beta confidence
            alpha = strong + 1
            beta_val = weak + 1
            confidence = alpha / (alpha + beta_val)

            if confidence > 0.7 and strong >= 3:
                status = "✓ VALIDATED"
            elif confidence > 0.5:
                status = "◐ PARTIALLY VALIDATED"
            elif confidence < 0.3 and len(tests) >= 3:
                status = "✗ WEAKENED — consider pivot"
            else:
                status = "? INSUFFICIENT DATA"

            bar = "█" * int(confidence * 20) + "░" * (20 - int(confidence * 20))
            output.append(f"  Status: {status}")
            output.append(
                f"  Confidence: [{bar}] {confidence:.0%}  "
                f"(Beta({alpha},{beta_val}))"
            )
            output.append(
                f"  Evidence: {strong} strong, {moderate} moderate, "
                f"{weak} weak  (max_sim={max_sim:.3f})"
            )

            top_support = np.argsort(sims)[-3:][::-1]
            for idx in top_support:
                if sims[idx] > 0.05:
                    iv = test_runs[idx]
                    output.append(
                        f"    #{iv.test_num} ({iv.person}, "
                        f"{iv.company}) sim={sims[idx]:.3f}"
                    )
        else:
            output.append(f"  Status: ? — no TF-IDF scoring available")

        if tested:
            tested_ivs = [i for i in tests if i.person in tested]
            if tested_ivs:
                scores = [_safe_float(i.synergy_score) for i in tested_ivs]
                avg_syn = np.mean(scores)
                output.append(f"  Avg synergy score: {avg_syn:.3f}")

        output.append("")

    # ── 4. SUMMARY ──
    output.append("HYPOTHESIS TRACKING SUMMARY")
    output.append("-" * 80)
    output.append(f"  Total hypotheses tracked: {len(hypotheses)}")
    output.append(f"  Completed test_runs: {len(tests)}")

    tested_count = sum(1 for h in hypotheses.values() if h['tested_by'])
    output.append(f"  Hypotheses with evidence: {tested_count}/{len(hypotheses)}")

    untested = [h['text'][:60] for h in hypotheses.values() if not h['tested_by']]
    if untested:
        output.append(f"\n  ⚠️ Untested hypotheses ({len(untested)}):")
        for h in untested[:5]:
            output.append(f"    → {h}...")
    output.append("")

    return "\n".join(output)


# ============================================================================
# SHARED HELPERS
# ============================================================================

LENS_ATTRS = {
    'q_layer': 'Layer (Who)',
    'q_object': 'Object (What)',
    'q_stack': 'Stack (Where)',
    'q_awareness': 'Awareness',
    'q_evidence': 'Evidence Type',
    'q_timehorizon': 'Time Horizon',
    'q_cascade': 'Cascade Depth',
    'q_normalization': 'Normalization',
    'q_counterflow': 'Counter-Flow',
    'q_tribalknowledge': 'Tribal Knowledge',
}

LENS_QUESTIONS = {
    'q_cascade': "How many handoffs does material go through from forest to your process?",
    'q_normalization': "Are there problems your team has accepted as 'just part of the job'?",
    'q_counterflow': "What information about your material do you wish you had from upstream?",
    'q_tribalknowledge': "What would be lost if your most experienced operator retired tomorrow?",
    'q_awareness': "How aware is management of this problem versus frontline workers?",
    'q_evidence': "Do you have documented data on this, or is it more experiential?",
    'q_timehorizon': "Is this a daily issue, seasonal, or has it been building for years?",
}


def _get_lens_values(tests, attr: str) -> list:
    """Get all lens values for a given attribute across tests."""
    vals = []
    for i in test_runs:
        v = getattr(i, attr, '')
        if attr == 'q_stack':
            if isinstance(v, list):
                vals.extend(v)
            elif v:
                vals.append(v)
        elif v:
            vals.append(v)
    return vals


def _append_lens_coverage(output: list, test_runs: list):
    """Append 10-lens coverage analysis to output."""
    output.append("PATTERN: 10-LENS HYPERCUBE COVERAGE")
    output.append("-" * 80)

    populated = 0
    for attr, label in LENS_ATTRS.items():
        vals = _get_lens_values(tests, attr)
        if vals:
            populated += 1
            counts = Counter(vals)
            top3 = counts.most_common(3)
            dist_str = ', '.join(f"{v}({c})" for v, c in top3)
            pct = len(vals) / len(tests) * 100
            output.append(f"  {label:20s} {pct:5.0f}% coverage  Top: {dist_str}")
        else:
            output.append(f"  {label:20s}   0% coverage  ⚠️ BLIND SPOT")

    output.append(f"\n  Coverage: {populated}/{len(LENS_ATTRS)} lenses populated")
    output.append("")


def _append_lens_blind_spots(output: list, test_runs: list):
    """Append lens blind spot questions to output."""
    blind = []
    for attr, label in LENS_ATTRS.items():
        if attr in ('q_layer', 'q_object', 'q_stack'):
            continue  # Foundation lenses — always filled by classification
        populated = sum(1 for i in tests if getattr(i, attr, ''))
        if populated < len(tests) * 0.3:
            blind.append((populated, label, attr))

    if blind:
        blind.sort()
        output.append("10-LENS BLIND SPOTS (need targeted questions)")
        output.append("-" * 80)

        for count, label, attr in blind:
            pct = count / len(tests) * 100 if tests else 0
            output.append(f"  ⚠️ {label}: {pct:.0f}% coverage ({count}/{len(tests)})")
            if attr in LENS_QUESTIONS:
                output.append(f"    → \"{LENS_QUESTIONS[attr]}\"")
            output.append("")
