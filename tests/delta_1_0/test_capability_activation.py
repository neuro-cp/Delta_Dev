from orchestration.runtime.delta_1_0_capability_activation import (
    activation_request,
    default_capabilities,
    evaluate_activation,
    gated_capability_report,
)


def test_self_activation_and_execute_are_rejected():
    cap = default_capabilities()["RC6_GOVERNED_EXTERNAL_INTELLIGENCE"]
    request = activation_request(
        cap.capability_id,
        "TRIAL_ACTIVE",
        "EXECUTE_BOUNDED",
        operator_approved=False,
        scope="auto activate",
        requested_by=cap.capability_id,
    )
    decision = evaluate_activation(cap, request)
    assert decision.allowed is False
    assert "self_activation_rejected" in decision.reasons
    assert "operator_approval_required" in decision.reasons


def test_activation_requires_evidence_and_valid_scope():
    cap = default_capabilities()["PYTHON_CODING_MODULE_V1"]
    request = activation_request(
        cap.capability_id,
        "PILOT_ELIGIBLE",
        "PREPARE",
        operator_approved=True,
        scope="DELTA-75 trial",
        evidence_refs=("a", "b", "c"),
    )
    decision = evaluate_activation(cap, request)
    assert decision.allowed is False
    assert "delta_75_out_of_scope" in decision.reasons


def test_negative_control_report_is_fail_closed():
    report = gated_capability_report()
    assert report["status"] == "GATED_CAPABILITY_FRAMEWORK_READY_FAIL_CLOSED"
    assert all(not decision.allowed for decision in report["negative_control_decisions"].values())
