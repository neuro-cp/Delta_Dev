from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_tiny_training_experiment import (
    RUNTIME_V14T_INVARIANT_FLAGS,
    TinyTrainingArtifactType,
    TinyTrainingExperimentOutcome,
    TinyTrainingMethod,
    create_tiny_training_approval_gate,
    create_tiny_training_artifact_plan,
    create_tiny_training_audit_record,
    create_tiny_training_evaluation_gate,
    create_tiny_training_experiment_candidate,
    create_tiny_training_experiment_decision,
    create_tiny_training_experiment_scope,
    create_tiny_training_report_entry,
    create_tiny_training_rollback_requirement,
    create_tiny_training_run_plan,
)


REPORT_MD = Path("reports/runtime_v14t_tiny_controlled_training_experiment_design.md")
REPORT_JSON = Path("reports/runtime_v14t_tiny_controlled_training_experiment_design.json")


def build_tiny_training_experiment_report_data() -> dict[str, object]:
    candidate = create_tiny_training_experiment_candidate(
        experiment_summary="future tiny offline experiment using reviewed runtime feedback candidates",
        purpose="define gating required before any tiny controlled training experiment could be considered",
        source_dataset_candidate_id="training-dataset-candidate-preview",
        source_training_candidate_ids=("learning-candidate-preview",),
        source_evaluation_case_set_ids=("runtime-v14s-case-set-preview",),
        provenance_reference_ids=("runtime-v14r-training-dataset-design", "runtime-v14s-offline-evaluation-design"),
    )
    scope = create_tiny_training_experiment_scope(
        candidate=candidate,
        allowed_dataset_scope="reviewed candidate examples only; no active export",
        allowed_model_scope="non-default offline artifact preview only",
        allowed_runtime_scope="offline comparison review only",
        max_example_count=12,
        max_training_steps=20,
    )
    approval_gate = create_tiny_training_approval_gate(
        candidate=candidate,
        required_approval_ids=("human-training-review",),
        required_safety_review_ids=("training-data-safety-review",),
        required_dataset_decision_ids=("training-export-decision",),
        required_evaluation_plan_ids=("pre-eval-plan", "post-eval-plan"),
    )
    run_plan = create_tiny_training_run_plan(
        candidate=candidate,
        scope=scope,
        approval_gate=approval_gate,
        training_method=TinyTrainingMethod.NO_TRAINING_REVIEW_ONLY,
        dataset_reference_preview="training-dataset-candidate-preview",
        output_artifact_preview="no artifact created; future artifact preview only",
        required_pre_eval_plan_ids=("pre-eval-plan",),
        required_post_eval_plan_ids=("post-eval-plan",),
    )
    artifact_plan = create_tiny_training_artifact_plan(
        run_plan=run_plan,
        artifact_type=TinyTrainingArtifactType.MODEL_ADAPTER_PREVIEW,
        artifact_reference_preview="future adapter preview placeholder",
        baseline_reference="Model B default baseline",
    )
    evaluation_gate = create_tiny_training_evaluation_gate(
        candidate=candidate,
        required_metric_ids=("no_mutation_guard", "grounding_regression_guard"),
        minimum_safety_status="human_review_required",
        regression_blockers=("unsupported_confident_answer", "default_change"),
        pre_training_case_set_id="runtime-v14s-case-set-preview",
        post_training_case_set_id="future-post-training-case-set-preview",
        baseline_target_id="runtime-v13-model-b",
    )
    rollback_requirement = create_tiny_training_rollback_requirement(
        candidate=candidate,
        rollback_strategy="versioned artifact rollback plan required before future execution",
        required_artifact_versioning="immutable baseline and candidate artifact references",
        required_baseline_reference="Model B default baseline",
    )
    decision = create_tiny_training_experiment_decision(
        candidate=candidate,
        outcome=TinyTrainingExperimentOutcome.REQUIRES_HUMAN_REVIEW,
        rationale="tiny training experiment remains design-only until approvals, dataset export review, offline evaluation, and rollback requirements are satisfied",
        invariant_status="all active training and mutation flags remain false",
    )
    audit = create_tiny_training_audit_record(
        candidate=candidate,
        source_reference_ids=("runtime-v14s-offline-evaluation-report", "runtime-v14r-training-dataset-report"),
        audit_summary="report-only tiny controlled training experiment design audit",
        run_plan=run_plan,
        approval_gate=approval_gate,
        evaluation_gate=evaluation_gate,
        rollback_requirement=rollback_requirement,
        decision=decision,
    )
    report_entry = create_tiny_training_report_entry(
        candidate=candidate,
        scope_summary="offline-only; no default or live runtime scope",
        approval_summary="unsatisfied approvals by default",
        run_plan_summary="no training/fine-tuning/weight update/job execution/dataset export",
        artifact_summary="artifact plan only; no artifact created or promoted",
        evaluation_summary="evaluation gate only; no evaluation run or promotion",
        rollback_summary="rollback requirement only; no rollback execution",
        decision_summary="requires human review; not applied",
        unresolved_gaps=(
            "human approval missing",
            "dataset export review missing",
            "offline evaluation review missing",
            "rollback verification missing",
        ),
        recommended_next_review_step="design trained artifact comparison against Model B",
    )

    return {
        "phase": "Runtime V1.4T",
        "title": "Tiny Controlled Training Experiment Design",
        "status": "tiny-training-experiment-design-only_no-training_no-artifact_no-promotion",
        "final_recommendation": "PROCEED_TRAINED_ARTIFACT_COMPARISON_AGAINST_MODEL_B_DESIGN",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v14_tiny_training_experiment.py",
            "orchestration/runtime/v14_tiny_training_experiment_report.py",
            "tests/runtime_v14/test_v14_tiny_training_experiment_design.py",
            "reports/runtime_v14t_tiny_controlled_training_experiment_design.md",
            "reports/runtime_v14t_tiny_controlled_training_experiment_design.json",
            "docs/runtime_v14t_tiny_controlled_training_experiment_prompt.txt",
        ],
        "design_summary": (
            "Inert tiny training experiment candidate, scope, approval gate, run plan, artifact plan, "
            "evaluation gate, rollback requirement, decision, audit, and report-entry shapes."
        ),
        "pipeline_summary": (
            "TinyTrainingExperimentCandidate -> TinyTrainingExperimentScope -> TinyTrainingExperimentApprovalGate -> "
            "TinyTrainingRunPlan -> TinyTrainingArtifactPlan -> TinyTrainingEvaluationGate -> "
            "TinyTrainingRollbackRequirement -> TinyTrainingExperimentDecision"
        ),
        "invariant_flags": dict(RUNTIME_V14T_INVARIANT_FLAGS),
        "candidate": candidate.as_dict(),
        "scope": scope.as_dict(),
        "approval_gate": approval_gate.as_dict(),
        "run_plan": run_plan.as_dict(),
        "artifact_plan": artifact_plan.as_dict(),
        "evaluation_gate": evaluation_gate.as_dict(),
        "rollback_requirement": rollback_requirement.as_dict(),
        "decision": decision.as_dict(),
        "audit": audit.as_dict(),
        "report_entry": report_entry.as_dict(),
        "safety_boundaries": [
            "tiny training experiment design is not training",
            "training run proposal is not training run",
            "artifact candidate is not promoted model",
            "rollback plan is not rollback execution",
            "evaluation gate is not promotion",
            "approval requirement is not approval",
            "tiny experiment is not default change",
            "offline plan is not live behavior",
        ],
        "inactive_systems": [
            "training",
            "fine-tuning",
            "model weight updates",
            "training job execution",
            "dataset export",
            "active dataset writes",
            "artifact creation",
            "artifact promotion",
            "offline evaluation runs",
            "provider calls",
            "specialist routing",
            "action execution",
            "tool calls",
            "canonical writes",
            "memory mutation",
            "runtime recall mutation",
            "autonomous/background learning",
            "schedulers/workers/queues",
            "runtime default changes",
        ],
        "test_status": "run py_compile and tests/runtime_v14 to verify",
    }


def write_tiny_training_experiment_report() -> dict[str, object]:
    data = build_tiny_training_experiment_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4T - Tiny Controlled Training Experiment Design",
        "",
        "## Summary",
        "",
        "Runtime V1.4T defines inert tiny controlled training experiment scaffolding. It does not train, fine-tune, update weights, export datasets, create artifacts, run jobs, call providers, promote artifacts, or change runtime behavior.",
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
            "## Unresolved Gaps",
            "",
        ]
    )
    report_entry = data["report_entry"]
    if isinstance(report_entry, dict):
        lines.extend(f"- {item}" for item in report_entry["unresolved_gaps"])
    lines.extend(
        [
            "",
            "## Test Status",
            "",
            str(data["test_status"]),
            "",
            "## Continuation Checkpoint",
            "",
            "Runtime V1.4T is tiny-training-experiment-design-only. It does not add training, fine-tuning, weight updates, training job execution, dataset export, active dataset writes, artifact creation/promotion, provider/tool calls, specialist routing, action execution, memory/canonical mutation, recall mutation, offline evaluation runs, schedulers, default changes, or runtime behavior changes.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_tiny_training_experiment_report()
