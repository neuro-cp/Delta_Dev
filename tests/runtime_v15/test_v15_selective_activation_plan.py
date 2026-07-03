from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v15_selective_activation_plan import (
    RUNTIME_V15B_INVARIANT_FLAGS,
    SelectiveActivationTargetType,
    create_selective_activation_decision,
    create_selective_activation_plan,
    create_selective_activation_targets,
    validate_selective_decision_inert,
    validate_selective_plan_inert,
    validate_selective_target_closed,
)
from orchestration.runtime.v15_selective_activation_plan_report import (
    build_selective_activation_plan_report_data,
    write_selective_activation_plan_report,
)


def test_selective_activation_import_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    assert RUNTIME_V15B_INVARIANT_FLAGS["runtime_console_preview_selected"] is True
    assert all(value is False for key, value in RUNTIME_V15B_INVARIANT_FLAGS.items() if key != "runtime_console_preview_selected")


def test_runtime_console_message_preview_is_selected_but_all_targets_closed():
    targets = create_selective_activation_targets()
    selected = [target for target in targets if target.selected_for_first_trial]
    assert len(selected) == 1
    assert selected[0].target_type == SelectiveActivationTargetType.RUNTIME_CONSOLE_MESSAGE_PREVIEW
    assert all(validate_selective_target_closed(target) for target in targets)


def test_plan_is_manual_local_deterministic_and_inert():
    selected = next(target for target in create_selective_activation_targets() if target.selected_for_first_trial)
    plan = create_selective_activation_plan(selected)
    decision = create_selective_activation_decision(plan)
    assert validate_selective_plan_inert(plan)
    assert validate_selective_decision_inert(decision)
    assert "provider_calls" in plan.blocked_components
    assert "training" in plan.blocked_components


def test_report_data_states_activation_plan_only_no_activation():
    data = build_selective_activation_plan_report_data()
    assert data["final_recommendation"] == "PROCEED_SINGLE_GATE_DRY_RUN_TRIAL_DESIGN"
    assert data["activation_plan"]["activation_enabled"] is False
    assert data["decision"]["gate_opened"] is False
    assert data["decision"]["activation_enabled"] is False
    assert sum(1 for target in data["targets"] if target["selected_for_first_trial"]) == 1
    assert all(target["active"] is False and target["gate_open"] is False for target in data["targets"])


def test_write_selective_activation_plan_report(tmp_path, monkeypatch):
    from orchestration.runtime import v15_selective_activation_plan_report as report_module

    md_path = tmp_path / "selective.md"
    json_path = tmp_path / "selective.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)
    data = write_selective_activation_plan_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8").lower()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "activation-plan-only" in text
    assert "runtime_console_message_preview" in text
