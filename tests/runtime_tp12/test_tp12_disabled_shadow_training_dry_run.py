from __future__ import annotations

from orchestration.runtime.tp12_disabled_shadow_training_dry_run import (
    answer_tp12_question,
    execute_disabled_dry_run,
    falsify_pipeline,
    is_tp12_question,
    run_tp12_disabled_shadow_training_dry_run,
    validate_abort_paths,
    validate_artifact_prevention,
    validate_dataset_integrity,
    validate_governance,
    write_tp12_reports,
)


def test_tp12_dry_run_terminates_before_training():
    result = execute_disabled_dry_run()
    assert result["passed"] is True
    assert result["optimization_reached"] is False
    assert result["training_started"] is False
    assert result["terminated_before_training"] is True


def test_tp12_dataset_and_governance_validation_pass():
    assert validate_dataset_integrity()["passed"] is True
    governance = validate_governance()
    assert governance["passed"] is True
    assert "held_out_benchmark_registration" in governance["evaluation_hooks"]


def test_tp12_artifact_abort_and_falsification_guards():
    artifact = validate_artifact_prevention()
    aborts = validate_abort_paths()
    falsification = falsify_pipeline()
    assert artifact["passed"] is True
    assert artifact["artifact_created"] is False
    assert aborts["passed"] is True
    assert falsification["passed"] is True


def test_tp12_safety_and_recommendation():
    payload = run_tp12_disabled_shadow_training_dry_run()
    assert payload["passed"] is True
    assert payload["final_recommendation"] == "READY_FOR_RESEARCH_ONLY_SHADOW_TRAINING"
    assert payload["safety"]["training_started"] is False
    assert payload["safety"]["optimization_started"] is False
    assert payload["safety"]["checkpoint_created"] is False
    assert payload["safety"]["model_artifact_created"] is False
    assert payload["safety"]["provider_call_performed"] is False


def test_tp12_reports_and_answer_route():
    payload = write_tp12_reports()
    answer = answer_tp12_question("Was any artifact created during TP12?")
    assert payload["passed"] is True
    assert is_tp12_question("shadow training dry run")
    assert answer["phase"] == "TP12 Disabled Shadow Training Dry-Run Validation"
