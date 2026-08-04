"""Executable closure shards for the chat-first routing campaign.

The cases deliberately use the coordinator and authoritative runtime state,
not only the pure planner.  They are a bounded, deterministic basis for the
larger persisted campaign manifests.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from orchestration.runtime.chat_first_dispatch_contract import plan_message_dispatch
from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    LocalSemanticInsufficiency,
    handle_conversational_message,
    record_foreground_message_for_reconciliation,
    save_runtime_state,
    start_or_restore_runtime,
)
from tests.runtime_gsr.chat_first_campaign_generator import generate_pairwise_assignments, pairwise_coverage_report, render_pairwise_prompt
from tests.runtime_gsr.chat_first_routing_matrix import AUTHORITATIVE_STATE_CONDITIONS


def _app(tmp_path):
    import DELTA

    app = object.__new__(DELTA.DeltaApp)
    app.conversational_runtime_state = start_or_restore_runtime(tmp_path)
    app.conversational_runtime_root = tmp_path
    app.mode = SimpleNamespace(get=lambda: "Conversation")
    app.developer_overlay_enabled = SimpleNamespace(get=lambda: False)
    app.session_history = []
    app.chat_records = []
    app._recent_history_for_router = lambda: []
    app._update_active_topic_anchor = lambda _payload: None
    app._queue_concept_candidate = lambda _payload: None
    app._append_chat = lambda speaker, text: app.chat_records.append((speaker, text))
    app._append_session = lambda role, content: app.session_history.append({"role": role, "content": content})
    app._refresh_state_cards = lambda: None
    app._refresh_conversational_runtime_status = lambda: None
    app._start_conversational_background_cycle = lambda _reason: True
    return app


def _goal(app):
    app.conversational_runtime_state = handle_conversational_message(
        app.conversational_runtime_state,
        "Your new goal is to study engine efficiency.",
        runtime_root=app.conversational_runtime_root,
        run_background_cycle=False,
    ).state


def _pending(app, request_type):
    request = ChatAddressableRequest(
        request_id=f"campaign-{request_type}", request_type=request_type,
        objective_id=app.conversational_runtime_state.active_objective.objective_id,
        goal_label="Engine efficiency", prompt_text="Bounded request.", max_calls=1, max_spend_usd=1.0,
    )
    app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(request,))


PAIRWISE_CASES = (
    ("formal_control_first", "Your new goal is to study engines. Also, what is kinetic energy?", None),
    ("casual_also", "Your new goal is to study engines. Also, what color is the sky?", None),
    ("lowercase_and", "your new goal is to study engines and what color is the sky?", None),
    ("question_first", "What color is the sky? Also, your new goal is to study engines.", None),
    ("pause_question", "Pause the goal. Also, what is kinetic energy?", "goal"),
    ("resume_question", "Resume the goal. Why is the Moon gray?", "goal"),
    ("provider_approval_question", "Approve one provider call. Also, what color is the sky?", "provider_authority"),
    ("provider_denial_question", "Do not use a provider. Also, what is kinetic energy?", "provider_authority"),
    ("adoption_question", "Yes, adopt it. Also, what color is the sky?", "capability_adoption_and_restart"),
    ("side_thread_question", "Yes, prioritize topic switches. Also, what is kinetic energy?", "directional_question"),
)

GENERATED_PAIRWISE_CASES = tuple(
    (f"PW{index:03d}", assignment, *render_pairwise_prompt(assignment))
    for index, assignment in enumerate(generate_pairwise_assignments(), start=1)
)


def test_generated_pairwise_manifest_has_complete_requested_dimension_coverage():
    report = pairwise_coverage_report(tuple(item[1] for item in GENERATED_PAIRWISE_CASES))

    assert report["requested_dimension_pairs"] == report["covered_dimension_pairs"]
    assert report["uncovered_pairs"] == []
    assert report["invalid_or_excluded_pairs"] == []


@pytest.mark.parametrize("_case_id,message,setup", PAIRWISE_CASES)
def test_pairwise_execution_preserves_composed_turn_and_foreground(tmp_path, _case_id, message, setup):
    app = _app(tmp_path)
    if setup:
        _goal(app)
        if setup != "goal":
            _pending(app, setup)
    before = app.conversational_runtime_state
    plan = plan_message_dispatch(before, message)

    assert app._coordinate_mixed_dispatch(message, plan) is True

    turns = app.conversational_runtime_state.conversation
    assert turns[-2].role == "user" and turns[-2].text == message
    assert turns[-1].role == "assistant"
    assert "i understand. i will treat this as ordinary conversation" not in turns[-1].text.lower()
    assert len([item for item in app.session_history if item["role"] == "user" and item["content"] == message]) == 1


@pytest.mark.parametrize("case_id,assignment,message,setup", GENERATED_PAIRWISE_CASES, ids=[item[0] for item in GENERATED_PAIRWISE_CASES])
def test_generated_pairwise_cases_execute_without_sticky_ownership(tmp_path, case_id, assignment, message, setup):
    app = _app(tmp_path)
    if setup:
        _goal(app)
        _pending(app, setup)
    plan = plan_message_dispatch(app.conversational_runtime_state, message)

    assert plan.foreground.requested, (case_id, assignment, plan.as_record())
    assert app._coordinate_mixed_dispatch(message, plan), (case_id, assignment)
    output = app.conversational_runtime_state.conversation[-1].text.lower()
    assert "i understand. i will treat this as ordinary conversation" not in output
    assert app.conversational_runtime_state.conversation[-2].text == message


def test_ambiguous_pending_reply_clarifies_without_consuming_or_suppressing_question(tmp_path):
    app = _app(tmp_path)
    _goal(app)
    provider = ChatAddressableRequest("provider", "provider_authority", app.conversational_runtime_state.active_objective.objective_id, "Engine", "Provider?", max_calls=1, max_spend_usd=1.0)
    direction = ChatAddressableRequest("direction", "directional_question", app.conversational_runtime_state.active_objective.objective_id, "Engine", "Direction?")
    app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(provider, direction))
    message = "Yes. Also, why is the Moon gray?"

    assert app._coordinate_mixed_dispatch(message, plan_message_dispatch(app.conversational_runtime_state, message))

    assert len(app.conversational_runtime_state.pending_chat_requests) == 2
    assert "clarification" in app.conversational_runtime_state.conversation[-1].text.lower()
    assert "moon" in app.conversational_runtime_state.conversation[-1].text.lower()


def test_restart_restores_composed_turn_without_duplicate_action(tmp_path):
    app = _app(tmp_path)
    message = "Your new goal is to study engines. Also, what color is the sky?"
    assert app._coordinate_mixed_dispatch(message, plan_message_dispatch(app.conversational_runtime_state, message))
    before = app.conversational_runtime_state
    save_runtime_state(app.conversational_runtime_root, before)
    restored = start_or_restore_runtime(app.conversational_runtime_root)

    assert [item.as_record() for item in restored.conversation] == [item.as_record() for item in before.conversation]
    assert sum(item.text == message for item in restored.conversation if item.role == "user") == 1
    assert len(restored.completed_cycle_keys) == len(before.completed_cycle_keys)


THREE_WAY_CASES = (
    ("goal_correction_question", "Your new goal is to study topic changes, and note I meant your earlier answer, and why is the Moon gray?", None, {"create_goal", "correction"}),
    ("adoption_constraint_question", "Adopt it, change nothing else, and remind me of the score.", "capability_adoption_and_restart", {"capability_adoption"}),
    ("pause_provider_denial_question", "Pause the current goal and deny the pending provider request. Also, what color is the sky?", "provider_authority", {"pause_goal", "provider_approval"}),
    ("ambiguous_yes_question", "Yes. Also, why is the Moon gray?", "multiple", {"clarification"}),
    ("side_thread_question", "Yes, prioritize topic switches. Also, what is kinetic energy?", "directional_question", {"side_thread_resolution"}),
    ("tentative_constraint_question", "Maybe later study fuel injection. Don't apply that rule to cooking questions. What color is the sky?", "goal", {"correction"}),
)


# Each row binds one declared three-way family to a production-backed runtime
# state. These are intentionally semantic combinations, not permutations of
# the pairwise wording generator.
THREE_WAY_MANIFEST = (
    ("TW001", "control_foreground_state", "running", "Your new goal is to study engines. Also, what color is the sky?", {"replace_goal"}),
    ("TW002", "control_foreground_state", "running", "Pause the goal. Also, what is kinetic energy?", {"pause_goal"}),
    ("TW003", "control_foreground_state", "blocked_provider", "Approve one provider call. Also, what color is the sky?", {"provider_approval"}),
    ("TW004", "pending_ambiguity_foreground", "multiple_pending", "Yes. Also, why is the Moon gray?", {"clarification"}),
    ("TW005", "pending_ambiguity_foreground", "blocked_provider", "Do not use a provider. Also, what color is the sky?", {"provider_approval"}),
    ("TW006", "pending_ambiguity_foreground", "adoption_pending", "Yes, adopt it. Also, what is kinetic energy?", {"capability_adoption"}),
    ("TW007", "correction_reference_unrelated", "running", "No, I meant your earlier answer. Also, why is the Moon gray?", {"correction"}),
    ("TW008", "correction_reference_unrelated", "queued", "Do not apply that rule here. Also, what color is the sky?", {"correction"}),
    ("TW009", "correction_reference_unrelated", "running", "No, I meant the previous answer, but what color is the sky?", {"correction"}),
    ("TW010", "goal_health_repeated_wording", "stalled", "Your new goal is to study engine efficiency. Also, what color is the sky?", {"replace_goal"}),
    ("TW011", "goal_health_repeated_wording", "failed", "Your new goal is to study engine efficiency. Also, what is kinetic energy?", {"replace_goal"}),
    ("TW012", "goal_health_repeated_wording", "model_budget_exhausted", "Your new goal is to study engine efficiency. Also, why is the Moon gray?", {"replace_goal"}),
    ("TW013", "restart_mixed_duplicate", "restart_pending", "Pause the goal. Also, what color is the sky?", {"pause_goal"}),
    ("TW014", "restart_mixed_duplicate", "restarting", "Pause the goal. Also, what is kinetic energy?", {"pause_goal"}),
    ("TW015", "restart_mixed_duplicate", "post_restart", "Pause the goal. Also, why is the Moon gray?", {"pause_goal"}),
)


RESTART_DUPLICATE_MATRIX = (
    ("RD001", "running", "Your new goal is to study engines. Also, what color is the sky?"),
    ("RD002", "paused", "Resume the goal. Also, what is kinetic energy?"),
    ("RD003", "blocked_provider", "Do not use a provider. Also, what color is the sky?"),
    ("RD004", "multiple_pending", "Yes. Also, why is the Moon gray?"),
    ("RD005", "adoption_pending", "Yes, adopt it. Also, what is kinetic energy?"),
    ("RD006", "restart_pending", "Pause the goal. Also, what color is the sky?"),
    ("RD007", "event_pending", "Pause the goal. Also, why is the Moon gray?"),
    ("RD008", "queued", "No, I meant your earlier answer. Also, what color is the sky?"),
    ("RD009", "failed", "Your new goal is to study engine efficiency. Also, what is kinetic energy?"),
    ("RD010", "legacy_schema", "Pause the goal. Also, what color is the sky?"),
)

RUNTIME_EXECUTION_STATES = (
    "no_active_goal", "queued", "running", "mid_inference", "paused_operator", "stalled",
    "paused_budget", "model_budget_exhausted", "blocked_operator", "blocked_provider", "failed",
    "review_ready", "complete", "archived", "adoption_pending", "restart_pending", "restarting",
    "post_restart", "multiple_pending", "missing_campaign", "legacy_schema", "worker_crashed", "event_pending",
)


def _authoritative_state(app, state_name):
    """Construct a state with durable fields, not merely a lifecycle label."""
    _goal(app)
    state = app.conversational_runtime_state
    objective = state.active_objective
    if state_name == "paused":
        return replace(state, lifecycle_state="paused_operator", objective_progress=state.objective_progress + ({"event": "operator_pause"},))
    if state_name == "queued":
        queued = record_foreground_message_for_reconciliation(
            state,
            "also compare that with how I use pronouns",
            runtime_root=app.conversational_runtime_root,
        )
        save_runtime_state(app.conversational_runtime_root, queued)
        return start_or_restore_runtime(app.conversational_runtime_root)
    if state_name == "mid_inference":
        return replace(
            state,
            objective_progress=state.objective_progress + ({"event": "worker_request_started", "request_id": "mid-inference-request", "worker_id": "in-flight-worker"},),
        )
    if state_name == "cycle_budget_exhausted":
        finite_objective = replace(objective, cycle_budget=3)
        return replace(
            state,
            active_objective=finite_objective,
            lifecycle_state="paused_budget",
            completed_cycle_keys=tuple(f"cycle-{i}" for i in range(finite_objective.cycle_budget)),
        )
    if state_name == "blocked_operator":
        return replace(state, lifecycle_state="blocked", pending_material_authority=({"objective_id": objective.objective_id, "status": "pending", "request_id": "operator-boundary"},))
    if state_name == "blocked_provider":
        request = ChatAddressableRequest("provider-boundary", "provider_authority", objective.objective_id, "Engine", "Provider?", max_calls=1, max_spend_usd=1.0)
        insufficiency = LocalSemanticInsufficiency(
            insufficiency_id="provider-boundary-insufficiency", goal_id=objective.objective_id,
            target_gap="reference_resolution", exact_information_needed="bounded synthetic counterexamples",
            local_model="local-qwen", local_prompt="local insufficiency probe",
            local_raw_response_reference="local-raw", local_adapted_response_reference="local-adapted",
            local_evaluation="locally_insufficient", insufficiency_reason="bounded test fixture",
            retry_attempted=True, local_retrieval_checked=True, local_evidence_references=("local-evidence",),
            material_block="provider comparison blocked", smallest_external_packet="one sanitized example set",
            prohibited_data=("actual operator messages",), recommended_provider_budget={"max_calls": 1}, final_status="locally_insufficient",
        )
        return replace(state, lifecycle_state="blocked", pending_chat_requests=(request,), local_semantic_insufficiencies=(insufficiency,))
    if state_name == "failed":
        return replace(state, lifecycle_state="failed", objective_progress=state.objective_progress + ({"event": "worker_failed", "reason": "synthetic_runtime_failure"},))
    if state_name == "stalled":
        return replace(state, lifecycle_state="stalled", objective_progress=state.objective_progress + ({"event": "worker_stalled", "reason": "no_progress_or_pending_work", "at": "2000-01-01T00:00:00+00:00"},))
    if state_name == "model_budget_exhausted":
        return replace(state, lifecycle_state="model_budget_exhausted", objective_progress=state.objective_progress + ({"event": "model_budget_exhausted", "model_calls_used": objective.model_call_budget, "model_call_budget": objective.model_call_budget},))
    if state_name == "adoption_pending":
        request = ChatAddressableRequest("adoption-boundary", "capability_adoption_and_restart", objective.objective_id, "Engine", "Adopt?")
        return replace(state, pending_chat_requests=(request,))
    if state_name == "multiple_pending":
        provider = ChatAddressableRequest("multiple-provider", "provider_authority", objective.objective_id, "Engine", "Provider?", max_calls=1, max_spend_usd=1.0)
        direction = ChatAddressableRequest("multiple-direction", "directional_question", objective.objective_id, "Engine", "Direction?")
        return replace(state, pending_chat_requests=(provider, direction))
    if state_name == "restart_pending":
        record = {"restart_id": "restart-pending", "objective_id": objective.objective_id, "status": "pending", "saved_state": True}
        return replace(state, lifecycle_state="restart_pending", restart_records=(record,))
    if state_name == "restarting":
        record = {"restart_id": "restart-in-progress", "objective_id": objective.objective_id, "status": "restarting", "saved_state": True, "pre_restart_runtime_id": state.runtime_id}
        save_runtime_state(app.conversational_runtime_root, state)
        return replace(state, lifecycle_state="restarting", restart_records=(record,))
    if state_name == "post_restart":
        record = {"restart_id": "restart-restored", "objective_id": objective.objective_id, "status": "restored", "saved_state": True, "post_restart_validation": "passed"}
        save_runtime_state(app.conversational_runtime_root, state)
        restored = start_or_restore_runtime(app.conversational_runtime_root)
        return replace(restored, lifecycle_state="running", restart_records=(record,))
    if state_name == "worker_crashed":
        return replace(state, lifecycle_state="failed", objective_progress=state.objective_progress + ({"event": "worker_started", "worker_id": "dead-worker"}, {"event": "worker_crashed", "worker_id": "dead-worker", "reason": "crash_evidence"}))
    if state_name == "event_pending":
        return replace(state, objective_progress=state.objective_progress + ({"event": "capability_campaign_milestone_ready", "milestone_id": "event-pending-1", "dedupe_key": "event-pending-1", "message": "Pending goal event"},))
    if state_name == "review_ready":
        return replace(state, lifecycle_state="review_ready", objective_progress=state.objective_progress + ({"event": "capability_campaign_recommendation", "proposal_id": "review-ready-1", "status": "review_required"},))
    if state_name == "completed":
        return replace(state, lifecycle_state="completed", objective_progress=state.objective_progress + ({"event": "objective_completed", "completion_id": "completed-1", "completed_at": "2026-01-01T00:00:00+00:00", "worker_status": "stopped"},))
    if state_name == "archived":
        archived = {"objective_id": objective.objective_id, "archived_at": "2026-01-01T00:00:00+00:00", "archive_reason": "operator_archived"}
        return replace(state, lifecycle_state="archived", archived_objectives=(archived,), pending_chat_requests=(), pending_material_authority=())
    if state_name == "legacy_schema":
        legacy = state.as_record()
        legacy["schema_version"] = "conversational_runtime_operation_marathon_1_v0"
        legacy.pop("capability_registry", None)
        legacy.pop("restart_records", None)
        (app.conversational_runtime_root / "state.json").parent.mkdir(parents=True, exist_ok=True)
        (app.conversational_runtime_root / "state.json").write_text(__import__("json").dumps(legacy), encoding="utf-8")
        return start_or_restore_runtime(app.conversational_runtime_root)
    if state_name == "missing_campaign":
        return replace(state, capability_campaigns=(), objective_progress=state.objective_progress + ({"event": "campaign_missing"},))
    return replace(state, lifecycle_state=state_name)


def _validate_authoritative_fixture(state, state_name):
    if state_name == "queued":
        return bool(state.active_objective) and any(
            turn.intent_type in {"ordinary_conversation_queued", "goal_or_priority_queued"}
            for turn in state.conversation
        ) and any(item.get("event") == "foreground_message_queued_for_reconciliation" for item in state.objective_progress)
    if state_name == "mid_inference":
        return bool(state.active_objective) and any(
            item.get("event") == "worker_request_started" and item.get("request_id") and item.get("worker_id")
            for item in state.objective_progress
        )
    if state_name == "paused":
        return state.lifecycle_state == "paused_operator" and any(item.get("event") == "operator_pause" for item in state.objective_progress)
    if state_name == "cycle_budget_exhausted":
        return state.lifecycle_state == "paused_budget" and len(state.completed_cycle_keys) == state.active_objective.cycle_budget
    if state_name == "blocked_operator":
        return state.lifecycle_state == "blocked" and bool(state.pending_material_authority)
    if state_name == "blocked_provider":
        return state.lifecycle_state == "blocked" and bool(state.pending_chat_requests) and bool(state.local_semantic_insufficiencies)
    if state_name == "failed":
        return state.lifecycle_state == "failed" and any(item.get("event") == "worker_failed" for item in state.objective_progress)
    if state_name == "stalled":
        return state.lifecycle_state == "stalled" and any(item.get("event") == "worker_stalled" for item in state.objective_progress)
    if state_name == "model_budget_exhausted":
        return state.lifecycle_state == "model_budget_exhausted" and any(item.get("event") == "model_budget_exhausted" and item.get("model_calls_used") == state.active_objective.model_call_budget for item in state.objective_progress)
    if state_name == "adoption_pending":
        return any(item.request_type == "capability_adoption_and_restart" and item.status == "pending" for item in state.pending_chat_requests)
    if state_name == "multiple_pending":
        return len(state.pending_chat_requests) == 2 and all(item.status == "pending" and not item.consumption_count for item in state.pending_chat_requests)
    if state_name == "restart_pending":
        return state.lifecycle_state == "restart_pending" and bool(state.restart_records) and state.restart_records[-1].get("status") == "pending"
    if state_name == "restarting":
        return state.lifecycle_state == "restarting" and bool(state.restart_records) and state.restart_records[-1].get("status") == "restarting" and bool(state.restart_records[-1].get("saved_state"))
    if state_name == "post_restart":
        return state.lifecycle_state == "running" and bool(state.restart_records) and state.restart_records[-1].get("post_restart_validation") == "passed"
    if state_name == "worker_crashed":
        events = {item.get("event") for item in state.objective_progress}
        return state.lifecycle_state == "failed" and {"worker_started", "worker_crashed"} <= events
    if state_name == "event_pending":
        return any(item.get("event") == "capability_campaign_milestone_ready" and item.get("dedupe_key") for item in state.objective_progress)
    if state_name == "review_ready":
        return state.lifecycle_state == "review_ready" and any(item.get("event") == "capability_campaign_recommendation" and item.get("status") == "review_required" for item in state.objective_progress)
    if state_name == "completed":
        return state.lifecycle_state == "completed" and any(item.get("event") == "objective_completed" and item.get("completion_id") for item in state.objective_progress)
    if state_name == "archived":
        return state.lifecycle_state == "archived" and bool(state.archived_objectives) and bool(state.archived_objectives[-1].get("archived_at")) and not state.pending_chat_requests
    if state_name == "legacy_schema":
        return state.active_objective is not None and state.schema_version != "conversational_runtime_operation_marathon_1_v0"
    if state_name == "missing_campaign":
        return state.active_objective is not None and not state.capability_campaigns
    return state.lifecycle_state == state_name


@pytest.mark.parametrize("state_name", tuple(AUTHORITATIVE_STATE_CONDITIONS))
def test_authoritative_fixture_construction_validates_before_execution(tmp_path, state_name):
    app = _app(tmp_path)
    state = _authoritative_state(app, state_name)

    assert _validate_authoritative_fixture(state, state_name), (state_name, AUTHORITATIVE_STATE_CONDITIONS[state_name])


def test_authoritative_fixture_validation_rejects_lifecycle_label_only(tmp_path):
    app = _app(tmp_path)
    _goal(app)

    malformed = replace(app.conversational_runtime_state, lifecycle_state="blocked")

    assert not _validate_authoritative_fixture(malformed, "blocked_provider")


def test_no_active_goal_production_state_executes_all_applicable_obligations(tmp_path):
    """Use the production restore path, then prove chat is not goal-captured."""
    app = _app(tmp_path)
    assert app.conversational_runtime_state.active_objective is None
    assert app.conversational_runtime_state.lifecycle_state == "running"

    factual = "What color is the sky?"
    app._render_coordinated_foreground(factual, session_user_message=factual)
    assert "blue" in app.chat_records[-1][1].lower()
    assert app.conversational_runtime_state.active_objective is None

    mixed = "Your new goal is to study engines. Also, what is kinetic energy?"
    assert app._coordinate_mixed_dispatch(mixed, plan_message_dispatch(app.conversational_runtime_state, mixed))
    assert app.conversational_runtime_state.active_objective is not None
    assert app.conversational_runtime_state.conversation[-2].text == mixed
    assert "kinetic energy" in app.conversational_runtime_state.conversation[-1].text.lower()

    correction = "No, I meant your earlier answer. Also, why is the Moon gray?"
    assert app._coordinate_mixed_dispatch(correction, plan_message_dispatch(app.conversational_runtime_state, correction))
    assert "moon" in app.conversational_runtime_state.conversation[-1].text.lower()
    assert "i understand. i will treat this as ordinary conversation" not in app.conversational_runtime_state.conversation[-1].text.lower()
    assert len({turn.turn_id for turn in app.conversational_runtime_state.conversation}) == len(app.conversational_runtime_state.conversation)


def test_running_goal_production_state_preserves_foreground_and_healthy_duplicate_behavior(tmp_path):
    app = _app(tmp_path)
    _goal(app)
    original_id = app.conversational_runtime_state.active_objective.objective_id
    assert app.conversational_runtime_state.lifecycle_state == "running"

    factual = "What color is the sky?"
    app._render_coordinated_foreground(factual, session_user_message=factual)
    assert "blue" in app.chat_records[-1][1].lower()
    assert app.conversational_runtime_state.active_objective.objective_id == original_id

    mixed = "Pause the goal. Also, what is kinetic energy?"
    assert app._coordinate_mixed_dispatch(mixed, plan_message_dispatch(app.conversational_runtime_state, mixed))
    assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
    assert "kinetic energy" in app.conversational_runtime_state.conversation[-1].text.lower()

    resumed = handle_conversational_message(
        app.conversational_runtime_state,
        "Resume the active goal.",
        runtime_root=app.conversational_runtime_root,
        run_background_cycle=False,
    )
    app.conversational_runtime_state = resumed.state
    duplicate = handle_conversational_message(
        app.conversational_runtime_state,
        "Your new goal is to study engine efficiency.",
        runtime_root=app.conversational_runtime_root,
        run_background_cycle=False,
    )
    assert duplicate.objective_created is False
    assert duplicate.state.active_objective.objective_id == original_id
    assert "already" in duplicate.reply.lower() or "matches" in duplicate.reply.lower()


def test_paused_state_requires_no_worker_progress_and_resumes_once_without_losing_foreground(tmp_path):
    app = _app(tmp_path)
    paused = _authoritative_state(app, "paused")
    app.conversational_runtime_state = paused
    assert _validate_authoritative_fixture(paused, "paused")
    before_progress = len(paused.objective_progress)

    factual = "What color is the sky?"
    app._render_coordinated_foreground(factual, session_user_message=factual)
    assert "blue" in app.chat_records[-1][1].lower()
    assert len(app.conversational_runtime_state.objective_progress) == before_progress

    resumed = handle_conversational_message(
        app.conversational_runtime_state, "Resume the active goal.",
        runtime_root=app.conversational_runtime_root, run_background_cycle=False,
    )
    assert resumed.state.lifecycle_state == "running"
    assert sum(item.get("event") == "objective_resumed" for item in resumed.state.objective_progress) == 1
    repeated = handle_conversational_message(
        resumed.state, "Resume the active goal.", runtime_root=app.conversational_runtime_root, run_background_cycle=False,
    )
    assert repeated.state.lifecycle_state == "running"
    assert sum(item.get("event") == "objective_resumed" for item in repeated.state.objective_progress) == 1


def test_cycle_budget_exhausted_state_keeps_chat_open_and_explicit_new_goal_is_fresh(tmp_path):
    app = _app(tmp_path)
    exhausted = _authoritative_state(app, "cycle_budget_exhausted")
    app.conversational_runtime_state = exhausted
    assert _validate_authoritative_fixture(exhausted, "cycle_budget_exhausted")
    old_id = exhausted.active_objective.objective_id

    factual = "What color is the sky?"
    app._render_coordinated_foreground(factual, session_user_message=factual)
    assert "blue" in app.chat_records[-1][1].lower()

    fresh = handle_conversational_message(
        app.conversational_runtime_state, "Your new goal is to study engine efficiency.",
        runtime_root=app.conversational_runtime_root, run_background_cycle=False,
    )
    assert fresh.objective_created is True
    assert fresh.state.active_objective.objective_id != old_id
    assert fresh.state.completed_cycle_keys == ()
    assert "already working" not in fresh.reply.lower()


def test_operator_blocked_state_keeps_foreground_open_and_does_not_consume_unrelated_reply(tmp_path):
    app = _app(tmp_path)
    blocked = _authoritative_state(app, "blocked_operator")
    app.conversational_runtime_state = blocked
    assert _validate_authoritative_fixture(blocked, "blocked_operator")
    pending_before = blocked.pending_material_authority

    factual = "What color is the sky?"
    app._render_coordinated_foreground(factual, session_user_message=factual)
    assert "blue" in app.chat_records[-1][1].lower()
    assert app.conversational_runtime_state.pending_material_authority == pending_before

    mixed = "Pause the goal. Also, what is kinetic energy?"
    assert app._coordinate_mixed_dispatch(mixed, plan_message_dispatch(app.conversational_runtime_state, mixed))
    output = app.conversational_runtime_state.conversation[-1].text.lower()
    assert "kinetic energy" in output
    assert app.conversational_runtime_state.pending_material_authority == pending_before

    correction = "No, I meant your earlier answer. Also, why is the Moon gray?"
    assert app._coordinate_mixed_dispatch(correction, plan_message_dispatch(app.conversational_runtime_state, correction))
    assert "moon" in app.conversational_runtime_state.conversation[-1].text.lower()


def test_provider_blocked_state_binds_denial_once_and_preserves_foreground(tmp_path):
    app = _app(tmp_path)
    blocked = _authoritative_state(app, "blocked_provider")
    app.conversational_runtime_state = blocked
    assert _validate_authoritative_fixture(blocked, "blocked_provider")

    mixed = "Do not use a provider. Also, what color is the sky?"
    assert app._coordinate_mixed_dispatch(mixed, plan_message_dispatch(app.conversational_runtime_state, mixed))
    output = app.conversational_runtime_state.conversation[-1].text.lower()
    assert "blue" in output
    assert not app.conversational_runtime_state.pending_chat_requests
    assert len(app.conversational_runtime_state.resolved_chat_requests) == 1
    assert app.conversational_runtime_state.resolved_chat_requests[0].resolution_policy == "denied_continue_locally"

    duplicate = handle_conversational_message(
        app.conversational_runtime_state, "Do not use a provider.",
        runtime_root=app.conversational_runtime_root, run_background_cycle=False,
    )
    assert duplicate.state.provider_authorities == ()
    assert len(duplicate.state.resolved_chat_requests) == 1


def test_failed_state_preserves_foreground_and_never_claims_healthy_duplicate_work(tmp_path):
    app = _app(tmp_path)
    failed = _authoritative_state(app, "failed")
    app.conversational_runtime_state = failed
    assert _validate_authoritative_fixture(failed, "failed")
    old_id = failed.active_objective.objective_id

    factual = "What color is the sky?"
    app._render_coordinated_foreground(factual, session_user_message=factual)
    assert "blue" in app.chat_records[-1][1].lower()

    fresh = handle_conversational_message(
        app.conversational_runtime_state, "Your new goal is to study engine efficiency.",
        runtime_root=app.conversational_runtime_root, run_background_cycle=False,
    )
    assert fresh.objective_created is True
    assert fresh.state.active_objective.objective_id != old_id
    assert "already working" not in fresh.reply.lower()


def test_stalled_state_keeps_chat_open_and_explicit_new_goal_supersedes_stale_work(tmp_path):
    app = _app(tmp_path)
    stalled = _authoritative_state(app, "stalled")
    app.conversational_runtime_state = stalled
    assert _validate_authoritative_fixture(stalled, "stalled")
    old_id = stalled.active_objective.objective_id

    app._render_coordinated_foreground("What color is the sky?", session_user_message="What color is the sky?")
    assert "blue" in app.chat_records[-1][1].lower()
    fresh = handle_conversational_message(
        app.conversational_runtime_state, "Your new goal is to study engine efficiency.",
        runtime_root=app.conversational_runtime_root, run_background_cycle=False,
    )
    assert fresh.objective_created is True
    assert fresh.state.active_objective.objective_id != old_id
    assert "already working" not in fresh.reply.lower()


def test_model_budget_exhausted_state_preserves_foreground_and_fresh_goal_scope(tmp_path):
    app = _app(tmp_path)
    exhausted = _authoritative_state(app, "model_budget_exhausted")
    app.conversational_runtime_state = exhausted
    assert _validate_authoritative_fixture(exhausted, "model_budget_exhausted")
    old_id = exhausted.active_objective.objective_id

    app._render_coordinated_foreground("What color is the sky?", session_user_message="What color is the sky?")
    assert "blue" in app.chat_records[-1][1].lower()
    fresh = handle_conversational_message(
        app.conversational_runtime_state, "Your new goal is to study engine efficiency.",
        runtime_root=app.conversational_runtime_root, run_background_cycle=False,
    )
    assert fresh.objective_created is True
    assert fresh.state.active_objective.objective_id != old_id
    assert fresh.state.completed_cycle_keys == ()


def test_multiple_pending_state_clarifies_ambiguous_yes_without_consumption(tmp_path):
    app = _app(tmp_path)
    pending = _authoritative_state(app, "multiple_pending")
    app.conversational_runtime_state = pending
    assert _validate_authoritative_fixture(pending, "multiple_pending")

    message = "Yes. Also, what color is the sky?"
    assert app._coordinate_mixed_dispatch(message, plan_message_dispatch(app.conversational_runtime_state, message))
    output = app.conversational_runtime_state.conversation[-1].text.lower()
    assert "clarification" in output and "blue" in output
    assert len(app.conversational_runtime_state.pending_chat_requests) == 2
    assert not app.conversational_runtime_state.resolved_chat_requests


def test_adoption_pending_state_replays_evidence_without_consumption_and_binds_once(tmp_path):
    app = _app(tmp_path)
    pending = _authoritative_state(app, "adoption_pending")
    app.conversational_runtime_state = pending
    assert _validate_authoritative_fixture(pending, "adoption_pending")

    replay = "Show me the evidence again. Also, what color is the sky?"
    assert app._coordinate_mixed_dispatch(replay, plan_message_dispatch(app.conversational_runtime_state, replay))
    assert "blue" in app.conversational_runtime_state.conversation[-1].text.lower()
    assert len(app.conversational_runtime_state.pending_chat_requests) == 1
    assert not app.conversational_runtime_state.resolved_chat_requests

    approved = handle_conversational_message(
        app.conversational_runtime_state, "Yes, adopt it.",
        runtime_root=app.conversational_runtime_root, run_background_cycle=False,
    )
    assert not approved.state.pending_chat_requests
    assert len(approved.state.resolved_chat_requests) == 1
    duplicate = handle_conversational_message(
        approved.state, "Yes, adopt it.", runtime_root=app.conversational_runtime_root, run_background_cycle=False,
    )
    assert len(duplicate.state.resolved_chat_requests) == 1


def test_restart_pending_state_restores_once_without_duplicate_composed_turn(tmp_path):
    app = _app(tmp_path)
    pending = _authoritative_state(app, "restart_pending")
    app.conversational_runtime_state = pending
    assert _validate_authoritative_fixture(pending, "restart_pending")
    message = "Pause the goal. Also, what color is the sky?"
    assert app._coordinate_mixed_dispatch(message, plan_message_dispatch(app.conversational_runtime_state, message))
    before = app.conversational_runtime_state
    save_runtime_state(app.conversational_runtime_root, before)
    restored = start_or_restore_runtime(app.conversational_runtime_root)
    assert [item.as_record() for item in restored.conversation] == [item.as_record() for item in before.conversation]
    assert sum(item.role == "user" and item.text == message for item in restored.conversation) == 1
    assert restored.restart_records == before.restart_records


def test_restarting_state_preserves_foreground_and_restores_saved_runtime_once(tmp_path):
    app = _app(tmp_path)
    restarting = _authoritative_state(app, "restarting")
    app.conversational_runtime_state = restarting
    assert _validate_authoritative_fixture(restarting, "restarting")
    app._render_coordinated_foreground("What color is the sky?", session_user_message="What color is the sky?")
    assert "blue" in app.chat_records[-1][1].lower()
    save_runtime_state(app.conversational_runtime_root, restarting)
    restored = start_or_restore_runtime(app.conversational_runtime_root)
    assert restored.restart_records[-1]["restart_id"] == "restart-in-progress"
    assert restored.active_objective.objective_id == restarting.active_objective.objective_id


def test_post_restart_restored_state_continues_goal_without_duplicate_turns(tmp_path):
    app = _app(tmp_path)
    restored = _authoritative_state(app, "post_restart")
    app.conversational_runtime_state = restored
    assert _validate_authoritative_fixture(restored, "post_restart")
    message = "Pause the goal. Also, what color is the sky?"
    assert app._coordinate_mixed_dispatch(message, plan_message_dispatch(app.conversational_runtime_state, message))
    assert sum(item.role == "user" and item.text == message for item in app.conversational_runtime_state.conversation) == 1
    assert "blue" in app.conversational_runtime_state.conversation[-1].text.lower()


def test_worker_crashed_state_keeps_foreground_open_and_never_reuses_failed_goal(tmp_path):
    app = _app(tmp_path)
    crashed = _authoritative_state(app, "worker_crashed")
    app.conversational_runtime_state = crashed
    assert _validate_authoritative_fixture(crashed, "worker_crashed")
    old_id = crashed.active_objective.objective_id
    app._render_coordinated_foreground("What color is the sky?", session_user_message="What color is the sky?")
    assert "blue" in app.chat_records[-1][1].lower()
    fresh = handle_conversational_message(app.conversational_runtime_state, "Your new goal is to study engine efficiency.", runtime_root=app.conversational_runtime_root, run_background_cycle=False)
    assert fresh.objective_created and fresh.state.active_objective.objective_id != old_id


def test_event_pending_state_does_not_replace_foreground_or_duplicate_event_key(tmp_path):
    app = _app(tmp_path)
    pending = _authoritative_state(app, "event_pending")
    app.conversational_runtime_state = pending
    assert _validate_authoritative_fixture(pending, "event_pending")
    app._render_coordinated_foreground("What color is the sky?", session_user_message="What color is the sky?")
    assert "blue" in app.chat_records[-1][1].lower()
    keys = [item.get("dedupe_key") for item in app.conversational_runtime_state.objective_progress if item.get("dedupe_key")]
    assert keys.count("event-pending-1") == 1


def test_review_ready_state_keeps_chat_open_and_explicit_new_goal_does_not_reuse_review(tmp_path):
    app = _app(tmp_path)
    review_ready = _authoritative_state(app, "review_ready")
    app.conversational_runtime_state = review_ready
    assert _validate_authoritative_fixture(review_ready, "review_ready")
    old_id = review_ready.active_objective.objective_id
    app._render_coordinated_foreground("What color is the sky?", session_user_message="What color is the sky?")
    assert "blue" in app.chat_records[-1][1].lower()
    fresh = handle_conversational_message(app.conversational_runtime_state, "Your new goal is to study engine efficiency.", runtime_root=app.conversational_runtime_root, run_background_cycle=False)
    assert fresh.objective_created and fresh.state.active_objective.objective_id != old_id


def test_completed_state_remains_historical_and_explicit_new_goal_is_fresh(tmp_path):
    app = _app(tmp_path)
    completed = _authoritative_state(app, "completed")
    app.conversational_runtime_state = completed
    assert _validate_authoritative_fixture(completed, "completed")
    old_id = completed.active_objective.objective_id
    app._render_coordinated_foreground("What color is the sky?", session_user_message="What color is the sky?")
    assert "blue" in app.chat_records[-1][1].lower()
    fresh = handle_conversational_message(app.conversational_runtime_state, "Your new goal is to study engine efficiency.", runtime_root=app.conversational_runtime_root, run_background_cycle=False)
    assert fresh.objective_created and fresh.state.active_objective.objective_id != old_id
    assert "already working" not in fresh.reply.lower()


def test_archived_state_does_not_reactivate_and_explicit_new_goal_is_fresh(tmp_path):
    app = _app(tmp_path)
    archived = _authoritative_state(app, "archived")
    app.conversational_runtime_state = archived
    assert _validate_authoritative_fixture(archived, "archived")
    old_id = archived.active_objective.objective_id
    app._render_coordinated_foreground("What color is the sky?", session_user_message="What color is the sky?")
    assert "blue" in app.chat_records[-1][1].lower()
    fresh = handle_conversational_message(app.conversational_runtime_state, "Your new goal is to study engine efficiency.", runtime_root=app.conversational_runtime_root, run_background_cycle=False)
    assert fresh.objective_created and fresh.state.active_objective.objective_id != old_id
    assert fresh.state.pending_chat_requests == ()


def test_legacy_schema_restores_current_shape_idempotently_without_duplicate_turns(tmp_path):
    app = _app(tmp_path)
    restored = _authoritative_state(app, "legacy_schema")
    app.conversational_runtime_state = restored
    assert _validate_authoritative_fixture(restored, "legacy_schema")
    message = "Pause the goal. Also, what color is the sky?"
    assert app._coordinate_mixed_dispatch(message, plan_message_dispatch(app.conversational_runtime_state, message))
    save_runtime_state(app.conversational_runtime_root, app.conversational_runtime_state)
    second = start_or_restore_runtime(app.conversational_runtime_root)
    assert second.schema_version == app.conversational_runtime_state.schema_version
    assert sum(item.role == "user" and item.text == message for item in second.conversation) == 1


@pytest.mark.parametrize("case_id,_family,state_name,message,expected_controls", THREE_WAY_MANIFEST)
def test_three_way_manifest_executes_independent_obligations_once(tmp_path, case_id, _family, state_name, message, expected_controls):
    app = _app(tmp_path)
    state = _authoritative_state(app, state_name)
    app.conversational_runtime_state = state
    assert _validate_authoritative_fixture(state, state_name), case_id
    plan = plan_message_dispatch(state, message)

    assert expected_controls & {item.control_type for item in plan.controls}, (case_id, plan.as_record())
    assert plan.foreground.requested, case_id
    assert app._coordinate_mixed_dispatch(message, plan), case_id
    response = app.conversational_runtime_state.conversation[-1].text.lower()
    assert "i understand. i will treat this as ordinary conversation" not in response
    assert any(token in response for token in ("blue", "kinetic energy", "moon")), (case_id, response)
    assert sum(turn.role == "user" and turn.text == message for turn in app.conversational_runtime_state.conversation) == 1


def test_queued_state_preserves_reconciliation_turn_once_without_capturing_foreground(tmp_path):
    app = _app(tmp_path)
    queued = _authoritative_state(app, "queued")
    app.conversational_runtime_state = queued
    assert _validate_authoritative_fixture(queued, "queued")
    queued_text = "also compare that with how I use pronouns"

    app._render_coordinated_foreground("What color is the sky?", session_user_message="What color is the sky?")
    assert "blue" in app.chat_records[-1][1].lower()
    correction = "No, I meant your earlier answer. Also, why is the Moon gray?"
    assert app._coordinate_mixed_dispatch(correction, plan_message_dispatch(app.conversational_runtime_state, correction))
    assert "moon" in app.conversational_runtime_state.conversation[-1].text.lower()

    repeated = handle_conversational_message(
        app.conversational_runtime_state,
        "Your new goal is to study engine efficiency.",
        runtime_root=app.conversational_runtime_root,
        run_background_cycle=False,
    )
    assert repeated.objective_created is False
    save_runtime_state(app.conversational_runtime_root, app.conversational_runtime_state)
    restored = start_or_restore_runtime(app.conversational_runtime_root)
    assert sum(turn.role == "user" and turn.text == queued_text for turn in restored.conversation) == 1


@pytest.mark.parametrize("case_id,state_name,message", RESTART_DUPLICATE_MATRIX)
def test_restart_duplicate_matrix_restores_composed_work_exactly_once(tmp_path, case_id, state_name, message):
    app = _app(tmp_path)
    state = _authoritative_state(app, state_name)
    app.conversational_runtime_state = state
    assert _validate_authoritative_fixture(state, state_name), case_id

    assert app._coordinate_mixed_dispatch(message, plan_message_dispatch(state, message)), case_id
    before = app.conversational_runtime_state
    before_records = tuple(turn.as_record() for turn in before.conversation)
    before_request_ids = tuple(item.request_id for item in before.resolved_chat_requests)
    before_event_keys = tuple(
        item.get("dedupe_key") for item in before.objective_progress if item.get("dedupe_key")
    )
    save_runtime_state(app.conversational_runtime_root, before)
    first = start_or_restore_runtime(app.conversational_runtime_root)
    second = start_or_restore_runtime(app.conversational_runtime_root)

    assert tuple(turn.as_record() for turn in first.conversation) == before_records, case_id
    assert tuple(turn.as_record() for turn in second.conversation) == before_records, case_id
    assert sum(turn.role == "user" and turn.text == message for turn in second.conversation) == 1, case_id
    assert tuple(item.request_id for item in second.resolved_chat_requests) == before_request_ids, case_id
    assert len(before_event_keys) == len(set(before_event_keys)), case_id
    after_event_keys = tuple(item.get("dedupe_key") for item in second.objective_progress if item.get("dedupe_key"))
    assert after_event_keys == before_event_keys, case_id
    assert second.completed_cycle_keys == before.completed_cycle_keys, case_id


@pytest.mark.parametrize("_case_id,message,setup,expected_controls", THREE_WAY_CASES)
def test_three_way_execution_preserves_each_independent_obligation(tmp_path, _case_id, message, setup, expected_controls):
    app = _app(tmp_path)
    if setup:
        _goal(app)
        if setup == "multiple":
            provider = ChatAddressableRequest("provider", "provider_authority", app.conversational_runtime_state.active_objective.objective_id, "Engine", "Provider?", max_calls=1, max_spend_usd=1.0)
            direction = ChatAddressableRequest("direction", "directional_question", app.conversational_runtime_state.active_objective.objective_id, "Engine", "Direction?")
            app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(provider, direction))
        elif setup != "goal":
            _pending(app, setup)
    plan = plan_message_dispatch(app.conversational_runtime_state, message)

    assert expected_controls & {item.control_type for item in plan.controls}
    assert app._coordinate_mixed_dispatch(message, plan)
    output = app.conversational_runtime_state.conversation[-1].text.lower()
    assert "i understand. i will treat this as ordinary conversation" not in output
    assert app.conversational_runtime_state.conversation[-2].text == message


@pytest.mark.parametrize("runtime_state", RUNTIME_EXECUTION_STATES)
def test_runtime_state_execution_never_allows_goal_state_to_suppress_factual_chat(tmp_path, runtime_state):
    app = _app(tmp_path)
    if runtime_state == "no_active_goal":
        message = "Your new goal is to study engines. Also, what color is the sky?"
    else:
        _goal(app)
        if runtime_state == "multiple_pending":
            provider = ChatAddressableRequest("provider", "provider_authority", app.conversational_runtime_state.active_objective.objective_id, "Engine", "Provider?", max_calls=1, max_spend_usd=1.0)
            direction = ChatAddressableRequest("direction", "directional_question", app.conversational_runtime_state.active_objective.objective_id, "Engine", "Direction?")
            app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(provider, direction))
        elif runtime_state == "adoption_pending":
            _pending(app, "capability_adoption_and_restart")
        else:
            app.conversational_runtime_state = replace(app.conversational_runtime_state, lifecycle_state=runtime_state)
        message = "Pause the goal. Also, what color is the sky?"
    plan = plan_message_dispatch(app.conversational_runtime_state, message)

    assert plan.foreground.requested
    assert app._coordinate_mixed_dispatch(message, plan)
    output = app.conversational_runtime_state.conversation[-1].text.lower()
    assert "blue" in output
    assert "i understand. i will treat this as ordinary conversation" not in output
