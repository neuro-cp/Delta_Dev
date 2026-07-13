import json
import queue
import time
import tkinter as tk

import DELTA
from DELTA import DeltaApp
from orchestration.runtime import delta_1_4_live_wikipedia_runtime as live_mod
from orchestration.runtime.delta_1_4_live_wikipedia_runtime import (
    handle_live_chat,
    start_live_wikipedia_runtime,
)
from orchestration.runtime.rc2_cognitive_episode import build_cognitive_episode
from orchestration.runtime.rc2_conversational_mode_router import route_message


OLD_ANCHOR = {
    "active_concept_id": "old",
    "active_concept_name": "Advanced Operator Mode Evidence Standard",
    "last_user_question": "Tell me about Advanced Operator Mode Evidence Standard",
    "last_answer_summary": "Advanced Operator Mode Evidence Standard details.",
    "retrieved_concept_ids": ["old"],
    "retrieved_concept_names": ["Advanced Operator Mode Evidence Standard"],
}


def _history_with_anchor(*turns, topic_state=None):
    history = []
    for user, assistant in turns:
        history.append({"role": "user", "content": user})
        history.append({"role": "assistant", "content": assistant})
    history.append({"role": "anchor", "content": json.dumps(OLD_ANCHOR)})
    if topic_state:
        history.append({"role": "topic_state", "content": json.dumps(topic_state)})
    return history


def test_brainstorming_promotes_substantive_topic_that_supersedes_old_anchor():
    payload = route_message(
        "Conversation",
        "what is the first concept that comes to mind related to physics",
        history=_history_with_anchor(("Tell me about Advanced Operator Mode Evidence Standard", "Advanced Operator Mode Evidence Standard details.")),
    )

    state = payload["conversation_topic_state"]
    assert payload["route"] == "local_conversation_model_lane"
    assert state["state_kind"] == "SUBSTANTIVE_TOPIC"
    assert state["topic"] == "motion in physics"
    assert state["supersedes_anchor"] is True


def test_followup_uses_promoted_physics_topic_before_concept_anchor():
    topic_state = {
        "state_kind": "SUBSTANTIVE_TOPIC",
        "topic": "motion in physics",
        "last_user_prompt": "what is the first concept that comes to mind related to physics",
        "last_visible_answer": "The first concept that comes to mind is motion in physics.",
        "source_route": "local_conversation_model_lane",
        "entities": ["motion in physics"],
        "supersedes_anchor": True,
    }
    history = _history_with_anchor(
        ("what is the first concept that comes to mind related to physics", "The first concept that comes to mind is motion in physics."),
        topic_state=topic_state,
    )

    payload = route_message("Conversation", "tell me more", history=history)

    assert payload["route"] == "session_memory"
    assert "motion" in payload["answer"].lower()
    assert "advanced operator mode" not in payload["answer"].lower()
    assert not (payload.get("local_model_offer") or {}).get("offered")


def test_sky_followup_elaborates_from_prior_visible_answer_without_model_consent():
    history = [
        {"role": "user", "content": "what color is the sky"},
        {"role": "assistant", "content": "The sky usually looks blue because air molecules scatter shorter blue wavelengths."},
        {"role": "topic_state", "content": json.dumps({
            "state_kind": "SUBSTANTIVE_TOPIC",
            "topic": "sky",
            "last_user_prompt": "what color is the sky",
            "last_visible_answer": "The sky usually looks blue because air molecules scatter shorter blue wavelengths.",
            "source_route": "local_conversation_model_lane",
            "entities": ["sky"],
            "supersedes_anchor": True,
        })},
    ]

    payload = route_message("Conversation", "why is that", history=history)

    assert payload["route"] == "session_memory"
    assert "wavelength" in payload["answer"].lower() or "scatter" in payload["answer"].lower()
    assert not (payload.get("local_model_offer") or {}).get("offered")


def test_limit_followup_answers_with_exception_frame_for_current_topic():
    history = [
        {"role": "user", "content": "what color is the sky"},
        {"role": "assistant", "content": "The sky usually looks blue because air molecules scatter shorter blue wavelengths."},
        {"role": "topic_state", "content": json.dumps({
            "state_kind": "SUBSTANTIVE_TOPIC",
            "topic": "sky",
            "last_user_prompt": "what color is the sky",
            "last_visible_answer": "The sky usually looks blue because air molecules scatter shorter blue wavelengths.",
            "source_route": "local_conversation_model_lane",
            "entities": ["sky"],
            "supersedes_anchor": True,
        })},
    ]

    payload = route_message("Conversation", "does it always look blue", history=history)
    answer = payload["answer"].lower()

    assert payload["route"] == "session_memory"
    assert payload["cognitive_episode"]["active_topic"] == "sky"
    assert "which one do you mean" not in answer
    assert "no" in answer or "not always" in answer
    assert "blue" in answer
    assert any(term in answer for term in ("condition", "context", "light", "evidence"))


def test_neutral_limit_followup_uses_general_exception_frame():
    history = [
        {"role": "user", "content": "what is architecture"},
        {"role": "assistant", "content": "Architecture usually organizes constraints, materials, and tradeoffs."},
        {"role": "topic_state", "content": json.dumps({
            "state_kind": "SUBSTANTIVE_TOPIC",
            "topic": "architecture",
            "last_user_prompt": "what is architecture",
            "last_visible_answer": "Architecture usually organizes constraints, materials, and tradeoffs.",
            "source_route": "local_conversation_model_lane",
            "entities": ["architecture"],
            "supersedes_anchor": True,
        })},
    ]

    payload = route_message("Conversation", "does it always work that way", history=history)
    answer = payload["answer"].lower()

    assert payload["route"] == "session_memory"
    assert payload["cognitive_episode"]["active_topic"] == "architecture"
    assert "architecture" in answer
    assert "not always" in answer or "does not always" in answer
    assert "sky" not in answer


def test_canonical_identity_deduplicates_article_variants_in_ambiguity():
    episode = build_cognitive_episode(
        "does it always look blue",
        [
            {"role": "user", "content": "what color is the sky"},
            {"role": "assistant", "content": "The sky usually looks blue."},
            {"role": "topic_state", "content": json.dumps({
                "state_kind": "FOLLOWUP",
                "topic": "sky",
                "last_user_prompt": "why is that",
                "last_visible_answer": "The sky usually looks blue.",
                "source_route": "session_memory",
                "entities": ["sky"],
                "supersedes_anchor": True,
            })},
        ],
        current_route="session_memory",
        current_payload={
            "route": "session_memory",
            "answer": "No, not always.",
            "conversation_topic_state": {
                "state_kind": "FOLLOWUP",
                "topic": "sky",
                "last_user_prompt": "does it always look blue",
                "last_visible_answer": "No, not always.",
                "source_route": "session_memory",
                "entities": ["sky"],
                "supersedes_anchor": True,
            },
        },
    )

    assert episode["active_topic"] == "sky"
    assert episode["resolved_references"] == [{"reference": "it", "resolved_to": "sky"}]


def test_case_and_article_variants_preserve_one_topic_identity():
    history = [
        {"role": "user", "content": "what color is the sky"},
        {"role": "assistant", "content": "The sky usually looks blue."},
        {"role": "topic_state", "content": json.dumps({
            "state_kind": "SUBSTANTIVE_TOPIC",
            "topic": "Sky",
            "last_user_prompt": "what color is the sky",
            "last_visible_answer": "The sky usually looks blue.",
            "source_route": "local_conversation_model_lane",
            "entities": ["The sky"],
            "supersedes_anchor": True,
        })},
    ]

    payload = route_message("Conversation", "does it always look blue", history=history)

    assert "which one do you mean" not in payload["answer"].lower()
    assert payload["cognitive_episode"]["active_topic"] == "Sky"


def test_distinct_topics_remain_distinct_for_explicit_ambiguity():
    episode = build_cognitive_episode(
        "which one matters more",
        [
            {"role": "user", "content": "First subject: architecture."},
            {"role": "assistant", "content": "Architecture shapes constraints."},
            {"role": "user", "content": "Second subject: gardening."},
            {"role": "assistant", "content": "Gardening shapes care routines."},
        ],
    )
    topics = [branch["topic"] for branch in episode["conversation_branch"]]

    assert "architecture" in topics
    assert "gardening" in topics
    assert episode["active_topic"] in {"architecture", "gardening"}


def test_topic_switch_commits_music_and_supersedes_prior_anchor():
    payload = route_message(
        "Conversation",
        "actually let's talk about music",
        history=_history_with_anchor(("tell me about physics", "I know several things about basic physics, including Buoyancy.")),
    )

    state = payload["conversation_topic_state"]
    assert state["state_kind"] == "TOPIC_SWITCH"
    assert state["topic"] == "music"
    assert state["supersedes_anchor"] is True
    assert "music" in payload["answer"].lower()


def test_neutral_topic_switch_acknowledgement_names_committed_topic():
    payload = route_message("Conversation", "now let's talk about gardening")

    state = payload["conversation_topic_state"]
    assert state["state_kind"] == "TOPIC_SWITCH"
    assert state["topic"] == "gardening"
    assert "gardening" in payload["answer"].lower()


def test_topic_reset_with_embedded_local_question_routes_normally():
    history = [
        {"role": "user", "content": "Feedback loops compare results with goals."},
        {"role": "assistant", "content": "Feedback loops compare results with goals so behavior can be adjusted."},
    ]

    payload = route_message("Conversation", "Switching subjects: what is capability activation?", history=history)

    assert payload["route"] == "local_conversation_model_lane"
    assert "capability activation" in payload["answer"].lower()
    assert "feedback loops" not in payload["answer"].lower()
    assert payload["conversation_topic_state"]["state_kind"] == "SUBSTANTIVE_TOPIC"


def test_neutral_topic_reset_with_embedded_question_is_not_ack_only():
    payload = route_message("Conversation", "New topic: how does planning work?")

    assert payload["route"] != "social_conversation"
    assert "let's talk about" not in payload["answer"].lower()
    assert payload["conversation_topic_state"]["state_kind"] != "TOPIC_SWITCH"


def test_compare_that_with_mars_uses_resolved_topic_not_raw_multi_concept_retrieval():
    moon_anchor = {
        "active_concept_id": "moon",
        "active_concept_name": "Moon Color Appearance",
        "last_user_question": "what makes the moon gray",
        "last_answer_summary": "The moon appears gray because of its surface and reflected sunlight.",
        "retrieved_concept_ids": ["moon"],
        "retrieved_concept_names": ["Moon Color Appearance"],
    }
    history = [
        {"role": "user", "content": "what makes the moon gray"},
        {"role": "assistant", "content": "The moon appears gray because of its surface and reflected sunlight."},
        {"role": "anchor", "content": json.dumps(moon_anchor)},
    ]

    payload = route_message("Conversation", "compare that with Mars", history=history)

    assert payload["route"] == "session_memory"
    assert "moon" in payload["answer"].lower()
    assert "mars" in payload["answer"].lower()
    assert "attention budgeting" not in payload["answer"].lower()


def test_followup_refreshes_topic_state_visible_answer():
    topic_state = {
        "state_kind": "SUBSTANTIVE_TOPIC",
        "topic": "sky",
        "last_user_prompt": "what color is the sky",
        "last_visible_answer": "The sky usually looks blue because air molecules scatter shorter blue wavelengths.",
        "source_route": "local_conversation_model_lane",
        "entities": ["sky"],
        "supersedes_anchor": True,
    }
    history = [
        {"role": "user", "content": "what color is the sky"},
        {"role": "assistant", "content": topic_state["last_visible_answer"]},
        {"role": "topic_state", "content": json.dumps(topic_state)},
    ]

    payload = route_message("Conversation", "tell me more", history=history)
    state = payload["conversation_topic_state"]

    assert state["state_kind"] == "FOLLOWUP"
    assert state["topic"] == "sky"
    assert state["last_user_prompt"] == "tell me more"
    assert state["last_visible_answer"] == payload["answer"]


def test_social_interlude_does_not_replace_substantive_topic():
    topic_state = {
        "state_kind": "SUBSTANTIVE_TOPIC",
        "topic": "sky",
        "last_user_prompt": "what color is the sky",
        "last_visible_answer": "The sky usually looks blue because air molecules scatter shorter blue wavelengths.",
        "source_route": "local_conversation_model_lane",
        "entities": ["sky"],
        "supersedes_anchor": True,
    }
    history = [{"role": "topic_state", "content": json.dumps(topic_state)}]

    payload = route_message("Conversation", "hi", history=history)

    assert payload["route"] == "social_conversation"
    assert payload["conversation_topic_state"]["state_kind"] == "SOCIAL_INTERLUDE"
    assert payload["conversation_topic_state"]["topic"] == ""


def test_deliberate_return_to_older_topic_is_not_suppressed_by_recent_topic():
    music_state = {
        "state_kind": "TOPIC_SWITCH",
        "topic": "music",
        "last_user_prompt": "actually let's talk about music",
        "last_visible_answer": "Got it. I will treat that as a correction to the current thread.",
        "source_route": "social_conversation",
        "entities": ["music"],
        "supersedes_anchor": True,
    }
    history = [
        {"role": "user", "content": "tell me about physics"},
        {"role": "assistant", "content": "I know several things about basic physics, including Buoyancy."},
        {"role": "user", "content": "actually let's talk about music"},
        {"role": "assistant", "content": "Got it. I will treat that as a correction to the current thread."},
        {"role": "topic_state", "content": json.dumps(music_state)},
    ]

    payload = route_message("Conversation", "go back to physics", history=history)

    assert payload["route"] == "topic_return"
    assert "physics" in payload["answer"].lower()
    assert payload["cognitive_episode"]["active_topic"] == "physics"


def test_current_topic_authority_keeps_motion_over_old_history_for_pronoun():
    topic_state = {
        "state_kind": "FOLLOWUP",
        "topic": "motion in physics",
        "last_user_prompt": "tell me more",
        "last_visible_answer": "Still on motion in physics.",
        "source_route": "session_memory",
        "entities": ["motion in physics"],
        "supersedes_anchor": True,
    }
    history = _history_with_anchor(
        ("Tell me about Advanced Operator Mode Evidence Standard", "Advanced Operator Mode Evidence Standard details."),
        ("what is the first concept that comes to mind related to physics", "The first concept that comes to mind is motion in physics."),
        ("tell me more", "Still on motion in physics."),
        topic_state=topic_state,
    )

    payload = route_message("Conversation", "why did you choose that one", history=history)

    assert "advanced operator mode" not in payload["answer"].lower()
    assert payload["cognitive_episode"]["active_topic"] == "motion in physics"


def test_current_topic_authority_keeps_music_over_old_history_for_pronoun():
    topic_state = {
        "state_kind": "FOLLOWUP",
        "topic": "music",
        "last_user_prompt": "tell me more",
        "last_visible_answer": "Still on music.",
        "source_route": "session_memory",
        "entities": ["music"],
        "supersedes_anchor": True,
    }
    history = [
        {"role": "user", "content": "tell me about physics"},
        {"role": "assistant", "content": "I know several things about basic physics."},
        {"role": "user", "content": "actually let's talk about music"},
        {"role": "assistant", "content": "Got it. Let's talk about music."},
        {"role": "user", "content": "tell me more"},
        {"role": "assistant", "content": "Still on music."},
        {"role": "topic_state", "content": json.dumps(topic_state)},
    ]

    payload = route_message("Conversation", "why do people respond emotionally to it", history=history)

    assert "which one do you mean" not in payload["answer"].lower()
    assert payload["cognitive_episode"]["active_topic"] == "music"


def test_emotional_response_followup_answers_from_current_topic():
    topic_state = {
        "state_kind": "FOLLOWUP",
        "topic": "music",
        "last_user_prompt": "tell me more",
        "last_visible_answer": "Still on music: Got it.",
        "source_route": "session_memory",
        "entities": ["music"],
        "supersedes_anchor": True,
    }
    history = [
        {"role": "user", "content": "actually let's talk about music"},
        {"role": "assistant", "content": "Got it. Let's talk about music."},
        {"role": "user", "content": "tell me more"},
        {"role": "assistant", "content": "Still on music: Got it."},
        {"role": "topic_state", "content": json.dumps(topic_state)},
    ]

    payload = route_message("Conversation", "why do people respond emotionally to it", history=history)
    answer = payload["answer"].lower()

    assert payload["route"] == "session_memory"
    assert payload["cognitive_episode"]["active_topic"] == "music"
    assert "got it" not in answer
    assert any(term in answer for term in ("emotion", "emotional", "rhythm", "memory"))


def test_neutral_emotional_response_followup_is_not_music_specific():
    topic_state = {
        "state_kind": "SUBSTANTIVE_TOPIC",
        "topic": "architecture",
        "last_user_prompt": "what is architecture",
        "last_visible_answer": "Architecture can shape how people move through space and notice patterns.",
        "source_route": "local_conversation_model_lane",
        "entities": ["architecture"],
        "supersedes_anchor": True,
    }
    history = [
        {"role": "user", "content": "what is architecture"},
        {"role": "assistant", "content": topic_state["last_visible_answer"]},
        {"role": "topic_state", "content": json.dumps(topic_state)},
    ]

    payload = route_message("Conversation", "why do people respond emotionally to it", history=history)
    answer = payload["answer"].lower()

    assert payload["route"] == "session_memory"
    assert payload["cognitive_episode"]["active_topic"] == "architecture"
    assert "architecture" in answer
    assert "music" not in answer
    assert any(term in answer for term in ("emotion", "emotional", "memory", "expectation"))


def test_concept_anchor_remains_historical_but_not_ordinary_pronoun_authority():
    topic_state = {
        "state_kind": "SUBSTANTIVE_TOPIC",
        "topic": "architecture",
        "last_user_prompt": "now let's talk about architecture",
        "last_visible_answer": "Got it. Let's talk about architecture.",
        "source_route": "social_conversation",
        "entities": ["architecture"],
        "supersedes_anchor": True,
    }
    history = _history_with_anchor(
        ("Tell me about Advanced Operator Mode Evidence Standard", "Advanced Operator Mode Evidence Standard details."),
        ("now let's talk about architecture", "Got it. Let's talk about architecture."),
        topic_state=topic_state,
    )

    ordinary = route_message("Conversation", "why is that important", history=history)
    older = route_message("Conversation", "return to Advanced Operator Mode", history=history)

    assert "advanced operator mode" not in ordinary["answer"].lower()
    assert ordinary["cognitive_episode"]["active_topic"] == "architecture"
    assert "advanced operator mode" in older["answer"].lower()


def test_provider_approval_path_is_not_intercepted_by_bounded_followup():
    topic_state = {
        "state_kind": "SUBSTANTIVE_TOPIC",
        "topic": "sky",
        "last_user_prompt": "what color is the sky",
        "last_visible_answer": "The sky usually looks blue because air molecules scatter shorter blue wavelengths.",
        "source_route": "local_conversation_model_lane",
        "entities": ["sky"],
        "supersedes_anchor": True,
    }
    history = [{"role": "topic_state", "content": json.dumps(topic_state)}]

    payload = route_message(
        "Conversation",
        "why is that",
        history=history,
        provider_approved=True,
        provider_transport=lambda prompt, headers, metadata, timeout: {
            "ok": True,
            "content": "Provider-approved support response.",
        },
    )

    assert payload["route"].startswith("provider_support")
    assert payload["provider_calls_performed"] is False


def test_explicit_local_model_approval_is_not_intercepted_by_bounded_followup():
    topic_state = {
        "state_kind": "SUBSTANTIVE_TOPIC",
        "topic": "architecture",
        "last_user_prompt": "now let's talk about architecture",
        "last_visible_answer": "Got it. Let's talk about architecture.",
        "source_route": "social_conversation",
        "entities": ["architecture"],
        "supersedes_anchor": True,
    }

    payload = route_message(
        "Conversation",
        "ask the local model",
        history=[{"role": "topic_state", "content": json.dumps(topic_state)}],
    )

    assert payload["route"] != "session_memory"
    assert not payload.get("resolved_from_prior_visible_answer")


def test_explicit_provider_refusal_is_not_intercepted_by_bounded_followup():
    topic_state = {
        "state_kind": "SUBSTANTIVE_TOPIC",
        "topic": "architecture",
        "last_user_prompt": "now let's talk about architecture",
        "last_visible_answer": "Got it. Let's talk about architecture.",
        "source_route": "social_conversation",
        "entities": ["architecture"],
        "supersedes_anchor": True,
    }

    payload = route_message(
        "Conversation",
        "no",
        history=[{"role": "topic_state", "content": json.dumps(topic_state)}],
    )

    assert payload["route"] != "session_memory"
    assert "architecture" not in payload["answer"].lower()


def test_live_wikipedia_topic_can_be_superseded_by_unrelated_topic():
    session = start_live_wikipedia_runtime(max_wikipedia_queries=3)

    def transport(_url, _max_chars):
        return {
            "title": "Ada Lovelace",
            "extract": "Ada Lovelace was an English mathematician and writer associated with Charles Babbage.",
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Ada_Lovelace"}},
        }

    session, response = handle_live_chat(session, "Look up Ada Lovelace on Wikipedia", wikipedia_transport=transport)
    state = response.payload["conversation_topic_state"]
    assert state["topic"] == "Ada Lovelace"

    history = [
        {"role": "assistant", "content": response.answer},
        {"role": "topic_state", "content": json.dumps(state)},
    ]
    gardening = route_message("Conversation", "now let's talk about gardening", history=history)
    followup_history = [
        *history,
        {"role": "user", "content": "now let's talk about gardening"},
        {"role": "assistant", "content": gardening["answer"]},
        {"role": "topic_state", "content": json.dumps(gardening["conversation_topic_state"])},
    ]
    followup = route_message("Conversation", "tell me more", history=followup_history)

    assert "gardening" in followup["answer"].lower()
    assert "ada lovelace" not in followup["answer"].lower()


def test_tk_local_model_response_query_returns_stored_result_before_concept_retrieval(monkeypatch):
    app, captured = _make_delta_app(monkeypatch)
    calls = []

    def fake_route(_mode, message, *_args, **kwargs):
        calls.append((message, bool(kwargs.get("execute_local_model"))))
        if kwargs.get("execute_local_model"):
            return {
                "mode": "Conversation",
                "route": "local_conversation_model_lane",
                "answer": "Practice floating, kicking, and breathing in safe shallow water.",
                "local_model_result": {
                    "executed": True,
                    "answer": "Practice floating, kicking, and breathing in safe shallow water.",
                    "provider_calls_performed": False,
                    "model_id": "fake-local",
                },
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
        if message == "what was the response":
            return {
                "mode": "Conversation",
                "route": "developmental_concept_memory",
                "answer": "I know about Demand Response Evidence Standard.",
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
        return {
            "mode": "Conversation",
            "route": "local_model_consent_required",
            "answer": "I don't think I know enough from my learned local knowledge yet. Would you like me to ask a local reasoning model?",
            "local_model_offer": {"offered": True, "prompt": "Would you like me to ask it?"},
            "local_model_result": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }

    monkeypatch.setattr(DELTA, "route_message", fake_route)
    try:
        _submit_chat_turn(app, "lookup how to swim")
        assert app.pending_local_model_question == "lookup how to swim"

        _submit_chat_turn(app, "yes")
        assert app.pending_local_model_question is None
        assert app.last_local_model_exchange["status"] == "completed"

        before = len(captured)
        _submit_chat_turn(app, "what was the response")
        response = next((text for speaker, text in reversed(captured[before:]) if speaker == "DELTA"), "")

        assert "Practice floating" in response
        assert "Demand Response" not in response
        assert ("what was the response", False) not in calls
    finally:
        _destroy_app(app)


def test_tk_local_model_response_query_reports_unavailable_without_concept_retrieval(monkeypatch):
    app, captured = _make_delta_app(monkeypatch)
    calls = []

    def fake_route(_mode, message, *_args, **kwargs):
        calls.append((message, bool(kwargs.get("execute_local_model"))))
        if kwargs.get("execute_local_model"):
            return {
                "mode": "Conversation",
                "route": "local_model_unavailable",
                "answer": "I couldn't reach the local conversation model from this session.",
                "local_model_result": {"executed": False, "reason": "model_unavailable"},
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
        if message == "what was the response":
            return {
                "mode": "Conversation",
                "route": "developmental_concept_memory",
                "answer": "I know about Demand Response Evidence Standard.",
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
        return {
            "mode": "Conversation",
            "route": "local_model_consent_required",
            "answer": "I don't think I know enough from my learned local knowledge yet. Would you like me to ask a local reasoning model?",
            "local_model_offer": {"offered": True, "prompt": "Would you like me to ask it?"},
            "local_model_result": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }

    monkeypatch.setattr(DELTA, "route_message", fake_route)
    try:
        _submit_chat_turn(app, "lookup how to swim")
        _submit_chat_turn(app, "yes")
        assert app.last_local_model_exchange["status"] == "unavailable"

        before = len(captured)
        _submit_chat_turn(app, "what was the response")
        response = next((text for speaker, text in reversed(captured[before:]) if speaker == "DELTA"), "")

        assert "do not have a completed local-model response" in response.lower()
        assert "Demand Response" not in response
        assert ("what was the response", False) not in calls
    finally:
        _destroy_app(app)


def test_tk_discourse_history_query_preserves_pending_local_model_offer(monkeypatch):
    app, captured = _make_delta_app(monkeypatch)
    calls = []

    def fake_route(_mode, message, *_args, **kwargs):
        calls.append((message, bool(kwargs.get("execute_local_model"))))
        if message == "tell me how to swim":
            return {
                "mode": "Conversation",
                "route": "developmental_concept_memory",
                "answer": "I know about How To Swim from noncanonical reviewed memory.",
                "conversation_topic_state": {
                    "state_kind": "CONCEPT_ANCHOR",
                    "topic": "How To Swim",
                    "source_route": "developmental_concept_memory",
                    "last_user_prompt": message,
                    "last_visible_answer": "I know about How To Swim from noncanonical reviewed memory.",
                    "entities": ["How To Swim"],
                    "confidence": 0.92,
                    "supersedes_anchor": False,
                    "read_only": True,
                },
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
        if kwargs.get("execute_local_model"):
            return {
                "mode": "Conversation",
                "route": "local_conversation_model_lane",
                "answer": "Mock underwater welding answer.",
                "local_model_result": {
                    "executed": True,
                    "answer": "Mock underwater welding answer.",
                    "provider_calls_performed": False,
                    "model_id": "fake-local",
                },
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
        if message == "what were we discussing before that":
            raise AssertionError("discourse-history query should not reach route_message")
        return {
            "mode": "Conversation",
            "route": "local_model_consent_required",
            "answer": "I don't think I know enough from my learned local knowledge yet. Would you like me to ask a local reasoning model?",
            "local_model_offer": {"offered": True, "prompt": "Would you like me to ask it?"},
            "local_model_result": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }

    monkeypatch.setattr(DELTA, "route_message", fake_route)
    try:
        _submit_chat_turn(app, "tell me how to swim")
        assert (app.conversation_topic_state or {}).get("topic") == "How To Swim"

        _submit_chat_turn(app, "give me a practical tip for underwater welding")
        assert app.pending_local_model_question == "give me a practical tip for underwater welding"

        before = len(captured)
        _submit_chat_turn(app, "what were we discussing before that")
        response = next((text for speaker, text in reversed(captured[before:]) if speaker == "DELTA"), "")

        assert "How To Swim" in response
        assert app.pending_local_model_question == "give me a practical tip for underwater welding"
        assert (app.conversation_topic_state or {}).get("topic") == "How To Swim"
        assert ("what were we discussing before that", False) not in calls

        _submit_chat_turn(app, "yes")
        assert ("give me a practical tip for underwater welding", True) in calls
        assert app.pending_local_model_question is None
    finally:
        _destroy_app(app)


def test_tk_discourse_history_query_then_no_cancels_original_pending_offer(monkeypatch):
    app, captured = _make_delta_app(monkeypatch)
    calls = []

    def fake_route(_mode, message, *_args, **kwargs):
        calls.append((message, bool(kwargs.get("execute_local_model"))))
        if message == "tell me how to swim":
            return {
                "mode": "Conversation",
                "route": "developmental_concept_memory",
                "answer": "I know about How To Swim from noncanonical reviewed memory.",
                "conversation_topic_state": {
                    "state_kind": "CONCEPT_ANCHOR",
                    "topic": "How To Swim",
                    "source_route": "developmental_concept_memory",
                    "last_user_prompt": message,
                    "last_visible_answer": "I know about How To Swim from noncanonical reviewed memory.",
                    "entities": ["How To Swim"],
                    "confidence": 0.92,
                    "supersedes_anchor": False,
                    "read_only": True,
                },
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
        if message == "what were we discussing before that":
            raise AssertionError("discourse-history query should not reach route_message")
        return {
            "mode": "Conversation",
            "route": "local_model_consent_required",
            "answer": "I don't think I know enough from my learned local knowledge yet. Would you like me to ask a local reasoning model?",
            "local_model_offer": {"offered": True, "prompt": "Would you like me to ask it?"},
            "local_model_result": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }

    monkeypatch.setattr(DELTA, "route_message", fake_route)
    try:
        _submit_chat_turn(app, "tell me how to swim")
        _submit_chat_turn(app, "give me a practical tip for underwater welding")
        _submit_chat_turn(app, "what were we discussing before that")

        before = len(captured)
        _submit_chat_turn(app, "no")
        response = next((text for speaker, text in reversed(captured[before:]) if speaker == "DELTA"), "")

        assert "leave that unanswered locally" in response
        assert app.pending_local_model_question is None
        assert (app.conversation_topic_state or {}).get("topic") == "How To Swim"
        assert ("what were we discussing before that", False) not in calls
        assert all(not execute for _message, execute in calls)
    finally:
        _destroy_app(app)


def test_tk_live_completion_wikipedia_topic_can_be_superseded(monkeypatch):
    monkeypatch.setattr(DeltaApp, "_warm_default_model", lambda self: setattr(self, "model_residency_status", "warm_skipped_by_test"))
    monkeypatch.setattr(DeltaApp, "_poll_live_runtime_worker_results", lambda self: None)
    monkeypatch.setattr(
        live_mod,
        "_default_wikipedia_transport",
        lambda _url, _max_chars: {
            "title": "Ada Lovelace",
            "extract": "Ada Lovelace was an English mathematician and writer associated with Charles Babbage.",
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Ada_Lovelace"}},
        },
    )

    root = tk.Tk()
    root.withdraw()
    app = DeltaApp(root)
    captured: list[tuple[str, str]] = []
    original_append = app._append_chat

    def capture(speaker: str, text: str) -> None:
        captured.append((speaker, str(text)))
        original_append(speaker, text)

    app._append_chat = capture
    try:
        app._start_live_runtime()
        _submit_and_complete_live_turn(app, "Look up Ada Lovelace on Wikipedia")
        assert (app.conversation_topic_state or {}).get("topic") == "Ada Lovelace"

        _submit_and_complete_live_turn(app, "now let's talk about gardening")
        assert (app.conversation_topic_state or {}).get("topic") == "gardening"

        before = len(captured)
        _submit_and_complete_live_turn(app, "tell me more")
        response = next((text for speaker, text in reversed(captured[before:]) if speaker == "DELTA"), "")
        visible = response.split("\n\n--- Developer Overlay ---", 1)[0].lower()

        assert "gardening" in visible
        assert "ada lovelace" not in visible
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def _make_delta_app(monkeypatch):
    monkeypatch.setattr(DeltaApp, "_warm_default_model", lambda self: setattr(self, "model_residency_status", "warm_skipped_by_test"))
    monkeypatch.setattr(DeltaApp, "_poll_live_runtime_worker_results", lambda self: None)
    root = tk.Tk()
    root.withdraw()
    app = DeltaApp(root)
    app.mode.set("Conversation")
    captured: list[tuple[str, str]] = []
    original_append = app._append_chat

    def capture(speaker: str, text: str) -> None:
        captured.append((speaker, str(text)))
        original_append(speaker, text)

    app._append_chat = capture
    return app, captured


def _submit_chat_turn(app: DeltaApp, message: str) -> None:
    app.chat_input.delete(0, tk.END)
    app.chat_input.insert(0, message)
    app._send_chat()


def _destroy_app(app: DeltaApp) -> None:
    try:
        app.root.destroy()
    except tk.TclError:
        pass


def _submit_and_complete_live_turn(app: DeltaApp, message: str) -> None:
    app.chat_input.delete(0, tk.END)
    app.chat_input.insert(0, message)
    app._send_chat()
    for _ in range(200):
        try:
            result = app.live_runtime_worker_results.get_nowait()
        except queue.Empty:
            time.sleep(0.02)
            continue
        app._complete_live_runtime_turn(result)
        return
    raise AssertionError(f"live runtime turn did not complete: {message}")
