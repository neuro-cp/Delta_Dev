from __future__ import annotations

from orchestration.runtime.v22_hyb1_opt_in_shadow_trial_design import (
    APPROVAL_TEXT,
    design_hyb1_shadow_trial,
    parse_hyb1_shadow_approval,
    validate_hyb1_shadow_design_safe,
)
from orchestration.runtime.v22_hyb1_opt_in_shadow_trial_design_report import write_hyb1_shadow_design_report


def test_disabled_by_default():
    payload = design_hyb1_shadow_trial()
    assert payload["opt_in_gate"]["opt_in_ready"] is False
    assert payload["decision"]["executes_hyb1_now"] is False


def test_exact_opt_in_required():
    assert parse_hyb1_shadow_approval("yes")["matches_required_shape"] is False
    assert parse_hyb1_shadow_approval(APPROVAL_TEXT)["matches_required_shape"] is True


def test_env_and_approval_can_make_future_gate_ready_without_execution():
    env = {"DELTA_HYB1_SHADOW_TRIAL_ENABLED": "true", "DELTA_HYB1_SHADOW_TRIAL_ALLOW_EXECUTION": "true"}
    payload = design_hyb1_shadow_trial(env, APPROVAL_TEXT)
    assert payload["opt_in_gate"]["opt_in_ready"] is True
    assert payload["decision"]["executes_hyb1_now"] is False


def test_model_b_default_and_hyb1_promotion_blocked():
    payload = design_hyb1_shadow_trial()
    flags = payload["invariant_flags"]
    assert flags["model_b_default_changed"] is False
    assert flags["hyb1_promoted"] is False
    assert validate_hyb1_shadow_design_safe(payload)


def test_report_generation():
    data = write_hyb1_shadow_design_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_V22_SAFETY_CLOSURE"
