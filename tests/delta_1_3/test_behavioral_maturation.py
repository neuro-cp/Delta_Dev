from orchestration.runtime.delta_1_3_behavioral_maturation import (
    build_campaign_report,
    run_live_conversation,
)
from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message


def _run_chat(*messages: str):
    history = []
    payloads = []
    for message in messages:
        payload = route_message("Conversation", message, history=history, execute_local_model=False)
        rendered = render_route(payload, developer_overlay=True)
        payloads.append(payload)
        history.append({"role": "user", "content": " ".join(message.split())[:1200]})
        history.append({"role": "assistant", "content": " ".join(rendered.split())[:1200]})
    return payloads


def test_development_workflow_prompts_stay_on_local_engineering_path():
    payloads = _run_chat(
        "Suppose a router test fails because a topic shift is classified as contradiction. What should DELTA inspect first?",
        "Now propose two bounded repair hypotheses and rank them.",
        "Which tests would prove the safer one?",
    )

    for payload in payloads:
        assert payload["route"] == "local_conversation_model_lane"
        assert payload["provider_calls_performed"] is False
        assert payload["web_search_performed"] is False
        assert payload["memory_candidate"] is None
    assert "router precedence" in payloads[1]["answer"].lower()
    assert "focused live-path regressions" in payloads[2]["answer"].lower()


def test_delta_1_2_runtime_questions_are_not_orphan_followups():
    payloads = _run_chat(
        "What should the DELTA 1.2 live runtime do when it notices repeated ambiguity failures?",
        "Should it implement the fix by itself?",
        "What question should it ask the operator first?",
    )

    answers = " ".join(payload["answer"].lower() for payload in payloads)
    assert "need the topic" not in answers
    assert "operator approval" in answers
    assert "bounded sandbox objective" in answers
    for payload in payloads:
        assert payload["provider_calls_performed"] is False
        assert payload["memory_candidate"] is None


def test_referent_selection_preserves_clean_subject_anchor():
    payloads = _run_chat(
        "First subject: feedback loops can improve planning.",
        "Second subject: memory candidates can improve future recall.",
        "Why is that risky?",
        "I mean the first one.",
        "Why does that matter?",
    )

    clarification = payloads[2]["answer"].lower()
    selected = payloads[3]["answer"].lower()
    significance = payloads[4]["answer"].lower()
    assert "which one" in clarification
    assert "feedback loops" in selected
    assert "first subject:" not in selected
    assert "continuing with feedback loops" in significance
    assert "continuing with planning" not in significance


def test_recovery_evidence_stays_governance_local():
    payloads = _run_chat(
        "Feedback loops compare results with goals.",
        "But now talk about rollback evidence.",
        "What would count as enough recovery evidence?",
    )

    for payload in payloads[1:]:
        assert payload["route"] == "local_conversation_model_lane"
        assert "exercise recovery" not in payload["answer"].lower()
        assert "unauthorized" in payload["answer"].lower() or "provider call" in payload["answer"].lower()
        assert payload["provider_calls_performed"] is False
        assert payload["memory_candidate"] is None


def test_campaign_harness_uses_live_router_path_and_keeps_sandbox_inert():
    turns = run_live_conversation(
        "delta13_test",
        (
            "What should the DELTA 1.2 live runtime do when it notices repeated ambiguity failures?",
            "Should it implement the fix by itself?",
        ),
    )
    report = build_campaign_report(turns)

    assert len(turns) == 2
    assert report["checks"]["live_turns_captured"] is False
    assert all(turn.provider_called is False for turn in turns)
    assert all(turn.web_search_performed is False for turn in turns)
    assert all(turn.canonical_write_performed is False for turn in turns)
