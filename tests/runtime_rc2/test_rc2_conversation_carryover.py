from __future__ import annotations

import json

from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message


def _anchor_from_payload(payload: dict) -> list[dict[str, str]]:
    anchor = payload.get("active_topic_anchor")
    assert isinstance(anchor, dict)
    assert anchor.get("active_concept_name")
    return [{"role": "anchor", "content": json.dumps(anchor, sort_keys=True)}]


def test_sky_blue_tell_me_more_uses_active_anchor_without_local_model_offer() -> None:
    first = route_message("Conversation", "Why is the sky blue")
    history = _anchor_from_payload(first)

    followup = route_message("Conversation", "tell me more", history=history)

    assert followup["route"] == "developmental_concept_anchor_followup"
    assert "Daytime Sky Color" in followup["answer"]
    assert followup.get("local_model_offer") is None
    assert followup["provider_calls_performed"] is False
    assert followup["training_performed"] is False
    assert followup["canonical_write_performed"] is False


def test_sky_blue_what_else_stays_near_active_science_topic() -> None:
    first = route_message("Conversation", "Why is the sky blue")
    history = _anchor_from_payload(first)

    followup = route_message("Conversation", "what else", history=history)

    assert followup["route"] == "developmental_concept_anchor_browse"
    assert "Staying with `Daytime Sky Color`" in followup["answer"]
    assert "Advanced Operator Mode" not in followup["answer"]
    assert followup.get("local_model_offer") is None


def test_sky_blue_example_uses_anchor() -> None:
    first = route_message("Conversation", "Why is the sky blue")
    history = _anchor_from_payload(first)

    followup = route_message("Conversation", "give me an example", history=history)

    assert followup["route"] == "developmental_concept_anchor_followup"
    assert "Daytime Sky Color" in followup["answer"]
    assert followup["canonical_write_performed"] is False


def test_sky_blue_relates_to_sunsets_uses_anchor() -> None:
    first = route_message("Conversation", "Why is the sky blue")
    history = _anchor_from_payload(first)

    followup = route_message("Conversation", "how does that relate to sunsets", history=history)

    assert followup["route"] == "developmental_concept_anchor_followup"
    assert "sunsets" in followup["answer"].lower()
    assert "Daytime Sky Color" in followup["answer"]


def test_explicit_new_topic_updates_concept_anchor() -> None:
    sky = route_message("Conversation", "Why is the sky blue")
    assert sky["active_topic_anchor"]["active_concept_name"] == "Daytime Sky Color"

    moon = route_message("Conversation", "what color is the moon", history=_anchor_from_payload(sky))
    assert moon["route"] == "developmental_concept_memory"
    assert moon["active_topic_anchor"]["active_concept_name"] != "Daytime Sky Color"


def test_sun_is_blue_question_is_corrected_not_blindly_sky_answered() -> None:
    payload = route_message("Conversation", "what do you know about why the sun is blue")

    assert payload["route"] == "conversation_clarified_misframed_question"
    assert "Sun is not normally blue" in payload["answer"]
    assert "sky appears blue" in payload["answer"]


def test_render_route_hides_developer_overlay_by_default() -> None:
    payload = route_message("Conversation", "Why is the sky blue")

    rendered = render_route(payload)

    assert "--- Developer Overlay ---" not in rendered
    assert "Chosen lane:" not in rendered


def test_render_route_shows_developer_overlay_when_requested() -> None:
    payload = route_message("Conversation", "Why is the sky blue")

    rendered = render_route(payload, developer_overlay=True)

    assert "--- Developer Overlay ---" in rendered
