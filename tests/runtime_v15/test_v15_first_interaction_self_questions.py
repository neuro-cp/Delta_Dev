from __future__ import annotations

import subprocess
import sys

from orchestration.runtime.v15_first_interaction import build_first_interaction_result, validate_first_interaction_result_safe
from scripts.ask_delta_self_test import SELF_QUESTIONS, run_self_questions, write_self_question_report


def test_self_question_pack_has_at_least_25_questions():
    assert len(SELF_QUESTIONS) >= 25


def test_self_questions_return_local_deterministic_safe_answers():
    for question in SELF_QUESTIONS:
        data = build_first_interaction_result(question)
        assert data["trace"]["trace_id"]
        assert data["trace"]["experience_preview_id"]
        assert data["trace"]["semantic_preview_id"]
        assert data["trace"]["persisted_to_memory"] is False
        assert data["trace"]["persisted_to_canonical_store"] is False
        assert data["safety_status"]["provider_calls_enabled"] is False
        assert data["safety_status"]["tool_calls_enabled"] is False
        assert data["safety_status"]["action_execution_enabled"] is False
        assert data["safety_status"]["training_enabled"] is False
        assert data["safety_status"]["canonical_write_enabled"] is False
        assert data["safety_status"]["runtime_recall_mutation_enabled"] is False
        assert data["safety_status"]["hyb1_default_activation_enabled"] is False
        assert data["invariant_flags"]["model_b_default_changed"] is False
        assert validate_first_interaction_result_safe(data)
        assert "cannot answer that from the local DELTA scaffold yet" not in data["response_preview"]["response_text"]


def test_self_question_runner_is_non_mutating_and_all_known_supported():
    data = run_self_questions()
    assert data["question_count"] >= 25
    assert data["unsupported_count"] == 0
    for result in data["results"]:
        assert result["persisted_to_memory"] is False
        assert result["persisted_to_canonical_store"] is False
        assert result["provider_calls_enabled"] is False
        assert result["tool_calls_enabled"] is False
        assert result["action_execution_enabled"] is False
        assert result["training_enabled"] is False
        assert result["canonical_write_enabled"] is False
        assert result["runtime_recall_mutation_enabled"] is False
        assert result["hyb1_default_activation_enabled"] is False
        assert result["model_b_default_changed"] is False


def test_write_self_question_report(tmp_path, monkeypatch):
    import scripts.ask_delta_self_test as module

    monkeypatch.setattr(module, "REPORT_MD", tmp_path / "self.md")
    monkeypatch.setattr(module, "REPORT_JSON", tmp_path / "self.json")
    data = write_self_question_report()
    assert module.REPORT_MD.exists()
    assert module.REPORT_JSON.exists()
    assert data["final_recommendation"] == "PROCEED_FEEDBACK_TO_MEMORY_CANDIDATE_PROPOSAL"


def test_ask_delta_self_test_script_runs():
    completed = subprocess.run(
        [sys.executable, "scripts/ask_delta_self_test.py"],
        check=True,
        text=True,
        capture_output=True,
    )
    output = completed.stdout.lower()
    assert "runtime v1.5f self-question test pack" in output
    assert "unsupported: 0" in output
