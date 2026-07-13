from __future__ import annotations

import json

from orchestration.runtime.rc2_conversational_mode_router import route_message


def _append_turn(history: list[dict[str, str]], message: str, payload: dict[str, object]) -> None:
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": str(payload.get("answer") or "")})
    anchor = payload.get("active_topic_anchor")
    if isinstance(anchor, dict) and anchor:
        history.append({"role": "anchor", "content": json.dumps(anchor)})


def test_explicit_new_topic_invalidates_stale_concept_anchor():
    history: list[dict[str, str]] = []

    first = route_message("Conversation", "Tell me about Advanced Operator Mode Evidence Standard", history=history)
    _append_turn(history, "Tell me about Advanced Operator Mode Evidence Standard", first)
    assert first["route"] == "developmental_concept_memory"

    physics = route_message("Conversation", "what is the first concept that comes to mind related to physics", history=history)
    _append_turn(history, "what is the first concept that comes to mind related to physics", physics)

    assert physics["route"] == "local_conversation_model_lane"
    assert "motion" in str(physics["answer"]).lower()
    assert "advanced operator mode evidence standard" not in str(physics["answer"]).lower()
    assert physics["routing_observability"]["explicit_new_topic_request"] is True
    assert physics["routing_observability"]["memory_retrieval_bypassed"] is True

    followup = route_message("Conversation", "tell me more", history=history)
    assert followup["route"] == "session_memory"
    assert "physics" in str(followup["answer"]).lower()
    assert "advanced operator mode evidence standard" not in str(followup["answer"]).lower()
    assert followup["routing_observability"]["anchor_available"] is False


def test_greeting_ignores_stale_anchor_state():
    history = [
        {
            "role": "anchor",
            "content": json.dumps({
                "active_concept_id": "stale",
                "active_concept_name": "Advanced Operator Mode Evidence Standard",
            }),
        }
    ]

    payload = route_message("Conversation", "hi", history=history)

    assert payload["route"] == "social_conversation"
    assert "hi" in str(payload["answer"]).lower()
    assert payload["memory_candidate"] is None
    assert payload["routing_observability"]["selected_route"] == "social_conversation"
