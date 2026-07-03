from __future__ import annotations

import subprocess
import sys

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v15_first_interaction import build_first_interaction_result, validate_first_interaction_result_safe
from orchestration.runtime.v15_local_knowledge_router import (
    RUNTIME_V15E_LOCAL_ROUTER_FLAGS,
    build_local_knowledge_topics,
    route_local_knowledge_answer,
    validate_local_knowledge_router_safe,
)
from orchestration.runtime.v15_local_knowledge_router_report import (
    build_local_knowledge_router_report_data,
    write_local_knowledge_router_report,
)


KNOWN_QUESTIONS = {
    "What is DELTA's current replay and consolidation path?": "replay_consolidation_path",
    "What is HYB1?": "hyb1_status",
    "Is HYB1 active?": "hyb1_status",
    "What is Model B?": "model_b_status",
    "Can DELTA remember things yet?": "memory_status",
    "Can DELTA train itself yet?": "training_status",
    "Can DELTA call providers?": "provider_call_status",
    "Can DELTA execute actions?": "action_execution_status",
    "What is currently active?": "active_capabilities",
    "What is still disabled?": "disabled_capabilities",
    "What is the safest next activation gate?": "safest_next_activation_gate",
    "What can DELTA not answer yet?": "what_delta_cannot_answer_yet",
}


def test_router_has_required_topics():
    topic_ids = {topic.topic_id for topic in build_local_knowledge_topics()}
    assert {
        "replay_consolidation_path",
        "memory_status",
        "canonical_write_status",
        "provider_call_status",
        "action_execution_status",
        "training_status",
        "hyb1_status",
        "model_b_status",
        "integration_gate_status",
        "runtime_console_purpose",
        "experience_adapter",
        "semantic_adapter",
        "feedback_capture",
        "controlled_learning",
        "offline_evaluation",
        "promotion_rollback",
        "active_capabilities",
        "disabled_capabilities",
        "scaffold_only_capabilities",
        "safest_next_activation_gate",
        "what_delta_cannot_answer_yet",
    } <= topic_ids


def test_known_questions_return_non_fallback_local_answers():
    for question, topic_id in KNOWN_QUESTIONS.items():
        route = route_local_knowledge_answer(question)
        assert route.matched is True
        assert route.topic_id == topic_id
        assert route.answer is not None
        assert route.answer.confidence_label in {"local_static", "local_report_summary"}
        assert "cannot answer that from the local delta scaffold yet" not in route.answer.answer_text.lower()
        assert validate_local_knowledge_router_safe(route)


def test_unsupported_question_still_returns_fallback():
    route = route_local_knowledge_answer("Who won a game yesterday?")
    assert route.matched is False
    assert route.topic_id == "unsupported"
    assert "cannot answer that from the local DELTA scaffold yet" in route.unsupported_reason
    assert validate_local_knowledge_router_safe(route)


def test_first_interaction_integrates_router_and_keeps_trace_safety():
    data = build_first_interaction_result("What is HYB1?")
    text = data["response_preview"]["response_text"].lower()
    assert "dormant" in text
    assert "env" in text or "environment" in text
    assert "not the default" in text
    assert data["trace"]["trace_id"]
    assert data["trace"]["experience_preview_id"]
    assert data["trace"]["semantic_preview_id"]
    assert validate_first_interaction_result_safe(data)


def test_safety_flags_remain_false_for_mutating_or_external_paths(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    assert RUNTIME_V15E_LOCAL_ROUTER_FLAGS["local_knowledge_router_enabled"] is True
    assert RUNTIME_V15E_LOCAL_ROUTER_FLAGS["static_topic_registry_enabled"] is True
    assert all(
        value is False
        for key, value in RUNTIME_V15E_LOCAL_ROUTER_FLAGS.items()
        if key not in {"local_knowledge_router_enabled", "static_topic_registry_enabled"}
    )
    data = build_first_interaction_result("Can DELTA train itself yet?")
    flags = data["invariant_flags"]
    assert flags["provider_calls_enabled"] is False
    assert flags["tool_calls_enabled"] is False
    assert flags["memory_mutation_enabled"] is False
    assert flags["canonical_write_enabled"] is False
    assert flags["runtime_recall_mutation_enabled"] is False
    assert flags["action_execution_enabled"] is False
    assert flags["training_enabled"] is False
    assert flags["hyb1_default_activation_enabled"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation_states_local_router_only(tmp_path, monkeypatch):
    from orchestration.runtime import v15_local_knowledge_router_report as report_module

    md_path = tmp_path / "router.md"
    json_path = tmp_path / "router.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)
    data = write_local_knowledge_router_report()
    text = md_path.read_text(encoding="utf-8").lower()
    assert json_path.exists()
    assert data["topic_count"] >= 21
    assert data["safety_summary"]["provider_calls_performed"] is False
    assert "local knowledge routing is not learned memory" in text
    assert "answer template is not provider generation" in text


def test_build_report_data_includes_sample_routes():
    data = build_local_knowledge_router_report_data()
    sample_topics = {sample["topic_id"] for sample in data["sample_routes"] if sample["matched"]}
    assert "hyb1_status" in sample_topics
    assert "memory_status" in sample_topics
    assert "active_capabilities" in sample_topics
    assert data["unsupported_sample_count"] == 1


def test_ask_delta_script_routes_known_local_question():
    completed = subprocess.run(
        [sys.executable, "scripts/ask_delta.py", "What is HYB1?"],
        check=True,
        text=True,
        capture_output=True,
    )
    output = completed.stdout.lower()
    assert "delta first interaction preview" in output
    assert "hyb1 is a dormant" in output
    assert "hyb1_default_activation_enabled: false" in output
    assert "provider_calls_enabled: false" in output
    assert "training_enabled: false" in output
