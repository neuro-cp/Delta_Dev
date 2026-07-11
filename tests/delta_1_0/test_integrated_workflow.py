import json

from orchestration.runtime.delta_1_0_integrated_workflow import (
    post_rc_reuse_audit,
    run_all_reports,
    run_delta_1_0_benchmark,
    run_integration_flows,
)


def test_reuse_audit_names_existing_rc_layers():
    audit = post_rc_reuse_audit()
    assert "RC4" in audit["reused_components"]
    assert "RC6" in audit["reused_components"]
    assert audit["boundaries"]["delta_75_scope"] is False


def test_benchmark_keeps_separate_metrics():
    benchmark = run_delta_1_0_benchmark()
    assert benchmark["recommendation"] == "DELTA_1_0_OPERATOR_PILOT_FOUNDATION_READY"
    assert "overall" not in benchmark["categories"]
    assert benchmark["categories"]["safety_invariants"] == 1.0


def test_integration_flows_are_reported_without_activation():
    flows = run_integration_flows()
    assert flows["status"] == "INTEGRATION_FLOWS_PASSED"
    assert flows["safety"]["provider_calls_performed"] is False


def test_report_generation_outputs_json(tmp_path, monkeypatch):
    # Exercise the report payload without writing into the real repo for this test.
    payload = run_all_reports(root=tmp_path, write=False)
    encoded = json.dumps(payload, default=str)
    assert "DELTA_1_0_OPERATOR_PILOT_FOUNDATION_READY" in encoded
    assert payload["safety"]["runtime_push_performed"] is False
