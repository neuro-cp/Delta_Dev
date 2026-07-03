from orchestration.runtime.v28_validation_hardening import (
    build_architecture_audit,
    build_documentation_consolidation,
    build_failure_injection,
    build_master_validation,
    build_observability_dashboard,
    build_pipeline_validation,
    build_stress_test,
    build_test_expansion,
    validate_report_safe,
)


def test_v28a_pipeline_validation_covers_complete_path_without_side_effects():
    data = build_pipeline_validation()

    assert validate_report_safe(data)
    assert data["pipeline_passed"] is True
    assert [stage["stage"] for stage in data["stages"]] == [
        "ask",
        "unknown_detection",
        "retrieval",
        "evidence",
        "provider_advisory",
        "evaluator",
        "candidate_memory",
        "approval_gate",
        "recall",
        "synthesis",
    ]


def test_v28b_failure_injection_stays_stable():
    data = build_failure_injection()

    assert validate_report_safe(data)
    assert data["all_stable"] is True
    assert {item["scenario"] for item in data["results"]} >= {"missing_memory", "provider_unavailable", "denied_approval"}
    assert all(not item["side_effects"] for item in data["results"])


def test_v28c_stress_test_is_fixture_only_and_bounded():
    data = build_stress_test(memory_count=25, recall_count=12, evaluation_count=8)

    assert validate_report_safe(data)
    assert data["fixture_sizes"]["memories"] == 25
    assert data["metrics"]["recall_queue_size"] == 12
    assert data["metrics"]["memory_ranking_stable"] is True


def test_v28d_observability_dashboard_changes_no_behavior():
    data = build_observability_dashboard()

    assert validate_report_safe(data)
    assert "pipeline_timing" in data["dashboard_sections"]
    assert data["active_behavior_changes"] == []


def test_v28e_architecture_audit_is_recommendations_only():
    data = build_architecture_audit(".")

    assert validate_report_safe(data)
    assert data["cleanup_performed"] is False
    assert data["cleanup_recommendations"]


def test_v28f_test_expansion_records_new_coverage():
    data = build_test_expansion()

    assert validate_report_safe(data)
    assert "approval" in data["coverage_focus"]
    assert data["new_test_cases"] >= 8


def test_v28g_documentation_consolidation_has_matrices():
    data = build_documentation_consolidation()

    assert "runtime_capability_matrix" in data
    assert "safety_matrix" in data
    assert data["safety_matrix"]["training_performed"] is False


def test_v28h_master_validation_recommends_v29_without_activation():
    data = build_master_validation()

    assert validate_report_safe(data)
    assert data["architecture_health"] == "stable_for_scaffolded_local_validation"
    assert data["recommended_v29_direction"] == "PROCEED_MANUAL_LOCAL_DEMO_AND_SELECTED_CLEANUP_REVIEW"
