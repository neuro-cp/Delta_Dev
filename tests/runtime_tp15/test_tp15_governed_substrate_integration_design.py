from __future__ import annotations

from orchestration.runtime.tp15_governed_substrate_integration_design import (
    answer_tp15_question,
    design_governance_gates,
    is_tp15_question,
    map_integration,
    run_falsification,
    run_tp15_governed_substrate_integration_design,
    write_tp15_reports,
)


def test_tp15_maps_all_tp14_improvements_inactive():
    mapping = map_integration()
    assert mapping["passed"] is True
    assert mapping["active_integrations"] == 0
    assert len(mapping["mapped_improvements"]) == 6
    assert all(item["active"] is False for item in mapping["mapped_improvements"])


def test_tp15_governance_gates_block_bypass():
    mapping = map_integration()
    gates = design_governance_gates(mapping)
    assert gates["passed"] is True
    assert gates["all_bypass_blocked"] is True
    assert all(gate["active"] is False for gate in gates["gates"])


def test_tp15_falsification_blocks_unsafe_integrations():
    falsification = run_falsification(map_integration())
    assert falsification["passed"] is True
    assert falsification["all_blocked"] is True


def test_tp15_safety_and_recommendation():
    payload = run_tp15_governed_substrate_integration_design()
    assert payload["passed"] is True
    assert payload["final_recommendation"] == "READY_FOR_CONTROLLED_SUBSTRATE_INTEGRATION"
    assert payload["safety"]["substrate_integration_performed"] is False
    assert payload["safety"]["model_b_modified"] is False
    assert payload["safety"]["training_started"] is False
    assert payload["safety"]["canonical_write_performed"] is False
    assert payload["safety"]["provider_call_performed"] is False


def test_tp15_reports_and_answer_route():
    payload = write_tp15_reports()
    answer = answer_tp15_question("How are substrate improvements integrated?")
    assert payload["passed"] is True
    assert is_tp15_question("governed substrate integration")
    assert answer["phase"] == "TP15 Governed Substrate Integration Design"
