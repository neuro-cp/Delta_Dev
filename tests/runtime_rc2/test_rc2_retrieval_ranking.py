from __future__ import annotations

import json

from orchestration.runtime import rc2_developmental_concept_memory as rc2mem
from orchestration.runtime.rc2_conversational_mode_router import route_message


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
    return knowledge


def _write_concepts(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _concept(name, domain, definition, related=()):
    return {
        "concept_id": f"id-{name.lower().replace(' ', '-')}",
        "concept_name": name,
        "domain": domain,
        "short_definition": definition,
        "propositions": [definition],
        "related_concepts": list(related),
        "approval_status": "approved_noncanonical",
        "canonical": False,
        "memory_type": "knowledge",
        "quality_score": 0.9,
    }


def test_ranker_prefers_exact_domain_concept(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Static Electricity", "basic physics", "Static electricity explains charge buildup.", ("electric charge",)),
        _concept("General Energy", "energy", "Energy describes capacity for work.", ("power",)),
        _concept("Business Planning", "business", "Planning organizes business activity.", ("strategy",)),
    ])

    result = rc2mem.query_approved_concepts("Tell me about electricity.")

    assert result["matched"] is True
    assert result["matches"][0]["concept_name"] == "Static Electricity"
    assert result["provider_calls_performed"] is False if "provider_calls_performed" in result else True


def test_multi_concept_retrieval_returns_review_set_without_synthesis(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Photosynthesis", "biology", "Photosynthesis converts light into stored chemical energy.", ("cellular respiration", "energy storage")),
        _concept("Cellular Respiration", "biology", "Cellular respiration releases usable energy from sugars.", ("photosynthesis", "ATP")),
        _concept("Energy Storage", "energy", "Energy storage keeps energy available for later work.", ("biology",)),
    ])

    payload = route_message("Conversation", "How does photosynthesis relate to respiration?")

    assert payload["route"] == "developmental_multi_concept_retrieval"
    assert payload["multi_concept_retrieval"]["synthesis_readiness"] is False
    assert "Synthesis is not enabled yet" in payload["answer"]
    names = [item["concept_name"] for item in payload["concept_matches"]]
    assert "Photosynthesis" in names
    assert "Cellular Respiration" in names
    assert payload["local_model_offer"] is None if "local_model_offer" in payload else True
    assert payload["provider_calls_performed"] is False
    assert payload["training_performed"] is False
    assert payload["canonical_write_performed"] is False


def test_read_only_synthesis_trial_shows_inputs_and_labeled_inference(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Photosynthesis", "biology", "Photosynthesis stores energy from light in chemical form.", ("cellular respiration", "energy storage")),
        _concept("Cellular Respiration", "biology", "Cellular respiration releases usable energy from stored sugars.", ("photosynthesis", "ATP")),
        _concept("Energy Storage", "energy", "Energy storage keeps energy available for later work.", ("biology",)),
    ])

    payload = route_message("Conversation", "Synthesize how photosynthesis relates to respiration.")

    assert payload["route"] == "read_only_cross_concept_synthesis_trial"
    assert payload["synthesis_trial"]["synthesis_trial_only"] is True
    assert payload["synthesis_trial"]["synthesis_enabled"] is False
    assert payload["synthesis_trial"]["memory_write_performed"] is False
    assert payload["memory_candidate"] is None
    assert "Stored concepts used:" in payload["answer"]
    assert "Photosynthesis" in payload["answer"]
    assert "Cellular Respiration" in payload["answer"]
    assert "Tentative inference:" in payload["answer"]
    assert "No memory was written" in payload["answer"]
    assert payload["provider_calls_performed"] is False
    assert payload["training_performed"] is False
    assert payload["canonical_write_performed"] is False


def test_domain_browse_alias_does_not_hijack_coding(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Python Parser", "programming", "A parser turns text into structured syntax.", ("coding",)),
    ])

    payload = route_message("Conversation", "Can you help me code a parser?")

    assert payload["intent"]["intent"] == "coding"
    assert payload["route"] != "developmental_concept_domain_browse"


def test_law_concept_browse_uses_domain_alias(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Separation of Powers", "law government basics", "Separation of powers divides authority among branches.", ("government",)),
    ])

    payload = route_message("Conversation", "Do you know anything about law?")

    assert payload["route"] == "developmental_concept_domain_browse"
    assert "Separation of Powers" in payload["answer"]
    assert payload["provider_calls_performed"] is False


def test_retrieval_set_deduplicates_concept_names(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Inflation", "finance", "Inflation is a general rise in prices.", ("interest rates",)),
        _concept("Inflation", "finance", "Duplicate inflation entry.", ("prices",)),
        _concept("Interest Rates", "finance", "Interest rates shape borrowing costs.", ("inflation",)),
    ])

    result = rc2mem.retrieve_multi_concept_set("Compare inflation and interest rates.")

    names = [item["concept_name"] for item in result["matches"]]
    assert names.count("Inflation") == 1
    assert "Interest Rates" in names
    assert result["duplicate_suppression_count"] >= 1


def test_relevance_gate_does_not_match_black_holes_to_patching_holes(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Patching Holes", "home repair", "Patching holes repairs walls and surfaces.", ("drywall",)),
    ])

    result = rc2mem.query_approved_concepts("Tell me about black holes.")

    assert result["matched"] is False


def test_unknown_topic_offer_preserves_topic_without_false_retrieval(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Patching Holes", "home repair", "Patching holes repairs walls and surfaces.", ("drywall",)),
    ])

    payload = route_message("Conversation", "Tell me about black holes.")
    history = [
        {"role": "user", "content": "Tell me about black holes."},
        {"role": "assistant", "content": payload["answer"]},
    ]
    followup = route_message("Conversation", "How big can they get?", history=history)

    assert payload["route"] == "local_model_consent_required"
    assert "black holes" in payload["answer"].lower()
    assert payload.get("concept_matches") in (None, [])
    assert followup["route"] == "conversation_short_term_memory"
    assert "black holes" in followup["answer"].lower()


def test_session_fact_bypasses_color_concept_retrieval(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Daytime Sky Color", "", "The sky usually looks blue.", ("light scattering",)),
        _concept("Moon Color Appearance", "", "The moon can appear gray.", ("surface reflection",)),
    ])

    history = []
    first = route_message("Conversation", "Pretend my favorite color is green.", history=history)
    history.extend([
        {"role": "user", "content": "Pretend my favorite color is green."},
        {"role": "assistant", "content": first["answer"]},
    ])
    second = route_message("Conversation", "What's my favorite color in this conversation?", history=history)

    assert first["route"] == "conversation_short_term_memory"
    assert second["route"] == "conversation_short_term_memory"
    assert "green" in second["answer"].lower()
    assert second.get("concept_matches") in (None, [])


def test_browse_jump_avoids_recent_domain_when_possible(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Approval Workflow", "DELTA architecture itself", "Approval workflow controls review.", ("governance",)),
        _concept("Audit Trail", "DELTA architecture itself", "Audit trails record decisions.", ("governance",)),
        _concept("Canonical Memory", "DELTA architecture itself", "Canonical memory is the governed long-term store.", ("governance",)),
        _concept("Static Electricity", "basic physics", "Static electricity explains charge buildup.", ("electric charge",)),
    ])

    first = route_message("Conversation", "Tell me something you know.")
    history = [
        {"role": "user", "content": "Tell me something you know."},
        {"role": "assistant", "content": first["answer"]},
    ]
    second = route_message("Conversation", "Something completely different.", history=history)

    assert second["route"] == "developmental_concept_browse_followup"
    assert "Static Electricity" in second["answer"]


def test_direct_exact_multiword_lookup_selects_base_concept():
    payload = route_message("Conversation", "tell me about activation energy")

    assert payload["route"] == "developmental_concept_memory"
    assert payload["concept_matches"][0]["concept_name"] == "Activation Energy (Chemistry)"
    assert "Baseload" not in payload["answer"]


def test_accepted_noncanonical_concept_retrievable_by_exact_title(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("How To Swim", "", "Swimming starts with water safety, floating, kicking, breathing, and supervised practice."),
    ])

    payload = route_message("Conversation", "How To Swim")

    assert payload["route"] == "developmental_concept_memory"
    assert payload["concept_matches"][0]["concept_name"] == "How To Swim"
    assert "noncanonical reviewed memory" in payload["answer"].lower()
    assert payload.get("local_model_offer") is None
    assert payload["canonical_write_performed"] is False


def test_accepted_noncanonical_concept_retrievable_by_tell_me_wrapper(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("How To Swim", "", "Swimming starts with water safety, floating, kicking, breathing, and supervised practice."),
    ])

    payload = route_message("Conversation", "tell me how to swim")

    assert payload["route"] == "developmental_concept_memory"
    assert payload["concept_matches"][0]["concept_name"] == "How To Swim"
    assert "noncanonical reviewed memory" in payload["answer"].lower()
    assert payload.get("local_model_offer") is None
    assert payload["provider_calls_performed"] is False
    assert payload["training_performed"] is False
    assert payload["canonical_write_performed"] is False


def test_accepted_noncanonical_concept_retrievable_by_bare_phrase(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("How To Swim", "", "Swimming starts with water safety, floating, kicking, breathing, and supervised practice."),
    ])

    payload = route_message("Conversation", "how to swim")

    assert payload["route"] == "developmental_concept_memory"
    assert payload["concept_matches"][0]["concept_name"] == "How To Swim"
    assert "local reasoning model" not in payload["answer"].lower()


def test_unrelated_unknown_query_still_falls_back_after_noncanonical_recall(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("How To Swim", "", "Swimming starts with water safety, floating, kicking, breathing, and supervised practice."),
    ])

    payload = route_message("Conversation", "tell me how to weld underwater")

    assert payload["route"] == "local_model_consent_required"
    assert payload.get("concept_matches") in (None, [])
    assert (payload.get("local_model_offer") or {}).get("offered") is True


def test_active_noncanonical_concept_answers_practical_tip_from_stored_content(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept(
            "How To Swim",
            "",
            "Swimming starts with water safety, floating, kicking, breathing, and supervised practice.",
        ) | {
            "propositions": [
                "Start with short supervised practice sessions.",
                "Practice floating before trying longer swimming.",
                "Focus on breathing naturally and relaxing your muscles.",
            ],
        },
    ])
    first = route_message("Conversation", "tell me how to swim")
    history = [
        {"role": "user", "content": "tell me how to swim"},
        {"role": "assistant", "content": first["answer"]},
        {"role": "topic_state", "content": json.dumps(first["conversation_topic_state"], sort_keys=True)},
    ]

    followup = route_message("Conversation", "give me another practical tip", history=history)

    assert followup["route"] == "session_memory"
    assert "noncanonical reviewed memory" in followup["answer"].lower()
    assert "How To Swim" in followup["answer"]
    assert any(term in followup["answer"].lower() for term in ("practice", "floating", "breathing", "supervised"))
    assert followup.get("local_model_offer") is None
    assert followup["provider_calls_performed"] is False
    assert followup["canonical_write_performed"] is False


def test_unrelated_practical_tip_request_still_falls_back(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("How To Swim", "", "Swimming starts with water safety and supervised practice."),
    ])

    payload = route_message("Conversation", "give me a practical tip for underwater welding")

    assert payload["route"] == "local_model_consent_required"
    assert (payload.get("local_model_offer") or {}).get("offered") is True
    assert payload.get("concept_matches") in (None, [])


def test_domain_list_followup_selects_listed_multiword_concept():
    first = route_message("Conversation", "what about chemistry?")
    history = [
        {"role": "user", "content": "what about chemistry?"},
        {"role": "assistant", "content": first["answer"]},
    ]

    second = route_message("Conversation", "tell me about activation energy", history=history)

    assert first["route"] == "developmental_concept_domain_browse"
    assert "Activation Energy" in first["answer"]
    assert second["route"] == "developmental_concept_memory"
    assert second["concept_matches"][0]["concept_name"] == "Activation Energy (Chemistry)"


def test_exact_phrase_outranks_broad_domain_token():
    exact = route_message("Conversation", "tell me about activation energy")
    broad = route_message("Conversation", "what about energy?")

    assert exact["concept_matches"][0]["domain"] == "chemistry"
    assert exact["concept_matches"][0]["concept_name"] == "Activation Energy (Chemistry)"
    assert broad["route"] == "developmental_concept_domain_browse"
    assert all(item["domain"] == "energy" for item in broad["concept_matches"])


def test_center_of_mass_does_not_collapse_to_mass():
    payload = route_message("Conversation", "tell me about center of mass")

    assert payload["route"] == "developmental_concept_memory"
    assert "Center of Mass" in payload["concept_matches"][0]["concept_name"]
    assert payload["concept_matches"][0]["domain"] == "basic physics"


def test_approval_workflow_does_not_collapse_to_workflow():
    payload = route_message("Conversation", "tell me about approval workflow")

    assert payload["route"] == "developmental_concept_memory"
    assert "Approval Workflow" in payload["concept_matches"][0]["concept_name"]
    assert payload["concept_matches"][0]["domain"] == "DELTA architecture itself"


def test_broad_energy_topic_still_browses_energy_domain():
    payload = route_message("Conversation", "what about energy?")

    assert payload["route"] == "developmental_concept_domain_browse"
    assert payload["concept_matches"]
    assert all(item["domain"] == "energy" for item in payload["concept_matches"])


def test_single_word_mechanism_binds_to_active_topic_before_global_retrieval(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Activation Energy", "chemistry", "Activation Energy is the energy barrier for a reaction.") | {
            "propositions": ["Activation Energy mechanism depends on particles reaching a transition state."],
        },
        _concept("Acid Base Reactions Mechanism", "chemistry", "Acid base mechanism describes proton transfer."),
    ])
    history = [
        {"role": "topic_state", "content": json.dumps({
            "state_kind": "TOPIC_SWITCH",
            "topic": "Activation Energy",
            "last_visible_answer": "Got it. Let's talk about Activation Energy.",
            "source_route": "social_conversation",
            "entities": ["Activation Energy"],
            "supersedes_anchor": True,
        })},
    ]

    payload = route_message("Conversation", "mechanism", history=history)

    assert payload["route"] == "session_memory"
    assert "Activation Energy" in payload["answer"]
    assert "transition state" in payload["answer"]
    assert payload.get("concept_matches") in (None, [])
    assert payload["conversation_topic_state"]["topic"] == "Activation Energy"
    assert payload["provider_calls_performed"] is False
    assert payload["canonical_write_performed"] is False


def test_single_word_limits_binds_to_active_topic_before_global_retrieval(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Activation Energy", "chemistry", "Activation Energy is the energy barrier for a reaction.") | {
            "propositions": ["Activation Energy limits include temperature, catalysts, and reaction pathway assumptions."],
        },
        _concept("Constitutional Limits Evidence Standard", "law", "Constitutional limits evidence belongs to law."),
    ])
    history = [
        {"role": "topic_state", "content": json.dumps({
            "state_kind": "TOPIC_SWITCH",
            "topic": "Activation Energy",
            "last_visible_answer": "Got it. Let's talk about Activation Energy.",
            "source_route": "social_conversation",
            "entities": ["Activation Energy"],
            "supersedes_anchor": True,
        })},
    ]

    payload = route_message("Conversation", "limits", history=history)

    assert payload["route"] == "session_memory"
    assert "Activation Energy" in payload["answer"]
    assert "temperature" in payload["answer"]
    assert "Constitutional Limits" not in payload["answer"]
    assert payload.get("concept_matches") in (None, [])
    assert payload["conversation_topic_state"]["topic"] == "Activation Energy"
    assert payload["provider_calls_performed"] is False
    assert payload["canonical_write_performed"] is False


def test_explicit_full_concept_request_still_retrieves_other_concept(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Activation Energy", "chemistry", "Activation Energy is the energy barrier for a reaction."),
        _concept("Acid Base Reactions Mechanism", "chemistry", "Acid base mechanism describes proton transfer."),
    ])
    history = [
        {"role": "topic_state", "content": json.dumps({
            "state_kind": "TOPIC_SWITCH",
            "topic": "Activation Energy",
            "last_visible_answer": "Got it. Let's talk about Activation Energy.",
            "source_route": "social_conversation",
            "entities": ["Activation Energy"],
            "supersedes_anchor": True,
        })},
    ]

    payload = route_message("Conversation", "tell me about Acid Base Reactions Mechanism", history=history)

    assert payload["route"] == "developmental_concept_memory"
    assert payload["concept_matches"][0]["concept_name"] == "Acid Base Reactions Mechanism"


def test_single_word_aspect_without_active_topic_keeps_existing_safe_path(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, [
        _concept("Acid Base Reactions Mechanism", "chemistry", "Acid base mechanism describes proton transfer."),
    ])

    payload = route_message("Conversation", "mechanism")

    assert payload["route"] == "developmental_concept_memory"
    assert "Acid Base Reactions Mechanism" in payload["concept_matches"][0]["concept_name"]
    assert payload["provider_calls_performed"] is False
    assert payload["canonical_write_performed"] is False


def _phase_b_concepts():
    return [
        _concept("How To Swim", "", "Swimming starts with water safety, floating, kicking, breathing, and supervised practice."),
        _concept("Activation Energy", "chemistry", "Activation Energy is the energy barrier for a reaction."),
        _concept("Constitutional Limits Evidence Standard", "law", "Constitutional limits evidence belongs to law."),
    ]


def _append_history(history, prompt, payload):
    history.extend([
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": payload["answer"]},
    ])
    if payload.get("conversation_topic_state"):
        history.append({"role": "topic_state", "content": json.dumps(payload["conversation_topic_state"], sort_keys=True)})


def _phase_b_history():
    history = []
    for prompt in [
        "tell me how to swim",
        "let's talk about activation energy",
        "tell me about Constitutional Limits Evidence Standard",
    ]:
        payload = route_message("Conversation", prompt, history=history)
        _append_history(history, prompt, payload)
    return history


def test_go_back_to_prior_topic_restores_how_to_swim(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, _phase_b_concepts())
    history = _phase_b_history()

    payload = route_message("Conversation", "go back to how to swim", history=history)

    assert payload["route"] == "topic_return"
    assert payload["conversation_topic_state"]["topic"] == "How To Swim"
    assert payload["conversation_topic_state"]["supersedes_anchor"] is True
    assert "How To Swim" in payload["answer"]
    assert "Constitutional Limits" not in payload["answer"]
    assert payload["provider_calls_performed"] is False
    assert payload["canonical_write_performed"] is False

    _append_history(history, "go back to how to swim", payload)
    followup = route_message("Conversation", "tell me more", history=history)

    assert followup["route"] == "session_memory"
    assert followup["conversation_topic_state"]["topic"] == "How To Swim"
    assert "How To Swim" in followup["answer"]
    assert "Constitutional Limits" not in followup["answer"]


def test_return_to_prior_topic_forms_restore_how_to_swim(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, _phase_b_concepts())

    for phrase in ("return to how to swim", "let's go back to how to swim", "back to how to swim"):
        payload = route_message("Conversation", phrase, history=_phase_b_history())

        assert payload["route"] == "topic_return"
        assert payload["conversation_topic_state"]["topic"] == "How To Swim"
        assert payload["provider_calls_performed"] is False
        assert payload["canonical_write_performed"] is False


def test_return_target_can_resolve_from_approved_concept_without_prior_topic(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, _phase_b_concepts())
    current = route_message("Conversation", "tell me about Constitutional Limits Evidence Standard")
    history = [
        {"role": "user", "content": "tell me about Constitutional Limits Evidence Standard"},
        {"role": "assistant", "content": current["answer"]},
        {"role": "topic_state", "content": json.dumps(current["conversation_topic_state"], sort_keys=True)},
    ]

    payload = route_message("Conversation", "go back to how to swim", history=history)

    assert payload["route"] == "topic_return"
    assert payload["conversation_topic_state"]["topic"] == "How To Swim"
    assert "How To Swim" in payload["answer"]
    assert "Constitutional Limits" not in payload["answer"]
    assert payload["provider_calls_performed"] is False
    assert payload["canonical_write_performed"] is False


def test_unknown_return_target_falls_back_without_model_or_memory_write(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, _phase_b_concepts())
    history = _phase_b_history()

    payload = route_message("Conversation", "return to orbital sandwich", history=history)

    assert payload["route"] == "topic_return_unresolved"
    assert "do not have a prior or approved topic" in payload["answer"]
    assert payload["conversation_topic_state"]["topic"] == ""
    assert payload["conversation_topic_state"]["state_kind"] == "NONE"
    assert payload.get("local_model_offer") is None
    assert payload["provider_calls_performed"] is False
    assert payload["canonical_write_performed"] is False


def test_explicit_topic_switch_remains_unchanged_after_return_parser(monkeypatch, tmp_path):
    knowledge = _isolate_rc2_store(monkeypatch, tmp_path)
    _write_concepts(knowledge, _phase_b_concepts())

    payload = route_message("Conversation", "let's talk about activation energy")

    assert payload["route"] == "social_conversation"
    assert payload["conversation_topic_state"]["topic"] == "activation energy"
    assert payload["provider_calls_performed"] is False
    assert payload["canonical_write_performed"] is False
