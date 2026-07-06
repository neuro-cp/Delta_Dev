from __future__ import annotations

from orchestration.runtime.tp6_controlled_operational_pilot import (
    answer_tp6_question,
    build_operational_scenarios,
    is_tp6_question,
    run_failure_exercises,
    run_tp6_operational_pilot,
    write_tp6_reports,
)


def test_tp6_scenarios_cover_approval_rejection_and_partial_review():
    scenarios = build_operational_scenarios()
    assert len(scenarios) == 4
    assert {scenario.decision for scenario in scenarios} >= {"approve", "reject", "defer"}
    assert any(scenario.expected_persisted for scenario in scenarios)
    assert any(not scenario.expected_persisted for scenario in scenarios)


def test_tp6_operational_pilot_transitions_and_metrics(tmp_path):
    payload = run_tp6_operational_pilot(store_dir=tmp_path, write=True)
    assert payload["passed"] is True
    assert payload["metrics"]["approval_rate"] == 0.5
    assert payload["metrics"]["rejection_rate"] == 0.5
    assert payload["metrics"]["deterministic_repeatability"] is True
    assert payload["replay"]["read_only"] is True
    assert payload["rollback"]["passed"] is True


def test_tp6_failure_exercises_do_not_persist_unsafe_candidates(tmp_path):
    failures = run_failure_exercises(store_dir=tmp_path)
    assert failures["passed"] is True
    assert failures["unsafe_candidates_persisted"] is False
    assert {case["case"] for case in failures["cases"]} >= {"missing_provenance", "invalid_approval", "conflicting_evidence"}


def test_tp6_governance_and_safety(tmp_path):
    payload = run_tp6_operational_pilot(store_dir=tmp_path, write=True)
    safety = payload["safety"]
    assert payload["governance_stress"]["passed"] is True
    assert payload["governance_stress"]["bypasses_detected"] is False
    assert safety["model_training_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["live_knowledge_mutation_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["hyb1_promoted"] is False


def test_tp6_reports_and_local_answer_route(tmp_path):
    payload = write_tp6_reports(store_dir=tmp_path)
    answer = answer_tp6_question("Has governance survived operational testing?")
    assert payload["final_recommendation"] == "READY_FOR_LONGITUDINAL_STABILITY_EVALUATION"
    assert is_tp6_question("Is the operational pilot complete?")
    assert answer["phase"] == "TP6 Controlled Operational Pilot"
