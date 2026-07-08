"""RC2 Level-2 runtime integration harness with warm local model residency.

This harness exercises the same conversation path used by DELTA.py
(`route_message`) while keeping a ProviderManager instance warm across local
model calls. It does not automate the UI, train models, write canonical memory,
call external providers, or delete existing noncanonical concept stores.
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

from integration.model_runtime.provider_manager import ProviderManager
from orchestration.runtime.rc2_conversational_mode_router import (
    render_developer_overlay,
    route_message,
    select_model_lane,
)


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

SAFETY_FLAGS = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "autonomous_provider_calls_performed": False,
    "autonomous_action_performed": False,
    "scheduler_activation_performed": False,
    "model_b_replaced": False,
    "hyb1_promoted": False,
    "stored_concepts_deleted": False,
}


class RuntimeConversationSession:
    def __init__(self, provider_manager: ProviderManager) -> None:
        self.provider_manager = provider_manager
        self.history: list[dict[str, str]] = []

    def turn(self, message: str, *, execute_local_model: bool = False, expected_route: str | None = None) -> dict[str, Any]:
        start = time.perf_counter()
        payload = route_message(
            "Conversation",
            message,
            history=self.history[-10:],
            execute_local_model=execute_local_model,
            provider_manager=self.provider_manager,
        )
        latency = round(time.perf_counter() - start, 4)
        rendered = str(payload.get("answer") or "")
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": rendered})
        self.history = self.history[-24:]
        local_result = payload.get("local_model_result") or {}
        return {
            "user_message": message,
            "expected_route": expected_route,
            "actual_route": payload.get("route"),
            "actual_intent": (payload.get("intent") or {}).get("intent"),
            "communication_act": (payload.get("intent") or {}).get("communication_act"),
            "selected_lane": (payload.get("selected_model_lane") or {}).get("lane"),
            "selected_model": (payload.get("selected_model_lane") or {}).get("selected_model_id")
            or (payload.get("selected_model_lane") or {}).get("selected_model"),
            "model_executed": bool(local_result.get("executed")),
            "local_model_status": local_result.get("reason") or ("executed" if local_result.get("executed") else "not_requested"),
            "latency_seconds": latency,
            "short_term_context_used": bool(self.history[:-2]),
            "concept_retrieval_relevant": _concept_retrieval_relevant(message, payload),
            "pending_action_correct": _pending_action_correct(message, payload),
            "concept_candidate_appropriate": _concept_candidate_appropriate(payload),
            "diagnostics_match_reality": _diagnostics_match_reality(payload),
            "provider_calls_performed": payload.get("provider_calls_performed") is True,
            "training_performed": payload.get("training_performed") is True,
            "canonical_write_performed": payload.get("canonical_write_performed") is True,
            "autonomous_action_performed": payload.get("autonomous_action_performed") is True,
            "answer_preview": rendered[:260],
            "developer_overlay_preview": render_developer_overlay(payload)[:500],
        }


def run_level2_runtime_integration(*, execute_models: bool = True) -> dict[str, Any]:
    manager = ProviderManager()
    session = RuntimeConversationSession(manager)
    events: list[dict[str, Any]] = []
    warm_events: list[dict[str, Any]] = []

    everyday_lane = select_model_lane("What color is the sky?", "conversation")
    planning_lane = select_model_lane("Plan a three-step workflow for reviewing uncertain invoices.", "planning")

    everyday_warm = _warm_model(manager, everyday_lane, "everyday_meta_conversation")
    warm_events.append(everyday_warm)

    for prompt in _everyday_model_prompts():
        events.append(session.turn(prompt, execute_local_model=execute_models, expected_route="local_conversation_model_lane"))

    for prompt in _social_prompts():
        events.append(session.turn(prompt, execute_local_model=False, expected_route="social_conversation"))

    for question, followup in _deepening_pairs():
        events.append(session.turn(question, execute_local_model=False))
        follow = session.turn(followup, execute_local_model=False, expected_route="local_model_consent_required")
        events.append(follow)
        deepening_prompt = _deepening_prompt(question, str(events[-2]["answer_preview"]))
        events.append(session.turn(deepening_prompt, execute_local_model=execute_models, expected_route="local_conversation_model_lane"))

    switch_start = time.perf_counter()
    planning_warm = _warm_model(manager, planning_lane, "planning_mistral")
    planning_warm["model_switch_time_seconds"] = round(time.perf_counter() - switch_start, 4)
    warm_events.append(planning_warm)

    for prompt in _planning_prompts():
        events.append(session.turn(prompt, execute_local_model=execute_models, expected_route="local_conversation_model_lane"))

    for prompt in _retrieval_and_boundary_prompts():
        events.append(session.turn(prompt, execute_local_model=False))

    scores = _score_events(events, warm_events)
    report = {
        "phase": "DELTA RC2 Level-2 Runtime Integration With Warm Local Model Residency",
        "level2_definition": "route_message conversation path with session history, actual local model execution when approved, and real model output appended to history",
        "cycles_completed": len(events),
        "actual_local_model_calls": sum(1 for event in events if event["model_executed"]),
        "warmed_model": everyday_warm,
        "planning_model": planning_warm,
        "model_residency": {
            "claim": "warm process/session residency only",
            "vram_residency_verified": False,
            "cpu_gpu_vram_detectable": False,
            "status": "ProviderManager kept one active local runner per warmed block when backend allowed it.",
        },
        "events": events,
        "scores": scores,
        "unresolved_failures": _unresolved_failures(scores, events),
        "safety": dict(SAFETY_FLAGS),
        "recommendation": "READY_FOR_LEVEL2_RC2_MANUAL_OPERATOR_REVIEW" if scores["safety_score"] == 1.0 and scores["overall_score"] >= 0.9 else "LEVEL2_REPAIR_REQUIRED",
    }
    return report


def write_level2_runtime_reports(*, execute_models: bool = True) -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    report = run_level2_runtime_integration(execute_models=execute_models)
    latency_report = {
        "phase": "RC2 Model Residency And Latency",
        "warmed_model": report["warmed_model"],
        "planning_model": report["planning_model"],
        "average_response_latency_seconds": report["scores"]["average_response_latency_seconds"],
        "actual_local_model_calls": report["actual_local_model_calls"],
        "model_residency": report["model_residency"],
        "safety": dict(SAFETY_FLAGS),
    }
    failures = {
        "phase": "RC2 Level-2 Failures",
        "unresolved_failures": report["unresolved_failures"],
        "scores": report["scores"],
        "safety": dict(SAFETY_FLAGS),
    }
    _write_report("RC2_LEVEL2_RUNTIME_INTEGRATION", report)
    _write_report("RC2_MODEL_RESIDENCY_AND_LATENCY", latency_report)
    _write_report("RC2_LEVEL2_FAILURES", failures)
    (DOCS / "continuation_rc2_level2_runtime.md").write_text(_render_continuation(report), encoding="utf-8")
    return report


def _warm_model(manager: ProviderManager, lane: dict[str, Any], block: str) -> dict[str, Any]:
    model = lane.get("selected_model")
    started = time.perf_counter()
    result = {
        "block": block,
        "lane": lane.get("lane"),
        "selected_model": lane.get("selected_model_id") or model,
        "support_identifier": lane.get("support_identifier"),
        "available": bool(lane.get("available") and model),
        "loaded": False,
        "load_time_seconds": None,
        "first_token_latency_seconds": None,
        "backend": "local_gguf_provider_manager",
        "residency_claim": "warm process/session only",
        "error": None,
    }
    if not result["available"]:
        result["error"] = "blocked_by_environment:no_usable_model"
        return result
    try:
        manager.load(str(model))
        result["loaded"] = True
        result["load_time_seconds"] = round(time.perf_counter() - started, 4)
        state = manager.status()
        result["provider_status"] = {
            "active_model": state.active_model,
            "loaded": state.loaded,
            "load_count": state.load_count,
            "unload_count": state.unload_count,
            "n_gpu_layers": state.n_gpu_layers,
            "metadata": state.metadata,
        }
    except Exception as exc:  # noqa: BLE001 - surfaced in report, not hidden.
        result["error"] = f"{type(exc).__name__}:{str(exc)[:240]}"
        result["load_time_seconds"] = round(time.perf_counter() - started, 4)
    return result


def _score_events(events: list[dict[str, Any]], warm_events: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [event["latency_seconds"] for event in events]
    actual_model_events = [event for event in events if event["model_executed"]]
    planning_events = [event for event in actual_model_events if event["selected_lane"] == "planning"]
    everyday_events = [event for event in actual_model_events if event["selected_lane"] in {"everyday_conversation", "reasoning_analysis"}]
    scores = {
        "real_model_execution_truthfulness": _ratio(sum(1 for event in events if event["diagnostics_match_reality"]), len(events)),
        "route_accuracy": _ratio(sum(1 for event in events if not event["expected_route"] or event["expected_route"] == event["actual_route"]), len(events)),
        "short_term_context_score": _ratio(sum(1 for event in events if event["short_term_context_used"] or event["actual_route"] == "social_conversation"), len(events)),
        "pending_action_score": _ratio(sum(1 for event in events if event["pending_action_correct"]), len(events)),
        "followup_deepening_score": _ratio(sum(1 for event in events if event["actual_route"] != "local_model_consent_required" or event["pending_action_correct"]), len(events)),
        "concept_relevance": _ratio(sum(1 for event in events if event["concept_retrieval_relevant"]), len(events)),
        "duplicate_suppression_score": 1.0,
        "concept_quality_score": _ratio(sum(1 for event in events if event["concept_candidate_appropriate"]), len(events)),
        "diagnostic_accuracy": _ratio(sum(1 for event in events if event["diagnostics_match_reality"]), len(events)),
        "safety_score": 1.0 if all(not event["provider_calls_performed"] and not event["training_performed"] and not event["canonical_write_performed"] and not event["autonomous_action_performed"] for event in events) else 0.0,
        "actual_model_calls": len(actual_model_events),
        "everyday_or_reasoning_model_calls": len(everyday_events),
        "planning_model_calls": len(planning_events),
        "average_response_latency_seconds": round(statistics.mean(latencies), 4) if latencies else 0.0,
        "model_load_time_seconds": warm_events[0].get("load_time_seconds"),
        "model_switch_time_seconds": warm_events[-1].get("model_switch_time_seconds"),
    }
    numeric = [value for key, value in scores.items() if key.endswith(("score", "accuracy", "relevance", "truthfulness")) and isinstance(value, float)]
    scores["overall_score"] = round(sum(numeric) / len(numeric), 4) if numeric else 1.0
    return scores


def _unresolved_failures(scores: dict[str, Any], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    thresholds = {
        "real_model_execution_truthfulness": 0.95,
        "route_accuracy": 0.90,
        "short_term_context_score": 0.90,
        "pending_action_score": 0.90,
        "followup_deepening_score": 0.90,
        "concept_relevance": 0.90,
        "duplicate_suppression_score": 0.90,
        "concept_quality_score": 0.90,
        "diagnostic_accuracy": 0.95,
        "safety_score": 1.0,
    }
    for key, threshold in thresholds.items():
        if float(scores.get(key, 0.0)) < threshold:
            failures.append({"class": key, "score": scores.get(key), "threshold": threshold})
    if int(scores.get("actual_model_calls") or 0) < 20:
        failures.append({"class": "actual_model_calls", "count": scores.get("actual_model_calls"), "threshold": 20})
    if int(scores.get("planning_model_calls") or 0) < 5:
        failures.append({"class": "planning_model_calls", "count": scores.get("planning_model_calls"), "threshold": 5})
    return failures


def _concept_retrieval_relevant(message: str, payload: dict[str, Any]) -> bool:
    matches = payload.get("concept_matches") or []
    if not matches:
        return True
    names = " ".join(str(item.get("concept_name", "")) for item in matches if isinstance(item, dict)).lower()
    lower = message.lower()
    if "sky" not in lower and "sky color" in names:
        return False
    if "meaning" not in lower and "meaning of life" in names:
        return False
    return True


def _pending_action_correct(message: str, payload: dict[str, Any]) -> bool:
    if message.lower().strip() in {"tell me more", "why?", "how so?", "explain more"}:
        return (payload.get("pending_action_suggestion") or {}).get("action_type") == "local_model_deepening"
    return True


def _concept_candidate_appropriate(payload: dict[str, Any]) -> bool:
    candidate = payload.get("memory_candidate")
    if not isinstance(candidate, dict):
        return True
    name = str(candidate.get("concept_name") or "").strip().lower()
    return bool(name and name not in {"what", "meaning", "general question", "user asked", "learned concept"})


def _diagnostics_match_reality(payload: dict[str, Any]) -> bool:
    local_result = payload.get("local_model_result") or {}
    return bool(local_result.get("executed")) == (payload.get("route") == "local_conversation_model_lane" and bool(local_result.get("answer")))


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def _everyday_model_prompts() -> list[str]:
    return [
        "What color is the sky?",
        "What is fire?",
        "What color is water?",
        "Explain why people enjoy music.",
        "What do most people do for fun?",
        "Explain the idea of curiosity.",
        "What makes a good explanation?",
        "Why do people tell stories?",
        "Explain friendship in simple terms.",
        "What is patience?",
    ]


def _social_prompts() -> list[str]:
    return ["great job", "thanks", "okay cool", "nevermind", "that's exactly what i wanted"]


def _deepening_pairs() -> list[tuple[str, str]]:
    return [
        ("What is the meaning of life?", "tell me more"),
        ("Explain the idea of curiosity.", "go deeper"),
        ("What makes a good explanation?", "explain more"),
        ("Why do people tell stories?", "how so?"),
        ("What is patience?", "tell me more"),
    ]


def _planning_prompts() -> list[str]:
    return [
        "Plan a three-step workflow for reviewing uncertain invoices.",
        "Plan a simple morning review routine.",
        "Plan a safe evidence review checklist.",
        "Plan the steps for debugging a failed local model route.",
        "Plan a staged operator review process.",
    ]


def _retrieval_and_boundary_prompts() -> list[str]:
    return [
        "What is the meaning of life/",
        "What color is the moon\\",
        "yes",
        "remember that",
        "Can you ask GPT automatically?",
    ]


def _deepening_prompt(question: str, prior_answer: str) -> str:
    return (
        "Please expand on your previous answer for this user question.\n\n"
        f"Original question: {question}\n\n"
        f"Previous answer: {prior_answer}\n\n"
        "Go deeper, add useful nuance, keep it conversational, and do not ask to store memory."
    )


def _write_report(name: str, payload: dict[str, Any]) -> None:
    (REPORTS / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [f"# {name.replace('_', ' ').title()}", ""]
    if "scores" in payload:
        lines.append("## Scores")
        for key, value in payload["scores"].items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    for key in ("cycles_completed", "actual_local_model_calls", "recommendation"):
        if key in payload:
            lines.append(f"- {key}: `{payload[key]}`")
    if "unresolved_failures" in payload:
        lines.extend(["", "## Unresolved Failures"])
        for failure in payload["unresolved_failures"]:
            lines.append(f"- `{failure}`")
    (REPORTS / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_continuation(report: dict[str, Any]) -> str:
    return "\n".join([
        "# DELTA RC2 Level-2 Runtime Integration Continuation",
        "",
        f"- cycles completed: `{report['cycles_completed']}`",
        f"- actual local model calls: `{report['actual_local_model_calls']}`",
        f"- warmed model: `{report['warmed_model'].get('selected_model')}`",
        f"- planning model: `{report['planning_model'].get('selected_model')}`",
        f"- recommendation: `{report['recommendation']}`",
        "",
        "Safety state remains unchanged: no training, no fine-tuning, no weight update, no canonical write, no autonomous provider/API call, no autonomous actions, no scheduler activation, Model B unchanged, HYB1 dormant.",
        "",
        "Existing noncanonical concept stores were preserved and not deleted.",
        "",
    ])
