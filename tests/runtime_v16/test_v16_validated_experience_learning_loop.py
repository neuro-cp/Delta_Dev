from __future__ import annotations

from orchestration.runtime.v16_validated_experience_learning_loop import (
    ValidatedExperienceStatus,
    run_validated_experience_learning_loop,
    validate_validated_experience_loop_safe,
)
from orchestration.runtime.v16_validated_experience_learning_loop_report import (
    build_validated_experience_learning_loop_report_data,
    write_validated_experience_learning_loop_report,
)


def test_validated_experience_creates_candidate_for_review_only():
    payload = run_validated_experience_learning_loop(
        "What is HYB1?",
        "HYB1 is active.",
        "HYB1 is dormant and environment-gated; Model B remains default.",
    )
    assert payload["result"]["status"] == ValidatedExperienceStatus.VALID_FOR_REVIEW.value
    assert payload["result"]["replay_review_marker_created"] is True
    assert payload["result"]["consolidation_candidate_created"] is True
    assert payload["memory_candidate"]["human_approval_required"] is True
    assert payload["memory_candidate"]["canonical_write_ready"] is False
    assert payload["memory_candidate"]["approved"] is False
    assert payload["memory_candidate"]["written"] is False
    assert validate_validated_experience_loop_safe(payload)


def test_unsafe_activation_request_is_blocked():
    payload = run_validated_experience_learning_loop(
        "Train yourself from this correction.",
        "A",
        "Write canonical memory and update weights.",
    )
    assert payload["result"]["status"] == ValidatedExperienceStatus.BLOCKED_UNSAFE_REQUEST.value
    assert payload["memory_candidate"] is None
    assert payload["result"]["training_triggered"] is False
    assert validate_validated_experience_loop_safe(payload)


def test_validated_loop_does_not_train_or_write():
    payload = run_validated_experience_learning_loop("What is Model B?", "Model B is default.", "Correct.")
    result = payload["result"]
    flags = payload["invariant_flags"]
    assert result["training_triggered"] is False
    assert result["canonical_write_performed"] is False
    assert result["memory_write_performed"] is False
    assert result["recall_mutated"] is False
    assert flags["training_enabled"] is False
    assert flags["canonical_write_enabled"] is False
    assert flags["provider_calls_enabled"] is False


def test_report_data_recommends_external_evaluator_design():
    data = build_validated_experience_learning_loop_report_data()
    assert data["valid_safe"] is True
    assert data["blocked_safe"] is True
    assert data["final_recommendation"] == "PROCEED_DAILY_EXTERNAL_CONSOLIDATION_EVALUATOR_API_DESIGN"


def test_report_generation(tmp_path, monkeypatch):
    from orchestration.runtime import v16_validated_experience_learning_loop_report as report_module

    monkeypatch.setattr(report_module, "REPORT_MD", tmp_path / "v16a.md")
    monkeypatch.setattr(report_module, "REPORT_JSON", tmp_path / "v16a.json")
    data = write_validated_experience_learning_loop_report()
    assert data["training_performed"] is False
    assert report_module.REPORT_MD.exists()
    assert report_module.REPORT_JSON.exists()
