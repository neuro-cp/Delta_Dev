from __future__ import annotations

from orchestration.runtime.tp10_training_readiness_review import (
    answer_tp10_question,
    assess_governance_compatibility,
    compare_training_options,
    is_tp10_question,
    review_training_necessity,
    run_tp10_training_readiness_review,
    write_tp10_reports,
)


def test_tp10_training_not_needed_now():
    necessity = review_training_necessity()
    assert necessity["training_needed_now"] is False
    assert "continue governed substrate learning" in necessity["conclusion"]


def test_tp10_options_prefer_substrate_learning():
    options = compare_training_options()
    assert options["recommended_option"] == "continue_substrate_learning_no_training"
    assert any(item["option"] == "production_training" and item["status"] == "forbidden" for item in options["options"])


def test_tp10_governance_prefers_reversible_substrate():
    governance = assess_governance_compatibility()
    assert governance["substrate_learning"]["compatibility"] == "high"
    assert governance["weight_training"]["compatibility"] == "low_until_researched"


def test_tp10_safety_and_final_recommendation():
    payload = run_tp10_training_readiness_review()
    assert payload["passed"] is True
    assert payload["final_recommendation"] == "CONTINUE_SUBSTRATE_LEARNING_NO_TRAINING"
    assert payload["safety"]["training_started"] is False
    assert payload["safety"]["fine_tuning_started"] is False
    assert payload["safety"]["weight_update_performed"] is False
    assert payload["safety"]["provider_call_performed"] is False


def test_tp10_reports_and_answer_route():
    payload = write_tp10_reports()
    answer = answer_tp10_question("Should DELTA train now?")
    assert payload["passed"] is True
    assert is_tp10_question("training readiness")
    assert answer["phase"] == "TP10 Training Readiness Review"
