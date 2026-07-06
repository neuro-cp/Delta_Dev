from __future__ import annotations

from orchestration.runtime.rc2_conversational_mode_router import (
    MODES,
    ROUTER_FLAGS,
    build_escalation_plan,
    classify_intent,
    render_route,
    route_message,
    write_rc2_report,
)


def test_rc2_modes_include_conversation_and_delta_modes():
    assert "Conversation" in MODES
    assert "Ask Substrate" in MODES
    assert "Evidence Review" in MODES
    assert "Contradiction Check" in MODES
    assert "Research Analyst" in MODES


def test_conversation_mode_answers_simple_local_question_without_provider():
    payload = route_message("Conversation", "What color is the sky?")
    assert payload["mode"] == "Conversation"
    assert payload["route"] == "local_conversation_scaffold"
    assert "blue" in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False
    assert payload["training_performed"] is False


def test_external_knowledge_request_creates_disabled_escalation_plan():
    payload = route_message("Conversation", "What is the relation between Avogadro's number and quantum field theory?")
    assert payload["provider_calls_performed"] is False
    assert payload["web_search_performed"] is False
    assert payload["escalation_plan"]["enabled_now"] is False
    assert "large_model_review_with_operator_approval" in payload["escalation_plan"]["recommended_routes"]


def test_evidence_mode_extracts_without_persistence():
    payload = route_message("Evidence Review", "", "Project Frontier has AI workers.")
    assert payload["route"] == "evidence_review"
    assert payload["extracted"]["candidate_count"] == 1
    assert payload["extracted"]["persisted"] is False
    assert payload["canonical_write_performed"] is False


def test_memory_mode_requires_explicit_approval_flag():
    payload = route_message("Memory Mode", "", "Project Frontier has AI workers.", approve=False)
    assert payload["result"]["approved_count"] == 0
    assert payload["result"]["requires_operator_approval"] is True
    assert payload["canonical_write_performed"] is False


def test_router_flags_keep_live_capabilities_disabled():
    assert ROUTER_FLAGS["provider_calls_enabled"] is False
    assert ROUTER_FLAGS["web_search_enabled"] is False
    assert ROUTER_FLAGS["training_enabled"] is False
    assert ROUTER_FLAGS["canonical_writes_enabled"] is False
    assert ROUTER_FLAGS["autonomous_actions_enabled"] is False


def test_intent_and_escalation_are_deterministic():
    intent = classify_intent("Tell me about beluga whales")
    plan = build_escalation_plan("Tell me about beluga whales")
    assert intent["intent"] == "external_knowledge_request"
    assert plan["requires_operator_approval"] is True
    assert plan["enabled_now"] is False


def test_render_and_report():
    rendered = render_route(route_message("Conversation", "How do you work?"))
    report = write_rc2_report()
    assert "Safety:" in rendered
    assert report["safe"] is True
    assert report["final_recommendation"] == "USE_RC2_CONVERSATIONAL_SHELL_AS_PRIMARY_UI_WITH_RC1_OPERATOR_MODE_AVAILABLE"

