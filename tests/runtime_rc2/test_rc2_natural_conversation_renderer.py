from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message
from orchestration.runtime.rc2_natural_conversation_renderer import build_natural_renderer_report


BAD_DEFAULT_MARKERS = [
    "Stored knowledge",
    "Reasoned connection",
    "Shared reasoning patterns",
    "No memory, graph edge",
    "Safety:",
    "Route:",
    "Developer Overlay",
    "You taught me the concept",
]


def assert_natural(answer: str) -> None:
    for marker in BAD_DEFAULT_MARKERS:
        assert marker not in answer


def test_factual_answer_is_natural():
    payload = route_message("Conversation", "What is blood pressure?")
    assert payload["route"] == "developmental_concept_memory"
    assert_natural(payload["answer"])
    assert "blood pressure" in payload["answer"].lower()


def test_wrs_answer_is_natural_prose():
    payload = route_message("Conversation", "How could allergies influence blood pressure interpretation?")
    assert payload["route"] == "working_reasoning_set"
    assert_natural(payload["answer"])
    assert "blood pressure" in payload["answer"].lower()
    assert "allerg" in payload["answer"].lower()


def test_contradiction_answer_directly_explains_compatibility():
    payload = route_message("Conversation", "Can these both be true: exercise raises blood pressure, and exercise lowers blood pressure?")
    assert payload["route"] == "contradiction_analysis"
    assert_natural(payload["answer"])
    assert "both be true" in payload["answer"].lower() or "can both" in payload["answer"].lower()


def test_analogy_answer_maps_and_limits():
    payload = route_message("Conversation", "How is photosynthesis like charging a battery?")
    assert payload["route"] == "analogy_analysis"
    assert_natural(payload["answer"])
    assert "shared pattern" in payload["answer"].lower()
    assert "where it breaks" in payload["answer"].lower()


def test_developer_overlay_retains_internal_sections():
    payload = route_message("Conversation", "How is photosynthesis like charging a battery?")
    normal = render_route(payload, developer_overlay=False)
    overlay = render_route(payload, developer_overlay=True)
    assert "Analogy analysis:" not in normal
    assert "Analogy analysis:" in overlay
    assert "Natural renderer:" in overlay


def test_local_model_consent_avoided_when_substrate_sufficient():
    payload = route_message("Conversation", "How is photosynthesis like charging a battery?")
    assert payload["route"] == "analogy_analysis"
    assert "Would you like me to ask" not in payload["answer"]


def test_local_model_offer_retained_when_substrate_insufficient():
    payload = route_message("Conversation", "What is the relation between zxqv norbital flendrome and plessar drift?")
    assert payload["route"] == "local_model_consent_required"
    assert "Would you like me to ask" in payload["answer"]


def test_explicit_new_topic_overrides_old_context():
    history = [
        {"role": "user", "content": "How is photosynthesis like charging a battery?"},
        {"role": "assistant", "content": "The shared pattern is energy storage."},
    ]
    payload = route_message("Conversation", "What is blood pressure?", history=history)
    assert payload["route"] == "developmental_concept_memory"
    assert "battery" not in payload["answer"].lower()


def test_renderer_report_generation():
    report = build_natural_renderer_report(write_reports=False)
    assert report["cases_rendered"] >= 6
    assert report["normal_output_internal_leak_count"] == 0
    assert report["overlay_completeness"] == 1.0
