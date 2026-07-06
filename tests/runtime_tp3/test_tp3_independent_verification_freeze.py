from __future__ import annotations

from orchestration.runtime.tp3_independent_verification_freeze import (
    EXPECTED_TP2,
    answer_tp3_question,
    build_freeze_manifest,
    build_independent_scorecard,
    is_tp3_question,
    load_tp3_benchmark_pack,
    replay_tp2_expected_values,
    run_falsification_tests,
    run_tp3_independent_verification,
    verify_freeze_package,
    write_tp3_reports,
)


def test_tp3_freeze_manifest_records_hashes_and_blocked_capabilities():
    manifest = build_freeze_manifest()

    assert manifest["runtime_phase"] == "TP3 independent verification freeze"
    assert len(manifest["corpus_hashes"]) == 8
    assert "model training" in manifest["blocked_capabilities"]
    assert "provider calls" in manifest["blocked_capabilities"]
    assert "canonical writes" in manifest["blocked_capabilities"]
    assert manifest["safety_invariants"]["provider_call_performed"] is False


def test_tp3_independent_benchmark_pack_is_separate_and_adversarial():
    docs = load_tp3_benchmark_pack()

    assert len(docs) == 8
    assert all(doc.document_id.startswith("tp3-") for doc in docs)
    assert all("tp2" not in doc.text.lower() for doc in docs)
    assert any(doc.contradiction_present for doc in docs)
    assert any(doc.missing_evidence_present for doc in docs)
    assert any(doc.provenance_trap_present for doc in docs)


def test_tp3_replays_frozen_tp2_expected_values():
    replay = replay_tp2_expected_values()

    assert replay["passed"] is True
    assert replay["observed"]["average_delta"] == EXPECTED_TP2["average_delta"]
    assert replay["observed"]["blinded_evaluator_agreement"] == EXPECTED_TP2["blinded_evaluator_agreement"]
    assert replay["observed"]["rollback_stability"] == EXPECTED_TP2["rollback_stability"]


def test_tp3_falsification_blocks_unsafe_interpretations():
    result = run_falsification_tests()

    assert result["passed"] is True
    assert result["confidence_inflation_detected"] is False
    assert result["all_unsafe_candidates_blocked"] is True
    assert result["unsupported_claims_refused"] is True
    assert result["rollback_stability"] == 1.0


def test_tp3_independent_scorecard_is_not_tp2_scorer_and_passes():
    scorecard = build_independent_scorecard()

    assert scorecard["implementation_note"] == "independent scoring shape; TP2 scorer is not reused"
    assert scorecard["metrics"]["governance_compliance"] == 1.0
    assert scorecard["metrics"]["rollback_integrity"] == 1.0
    assert scorecard["passed"] is True


def test_tp3_release_freeze_is_conservative_and_non_mutating():
    payload = run_tp3_independent_verification()
    safety = payload["safety"]

    assert payload["passed"] is True
    assert payload["final_recommendation"] in {
        "VERIFIED_READY_FOR_CONTROLLED_PERSISTENT_PILOT",
        "VERIFIED_READY_FOR_MORE_NONCANONICAL_TESTING",
    }
    assert safety["model_training_performed"] is False
    assert safety["fine_tuning_performed"] is False
    assert safety["weight_update_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["live_memory_mutation_performed"] is False
    assert safety["live_knowledge_mutation_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["action_execution_performed"] is False
    assert safety["hyb1_promoted"] is False
    assert safety["model_b_default_changed"] is False


def test_tp3_reports_and_verification_package_are_written():
    payload = write_tp3_reports()
    verification = verify_freeze_package()

    assert payload["release_freeze_review"]["manifest_complete"] is True
    assert verification["corpus_hashes_passed"] is True
    assert verification["report_hashes_passed"] is True
    assert verification["passed"] is True


def test_tp3_local_answer_route():
    assert is_tp3_question("Is DELTA frozen for verification?")
    answer = answer_tp3_question("What does TP3 verify?")

    assert answer["phase"] == "TP3 Independent Verification Freeze"
    assert "verifies" in answer["answer_text"]
    assert answer["safety"]["provider_call_performed"] is False
