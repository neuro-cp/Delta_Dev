"""RC2 adversarial routing benchmark.

This benchmark targets route collisions and reference ambiguity. It is separate
from the permanent cognitive capability benchmark so historical scores remain
comparable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import re
from pathlib import Path
import sys
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message
from orchestration.runtime.rc2_route_arbitration import SAFETY_FIELDS, safety_schema_complete


REPORT_JSON = ROOT / "reports" / "RC2_ADVERSARIAL_ROUTING_BENCHMARK.json"
REPORT_MD = ROOT / "reports" / "RC2_ADVERSARIAL_ROUTING_BENCHMARK.md"


@dataclass(frozen=True)
class AdversarialCase:
    case_id: str
    category: str
    prompt: str
    expected_routes: tuple[str, ...]
    expected_terms: tuple[str, ...] = ()
    absent_terms: tuple[str, ...] = ()
    history: tuple[dict[str, str], ...] = ()
    note: str = ""


def _history(*turns: tuple[str, str]) -> tuple[dict[str, str], ...]:
    items: list[dict[str, str]] = []
    for user, assistant in turns:
        items.append({"role": "user", "content": user})
        items.append({"role": "assistant", "content": assistant})
    return tuple(items)


def build_adversarial_cases() -> list[AdversarialCase]:
    contradiction_history = _history(
        ("What is noncanonical memory?", "Noncanonical memory is reversible and supports rollback."),
        ("What else?", "Noncanonical memory cannot be rolled back."),
    )
    analogy_history = _history(
        ("How is photosynthesis like charging a battery?", "The analogy works through energy input, conversion, storage, and later use. Where it breaks: photosynthesis is biochemical and a battery is electrochemical."),
    )
    branch_history = _history(
        ("Let's discuss photosynthesis.", "Photosynthesis stores light energy in chemical bonds."),
        ("Now switch to planning.", "Planning organizes actions toward goals."),
        ("Tell me about interest rates.", "Interest rates influence borrowing costs."),
        ("Talk about allergies.", "Allergies involve immune responses to allergens."),
        ("Now talk about feedback loops.", "Feedback loops use outcomes to adjust future behavior."),
        ("What is cellular respiration?", "Cellular respiration releases stored energy as ATP."),
    )
    stale_history = _history(
        ("How is photosynthesis like charging a battery?", "The analogy works through energy storage."),
    )
    cases = [
        AdversarialCase("contradiction_pronoun", "route_collision", "Is that inconsistent with what you said before?", ("contradiction_analysis",), ("contradict", "conflict"), history=contradiction_history),
        AdversarialCase("contradiction_both_true", "route_collision", "Can both of those be true?", ("contradiction_analysis",), ("noncanonical", "conflict"), history=contradiction_history),
        AdversarialCase("generic_explain_that", "working_memory", "Explain that more clearly.", ("session_memory",), ("noncanonical", "memory"), history=contradiction_history),
        AdversarialCase("analogy_break", "route_collision", "Where does that analogy break?", ("analogy_analysis", "session_memory"), ("break",), history=analogy_history),
        AdversarialCase("analogy_are_like", "route_collision", "Test this analogy: photosynthesis and respiration are like charging and discharging. What works and what breaks?", ("analogy_analysis",), ("energy", "break")),
        AdversarialCase("wrs_compare", "route_collision", "Compare photosynthesis and respiration.", ("working_reasoning_set", "developmental_multi_concept_retrieval"), ("photosynthesis", "respiration")),
        AdversarialCase("missing_evidence_standalone", "missing_evidence", "What evidence is missing before concluding inflation will fall after interest rates rise?", ("working_reasoning_set", "developmental_multi_concept_retrieval", "developmental_concept_memory"), ("inflation", "interest")),
        AdversarialCase("orphan_that", "orphan_reference", "Explain that.", ("session_memory",), ("need",)),
        AdversarialCase("orphan_first", "orphan_reference", "The first one.", ("session_memory",), ("need",)),
        AdversarialCase("explicit_override", "topic_override", "What is blood pressure?", ("developmental_concept_memory", "working_reasoning_set", "developmental_multi_concept_retrieval"), ("blood pressure",), ("battery",), history=stale_history),
        AdversarialCase("return_first", "branch_return", "Return to the first topic and explain how it stores energy.", ("session_memory",), ("photosynthesis", "energy"), history=branch_history),
        AdversarialCase("return_named_planning", "branch_return", "Go back to planning.", ("session_memory",), ("planning",), history=branch_history),
        AdversarialCase("return_named_feedback", "branch_return", "Return to the feedback-loop topic and connect it to planning.", ("session_memory",), ("feedback", "planning"), history=branch_history),
        AdversarialCase("social_pure", "social_cognitive_mixed", "Thanks, that helped.", ("social_conversation", "local_conversation_scaffold"), ("welcome", "glad", "help")),
        AdversarialCase("social_continue", "social_cognitive_mixed", "Okay, continue explaining photosynthesis.", ("session_memory", "developmental_concept_memory", "working_reasoning_set"), ("photosynthesis",), history=branch_history),
        AdversarialCase("malformed_slash", "malformed_prompt", "what is the meaning of life\\", ("developmental_concept_memory", "working_reasoning_set", "local_model_consent_required"), ("meaning", "life")),
    ]
    return cases


def run_case(case: AdversarialCase) -> dict[str, Any]:
    payload = route_message("Conversation", case.prompt, history=list(case.history))
    answer = str(payload.get("answer") or "")
    route = str(payload.get("route") or "")
    rendered = render_route(payload, developer_overlay=False)
    route_ok = route in case.expected_routes
    term_ok = all(term.lower() in answer.lower() for term in case.expected_terms)
    absent_ok = all(term.lower() not in answer.lower() for term in case.absent_terms)
    safety_ok = (
        safety_schema_complete(payload)
        and all(payload.get(key) is False for key in SAFETY_FIELDS)
        and payload.get("safety_metadata", {}).get("behavioral_safety_passed") is True
    )
    leak_count = _leak_count(rendered)
    score = mean([1.0 if route_ok else 0.0, 1.0 if term_ok else 0.0, 1.0 if absent_ok else 0.0, 1.0 if safety_ok else 0.0, 1.0 if leak_count == 0 else 0.0])
    return {
        "case_id": case.case_id,
        "category": case.category,
        "prompt": case.prompt,
        "route": route,
        "expected_routes": case.expected_routes,
        "route_ok": route_ok,
        "term_ok": term_ok,
        "absent_ok": absent_ok,
        "safety_ok": safety_ok,
        "internal_leak_count": leak_count,
        "score": round(score, 4),
        "answer_preview": answer[:360],
        "arbitration": payload.get("route_arbitration"),
        "safety_metadata": payload.get("safety_metadata"),
    }


def build_adversarial_routing_report(write_reports: bool = True) -> dict[str, Any]:
    cases = build_adversarial_cases()
    results = [run_case(case) for case in cases]
    categories = sorted({item["category"] for item in results})
    category_scores = {
        category: round(mean(item["score"] for item in results if item["category"] == category), 4)
        for category in categories
    }
    route_accuracy = round(mean(1.0 if item["route_ok"] else 0.0 for item in results), 4)
    safety_completeness = round(mean(1.0 if item["safety_ok"] else 0.0 for item in results), 4)
    report = {
        "report": "RC2_ADVERSARIAL_ROUTING_BENCHMARK",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "case_count": len(results),
        "route_accuracy": route_accuracy,
        "route_collision_accuracy": _category_accuracy(results, "route_collision"),
        "pronoun_reference_accuracy": _category_accuracy(results, "working_memory"),
        "branch_return_accuracy": _category_accuracy(results, "branch_return"),
        "explicit_topic_override_accuracy": _category_accuracy(results, "topic_override"),
        "orphan_clarification_accuracy": _category_accuracy(results, "orphan_reference"),
        "social_cognitive_accuracy": _category_accuracy(results, "social_cognitive_mixed"),
        "safety_metadata_completeness": safety_completeness,
        "internal_leak_count": sum(item["internal_leak_count"] for item in results),
        "category_scores": category_scores,
        "results": results,
        "safety": {
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "noncanonical_write_performed": False,
            "graph_write_performed": False,
            "replay_write_performed": False,
            "autonomous_action_performed": False,
            "scheduler_action_performed": False,
        },
        "recommendation": "PROCEED_RC2_COGNITIVE_REFINEMENT_FREEZE" if route_accuracy >= 0.9 and safety_completeness == 1.0 else "CONTINUE_ROUTING_ARBITRATION",
    }
    if write_reports:
        _write_reports(report)
    return report


def _category_accuracy(results: list[dict[str, Any]], category: str) -> float:
    subset = [item for item in results if item["category"] == category]
    return round(mean(1.0 if item["route_ok"] and item["term_ok"] and item["absent_ok"] else 0.0 for item in subset), 4) if subset else 1.0


def _leak_count(text: str) -> int:
    lower = str(text or "").lower()
    markers = ("developer overlay", "route:", "provider_calls_performed", "canonical_write_performed", "retrieval_score")
    return sum(1 for marker in markers if marker in lower)


def _write_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 Adversarial Routing Benchmark",
        "",
        f"Created: {report['created_at']}",
        f"Cases: {report['case_count']}",
        f"Route accuracy: {report['route_accuracy']}",
        f"Route-collision accuracy: {report['route_collision_accuracy']}",
        f"Pronoun/reference accuracy: {report['pronoun_reference_accuracy']}",
        f"Branch-return accuracy: {report['branch_return_accuracy']}",
        f"Explicit topic-override accuracy: {report['explicit_topic_override_accuracy']}",
        f"Orphan clarification accuracy: {report['orphan_clarification_accuracy']}",
        f"Safety metadata completeness: {report['safety_metadata_completeness']}",
        f"Internal leaks: {report['internal_leak_count']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Category Scores",
        "",
    ]
    for category, score in sorted(report["category_scores"].items()):
        lines.append(f"- {category}: {score}")
    lines.extend(["", "## Cases", ""])
    for item in report["results"]:
        status = "PASS" if item["score"] == 1.0 else "CHECK"
        lines.extend([
            f"### {status}: {item['case_id']}",
            f"- Category: {item['category']}",
            f"- Route: {item['route']}",
            f"- Expected routes: {', '.join(item['expected_routes'])}",
            f"- Score: {item['score']}",
            f"- Preview: {item['answer_preview'].replace(chr(10), ' ')}",
            "",
        ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_adversarial_routing_report(write_reports=True)
    print(json.dumps({
        "case_count": report["case_count"],
        "route_accuracy": report["route_accuracy"],
        "route_collision_accuracy": report["route_collision_accuracy"],
        "branch_return_accuracy": report["branch_return_accuracy"],
        "orphan_clarification_accuracy": report["orphan_clarification_accuracy"],
        "safety_metadata_completeness": report["safety_metadata_completeness"],
        "internal_leak_count": report["internal_leak_count"],
        "recommendation": report["recommendation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
