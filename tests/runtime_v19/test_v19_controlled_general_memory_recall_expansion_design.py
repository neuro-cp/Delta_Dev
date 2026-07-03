from __future__ import annotations

from orchestration.runtime.v19_controlled_general_memory_recall_expansion import build_controlled_general_memory_recall_expansion_design, validate_general_memory_expansion_design_safe
from orchestration.runtime.v19_controlled_general_memory_recall_expansion_report import write_general_memory_expansion_report


def test_design_excludes_unapproved_and_rolled_back_records():
    data = build_controlled_general_memory_recall_expansion_design()
    excluded = data["source_policy"]["excluded_sources"]
    assert "unapproved candidates" in excluded
    assert "rolled-back records" in excluded
    assert validate_general_memory_expansion_design_safe(data)


def test_design_does_not_activate_memory_or_authoritative_recall():
    data = build_controlled_general_memory_recall_expansion_design()
    assert data["scope"]["activates_general_memory"] is False
    assert data["recall_policy"]["authoritative_recall_allowed"] is False


def test_no_provider_training_or_model_change():
    data = build_controlled_general_memory_recall_expansion_design()
    flags = data["invariant_flags"]
    assert flags["provider_call_performed"] is False
    assert flags["training_triggered"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_exact_approval_and_rollback_required():
    data = build_controlled_general_memory_recall_expansion_design()
    assert data["write_policy"]["exact_approval_required"] is True
    assert data["write_policy"]["rollback_required"] is True
    assert data["audit_plan"]["audit_required"] is True


def test_report_generation():
    data = write_general_memory_expansion_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_UX_FIRST_LOCAL_DELTA_CONSOLE"
