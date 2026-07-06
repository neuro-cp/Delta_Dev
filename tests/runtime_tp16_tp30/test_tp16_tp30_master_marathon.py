from __future__ import annotations

from orchestration.runtime.tp16_tp30_master_marathon import (
    PHASES,
    SAFETY,
    build_phase_payload,
    run_all_report_only,
    write_reports,
)


def test_tp16_tp30_phase_range_is_complete():
    assert sorted(PHASES) == list(range(16, 31))


def test_every_phase_preserves_hard_safety_invariants():
    assert all(value is False for value in SAFETY.values())
    for phase in sorted(PHASES):
        payload = build_phase_payload(phase)
        assert payload["passed"] is True
        assert payload["safety"]["model_training_performed"] is False
        assert payload["safety"]["model_b_default_changed"] is False
        assert payload["safety"]["hyb1_promoted"] is False
        assert payload["safety"]["provider_call_performed"] is False
        assert payload["safety"]["baseline_routing_changed"] is False


def test_tp20_recommends_substrate_first_without_training():
    payload = build_phase_payload(20)
    assert payload["recommendation"] == "CONTINUE_SUBSTRATE_FIRST"
    assert payload["training_decision"]["training_performed"] is False
    assert payload["hard_stop_required"] is False


def test_tp30_final_review_defers_training_research():
    payload = build_phase_payload(30)
    assert payload["recommendation"] == "SUBSTRATE_EVOLUTION_REMAINS_PRIMARY_NEXT_PATH"
    assert payload["scientific_conclusion"]["training_research"].startswith("deferred")


def test_runner_writes_phase_report():
    payload = write_reports(16)
    assert payload["phase"] == "TP16"
    assert payload["recommendation"] == "PROCEED_TP17_OPERATIONAL_SUBSTRATE_PILOT"


def test_report_only_all_phases():
    payloads = run_all_report_only()
    assert len(payloads) == 15
    assert all(item["passed"] for item in payloads)

