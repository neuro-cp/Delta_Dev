from memory.attention.attention_item import AttentionItem
from memory.attention.attention_policy import AttentionPolicy
from memory.attention.attention_field import AttentionField


def test_attention_field_add_and_step() -> None:
    policy = AttentionPolicy(
        decay_rate=0.5,
        min_gain=0.1,
        max_gain=1.0,
    )

    field = AttentionField(policy=policy)

    field.add(AttentionItem("a", 1.0, 0))
    field.add(AttentionItem("b", 0.5, 0))

    field.step(current_step=2)

    items = field.items()
    assert len(items) > 0
    assert all(i.gain <= 1.0 for i in items)


def test_attention_field_suppresses_weak_items() -> None:
    policy = AttentionPolicy(
        decay_rate=0.5,
        min_gain=0.3,
        max_gain=1.0,
    )

    field = AttentionField(policy=policy)
    field.add(AttentionItem("x", 0.2, 0))

    field.step(current_step=1)

    assert len(field.items()) == 0
