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


def test_explicit_format_directive_is_not_orphan_followup():
    message = """Format compliance test.

Answer this using exactly these headings and no other headings:
1. What I inspected
2. Bounded next operator step
3. Evidence that would make this freeze-relevant
4. What remains unproven

Topic: A governed AI system is preparing for a real operator pilot.

Do not write memory.
Do not call providers."""
    payload = route_message("Conversation", message, history=[])
    assert payload["route"] != "session_memory"
    assert "need the topic" not in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False


def test_retry_directive_is_not_orphan_followup():
    message = """Retry the previous DELTA 1.0 pilot answer.

Original task:
Inspect the current DELTA 1.0 readiness/report state and propose one bounded next step toward operator validation.

Use exactly these headings:
1. What I inspected
2. Bounded next operator step
3. Evidence that would make this freeze-relevant
4. What remains unproven

Keep the answer concise.
Do not write memory.
Do not call providers.
Do not modify files.
Do not claim freeze readiness."""
    payload = route_message("Conversation", message, history=[])
    assert payload["route"] != "session_memory"
    assert "need the topic" not in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False


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


def test_second_one_asks_clarification_when_prior_answer_has_no_list():
    history = _history(("What are two useful debugging habits?", "I can help with coding by reading the repo, explaining files, proposing patches, writing tests, and validating behavior."))
    payload = route_message("Conversation", "And the second one?", history=history)
    assert payload["route"] == "session_memory"
    assert "need the two-item list" in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False


def test_feedback_loop_why_followup_gives_substantive_explanation():
    history = _history(("So the real issue is probably the feedback loop, right?", "I know about Feedback Loops. Feedback loops are cycles where outcomes are compared with goals so behavior or plans can be adjusted."))
    payload = route_message("Conversation", "Why do you think it keeps doing that?", history=history)
    assert payload["route"] == "session_memory"
    assert "feedback loop" in payload["answer"].lower()
    assert "specific adjustment" in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False


def test_significance_followups_explain_decision_impact():
    history = _history(("Feedback loops matter because they turn observed results into changed behavior.", "Feedback loops compare results with goals so behavior can be adjusted."))
    prompts = [
        "Why does that matter?",
        "Why is that important?",
        "Why should I care about that?",
        "What difference does that make?",
        "How does that affect the decision?",
    ]
    for prompt in prompts:
        payload = route_message("Conversation", prompt, history=history)
        answer = payload["answer"].lower()
        assert payload["route"] == "session_memory"
        assert "feedback loops" in answer
        assert "decision" in answer or "action" in answer
        assert "adjust" in answer
        assert payload["provider_calls_performed"] is False
        assert payload["memory_candidate"] is None


def test_significance_followup_prefers_immediate_recent_topic_over_older_branch():
    history = _history(
        ("First subject: photosynthesis as an analogy. Main limitation: it is biochemical.", "Got it. I will keep photosynthesis as an analogy as context for this conversation."),
        ("Feedback loops matter because they turn observed results into changed behavior.", "Feedback loops compare results with goals so behavior can be adjusted."),
    )
    payload = route_message("Conversation", "Why does that matter?", history=history)
    answer = payload["answer"].lower()
    assert payload["route"] == "session_memory"
    assert "feedback loops" in answer
    assert "decision" in answer or "action" in answer
    assert "which one" not in answer
    assert payload["provider_calls_performed"] is False


def test_context_declaration_is_not_orphan_followup():
    payload = route_message(
        "Conversation",
        "For this conversation, here are two points about feedback loops: 1. Observation compares actual results to the goal. 2. Adjustment changes the next action based on that comparison.",
        history=[],
    )
    assert payload["route"] == "session_memory"
    assert "got it" in payload["answer"].lower()
    assert "need the topic" not in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False


def test_tell_me_more_about_second_point_uses_ordered_context():
    history = _history((
        "For this conversation, here are two points about feedback loops: 1. Observation compares actual results to the goal. 2. Adjustment changes the next action based on that comparison.",
        "Got it. I will keep those points as context for this conversation.",
    ))
    payload = route_message("Conversation", "Tell me more about the second point.", history=history)
    assert payload["route"] == "session_memory"
    assert "adjustment" in payload["answer"].lower()
    assert "changes the next action" in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False


def test_going_back_to_first_subject_resolves_delayed_topic():
    history = _history(
        ("First subject: photosynthesis as an analogy. Main limitation: it is biochemical, while planning is decision-based and social.", "Got it. I will keep the first subject as context for this conversation."),
        ("Second subject: fire is combustion that releases heat and light.", "Got it. I will keep the second subject as context for this conversation."),
    )
    payload = route_message("Conversation", "Going back to the first subject, what was the main limitation?", history=history)
    assert payload["route"] == "session_memory"
    assert "photosynthesis" in payload["answer"].lower()
    assert "biochemical" in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False


def test_going_back_to_first_subject_uses_labeled_pair_not_absolute_history_start():
    history = _history(
        ("For this conversation, here are two points about feedback loops: 1. Observation compares actual results to the goal. 2. Adjustment changes the next action based on that comparison.", "Got it. I will keep feedback loops as context for this conversation."),
        ("First subject: photosynthesis as an analogy. Main limitation: it is biochemical, while planning is decision-based and social.", "Got it. I will keep photosynthesis as an analogy as context for this conversation."),
        ("Second subject: fire is combustion that releases heat and light.", "Got it. I will keep fire as context for this conversation."),
    )
    payload = route_message("Conversation", "Going back to the first subject, what was the main limitation?", history=history)
    assert payload["route"] == "session_memory"
    assert "photosynthesis" in payload["answer"].lower()
    assert "biochemical" in payload["answer"].lower()
    assert "feedback loops" not in payload["answer"].lower()
    assert payload["provider_calls_performed"] is False


def test_ambiguous_that_with_two_explicit_topics_asks_clarification():
    history = _history(
        ("First subject: feedback loops can improve planning.", "Got it. I will keep feedback loops as context for this conversation."),
        ("Second subject: memory candidates can improve future recall.", "Got it. I will keep memory candidates as context for this conversation."),
    )
    payload = route_message("Conversation", "Why is that risky?", history=history)
    answer = payload["answer"].lower()
    assert payload["route"] == "session_memory"
    assert "which one" in answer or "do you mean" in answer
    assert "feedback" in answer
    assert "memory" in answer
    assert payload["provider_calls_performed"] is False
    assert payload["memory_candidate"] is None


def test_ambiguous_that_with_two_named_entities_asks_clarification():
    history = _history(
        ("Context: Alice owns the truck.", "Got it. I will keep Alice as context for this conversation."),
        ("Context: Bob owns the trailer.", "Got it. I will keep Bob as context for this conversation."),
    )
    payload = route_message("Conversation", "Does that affect it?", history=history)
    answer = payload["answer"].lower()
    assert payload["route"] == "session_memory"
    assert "which one" in answer or "do you mean" in answer
    assert "alice" in answer
    assert "bob" in answer
    assert payload["provider_calls_performed"] is False


def test_ambiguous_ordered_points_ask_clarification():
    history = _history((
        "For this conversation, here are two points: 1. Observation checks the result. 2. Adjustment changes the next action.",
        "Got it. I will keep those points as context for this conversation.",
    ))
    payload = route_message("Conversation", "Which one is more important?", history=history)
    answer = payload["answer"].lower()
    assert payload["route"] == "session_memory"
    assert "which one" in answer or "do you mean" in answer
    assert "observation" in answer
    assert "adjustment" in answer
    assert payload["provider_calls_performed"] is False


def test_explicit_topic_reset_uses_local_delta_knowledge_without_stale_context():
    history = _history((
        "Feedback loops compare results with goals.",
        "Feedback loops compare results with goals so behavior can be adjusted.",
    ))
    cases = [
        ("New topic: explain the module permission boundary.", "module permission boundary", "prohibited permissions"),
        ("Switching subjects: what is capability activation?", "capability activation", "fail-closed"),
        ("Different topic: how does rollback work?", "rollback", "strategy"),
        ("Let's move on. Explain operator approval.", "operator approval", "explicit gate"),
        ("Forget the prior topic for now. What is a module manifest?", "module manifest", "declares"),
    ]
    for message, topic, expected in cases:
        payload = route_message("Conversation", message, history=history)
        answer = payload["answer"].lower()
        episode = payload["cognitive_episode"]
        assert payload["route"] == "local_conversation_model_lane"
        assert payload["local_model_offer"] is None
        assert payload["provider_calls_performed"] is False
        assert payload["memory_candidate"] is None
        assert topic in answer
        assert expected in answer
        assert "feedback loops" not in answer
        assert "feedback loops" not in str(episode.get("active_topic") or "").lower()


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
