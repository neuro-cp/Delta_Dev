from orchestration.runtime.rc1_runtime_artifact_registry import build_artifact_registry, write_artifact_registry_report


def test_artifact_registry_has_consumers_for_rc1_reports():
    registry = build_artifact_registry()
    assert registry["artifact_count"] >= 6
    assert registry["all_artifacts_have_consumers"] is True
    assert registry["consumerless_artifacts"] == []


def test_artifact_registry_is_read_only():
    registry = build_artifact_registry()
    assert registry["all_artifacts_read_only"] is True
    assert registry["mutating_artifacts"] == []


def test_artifact_registry_report_recommends_manual_scenario_validation():
    report = write_artifact_registry_report()
    assert report["final_recommendation"] == "PROCEED_RC1_MANUAL_SCENARIO_VALIDATION"
    assert report["estimated_runtime_maturity"] >= 95
