from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.integrated_cognitive_runtime import (
    build_architecture_audit,
    build_integrated_cognitive_trace,
    build_readiness_review,
    evaluate_adversarial_cross_layer,
    evaluate_long_conversation,
    evaluate_operator_scenarios,
    measure_performance,
    write_integrated_runtime_reports,
)


ANCHOR = {
    "report_name": "RC45_FREEZE_READINESS_REVIEW.md",
    "answer_summary": "Status: READY_FOR_REAL_OPERATOR_PILOT_NOT_FREEZE; operator evidence remains required.",
}


def test_architecture_audit_covers_existing_layers_without_rc6():
    audit = build_architecture_audit()

    layer_names = {layer["layer"] for layer in audit["layers"]}
    assert "RC2 Conversation Runtime" in layer_names
    assert "Discourse Cognition Bridge" in layer_names
    assert "PC1 Pragmatic Cognition" in layer_names
    assert "RC3 Goal and Planning" in layer_names
    assert "RC4 Governed Action" in layer_names
    assert "RC5 Development" in layer_names
    assert audit["global_boundaries"]["rc6_created"] is False
    assert audit["global_boundaries"]["delta75_interaction_performed"] is False


def test_integrated_trace_exposes_complete_developer_overlay_chain():
    trace = build_integrated_cognitive_trace(
        "The diagnosis is useful, but the proposed fix is too broad. How should I record that?",
        ANCHOR,
        include_rc2_route_preview=False,
    )

    assert trace["developer_overlay_only"] is True
    assert "conversation_understanding" in trace
    assert "discourse_frame" in trace
    assert "pragmatic_frame" in trace
    assert "goal_interpretation" in trace
    assert "planning" in trace
    assert "governance" in trace
    assert "development_evaluation" in trace
    assert trace["cross_layer_consistency"]["passed"] is True
    assert trace["final_response_policy"]["response_type"] == "mixed_judgment_with_separate_dimensions"
    assert trace["safety"]["provider_calls_performed"] is False


def test_long_conversation_metrics_preserve_scope_and_governance():
    result = evaluate_long_conversation(20)

    assert result["turn_count"] == 20
    assert result["topic_continuity"] >= 0.9
    assert result["goal_continuity"] >= 0.9
    assert result["scope_preservation"] >= 0.9
    assert result["governance_consistency"] == 1.0


def test_operator_scenarios_and_adversarial_suite_pass():
    scenarios = evaluate_operator_scenarios()
    adversarial = evaluate_adversarial_cross_layer()

    assert scenarios["passed"] is True
    assert scenarios["score"] == 1.0
    assert adversarial["passed"] is True
    assert adversarial["score"] == 1.0


def test_performance_report_measures_without_optimizing():
    perf = measure_performance()

    assert perf["sample_count"] > 0
    assert perf["average_pragmatic_inference_latency_ms"] >= 0
    assert perf["average_planning_latency_ms"] >= 0
    assert perf["average_overall_response_latency_ms"] >= 0
    assert perf["trace_size_bytes_average"] > 0
    assert perf["optimization_performed"] is False


def test_readiness_review_recommends_operator_use_with_pilot_evidence():
    review = build_readiness_review()

    assert review["recommendation"] == "READY_FOR_EVERYDAY_OPERATOR_USE_WITH_CONTINUED_PILOT_EVIDENCE"
    assert review["weaknesses"] == []
    assert "More real low-risk operator sessions across ordinary, unscripted work." in review["remaining_operator_evidence"]
    assert review["safety"]["provider_calls_performed"] is False


def test_write_integrated_reports_creates_valid_json_and_markdown():
    reports = write_integrated_runtime_reports()
    paths = [
        Path("reports") / "INTEGRATED_RUNTIME_ARCHITECTURE.json",
        Path("reports") / "INTEGRATED_RUNTIME_ARCHITECTURE.md",
        Path("reports") / "INTEGRATED_RUNTIME_READINESS.json",
        Path("reports") / "INTEGRATED_RUNTIME_READINESS.md",
    ]

    for path in paths:
        assert path.exists()
    for path in paths:
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
    assert reports["readiness"]["recommendation"] == "READY_FOR_EVERYDAY_OPERATOR_USE_WITH_CONTINUED_PILOT_EVIDENCE"
