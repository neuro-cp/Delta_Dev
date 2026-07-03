from __future__ import annotations

from orchestration.runtime.v16_canonical_memory_rollback_trial import (
    RollbackDecisionValue,
    build_rollback_approval_text,
    execute_canonical_memory_rollback_trial,
    is_canonical_trial_record_rolled_back,
    validate_rollback_trial_safe,
)
from orchestration.runtime.v16_canonical_memory_rollback_trial_report import write_rollback_trial_report


def test_dry_run_default_does_not_mutate(tmp_path):
    payload = execute_canonical_memory_rollback_trial("record-1", marker_path=tmp_path / "markers.jsonl")
    assert payload["decision"]["decision"] == RollbackDecisionValue.DRY_RUN_ONLY.value
    assert payload["decision"]["marker_written"] is False
    assert not (tmp_path / "markers.jsonl").exists()
    assert validate_rollback_trial_safe(payload)


def test_casual_rollback_rejected(tmp_path):
    payload = execute_canonical_memory_rollback_trial("record-1", "yeah roll it back", dry_run=False, marker_path=tmp_path / "markers.jsonl")
    assert payload["decision"]["decision"] == RollbackDecisionValue.REJECTED_APPROVAL_MISMATCH.value
    assert not (tmp_path / "markers.jsonl").exists()
    assert validate_rollback_trial_safe(payload)


def test_exact_rollback_approval_writes_marker_only(tmp_path):
    path = tmp_path / "markers.jsonl"
    payload = execute_canonical_memory_rollback_trial("record-1", build_rollback_approval_text("record-1"), dry_run=False, marker_path=path)
    assert payload["decision"]["decision"] == RollbackDecisionValue.MARKER_WRITTEN.value
    assert payload["decision"]["source_record_deleted"] is False
    assert path.exists()
    assert is_canonical_trial_record_rolled_back("record-1", path)
    assert validate_rollback_trial_safe(payload)


def test_report_generation():
    data = write_rollback_trial_report("record-1")
    assert data["rollback_safe"] is True
    assert data["final_recommendation"] == "PROCEED_LIMITED_GENERAL_RECALL_ROUTER_DESIGN"
