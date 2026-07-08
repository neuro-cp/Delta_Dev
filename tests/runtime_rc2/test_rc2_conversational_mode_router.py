from __future__ import annotations

from orchestration.runtime.rc2_conversational_mode_router import (
    DISPLAY_MODES,
    MODES,
    ROUTER_FLAGS,
    build_escalation_plan,
    build_gpt_approval_preview,
    build_memory_candidate_from_answer,
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
from orchestration.runtime.rc2_dialogue_intent_classifier import (
    build_dialogue_intent_corpus,
    classify_dialogue_act,
    evaluate_dialogue_intent_corpus,
    write_dialogue_intent_artifacts,
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


def test_social_turn_does_not_trigger_model_memory_or_retrieval(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "great job")
    assert payload["intent"]["intent"] == "compliment"
    assert payload["route"] == "social_conversation"
    assert payload["local_model_offer"] is None
    assert payload["supporting_information_offer"] is None
    assert payload["memory_candidate"] is None
    assert "glad" in payload["answer"].lower()


def test_dialogue_act_classifier_covers_social_acceptance_cases():
    cases = {
        "great effort": ("encouragement", "social_response_only"),
        "good job": ("compliment", "social_response_only"),
        "thanks": ("thanks", "social_response_only"),
        "nevermind": ("cancellation", "stop_pending_action"),
        "no": ("refusal", "reject_current_pending_action_only"),
        "yes": ("affirmation", "approve_current_pending_action_only"),
        "okay go ahead": ("affirmation", "approve_current_pending_action_only"),
        "try again": ("clarification_followup", "use_short_term_context"),
        "explain simpler": ("clarification_followup", "use_short_term_context"),
        "tell me more": ("clarification_followup", "use_short_term_context"),
        "remember that": ("memory_request", "concept_approval_path"),
        "don't remember that": ("memory_request", "concept_approval_path"),
    }
    for utterance, (act, action) in cases.items():
        observed = classify_dialogue_act(utterance)
        assert observed["communication_act"] == act
        assert observed["routed_action"] == action
        assert observed["provider_calls_performed"] is False if "provider_calls_performed" in observed else observed["safety"]["provider_calls_performed"] is False


def test_dialogue_corpus_evaluation_is_large_and_clean():
    corpus = build_dialogue_intent_corpus()
    report = evaluate_dialogue_intent_corpus(corpus)
    assert len(corpus) >= 200
    assert report["corpus_size"] == len(corpus)
    assert report["accuracy"] >= 0.98
    assert report["safety"]["training_performed"] is False
    assert report["safety"]["provider_calls_performed"] is False
    assert report["safety"]["canonical_write_performed"] is False


def test_dialogue_artifact_writer_creates_corpus_and_report(monkeypatch, tmp_path):
    from orchestration.runtime import rc2_dialogue_intent_classifier as classifier

    monkeypatch.setattr(classifier, "DATA", tmp_path / "data")
    monkeypatch.setattr(classifier, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(classifier, "CORPUS_PATH", tmp_path / "data" / "dialogue_intent_corpus.json")
    monkeypatch.setattr(classifier, "REPORT_JSON", tmp_path / "reports" / "RC2_DIALOGUE_INTENT_CLASSIFIER.json")
    monkeypatch.setattr(classifier, "REPORT_MD", tmp_path / "reports" / "RC2_DIALOGUE_INTENT_CLASSIFIER.md")
    report = write_dialogue_intent_artifacts()
    assert report["corpus_size"] >= 200
    assert classifier.CORPUS_PATH.exists()
    assert classifier.REPORT_JSON.exists()
    assert classifier.REPORT_MD.exists()


def test_social_communication_acts_never_route_to_model_or_memory(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    for utterance in ["great effort", "good job", "thanks", "no", "nevermind", "how are you"]:
        payload = route_message("Conversation", utterance)
        assert payload["route"] == "social_conversation"
        assert payload["local_model_offer"] is None
        assert payload["memory_candidate"] is None
        assert payload["provider_calls_performed"] is False


def test_developer_overlay_shows_route_model_and_support_identifier(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What do most people do for fun?")
    rendered = render_route(payload, developer_overlay=True)
    assert "Developer Overlay" in rendered
    assert "Chosen model:" in rendered
    assert "Support identifier:" in rendered
    assert "Knowledge boundary: unknown_seek_local_model" in rendered


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


def test_local_model_falls_back_to_venv_subprocess_when_llama_cpp_missing(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    fake_model = tmp_path / "llama-test.gguf"
    fake_model.write_text("not a real model; subprocess is monkeypatched", encoding="utf-8")
    monkeypatch.setattr(
        rc2router,
        "list_available_models",
        lambda: {
            "llama": ModelSpec(
                name="llama-test",
                path=str(fake_model),
                tier=4,
                description="fake",
                context_length=4096,
                family="llama",
            )
        },
    )

    class MissingLlamaProviderManager:
        def infer(self, **_kwargs):
            raise ModuleNotFoundError("No module named 'llama_cpp'", name="llama_cpp")

    monkeypatch.setattr(rc2router, "ProviderManager", MissingLlamaProviderManager)
    monkeypatch.setattr(
        rc2router,
        "_infer_local_model_via_venv_subprocess",
        lambda model_name, prompt, model_lane: {
            "executed": True,
            "available": True,
            "answer": "Subprocess model answer.",
            "confidence_score": 0.77,
            "model_id": model_name,
            "prompt_sent": prompt,
            "execution_adapter": "venv_subprocess",
            "provider_calls_performed": False,
        },
    )
    payload = route_message("Conversation", "what color is the moon", execute_local_model=True)
    assert payload["local_model_result"]["executed"] is True
    assert payload["local_model_result"]["execution_adapter"] == "venv_subprocess"
    assert payload["answer"] == "Subprocess model answer."


def test_successful_local_model_answer_offers_memory_candidate(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    fake_model = tmp_path / "llama-test.gguf"
    fake_model.write_text("not a real model; ProviderManager is monkeypatched", encoding="utf-8")
    monkeypatch.setattr(
        rc2router,
        "list_available_models",
        lambda: {
            "llama": ModelSpec(
                name="llama-test",
                path=str(fake_model),
                tier=4,
                description="fake",
                context_length=4096,
                family="llama",
            )
        },
    )

    class FakeProviderManager:
        def infer(self, **_kwargs):
            return CanonicalInferenceResult(
                provider="local_gguf",
                model_id="llama-test",
                answer=(
                    "The moon is mostly gray because its surface is covered in dusty rock called regolith. "
                    "It can look white, yellow, orange, or red from Earth depending on lighting and atmosphere."
                ),
                raw_output="",
                confidence=0.82,
                latency_seconds=0.0,
                prompt_tokens=20,
                response_tokens=28,
                evidence=[],
                metadata={},
            )

    monkeypatch.setattr(rc2router, "ProviderManager", FakeProviderManager)
    payload = route_message("Conversation", "what color is the moon", execute_local_model=True)
    rendered = render_route(payload)
    assert payload["local_model_result"]["executed"] is True
    assert payload["memory_candidate"]["concept_name"] == "Moon Color Appearance"
    assert "Concept Review" in rendered
    assert "accepting it there is the only way to store it" in rendered
    assert payload["canonical_write_performed"] is False
    assert payload["training_performed"] is False
    assert payload["provider_calls_performed"] is False


def test_lane_selection_uses_usable_family_fallback_when_alias_is_bad(monkeypatch, tmp_path):
    fail_dir = tmp_path / "fail"
    good_dir = tmp_path / "good"
    fail_dir.mkdir()
    good_dir.mkdir()
    bad = fail_dir / "qwen-bad.gguf"
    good = good_dir / "qwen-good.gguf"
    bad.write_text("bad", encoding="utf-8")
    good.write_text("good", encoding="utf-8")
    monkeypatch.setattr(
        rc2router,
        "list_available_models",
        lambda: {
            "qwen": ModelSpec(name="qwen-bad", path=str(bad), tier=3, description="bad", context_length=4096, family="qwen"),
            "qwen-good": ModelSpec(name="qwen-good", path=str(good), tier=3, description="good", context_length=4096, family="qwen"),
        },
    )
    lane = select_model_lane("Debug this Python function", "coding")
    assert lane["selected_model"] == "qwen-good"
    assert lane["selected_model_id"] == "qwen-good"
    assert lane["rejected_models"][0]["reason"] == "unusable_or_marked_fail"


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
    assert payload["route"] == "local_model_consent_required"
    assert "local reasoning model" in rendered.lower()
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


def test_concept_retrieval_does_not_overmatch_generic_overlap(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    sky = route_message("Conversation", "What color is the sky?")
    remember_useful_answer("What color is the sky?", sky)
    fun = route_message("Conversation", "What do people usually do for fun?")
    assert fun["route"] == "local_model_consent_required"
    assert "Daytime Sky Color" not in render_route(fun)


def test_existing_approved_concept_is_not_requeued_for_review(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    sky = route_message("Conversation", "What color is the sky?")
    remember_useful_answer("What color is the sky?", sky)
    known = route_message("Conversation", "What color is the sky?")
    assert known["route"] == "developmental_concept_memory"
    assert known["memory_candidate"] is None


def test_memory_command_does_not_create_concept_from_command_text(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "remember that")
    assert payload["intent"]["communication_act"] == "memory_request"
    assert payload["memory_candidate"] is None
    assert "Remember That" not in render_route(payload)


def test_explicit_memory_request_can_review_lower_confidence_previous_answer(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = {
        "route": "local_conversation_model_lane",
        "answer": (
            "The meaning of life is a broad philosophical question. Some perspectives emphasize purpose, "
            "relationships, growth, contribution, beauty, truth, or personal fulfillment."
        ),
        "confidence_score": 0.65,
        "selected_model_lane": select_model_lane("what is the meaning of life"),
    }
    candidate = build_memory_candidate_from_answer("what is the meaning of life", payload)
    assert candidate["concept_name"] == "Meaning of Life Perspectives"
    assert candidate_is_memory_worthy(candidate, payload) is False
    review_candidate = {
        **candidate,
        "approval_status": "pending_operator_review_user_requested",
        "operator_review_required": True,
        "memory_request_source": "explicit_user_remember_that",
        "uncertainty": "moderate_operator_review_required",
    }
    assert review_candidate["operator_review_required"] is True
    assert review_candidate["approval_status"] == "pending_operator_review_user_requested"


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


def test_approved_concept_query_tolerates_accidental_slashes(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "what is the meaning of life")
    candidate = rc2mem.extract_candidate_concept(
        question="what is the meaning of life",
        answer="The meaning of life can involve purpose, relationships, growth, and contribution.",
        source_model_lane=payload["selected_model_lane"],
    )
    assert rc2mem.approve_candidate_concept(candidate)["approved"] is True
    assert route_message("Conversation", "what is the meaning of life/")["route"] == "developmental_concept_memory"
    assert route_message("Conversation", "what is the meaning of life\\")["route"] == "developmental_concept_memory"


def test_execute_local_model_bypasses_approved_concept_retrieval(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    concept = rc2mem.extract_candidate_concept(
        question="what is the meaning of life",
        answer="The meaning of life can involve purpose, relationships, growth, and contribution.",
        source_model_lane=select_model_lane("what is the meaning of life"),
    )
    assert rc2mem.approve_candidate_concept(concept)["approved"] is True
    seen = {}

    def fake_execute(message, model_lane, history=None):
        seen["message"] = message
        return {
            "executed": True,
            "available": True,
            "answer": "A deeper local-model elaboration about meaning, purpose, relationships, and responsibility.",
            "confidence_score": 0.81,
            "provider_calls_performed": False,
        }

    monkeypatch.setattr(rc2router, "execute_local_model_answer", fake_execute)
    payload = route_message(
        "Conversation",
        "Please expand on your previous answer. Original question: what is the meaning of life",
        history=[{"role": "user", "content": "what is the meaning of life"}],
        execute_local_model=True,
    )
    assert payload["route"] == "local_conversation_model_lane"
    assert payload["local_model_result"]["executed"] is True
    assert "deeper local-model elaboration" in payload["answer"]
    assert "Please expand" in seen["message"]


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


def test_deepened_answer_enriches_existing_concept_without_prompt_keywords(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    lane = select_model_lane("what is the meaning of life")
    first = rc2mem.extract_candidate_concept(
        question="what is the meaning of life",
        answer="The meaning of life can involve purpose, relationships, growth, and contribution.",
        source_model_lane=lane,
    )
    assert rc2mem.approve_candidate_concept(first)["approved"] is True
    enrichment = rc2mem.extract_candidate_concept(
        question="Please expand on your previous answer for this user question. Original question: what is the meaning of life",
        answer="Another perspective is that meaning is discovered through relationships, responsibility, creativity, and service to others.",
        source_model_lane=lane,
    )
    enrichment = {
        **enrichment,
        "enrichment_of_concept_id": first["concept_id"],
        "source_question": "what is the meaning of life",
        "source_type": "local_model_lane_enrichment",
    }
    assert enrichment["concept_name"] == "Meaning of Life Perspectives"
    assert "please" not in enrichment["related_concepts"]
    assert "expand" not in enrichment["related_concepts"]
    assert "previous" not in enrichment["related_concepts"]
    assert "complex" not in enrichment["related_concepts"]
    assert "multifaceted" not in enrichment["related_concepts"]
    result = rc2mem.approve_candidate_concept(enrichment)
    assert result["approved"] is True
    assert result["enriched_existing"] is True
    state = rc2mem.build_developmental_memory_state()
    assert state["knowledge_memory_records"] == 1
    stored = rc2mem.query_approved_concepts("meaning of life")["matches"][0]
    assert stored["enrichment_count"] == 1
    assert any("relationships" in item.lower() for item in stored["propositions"])


def test_meaning_of_life_related_concepts_prefer_reusable_phrases(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    candidate = rc2mem.extract_candidate_concept(
        question="What is the meaning of life?",
        answer=(
            "The meaning of life can be explored through the pursuit of happiness, relationships, "
            "personal growth, self-reflection, purpose, passions, and learning and adaptation."
        ),
        source_model_lane=select_model_lane("What is the meaning of life?"),
    )
    related = candidate["related_concepts"]
    assert "pursuit of happiness" in related
    assert "personal growth" in related
    assert "self-reflection" in related
    assert "meaning" not in related
    assert "complex" not in related
    assert "concept" not in related


def test_list_numbered_answers_do_not_create_numeric_definition(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    candidate = rc2mem.extract_candidate_concept(
        question="Plan a three-step workflow for understanding coding",
        answer=(
            "1.\nResearch the basics of coding: Learn about programming languages, data structures, and algorithms.\n"
            "2.\nPractice coding: Write code to solve problems and build projects.\n"
            "3.\nReview and learn from mistakes: Analyze your code, identify errors, and learn from them."
        ),
        source_model_lane=select_model_lane("Plan a three-step workflow for understanding coding", "planning"),
    )
    assert candidate["concept_name"] == "Coding Learning Workflow"
    assert candidate["short_definition"] != "1."
    assert all(item not in {"1.", "2.", "3."} for item in candidate["propositions"])
    assert "Research the basics of coding" in candidate["short_definition"]


def test_short_term_session_memory_answers_followup_without_persistence(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    history = [{"role": "user", "content": "What is fire?"}, {"role": "assistant", "content": "Fire is combustion."}]
    payload = route_message("Conversation", "What did I just ask?", history=history)
    assert payload["route"] == "conversation_short_term_memory"
    assert "what is fire" in payload["answer"].lower()
    assert rc2mem.build_developmental_memory_state()["knowledge_memory_records"] == 0


def test_vague_followup_does_not_retrieve_wrong_approved_concept(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    sky = rc2mem.extract_candidate_concept(
        question="What color is the sky?",
        answer="The sky usually looks blue during the day because air molecules scatter shorter blue wavelengths.",
        source_model_lane=select_model_lane("What color is the sky?"),
    )
    meaning = rc2mem.extract_candidate_concept(
        question="What is the meaning of life?",
        answer="The meaning of life can involve purpose, relationships, growth, and contribution.",
        source_model_lane=select_model_lane("What is the meaning of life?"),
    )
    assert rc2mem.approve_candidate_concept(sky)["approved"] is True
    assert rc2mem.approve_candidate_concept(meaning)["approved"] is True
    history = [
        {"role": "user", "content": "What is the meaning of life?"},
        {"role": "assistant", "content": "The meaning of life can involve purpose, relationships, growth, and contribution."},
    ]
    payload = route_message("Conversation", "tell me more", history=history)
    assert payload["intent"]["communication_act"] == "clarification_followup"
    assert payload["route"] != "developmental_concept_memory"
    assert "sky" not in payload["answer"].lower()
    assert payload["local_model_offer"]["offered"] is True
    assert payload["pending_action_suggestion"]["action_type"] == "local_model_deepening"
    rendered = render_route(payload, developer_overlay=True)
    assert "Active pending action type: local_model_deepening" in rendered
    assert "Pending action created: True" in rendered


def test_local_model_prompt_includes_recent_context(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    fake_model = tmp_path / "llama-test.gguf"
    fake_model.write_text("not a real model; ProviderManager is monkeypatched", encoding="utf-8")
    monkeypatch.setattr(
        rc2router,
        "list_available_models",
        lambda: {
            "llama": ModelSpec(
                name="llama-test",
                path=str(fake_model),
                tier=4,
                description="fake",
                context_length=4096,
                family="llama",
            )
        },
    )
    seen = {}

    class FakeProviderManager:
        def infer(self, *, model_name, prompt, task_type="open_ended", metadata=None):
            seen["prompt"] = prompt
            return CanonicalInferenceResult(
                provider="local_gguf",
                model_id=model_name,
                answer="It refers to the prior sky question.",
                raw_output="It refers to the prior sky question.",
                confidence=0.8,
                latency_seconds=0.0,
                prompt_tokens=len(prompt.split()),
                response_tokens=8,
                evidence=[],
                metadata={},
            )

    monkeypatch.setattr(rc2router, "ProviderManager", FakeProviderManager)
    history = [
        {"role": "user", "content": "What color is the sky?"},
        {"role": "assistant", "content": "The sky usually looks blue."},
    ]
    payload = route_message("Conversation", "Why does it look that way?", history=history, execute_local_model=True)
    assert payload["local_model_result"]["executed"] is True
    assert "Relevant recent turns:" in seen["prompt"]
    assert "What color is the sky?" in seen["prompt"]
    assert "resolve pronouns" in seen["prompt"]


def test_deepening_prompt_preserves_prior_answer_without_current_message_truncation(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    fake_model = tmp_path / "llama-test.gguf"
    fake_model.write_text("not a real model; ProviderManager is monkeypatched", encoding="utf-8")
    monkeypatch.setattr(
        rc2router,
        "list_available_models",
        lambda: {
            "llama": ModelSpec(
                name="llama-test",
                path=str(fake_model),
                tier=4,
                description="fake",
                context_length=4096,
                family="llama",
            )
        },
    )
    seen = {}

    class FakeProviderManager:
        def infer(self, *, model_name, prompt, task_type="open_ended", metadata=None):
            seen["prompt"] = prompt
            return CanonicalInferenceResult(
                provider="local_gguf",
                model_id=model_name,
                answer="Here is a deeper explanation.",
                raw_output="Here is a deeper explanation.",
                confidence=0.8,
                latency_seconds=0.0,
                prompt_tokens=len(prompt.split()),
                response_tokens=5,
                evidence=[],
                metadata={},
            )

    monkeypatch.setattr(rc2router, "ProviderManager", FakeProviderManager)
    prior = (
        "The meaning of life is debated by philosophers, theologians, and scientists. "
        "It can involve happiness, relationships, purpose, personal growth, and responsibility. "
        "This sentence appears late enough that the old 700-character compact question would cut it off."
    )
    message = (
        "Please expand on your previous answer for this user question.\n\n"
        "Original question: What is the meaning of life?\n\n"
        f"Previous answer: {prior}\n\n"
        "Go deeper, add useful nuance, keep it conversational, and do not ask to store memory."
    )
    payload = route_message("Conversation", message, execute_local_model=True)
    assert payload["local_model_result"]["executed"] is True
    assert "Task:\nElaborate on the prior answer" in seen["prompt"]
    assert "Previous answer to deepen:" in seen["prompt"]
    assert "This sentence appears late enough" in seen["prompt"]
    assert "Current user message:" not in seen["prompt"]


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
    assert classify_intent("great job")["intent"] == "compliment"
    assert classify_intent("nevermind")["intent"] == "cancel"
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


def test_memory_candidate_quality_allows_coherent_broad_answer(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What do most people do for fun?")
    candidate = rc2mem.extract_candidate_concept(
        question="What do most people do for fun?",
        answer="People often enjoy sports, reading, music, games, travel, and time with friends.",
        source_model_lane=payload["selected_model_lane"],
    )
    answered_payload = {**payload, "answer": "People often enjoy sports, reading, music, games, travel, and time with friends.", "confidence_score": 0.82}
    assert candidate["concept_name"] == "Common Leisure Activities"
    assert candidate_is_memory_worthy(candidate, answered_payload) is True


def test_memory_candidate_quality_rejects_vague_low_confidence_concept(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    payload = route_message("Conversation", "What most people?")
    candidate = rc2mem.extract_candidate_concept(
        question="What most people?",
        answer="I do not have enough local confidence for that.",
        source_model_lane=payload["selected_model_lane"],
    )
    assert candidate["concept_name"].startswith("What")
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
