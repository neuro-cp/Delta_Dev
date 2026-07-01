from __future__ import annotations

from orchestration.benchmarks import CognitiveBenchmarkComparator


def test_cognitive_benchmark_separates_engineering_cognitive_and_task_metrics():
    report = CognitiveBenchmarkComparator().compare(
        baseline_summary={
            "ticks_requested": 100,
            "ticks_completed": 100,
            "prediction_quality": {"accuracy": 0.5, "coverage": 0.4},
            "self_model": {"cognitive_health": {"contradiction_pressure": 0.3}},
        },
        candidate_summary={
            "ticks_requested": 10000,
            "ticks_completed": 10000,
            "prediction_quality": {"accuracy": 0.8, "coverage": 0.7},
            "self_model": {"cognitive_health": {"contradiction_pressure": 0.1}},
        },
        baseline_task_summary={"pass_rate": 0.4},
        candidate_task_summary={"pass_rate": 0.6},
        provider_summary={"baseline_api_calls": 10, "candidate_api_calls": 3},
    )

    assert report["summary"]["measured"] == 6
    assert report["summary"]["improved"] == 6
    assert report["engineering_correctness"][0].metric == "runtime_completion"
    assert [item.metric for item in report["cognitive_correctness"]] == [
        "prediction_accuracy",
        "prediction_coverage",
        "contradiction_pressure",
    ]
    assert [item.metric for item in report["task_performance"]] == [
        "task_pass_rate",
        "api_call_efficiency",
    ]


def test_cognitive_benchmark_reports_insufficient_data_without_guessing():
    report = CognitiveBenchmarkComparator().compare(
        baseline_summary={"ticks_requested": 1, "ticks_completed": 1},
        candidate_summary={"ticks_requested": 1, "ticks_completed": 1},
    )

    assert report["summary"]["measured"] == 1
    assert set(report["summary"]["insufficient_data"]) == {
        "prediction_accuracy",
        "prediction_coverage",
        "contradiction_pressure",
        "task_pass_rate",
        "api_call_efficiency",
    }
    assert all(
        item.status == "insufficient_data"
        for section in ("cognitive_correctness", "task_performance")
        for item in report[section]
    )


def test_cognitive_benchmark_flags_flat_or_regressed_metrics():
    report = CognitiveBenchmarkComparator().compare(
        baseline_summary={
            "ticks_requested": 100,
            "ticks_completed": 100,
            "prediction_quality": {"accuracy": 0.8, "coverage": 0.6},
            "self_model": {"cognitive_health": {"contradiction_pressure": 0.1}},
        },
        candidate_summary={
            "ticks_requested": 1000,
            "ticks_completed": 900,
            "prediction_quality": {"accuracy": 0.7, "coverage": 0.6},
            "self_model": {"cognitive_health": {"contradiction_pressure": 0.2}},
        },
    )

    assert report["engineering_correctness"][0].improved is False
    assert report["summary"]["regressed_or_flat"] == 4
    assert "non-improving" in report["summary"]["interpretation"]
