from __future__ import annotations

from orchestration.runtime.rc2_conversational_mode_router import (
    DISPLAY_MODES,
    MODES,
    ROUTER_FLAGS,
    build_escalation_plan,
    build_gpt_approval_preview,
    candidate_is_memory_worthy,
    classify_intent,
    confidence_engine,
    discover_local_model_lanes,
    execute_gpt_support_request,
    remember_useful_answer,
    render_route,
    report_payloads,
    route_message,
    select_model_lane,
    write_rc2_report,
)
from orchestration.runtime import rc1_operator_console as rc1
from orchestration.runtime import rc2_developmental_concept_memory as rc2mem
from orchestration.runtime import rc2_conversational_mode_router as rc2router
from integration.model_runtime.inference_types import CanonicalInferenceResult
from integration.model_runtime.model_registry import ModelSpec


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


def _isolate_rc2_store(monkeypatch, tmp_path):
    conversation = tmp_path / "conversation_memory.jsonl"
    personal = tmp_path / "personal_memory.jsonl"
    knowledge = tmp_path / "knowledge_concepts.jsonl"
    edges = tmp_path / "concept_edges.jsonl"
    replay = tmp_path / "concept_replay_queue.jsonl"
    contradictions = tmp_path / "concept_contradictions.jsonl"
    monkeypatch.setattr(rc2mem, "DATA", tmp_path)
    monkeypatch.setattr(rc2mem, "CONVERSATION_MEMORY_LOG", conversation)
    monkeypatch.setattr(rc2mem, "PERSONAL_MEMORY_LOG", personal)
    monkeypatch.setattr(rc2mem, "KNOWLEDGE_MEMORY_LOG", knowledge)
    monkeypatch.setattr(rc2mem, "CONCEPT_EDGE_LOG", edges)
    monkeypatch.setattr(rc2mem, "CONCEPT_REPLAY_LOG", replay)
    monkeypatch.setattr(rc2mem, "CONCEPT_CONTRADICTION_LOG", contradictions)
    monkeypatch.setattr(rc2mem, "STORE_BY_TYPE", {"conversation": conversation, "personal": personal, "knowledge": knowledge})


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
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What color is the sky?")
    assert payload["mode"] == "Conversation"
    assert payload["route"] == "local_conversation_model_lane"
    assert "blue" in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False
    assert payload["training_performed"] is False
    assert payload["memory_candidate"]["approval_status"] == "pending_operator_approval"
    rendered = render_route(payload)
    assert "Safety:" not in rendered
    assert "Preferred local model" not in rendered
    assert "I routed" not in rendered


def test_conversation_executes_local_model_when_requested(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    fake_model = tmp_path / "phi4-test.gguf"
    fake_model.write_text("not a real model; ProviderManager is monkeypatched", encoding="utf-8")
    monkeypatch.setattr(
        rc2router,
        "list_available_models",
        lambda: {
            "phi4": ModelSpec(
                name="phi4-test",
                path=str(fake_model),
                tier=2,
                description="fake",
                context_length=4096,
                family="phi4",
            )
        },
    )
    seen = {}

    class FakeProviderManager:
        def infer(self, *, model_name, prompt, task_type="open_ended", metadata=None):
            seen["model_name"] = model_name
            seen["prompt"] = prompt
            seen["task_type"] = task_type
            seen["metadata"] = metadata
            return CanonicalInferenceResult(
                provider="local_gguf",
                model_id=model_name,
                answer="A local model says fire is combustion.",
                raw_output="A local model says fire is combustion.",
                confidence=0.81,
                latency_seconds=0.0,
                prompt_tokens=len(prompt.split()),
                response_tokens=7,
                evidence=[],
                metadata={},
            )

    monkeypatch.setattr(rc2router, "ProviderManager", FakeProviderManager)

    payload = route_message(
        "Conversation",
        "What is fire?",
        execute_local_model=True,
    )
    assert seen["task_type"] == "rc2_conversation"
    assert seen["metadata"]["route"] == "rc2_local_model_lane"
    assert "Current user message:" in seen["prompt"]
    assert payload["selected_model_lane"]["support_identifier"].startswith("rc2-local-lane:everyday_conversation:model:phi4-test")
    assert payload["selected_model_lane"]["selected_model_id"] == "phi4-test"
    assert payload["local_model_result"]["executed"] is True
    assert payload["selected_model_lane"]["executed"] is True
    assert payload["provider_calls_performed"] is False
    assert payload["answer"] == "A local model says fire is combustion."


def test_conversation_answers_water_and_fire_without_placeholder(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    water = route_message("Conversation", "What color is water?")
    fire = route_message("Conversation", "What is fire?")
    assert "colorless" in water["answer"].lower()
    assert "combustion" in fire["answer"].lower()
    assert "switch modes" not in water["answer"].lower()
    assert water["provider_calls_performed"] is False
    assert fire["provider_calls_performed"] is False


def test_coding_question_selects_model_lane_without_executing(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What do you know about coding?")
    assert payload["intent"]["intent"] == "coding"
    assert payload["selected_model_lane"]["lane"] == "coding_technical"
    assert payload["selected_model_lane"]["executed"] is False
    assert payload["provider_calls_performed"] is False
    assert "coding" in payload["answer"].lower()


def test_broad_question_gets_normal_answer_and_no_bad_concept(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What do most people do for fun?")
    rendered = render_route(payload)
    assert "friends" in payload["answer"].lower() or "hobbies" in payload["answer"].lower()
    assert "switch modes" not in payload["answer"].lower()
    assert payload["memory_candidate"] is None
    assert "What Most People" not in rendered


def test_external_knowledge_request_creates_disabled_escalation_plan(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What is the relation between Avogadro's number and quantum field theory?")
    assert payload["provider_calls_performed"] is False
    assert payload["web_search_performed"] is False
    assert payload["escalation_plan"]["enabled_now"] is False
    assert "large_model_review_with_operator_approval" in payload["escalation_plan"]["recommended_routes"]
    assert payload["confidence_decision"]["provider_necessity"] == "gated_provider_or_web_may_be_needed"
    assert payload["supporting_information_offer"]["offered"] is True
    assert payload["supporting_information_offer"]["dry_run_provider_request"]["api_key_redacted"] is True
    assert payload["supporting_information_offer"]["compact_support_packet"]["provider_call_performed"] is False


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
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What is fire?")
    result = remember_useful_answer("What is fire?", payload)
    assert result["memory_write_performed"] is True
    assert result["memory_scope"] == "local_noncanonical_rc2_developmental_concept_store"
    assert result["canonical_write_performed"] is False
    assert result["training_performed"] is False
    assert rc2mem.build_developmental_memory_state()["knowledge_memory_records"] == 1


def test_approved_concept_is_reused_in_conversation(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    first = route_message("Conversation", "What is fire?")
    remember_useful_answer("What is fire?", first)
    followup = route_message("Conversation", "Tell me about fire")
    assert followup["route"] == "developmental_concept_memory"
    assert "you taught me" in followup["answer"].lower()
    assert followup["provider_calls_performed"] is False


def test_concept_contradiction_detection_first_pass(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    lane = select_model_lane("Project Frontier is automatic.")
    first = rc2mem.extract_candidate_concept(
        question="Is Project Frontier automatic?",
        answer="Project Frontier is automatic.",
        source_model_lane=lane,
    )
    second = rc2mem.extract_candidate_concept(
        question="Is Project Frontier automatic?",
        answer="Project Frontier is not automatic.",
        source_model_lane=lane,
    )
    assert rc2mem.approve_candidate_concept(first)["approved"] is True
    result = rc2mem.approve_candidate_concept(second)
    assert result["approved"] is True
    assert result["contradictions"]


def test_short_term_session_memory_answers_followup_without_persistence(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    history = [{"role": "user", "content": "What is fire?"}, {"role": "assistant", "content": "Fire is combustion."}]
    payload = route_message("Conversation", "What did I just ask?", history=history)
    assert payload["route"] == "conversation_short_term_memory"
    assert "what is fire" in payload["answer"].lower()
    assert rc2mem.build_developmental_memory_state()["knowledge_memory_records"] == 0


def test_gpt_approval_preview_is_compact_and_no_call(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    history = [{"role": "user", "content": "Tell me about Avogadro and quantum field theory."}]
    payload = build_gpt_approval_preview("Tell me about Avogadro and quantum field theory.", history)
    rendered = render_route(payload)
    assert payload["provider_calls_performed"] is False
    assert payload["compact_support_packet"]["provider_call_performed"] is False
    assert len(payload["compact_support_packet"]["relevant_chat_history"]) == 1
    assert "If you say yes" in rendered
    assert "Safety:" not in rendered


def test_provider_path_executes_only_after_explicit_approval(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)

    def fake_transport(_endpoint, _headers, body, _timeout):
        assert body["max_tokens"] == 120
        return {"choices": [{"message": {"content": "Provider evidence answer."}}]}

    monkeypatch.setattr(
        "orchestration.runtime.v16_external_consolidation_evaluator_api_trial._default_transport",
        fake_transport,
        raising=False,
    )
    monkeypatch.setattr(
        "orchestration.runtime.v17_provider_assisted_unknown_answer._default_transport",
        fake_transport,
    )
    monkeypatch.setattr(
        "orchestration.runtime.v17_provider_assisted_unknown_answer.parse_env_file",
        lambda: {
            "DELTA_UNKNOWN_PROVIDER_ENABLED": "true",
            "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true",
            "DELTA_EVALUATOR_API_KEY": "redacted-test-key",
            "DELTA_UNKNOWN_PROVIDER_MODEL": "gpt-test",
        },
    )
    preview = route_message("Conversation", "Tell me about beluga whales")
    assert preview["provider_calls_performed"] is False
    approved = route_message(
        "Conversation",
        "Tell me about beluga whales",
        provider_approved=True,
        provider_transport=fake_transport,
    )
    assert approved["provider_calls_performed"] is True
    assert approved["answer"] == "Provider evidence answer."


def test_clear_local_store_requires_exact_confirmation(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What is fire?")
    remember_useful_answer("What is fire?", payload)
    refused = rc2mem.clear_developmental_memory_store("yes clear it")
    assert refused["cleared"] is False
    assert rc2mem.build_developmental_memory_state()["knowledge_memory_records"] == 1
    cleared = rc2mem.clear_developmental_memory_store("DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE")
    assert cleared["cleared"] is True
    assert rc2mem.build_developmental_memory_state()["knowledge_memory_records"] == 0


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
    assert confidence_engine("What color is the sky?")["provider_necessity"] == "not_required_for_local_response"


def test_intent_and_escalation_are_deterministic():
    intent = classify_intent("Tell me about beluga whales")
    plan = build_escalation_plan("Tell me about beluga whales")
    assert intent["intent"] == "external_knowledge_request"
    assert plan["requires_operator_approval"] is True
    assert plan["enabled_now"] is False


def test_model_lane_selection_is_deterministic_and_nonexecuting():
    lane = select_model_lane("Debug this Python function", "coding")
    assert lane["lane"] == "coding_technical"
    assert lane["support_identifier"].startswith("rc2-local-lane:coding_technical:")
    assert lane["executed"] is False
    assert lane["provider_calls_performed"] is False


def test_local_model_lanes_are_discovered_from_registry():
    data = discover_local_model_lanes()
    assert "lanes" in data
    assert "everyday_conversation" in data["lanes"]
    assert data["model_execution_enabled_by_default"] is False


def test_render_and_report(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    rendered = render_route(route_message("Conversation", "How do you work?"))
    report = write_rc2_report()
    assert "Safety:" not in rendered
    assert "Mode:" not in rendered
    assert report["safe"] is True
    assert report["final_recommendation"] == "USE_RC2_CONVERSATIONAL_SHELL_AS_PRIMARY_UI_WITH_RC1_OPERATOR_MODE_AVAILABLE"


def test_memory_candidate_quality_rejects_vague_concept(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What do most people do for fun?")
    candidate = rc2mem.extract_candidate_concept(
        question="What do most people do for fun?",
        answer=payload["answer"],
        source_model_lane=payload["selected_model_lane"],
    )
    assert candidate["concept_name"] == "What Most People"
    assert candidate_is_memory_worthy(candidate, payload) is False


def test_named_rc2_reports_exist_in_payloads():
    payloads = report_payloads()
    for name in [
        "RC2_CONVERSATIONAL_ARCHITECTURE",
        "RC2_MODE_ROUTER",
        "RC2_INTENT_ROUTER",
        "RC2_MEMORY_EXPERIENCE",
        "RC2_OPERATOR_SEPARATION",
        "RC2_UI_REVIEW",
        "RC2_MODEL_LANE_ROUTER",
        "RC2_DEVELOPMENTAL_CONCEPT_FORMATION",
        "RC2_MEMORY_STORE_SEPARATION",
        "RC2_CONCEPT_GRAPH_LINKING",
        "RC2_CONCEPT_APPROVAL_UX",
        "RC2_DEVELOPMENTAL_LIFECYCLE",
    ]:
        assert name in payloads
    assert payloads["RC2_OPERATOR_SEPARATION"]["default_tab"] == "Conversation"
    assert payloads["RC2_MEMORY_EXPERIENCE"]["canonical_writes_enabled"] is False
