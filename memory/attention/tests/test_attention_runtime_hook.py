from memory.attention.attention_item import AttentionItem
from memory.attention.attention_policy import AttentionPolicy
from memory.attention.attention_field import AttentionField
from memory.attention.attention_runtime_hook import AttentionRuntimeHook


def test_attention_runtime_snapshot() -> None:
    policy = AttentionPolicy(
        decay_rate=1.0,
        min_gain=0.0,
        max_gain=1.0,
    )

    field = AttentionField(policy=policy)
    field.add(AttentionItem("a", 0.6, 0))
    field.add(AttentionItem("b", 0.4, 0))

    hook = AttentionRuntimeHook(field=field)
    snap = hook.snapshot()

    assert snap["count"] == 2
    assert snap["gains"]["a"] == 0.6
    assert snap["gains"]["b"] == 0.4
