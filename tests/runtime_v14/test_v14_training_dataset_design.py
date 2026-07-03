from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_training_dataset import (
    RUNTIME_V14R_INVARIANT_FLAGS,
    TrainingCandidateSourceType,
    TrainingDataApprovalType,
    TrainingExportFormat,
    TrainingExportOutcome,
    TrainingSafetyStatus,
    create_training_candidate_source,
    create_training_data_approval_requirement,
    create_training_dataset_audit_record,
    create_training_dataset_candidate,
    create_training_dataset_report_entry,
    create_training_example_draft,
    create_training_export_plan,
    decide_training_export,
    review_training_data_safety,
    validate_training_candidate_source_inert,
    validate_training_data_approval_requirement_unsatisfied,
    validate_training_data_safety_review_not_approval,
    validate_training_dataset_audit_record_review_only,
    validate_training_dataset_candidate_inert,
    validate_training_dataset_report_entry_review_only,
    validate_training_example_draft_inert,
    validate_training_export_decision_inert,
    validate_training_export_plan_inert,
)
from orchestration.runtime.v14_training_dataset_report import (
    build_training_dataset_report_data,
    write_training_dataset_report,
)


def _training_parts():
    source = create_training_candidate_source(
        source_type=TrainingCandidateSourceType.MANUAL_E2E_CASE,
        source_reference_id="case-1",
        source_summary="manual e2e case",
        provenance_reference_ids=("trace-1",),
        contains_user_message=True,
    )
    draft = create_training_example_draft(
        source=source,
        input_preview="Use this as training data.",
        target_preview="Do not train from this automatically.",
        rationale="draft only",
        safety_notes=("requires review",),
        privacy_notes=("contains user message",),
    )
    candidate = create_training_dataset_candidate(
        drafts=(draft,),
        dataset_purpose="future offline eval review",
        dataset_scope="manual console previews",
        evidence_summary="review-only source",
    )
    review = review_training_data_safety(
        candidate.dataset_candidate_id,
        contains_user_message=source.contains_user_message,
        provenance_reference_ids=source.provenance_reference_ids,
    )
    approval = create_training_data_approval_requirement(
        target_reference_id=candidate.dataset_candidate_id,
        approval_type=TrainingDataApprovalType.HUMAN_REQUIRED,
        required_actor="human_reviewer",
        approval_reason="manual review required",
    )
    decision = decide_training_export(
        dataset_candidate=candidate,
        draft=draft,
        safety_review=review,
        approval_requirement=approval,
    )
    plan = create_training_export_plan(
        dataset_candidate=candidate,
        output_format=TrainingExportFormat.JSONL_PREVIEW,
        output_location_preview="reports/future.jsonl",
        required_approval_ids=(approval.requirement_id,),
        required_review_ids=(review.review_id,),
        export_steps=("review only",),
    )
    audit = create_training_dataset_audit_record(
        drafts=(draft,),
        dataset_candidate=candidate,
        decision=decision,
        source_reference_ids=(source.source_id,),
        review_reference_ids=(review.review_id,),
        approval_requirement_ids=(approval.requirement_id,),
        audit_summary="review-only audit",
    )
    return source, draft, candidate, review, approval, decision, plan, audit


def test_importing_training_dataset_design_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14R_INVARIANT_FLAGS.values())


def test_training_candidate_source_is_deterministic_inactive_and_not_training_data():
    first = create_training_candidate_source(
        source_type=TrainingCandidateSourceType.RUNTIME_CONSOLE_PREVIEW,
        source_reference_id="preview-1",
        source_summary="console preview",
        provenance_reference_ids=("trace-1",),
        contains_user_message=True,
    )
    second = create_training_candidate_source(
        source_type=TrainingCandidateSourceType.RUNTIME_CONSOLE_PREVIEW,
        source_reference_id="preview-1",
        source_summary="console preview",
        provenance_reference_ids=("trace-1",),
        contains_user_message=True,
    )

    assert first.source_id == second.source_id
    assert first.active is False
    assert first.training_enabled is False
    assert first.automatic_training_allowed is False
    assert first.contains_user_message is True
    assert validate_training_candidate_source_inert(first)


def test_training_example_draft_is_not_approved_training_ready_or_exported():
    source, draft, *_ = _training_parts()

    assert draft.source_id == source.source_id
    assert draft.active is False
    assert draft.approved is False
    assert draft.training_ready is False
    assert draft.exported is False
    assert validate_training_example_draft_inert(draft)


def test_training_dataset_candidate_is_inactive_not_approved_not_export_ready():
    _, draft, candidate, *_ = _training_parts()

    assert draft.draft_id in candidate.draft_ids
    assert candidate.active is False
    assert candidate.approved is False
    assert candidate.export_ready is False
    assert candidate.exported is False
    assert validate_training_dataset_candidate_inert(candidate)


def test_safety_review_does_not_approve_export_by_itself():
    _, _, _, review, *_ = _training_parts()

    assert review.privacy_status == TrainingSafetyStatus.PRIVACY_REVIEW_REQUIRED
    assert review.required_before_export is True
    assert review.approved is False
    assert validate_training_data_safety_review_not_approval(review)


def test_approval_requirement_is_unsatisfied_by_default():
    _, _, _, _, approval, *_ = _training_parts()

    assert approval.approval_type == TrainingDataApprovalType.HUMAN_REQUIRED
    assert approval.satisfied is False
    assert validate_training_data_approval_requirement_unsatisfied(approval)


def test_export_decision_is_not_applied_exported_or_training_triggered():
    _, _, _, _, _, decision, *_ = _training_parts()

    assert decision.outcome in {
        TrainingExportOutcome.REQUIRES_PRIVACY_REVIEW,
        TrainingExportOutcome.REQUIRES_HUMAN_REVIEW,
    }
    assert decision.applied is False
    assert decision.approved is False
    assert decision.exported is False
    assert decision.training_triggered is False
    assert validate_training_export_decision_inert(decision)


def test_training_export_plan_does_not_enable_export_write_or_training():
    _, _, candidate, review, approval, _, plan, _ = _training_parts()

    assert plan.dataset_candidate_id == candidate.dataset_candidate_id
    assert plan.output_format == TrainingExportFormat.JSONL_PREVIEW
    assert approval.requirement_id in plan.required_approval_ids
    assert review.review_id in plan.required_review_ids
    assert plan.export_enabled is False
    assert plan.dataset_write_enabled is False
    assert plan.training_enabled is False
    assert plan.fine_tuning_enabled is False
    assert plan.weight_update_enabled is False
    assert validate_training_export_plan_inert(plan)


def test_training_audit_record_is_review_only_not_persisted_or_exported():
    *_, audit = _training_parts()

    assert audit.generated_for_review_only is True
    assert audit.persisted_to_active_dataset is False
    assert audit.exported is False
    assert audit.training_triggered is False
    assert validate_training_dataset_audit_record_review_only(audit)


def test_training_dataset_report_entry_is_review_only():
    _, draft, candidate, review, approval, decision, _, audit = _training_parts()
    report_entry = create_training_dataset_report_entry(
        dataset_candidate=candidate,
        drafts=(draft,),
        safety_review=review,
        approval_requirement=approval,
        decision=decision,
        audit_record=audit,
        unresolved_gaps=("offline harness missing",),
    )

    assert report_entry.generated_for_review_only is True
    assert report_entry.unresolved_gaps == ("offline harness missing",)
    assert validate_training_dataset_report_entry_review_only(report_entry)


def test_training_dataset_report_data_states_no_export_or_training():
    data = build_training_dataset_report_data()

    assert data["final_recommendation"] == "PROCEED_OFFLINE_EVALUATION_HARNESS_DESIGN"
    assert data["status"] == "dataset_design_only_no_export_no_training"
    assert data["source"]["training_enabled"] is False
    assert data["source"]["automatic_training_allowed"] is False
    assert data["draft"]["training_ready"] is False
    assert data["dataset_candidate"]["export_ready"] is False
    assert data["export_plan"]["export_enabled"] is False
    assert data["export_plan"]["dataset_write_enabled"] is False
    assert data["export_plan"]["training_enabled"] is False
    assert data["audit_record"]["persisted_to_active_dataset"] is False
    assert "training dataset export" in data["inactive_systems"]


def test_write_training_dataset_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_training_dataset_report as report_module

    md_path = tmp_path / "training_dataset.md"
    json_path = tmp_path / "training_dataset.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)

    data = write_training_dataset_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "dataset-design-only" in text.lower() or "training dataset candidate" in text.lower()
    assert "no export" in text.lower() or "does not add training" in text.lower()
