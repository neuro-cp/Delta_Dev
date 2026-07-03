from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_offline_evaluation import (
    RUNTIME_V14S_INVARIANT_FLAGS,
    EvaluationBlockerType,
    EvaluationCaseType,
    EvaluationMetricType,
    EvaluationMode,
    EvaluationSafetyStatus,
    EvaluationTargetType,
    create_evaluation_case,
    create_evaluation_case_set,
    create_evaluation_comparison_report,
    create_evaluation_harness_report_entry,
    create_evaluation_metric_spec,
    create_evaluation_promotion_blocker,
    create_evaluation_result_draft,
    create_evaluation_run_plan,
    create_evaluation_scorecard,
    create_evaluation_target,
    review_evaluation_safety,
    validate_evaluation_case_inert,
    validate_evaluation_case_set_inert,
    validate_evaluation_comparison_report_inert,
    validate_evaluation_harness_report_entry_review_only,
    validate_evaluation_metric_spec_report_only,
    validate_evaluation_promotion_blocker_unresolved,
    validate_evaluation_result_draft_review_only,
    validate_evaluation_run_plan_inert,
    validate_evaluation_safety_review_not_approval,
    validate_evaluation_scorecard_report_only,
    validate_evaluation_target_inert,
)
from orchestration.runtime.v14_offline_evaluation_report import (
    build_offline_evaluation_report_data,
    write_offline_evaluation_report,
)


def _evaluation_parts():
    case = create_evaluation_case(
        case_type=EvaluationCaseType.TRAINING_SENSITIVE_CASE,
        input_preview="Use this as training data.",
        expected_behavior_summary="must not train",
        safety_expectations=("training_enabled=false",),
        source_reference_ids=("case-source",),
        provenance_reference_ids=("trace-1",),
    )
    case_set = create_evaluation_case_set(
        cases=(case,),
        purpose="future safety evaluation review",
        scope="manual console cases",
    )
    baseline = create_evaluation_target(
        target_type=EvaluationTargetType.MODEL_B_BASELINE_REFERENCE,
        target_reference_id="model-b",
        target_summary="Model B default reference",
        baseline=True,
    )
    candidate = create_evaluation_target(
        target_type=EvaluationTargetType.RUNTIME_VARIANT_CANDIDATE,
        target_reference_id="candidate-x",
        target_summary="candidate only",
        candidate=True,
    )
    metric = create_evaluation_metric_spec(
        metric_name="no_training",
        metric_type=EvaluationMetricType.SAFETY_INVARIANT,
        description="training must remain disabled",
        safety_critical=True,
    )
    run_plan = create_evaluation_run_plan(
        case_set=case_set,
        targets=(baseline, candidate),
        metric_specs=(metric,),
        evaluation_mode=EvaluationMode.REVIEW_ONLY,
    )
    result = create_evaluation_result_draft(
        run_plan=run_plan,
        target=candidate,
        case=case,
        metric=metric,
        observed_summary="report-only draft result",
        rationale="not applied",
    )
    scorecard = create_evaluation_scorecard(
        run_plan=run_plan,
        target=candidate,
        results=(result,),
        aggregate_summary="not authoritative",
    )
    review = review_evaluation_safety(run_plan=run_plan, target=candidate, case_set=case_set)
    comparison = create_evaluation_comparison_report(
        baseline_target=baseline,
        candidate_targets=(candidate,),
        scorecards=(scorecard,),
        comparison_summary="no default change",
    )
    blocker = create_evaluation_promotion_blocker(
        target_id=candidate.target_id,
        blocker_type=EvaluationBlockerType.MISSING_HUMAN_REVIEW,
        rationale="human review missing",
        required_resolution="manual review",
    )
    report_entry = create_evaluation_harness_report_entry(
        run_plan=run_plan,
        case_set=case_set,
        targets=(baseline, candidate),
        metrics=(metric,),
        results=(result,),
        safety_review=review,
        comparison=comparison,
        blockers=(blocker,),
    )
    return case, case_set, baseline, candidate, metric, run_plan, result, scorecard, review, comparison, blocker, report_entry


def test_importing_offline_evaluation_design_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14S_INVARIANT_FLAGS.values())


def test_evaluation_case_is_deterministic_inert_and_not_training_example():
    first = create_evaluation_case(
        case_type=EvaluationCaseType.MANUAL_E2E_CASE,
        input_preview="Remember this.",
        expected_behavior_summary="no memory write",
    )
    second = create_evaluation_case(
        case_type=EvaluationCaseType.MANUAL_E2E_CASE,
        input_preview="Remember this.",
        expected_behavior_summary="no memory write",
    )

    assert first.case_id == second.case_id
    assert first.active is False
    assert first.training_example is False
    assert first.dataset_exported is False
    assert validate_evaluation_case_inert(first)


def test_evaluation_case_set_is_not_exported_or_used_for_training():
    case, case_set, *_ = _evaluation_parts()

    assert case.case_id in case_set.case_ids
    assert case_set.active is False
    assert case_set.used_for_training is False
    assert case_set.exported is False
    assert validate_evaluation_case_set_inert(case_set)


def test_evaluation_target_does_not_alter_model_b_default_or_promote():
    _, _, baseline, candidate, *_ = _evaluation_parts()

    assert baseline.baseline is True
    assert baseline.active_runtime_target is False
    assert baseline.promoted is False
    assert candidate.candidate is True
    assert candidate.promoted is False
    assert validate_evaluation_target_inert(baseline)
    assert validate_evaluation_target_inert(candidate)


def test_evaluation_run_plan_does_not_enable_runs_providers_training_or_promotion():
    *_, run_plan, result, scorecard, review, comparison, blocker, report_entry = _evaluation_parts()

    assert run_plan.evaluation_mode == EvaluationMode.REVIEW_ONLY
    assert run_plan.run_enabled is False
    assert run_plan.provider_calls_enabled is False
    assert run_plan.training_enabled is False
    assert run_plan.promotion_enabled is False
    assert validate_evaluation_run_plan_inert(run_plan)


def test_evaluation_metric_result_and_scorecard_are_report_only():
    _, _, _, _, metric, _, result, scorecard, *_ = _evaluation_parts()

    assert metric.authoritative is False
    assert result.generated_for_review_only is True
    assert result.authoritative is False
    assert result.applied is False
    assert scorecard.score_is_authoritative is False
    assert scorecard.promotion_recommended is False
    assert validate_evaluation_metric_spec_report_only(metric)
    assert validate_evaluation_result_draft_review_only(result)
    assert validate_evaluation_scorecard_report_only(scorecard)


def test_evaluation_safety_review_does_not_approve_training_or_promotion():
    *_, review, comparison, blocker, report_entry = _evaluation_parts()

    assert review.safety_status == EvaluationSafetyStatus.HUMAN_REVIEW_REQUIRED
    assert review.required_before_training is True
    assert review.required_before_promotion is True
    assert review.approved is False
    assert validate_evaluation_safety_review_not_approval(review)


def test_evaluation_comparison_does_not_change_defaults():
    *_, comparison, blocker, report_entry = _evaluation_parts()

    assert comparison.preferred_is_authoritative is False
    assert comparison.default_change_recommended is False
    assert comparison.applied is False
    assert validate_evaluation_comparison_report_inert(comparison)


def test_evaluation_promotion_blocker_is_unresolved_by_default():
    *_, blocker, report_entry = _evaluation_parts()

    assert blocker.blocker_type == EvaluationBlockerType.MISSING_HUMAN_REVIEW
    assert blocker.resolved is False
    assert validate_evaluation_promotion_blocker_unresolved(blocker)


def test_evaluation_harness_report_entry_is_review_only():
    *_, report_entry = _evaluation_parts()

    assert report_entry.generated_for_review_only is True
    assert validate_evaluation_harness_report_entry_review_only(report_entry)


def test_offline_evaluation_report_data_states_design_only_no_training_or_promotion():
    data = build_offline_evaluation_report_data()

    assert data["final_recommendation"] == "PROCEED_TINY_CONTROLLED_TRAINING_EXPERIMENT_DESIGN"
    assert data["status"] == "evaluation_harness_design_only_no_training_no_promotion"
    assert data["run_plan"]["run_enabled"] is False
    assert data["run_plan"]["provider_calls_enabled"] is False
    assert data["run_plan"]["training_enabled"] is False
    assert data["run_plan"]["promotion_enabled"] is False
    assert data["metric"]["authoritative"] is False
    assert data["scorecard"]["promotion_recommended"] is False
    assert data["comparison"]["default_change_recommended"] is False
    assert "training" in data["inactive_systems"]
    assert "model default changes" in data["inactive_systems"]


def test_write_offline_evaluation_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_offline_evaluation_report as report_module

    md_path = tmp_path / "offline_eval.md"
    json_path = tmp_path / "offline_eval.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)

    data = write_offline_evaluation_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "evaluation-harness-design-only" in text.lower() or "offline evaluation harness" in text.lower()
    assert "does not add training" in text.lower() or "does not run evaluation jobs" in text.lower()
