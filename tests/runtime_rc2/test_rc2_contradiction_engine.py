from orchestration.runtime.rc2_contradiction_engine import (
    build_contradiction_analysis,
    build_contradiction_engine_report,
    is_contradiction_prompt,
)
from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message


def _classification(prompt: str) -> str:
    payload = build_contradiction_analysis(prompt)
    assert payload["matched"] is True
    assert payload["route"] == "contradiction_analysis"
    assert payload["provider_calls_performed"] is False
    assert payload["web_search_performed"] is False
    assert payload["training_performed"] is False
    assert payload["canonical_write_performed"] is False
    return payload["contradiction_analysis"]["compatibility_classification"]


def test_detects_contradiction_intent_variants():
    prompts = [
        "Can these both be true: blood pressure is constant, and blood pressure varies?",
        "Are these statements contradictory: blood pressure is constant; blood pressure varies.",
        "Check for contradiction: allergies are harmless, and severe allergies require emergency treatment.",
        "Do these claims conflict: photosynthesis stores energy, and photosynthesis never stores energy?",
        "Earlier you said memory is reversible; now you said memory cannot be rolled back.",
    ]
    for prompt in prompts:
        assert is_contradiction_prompt(prompt)


def test_direct_contradictions():
    cases = [
        "Can these both be true: blood pressure is always constant, and blood pressure varies with activity and stress?",
        "Can these both be true: photosynthesis consumes stored glucose, and photosynthesis stores energy in sugars?",
        "Can these both be true: all allergies are harmless, and severe allergies can require emergency treatment?",
        "Can these both be true: noncanonical memory is reversible, and noncanonical memory cannot be rolled back?",
        "Can these both be true: feedback loops adjust behavior, and feedback loops never change behavior?",
    ]
    for prompt in cases:
        assert _classification(prompt) == "direct_contradiction"


def test_conditional_compatibility_cases():
    cases = [
        "Can these both be true: exercise raises blood pressure, and exercise lowers blood pressure?",
        "Can these both be true: stress can raise blood pressure, and rest can lower blood pressure?",
        "Can these both be true: plants release oxygen, and plants consume oxygen during respiration?",
    ]
    for prompt in cases:
        assert _classification(prompt) == "conditional_compatibility"


def test_scope_time_population_and_definition_differences():
    expected = {
        "Can these both be true: allergies are immune reactions, and not every adverse drug reaction is an allergy?": "scope_difference",
        "Can these both be true: inflation is falling, and prices remain high shortly afterward?": "timeframe_difference",
        "Can these both be true: this treatment helps adults, and this treatment does not help children?": "population_difference",
        "Can these both be true: memory means stored information, and working memory means active temporary processing?": "definition_difference",
    }
    for prompt, classification in expected.items():
        assert _classification(prompt) == classification


def test_insufficient_information_and_compatible_claims():
    assert _classification("Does this evidence contradict the conclusion: the patient has symptoms, and the patient has a diagnosis?") == "insufficient_information"
    assert _classification("Can these both be true: blood pressure affects clinical interpretation, and allergies affect medication choice?") == "mutually_compatible"
    assert _classification("Can these both be true: gravity shapes orbital motion, and allergies involve immune responses?") == "unrelated_claims"


def test_router_uses_contradiction_route_before_wrs():
    payload = route_message(
        "Conversation",
        "Can these both be true: blood pressure is always constant, and blood pressure varies with activity and stress?",
    )
    assert payload["route"] == "contradiction_analysis"
    assert payload["memory_candidate"] is None
    assert payload["provider_calls_performed"] is False
    assert "conflict" in payload["answer"].lower() or "contradict" in payload["answer"].lower()


def test_recent_turn_contradiction_check():
    history = [
        {"role": "user", "content": "What is noncanonical memory?"},
        {"role": "assistant", "content": "Noncanonical memory is reversible and supports rollback."},
        {"role": "assistant", "content": "Noncanonical memory cannot be rolled back."},
    ]
    payload = route_message("Conversation", "Is that inconsistent with what you said before?", history=history)
    assert payload["route"] == "contradiction_analysis"
    assert payload["contradiction_analysis"]["compatibility_classification"] in {
        "direct_contradiction",
        "evidence_tension",
    }


def test_default_render_hides_diagnostics_and_overlay_shows_them():
    payload = route_message(
        "Conversation",
        "Can these both be true: exercise raises blood pressure, and exercise lowers blood pressure?",
    )
    normal = render_route(payload, developer_overlay=False)
    overlay = render_route(payload, developer_overlay=True)
    assert "Contradiction analysis:" not in normal
    assert "Contradiction analysis:" in overlay
    assert "classification:" in overlay


def test_non_contradiction_prompt_still_uses_other_routes():
    payload = route_message("Conversation", "How does photosynthesis relate to cellular respiration?")
    assert payload["route"] != "contradiction_analysis"


def test_natural_topic_drift_with_but_now_is_not_contradiction_route():
    prompt = "I started with debugging, but now I am thinking more about how teams avoid repeating the same mistakes."
    assert not is_contradiction_prompt(prompt)
    payload = route_message("Conversation", prompt)
    assert payload["route"] != "contradiction_analysis"
    assert payload["memory_candidate"] is None


def test_report_generation_is_read_only():
    report = build_contradiction_engine_report(write_reports=False)
    assert report["accuracy"] >= 0.85
    assert report["safety"]["training_performed"] is False
    assert report["safety"]["canonical_write_performed"] is False
    assert report["safety"]["provider_calls_performed"] is False
