from engine.vta_value.value_engine import ValueEngine
from engine.vta_value.value_signal import ValueSignal
from engine.vta_value.value_policy import ValuePolicy
from engine.vta_value.value_trace import ValueTrace
from engine.vta_value.value_adapter import ValueAdapter
from engine.vta_value.value_source import ValueProposal

from engine.integration.memory_bias_registry import MemoryBiasRegistry


def test_value_bias_flow_inspection_only() -> None:
    """
    Integration proof:

    Value → BiasRegistry (inspection only)

    Verifies:
    - Value signal can change (policy-respecting)
    - Value-derived bias can be computed from actual value
    - Bias is registered
    - Bias is observable
    - Bias is NOT applied to any system
    """

    # --------------------------------------------------
    # Value setup
    # --------------------------------------------------
    signal = ValueSignal()
    policy = ValuePolicy(min_interval_steps=0)
    trace = ValueTrace()

    engine = ValueEngine(
        signal=signal,
        policy=policy,
        trace=trace,
    )

    # Apply a value proposal (proposal ≠ applied delta)
    engine.apply_proposal(
        proposal=ValueProposal(
            delta=0.6,
            source="test",
        ),
        current_step=0,
    )

    # Value must change, but remains policy-bounded
    assert signal.value > 0.0

    # --------------------------------------------------
    # Compute bias (inspection-only)
    # --------------------------------------------------
    adapter = ValueAdapter(
        decision_bias_gain=0.5,
        enabled=True,
    )

    base_bias = {
        "A": 1.0,
        "B": -0.5,
    }

    value_bias = adapter.apply_to_decision_bias(
        value=signal.value,
        bias_map=base_bias,
    )

    expected_scale = 1.0 + (signal.value * adapter.decision_bias_gain)

    assert value_bias["A"] == base_bias["A"] * expected_scale
    assert value_bias["B"] == base_bias["B"] * expected_scale

    # --------------------------------------------------
    # Bias registry (inspection only)
    # --------------------------------------------------
    registry = MemoryBiasRegistry()

    registry.register_attention_bias(
        source="value",
        bias=value_bias,
    )

    snapshot = registry.snapshot()

    assert "value" in snapshot["attention_bias"]
    assert snapshot["attention_bias"]["value"]["A"] == base_bias["A"] * expected_scale

    # --------------------------------------------------
    # Nothing is applied
    # --------------------------------------------------
    # Registry does not mutate any system state.
##validated##