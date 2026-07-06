from __future__ import annotations

from orchestration.runtime.tp13_research_shadow_training_protocol import (
    ARTIFACT_PATH,
    answer_tp13_question,
    build_research_protocol,
    is_tp13_question,
    perform_single_research_shadow_run,
    run_tp13_research_shadow_training_protocol,
    verify_artifact_containment,
    write_tp13_reports,
)


def test_tp13_protocol_has_null_hypothesis_and_thresholds():
    protocol = build_research_protocol()
    assert "Governed substrate evolution is sufficient" in protocol["null_hypothesis"]
    assert protocol["stopping_conditions"][0] == "exactly one run"
    assert "no retries" in protocol["stopping_conditions"]


def test_tp13_single_shadow_artifact_is_created_and_isolated():
    artifact = perform_single_research_shadow_run()
    containment = verify_artifact_containment(artifact)
    assert ARTIFACT_PATH.exists()
    assert artifact["non_deployed"] is True
    assert artifact["non_routable"] is True
    assert artifact["model_b_replaced"] is False
    assert containment["passed"] is True
    assert containment["checks"]["exactly_one_artifact"] is True


def test_tp13_final_recommendation_is_conservative():
    payload = run_tp13_research_shadow_training_protocol()
    assert payload["passed"] is True
    assert payload["final_recommendation"] == "CONTINUE_SUBSTRATE_EVOLUTION"
    assert payload["experiment_results"]["scientific_conclusion"] == "governance cost outweighs benefit"


def test_tp13_safety_preserves_baseline_and_no_routing():
    payload = run_tp13_research_shadow_training_protocol()
    safety = payload["safety"]
    assert safety["model_b_modified"] is False
    assert safety["baseline_replacement_performed"] is False
    assert safety["routing_to_shadow_artifact_enabled"] is False
    assert safety["provider_call_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["hyb1_promoted"] is False


def test_tp13_reports_and_answer_route():
    payload = write_tp13_reports()
    answer = answer_tp13_question("Did training improve reasoning?")
    assert payload["passed"] is True
    assert is_tp13_question("research-only shadow training")
    assert answer["phase"] == "TP13 Research-Only Shadow Training Protocol"
