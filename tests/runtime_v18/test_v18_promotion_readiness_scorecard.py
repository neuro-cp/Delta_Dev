from __future__ import annotations

from orchestration.runtime.v18_promotion_readiness_scorecard import PromotionReadinessDecisionValue, run_promotion_readiness_scorecard, validate_promotion_readiness_scorecard_safe
from orchestration.runtime.v18_promotion_readiness_scorecard_report import write_promotion_readiness_scorecard_report


def test_scorecard_does_not_promote():
    data = run_promotion_readiness_scorecard()
    assert data["audit_record"]["promotions_performed"] is False
    assert all(card["decision"]["promoted"] is False for card in data["scorecards"])
    assert validate_promotion_readiness_scorecard_safe(data)


def test_blockers_generated_for_missing_or_blocked_evidence():
    data = run_promotion_readiness_scorecard()
    blocked = [card for card in data["scorecards"] if card["blockers"]]
    assert blocked
    outcomes = {card["decision"]["outcome"] for card in blocked}
    assert PromotionReadinessDecisionValue.DESIGN_ONLY.value in outcomes or PromotionReadinessDecisionValue.BLOCKED_BY_INVARIANT.value in outcomes


def test_hyb1_not_promoted():
    data = run_promotion_readiness_scorecard()
    hyb1 = next(card for card in data["scorecards"] if card["target"]["name"] == "HYB1_default_activation")
    assert hyb1["decision"]["promoted"] is False
    assert hyb1["decision"]["outcome"] == PromotionReadinessDecisionValue.BLOCKED_BY_INVARIANT.value


def test_no_scheduler_provider_memory_training_or_model_change():
    data = run_promotion_readiness_scorecard()
    flags = data["invariant_flags"]
    assert flags["scheduler_activated"] is False
    assert flags["provider_default_changed"] is False
    assert flags["memory_mutation_performed"] is False
    assert flags["training_triggered"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_promotion_readiness_scorecard_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_V17_V18_SAFETY_CLOSURE_REPORT"
