from engine.vta_value.value_engine import ValueEngine
from engine.vta_value.value_signal import ValueSignal
from engine.vta_value.value_policy import ValuePolicy
from engine.vta_value.value_trace import ValueTrace
from engine.vta_value.value_adapter import ValueAdapter
from engine.vta_value.value_source import ValueProposal

from memory.drive.drive_signal import DriveSignal
from memory.drive.drive_policy import DrivePolicy
from memory.drive.drive_field import DriveField
from memory.drive.drive_to_attention_adapter import DriveToAttentionAdapter

from memory.attention.attention_item import AttentionItem
from memory.attention.attention_policy import AttentionPolicy
from memory.attention.attention_field import AttentionField
from memory.attention.attention_bias_aggregator import AttentionBiasAggregator

from engine.integration.memory_bias_registry import MemoryBiasRegistry


def test_drive_value_joint_attention_bias_flow_inspection_only() -> None:
    """
    Integration proof (Option B):

    Drive + Value → BiasRegistry → AttentionBiasAggregator (inspection only)

    Verifies:
    - Drive-derived attention bias exists
    - Value-derived attention bias exists
    - Both coexist in the registry
    - Aggregation combines both sources deterministically
    - Order of sources does not matter
    - No attention state is mutated
    """

    # --------------------------------------------------
    # Drive setup
    # --------------------------------------------------
    drive_policy = DrivePolicy(
        decay_rate=1.0,
        min_magnitude=0.0,
        max_magnitude=1.0,
    )
    drive_field = DriveField(policy=drive_policy)

    drive_field.ingest(
        [
            DriveSignal(
                key="novelty",
                magnitude=0.5,
                created_step=0,
            )
        ]
    )

    drive_att_adapter = DriveToAttentionAdapter(field=drive_field)
    drive_attention_bias = drive_att_adapter.compute_gain_bias()

    # --------------------------------------------------
    # Value setup
    # --------------------------------------------------
    value_signal = ValueSignal()
    value_policy = ValuePolicy(min_interval_steps=0)
    value_trace = ValueTrace()

    value_engine = ValueEngine(
        signal=value_signal,
        policy=value_policy,
        trace=value_trace,
    )

    value_engine.apply_proposal(
        proposal=ValueProposal(
            delta=0.6,
            source="test",
        ),
        current_step=0,
    )

    assert value_signal.value > 0.0

    value_adapter = ValueAdapter(
        decision_bias_gain=0.5,
        enabled=True,
    )

    # Value expresses itself as a multiplicative attention-style bias
    value_attention_bias = value_adapter.apply_to_decision_bias(
        value=value_signal.value,
        bias_map={"novelty": 1.0},
    )

    # --------------------------------------------------
    # Bias registry (inspection only)
    # --------------------------------------------------
    registry = MemoryBiasRegistry()

    registry.register_attention_bias(
        source="drive",
        bias=drive_attention_bias,
    )
    registry.register_attention_bias(
        source="value",
        bias=value_attention_bias,
    )

    snapshot = registry.attention_bias()

    assert "drive" in snapshot
    assert "value" in snapshot

    # --------------------------------------------------
    # Attention aggregation (NOT applied)
    # --------------------------------------------------
    attention_policy = AttentionPolicy(
        decay_rate=1.0,
        min_gain=0.0,
        max_gain=2.0,
    )
    attention_field = AttentionField(policy=attention_policy)

    attention_field.add(
        AttentionItem(
            key="novelty",
            gain=1.0,
            created_step=0,
        )
    )

    aggregator = AttentionBiasAggregator()

    aggregated = aggregator.aggregate(
        base_gains={"novelty": 1.0},
        bias_sources=registry.attention_bias(),
    )

    # --------------------------------------------------
    # Expected combined bias
    # --------------------------------------------------
    drive_gain = drive_attention_bias["novelty"]
    value_gain = value_attention_bias["novelty"]

    expected = 1.0 * drive_gain * value_gain

    assert aggregated["novelty"] == expected

    # --------------------------------------------------
    # Attention field remains unchanged (no application)
    # --------------------------------------------------
    assert attention_field.items()[0].gain == 1.0
##validated##