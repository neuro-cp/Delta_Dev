from orchestration.runtime.rc2_cognitive_episode import (
    SAFETY,
    build_working_memory_episode_report,
    resolve_working_memory_followup,
)
from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message


def _history(*turns):
    history = []
    for user, assistant in turns:
        history.append({"role": "user", "content": user})
        history.append({"role": "assistant", "content": assistant})
    return history


def test_tell_me_more_uses_recent_topic_without_model_offer():
    payload = route_message(
        "Conversation",
        "Tell me more.",
        history=_history(("What is blood pressure?", "Blood pressure is the force exerted by circulating blood against artery walls.")),
    )
    assert payload["route"] == "session_memory"
    assert "blood pressure" in payload["answer"].lower()
    assert not (payload.get("local_model_offer") or {}).get("offered")
    assert not payload["provider_calls_performed"]


def test_followup_relation_resolves_that_to_prior_topic_and_new_entity():
    payload = route_message(
        "Conversation",
        "How does that relate to allergies?",
        history=_history(("What is blood pressure?", "Blood pressure is the force exerted by circulating blood against artery walls.")),
    )
    answer = payload["answer"].lower()
    assert payload["route"] == "session_memory"
    assert "blood pressure" in answer
    assert "allerg" in answer


def test_orphan_followup_asks_for_context_instead_of_retrieving():
    payload = route_message("Conversation", "Give me an example.", history=[])
    assert payload["route"] == "session_memory"
    assert "need" in payload["answer"].lower()
    assert not payload["provider_calls_performed"]


def test_explicit_topic_change_does_not_reuse_stale_analogy():
    payload = route_message(
        "Conversation",
        "What is blood pressure?",
        history=_history(("How is photosynthesis like charging a battery?", "The shared pattern is energy input, conversion, storage, and later use.")),
    )
    answer = payload["answer"].lower()
    assert "blood pressure" in answer
    assert "battery" not in answer
    assert payload["route"] != "session_memory"


def test_branch_return_can_select_first_topic():
    history = _history(
        ("Let's discuss photosynthesis.", "Photosynthesis stores light energy in chemical bonds."),
        ("Now switch to planning.", "Planning organizes actions toward goals."),
        ("Talk about allergies.", "Allergies involve immune responses to allergens."),
    )
    payload = route_message("Conversation", "Return to the first topic.", history=history)
    assert payload["route"] == "session_memory"
    assert "photosynthesis" in payload["answer"].lower()


def test_analogy_break_followup_uses_recent_analogy_limits():
    history = _history(("How is photosynthesis like charging a battery?", "The shared pattern is energy input, conversion, storage, and later use. Where it breaks: photosynthesis is biochemical and a battery is electrochemical."))
    payload = route_message("Conversation", "Where does that analogy break?", history=history)
    assert payload["route"] == "session_memory"
    assert "break" in payload["answer"].lower()


def test_developer_overlay_shows_cognitive_episode():
    payload = route_message(
        "Conversation",
        "Tell me more.",
        history=_history(("What is blood pressure?", "Blood pressure is the force exerted by circulating blood against artery walls.")),
    )
    rendered = render_route(payload, developer_overlay=True)
    assert "Cognitive episode:" in rendered
    assert "active_topic: blood pressure" in rendered


def test_working_memory_report_and_safety_flags():
    report = build_working_memory_episode_report(write_reports=False)
    assert report["followup_resolution_accuracy"] >= 0.8
    assert all(value is False for value in SAFETY.values())

