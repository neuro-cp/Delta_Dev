from __future__ import annotations

from orchestration.runtime.v16_env import DeltaEvaluatorEnv
from orchestration.runtime.v16_external_consolidation_evaluator_api_design import (
    build_external_consolidation_evaluator_api_design_payload,
    build_external_consolidation_evaluator_request,
    build_external_evaluator_policy,
    validate_external_evaluator_api_design_safe,
)
from orchestration.runtime.v16_external_consolidation_evaluator_api_design_report import (
    write_external_evaluator_api_design_report,
)


def test_policy_never_allows_live_call_in_design_phase():
    env = DeltaEvaluatorEnv(api_key_present=True, enabled=True, allow_live_call=True)
    policy = build_external_evaluator_policy(env)
    assert policy.live_call_permitted_by_env is True
    assert policy.live_call_allowed_in_phase is False
    assert policy.automatic_daily_run_enabled is False
    assert policy.evaluator_authoritative is False


def test_request_is_design_only_even_when_env_permits_live_call():
    env = DeltaEvaluatorEnv(api_key_present=True, enabled=True, allow_live_call=True)
    request = build_external_consolidation_evaluator_request(
        {
            "memory_candidate_id": "candidate-1",
            "proposed_memory_text": "HYB1 remains dormant.",
            "provenance_reference_ids": ["trace-1"],
        },
        env,
    )
    assert request.live_call_requested is True
    assert request.live_call_allowed is False
    assert request.candidate_is_truth is False
    assert request.evaluator_is_authority is False


def test_design_payload_is_safe():
    payload = build_external_consolidation_evaluator_api_design_payload()
    assert validate_external_evaluator_api_design_safe(payload)
    assert payload["design_review"]["provider_calls_performed"] is False
    assert payload["invariant_flags"]["scheduler_enabled"] is False


def test_report_generation(tmp_path, monkeypatch):
    from orchestration.runtime import v16_external_consolidation_evaluator_api_design_report as report_module

    monkeypatch.setattr(report_module, "REPORT_MD", tmp_path / "v16b.md")
    monkeypatch.setattr(report_module, "REPORT_JSON", tmp_path / "v16b.json")
    data = write_external_evaluator_api_design_report()
    assert data["design_safe"] is True
    assert data["final_recommendation"] == "PROCEED_DAILY_EXTERNAL_CONSOLIDATION_EVALUATOR_API_TRIAL"
    assert report_module.REPORT_MD.exists()
    assert report_module.REPORT_JSON.exists()
