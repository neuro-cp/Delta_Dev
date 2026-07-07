from __future__ import annotations

from orchestration.runtime.rc2_conversational_mode_router import (
    DISPLAY_MODES,
    MODES,
    ROUTER_FLAGS,
    build_escalation_plan,
    classify_intent,
    confidence_engine,
    remember_useful_answer,
    render_route,
    report_payloads,
    route_message,
    select_model_lane,
    write_rc2_report,
)
from orchestration.runtime import rc1_operator_console as rc1


def _isolate_rc1_store(monkeypatch, tmp_path):
    proposition = tmp_path / "noncanonical_propositions.jsonl"
    evidence = tmp_path / "evidence_links.jsonl"
    replay = tmp_path / "replay_queue.jsonl"
    contradictions = tmp_path / "contradictions.jsonl"
    monkeypatch.setattr(rc1, "DATA", tmp_path)
    monkeypatch.setattr(rc1, "PROPOSITION_LOG", proposition)
    monkeypatch.setattr(rc1, "EVIDENCE_LOG", evidence)
    monkeypatch.setattr(rc1, "REPLAY_LOG", replay)
    monkeypatch.setattr(rc1, "CONTRADICTION_LOG", contradictions)
    monkeypatch.setattr(rc1, "LOCAL_STORE_LOGS", (proposition, evidence, replay, contradictions))


def test_rc2_test_store_isolated(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    assert rc1.build_cognitive_state()["noncanonical_propositions"] == 0


def test_rc2_modes_include_conversation_and_delta_modes():
    assert "Conversation" in MODES
    assert "Conversation" in DISPLAY_MODES
    assert "Research" in DISPLAY_MODES
    assert "Memory Mode" in DISPLAY_MODES
    assert "Evidence Review" in MODES
    assert "Investigation" in DISPLAY_MODES
    assert "Developer" in DISPLAY_MODES


def test_conversation_mode_answers_simple_local_question_without_provider(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What color is the sky?")
    assert payload["mode"] == "Conversation"
    assert payload["route"] == "local_conversation_model_lane"
    assert "blue" in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False
    assert payload["training_performed"] is False
    assert payload["memory_candidate"]["requires_user_action"]


def test_conversation_answers_water_and_fire_without_placeholder(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    water = route_message("Conversation", "What color is water?")
    fire = route_message("Conversation", "What is fire?")
    assert "colorless" in water["answer"].lower()
    assert "combustion" in fire["answer"].lower()
    assert "switch modes" not in water["answer"].lower()
    assert water["provider_calls_performed"] is False
    assert fire["provider_calls_performed"] is False


def test_coding_question_selects_model_lane_without_executing(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What do you know about coding?")
    assert payload["intent"]["intent"] == "coding"
    assert payload["selected_model_lane"]["lane"] == "coding"
    assert payload["selected_model_lane"]["executed"] is False
    assert payload["provider_calls_performed"] is False
    assert "coding" in payload["answer"].lower()


def test_external_knowledge_request_creates_disabled_escalation_plan(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What is the relation between Avogadro's number and quantum field theory?")
    assert payload["provider_calls_performed"] is False
    assert payload["web_search_performed"] is False
    assert payload["escalation_plan"]["enabled_now"] is False
    assert "large_model_review_with_operator_approval" in payload["escalation_plan"]["recommended_routes"]
    assert payload["confidence_decision"]["provider_necessity"] == "gated_provider_or_web_may_be_needed"
    assert payload["supporting_information_offer"]["offered"] is True
    assert payload["supporting_information_offer"]["dry_run_provider_request"]["api_key_redacted"] is True


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


def test_remember_useful_answer_writes_only_noncanonical_local_record(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What is fire?")
    result = remember_useful_answer("What is fire?", payload)
    assert result["memory_write_performed"] is True
    assert result["memory_scope"] == "local_noncanonical_rc1_operator_store"
    assert result["canonical_write_performed"] is False
    assert result["training_performed"] is False
    assert rc1.build_cognitive_state()["noncanonical_propositions"] == 1


def test_clear_local_store_requires_exact_confirmation(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What is fire?")
    remember_useful_answer("What is fire?", payload)
    refused = rc1.clear_local_noncanonical_store("yes clear it")
    assert refused["cleared"] is False
    assert rc1.build_cognitive_state()["noncanonical_propositions"] == 1
    cleared = rc1.clear_local_noncanonical_store("DELETE_RC1_LOCAL_NONCANONICAL_STORE")
    assert cleared["cleared"] is True
    assert rc1.build_cognitive_state()["noncanonical_propositions"] == 0


def test_router_flags_keep_live_capabilities_disabled():
    assert ROUTER_FLAGS["provider_calls_enabled"] is False
    assert ROUTER_FLAGS["web_search_enabled"] is False
    assert ROUTER_FLAGS["training_enabled"] is False
    assert ROUTER_FLAGS["canonical_writes_enabled"] is False
    assert ROUTER_FLAGS["autonomous_actions_enabled"] is False


def test_intent_classifier_covers_product_intents():
    assert classify_intent("Can you write Python code?")["intent"] == "coding"
    assert classify_intent("Plan my invoice workflow")["intent"] == "planning"
    assert classify_intent("Analyze this document")["intent"] == "analysis"
    assert classify_intent("Show diagnostics")["intent"] == "diagnostics"
    assert confidence_engine("What color is the sky?")["provider_necessity"] == "not_required_for_scaffold_response"


def test_intent_and_escalation_are_deterministic():
    intent = classify_intent("Tell me about beluga whales")
    plan = build_escalation_plan("Tell me about beluga whales")
    assert intent["intent"] == "external_knowledge_request"
    assert plan["requires_operator_approval"] is True
    assert plan["enabled_now"] is False


def test_model_lane_selection_is_deterministic_and_nonexecuting():
    lane = select_model_lane("Debug this Python function", "coding")
    assert lane["lane"] == "coding"
    assert lane["executed"] is False
    assert lane["provider_calls_performed"] is False


def test_render_and_report(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    rendered = render_route(route_message("Conversation", "How do you work?"))
    report = write_rc2_report()
    assert "Safety:" in rendered
    assert "Mode:" not in rendered
    assert report["safe"] is True
    assert report["final_recommendation"] == "USE_RC2_CONVERSATIONAL_SHELL_AS_PRIMARY_UI_WITH_RC1_OPERATOR_MODE_AVAILABLE"


def test_named_rc2_reports_exist_in_payloads():
    payloads = report_payloads()
    for name in [
        "RC2_CONVERSATIONAL_ARCHITECTURE",
        "RC2_MODE_ROUTER",
        "RC2_INTENT_ROUTER",
        "RC2_MEMORY_EXPERIENCE",
        "RC2_OPERATOR_SEPARATION",
        "RC2_UI_REVIEW",
    ]:
        assert name in payloads
    assert payloads["RC2_OPERATOR_SEPARATION"]["default_tab"] == "Conversation"
    assert payloads["RC2_MEMORY_EXPERIENCE"]["canonical_writes_enabled"] is False
