from __future__ import annotations

from orchestration.runtime.v19_console_review_workflow import export_console_review_action, validate_console_review_workflow_safe
from orchestration.runtime.v19_console_review_workflow_report import write_console_review_workflow_report
from orchestration.runtime.v19_local_delta_console import run_delta_console_command


def test_export_strings_exact():
    candidate_id = "memory-candidate-demo"
    approval = export_console_review_action("approve", candidate_id)["result"]["export_text"]
    rejection = export_console_review_action("reject", candidate_id)["result"]["export_text"]
    defer = export_console_review_action("defer", candidate_id)["result"]["export_text"]
    assert approval == "APPROVE_CANONICAL_MEMORY_WRITE\ncandidate_id=memory-candidate-demo\napproved_by=user\napproval_scope=single_memory_candidate_only"
    assert rejection == "REJECT_MEMORY_CANDIDATE\ncandidate_id=memory-candidate-demo\nrejected_by=user\nrejection_scope=single_memory_candidate_only"
    assert defer == "DEFER_MEMORY_CANDIDATE\ncandidate_id=memory-candidate-demo\ndeferred_by=user\ndefer_scope=single_memory_candidate_only"


def test_casual_approval_not_accepted_as_write():
    payload = export_console_review_action("yeah", "memory-candidate-demo")
    assert "APPROVE_CANONICAL_MEMORY_WRITE" not in payload["result"]["export_text"]
    assert validate_console_review_workflow_safe(payload)


def test_console_exports_do_not_write():
    payload = run_delta_console_command("export-approve", "memory-candidate-demo")
    assert payload["result"]["output"]["result"]["writes_memory"] is False


def test_no_provider_training_or_recall_mutation():
    payload = export_console_review_action("approve", "memory-candidate-demo")
    flags = payload["invariant_flags"]
    assert flags["provider_call_performed"] is False
    assert flags["training_triggered"] is False
    assert flags["recall_mutated"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_console_review_workflow_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_SESSION_TO_CANDIDATE_MEMORY_PROPOSAL_FLOW"
