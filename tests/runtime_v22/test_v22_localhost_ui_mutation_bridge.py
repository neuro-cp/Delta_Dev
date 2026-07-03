from __future__ import annotations

from orchestration.runtime.v22_localhost_ui_mutation_bridge import (
    LocalhostUIEventKind,
    build_ui_mutation_event,
    parse_ui_mutation_event,
    run_ui_mutation_bridge,
    validate_ui_mutation_bridge_safe,
)
from orchestration.runtime.v22_localhost_ui_mutation_bridge_report import write_ui_mutation_bridge_report


def test_ui_approval_export_exact():
    text = build_ui_mutation_event("candidate-1", LocalhostUIEventKind.APPROVE)
    assert text == "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE\ncandidate_id=candidate-1\napproved_by=user\napproval_scope=single_memory_candidate_only\napproval_source=localhost_review_ui"
    assert parse_ui_mutation_event(text)["approval_valid"] is True


def test_reject_and_defer_exports_exact():
    assert parse_ui_mutation_event(build_ui_mutation_event("candidate-1", LocalhostUIEventKind.REJECT))["reject_valid"] is True
    assert parse_ui_mutation_event(build_ui_mutation_event("candidate-1", LocalhostUIEventKind.DEFER))["defer_valid"] is True


def test_casual_approval_rejected():
    assert parse_ui_mutation_event("yeah save it")["machine_readable"] is False


def test_bridge_dry_run_writes_nothing():
    payload = run_ui_mutation_bridge("candidate-1", LocalhostUIEventKind.APPROVE)
    assert payload["decision"]["export_written"] is False
    assert payload["decision"]["backend_memory_write_performed"] is False
    assert validate_ui_mutation_bridge_safe(payload)


def test_export_write_is_export_only(tmp_path):
    payload = run_ui_mutation_bridge("candidate-1", LocalhostUIEventKind.APPROVE, dry_run=False, export_dir=tmp_path)
    assert payload["decision"]["export_written"] is True
    assert payload["decision"]["backend_memory_write_performed"] is False
    assert (tmp_path / "candidate-1.approve.txt").exists()


def test_report_generation():
    data = write_ui_mutation_bridge_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_GENERAL_RECALL_EXPANSION"
