from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_approved_plan_execution import (
    acquire_execution_lock,
    compile_execution_authority,
    compile_fixed_evaluator,
    compile_revision,
    evaluate_strategy,
    persist_work_item_transition,
    recover_prepared_execution,
    reconstruct_lifecycle_state,
    release_execution_lock,
    resume_paused_execution,
    run_approved_plan_execution,
    validate_execution_eligibility,
)
from orchestration.runtime.autonomy_goal_queue_planning import approve_plan_for_future_execution, compile_plan_proposal, normalize_plan_feedback, transition_goal
from tests.runtime_gsr.test_autonomy_3_goal_queue_planning import _queued

if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


class _DummyProviderManager:
    def __init__(self, keep_loaded: bool = True) -> None:
        self.keep_loaded = keep_loaded

    def warm(self, _model_id: str) -> None:
        return None


def _approved_plan():
    goal = _queued()
    plan = compile_plan_proposal(goal)
    approval = approve_plan_for_future_execution(plan, normalize_plan_feedback("looks good"))
    return goal, plan, approval


def test_approved_plan_eligibility_and_digest_binding():
    _goal, plan, approval = _approved_plan()
    authority = compile_execution_authority(plan, approval)
    ok = validate_execution_eligibility(plan, approval, authority)
    bad_approval = {**approval, "plan_digest": "wrong"}
    mismatch = validate_execution_eligibility(plan, bad_approval, authority)

    assert ok["eligible"] is True
    assert mismatch["eligible"] is False
    assert "plan_approval_digest_mismatch" in mismatch["reasons"]


def test_stale_superseded_consumed_duplicate_resolved_and_missing_validator_rejected():
    _goal, plan, approval = _approved_plan()
    authority = compile_execution_authority(plan, approval)
    consumed = {**authority, "consumed": True}
    no_validator = {**plan, "validation_strategy": ()}

    assert "superseded_plan" in validate_execution_eligibility(plan, approval, authority, active_plan_digest="newer")["reasons"]
    assert "authority_consumed" in validate_execution_eligibility(plan, approval, consumed)["reasons"]
    assert "duplicate_active_runner" in validate_execution_eligibility(plan, approval, authority, active_runner_exists=True)["reasons"]
    assert "goal_resolved_before_execution" in validate_execution_eligibility(plan, approval, authority, resolved_goal=True)["reasons"]
    assert "missing_validator" in validate_execution_eligibility(no_validator, approval, authority)["reasons"]


def test_authority_expiration_and_revocation_are_rejected():
    _goal, plan, approval = _approved_plan()
    expired = compile_execution_authority(plan, approval, issued_at="2026-07-23T00:00:00+00:00", expires_at="2026-07-23T00:00:01+00:00")
    revoked = {**compile_execution_authority(plan, approval), "revoked": True}

    late = validate_execution_eligibility(plan, approval, expired, now=lambda: datetime(2026, 7, 23, 0, 0, 2, tzinfo=timezone.utc))
    revoked_result = validate_execution_eligibility(plan, approval, revoked)

    assert "authority_expired" in late["reasons"]
    assert "authority_revoked" in revoked_result["reasons"]


def test_evaluator_fixed_before_strategy_and_hidden_cases_isolated():
    _goal, plan, _approval = _approved_plan()
    evaluator = compile_fixed_evaluator(plan)

    assert evaluator["sealed_before_strategy"] is True
    assert "ambiguous_near_match" in evaluator["hidden_cases"]
    assert evaluator["leakage_controls"]
    assert evaluator["negative_controls"] is True
    assert evaluator["transfer_cases"] is True


def test_initial_pass_needs_no_revision(tmp_path):
    _goal, plan, approval = _approved_plan()
    result = run_approved_plan_execution(plan, approval, output_root=tmp_path, initial_pass=True)

    assert result["status"] == "completed_without_revision"
    assert result["revision"] is None
    assert len(result["strategies"]) == 1
    assert result["final_synthesis"]["capability_promotion"] is False


def test_specific_failure_revision_and_revised_pass(tmp_path):
    _goal, plan, approval = _approved_plan()
    result = run_approved_plan_execution(plan, approval, output_root=tmp_path)

    assert result["status"] == "completed_with_provisional_evidence"
    assert result["evaluations"][0]["aggregate_status"] == "revision_required"
    assert result["revision"]["diagnosed_first_incorrect_transition"] == "identifier absent -> name similarity -> confirmed match instead of ambiguity"
    assert result["revision"]["unchanged_evaluator_digest"] == result["evaluator"]["artifact_digest"]
    assert result["evaluations"][1]["aggregate_status"] == "passed"
    assert result["final_synthesis"]["provisional_capability_evidence"] is True


def test_revision_requires_failed_evidence_and_budget():
    _goal, plan, _approval = _approved_plan()
    evaluator = compile_fixed_evaluator(plan)
    strategy = {"strategy_id": "s", "artifact_digest": "d"}
    passed = {"failed_case_ids": (), "artifact_digest": "e"}
    failed = {"failed_case_ids": ("case",), "artifact_digest": "e"}

    try:
        compile_revision(strategy, passed, evaluator, budget_remaining=1)
    except ValueError as exc:
        assert str(exc) == "revision_requires_failed_evidence"
    else:
        raise AssertionError("revision without failed evidence accepted")
    try:
        compile_revision(strategy, failed, evaluator, budget_remaining=0)
    except ValueError as exc:
        assert str(exc) == "revision_budget_exhausted"
    else:
        raise AssertionError("revision without budget accepted")


def test_revision_also_fails_stops_honestly(tmp_path):
    _goal, plan, approval = _approved_plan()
    result = run_approved_plan_execution(plan, approval, output_root=tmp_path, force_revision_fail=True)

    assert result["status"] == "failed_after_revision"
    assert len(result["strategies"]) == 2
    assert result["final_synthesis"]["provisional_capability_evidence"] is False


def test_final_synthesis_safety_counts(tmp_path):
    _goal, plan, approval = _approved_plan()
    result = run_approved_plan_execution(plan, approval, output_root=tmp_path)
    final = result["final_synthesis"]

    assert final["provider_calls"] == 0
    assert final["source_mutation_count"] == 0
    assert final["trusted_admission"] is False
    assert final["capability_promotion"] is False
    assert final["learning_attempts"] == 1


def test_durable_work_item_lifecycle_and_invalid_transitions(tmp_path):
    _goal, plan, approval = _approved_plan()
    result = run_approved_plan_execution(plan, approval, output_root=tmp_path)
    lifecycle = reconstruct_lifecycle_state(tmp_path)

    assert result["status"] == "completed_with_provisional_evidence"
    assert lifecycle["terminal"] is True
    assert lifecycle["states"]["approved-plan-execution"] == "terminal"
    assert lifecycle["states"]["sealed-evaluator"] == "completed"
    assert lifecycle["states"]["initial-strategy-evaluation"] == "failed_evaluation"
    assert lifecycle["states"]["bounded-strategy-revision"] == "revision_required"
    try:
        persist_work_item_transition(
            tmp_path,
            execution_id="execution",
            goal_id=plan["goal_id"],
            plan_id=plan["plan_id"],
            work_item_id="sealed-evaluator",
            previous_state="completed",
            next_state="running",
            reason="illegal_rerun",
            source_artifact_id="source",
            source_artifact_digest="digest",
            authority_id="authority",
            controller_cycle=99,
        )
    except ValueError as exc:
        assert str(exc) == "invalid_work_item_transition:completed->running"
    else:
        raise AssertionError("invalid lifecycle transition accepted")


def test_lr4_compatible_lock_rejects_second_runner_and_releases(tmp_path):
    _goal, plan, approval = _approved_plan()
    authority = compile_execution_authority(plan, approval)
    first = acquire_execution_lock(tmp_path, authority)
    second = acquire_execution_lock(tmp_path, authority)

    assert first["acquired"] is True
    assert first["owner"]["schema"] == "live_runtime_4_runner_lock_owner_v1"
    assert first["owner"]["runner_lock_scope"]
    assert second["acquired"] is False
    assert second["reason"] == "duplicate_active_runner"
    release_execution_lock(tmp_path)
    third = acquire_execution_lock(tmp_path, authority)
    assert third["acquired"] is True
    release_execution_lock(tmp_path)


def test_operator_pause_persists_safe_boundary_and_requires_explicit_resume(tmp_path):
    _goal, plan, approval = _approved_plan()
    paused = run_approved_plan_execution(plan, approval, output_root=tmp_path, pause_after_stage="evaluator")
    replay = run_approved_plan_execution(plan, approval, output_root=tmp_path)
    resumed = resume_paused_execution(plan, approval, output_root=tmp_path)
    second_replay = run_approved_plan_execution(plan, approval, output_root=tmp_path)

    assert paused["status"] == "paused_operator"
    assert not (tmp_path / "runner.lock").exists()
    assert replay["status"] == "paused_operator"
    assert resumed["status"] == "completed_with_provisional_evidence"
    assert second_replay["status"] == "completed_with_provisional_evidence"
    assert len(tuple((tmp_path / "final_synthesis").glob("*.json"))) == 1


def test_operator_stop_is_terminal_and_does_not_resume(tmp_path):
    _goal, plan, approval = _approved_plan()
    stopped = run_approved_plan_execution(plan, approval, output_root=tmp_path, stop_after_stage="prepared")
    replay = run_approved_plan_execution(plan, approval, output_root=tmp_path)

    assert stopped["status"] == "stopped_by_operator"
    assert replay["status"] == "stopped_by_operator"
    assert not tuple((tmp_path / "final_synthesis").glob("*.json"))
    assert not (tmp_path / "runner.lock").exists()


def test_authority_expiration_before_work_item_stops_at_safe_boundary(tmp_path):
    _goal, plan, approval = _approved_plan()
    authority = compile_execution_authority(plan, approval, issued_at="2026-07-23T00:00:00+00:00", expires_at="2026-07-23T00:00:01+00:00")
    result = run_approved_plan_execution(
        plan,
        approval,
        output_root=tmp_path,
        authority=authority,
        now=lambda: datetime(2026, 7, 23, 0, 0, 2, tzinfo=timezone.utc),
    )

    assert result["status"] == "integrity_stop"
    assert "authority_expired" in result["eligibility"]["reasons"]
    assert not (tmp_path / "runner.lock").exists()


def test_authority_expiration_after_start_stops_before_next_work_item(tmp_path):
    _goal, plan, approval = _approved_plan()
    authority = compile_execution_authority(plan, approval, issued_at="2026-07-23T00:00:00+00:00", expires_at="2026-07-23T00:00:03+00:00")
    ticks = iter(
        (
            datetime(2026, 7, 23, 0, 0, 1, tzinfo=timezone.utc),
            datetime(2026, 7, 23, 0, 0, 4, tzinfo=timezone.utc),
        )
    )

    result = run_approved_plan_execution(plan, approval, output_root=tmp_path, authority=authority, now=lambda: next(ticks))
    lifecycle = reconstruct_lifecycle_state(tmp_path)

    assert result["status"] == "authority_expired"
    assert lifecycle["states"]["approved-plan-preflight"] == "completed"
    assert lifecycle["states"]["approved-plan-execution"] == "authority_expired"
    assert not tuple((tmp_path / "evaluator").glob("*.json"))
    assert not (tmp_path / "runner.lock").exists()


def test_prepared_journal_recovery_resumes_without_duplicate_semantic_execution(tmp_path):
    _goal, plan, approval = _approved_plan()
    interrupted = run_approved_plan_execution(plan, approval, output_root=tmp_path, crash_after_prepared=True)
    recovered = recover_prepared_execution(tmp_path)

    assert interrupted["status"] == "interrupted_after_prepared_journal"
    assert interrupted["journal"]["semantic_execution_started"] is False
    assert recovered["status"] == "resumed_prepared_not_applied"
    assert recovered["classification"] == "prepared_not_applied"
    assert recovered["result"]["status"] == "completed_with_provisional_evidence"
    assert len(tuple((tmp_path / "final_synthesis").glob("*.json"))) == 1


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


def _seed_approved_plan(app: DELTA.DeltaApp, plan: dict[str, object], approval: dict[str, object]) -> None:
    plan_dir = app.operator_ux_root / "autonomy_3_plans"
    approval_dir = app.operator_ux_root / "autonomy_3_plan_approvals"
    plan_dir.mkdir(parents=True, exist_ok=True)
    approval_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / f"{plan['plan_id']}.json").write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
    (approval_dir / f"{approval['approval_id']}.json").write_text(json.dumps(approval, sort_keys=True), encoding="utf-8")
    app._refresh_operator_ux_views()


def _button_enabled(app: DELTA.DeltaApp, key: str) -> bool:
    return "disabled" not in app.a4_control_buttons[key].state()


def test_tk_visible_a4_controls_render_and_bind_existing_handlers(monkeypatch, tmp_path):
    _goal, plan, approval = _approved_plan()
    root, app = _app(monkeypatch, tmp_path)
    try:
        _seed_approved_plan(app, plan, approval)
        assert set(app.a4_control_buttons) == {"start", "pause", "resume", "stop", "step", "limits", "evidence"}
        assert app.a4_execution_status.get() == "A4: approved, not started"
        assert _button_enabled(app, "start") is True
        assert _button_enabled(app, "pause") is False
        assert _button_enabled(app, "resume") is False
        assert _button_enabled(app, "stop") is False
        assert _button_enabled(app, "step") is True
        assert _button_enabled(app, "limits") is True
        assert _button_enabled(app, "evidence") is True

        calls = []

        def fake_start(*, mode: str = "start") -> dict[str, object]:
            calls.append(("start", mode))
            return {"status": mode}

        def fake_explain(topic: str) -> dict[str, object]:
            calls.append(("explain", topic))
            return {"status": "explained", "topic": topic}

        monkeypatch.setattr(app, "_start_autonomy_4_approved_plan", fake_start)
        monkeypatch.setattr(app, "_explain_autonomy_4_execution", fake_explain)

        app.a4_control_buttons["start"].invoke()
        app.a4_control_buttons["step"].invoke()
        app.a4_control_buttons["limits"].invoke()
        app.a4_control_buttons["evidence"].invoke()

        assert calls == [("start", "start"), ("explain", "step"), ("explain", "limits"), ("explain", "evidence")]
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_tk_visible_a4_control_state_tracks_running_paused_and_terminal(monkeypatch, tmp_path):
    _goal, plan, approval = _approved_plan()
    root, app = _app(monkeypatch, tmp_path)
    try:
        _seed_approved_plan(app, plan, approval)
        execution_root = app.operator_ux_root / "autonomy_4_execution"
        authority = compile_execution_authority(plan, approval)
        acquire_execution_lock(execution_root, authority)
        app._refresh_operator_ux_views()
        assert app.a4_execution_status.get() == "A4: running"
        assert _button_enabled(app, "start") is False
        assert _button_enabled(app, "pause") is True
        assert _button_enabled(app, "resume") is False
        assert _button_enabled(app, "stop") is True
        release_execution_lock(execution_root)

        run_approved_plan_execution(plan, approval, output_root=execution_root, pause_after_stage="evaluator")
        app._refresh_operator_ux_views()
        assert app.a4_execution_status.get() == "A4: paused"
        assert _button_enabled(app, "start") is False
        assert _button_enabled(app, "pause") is False
        assert _button_enabled(app, "resume") is True
        assert _button_enabled(app, "stop") is True

        resume_paused_execution(plan, approval, output_root=execution_root)
        app._refresh_operator_ux_views()
        assert app.a4_execution_status.get() == "A4: completed"
        assert _button_enabled(app, "start") is False
        assert _button_enabled(app, "pause") is False
        assert _button_enabled(app, "resume") is False
        assert _button_enabled(app, "stop") is False
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_tk_visible_a4_pause_resume_stop_buttons_share_existing_handler(monkeypatch, tmp_path):
    _goal, plan, approval = _approved_plan()
    root, app = _app(monkeypatch, tmp_path)
    try:
        _seed_approved_plan(app, plan, approval)
        calls = []

        def fake_start(*, mode: str = "start") -> dict[str, object]:
            calls.append(mode)
            return {"status": mode}

        monkeypatch.setattr(app, "_start_autonomy_4_approved_plan", fake_start)
        execution_root = app.operator_ux_root / "autonomy_4_execution"
        authority = compile_execution_authority(plan, approval)
        acquire_execution_lock(execution_root, authority)
        app._refresh_operator_ux_views()
        app.a4_control_buttons["pause"].invoke()
        app.a4_control_buttons["stop"].invoke()
        release_execution_lock(execution_root)

        run_approved_plan_execution(plan, approval, output_root=execution_root, pause_after_stage="evaluator")
        app._refresh_operator_ux_views()
        app.a4_control_buttons["resume"].invoke()

        assert calls == ["pause", "stop", "resume"]
        assert not tuple((execution_root / "final_synthesis").glob("*.json"))
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_tk_visible_a4_button_and_chat_start_share_persisted_action(monkeypatch, tmp_path):
    _goal, plan, approval = _approved_plan()
    root, app = _app(monkeypatch, tmp_path)
    try:
        app.operator_ux_root = tmp_path / "button-root"
        _seed_approved_plan(app, plan, approval)
        app.a4_control_buttons["start"].invoke()
        button_final = json.loads(next((app.operator_ux_root / "autonomy_4_final_synthesis").glob("*.json")).read_text(encoding="utf-8"))

        app.operator_ux_root = tmp_path / "chat-root"
        _seed_approved_plan(app, plan, approval)
        _send(app, root, "start approved plan")
        chat_final = json.loads(next((app.operator_ux_root / "autonomy_4_final_synthesis").glob("*.json")).read_text(encoding="utf-8"))

        assert button_final["final_disposition"] == chat_final["final_disposition"]
        assert button_final["artifact_digest"] == chat_final["artifact_digest"]
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_tk_visible_a4_controls_restore_terminal_state_from_persisted_records(monkeypatch, tmp_path):
    _goal, plan, approval = _approved_plan()
    root, app = _app(monkeypatch, tmp_path)
    try:
        _seed_approved_plan(app, plan, approval)
        app.a4_control_buttons["start"].invoke()
        assert app.a4_execution_status.get() == "A4: completed"

        app.a4_execution_status.set("A4: stale")
        for button in app.a4_control_buttons.values():
            button.configure(state=tk.NORMAL)
        app._refresh_operator_ux_views()
        assert app.a4_execution_status.get() == "A4: completed"
        assert _button_enabled(app, "start") is False
        assert _button_enabled(app, "pause") is False
        assert _button_enabled(app, "resume") is False
        assert _button_enabled(app, "stop") is False
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_tk_start_approved_plan_terminal_restart_no_duplicate(monkeypatch, tmp_path):
    _goal, plan, approval = _approved_plan()
    root, app = _app(monkeypatch, tmp_path)
    try:
        plan_dir = app.operator_ux_root / "autonomy_3_plans"
        approval_dir = app.operator_ux_root / "autonomy_3_plan_approvals"
        plan_dir.mkdir(parents=True, exist_ok=True)
        approval_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / f"{plan['plan_id']}.json").write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
        (approval_dir / f"{approval['approval_id']}.json").write_text(json.dumps(approval, sort_keys=True), encoding="utf-8")

        _send(app, root, "start approved plan")
        finals = tuple((app.operator_ux_root / "autonomy_4_final_synthesis").glob("*.json"))
        assert len(finals) == 1
        final = json.loads(finals[0].read_text(encoding="utf-8"))
        assert final["final_disposition"] == "completed_with_provisional_evidence"
        assert final["provider_calls"] == 0
        assert final["source_mutation_count"] == 0
        assert final["trusted_admission"] is False
        assert final["capability_promotion"] is False
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass

    recovered_root, recovered = _app(monkeypatch, tmp_path)
    try:
        recovered.operator_ux_root = tmp_path / "operator-ux"
        recovered._refresh_operator_ux_views()
        before = set(recovered.operator_ux_narration_events)
        recovered._refresh_operator_ux_views()
        assert before == set(recovered.operator_ux_narration_events)
        assert len(tuple((recovered.operator_ux_root / "autonomy_4_final_synthesis").glob("*.json"))) == 1
    finally:
        try:
            recovered_root.destroy()
        except tk.TclError:
            pass


def test_tk_pause_resume_approved_plan(monkeypatch, tmp_path):
    _goal, plan, approval = _approved_plan()
    root, app = _app(monkeypatch, tmp_path)
    try:
        plan_dir = app.operator_ux_root / "autonomy_3_plans"
        approval_dir = app.operator_ux_root / "autonomy_3_plan_approvals"
        plan_dir.mkdir(parents=True, exist_ok=True)
        approval_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / f"{plan['plan_id']}.json").write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
        (approval_dir / f"{approval['approval_id']}.json").write_text(json.dumps(approval, sort_keys=True), encoding="utf-8")

        _send(app, root, "pause approved plan")
        assert not tuple((app.operator_ux_root / "autonomy_4_final_synthesis").glob("*.json"))
        assert not (app.operator_ux_root / "autonomy_4_execution" / "runner.lock").exists()

        _send(app, root, "resume approved plan")
        finals = tuple((app.operator_ux_root / "autonomy_4_final_synthesis").glob("*.json"))
        assert len(finals) == 1
        final = json.loads(finals[0].read_text(encoding="utf-8"))
        assert final["final_disposition"] == "completed_with_provisional_evidence"
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
