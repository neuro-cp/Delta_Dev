from __future__ import annotations

from orchestration.runtime.tp2_scientific_validation import (
    CORPUS_ORDER,
    answer_tp2_question,
    is_tp2_question,
    load_tp2_corpora,
    run_tp2_scientific_validation,
    write_tp2_reports,
)


def test_tp2_loads_independent_multi_corpus_benchmark():
    docs = load_tp2_corpora()
    payload = run_tp2_scientific_validation()

    assert set(CORPUS_ORDER) <= set(docs)
    assert len(docs) == 8
    assert all("tp2_independent" in doc.provenance for doc in docs.values())
    assert payload["multi_corpus_generalization"]["corpus_count"] == 8


def test_tp2_generalization_is_positive_but_not_perfect_score_chasing():
    payload = run_tp2_scientific_validation()
    summary = payload["multi_corpus_generalization"]

    assert summary["average_delta"] > 0
    assert summary["average_after_score"] < 1.0
    assert summary["all_corpora_improved"] is True
    assert summary["smallest_improvement"]["delta"] < summary["largest_improvement"]["delta"]


def test_tp2_blinded_evaluators_agree_without_unblinding():
    payload = run_tp2_scientific_validation()
    blinded = payload["blinded_evaluation"]

    assert blinded["anonymized"] is True
    assert blinded["before_after_hidden"] is True
    assert blinded["agreement_score"] >= 0.875
    assert "mean" in blinded["confidence_interval"]


def test_tp2_negative_controls_do_not_inflate():
    payload = run_tp2_scientific_validation()
    controls = payload["negative_controls"]

    assert controls["score_inflation_detected"] is False
    assert controls["all_refusals_preserved"] is True
    assert controls["all_controls_stable"] is True


def test_tp2_adversarial_validation_and_replay_remain_safe():
    payload = run_tp2_scientific_validation()

    assert payload["adversarial_validation"]["passed"] is True
    assert all(item["unsafe_consolidation_blocked"] for item in payload["adversarial_validation"]["cases"])
    assert payload["longitudinal_replay"]["rollback_stability"] == 1.0
    assert payload["longitudinal_replay"]["canonical_mutation"] is False


def test_tp2_training_science_review_recommends_independent_verification():
    payload = run_tp2_scientific_validation()
    science = payload["training_science_review"]

    assert science["reasoning_improved"] is True
    assert science["tp3_justified"] is True
    assert "external independent verification" in science["interpretation"]
    assert payload["final_recommendation"] == "PROCEED_TP3_INDEPENDENT_VERIFICATION_FREEZE"


def test_tp2_safety_invariants_preserved():
    payload = run_tp2_scientific_validation()
    safety = payload["safety"]

    assert safety["model_weight_training_performed"] is False
    assert safety["training_performed"] is False
    assert safety["fine_tuning_performed"] is False
    assert safety["model_update_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["memory_mutation_performed"] is False
    assert safety["knowledge_mutation_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["background_worker_started"] is False
    assert safety["action_execution_performed"] is False
    assert safety["hyb1_promoted"] is False
    assert safety["model_b_default"] == "unchanged"


def test_tp2_local_answer_route_and_reports_are_written():
    assert is_tp2_question("What did TP2 prove?")
    answer = answer_tp2_question("Did evaluators agree?")
    payload = write_tp2_reports()

    assert answer["phase"] == "TP2 Multi-Corpus Scientific Validation"
    assert answer["evaluator_agreement"] >= 0.875
    assert payload["readiness"]["tp2_status"] == "passed"
