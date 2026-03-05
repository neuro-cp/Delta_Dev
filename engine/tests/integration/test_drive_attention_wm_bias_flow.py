from memory.drive.drive_signal import DriveSignal
from memory.drive.drive_policy import DrivePolicy
from memory.drive.drive_field import DriveField
from memory.drive.drive_to_attention_adapter import DriveToAttentionAdapter
from memory.drive.drive_to_working_memory_adapter import DriveToWorkingMemoryAdapter

from memory.attention.attention_item import AttentionItem
from memory.attention.attention_policy import AttentionPolicy
from memory.attention.attention_field import AttentionField
from memory.attention.attention_bias_aggregator import AttentionBiasAggregator

from memory.working_memory.working_item import WorkingItem
from memory.working_memory.working_memory_policy import WorkingMemoryPolicy
from memory.working_memory.working_memory_buffer import WorkingMemoryBuffer
from memory.working_memory.working_memory_runtime_hook import WorkingMemoryRuntimeHook

from engine.integration.memory_bias_registry import MemoryBiasRegistry


def test_drive_attention_wm_bias_flow() -> None:
    """
    Integration proof:

    Drive → BiasRegistry → Attention / Working Memory

    Verifies:
    - Drive produces bias
    - Bias is registered
    - Bias is observable
    - Bias is NOT applied to state
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
    drive_wm_adapter = DriveToWorkingMemoryAdapter(field=drive_field)

    # --------------------------------------------------
    # Bias registry
    # --------------------------------------------------
    registry = MemoryBiasRegistry()

    registry.register_attention_bias(
        source="drive",
        bias=drive_att_adapter.compute_gain_bias(),
    )

    wm_decay_bias = drive_wm_adapter.compute_decay_bias()
    registry.register_working_memory_decay_bias(
        source="drive",
        bias=wm_decay_bias["novelty"],
    )

    # --------------------------------------------------
    # Attention side (bias computed, NOT applied)
    # --------------------------------------------------
    attention_policy = AttentionPolicy(
        decay_rate=1.0,
        min_gain=0.0,
        max_gain=2.0,
    )
    attention_field = AttentionField(policy=attention_policy)

    # Baseline attention
    attention_field.add(
        AttentionItem(
            key="novelty",
            gain=1.0,
            created_step=0,
        )
    )

    aggregator = AttentionBiasAggregator()

    biased_attention = aggregator.aggregate(
        base_gains={i.key: i.gain for i in attention_field.items()},
        bias_sources=registry.attention_bias(),
    )

    # Bias exists
    assert biased_attention["novelty"] == 1.5

    # But attention field itself is unchanged
    assert attention_field.items()[0].gain == 1.0

    # --------------------------------------------------
    # Working memory side (bias exists, NOT applied)
    # --------------------------------------------------
    wm_policy = WorkingMemoryPolicy(
        decay_rate=0.9,
        min_strength=0.0,
    )
    wm_buffer = WorkingMemoryBuffer(
        capacity=3,
        policy=wm_policy,
    )

    wm_buffer.insert(
        WorkingItem(
            key="x",
            payload=None,
            strength=1.0,
            created_step=0,
        )
    )

    wm_hook = WorkingMemoryRuntimeHook(buffer=wm_buffer)
    wm_hook.step(current_step=1)

    wm_snapshot = wm_hook.snapshot()

    # Bias is visible
    assert wm_snapshot["decay_bias"] == 1.0

    # Item strength is unchanged (no application)
    assert wm_snapshot["items"][0]["strength"] == 1.0
