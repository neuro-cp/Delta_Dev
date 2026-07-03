from __future__ import annotations

import subprocess
import sys

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v15_feedback_memory_candidate import (
    FeedbackSignalType,
    MemoryCandidateOutcome,
    build_feedback_memory_candidate_case,
    sample_feedback_memory_candidate_cases,
    validate_feedback_memory_candidate_safe,
)
from orchestration.runtime.v15_feedback_memory_candidate_report import build_feedback_memory_candidate_report_data, write_feedback_memory_candidate_report


def test_confirmation_creates_candidate_pressure_only():
    case = build_feedback_memory_candidate_case(
        "What is HYB1?",
        "HYB1 is dormant/env-gated and Model B remains default.",
        "Yeah, that is right. HYB1 reduced reasoning drift in the V1.4U snapshot.",
    )
    assert case["feedback_signal"]["signal_type"] == FeedbackSignalType.CONFIRMATION.value
    assert case["decision"]["outcome"] == MemoryCandidateOutcome.ELIGIBLE_FOR_FUTURE_HUMAN_APPROVED_WRITE_TRIAL.value
    assert validate_feedback_memory_candidate_safe(case)


def test_correction_creates_candidate_pressure_only():
    case = build_feedback_memory_candidate_case(
        "What is HYB1?",
        "HYB1 is active.",
        "No, HYB1 is not active. It is dormant and env-gated.",
    )
    assert case["feedback_signal"]["signal_type"] == FeedbackSignalType.CORRECTION.value
    assert case["memory_candidate"]["human_approval_required"] is True
    assert case["memory_candidate"]["written"] is False
    assert validate_feedback_memory_candidate_safe(case)


def test_sarcasm_or_ambiguity_is_not_promoted():
    case = build_feedback_memory_candidate_case(
        "What is HYB1?",
        "HYB1 is dormant/env-gated and Model B remains default.",
        "Yeah sure, whatever.",
    )
    assert case["feedback_signal"]["signal_type"] == FeedbackSignalType.SARCASM_POSSIBLE.value
    assert case["decision"]["outcome"] == MemoryCandidateOutcome.REQUIRES_HUMAN_REVIEW.value
    assert case["memory_candidate"]["canonical_write_ready"] is False
    assert validate_feedback_memory_candidate_safe(case)


def test_sample_cases_are_deterministic_and_safe():
    first = sample_feedback_memory_candidate_cases()
    second = sample_feedback_memory_candidate_cases()
    assert first == second
    assert all(validate_feedback_memory_candidate_safe(case) for case in first)


def test_hyb1_and_model_b_defaults_preserved(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    case = sample_feedback_memory_candidate_cases()[0]
    flags = case["invariant_flags"]
    assert flags["hyb1_default_activation_enabled"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["provider_calls_enabled"] is False
    assert flags["tool_calls_enabled"] is False
    assert flags["action_execution_enabled"] is False
    assert flags["memory_mutation_enabled"] is False
    assert flags["canonical_write_enabled"] is False
    assert flags["runtime_recall_mutation_enabled"] is False
    assert flags["training_enabled"] is False
    assert flags["scheduler_enabled"] is False


def test_report_generation(tmp_path, monkeypatch):
    from orchestration.runtime import v15_feedback_memory_candidate_report as report_module

    monkeypatch.setattr(report_module, "REPORT_MD", tmp_path / "feedback.md")
    monkeypatch.setattr(report_module, "REPORT_JSON", tmp_path / "feedback.json")
    data = write_feedback_memory_candidate_report()
    assert data["all_cases_safe"] is True
    assert data["final_recommendation"] == "PROCEED_HUMAN_APPROVED_CANONICAL_MEMORY_WRITE_TRIAL_DESIGN"
    assert report_module.REPORT_MD.exists()
    assert report_module.REPORT_JSON.exists()


def test_build_report_data_has_required_cases():
    data = build_feedback_memory_candidate_report_data()
    signals = {case["feedback_signal"]["signal_type"] for case in data["cases"]}
    assert {FeedbackSignalType.CONFIRMATION.value, FeedbackSignalType.CORRECTION.value, FeedbackSignalType.SARCASM_POSSIBLE.value} <= signals


def test_ask_delta_feedback_script_outputs_review_only_candidate():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/ask_delta_feedback.py",
            "--question",
            "What is HYB1?",
            "--answer",
            "HYB1 is active.",
            "--feedback",
            "No, HYB1 is not active. It is dormant and env-gated.",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    output = completed.stdout.lower()
    assert "correction" in output
    assert '"written": false' in output
    assert '"canonical_write_triggered": false' in output
    assert '"training_triggered": false' in output
