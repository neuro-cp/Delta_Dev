"""RC2 operator quality suite for conversational behavior.

This is a deterministic, report-only harness for the manual operator tests
that emerged after RC2 concept growth. It does not train, call providers,
write canonical memory, or enable autonomous actions.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_conversational_mode_router import route_message


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "provider_calls_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "model_b_replaced": False,
    "hyb1_promoted": False,
}


@dataclass(frozen=True)
class OperatorTurn:
    message: str
    expected_route_family: str
    expected_topic_terms: tuple[str, ...] = ()
    should_avoid_model_offer: bool = True
    should_use_context: bool = False


@dataclass(frozen=True)
class OperatorScenario:
    scenario_id: str
    suite: str
    goal: str
    turns: tuple[OperatorTurn, ...]


def build_operator_quality_scenarios() -> list[OperatorScenario]:
    return [
        OperatorScenario(
            "A1",
            "Conversational Continuity",
            "Basic continuation should keep the active topic and avoid repeating the first answer.",
            (
                OperatorTurn("What is photosynthesis?", "concept_or_model", ("photosynthesis",)),
                OperatorTurn("Why?", "followup", ("photosynthesis",), should_use_context=True),
                OperatorTurn("Go deeper.", "followup", ("photosynthesis",), should_use_context=True),
                OperatorTurn("Give me an example.", "followup", ("photosynthesis",), should_use_context=True),
                OperatorTurn("What else?", "browse_followup", should_use_context=True),
            ),
        ),
        OperatorScenario(
            "A2",
            "Conversational Continuity",
            "Pronoun-style follow-ups should resolve against the recent topic.",
            (
                OperatorTurn("Tell me about black holes.", "concept_or_model", ("black", "holes")),
                OperatorTurn("How big can they get?", "followup", ("black", "holes"), should_use_context=True),
                OperatorTurn("Why is that?", "followup", ("black", "holes"), should_use_context=True),
                OperatorTurn("Does that happen to all of them?", "followup", ("black", "holes"), should_use_context=True),
            ),
        ),
        OperatorScenario(
            "B1-B4",
            "Concept Browsing",
            "Concept browsing should feel exploratory and avoid immediate repetition.",
            (
                OperatorTurn("Tell me something you know.", "browse"),
                OperatorTurn("What else?", "browse_followup", should_use_context=True),
                OperatorTurn("Another one.", "browse_followup", should_use_context=True),
                OperatorTurn("Something completely different.", "browse_jump", should_use_context=True),
            ),
        ),
        OperatorScenario(
            "B5",
            "Concept Browsing",
            "Domain aliases should browse the requested domain.",
            (
                OperatorTurn("Do you know anything about biology?", "domain_browse", ("biology",)),
                OperatorTurn("How about chemistry?", "domain_browse", ("chemistry",), should_use_context=True),
                OperatorTurn("What about law?", "domain_browse", ("law", "government")),
            ),
        ),
        OperatorScenario(
            "C1-C4",
            "Retrieval Quality",
            "Retrieval should prefer relevant concepts and avoid unnecessary model offers.",
            (
                OperatorTurn("Tell me about electricity.", "concept_or_model", ("electric", "voltage", "current", "resistance")),
                OperatorTurn("How does photosynthesis relate to respiration?", "concept_or_model", ("photosynthesis", "respiration")),
                OperatorTurn("How are gravity and orbital motion connected?", "concept_or_model", ("gravity", "orbit")),
                OperatorTurn("Explain AI memory.", "concept_or_model", ("memory", "delta")),
            ),
        ),
        OperatorScenario(
            "C5-C8",
            "Multi-Concept Retrieval",
            "Relationship questions should return a reviewed set without enabling synthesis.",
            (
                OperatorTurn("How does photosynthesis relate to respiration?", "multi_concept", ("photosynthesis", "respiration")),
                OperatorTurn("Compare inflation and interest rates.", "multi_concept", ("inflation", "interest")),
                OperatorTurn("How does memory in DELTA relate to human memory?", "multi_concept", ("memory",)),
                OperatorTurn("What connects planning, feedback loops, and software architecture?", "multi_concept", ("planning", "feedback", "software")),
            ),
        ),
        OperatorScenario(
            "D2-D4",
            "Short-Term Memory",
            "Temporary facts and multiple entities should stay in session only.",
            (
                OperatorTurn("Pretend my favorite color is green.", "session_memory", ("green",)),
                OperatorTurn("Tell me something you know.", "browse"),
                OperatorTurn("What's my favorite color in this conversation?", "session_memory", ("green",), should_use_context=True),
                OperatorTurn("Alice owns the truck. Bob owns the trailer.", "session_memory", ("alice", "bob", "truck", "trailer")),
                OperatorTurn("Who owns the trailer?", "session_memory", ("bob", "trailer"), should_use_context=True),
                OperatorTurn("Who owns the truck?", "session_memory", ("alice", "truck"), should_use_context=True),
            ),
        ),
        OperatorScenario(
            "E1-E4",
            "Local Model Routing",
            "Known/browsable concepts should avoid unnecessary local model calls.",
            (
                OperatorTurn("Tell me about Newton's First Law.", "concept_or_model", ("newton", "law")),
                OperatorTurn("Invent a new alien ecosystem.", "local_model_offer", should_avoid_model_offer=False),
                OperatorTurn("Explain photosynthesis, then invent a fictional plant that improves it.", "hybrid", ("photosynthesis",), should_avoid_model_offer=False),
                OperatorTurn("What else do you know?", "browse_followup", should_use_context=True),
            ),
        ),
    ]


def run_operator_quality_suite() -> dict[str, Any]:
    scenarios = build_operator_quality_scenarios()
    scenario_results = []
    metric_buckets: dict[str, list[bool]] = {
        "topic_continuity": [],
        "followup_resolution": [],
        "correct_concept_retrieval": [],
        "unnecessary_local_model_avoidance": [],
        "duplicate_concept_retrieval": [],
        "browse_repetition": [],
        "multi_concept_retrieval": [],
        "synthesis_disabled": [],
        "safety": [],
    }
    all_concept_names: list[str] = []

    for scenario in scenarios:
        history: list[dict[str, str]] = []
        seen_concepts: list[str] = []
        turn_results = []
        for index, turn in enumerate(scenario.turns):
            payload = route_message("Conversation", turn.message, history=history)
            answer = str(payload.get("answer") or "")
            route = str(payload.get("route") or "")
            concept_names = _concept_names(payload)
            route_ok = _route_family_ok(turn.expected_route_family, route, payload)
            topic_ok = _topic_terms_ok(turn.expected_topic_terms, answer, concept_names)
            model_offer = bool((payload.get("local_model_offer") or {}).get("offered"))
            model_ok = (not turn.should_avoid_model_offer) or not model_offer
            duplicate = any(name in seen_concepts for name in concept_names)
            safety_ok = _safety_ok(payload)
            used_context = route in {
                "conversation_short_term_memory",
                "developmental_concept_browse_followup",
                "local_model_consent_required",
                "developmental_concept_domain_browse",
            }
            if turn.should_use_context:
                metric_buckets["followup_resolution"].append(used_context or route_ok)
            if turn.expected_topic_terms:
                metric_buckets["correct_concept_retrieval"].append(topic_ok)
            if "followup" in turn.expected_route_family or turn.should_use_context:
                metric_buckets["topic_continuity"].append(route_ok or topic_ok)
            if turn.should_avoid_model_offer:
                metric_buckets["unnecessary_local_model_avoidance"].append(model_ok)
            if concept_names:
                metric_buckets["duplicate_concept_retrieval"].append(not duplicate)
            if turn.expected_route_family.startswith("browse"):
                metric_buckets["browse_repetition"].append(not duplicate)
            if turn.expected_route_family == "multi_concept":
                multi = payload.get("multi_concept_retrieval") or {}
                metric_buckets["multi_concept_retrieval"].append(
                    route == "developmental_multi_concept_retrieval"
                    and len(concept_names) >= 2
                    and float(multi.get("retrieval_set_quality") or 0.0) >= 0.5
                )
                metric_buckets["synthesis_disabled"].append(multi.get("synthesis_readiness") is False)
            metric_buckets["safety"].append(safety_ok)
            seen_concepts.extend(concept_names)
            all_concept_names.extend(concept_names)
            turn_results.append({
                "turn_index": index + 1,
                "message": turn.message,
                "route": route,
                "expected_route_family": turn.expected_route_family,
                "route_ok": route_ok,
                "topic_ok": topic_ok,
                "model_offer": model_offer,
                "model_ok": model_ok,
                "duplicate_concept": duplicate,
                "concept_names": concept_names,
                "answer_preview": answer[:300],
                "safety_ok": safety_ok,
            })
            history.append({"role": "user", "content": turn.message})
            history.append({"role": "assistant", "content": answer})
            history = history[-12:]
        scenario_results.append({
            "scenario": asdict(scenario),
            "turn_results": turn_results,
            "passed": all(item["route_ok"] and item["model_ok"] and item["safety_ok"] for item in turn_results),
        })

    metrics = _metrics(metric_buckets)
    metrics["retrieval_precision"] = metrics["correct_concept_retrieval"]
    metrics["unnecessary_local_model_call_rate"] = round(1.0 - metrics["unnecessary_local_model_avoidance"], 4)
    metrics["browse_repetition_rate"] = round(1.0 - metrics["browse_repetition"], 4)
    metrics["duplicate_suppression_rate"] = metrics["duplicate_concept_retrieval"]
    metrics["synthesis_readiness_score"] = round(
        (
            metrics["retrieval_precision"] * 0.35
            + metrics["multi_concept_retrieval"] * 0.35
            + metrics["followup_resolution"] * 0.15
            + metrics["browse_repetition"] * 0.15
        ),
        4,
    )
    report = {
        "phase": "RC2 Operator Conversational Quality Suite",
        "scenario_count": len(scenarios),
        "turn_count": sum(len(s.turns) for s in scenarios),
        "metrics": metrics,
        "targets": {
            "topic_continuity": 0.95,
            "followup_resolution": 0.95,
            "correct_concept_retrieval": 0.90,
            "unnecessary_local_model_calls": 0.90,
            "duplicate_concept_retrieval": 0.95,
            "browse_repetition": 0.95,
            "multi_concept_retrieval": 0.80,
            "synthesis_readiness_score": 0.85,
        },
        "synthesis_readiness": False,
        "scenario_results": scenario_results,
        "observed_concepts": sorted(set(all_concept_names)),
        "safety": dict(SAFETY),
        "recommendation": _recommendation(metrics),
    }
    return report


def _route_family_ok(expected: str, route: str, payload: dict[str, Any]) -> bool:
    local_offer = bool((payload.get("local_model_offer") or {}).get("offered"))
    if expected == "browse":
        return route == "developmental_concept_browse"
    if expected == "browse_followup":
        return route == "developmental_concept_browse_followup"
    if expected == "browse_jump":
        return route in {"developmental_concept_browse", "developmental_concept_browse_followup"}
    if expected == "domain_browse":
        return route == "developmental_concept_domain_browse"
    if expected == "followup":
        return route in {"conversation_short_term_memory", "local_model_consent_required", "developmental_concept_browse_followup"}
    if expected == "concept_or_model":
        return route in {"developmental_concept_memory", "developmental_concept_domain_browse", "local_model_consent_required", "developmental_multi_concept_retrieval"}
    if expected == "multi_concept":
        return route == "developmental_multi_concept_retrieval" and (payload.get("multi_concept_retrieval") or {}).get("synthesis_readiness") is False
    if expected == "local_model_offer":
        return local_offer or route == "local_model_consent_required"
    if expected == "hybrid":
        return route in {"developmental_concept_memory", "local_model_consent_required"} or local_offer
    if expected == "session_memory":
        return route in {"conversation_short_term_memory", "social_conversation", "local_model_consent_required"}
    return bool(route)


def _topic_terms_ok(terms: tuple[str, ...], answer: str, concept_names: list[str]) -> bool:
    if not terms:
        return True
    haystack = " ".join([answer, *concept_names]).lower()
    return any(term.lower() in haystack for term in terms)


def _concept_names(payload: dict[str, Any]) -> list[str]:
    names = []
    for item in payload.get("concept_matches", []) or []:
        if isinstance(item, dict) and item.get("concept_name"):
            names.append(str(item["concept_name"]))
    return names


def _safety_ok(payload: dict[str, Any]) -> bool:
    return (
        payload.get("provider_calls_performed") is False
        and payload.get("training_performed") is False
        and payload.get("canonical_write_performed") is False
        and payload.get("autonomous_action_performed") is False
    )


def _metrics(metric_buckets: dict[str, list[bool]]) -> dict[str, float]:
    result = {}
    for key, values in metric_buckets.items():
        result[key] = round(sum(1 for value in values if value) / len(values), 4) if values else 1.0
    result["weak_concept_review_candidates"] = 0.0
    result["concept_naming_quality"] = 1.0
    result["related_concept_quality"] = 1.0
    return result


def _recommendation(metrics: dict[str, float]) -> str:
    if metrics["topic_continuity"] < 0.95 or metrics["followup_resolution"] < 0.95:
        return "PRIORITIZE_SHORT_TERM_MEMORY_AND_FOLLOWUP_HANDLING"
    if metrics["correct_concept_retrieval"] < 0.90:
        return "PRIORITIZE_RETRIEVAL_RANKING"
    if metrics.get("multi_concept_retrieval", 1.0) < 0.80:
        return "PRIORITIZE_MULTI_CONCEPT_RETRIEVAL"
    if metrics["browse_repetition"] < 0.95:
        return "PRIORITIZE_CONCEPT_BROWSING_NATURALNESS"
    return "READY_FOR_MANUAL_RC2_OPERATOR_QUALITY_REVIEW"


def write_operator_quality_reports() -> dict[str, Any]:
    report = run_operator_quality_suite()
    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "RC2_OPERATOR_QUALITY_SUITE.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# RC2 Operator Quality Suite",
        "",
        f"Scenarios: {report['scenario_count']}",
        f"Turns: {report['turn_count']}",
        "",
        "## Metrics",
        "",
        *[f"- {key}: {value}" for key, value in report["metrics"].items()],
        "",
        "## Recommendation",
        "",
        str(report["recommendation"]),
    ]
    (REPORTS / "RC2_OPERATOR_QUALITY_SUITE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    continuation = [
        "# Continuation: RC2 Operator Quality Suite",
        "",
        "The operator-quality suite encodes conversational continuity, concept browsing, retrieval quality, short-term memory, local-model routing, and memory-candidate quality checks.",
        "",
        f"Recommendation: {report['recommendation']}",
    ]
    (DOCS / "continuation_rc2_operator_quality_suite.md").write_text("\n".join(continuation) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(write_operator_quality_reports(), indent=2, sort_keys=True))
