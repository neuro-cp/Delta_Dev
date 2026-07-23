from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_goal_queue_planning import (
    approve_plan_for_future_execution,
    compile_goal_record,
    compile_plan_proposal,
    compile_plan_review_request,
    dedupe_or_plan_disposition,
    normalize_plan_feedback,
    select_goal_for_planning,
    transition_goal,
)

if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


class _DummyProviderManager:
    def __init__(self, keep_loaded: bool = True) -> None:
        self.keep_loaded = keep_loaded

    def warm(self, _model_id: str) -> None:
        return None


def _selection(condition: str = "missing_or_unreliable_identifier_reconciliation", *, priority: int = 5, missing=(), authority=()):
    candidate = {
        "candidate_id": f"candidate-{condition}",
        "artifact_digest": f"digest-{condition}",
        "title": condition.replace("_", " ").title(),
        "objective": f"Improve {condition.replace('_', ' ')}.",
        "condition_key": condition,
        "evidence_roots": ("root",),
        "source_artifact_ids": ("artifact",),
        "source_artifact_digests": ("artifact-digest",),
        "expected_benefit": 8,
        "success_criteria": ("sealed evaluation passes",),
        "prerequisites": ("retained evidence", "validator design"),
        "missing_prerequisites": tuple(missing),
        "estimated_cost": 3,
        "risk": 2,
        "authority_requirements": tuple(authority),
    }
    return {
        "selected_candidate_id": candidate["candidate_id"],
        "selected_candidate_digest": candidate["artifact_digest"],
        "ranking_id": "ranking-1",
        "ranking_digest": "ranking-digest",
        "selected_candidate": candidate,
        "status": "queued",
        "priority": priority,
    }


def _queued(condition="missing_or_unreliable_identifier_reconciliation", *, priority=5, missing=(), authority=()):
    goal = compile_goal_record(_selection(condition, priority=priority, missing=missing, authority=authority), priority=priority)
    queued, _ = transition_goal(goal, "queued", reason="operator_selected", source_authority="autonomy_2_selection")
    return queued


def test_durable_goal_states_and_valid_transitions():
    goal = compile_goal_record(_selection(), priority=7)
    queued, t1 = transition_goal(goal, "queued", reason="approved_goal_added", source_authority="operator")
    planning, t2 = transition_goal(queued, "planning", reason="selected_for_planning", source_authority="scheduler")
    waiting, t3 = transition_goal(planning, "waiting_for_operator", reason="plan_proposed", source_authority="planner")

    assert goal["current_queue_state"] == "approved"
    assert queued["current_queue_state"] == "queued"
    assert waiting["current_queue_state"] == "waiting_for_operator"
    assert t1["previous_state"] == "approved" and t2["next_state"] == "planning" and t3["next_state"] == "waiting_for_operator"


def test_invalid_transition_rejected():
    goal = compile_goal_record(_selection())
    try:
        transition_goal(goal, "planning", reason="skip_queue", source_authority="test")
    except ValueError as exc:
        assert str(exc) == "queue_transition_invalid"
    else:
        raise AssertionError("invalid transition accepted")


def test_duplicate_resolved_and_prohibited_dispositions():
    goal = _queued("same_goal")
    duplicate = _queued("same_goal")
    resolved = _queued("resolved_goal")
    prohibited = _queued("network_goal", authority=("network_expansion",))

    assert dedupe_or_plan_disposition(goal, (duplicate,))["disposition"] == "duplicate_suppressed"
    assert dedupe_or_plan_disposition(resolved, (), resolved_conditions=("resolved_goal",))["disposition"] == "resolved_before_planning"
    assert dedupe_or_plan_disposition(prohibited, ())["disposition"] == "blocked_prohibited_authority"


def test_priority_selection_excludes_paused_and_deferred():
    low = _queued("low", priority=1)
    high = _queued("high", priority=10)
    paused, _ = transition_goal(_queued("paused"), "deferred", reason="operator_deferred", source_authority="operator")

    assert select_goal_for_planning((low, high, paused))["condition_key"] == "high"


def test_goal_sensitive_work_graph_and_missing_prerequisite_item():
    capability = _queued("missing_or_unreliable_identifier_reconciliation")
    maintenance = _queued("operator_summary_maintenance")
    missing = _queued("missing_prereq_goal", missing=("accepted parser",))
    cap_plan = compile_plan_proposal(capability)
    maint_plan = compile_plan_proposal(maintenance)
    missing_plan = compile_plan_proposal(missing)

    assert cap_plan["proposed_work_items"][0]["title"].startswith("Inspect current accepted competence")
    assert maint_plan["proposed_work_items"][0]["title"].startswith("Inspect retained summaries")
    assert missing_plan["proposed_work_items"][0]["task_class"] == "prerequisite_analysis"


def test_validation_first_fields_and_authority_defaults():
    plan = compile_plan_proposal(_queued())

    assert all(item["validator"]["evaluator_authoring_boundary"] == "defined before candidate execution" for item in plan["proposed_work_items"])
    assert all(item["validator"]["negative_controls"] is True for item in plan["proposed_work_items"])
    assert plan["authority_requirements"]["tracked_source_mutation"] is False
    assert plan["authority_requirements"]["network"] is False
    assert plan["authority_requirements"]["trusted_admission"] is False
    assert plan["execution_started"] is False and plan["learning_started"] is False


def test_budget_and_preference_sensitive_planning():
    full = compile_plan_proposal(_queued(), budget={"max_work_items": 6})
    reduced = compile_plan_proposal(_queued(), budget={"max_work_items": 3}, preference={"priority": "low_cost"})

    assert len(full["proposed_work_items"]) > len(reduced["proposed_work_items"])
    assert reduced["estimated_budgets"]["max_work_items"] == 3


def test_plan_digest_stability_versioning_and_original_immutability():
    goal = _queued()
    original = compile_plan_proposal(goal)
    same = compile_plan_proposal(goal)
    revised = compile_plan_proposal(goal, prior_plan=original, requested_changes=("reduce budget",), budget={"max_work_items": 3})

    assert original["artifact_digest"] == same["artifact_digest"]
    assert revised["artifact_digest"] != original["artifact_digest"]
    assert revised["prior_plan_digest"] == original["artifact_digest"]
    assert original["requested_changes"] == ()


def test_plan_review_request_and_feedback_boundaries():
    plan = compile_plan_proposal(_queued())
    request = compile_plan_review_request(plan)
    explain = normalize_plan_feedback("explain the evaluator")
    ambiguous = normalize_plan_feedback("maybe")
    approval = approve_plan_for_future_execution(plan, normalize_plan_feedback("looks good"))

    assert request["title"] == "I created a plan for this goal"
    assert request["plan_digest"] == plan["artifact_digest"]
    assert request["goal_digest"] == plan["goal_digest"]
    assert request["active_plan_version"] == plan["plan_id"]
    assert request["request_integrity_digest"] != request["card_digest"]
    assert request["work_graph_digest"]
    assert request["authority_limits_digest"]
    assert request["learning_attempts"] == 0
    assert explain["intent"] == "explain"
    assert ambiguous["requires_clarification"] is True
    assert approval["plan_status"] == "approved_for_future_execution"
    assert approval["mission_started"] is False
    assert approval["worker_started"] is False
    assert approval["provider_calls"] == 0
    assert approval["learning_started"] is False


def _app(monkeypatch, tmp_path):
    monkeypatch.setattr(DELTA, "ProviderManager", _DummyProviderManager)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ROOT", tmp_path / "live-runtime-2")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ROOT", tmp_path / "live-runtime-3")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ROOT", tmp_path / "live-runtime-4")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    root = tk.Tk()
    root.update()
    app = DELTA.DeltaApp(root)
    app.operator_ux_root = tmp_path / "operator-ux"
    root.update()
    return root, app


def _send(app: DELTA.DeltaApp, root: tk.Tk, message: str) -> None:
    app.chat_input.delete(0, tk.END)
    app.chat_input.insert(0, message)
    app._send_chat()
    root.update()


def test_tk_plan_next_goal_revision_approval_restart_no_execution(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        goal = _queued("missing_or_unreliable_identifier_reconciliation", priority=9)
        lower = _queued("operator_summary_maintenance", priority=1)
        duplicate = _queued("missing_or_unreliable_identifier_reconciliation", priority=5)
        goal_dir = app.operator_ux_root / "approved_goals"
        goal_dir.mkdir(parents=True, exist_ok=True)
        (goal_dir / "goal.json").write_text(json.dumps(goal, sort_keys=True), encoding="utf-8")
        (goal_dir / "lower.json").write_text(json.dumps(lower, sort_keys=True), encoding="utf-8")
        (goal_dir / "duplicate.json").write_text(json.dumps(duplicate, sort_keys=True), encoding="utf-8")

        _send(app, root, "plan next queued goal")
        assert app.active_operator_ux_request is not None
        assert app.operator_ux_request_card["title"] == "I created a plan for this goal"
        original_plans = tuple((app.operator_ux_root / "autonomy_3_plans").glob("*.json"))
        assert len(original_plans) == 1

        _send(app, root, "explain the evaluator")
        assert app.active_operator_ux_request is not None
        _send(app, root, "reduce the budget")
        revised_plans = tuple((app.operator_ux_root / "autonomy_3_plans").glob("*.json"))
        assert len(revised_plans) == 2
        revised_request = app.active_operator_ux_request
        revised_plan = json.loads((app.operator_ux_root / "autonomy_3_plans" / f"{revised_request['plan_id']}.json").read_text(encoding="utf-8"))
        assert revised_request["plan_digest"] == revised_plan["artifact_digest"]
        assert revised_request["active_plan_version"] == revised_plan["plan_id"]
        assert revised_plan["prior_plan_id"]

        _send(app, root, "looks good")
        assert app.active_operator_ux_request is None
        approvals = tuple((app.operator_ux_root / "autonomy_3_plan_approvals").glob("*.json"))
        consumed = tuple((app.operator_ux_root / "consumed_responses").glob("*.json"))
        assert len(approvals) == 1
        assert len(consumed) == 2
        approval = json.loads(approvals[0].read_text(encoding="utf-8"))
        assert approval["plan_status"] == "approved_for_future_execution"
        assert approval["plan_digest"] == revised_plan["artifact_digest"]
        assert approval["plan_id"] == revised_plan["plan_id"]
        assert approval["mission_started"] is False
        assert approval["worker_started"] is False
        assert approval["provider_calls"] == 0
        assert approval["learning_started"] is False
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass

    recovered_root, recovered = _app(monkeypatch, tmp_path)
    try:
        recovered.operator_ux_root = tmp_path / "operator-ux"
        recovered._refresh_operator_ux_views()
        assert recovered.active_operator_ux_request is None
        assert len(tuple((recovered.operator_ux_root / "autonomy_3_plan_approvals").glob("*.json"))) == 1
        before = set(recovered.operator_ux_narration_events)
        recovered._refresh_operator_ux_views()
        assert before == set(recovered.operator_ux_narration_events)
    finally:
        try:
            recovered_root.destroy()
        except tk.TclError:
            pass
