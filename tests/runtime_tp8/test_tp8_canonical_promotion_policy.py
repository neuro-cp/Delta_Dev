from __future__ import annotations

from orchestration.runtime.tp8_canonical_promotion_policy import (
    answer_tp8_question,
    build_promotion_policy,
    classify_candidate,
    is_tp8_question,
    run_falsification_suite,
    run_tp8_policy_validation,
    validate_contradiction_and_uncertainty_gates,
    validate_multi_reviewer_policy,
    write_tp8_reports,
)


def test_tp8_policy_keeps_canonical_memory_disabled():
    policy = build_promotion_policy()
    assert policy["canonical_memory_enabled"] is False
    assert policy["reviewer_agreement_requirements"]["minimum_agreement"] == 1.0
    assert "unresolved contradictions block" in policy["contradiction_handling_requirements"]


def test_tp8_candidate_classification_blocks_unsafe_cases():
    assert classify_candidate({"candidate_id": "x", "source_references": (), "source_checksum": ""})["classification"] == "provenance_incomplete"
    assert classify_candidate({"candidate_id": "x", "source_references": ("s",), "source_checksum": "h", "contradictions": ("c",)})["classification"] == "contradiction_unresolved"
    assert classify_candidate({"candidate_id": "x", "source_references": ("s",), "source_checksum": "h", "confidence": 0.9, "uncertainty": "bounded"}, reviewer_agreement=0.5)["classification"] == "operator_disagreement"


def test_tp8_gates_reviewers_and_falsification():
    assert validate_contradiction_and_uncertainty_gates()["passed"] is True
    assert validate_multi_reviewer_policy()["disagreement_blocks_promotion"] is True
    assert run_falsification_suite()["unsafe_candidates_blocked"] is True


def test_tp8_policy_validation_safety_and_recommendation():
    payload = run_tp8_policy_validation()
    safety = payload["safety"]
    assert payload["final_recommendation"] == "READY_FOR_CONTROLLED_CANONICAL_PILOT_DESIGN"
    assert safety["canonical_memory_enabled"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["canonical_memory_mutation_performed"] is False
    assert safety["autonomous_promotion_performed"] is False
    assert safety["provider_call_performed"] is False


def test_tp8_reports_and_answer_route():
    payload = write_tp8_reports()
    answer = answer_tp8_question("Can DELTA promote knowledge yet?")
    assert payload["passed"] is True
    assert is_tp8_question("What blocks promotion?")
    assert answer["phase"] == "TP8 Canonical Promotion Policy Validation"
