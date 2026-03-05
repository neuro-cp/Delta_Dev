from engine.vta_value.value_trace import ValueTrace


def test_value_trace_records_proposal_and_decay() -> None:
    trace = ValueTrace()

    trace.record_proposal(
        step=0,
        source="test",
        proposed_delta=0.1,
        accepted=True,
        resulting_value=0.1,
        reason="accepted",
    )

    trace.record_decay(
        step=10,
        value=0.05,
    )

    summary = trace.summary()

    assert summary["count"] == 2
    assert summary["proposals"] == 1
    assert summary["accepted"] == 1
    assert summary["decays"] == 1
