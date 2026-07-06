from __future__ import annotations

from orchestration.runtime.tp14_substrate_first_improvement import (
    analyze_tp13_differences,
    answer_tp14_question,
    extract_substrate_improvements,
    is_tp14_question,
    run_tp14_substrate_first_improvement,
    verify_governance,
    write_tp14_reports,
)


def test_tp14_difference_analysis_reads_tp13_findings():
    difference = analyze_tp13_differences()
    assert difference["model_b_unchanged"] is True
    assert difference["material_governance_regression"] is True
    assert any(item["category"] == "genuine_small_improvement" for item in difference["differences"])


def test_tp14_substrate_improvements_are_governed():
    improvements = extract_substrate_improvements(analyze_tp13_differences())
    assert improvements["all_governed"] is True
    assert improvements["live_mutation_performed"] is False
    assert len(improvements["improvements"]) >= 5


def test_tp14_governance_and_final_recommendation():
    payload = run_tp14_substrate_first_improvement()
    assert payload["passed"] is True
    assert payload["vs_training"]["substrate_matches_or_exceeds_shadow"] is True
    assert payload["final_recommendation"] == "TRAINING_REMAINS_UNJUSTIFIED"
    assert verify_governance(payload["improvements"])["passed"] is True


def test_tp14_safety_no_model_or_artifact_changes():
    payload = run_tp14_substrate_first_improvement()
    safety = payload["safety"]
    assert safety["model_b_modified"] is False
    assert safety["training_started"] is False
    assert safety["fine_tuning_started"] is False
    assert safety["weight_update_performed"] is False
    assert safety["new_shadow_artifact_created"] is False
    assert safety["provider_call_performed"] is False
    assert safety["canonical_write_performed"] is False


def test_tp14_reports_and_answer_route():
    payload = write_tp14_reports()
    answer = answer_tp14_question("Did DELTA improve without training?")
    assert payload["passed"] is True
    assert is_tp14_question("substrate-first")
    assert answer["phase"] == "TP14 Substrate-First Improvement From TP13 Findings"
