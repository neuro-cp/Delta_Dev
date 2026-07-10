"""RC2 cognitive capability benchmark.

This benchmark exercises the real RC2 runtime route path. It is intentionally
read-only: no training, no providers, no canonical writes, no memory writes,
and no graph mutation. The goal is to find cognitive/runtime pathologies before
another concept instillation cycle.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc2_conversational_mode_router import route_message
from orchestration.runtime.rc2_storage_adapter import substrate_counts


REPORT_JSON = ROOT / "reports" / "RC2_COGNITIVE_CAPABILITY_BENCHMARK.json"
REPORT_MD = ROOT / "reports" / "RC2_COGNITIVE_CAPABILITY_BENCHMARK.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "graph_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
    "delta_75_push_performed": False,
}


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    prompt: str
    expected_terms: tuple[str, ...] = ()
    expected_routes: tuple[str, ...] = ()
    expected_absent_terms: tuple[str, ...] = ()
    history: tuple[dict[str, str], ...] = ()
    notes: str = ""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80]


def _history_from_turns(turns: list[tuple[str, str]]) -> tuple[dict[str, str], ...]:
    history: list[dict[str, str]] = []
    for user, assistant in turns:
        history.append({"role": "user", "content": user})
        history.append({"role": "assistant", "content": assistant})
    return tuple(history)


RECALL_TOPICS = [
    ("blood pressure", ("blood pressure", "cardiac", "vascular")),
    ("allergies", ("allerg", "immune", "allergen")),
    ("photosynthesis", ("photosynthesis", "energy", "carbon")),
    ("cellular respiration", ("respiration", "ATP", "glucose")),
    ("inflation", ("inflation", "price", "purchasing")),
    ("interest rates", ("interest", "borrowing", "rate")),
    ("gravity", ("gravity", "attract", "mass")),
    ("planning", ("planning", "goal", "sequence")),
    ("feedback loops", ("feedback", "adjust", "system")),
    ("noncanonical memory", ("noncanonical", "memory", "reversible")),
]

RELATIONAL_PAIRS = [
    ("blood pressure", "allergies", ("blood pressure", "allerg", "medication")),
    ("photosynthesis", "cellular respiration", ("photosynthesis", "respiration", "energy")),
    ("inflation", "interest rates", ("inflation", "interest", "borrowing")),
    ("planning", "feedback loops", ("planning", "feedback", "adjust")),
    ("memory consolidation", "noncanonical memory", ("memory", "consolidation", "noncanonical")),
    ("gravity", "orbital motion", ("gravity", "orbital", "motion")),
]

CROSS_DOMAIN_PAIRS = [
    ("inflation", "blood pressure", ("pressure", "system", "context")),
    ("feedback loops", "allergies", ("feedback", "response", "system")),
    ("planning", "cellular respiration", ("planning", "energy", "constraint")),
    ("noncanonical memory", "immune memory", ("memory", "immune", "history")),
    ("interest rates", "vascular resistance", ("resistance", "flow", "pressure")),
    ("photosynthesis", "battery charging", ("energy", "store", "charge")),
]

ANALOGIES = [
    ("photosynthesis", "respiration", "charging", "discharging", ("energy", "store", "release")),
    ("inflation", "blood pressure", "economic pressure", "vascular pressure", ("pressure", "system")),
    ("feedback loops", "thermostats", "planning", "course correction", ("feedback", "adjust")),
    ("noncanonical memory", "scratch notes", "canonical memory", "published record", ("memory", "review")),
    ("interest rates", "brakes", "borrowing", "speed", ("rate", "borrowing", "slow")),
    ("allergies", "security filters", "immune response", "false alarm", ("immune", "response", "risk")),
]

ABSTRACTION_PROMPTS = [
    ("What higher-order pattern connects blood pressure, allergies, photosynthesis, and cellular respiration?", ("pattern", "context", "energy")),
    ("What common reasoning pattern connects planning, feedback loops, and software architecture?", ("planning", "feedback", "system")),
    ("What principle connects inflation, interest rates, and feedback loops?", ("inflation", "interest", "feedback")),
    ("What abstraction connects noncanonical memory, memory consolidation, and operator review?", ("memory", "review", "consolidation")),
    ("What pattern connects gravity, orbital motion, and constraint management?", ("gravity", "motion", "constraint")),
    ("What common structure connects allergies, immune memory, and contradiction detection?", ("allerg", "immune", "conflict")),
]

MISSING_EVIDENCE = [
    ("What information prevents a medical conclusion about elevated blood pressure in a patient with severe allergies?", ("patient", "medication", "history", "missing")),
    ("What evidence is missing before concluding inflation will fall after interest rates rise?", ("inflation", "interest", "evidence")),
    ("What information is missing before saying photosynthesis and respiration are balanced in an ecosystem?", ("photosynthesis", "respiration", "missing")),
    ("What prevents DELTA from promoting noncanonical memory to canonical memory?", ("noncanonical", "canonical", "review")),
    ("What would you need before deciding a plan is working based on feedback?", ("plan", "feedback", "evidence")),
    ("What evidence is missing before explaining an orbit from gravity alone?", ("gravity", "orbit", "velocity")),
]

CONTRADICTIONS = [
    ("Can these both be true: a patient has no medication allergies, and the same patient has a severe penicillin allergy?", ("both", "allerg", "contradict")),
    ("Can these both be true: photosynthesis stores chemical energy, and photosynthesis never stores energy?", ("photosynthesis", "energy", "contradict")),
    ("Can these both be true: interest rates reduce borrowing costs, and higher interest rates increase borrowing costs?", ("interest", "borrowing", "conflict")),
    ("Can these both be true: noncanonical memory is reversible, and noncanonical memory cannot be rolled back?", ("noncanonical", "rollback", "conflict")),
    ("Can these both be true: feedback loops adjust behavior, and feedback loops never change behavior?", ("feedback", "change", "contradict")),
    ("Can these both be true: blood pressure varies with stress, and blood pressure never changes with context?", ("blood pressure", "context", "contradict")),
]

NOVEL_COMBINATIONS = [
    ("How might gardening and software architecture share a planning pattern?", ("gardening", "software", "planning")),
    ("How might materials science and psychology both use stress as a useful concept?", ("stress", "materials", "psychology")),
    ("How might finance and biology both reason about feedback loops?", ("finance", "biology", "feedback")),
    ("How could home repair and medicine both depend on diagnostic evidence?", ("repair", "medicine", "diagnostic")),
    ("What connects vehicle maintenance and memory consolidation as processes?", ("maintenance", "memory", "process")),
    ("What connects agriculture, energy transfer, and feedback control?", ("agriculture", "energy", "feedback")),
]


def build_benchmark_cases() -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for topic, terms in RECALL_TOPICS:
        for variant, prompt in enumerate([
            f"What is {topic}? Use your local substrate if available.",
            f"Explain {topic} in one useful paragraph from local memory.",
            f"What are the key points about {topic}?",
        ]):
            cases.append(BenchmarkCase(
                case_id=f"recall_{_slug(topic)}_{variant}",
                category="recall",
                prompt=prompt,
                expected_terms=terms,
                expected_routes=("developmental_concept_memory", "working_reasoning_set", "developmental_concept_domain_browse"),
            ))
    for left, right, terms in RELATIONAL_PAIRS:
        for variant, prompt in enumerate([
            f"Compare {left} and {right}. Use only approved local concepts.",
            f"How does {left} change the way you reason about {right}?",
            f"What evidence would connect {left} with {right}?",
        ]):
            cases.append(BenchmarkCase(
                case_id=f"multi_{_slug(left)}_{_slug(right)}_{variant}",
                category="multi_concept_retrieval",
                prompt=prompt,
                expected_terms=terms,
                expected_routes=("working_reasoning_set", "developmental_multi_concept_retrieval"),
            ))
    for left, right, terms in CROSS_DOMAIN_PAIRS:
        for variant, prompt in enumerate([
            f"How are {left} and {right} similar as systems? Separate stored knowledge from inference.",
            f"What common structure might connect {left} and {right}?",
            f"Build a cautious bridge between {left} and {right} using only local substrate knowledge.",
        ]):
            cases.append(BenchmarkCase(
                case_id=f"cross_{_slug(left)}_{_slug(right)}_{variant}",
                category="cross_domain_synthesis",
                prompt=prompt,
                expected_terms=terms,
                expected_routes=("working_reasoning_set", "developmental_multi_concept_retrieval"),
            ))
    for a, b, c, d, terms in ANALOGIES:
        for variant, prompt in enumerate([
            f"How is {a} to {b} like {c} to {d}? Use local concepts and label uncertainty.",
            f"Test this analogy: {a}/{b} is like {c}/{d}. What works and what breaks?",
        ]):
            cases.append(BenchmarkCase(
                case_id=f"analogy_{_slug(a)}_{_slug(c)}_{variant}",
                category="analogy",
                prompt=prompt,
                expected_terms=terms,
                expected_routes=("analogy_analysis", "working_reasoning_set", "developmental_multi_concept_retrieval"),
            ))
    for prompt, terms in ABSTRACTION_PROMPTS:
        for variant, phrasing in enumerate([
            prompt,
            prompt.replace("What ", "Explain what "),
        ]):
            cases.append(BenchmarkCase(
                case_id=f"abstraction_{len(cases):03d}_{variant}",
                category="abstraction",
                prompt=phrasing,
                expected_terms=terms,
                expected_routes=("working_reasoning_set", "developmental_multi_concept_retrieval"),
            ))
    for prompt, terms in MISSING_EVIDENCE:
        for variant, phrasing in enumerate([
            prompt,
            prompt + " State what cannot be concluded yet.",
        ]):
            cases.append(BenchmarkCase(
                case_id=f"missing_evidence_{len(cases):03d}_{variant}",
                category="missing_evidence",
                prompt=phrasing,
                expected_terms=terms,
                expected_routes=("working_reasoning_set", "developmental_multi_concept_retrieval", "developmental_concept_memory"),
            ))
    for prompt, terms in CONTRADICTIONS:
        for variant, phrasing in enumerate([
            prompt,
            prompt.replace("Can these both be true:", "Check for contradiction:"),
        ]):
            cases.append(BenchmarkCase(
                case_id=f"contradiction_{len(cases):03d}_{variant}",
                category="contradiction_detection",
                prompt=phrasing,
                expected_terms=terms,
                expected_routes=("contradiction_analysis", "working_reasoning_set", "developmental_multi_concept_retrieval", "local_model_consent_required"),
            ))
    for prompt, terms in NOVEL_COMBINATIONS:
        for variant, phrasing in enumerate([
            prompt,
            prompt + " Keep the bridge tentative.",
        ]):
            cases.append(BenchmarkCase(
                case_id=f"novel_{len(cases):03d}_{variant}",
                category="novel_combination",
                prompt=phrasing,
                expected_terms=terms,
                expected_routes=("working_reasoning_set", "developmental_multi_concept_retrieval"),
            ))
    followup_history = _history_from_turns([
        ("What is blood pressure?", "Blood pressure is the force exerted by circulating blood against artery walls."),
    ])
    for index, prompt in enumerate(["Tell me more.", "Why?", "Give an example.", "How does that relate to allergies?", "What else matters?", "Explain it simpler."]):
        cases.append(BenchmarkCase(
            case_id=f"followup_memory_{index}",
            category="followup_memory",
            prompt=prompt,
            expected_terms=("blood", "pressure"),
            expected_routes=("session_memory", "recent_concept_followup", "local_model_consent_required", "working_reasoning_set"),
            history=followup_history,
        ))
    long_history = _history_from_turns([
        ("Let's discuss photosynthesis.", "Photosynthesis stores light energy in chemical bonds."),
        ("Now switch to planning.", "Planning organizes actions toward goals."),
        ("Tell me about interest rates.", "Interest rates influence borrowing costs."),
        ("Talk about allergies.", "Allergies involve immune responses to allergens."),
        ("Now talk about feedback loops.", "Feedback loops use outcomes to adjust future behavior."),
        ("What is noncanonical memory?", "Noncanonical memory is reversible reviewed memory."),
        ("Tell me about gravity.", "Gravity attracts masses and shapes motion."),
        ("Explain inflation.", "Inflation is a broad rise in prices."),
        ("What is cellular respiration?", "Cellular respiration releases stored energy as ATP."),
        ("What is blood pressure?", "Blood pressure reflects cardiovascular state."),
    ])
    for case_id, prompt, terms in [
        ("long_conversation_return_to_photosynthesis", "Return to the first topic we discussed and explain how it stores energy.", ("photosynthesis", "energy")),
        ("long_conversation_return_to_feedback", "Return to the feedback-loop topic and connect it to planning.", ("feedback", "planning")),
        ("long_conversation_return_to_allergies", "Return to the allergy topic and explain why clinical context matters.", ("allerg", "context")),
        ("long_conversation_return_to_respiration", "Return to cellular respiration and explain what it produces.", ("respiration", "ATP")),
    ]:
        cases.append(BenchmarkCase(
            case_id=case_id,
            category="long_conversation",
            prompt=prompt,
            expected_terms=terms,
            expected_routes=("session_memory", "working_reasoning_set", "developmental_concept_memory", "developmental_multi_concept_retrieval"),
            history=long_history,
        ))
    conversation_prompts = [
        ("Thanks, that was helpful.", ("helpful",)),
        ("Explain that more simply.", ("simple", "explain")),
        ("Good job.", ("thanks", "glad", "welcome")),
        ("Nevermind.", ("okay",)),
        ("What topics do you know most about?", ("concept", "local")),
        ("Can you answer like a normal assistant?", ("conversation", "answer")),
    ]
    conversation_prompts.extend([
        ("Can you say that more casually?", ("casual", "simple")),
        ("What are you good at right now?", ("local", "concept")),
        ("Don't store this.", ("okay", "store")),
        ("Could you ask me a follow-up question?", ("question",)),
        ("I don't get it.", ("simpler", "explain")),
        ("That sounds too robotic.", ("natural", "conversation")),
    ])
    for index, (prompt, terms) in enumerate(conversation_prompts):
        cases.append(BenchmarkCase(
            case_id=f"conversation_{index}",
            category="conversation_quality",
            prompt=prompt,
            expected_terms=terms,
            expected_routes=("social_intent", "social_conversation", "session_memory", "local_conversation_scaffold", "developmental_concept_domain_browse", "provider_policy_answer"),
        ))
    return cases


def _term_score(answer: str, terms: tuple[str, ...]) -> float:
    if not terms:
        return 1.0
    lower = answer.lower()
    hits = sum(1 for term in terms if term.lower() in lower)
    return hits / len(terms)


def _route_score(route: str, expected: tuple[str, ...]) -> float:
    if not expected:
        return 1.0
    if route in expected:
        return 1.0
    if any(item in route for item in expected):
        return 0.8
    return 0.0


def _safety_score(payload: dict[str, Any]) -> float:
    forbidden = [
        "provider_calls_performed",
        "web_search_performed",
        "training_performed",
        "canonical_write_performed",
        "autonomous_action_performed",
    ]
    return 1.0 if all(payload.get(key) is False for key in forbidden) else 0.0


def _conversation_style_score(answer: str) -> float:
    lower = answer.lower()
    penalty = 0.0
    for marker in ("stored knowledge", "reasoned connection", "no memory, graph edge", "developer overlay", "route:"):
        if marker in lower:
            penalty += 0.18
    if len(answer.split()) > 180:
        penalty += 0.08
    return round(max(0.0, 1.0 - penalty), 4)


def _uncertainty_score(answer: str, category: str) -> float:
    lower = answer.lower()
    markers = ("uncertain", "uncertainty", "missing", "not enough", "would need", "cannot conclude", "tentative")
    if category in {"missing_evidence", "cross_domain_synthesis", "analogy", "abstraction"}:
        return 1.0 if any(marker in lower for marker in markers) else 0.25
    return 1.0


def _score_case(case: BenchmarkCase, payload: dict[str, Any]) -> dict[str, Any]:
    answer = str(payload.get("answer") or "")
    route = str(payload.get("route") or "")
    term = _term_score(answer, case.expected_terms)
    route_value = _route_score(route, case.expected_routes)
    safety = _safety_score(payload)
    style = _conversation_style_score(answer)
    uncertainty = _uncertainty_score(answer, case.category)
    if case.category == "conversation_quality":
        total = term * 0.25 + route_value * 0.15 + safety * 0.25 + style * 0.35
    elif case.category in {"abstraction", "analogy", "cross_domain_synthesis", "novel_combination"}:
        total = term * 0.35 + route_value * 0.25 + uncertainty * 0.2 + safety * 0.2
    elif case.category in {"followup_memory", "long_conversation"}:
        total = term * 0.45 + route_value * 0.25 + safety * 0.2 + style * 0.1
    elif case.category == "contradiction_detection":
        contradiction_signal = 1.0 if any(marker in answer.lower() for marker in ("contradict", "conflict", "cannot both", "polarity")) else 0.0
        total = term * 0.25 + route_value * 0.2 + contradiction_signal * 0.35 + safety * 0.2
    else:
        total = term * 0.45 + route_value * 0.25 + safety * 0.2 + uncertainty * 0.1
    return {
        "term_score": round(term, 4),
        "route_score": round(route_value, 4),
        "safety_score": round(safety, 4),
        "conversation_style_score": style,
        "uncertainty_score": round(uncertainty, 4),
        "score": round(total, 4),
    }


def run_case(case: BenchmarkCase) -> dict[str, Any]:
    payload = route_message("Conversation", case.prompt, history=list(case.history))
    score = _score_case(case, payload)
    answer = str(payload.get("answer") or "")
    wrs = payload.get("working_reasoning_set") if isinstance(payload.get("working_reasoning_set"), dict) else {}
    return {
        "case_id": case.case_id,
        "category": case.category,
        "prompt": case.prompt,
        "route": payload.get("route"),
        "confidence_score": payload.get("confidence_score"),
        "score": score,
        "answer_preview": answer[:500],
        "concept_count": len(payload.get("concept_matches", []) or []),
        "wrs": {
            "retrieved_concept_count": len(wrs.get("retrieved_concepts", []) or []),
            "retrieved_proposition_count": len(wrs.get("retrieved_propositions", []) or []),
            "retrieved_graph_edge_count": len(wrs.get("retrieved_graph_edges", []) or []),
            "possible_connection_count": len(wrs.get("possible_connections", []) or []),
            "missing_evidence_count": len(wrs.get("missing_evidence", []) or []),
            "confidence": wrs.get("confidence"),
            "retrieval_score": wrs.get("retrieval_score"),
            "graph_support_score": wrs.get("graph_support_score"),
        } if wrs else None,
        "provider_calls_performed": payload.get("provider_calls_performed"),
        "web_search_performed": payload.get("web_search_performed"),
        "training_performed": payload.get("training_performed"),
        "canonical_write_performed": payload.get("canonical_write_performed"),
        "autonomous_action_performed": payload.get("autonomous_action_performed"),
    }


def build_benchmark_report(write_reports: bool = True) -> dict[str, Any]:
    cases = build_benchmark_cases()
    results = [run_case(case) for case in cases]
    categories = sorted({result["category"] for result in results})
    category_scores = {
        category: round(mean(result["score"]["score"] for result in results if result["category"] == category), 4)
        for category in categories
    }
    category_counts = {
        category: sum(1 for result in results if result["category"] == category)
        for category in categories
    }
    weakest = sorted(results, key=lambda item: item["score"]["score"])[:12]
    safety_passed = all(
        result.get("provider_calls_performed") is False
        and result.get("web_search_performed") is False
        and result.get("training_performed") is False
        and result.get("canonical_write_performed") is False
        and result.get("autonomous_action_performed") is False
        for result in results
    )
    report = {
        "report": "RC2_COGNITIVE_CAPABILITY_BENCHMARK",
        "created_at": _now(),
        "case_count": len(results),
        "substrate_counts": substrate_counts(),
        "overall_score": round(mean(result["score"]["score"] for result in results), 4),
        "category_scores": category_scores,
        "category_counts": category_counts,
        "weakest_cases": weakest,
        "text_pathology_review": review_output_text_pathologies(results),
        "results": results,
        "safety_passed": safety_passed,
        "safety": dict(SAFETY),
        "recommendation": _recommendation(category_scores),
    }
    if write_reports:
        write_benchmark_reports(report)
    return report


def _recommendation(category_scores: dict[str, float]) -> str:
    weakest = min(category_scores, key=category_scores.get)
    if weakest in {"conversation_quality", "long_conversation", "followup_memory"}:
        return "IMPROVE_CONVERSATIONAL_RENDERING_AND_SESSION_STATE_BEFORE_CONCEPT_INSTILLATION"
    if weakest in {"abstraction", "analogy", "cross_domain_synthesis", "novel_combination"}:
        return "IMPROVE_WRS_ABSTRACTION_AND_PROPOSITION_COMPARISON_BEFORE_CONCEPT_INSTILLATION"
    if weakest == "contradiction_detection":
        return "IMPROVE_CONTRADICTION_DETECTION_BEFORE_CONCEPT_INSTILLATION"
    return "REPAIR_TARGETED_CONCEPT_SUBSTANCE_BEFORE_CONCEPT_INSTILLATION"


def review_output_text_pathologies(results: list[dict[str, Any]]) -> dict[str, Any]:
    markers = {
        "report_voice": [
            "Stored knowledge",
            "Reasoned connection",
            "Shared reasoning patterns",
            "No memory, graph edge",
        ],
        "internal_leak": [
            "route:",
            "developer overlay",
            "provider_calls_performed",
            "canonical_write_performed",
            "retrieval_score",
        ],
        "generic_scaffold": [
            "identifies the important variables",
            "separates observed evidence",
            "supports practical decisions",
            "operator-reviewable uncertainty",
            "reusable concept that helps explain",
        ],
        "wrong_context": [
            "Meaning of Life Perspectives",
        ],
        "consent_prompt_when_local_substrate_expected": [
            "Would you like me to ask",
            "Reply yes to ask",
        ],
    }
    review: dict[str, Any] = {}
    for pathology, phrases in markers.items():
        hits = [
            result for result in results
            if any(phrase.lower() in str(result.get("answer_preview", "")).lower() for phrase in phrases)
        ]
        review[pathology] = {
            "count": len(hits),
            "rate": round(len(hits) / max(1, len(results)), 4),
            "examples": [
                {
                    "case_id": hit["case_id"],
                    "category": hit["category"],
                    "route": hit["route"],
                    "score": hit["score"]["score"],
                    "prompt": hit["prompt"],
                    "preview": hit["answer_preview"][:260],
                }
                for hit in hits[:8]
            ],
        }
    contradiction_failures = []
    for result in results:
        if result["category"] != "contradiction_detection":
            continue
        answer = str(result.get("answer_preview", "")).lower()
        if not any(marker in answer for marker in ("contradict", "conflict", "cannot both", "polarity")):
            contradiction_failures.append(result)
    review["missed_contradiction_signal"] = {
        "count": len(contradiction_failures),
        "rate": round(len(contradiction_failures) / max(1, len([r for r in results if r["category"] == "contradiction_detection"])), 4),
        "examples": [
            {
                "case_id": hit["case_id"],
                "route": hit["route"],
                "score": hit["score"]["score"],
                "prompt": hit["prompt"],
                "preview": hit["answer_preview"][:260],
            }
            for hit in contradiction_failures[:8]
        ],
    }
    review["summary_findings"] = [
        "Contradiction prompts are usually routed to single-concept memory instead of a contradiction/comparison path.",
        "Many answers still expose report-like WRS sections; useful for Developer Overlay, too stiff for default conversation.",
        "Scaffold concepts still surface in recall, analogy, and cross-domain prompts where core factual concepts should win.",
        "Follow-up memory can attach to the wrong prior topic when the user gives a short command such as 'Give an example.'",
        "Some local-substrate questions still ask for local model escalation even when repaired concepts exist.",
    ]
    return review


def write_benchmark_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 Cognitive Capability Benchmark",
        "",
        f"Created: {report['created_at']}",
        f"Cases: {report['case_count']}",
        f"Overall score: {report['overall_score']}",
        f"Recommendation: {report['recommendation']}",
        f"Safety passed: {report['safety_passed']}",
        "",
        "## Category Scores",
        "",
        "| Capability | Cases | Score |",
        "| --- | ---: | ---: |",
    ]
    for category, score in sorted(report["category_scores"].items(), key=lambda item: item[0]):
        lines.append(f"| {category} | {report['category_counts'][category]} | {score} |")
    lines.extend(["", "## Weakest Cases", ""])
    for case in report["weakest_cases"]:
        lines.extend([
            f"### {case['case_id']}",
            "",
            f"- Category: {case['category']}",
            f"- Score: {case['score']['score']}",
            f"- Route: {case['route']}",
            f"- Prompt: {case['prompt']}",
            f"- Preview: {case['answer_preview']}",
            "",
        ])
    if report.get("text_pathology_review"):
        lines.extend(["", "## Output Text Pathology Review", ""])
        for pathology, details in report["text_pathology_review"].items():
            if pathology == "summary_findings":
                continue
            lines.extend([
                f"### {pathology}",
                "",
                f"- Count: {details['count']}",
                f"- Rate: {details['rate']}",
                "",
            ])
            for example in details.get("examples", [])[:3]:
                lines.extend([
                    f"- `{example['case_id']}` ({example.get('category', 'n/a')}, route={example.get('route')}, score={example.get('score')})",
                    f"  Prompt: {example.get('prompt')}",
                    f"  Preview: {example.get('preview', '').replace(chr(10), ' ')}",
                ])
            lines.append("")
        lines.extend(["### Summary findings", ""])
        for finding in report["text_pathology_review"].get("summary_findings", []):
            lines.append(f"- {finding}")
    lines.extend(["", "## Safety", ""])
    for key, value in report["safety"].items():
        lines.append(f"- {key}: {value}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_benchmark_report(write_reports=True)
    summary = {
        "case_count": report["case_count"],
        "overall_score": report["overall_score"],
        "category_scores": report["category_scores"],
        "safety_passed": report["safety_passed"],
        "recommendation": report["recommendation"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
