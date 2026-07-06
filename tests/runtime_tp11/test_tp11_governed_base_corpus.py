from __future__ import annotations

from orchestration.runtime.tp11_governed_base_corpus import (
    answer_tp11_question,
    build_governed_base_corpus,
    build_shadow_training_scaffold,
    is_tp11_question,
    review_contamination,
    review_data_governance,
    run_tp11_governed_base_corpus,
    write_tp11_reports,
)


def test_tp11_base_corpus_is_governed_and_nonempty():
    base = build_governed_base_corpus()
    assert base["included_count"] > 0
    assert base["training_performed"] is False
    assert "tp3_independent" in base["held_out_families_excluded"]
    assert all(item["provenance"] for item in base["items"])


def test_tp11_governance_and_contamination_pass():
    base = build_governed_base_corpus()
    governance = review_data_governance(base)
    contamination = review_contamination(base)
    assert governance["passed"] is True
    assert contamination["passed"] is True
    assert contamination["held_out_hash_overlap_count"] == 0


def test_tp11_shadow_training_scaffold_is_disabled():
    payload = run_tp11_governed_base_corpus()
    scaffold = build_shadow_training_scaffold(payload["base"], payload["manifest"])
    assert scaffold["enabled"] is False
    assert scaffold["training_performed"] is False
    assert scaffold["model_artifact_created"] is False


def test_tp11_safety_and_recommendation():
    payload = run_tp11_governed_base_corpus()
    assert payload["passed"] is True
    assert payload["final_recommendation"] == "READY_FOR_SHADOW_TRAINING_DRY_RUN"
    assert payload["safety"]["training_started"] is False
    assert payload["safety"]["fine_tuning_started"] is False
    assert payload["safety"]["weight_update_performed"] is False
    assert payload["safety"]["model_artifact_created"] is False
    assert payload["safety"]["provider_call_performed"] is False


def test_tp11_reports_and_answer_route():
    payload = write_tp11_reports()
    answer = answer_tp11_question("What is the governed base corpus?")
    assert payload["passed"] is True
    assert is_tp11_question("shadow training readiness")
    assert answer["phase"] == "TP11 Governed Base Corpus and Shadow Training Readiness"
