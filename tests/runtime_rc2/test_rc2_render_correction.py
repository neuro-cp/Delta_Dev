from orchestration.runtime.rc2_conversational_mode_router import route_message
from orchestration.runtime.rc2_render_correction import build_render_correction_payload, is_render_correction_request


def _history(user: str, assistant: str):
    return [
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]


PRIOR_ANSWER = (
    "Blood pressure reflects cardiac output, vascular resistance, and blood volume. "
    "Allergy history can affect medication choices and emergency planning. "
    "The important operator evidence is whether the proposed decision stayed bounded and recoverable."
)


def test_retry_previous_answer_is_render_correction_not_retrieval():
    payload = route_message("Conversation", "Retry the previous answer.", history=_history("Explain this.", PRIOR_ANSWER))

    assert payload["route"] == "render_correction"
    assert "Blood pressure" in payload["answer"]
    assert payload["memory_candidate"] is None
    assert payload["provider_calls_performed"] is False
    assert payload["render_correction"]["operation"] == "RENDER_CORRECTION"
    assert payload["render_correction"]["scope"] == "presentation_only"


def test_requested_headings_apply_to_existing_semantic_answer():
    message = """Use exactly these headings:
1. What I inspected
2. Bounded next operator step
3. Evidence that would make this freeze-relevant
4. What remains unproven

Do not write memory.
Do not call providers."""
    payload = route_message("Conversation", message, history=_history("Pilot task.", PRIOR_ANSWER))

    assert payload["route"] == "render_correction"
    assert payload["answer"].startswith("1. What I inspected")
    assert "2. Bounded next operator step" in payload["answer"]
    assert "No memory was written" in payload["answer"]
    assert "No provider was called" in payload["answer"]
    assert payload["memory_candidate"] is None


def test_repeated_heading_correction_does_not_duplicate_section_labels():
    previous = """1. What I inspected
- The topic is a governed AI system preparing for a real operator pilot.

2. Bounded next operator step
- Run one bounded operator-reviewed session.

3. Evidence that would make this freeze-relevant
- Record operator decision, reason, safety boundaries, and recovery.

4. What remains unproven
- It remains unproven whether this holds across multiple sessions.

No memory was written. No provider was called."""
    message = """Retry the previous answer.

Use exactly these headings:
1. What I inspected
2. Bounded next operator step
3. Evidence that would make this freeze-relevant
4. What remains unproven

Do not write memory.
Do not call providers."""
    payload = route_message("Conversation", message, history=_history("Format it.", previous))
    answer = payload["answer"]

    assert payload["route"] == "render_correction"
    assert "What I inspected - What I inspected" not in answer
    assert "What I inspected The topic" not in answer
    assert "Evidence that would make this freeze-relevant - Evidence" not in answer
    assert "Evidence that would make this freeze-relevant Record" not in answer
    assert "2. Bounded next operator step\n- Run one bounded operator-reviewed session." in answer
    assert answer.count("1. What I inspected") == 1
    assert payload["memory_candidate"] is None


def test_same_answer_but_shorter_stays_local_and_concise():
    payload = route_message("Conversation", "Same answer but shorter. Do not call providers.", history=_history("Explain this.", PRIOR_ANSWER))

    assert payload["route"] == "render_correction"
    assert len(payload["answer"]) < len(PRIOR_ANSWER) + 80
    assert "No provider was called" in payload["answer"]
    assert payload["provider_calls_performed"] is False


def test_summarize_previous_answer_is_render_correction():
    payload = route_message("Conversation", "Summarize the previous answer in two sentences.", history=_history("Explain this.", PRIOR_ANSWER))

    assert payload["route"] == "render_correction"
    assert "Blood pressure" in payload["answer"]
    assert "Allergy history" in payload["answer"]
    assert payload["memory_candidate"] is None
    assert payload["provider_calls_performed"] is False
    assert payload["web_search_performed"] is False
    assert payload.get("local_model_offer") is None


def test_rewrite_as_bullets_preserves_topic_without_specialist_routes():
    payload = route_message("Conversation", "Rewrite that as bullet points.", history=_history("Explain blood pressure.", PRIOR_ANSWER))

    assert payload["route"] == "render_correction"
    assert payload["answer"].startswith("- ")
    assert "Blood pressure" in payload["answer"]
    assert payload.get("concept_matches") == []


def test_research_latest_request_is_not_performed_inside_render_correction():
    payload = route_message(
        "Conversation",
        "Rewrite the answer and also research the latest documentation. Do not call providers.",
        history=_history("Explain governance.", PRIOR_ANSWER),
    )

    assert payload["route"] == "render_correction"
    assert "External research was not performed" in payload["answer"]
    assert payload["provider_calls_performed"] is False
    assert payload["web_search_performed"] is False


def test_render_correction_detection_is_generic():
    assert is_render_correction_request("Keep the content but reorganize it.")
    assert is_render_correction_request("You ignored the format. Try again.")
    assert is_render_correction_request("Same answer but longer.")
    assert is_render_correction_request("Summarize the previous answer in two sentences.")
    assert build_render_correction_payload("What is blood pressure?", _history("Q", PRIOR_ANSWER)) is None
