from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_artifact_comparison import (
    RUNTIME_V14U_INVARIANT_FLAGS,
    ArtifactComparisonCaseType,
    ArtifactComparisonDecisionOutcome,
    ArtifactComparisonMetricType,
    ArtifactComparisonMode,
    ArtifactComparisonTargetType,
    ArtifactRegressionType,
    ArtifactSafetyStatus,
    create_artifact_comparison_case,
    create_artifact_comparison_decision,
    create_artifact_comparison_metric,
    create_artifact_comparison_report_entry,
    create_artifact_comparison_result_draft,
    create_artifact_comparison_run_plan,
    create_artifact_comparison_scorecard,
    create_artifact_comparison_target,
    create_artifact_promotion_eligibility_review,
    create_artifact_regression_finding,
    create_artifact_safety_comparison_review,
    validate_artifact_comparison_case_inert,
    validate_artifact_comparison_decision_inert,
    validate_artifact_comparison_metric_report_only,
    validate_artifact_comparison_report_entry_review_only,
    validate_artifact_comparison_result_review_only,
    validate_artifact_comparison_run_plan_inert,
    validate_artifact_comparison_scorecard_report_only,
    validate_artifact_promotion_review_not_approval,
    validate_artifact_regression_blocks_until_resolved,
    validate_artifact_safety_review_not_approved,
    validate_model_b_target_is_baseline_reference,
    validate_upgraded_target_is_inactive_candidate,
)
from orchestration.runtime.v14_artifact_comparison_report import (
    build_artifact_comparison_report_data,
    write_artifact_comparison_report,
)


def _comparison_parts():
    model_b = create_artifact_comparison_target(
        target_name="Model B",
        target_type=ArtifactComparisonTargetType.MODEL_B_BASELINE_REFERENCE,
        target_reference_id="runtime-v13-model-b",
        target_summary="default reference",
        baseline=True,
        model_b_reference=True,
        active_runtime_target=True,
    )
    hyb1 = create_artifact_comparison_target(
        target_name="HYB1",
        target_type=ArtifactComparisonTargetType.UPGRADED_VARIANT_CANDIDATE,
        target_reference_id=HYB1_ENV_FLAG,
        target_summary="dormant candidate",
        candidate=True,
        upgraded_variant_reference=True,
    )
    case = create_artifact_comparison_case(
        case_type=ArtifactComparisonCaseType.REGRESSION_GUARD,
        input_preview="Stay grounded.",
        expected_behavior_summary="candidate must not regress against Model B",
        safety_expectations=("no default change",),
        metric_focus=("regression_guard",),
        source_reference_ids=("manual-case",),
    )
    metric = create_artifact_comparison_metric(
        metric_name="regression_guard",
        metric_type=ArtifactComparisonMetricType.REGRESSION_GUARD,
        description="candidate regression guard",
        safety_critical=True,
    )
    run_plan = create_artifact_comparison_run_plan(
        baseline_target=model_b,
        candidate_targets=(hyb1,),
        cases=(case,),
        metrics=(metric,),
        comparison_mode=ArtifactComparisonMode.REVIEW_ONLY,
    )
    result = create_artifact_comparison_result_draft(
        run_plan=run_plan,
        target=hyb1,
        case=case,
        metric=metric,
        observed_summary="not run",
        rationale="review only",
    )
    scorecard = create_artifact_comparison_scorecard(
        run_plan=run_plan,
        baseline_target=model_b,
        candidate_target=hyb1,
        result_ids=(result.result_id,),
        baseline_summary="baseline preserved",
        candidate_summary="candidate inactive",
        aggregate_comparison_summary="not authoritative",
    )
    regression = create_artifact_regression_finding(
        candidate_target=hyb1,
        baseline_target=model_b,
        regression_type=ArtifactRegressionType.UNKNOWN,
        severity="unknown",
        rationale="comparison required",
    )
    safety_review = create_artifact_safety_comparison_review(
        run_plan=run_plan,
        baseline_target=model_b,
        candidate_target=hyb1,
        safety_status=ArtifactSafetyStatus.HUMAN_REVIEW_REQUIRED,
        regression_ids=(regression.regression_id,),
    )
    eligibility = create_artifact_promotion_eligibility_review(
        candidate_target=hyb1,
        baseline_target=model_b,
        comparison_scorecard_id=scorecard.scorecard_id,
        safety_review_id=safety_review.safety_review_id,
    )
    decision = create_artifact_comparison_decision(
        run_plan=run_plan,
        candidate_target=hyb1,
        outcome=ArtifactComparisonDecisionOutcome.REQUIRES_MORE_EVAL,
        rationale="no promotion",
        invariant_status="all false",
    )
    report_entry = create_artifact_comparison_report_entry(
        run_plan=run_plan,
        baseline_target=model_b,
        candidate_target=hyb1,
        case_summary="one case",
        metric_summary="one metric",
        scorecard_summary="not authoritative",
        regression_summary="unresolved",
        safety_summary="not approved",
        eligibility_summary="not eligible",
        decision_summary="not applied",
        unresolved_gaps=("more eval",),
        recommended_next_review_step="promotion rollback decision design",
    )
    return model_b, hyb1, case, metric, run_plan, result, scorecard, regression, safety_review, eligibility, decision, report_entry


def test_importing_artifact_comparison_design_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14U_INVARIANT_FLAGS.values())


def test_model_b_target_is_baseline_reference_without_default_change():
    model_b, *_ = _comparison_parts()

    assert model_b.baseline is True
    assert model_b.candidate is False
    assert model_b.model_b_reference is True
    assert model_b.active_runtime_target is True
    assert model_b.default_change_allowed is False
    assert model_b.promoted is False
    assert validate_model_b_target_is_baseline_reference(model_b)


def test_hyb1_target_is_candidate_only_inactive_and_unpromoted():
    _, hyb1, *_ = _comparison_parts()

    assert hyb1.target_name == "HYB1"
    assert hyb1.target_reference_id == HYB1_ENV_FLAG
    assert hyb1.candidate is True
    assert hyb1.baseline is False
    assert hyb1.upgraded_variant_reference is True
    assert hyb1.active_runtime_target is False
    assert hyb1.promoted is False
    assert hyb1.default_change_allowed is False
    assert validate_upgraded_target_is_inactive_candidate(hyb1)


def test_comparison_case_is_not_training_or_exported():
    *_, case, metric, run_plan, result, scorecard, regression, safety_review, eligibility, decision, report_entry = _comparison_parts()

    assert case.training_example is False
    assert case.exported is False
    assert validate_artifact_comparison_case_inert(case)


def test_run_plan_requires_model_b_and_enables_no_calls_training_promotion_or_default_change():
    *_, run_plan, result, scorecard, regression, safety_review, eligibility, decision, report_entry = _comparison_parts()

    assert run_plan.baseline_required is True
    assert run_plan.model_b_default_preserved is True
    assert run_plan.run_enabled is False
    assert run_plan.provider_calls_enabled is False
    assert run_plan.training_enabled is False
    assert run_plan.promotion_enabled is False
    assert run_plan.default_change_enabled is False
    assert validate_artifact_comparison_run_plan_inert(run_plan)


def test_metric_result_and_scorecard_are_report_only():
    *_, metric, run_plan, result, scorecard, regression, safety_review, eligibility, decision, report_entry = _comparison_parts()

    assert metric.authoritative is False
    assert result.generated_for_review_only is True
    assert result.authoritative is False
    assert result.applied is False
    assert scorecard.score_is_authoritative is False
    assert scorecard.promotion_recommended is False
    assert scorecard.candidate_has_regressions is True
    assert validate_artifact_comparison_metric_report_only(metric)
    assert validate_artifact_comparison_result_review_only(result)
    assert validate_artifact_comparison_scorecard_report_only(scorecard)


def test_regression_safety_eligibility_and_decision_do_not_promote_or_change_default():
    *_, regression, safety_review, eligibility, decision, report_entry = _comparison_parts()

    assert regression.blocks_promotion is True
    assert regression.resolved is False
    assert safety_review.required_before_promotion is True
    assert safety_review.approved is False
    assert eligibility.promotion_approved is False
    assert eligibility.default_change_allowed is False
    assert decision.applied is False
    assert decision.promoted is False
    assert decision.default_changed is False
    assert decision.training_triggered is False
    assert validate_artifact_regression_blocks_until_resolved(regression)
    assert validate_artifact_safety_review_not_approved(safety_review)
    assert validate_artifact_promotion_review_not_approval(eligibility)
    assert validate_artifact_comparison_decision_inert(decision)


def test_report_entry_is_review_only():
    *_, report_entry = _comparison_parts()

    assert report_entry.generated_for_review_only is True
    assert validate_artifact_comparison_report_entry_review_only(report_entry)


def test_report_data_states_model_b_vs_hyb1_design_only_no_promotion_or_default_change():
    data = build_artifact_comparison_report_data()

    assert data["final_recommendation"] == "PROCEED_PROMOTION_ROLLBACK_DECISION_DESIGN"
    assert data["status"] == "model-b-vs-upgraded-variant-comparison-design-only_no-promotion_no-default-change"
    assert data["model_b_baseline_target_summary"]["target_name"] == "Model B"
    assert data["upgraded_variant_candidate_target_summary"]["target_name"] == "HYB1"
    assert data["upgraded_variant_candidate_target_summary"]["active_runtime_target"] is False
    assert data["upgraded_variant_candidate_target_summary"]["promoted"] is False
    assert data["run_plan"]["run_enabled"] is False
    assert data["run_plan"]["provider_calls_enabled"] is False
    assert data["run_plan"]["training_enabled"] is False
    assert data["run_plan"]["promotion_enabled"] is False
    assert data["run_plan"]["default_change_enabled"] is False
    assert data["scorecard"]["promotion_recommended"] is False
    assert data["eligibility"]["promotion_approved"] is False
    assert data["eligibility"]["default_change_allowed"] is False
    assert data["decision"]["default_changed"] is False
    assert all(value is False for value in data["invariant_flags"].values())


def test_write_artifact_comparison_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_artifact_comparison_report as report_module

    md_path = tmp_path / "artifact_comparison.md"
    json_path = tmp_path / "artifact_comparison.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)

    data = write_artifact_comparison_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "model b baseline" in text.lower()
    assert "hyb1" in text.lower()
    assert "does not run comparisons" in text.lower() or "comparison-design-only" in text.lower()
