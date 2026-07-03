from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_dry_run_action_execution import (
    RUNTIME_V14Q_INVARIANT_FLAGS,
    DryRunActionKind,
    DryRunRequestedMode,
    DryRunSideEffectRisk,
    DryRunSimulatedStatus,
    create_dry_run_action,
    create_dry_run_execution_input,
    create_dry_run_execution_report_entry,
    create_dry_run_execution_result,
    create_dry_run_execution_step,
    create_dry_run_execution_trace,
    create_dry_run_rollback_plan,
    create_execution_side_effect_boundary,
    invariant_flags_safe,
    validate_dry_run_action_inactive,
    validate_dry_run_execution_input_simulation_only,
    validate_dry_run_execution_report_entry_review_only,
    validate_dry_run_execution_result_simulated,
    validate_dry_run_execution_step_simulated,
    validate_dry_run_execution_trace_review_only,
    validate_dry_run_rollback_plan_inert,
    validate_execution_side_effect_boundary_blocks_effects,
)
from orchestration.runtime.v14_dry_run_action_execution_report import (
    build_dry_run_action_execution_report_data,
    write_dry_run_action_execution_report,
)


def _dry_run_parts():
    action = create_dry_run_action(
        action_intent_id="intent-1",
        action_kind=DryRunActionKind.CALL_TOOL,
        action_summary="simulate a future tool call",
        source_reference_ids=("trace-1",),
        ledger_entry_id="ledger-1",
        authorization_decision_id="auth-1",
    )
    execution_input = create_dry_run_execution_input(
        action,
        requested_mode=DryRunRequestedMode.SIMULATE_STEPS,
        preconditions=("ledger drafted",),
    )
    steps = (
        create_dry_run_execution_step(
            execution_input,
            step_order=1,
            step_summary="would inspect authorization",
            side_effect_risk=DryRunSideEffectRisk.LOW,
        ),
        create_dry_run_execution_step(
            execution_input,
            step_order=2,
            step_summary="would describe tool call only",
            would_touch_target="tool-x",
            side_effect_risk=DryRunSideEffectRisk.HIGH,
        ),
    )
    result = create_dry_run_execution_result(execution_input, steps)
    boundary = create_execution_side_effect_boundary(action)
    trace = create_dry_run_execution_trace(
        action=action,
        execution_input=execution_input,
        steps=steps,
        result=result,
        boundary=boundary,
    )
    rollback = create_dry_run_rollback_plan(action, result_id=result.result_id)
    return action, execution_input, steps, result, boundary, trace, rollback


def test_importing_dry_run_action_execution_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert RUNTIME_V14Q_INVARIANT_FLAGS["human_approval_required_for_risky_actions"] is True
    assert RUNTIME_V14Q_INVARIANT_FLAGS["authorization_required_before_execution"] is True
    assert RUNTIME_V14Q_INVARIANT_FLAGS["ledger_required_before_execution"] is True
    assert invariant_flags_safe(RUNTIME_V14Q_INVARIANT_FLAGS)


def test_dry_run_action_is_deterministic_inactive_and_no_calls():
    first = create_dry_run_action(
        action_intent_id="intent-1",
        action_kind=DryRunActionKind.FILE_OPERATION,
        action_summary="simulate file write",
        source_reference_ids=("trace-1",),
    )
    second = create_dry_run_action(
        action_intent_id="intent-1",
        action_kind=DryRunActionKind.FILE_OPERATION,
        action_summary="simulate file write",
        source_reference_ids=("trace-1",),
    )

    assert first.dry_run_action_id == second.dry_run_action_id
    assert first.active is False
    assert first.real_execution_enabled is False
    assert first.tool_calls_enabled is False
    assert first.provider_calls_enabled is False
    assert first.side_effects_enabled is False
    assert validate_dry_run_action_inactive(first)


def test_dry_run_execution_input_is_simulation_only_and_tracks_missing_requirements():
    action = create_dry_run_action(
        action_intent_id="intent-2",
        action_kind=DryRunActionKind.NETWORK_OPERATION,
        action_summary="simulate network call",
    )
    execution_input = create_dry_run_execution_input(action)

    assert execution_input.simulation_only is True
    assert execution_input.real_execution_enabled is False
    assert execution_input.missing_requirements == ("authorization_decision", "ledger_entry")
    assert validate_dry_run_execution_input_simulation_only(execution_input)


def test_dry_run_steps_are_simulated_and_not_executed():
    _, execution_input, steps, _, _, _, _ = _dry_run_parts()
    duplicate = create_dry_run_execution_step(
        execution_input,
        step_order=1,
        step_summary="would inspect authorization",
        side_effect_risk=DryRunSideEffectRisk.LOW,
    )

    assert steps[0].step_id == duplicate.step_id
    assert all(step.simulated for step in steps)
    assert all(step.executed is False for step in steps)
    assert all(step.side_effects_created is False for step in steps)
    assert all(validate_dry_run_execution_step_simulated(step) for step in steps)


def test_dry_run_result_is_simulated_not_real():
    _, _, _, result, _, _, _ = _dry_run_parts()

    assert result.simulated_status == DryRunSimulatedStatus.SIMULATED_REQUIRES_HUMAN_REVIEW
    assert result.simulated is True
    assert result.real_result is False
    assert result.action_executed is False
    assert result.side_effects_created is False
    assert result.requires_human_review is True
    assert result.requires_ledger is True
    assert result.requires_authorization is True
    assert validate_dry_run_execution_result_simulated(result)


def test_side_effect_boundary_blocks_file_network_database_tool_provider_operations():
    _, _, _, _, boundary, _, _ = _dry_run_parts()

    assert boundary.file_mutation_enabled is False
    assert boundary.network_enabled is False
    assert boundary.database_mutation_enabled is False
    assert boundary.tool_calls_enabled is False
    assert boundary.provider_calls_enabled is False
    assert boundary.side_effects_enabled is False
    assert "filesystem" in boundary.external_systems_blocked
    assert validate_execution_side_effect_boundary_blocks_effects(boundary)


def test_trace_is_review_only_and_not_persisted_to_active_ledger():
    _, _, _, _, _, trace, _ = _dry_run_parts()

    assert trace.generated_for_review_only is True
    assert trace.applied is False
    assert trace.persisted_to_active_ledger is False
    assert validate_dry_run_execution_trace_review_only(trace)


def test_rollback_plan_does_not_execute_rollback():
    _, _, _, _, _, _, rollback = _dry_run_parts()

    assert rollback.rollback_required_for_real_execution is True
    assert rollback.rollback_executed is False
    assert rollback.side_effect_reversal_executed is False
    assert rollback.applied is False
    assert validate_dry_run_rollback_plan_inert(rollback)


def test_dry_run_report_entry_is_review_only():
    action, execution_input, steps, result, boundary, trace, rollback = _dry_run_parts()
    entry = create_dry_run_execution_report_entry(
        action=action,
        execution_input=execution_input,
        steps=steps,
        result=result,
        boundary=boundary,
        trace=trace,
        rollback_plan=rollback,
        unresolved_gaps=("manual UI missing",),
    )

    assert entry.generated_for_review_only is True
    assert entry.unresolved_gaps == ("manual UI missing",)
    assert validate_dry_run_execution_report_entry_review_only(entry)


def test_dry_run_report_data_states_no_real_execution_or_side_effects():
    data = build_dry_run_action_execution_report_data()

    assert data["final_recommendation"] == "PROCEED_MINIMAL_RUNTIME_UI_MESSAGE_CONSOLE"
    assert data["status"] == "dry_run_design_only_no_real_execution_no_side_effects"
    assert data["dry_run_action"]["real_execution_enabled"] is False
    assert data["dry_run_action"]["tool_calls_enabled"] is False
    assert data["dry_run_action"]["provider_calls_enabled"] is False
    assert data["execution_result"]["real_result"] is False
    assert data["execution_result"]["action_executed"] is False
    assert data["execution_result"]["side_effects_created"] is False
    assert data["execution_trace"]["persisted_to_active_ledger"] is False
    assert data["rollback_plan"]["rollback_executed"] is False
    assert "real action execution" in data["inactive_systems"]
    assert "active ledger persistence" in data["inactive_systems"]


def test_write_dry_run_action_execution_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_dry_run_action_execution_report as report_module

    md_path = tmp_path / "dry_run.md"
    json_path = tmp_path / "dry_run.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)

    data = write_dry_run_action_execution_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    md_text = md_path.read_text(encoding="utf-8")

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "dry-run-design-only" in md_text.lower() or "dry-run action execution design" in md_text.lower()
    assert "real execution" in md_text.lower()
    assert "side effects" in md_text.lower()
