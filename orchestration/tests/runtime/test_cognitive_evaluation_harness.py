from __future__ import annotations

import json

from orchestration.evaluation import CognitiveEvaluationCase, CognitiveEvaluationHarness


def test_cognitive_evaluation_harness_runs_isolated_cases(tmp_path):
    cases = [
        CognitiveEvaluationCase(
            case_id="math-1",
            category="reasoning",
            prompt="What is 2 + 4?",
            expected_route="deterministic_solver",
            expected_success=True,
        ),
        CognitiveEvaluationCase(
            case_id="unknown-1",
            category="reflection",
            prompt="Compare memory and attention",
            expected_success=False,
        ),
    ]

    results = CognitiveEvaluationHarness(store_root=tmp_path).run_cases(cases)
    summary = CognitiveEvaluationHarness.summarize(results)

    assert len(results) == 2
    assert results[0].passed is True
    assert results[0].memory_count == 2
    assert results[0].relationship_count == 1
    assert results[0].learning_count == 1
    assert summary["total"] == 2
    assert "reasoning" in summary["categories"]


def test_cognitive_evaluation_harness_writes_summary(tmp_path):
    summary_path = tmp_path / "summary.json"
    cases = [
        CognitiveEvaluationCase(
            case_id="math-1",
            category="reasoning",
            prompt="What is 1 + 1?",
            expected_route="deterministic_solver",
            expected_success=True,
        )
    ]

    CognitiveEvaluationHarness(store_root=tmp_path).run_cases(
        cases,
        summary_path=summary_path,
    )
    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["summary"]["total"] == 1
    assert payload["summary"]["passed"] == 1
    assert payload["results"][0]["case_id"] == "math-1"
