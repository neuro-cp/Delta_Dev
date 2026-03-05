from engine.vta_value.value_engine import ValueEngine
from engine.vta_value.value_signal import ValueSignal
from engine.vta_value.value_policy import ValuePolicy
from engine.vta_value.value_trace import ValueTrace
from engine.vta_value.value_source import ValueProposal


def test_value_engine_applies_proposal() -> None:
    signal = ValueSignal()
    policy = ValuePolicy(min_interval_steps=0)
    trace = ValueTrace()

    engine = ValueEngine(
        signal=signal,
        policy=policy,
        trace=trace,
    )

    proposal = ValueProposal(
        delta=0.1,
        source="test",
    )

    accepted = engine.apply_proposal(
        proposal=proposal,
        current_step=0,
    )

    assert accepted is True
    assert signal.value == 0.1
    assert trace.records[-1]["event"] == "proposal"


def test_value_engine_rejects_proposal() -> None:
    signal = ValueSignal()
    policy = ValuePolicy(min_interval_steps=10)
    trace = ValueTrace()

    engine = ValueEngine(
        signal=signal,
        policy=policy,
        trace=trace,
    )

    engine.apply_proposal(
        proposal=ValueProposal(delta=0.1, source="a"),
        current_step=0,
    )

    accepted = engine.apply_proposal(
        proposal=ValueProposal(delta=0.1, source="b"),
        current_step=1,
    )

    assert accepted is False
    assert signal.value == 0.1
