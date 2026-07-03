from orchestration.runtime.v23_hyb1_shadow_trial_simulation import APPROVAL_TEXT, run_hyb1_shadow_simulation, validate_hyb1_shadow_simulation_safe
from orchestration.runtime.v23_hyb1_shadow_trial_simulation_report import write_hyb1_shadow_simulation_report


def test_disabled_by_default():
    payload = run_hyb1_shadow_simulation("question")
    assert payload["gate"]["simulation_permitted"] is False
    assert payload["decision"]["promotes_hyb1"] is False


def test_exact_opt_in_required():
    payload = run_hyb1_shadow_simulation("question", approval_text="go ahead", env={"DELTA_HYB1_SHADOW_TRIAL_ENABLED": "true", "DELTA_HYB1_SHADOW_TRIAL_ALLOW_EXECUTION": "true"})
    assert payload["gate"]["simulation_permitted"] is False


def test_env_and_approval_allow_comparison_only():
    payload = run_hyb1_shadow_simulation("question", approval_text=APPROVAL_TEXT, env={"DELTA_HYB1_SHADOW_TRIAL_ENABLED": "true", "DELTA_HYB1_SHADOW_TRIAL_ALLOW_EXECUTION": "true"})
    assert payload["gate"]["simulation_permitted"] is True
    assert payload["hyb1_candidate_output"]["comparison_only"] is True
    assert validate_hyb1_shadow_simulation_safe(payload)


def test_model_b_default_and_hyb1_promotion_blocked():
    payload = run_hyb1_shadow_simulation("question")
    assert payload["model_b_output"]["default_runtime"] is True
    assert payload["decision"]["changes_default"] is False


def test_report_generation():
    data = write_hyb1_shadow_simulation_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_LOCALHOST_WRITE_EXECUTION_BRIDGE"

