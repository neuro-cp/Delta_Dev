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
