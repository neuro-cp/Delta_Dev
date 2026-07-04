from orchestration.runtime.rc1_adversarial_validation import run_adversarial_validation, write_adversarial_validation_reports


def test_adversarial_validation_runs_all_required_scenarios():
    report = run_adversarial_validation()
    assert report["scenario_count"] == 30
    assert report["passed_count"] == 30
    assert report["failed_count"] == 0


def test_adversarial_validation_preserves_safety_invariants():
    report = run_adversarial_validation()
    safety = report["safety"]
    assert safety["model_b_default"] == "unchanged"
    assert safety["hyb1"] == "dormant_env_gated"
    assert safety["training_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["memory_mutation_performed"] is False
    assert safety["knowledge_mutation_performed"] is False


def test_adversarial_validation_keeps_domain_gaps_bounded():
    report = run_adversarial_validation()
    assert "domain_specific_live_expertise_unavailable_without_provider_or_curated_fixture" in report["bounded_pathologies"]
    assert report["final_recommendation"] == "PROCEED_MANUAL_RC1_VALIDATION_NO_LIVE_CAPABILITIES"


def test_adversarial_validation_reports_are_generated():
    report = write_adversarial_validation_reports()
    assert report["runtime_maturity_estimate"] >= 97
    assert report["failed_count"] == 0
