from memory.working_memory.working_item import WorkingItem
from memory.working_memory.working_memory_buffer import WorkingMemoryBuffer
from memory.working_memory.working_memory_policy import WorkingMemoryPolicy
from memory.working_memory.working_memory_runtime_hook import WorkingMemoryRuntimeHook

from memory.attention.attention_policy import AttentionPolicy
from memory.attention.attention_field import AttentionField
from memory.attention.attention_ingest import AttentionIngest
from memory.attention.sources.working_memory_source import (
    WorkingMemoryAttentionSource,
)


def test_working_memory_feeds_attention_field() -> None:
    # --------------------------------------------------
    # Build working memory
    # --------------------------------------------------
    wm_policy = WorkingMemoryPolicy(
        decay_rate=1.0,
        min_strength=0.0,
    )
    wm_buffer = WorkingMemoryBuffer(
        capacity=5,
        policy=wm_policy,
    )

    wm_buffer.insert(WorkingItem("a", None, 0.8, created_step=0))
    wm_buffer.insert(WorkingItem("b", None, 0.2, created_step=0))

    wm_hook = WorkingMemoryRuntimeHook(buffer=wm_buffer)
    wm_hook.step(current_step=10)

    # --------------------------------------------------
    # Build attention system
    # --------------------------------------------------
    att_policy = AttentionPolicy(
        decay_rate=1.0,
        min_gain=0.0,
        max_gain=1.0,
    )
    field = AttentionField(policy=att_policy)

    source = WorkingMemoryAttentionSource(wm_hook=wm_hook)
    ingest = AttentionIngest(field=field, sources=[source])

    # --------------------------------------------------
    # Ingest WM → Attention
    # --------------------------------------------------
    ingest.ingest()

    items = field.items()
    gains = {i.key: i.gain for i in items}

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    assert gains["a"] == 0.8
    assert gains["b"] == 0.2
    assert len(gains) == 2
##validated test##