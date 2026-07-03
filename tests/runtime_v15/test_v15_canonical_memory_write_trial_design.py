from __future__ import annotations

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v15_canonical_memory_write_trial import (
    CanonicalMemoryWriteOutcome,
    build_canonical_memory_write_trial_design,
    sample_canonical_memory_write_trial_design,
    validate_canonical_memory_write_trial_safe,
)
from orchestration.runtime.v15_canonical_memory_write_trial_report import build_canonical_memory_write_trial_report_data, write_canonical_memory_write_trial_report


def test_write_candidate_is_inactive_and_deterministic():
    first = sample_canonical_memory_write_trial_design()
    second = sample_canonical_memory_write_trial_design()
    assert first == second
    assert first["write_candidate"]["write_enabled"] is False
    assert first["write_candidate"]["canonical_write_executed"] is False
    assert validate_canonical_memory_write_trial_safe(first)


def test_approval_gate_unsatisfied_by_default():
    data = sample_canonical_memory_write_trial_design()
    gate = data["approval_gate"]
    assert gate["explicit_approval_required"] is True
    assert gate["approval_present"] is False
    assert gate["satisfied"] is False


def test_no_canonical_write_memory_recall_training_or_rollback_occurs():
    data = sample_canonical_memory_write_trial_design()
    assert data["write_plan"]["write_enabled"] is False
    assert data["write_plan"]["canonical_write_executed"] is False
    assert data["write_plan"]["recall_activation_enabled"] is False
    assert data["write_plan"]["training_enabled"] is False
    assert data["rollback_reference"]["rollback_executed"] is False
    assert data["audit_record"]["canonical_write_executed"] is False
    assert data["audit_record"]["memory_mutated"] is False
    assert data["audit_record"]["recall_mutated"] is False
    assert data["audit_record"]["training_triggered"] is False


def test_decision_is_not_applied():
    data = sample_canonical_memory_write_trial_design()
    decision = data["decision"]
    assert decision["outcome"] == CanonicalMemoryWriteOutcome.BLOCKED_APPROVAL_ABSENT.value
    assert decision["applied"] is False
    assert decision["canonical_write_triggered"] is False
    assert decision["recall_triggered"] is False
    assert decision["training_triggered"] is False


def test_flags_preserve_model_b_hyb1_and_external_boundaries(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    flags = sample_canonical_memory_write_trial_design()["invariant_flags"]
    assert flags["hyb1_default_activation_enabled"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["provider_calls_enabled"] is False
    assert flags["tool_calls_enabled"] is False
    assert flags["action_execution_enabled"] is False
    assert flags["training_enabled"] is False
    assert flags["scheduler_enabled"] is False


def test_custom_candidate_still_design_only():
    data = build_canonical_memory_write_trial_design("candidate-x", "DELTA test memory candidate.", ("feedback-x",))
    assert data["write_candidate"]["memory_candidate_id"] == "candidate-x"
    assert data["write_candidate"]["proposed_memory_text"] == "DELTA test memory candidate."
    assert validate_canonical_memory_write_trial_safe(data)


def test_report_data_states_design_only_no_write_no_recall_no_training():
    data = build_canonical_memory_write_trial_report_data()
    assert data["design_safe"] is True
    assert data["status"] == "design_only_no_canonical_write_no_recall_no_training"
    assert data["final_recommendation"] == "PROCEED_EXPLICIT_USER_APPROVED_CANONICAL_MEMORY_WRITE_TRIAL_OR_RECALL_BRIDGE_LIMITED_TRIAL_DESIGN"


def test_write_report(tmp_path, monkeypatch):
    from orchestration.runtime import v15_canonical_memory_write_trial_report as report_module

    monkeypatch.setattr(report_module, "REPORT_MD", tmp_path / "write.md")
    monkeypatch.setattr(report_module, "REPORT_JSON", tmp_path / "write.json")
    data = write_canonical_memory_write_trial_report()
    text = report_module.REPORT_MD.read_text(encoding="utf-8")
    assert data["design_safe"] is True
    assert report_module.REPORT_JSON.exists()
    assert "canonical_write_executed" in text
