from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message
from orchestration.runtime.rc2_route_arbitration import SAFETY_FIELDS, safety_schema_complete


def _history(*turns):
    history = []
    for user, assistant in turns:
        history.append({"role": "user", "content": user})
        history.append({"role": "assistant", "content": assistant})
    return history


def test_contradiction_prompt_with_pronoun_yields_past_working_memory():
    history = _history(
        ("What is noncanonical memory?", "Noncanonical memory is reversible and supports rollback."),
        ("What else?", "Noncanonical memory cannot be rolled back."),
    )
    payload = route_message("Conversation", "Is that inconsistent with what you said before?", history=history)
    assert payload["route"] == "contradiction_analysis"
    arbitration = payload["route_arbitration"]
    assert arbitration["selected_group"] == "contradiction_analysis"
    assert any(item["route"] == "working_memory_reference_resolution" for item in arbitration["candidate_routes"])


def test_analogy_prompt_with_overlap_yields_past_wrs():
    payload = route_message("Conversation", "Test this analogy: photosynthesis and respiration are like charging and discharging. What works and what breaks?")
    assert payload["route"] == "analogy_analysis"
    arbitration = payload["route_arbitration"]
    assert arbitration["selected_group"] == "analogy_analysis"
    assert any(item["route"] == "working_reasoning_set" for item in arbitration["candidate_routes"])


def test_missing_evidence_without_history_is_not_memory_orphan():
    payload = route_message("Conversation", "What evidence is missing before concluding inflation will fall after interest rates rise?")
    assert payload["route"] in {"working_reasoning_set", "developmental_multi_concept_retrieval", "developmental_concept_memory"}
    assert payload["route"] != "session_memory"


def test_orphan_context_dependent_prompt_asks_for_clarification():
    payload = route_message("Conversation", "Explain that.", history=[])
    assert payload["route"] == "session_memory"
    assert "need" in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False


def test_explicit_entity_lookup_overrides_stale_context():
    history = _history(("How is photosynthesis like charging a battery?", "The analogy works around energy storage."))
    payload = route_message("Conversation", "What is blood pressure?", history=history)
    assert payload["route"] != "session_memory"
    assert "blood pressure" in payload["answer"].lower()
    assert "battery" not in payload["answer"].lower()


def test_named_branch_return_uses_named_topic():
    history = _history(
        ("Let's discuss photosynthesis.", "Photosynthesis stores light energy in chemical bonds."),
        ("Now switch to planning.", "Planning organizes actions toward goals."),
        ("Talk about allergies.", "Allergies involve immune responses to allergens."),
    )
    payload = route_message("Conversation", "Go back to planning.", history=history)
    assert payload["route"] == "session_memory"
    assert "planning" in payload["answer"].lower()


def test_pure_social_turn_does_not_trigger_cognitive_route():
    payload = route_message("Conversation", "Good job.")
    assert payload["route"] in {"social_conversation", "local_conversation_scaffold"}
    assert payload.get("concept_matches") in (None, [])
    assert payload["provider_calls_performed"] is False


def test_social_plus_cognitive_command_continues_context():
    history = _history(("Explain photosynthesis.", "Photosynthesis stores light energy in chemical bonds."))
    payload = route_message("Conversation", "Okay, continue explaining photosynthesis.", history=history)
    assert "photosynthesis" in payload["answer"].lower()
    assert payload["route"] in {"session_memory", "developmental_concept_memory", "working_reasoning_set"}


def test_safety_metadata_complete_for_representative_routes():
    cases = [
        ("Good job.", []),
        ("What is blood pressure?", []),
        ("How is photosynthesis like charging a battery?", []),
        ("Can these both be true: blood pressure varies with stress, and blood pressure never changes?", []),
        ("Tell me more.", _history(("What is blood pressure?", "Blood pressure reflects cardiovascular state."))),
    ]
    for message, history in cases:
        payload = route_message("Conversation", message, history=history)
        assert safety_schema_complete(payload), message
        assert set(SAFETY_FIELDS).issubset(payload.keys())
        assert payload["safety_metadata"]["behavioral_safety_passed"] is True


def test_developer_overlay_contains_arbitration_and_safety_metadata():
    payload = route_message("Conversation", "How is photosynthesis like charging a battery?")
    rendered = render_route(payload, developer_overlay=True)
    assert "Route arbitration:" in rendered
    assert "Safety metadata:" in rendered
    assert "selected_group: analogy_analysis" in rendered

