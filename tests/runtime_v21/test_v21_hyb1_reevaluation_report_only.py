from __future__ import annotations

from orchestration.runtime.v21_hyb1_reevaluation_report_only import reevaluate_hyb1_report_only, validate_hyb1_reevaluation_safe
from orchestration.runtime.v21_hyb1_reevaluation_report_only_report import write_hyb1_reevaluation_report


def test_hyb1_not_activated_or_promoted():
    payload = reevaluate_hyb1_report_only()
    flags = payload["invariant_flags"]
    assert flags["hyb1_default_activation_enabled"] is False
    assert flags["hyb1_promoted"] is False
    assert payload["recommendation"] == "keep_dormant"


def test_model_b_unchanged():
    payload = reevaluate_hyb1_report_only()
    assert payload["invariant_flags"]["model_b_default_changed"] is False


def test_scorecard_generated_with_blockers():
    payload = reevaluate_hyb1_report_only()
    assert payload["scorecard"]["blockers"]
    assert payload["scorecard"]["promotion_readiness_status"] == "report_only_no_change"


def test_no_mutation_flags():
    payload = reevaluate_hyb1_report_only()
    assert validate_hyb1_reevaluation_safe(payload)


def test_report_generation():
    data = write_hyb1_reevaluation_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_V21_SAFETY_CHECKPOINT_REPORT"
