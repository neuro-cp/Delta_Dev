from orchestration.runtime.rc1_activation_readiness import SAFETY_FLAGS
from scripts.delta_rc1_manual_validation import run_manual_validation


def test_manual_validation_passes_without_live_capabilities():
    report = run_manual_validation()
    assert report["passed"] is True
    assert all(report["checks"].values())


def test_manual_validation_preserves_hard_safety_flags():
    report = run_manual_validation()
    assert report["safety"]["model_b_default"] == "unchanged"
    assert report["safety"]["hyb1"] == "dormant_env_gated"
    assert report["prohibited_capabilities"]["provider_call_performed"] is False
    assert report["prohibited_capabilities"]["training_performed"] is False
    assert SAFETY_FLAGS["knowledge_mutation_performed"] is False
