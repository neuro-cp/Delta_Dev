from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_runtime_console import build_runtime_console_preview
from orchestration.runtime.v14_training_dataset import (
    RUNTIME_V14R_INVARIANT_FLAGS,
    TrainingCandidateSourceType,
    TrainingDataApprovalType,
    TrainingExportFormat,
    create_training_candidate_source,
    create_training_data_approval_requirement,
    create_training_dataset_audit_record,
    create_training_dataset_candidate,
    create_training_dataset_report_entry,
    create_training_example_draft,
    create_training_export_plan,
    decide_training_export,
    review_training_data_safety,
)


REPORT_MD = Path("reports/runtime_v14r_training_dataset_candidate_export_design.md")
REPORT_JSON = Path("reports/runtime_v14r_training_dataset_candidate_export_design.json")


def build_training_dataset_report_data() -> dict[str, object]:
    preview = build_runtime_console_preview(
        "Use this as training data.",
        source_reference="training-dataset-design-demo",
    )
    source = create_training_candidate_source(
        source_type=TrainingCandidateSourceType.RUNTIME_CONSOLE_PREVIEW,
        source_reference_id=preview.preview_id,
        source_summary="manual console preview considered for future training review",
        provenance_reference_ids=(preview.trace_summary.trace_summary_id,),
        contains_user_message=True,
    )
    draft = create_training_example_draft(
        source=source,
        input_preview=preview.console_input.user_message,
        target_preview=preview.placeholder_response,
        instruction_preview="Review whether this trace is appropriate for future offline evaluation.",
        rationale="example draft only; not training data",
        safety_notes=("human approval required",),
        privacy_notes=("contains user-visible message",),
        lane_scope=tuple(preview.console_input.lane_scope),
    )
    candidate = create_training_dataset_candidate(
        drafts=(draft,),
        dataset_purpose="future offline evaluation review",
        dataset_scope="manual runtime console preview traces",
        evidence_summary="single review-only preview trace",
        exclusion_notes=("not exported", "not training-ready"),
    )
    safety_review = review_training_data_safety(
        candidate.dataset_candidate_id,
        contains_user_message=source.contains_user_message,
        provenance_reference_ids=source.provenance_reference_ids,
    )
    approval = create_training_data_approval_requirement(
        target_reference_id=candidate.dataset_candidate_id,
        approval_type=TrainingDataApprovalType.PRIVACY_REVIEW_REQUIRED,
        required_actor="human_reviewer",
        approval_reason="user-visible message cannot become training material without review",
    )
    decision = decide_training_export(
        dataset_candidate=candidate,
        draft=draft,
        safety_review=safety_review,
        approval_requirement=approval,
    )
    plan = create_training_export_plan(
        dataset_candidate=candidate,
        output_format=TrainingExportFormat.JSONL_PREVIEW,
        output_location_preview="reports/future_training_dataset_preview.jsonl",
        required_approval_ids=(approval.requirement_id,),
        required_review_ids=(safety_review.review_id,),
        export_steps=("review source provenance", "review privacy", "review safety", "do not export in V1.4R"),
    )
    audit = create_training_dataset_audit_record(
        drafts=(draft,),
        dataset_candidate=candidate,
        decision=decision,
        source_reference_ids=(source.source_id,),
        review_reference_ids=(safety_review.review_id,),
        approval_requirement_ids=(approval.requirement_id,),
        audit_summary="training dataset candidate/export design is review-only",
    )
    report_entry = create_training_dataset_report_entry(
        dataset_candidate=candidate,
        drafts=(draft,),
        safety_review=safety_review,
        approval_requirement=approval,
        decision=decision,
        audit_record=audit,
        unresolved_gaps=(
            "offline evaluation harness is not implemented",
            "training dataset export is not enabled",
            "human approval workflow is not implemented",
        ),
    )
    return {
        "phase": "Runtime V1.4R",
        "title": "Training Dataset Candidate / Export Design",
        "status": "dataset_design_only_no_export_no_training",
        "final_recommendation": "PROCEED_OFFLINE_EVALUATION_HARNESS_DESIGN",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v14_training_dataset.py",
            "orchestration/runtime/v14_training_dataset_report.py",
            "tests/runtime_v14/test_v14_training_dataset_design.py",
            "reports/runtime_v14r_training_dataset_candidate_export_design.md",
            "reports/runtime_v14r_training_dataset_candidate_export_design.json",
            "docs/runtime_v14r_training_dataset_candidate_export_prompt.txt",
        ],
        "design_summary": "Inert training candidate, draft, dataset candidate, safety review, approval requirement, export decision, export plan, audit record, and report entry shapes.",
        "pipeline_summary": (
            "RuntimeConsolePreview -> TrainingCandidateSource -> TrainingExampleDraft -> "
            "TrainingDatasetCandidate -> TrainingDataSafetyReview -> TrainingExportDecision -> TrainingExportPlan"
        ),
        "invariant_flags": dict(RUNTIME_V14R_INVARIANT_FLAGS),
        "source": source.as_dict(),
        "draft": draft.as_dict(),
        "dataset_candidate": candidate.as_dict(),
        "safety_review": safety_review.as_dict(),
        "approval_requirement": approval.as_dict(),
        "export_decision": decision.as_dict(),
        "export_plan": plan.as_dict(),
        "audit_record": audit.as_dict(),
        "report_entry": report_entry.as_dict(),
        "safety_boundaries": [
            "training candidate is not training data",
            "training example draft is not dataset export",
            "export decision is not export execution",
            "dataset plan is not fine-tune",
            "review eligibility is not approval",
            "human approval requirement is not approval",
            "user message is not automatic training example",
            "trace reuse is not model update",
        ],
        "inactive_systems": [
            "training",
            "fine-tuning",
            "model weight updates",
            "training dataset export",
            "active dataset writes",
            "automatic training from user messages",
            "background learning",
            "canonical writes",
            "memory mutation",
            "runtime recall mutation",
            "provider calls",
            "specialist routing",
            "action execution",
            "tool calls",
            "schedulers/background workers/timers/queues",
        ],
        "test_status": "run py_compile and tests/runtime_v14 to verify",
    }


def write_training_dataset_report() -> dict[str, object]:
    data = build_training_dataset_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4R - Training Dataset Candidate / Export Design",
        "",
        "## Summary",
        "",
        "Runtime V1.4R defines inert training dataset candidate and export review scaffolding. It does not train, fine-tune, update weights, export datasets, write active dataset files, or turn user messages into automatic training examples.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Pipeline Summary",
        "",
        str(data["pipeline_summary"]),
        "",
        "## Safety Boundaries",
        "",
    ]
    lines.extend(f"- {item}" for item in data["safety_boundaries"])
    lines.extend(["", "## Inactive Systems", ""])
    lines.extend(f"- {item}" for item in data["inactive_systems"])
    lines.extend(["", "## Invariant Flags", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in data["invariant_flags"].items())
    lines.extend(
        [
            "",
            "## Test Status",
            "",
            str(data["test_status"]),
            "",
            "## Continuation Checkpoint",
            "",
            "Runtime V1.4R is dataset-design-only. It does not add training, fine-tuning, weight updates, real dataset export, active dataset writes, provider/tool calls, specialist routing, action execution, memory/canonical mutation, recall mutation, background learning, schedulers, or runtime default changes.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_training_dataset_report()
