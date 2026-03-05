from memory.attention.attention_item import AttentionItem
from memory.attention.attention_policy import AttentionPolicy


def test_attention_decay_reduces_gain() -> None:
    policy = AttentionPolicy(
        decay_rate=0.5,
        min_gain=0.1,
        max_gain=1.0,
    )

    item = AttentionItem(
        key="a",
        gain=1.0,
        created_step=0,
    )

    decayed = policy.decay(item, current_step=2)
    assert decayed.gain < item.gain


def test_attention_suppression() -> None:
    policy = AttentionPolicy(
        decay_rate=1.0,
        min_gain=0.2,
        max_gain=1.0,
    )

    item = AttentionItem(
        key="b",
        gain=0.2,
        created_step=0,
    )

    assert policy.should_suppress(item)


def test_attention_normalization() -> None:
    policy = AttentionPolicy(
        decay_rate=1.0,
        min_gain=0.0,
        max_gain=1.0,
    )

    items = [
        AttentionItem("x", 1.0, 0),
        AttentionItem("y", 1.0, 0),
    ]

    normed = policy.normalize(items)
    total = sum(i.gain for i in normed)

    assert abs(total - 1.0) < 1e-6
