from orchestration.runtime.rc1_activation_readiness import (
    build_activation_matrix,
    build_activation_wave_plan,
    build_first_activation_candidate,
    write_activation_readiness_reports,
)


def test_activation_matrix_covers_required_capabilities():
    matrix = build_activation_matrix()
    names = {item["capability"] for item in matrix["capabilities"]}
    assert len(names) == 15
    assert "live document adapter" in names
    assert "sleep/replay consolidation" in names
    assert matrix["recommended_first_activation_candidate"] == "fixture-only corpus ingestion into noncanonical semantic records"


def test_activation_matrix_keeps_live_capabilities_disabled_or_gated():
    matrix = build_activation_matrix()
    states = {item["recommended_first_activation_state"] for item in matrix["capabilities"]}
    assert "live_allowed" not in states
    assert matrix["safety"]["provider_call_performed"] is False
    assert matrix["safety"]["knowledge_mutation_performed"] is False


def test_activation_wave_plan_starts_with_manual_validation():
    plan = build_activation_wave_plan()
    waves = plan["waves"]
    assert waves[0]["wave"] == 0
    assert waves[0]["name"] == "manual RC1 validation only"
    assert "provider-assisted evidence, gated" == waves[5]["name"]
    assert plan["final_recommendation"] == "PROCEED_WAVE_0_MANUAL_RC1_VALIDATION"


def test_first_activation_candidate_is_fixture_only_and_noncanonical():
    candidate = build_first_activation_candidate()
    assert candidate["do_not_activate_in_this_run"] is True
    assert "fixture-only corpus ingestion" in candidate["candidate"]
    assert "canonical_write_enabled=false" in candidate["safety_flags"]
    assert candidate["output_folder"].startswith(".tmp/")


def test_activation_readiness_reports_are_written():
    payload = write_activation_readiness_reports()
    assert payload["matrix"]["runtime_maturity_estimate"] == 97
    assert payload["waves"]["waves"][0]["wave"] == 0
    assert payload["first_activation_candidate"]["final_recommendation"] == "PROCEED_WAVE_0_MANUAL_RC1_VALIDATION_FIRST"
