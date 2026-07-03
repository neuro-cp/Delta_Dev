from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
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
    validate_tiny_training_approval_gate_unsatisfied,
    validate_tiny_training_artifact_plan_inert,
    validate_tiny_training_audit_record_review_only,
    validate_tiny_training_candidate_inert,
    validate_tiny_training_decision_inert,
    validate_tiny_training_evaluation_gate_inert,
    validate_tiny_training_report_entry_review_only,
    validate_tiny_training_rollback_requirement_inert,
    validate_tiny_training_run_plan_inert,
    validate_tiny_training_scope_offline_only,
)
from orchestration.runtime.v14_tiny_training_experiment_report import (
    build_tiny_training_experiment_report_data,
    write_tiny_training_experiment_report,
)


def _experiment_parts():
    candidate = create_tiny_training_experiment_candidate(
        experiment_summary="tiny reviewed experiment",
        purpose="future offline review only",
        source_dataset_candidate_id="dataset-candidate",
        source_training_candidate_ids=("training-candidate",),
        source_evaluation_case_set_ids=("case-set",),
        provenance_reference_ids=("report",),
    )
    scope = create_tiny_training_experiment_scope(
        candidate=candidate,
        allowed_dataset_scope="reviewed candidates only",
        allowed_model_scope="offline preview only",
        allowed_runtime_scope="comparison review only",
        max_example_count=4,
        max_training_steps=2,
    )
    approval_gate = create_tiny_training_approval_gate(
        candidate=candidate,
        required_approval_ids=("human",),
        required_safety_review_ids=("safety",),
        required_dataset_decision_ids=("dataset-decision",),
        required_evaluation_plan_ids=("eval-plan",),
    )
    run_plan = create_tiny_training_run_plan(
        candidate=candidate,
        scope=scope,
        approval_gate=approval_gate,
        training_method=TinyTrainingMethod.LORA_PREVIEW,
        dataset_reference_preview="dataset preview only",
        output_artifact_preview="artifact preview only",
        required_pre_eval_plan_ids=("pre",),
        required_post_eval_plan_ids=("post",),
    )
    artifact_plan = create_tiny_training_artifact_plan(
        run_plan=run_plan,
        artifact_type=TinyTrainingArtifactType.MODEL_ADAPTER_PREVIEW,
        artifact_reference_preview="adapter preview",
        baseline_reference="Model B",
    )
    evaluation_gate = create_tiny_training_evaluation_gate(
        candidate=candidate,
        required_metric_ids=("no-mutation",),
        minimum_safety_status="human_review_required",
        regression_blockers=("default-change",),
        pre_training_case_set_id="pre-cases",
        post_training_case_set_id="post-cases",
        baseline_target_id="model-b",
    )
    rollback_requirement = create_tiny_training_rollback_requirement(
        candidate=candidate,
        rollback_strategy="versioned rollback required",
        required_artifact_versioning="immutable refs",
        required_baseline_reference="Model B",
    )
    decision = create_tiny_training_experiment_decision(
        candidate=candidate,
        outcome=TinyTrainingExperimentOutcome.REQUIRES_HUMAN_REVIEW,
        rationale="not approved",
        invariant_status="all false",
    )
    audit = create_tiny_training_audit_record(
        candidate=candidate,
        source_reference_ids=("source",),
        audit_summary="review only",
        run_plan=run_plan,
        approval_gate=approval_gate,
        evaluation_gate=evaluation_gate,
        rollback_requirement=rollback_requirement,
        decision=decision,
    )
    report_entry = create_tiny_training_report_entry(
        candidate=candidate,
        scope_summary="offline only",
        approval_summary="unsatisfied",
        run_plan_summary="disabled",
        artifact_summary="not created",
        evaluation_summary="not run",
        rollback_summary="not executed",
        decision_summary="not applied",
        unresolved_gaps=("human review",),
        recommended_next_review_step="compare artifact against Model B design",
    )
    return (
        candidate,
        scope,
        approval_gate,
        run_plan,
        artifact_plan,
        evaluation_gate,
        rollback_requirement,
        decision,
        audit,
        report_entry,
    )


def test_importing_tiny_training_experiment_design_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert RUNTIME_V14T_INVARIANT_FLAGS["model_b_default_changed"] is False
    assert RUNTIME_V14T_INVARIANT_FLAGS["runtime_defaults_changed"] is False
    assert all(value is False for value in RUNTIME_V14T_INVARIANT_FLAGS.values())


def test_candidate_is_deterministic_inactive_not_approved_or_executed():
    candidate, *_ = _experiment_parts()
    duplicate = create_tiny_training_experiment_candidate(
        experiment_summary="tiny reviewed experiment",
        purpose="future offline review only",
        source_dataset_candidate_id="dataset-candidate",
        source_training_candidate_ids=("training-candidate",),
        source_evaluation_case_set_ids=("case-set",),
        provenance_reference_ids=("report",),
    )

    assert candidate.experiment_candidate_id == duplicate.experiment_candidate_id
    assert candidate.human_approval_required is True
    assert candidate.safety_review_required is True
    assert candidate.baseline_comparison_required is True
    assert candidate.rollback_required is True
    assert validate_tiny_training_candidate_inert(candidate)


def test_scope_is_offline_only_and_does_not_allow_live_runtime_or_default_change():
    _, scope, *_ = _experiment_parts()

    assert scope.offline_only is True
    assert scope.live_runtime_allowed is False
    assert scope.model_default_change_allowed is False
    assert scope.provider_calls_allowed is False
    assert validate_tiny_training_scope_offline_only(scope)


def test_approval_gate_is_unsatisfied_by_default():
    *_, report_entry = _experiment_parts()
    _, _, approval_gate, *_rest = _experiment_parts()

    assert approval_gate.human_approval_present is False
    assert approval_gate.dataset_export_approved is False
    assert approval_gate.safety_approved is False
    assert approval_gate.evaluation_approved is False
    assert approval_gate.gate_satisfied is False
    assert validate_tiny_training_approval_gate_unsatisfied(approval_gate)
    assert report_entry.generated_for_review_only is True


def test_run_plan_does_not_enable_training_finetuning_weight_update_job_or_export():
    *_, run_plan, artifact_plan, evaluation_gate, rollback_requirement, decision, audit, report_entry = _experiment_parts()

    assert run_plan.training_enabled is False
    assert run_plan.fine_tuning_enabled is False
    assert run_plan.weight_update_enabled is False
    assert run_plan.job_execution_enabled is False
    assert run_plan.dataset_export_enabled is False
    assert validate_tiny_training_run_plan_inert(run_plan)
    assert artifact_plan.artifact_created is False
    assert evaluation_gate.promotion_allowed is False
    assert rollback_requirement.rollback_executed is False
    assert decision.training_triggered is False
    assert audit.training_triggered is False
    assert report_entry.generated_for_review_only is True


def test_artifact_plan_does_not_create_promote_or_activate_artifact():
    *_, artifact_plan, evaluation_gate, rollback_requirement, decision, audit, report_entry = _experiment_parts()

    assert artifact_plan.artifact_created is False
    assert artifact_plan.promoted is False
    assert artifact_plan.active_runtime_artifact is False
    assert validate_tiny_training_artifact_plan_inert(artifact_plan)


def test_evaluation_gate_does_not_run_eval_or_allow_promotion():
    *_, evaluation_gate, rollback_requirement, decision, audit, report_entry = _experiment_parts()

    assert evaluation_gate.pre_eval_passed is False
    assert evaluation_gate.post_eval_passed is False
    assert evaluation_gate.promotion_allowed is False
    assert validate_tiny_training_evaluation_gate_inert(evaluation_gate)


def test_rollback_requirement_does_not_execute_rollback():
    *_, rollback_requirement, decision, audit, report_entry = _experiment_parts()

    assert rollback_requirement.rollback_test_required is True
    assert rollback_requirement.rollback_ready is False
    assert rollback_requirement.rollback_executed is False
    assert validate_tiny_training_rollback_requirement_inert(rollback_requirement)


def test_decision_is_not_applied_and_does_not_trigger_training_or_promotion():
    *_, decision, audit, report_entry = _experiment_parts()

    assert decision.outcome == TinyTrainingExperimentOutcome.REQUIRES_HUMAN_REVIEW
    assert decision.applied is False
    assert decision.training_triggered is False
    assert decision.artifact_created is False
    assert decision.promoted is False
    assert validate_tiny_training_decision_inert(decision)


def test_audit_and_report_entry_are_review_only_and_not_persisted():
    *_, audit, report_entry = _experiment_parts()

    assert audit.generated_for_review_only is True
    assert audit.persisted_to_active_training_registry is False
    assert audit.training_triggered is False
    assert audit.artifact_created is False
    assert audit.promoted is False
    assert validate_tiny_training_audit_record_review_only(audit)
    assert validate_tiny_training_report_entry_review_only(report_entry)


def test_report_data_states_tiny_training_design_only_no_training_or_artifact():
    data = build_tiny_training_experiment_report_data()

    assert data["final_recommendation"] == "PROCEED_TRAINED_ARTIFACT_COMPARISON_AGAINST_MODEL_B_DESIGN"
    assert data["status"] == "tiny-training-experiment-design-only_no-training_no-artifact_no-promotion"
    assert data["candidate"]["training_enabled"] is False
    assert data["candidate"]["approved"] is False
    assert data["run_plan"]["training_enabled"] is False
    assert data["run_plan"]["fine_tuning_enabled"] is False
    assert data["run_plan"]["weight_update_enabled"] is False
    assert data["run_plan"]["job_execution_enabled"] is False
    assert data["run_plan"]["dataset_export_enabled"] is False
    assert data["artifact_plan"]["artifact_created"] is False
    assert data["artifact_plan"]["promoted"] is False
    assert data["evaluation_gate"]["promotion_allowed"] is False
    assert data["decision"]["training_triggered"] is False
    assert data["decision"]["promoted"] is False
    assert "training" in data["inactive_systems"]
    assert "artifact creation" in data["inactive_systems"]
    assert all(value is False for value in data["invariant_flags"].values())


def test_write_tiny_training_experiment_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_tiny_training_experiment_report as report_module

    md_path = tmp_path / "tiny_training.md"
    json_path = tmp_path / "tiny_training.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)

    data = write_tiny_training_experiment_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "tiny controlled training experiment" in text.lower()
    assert "does not add training" in text.lower() or "does not train" in text.lower()
