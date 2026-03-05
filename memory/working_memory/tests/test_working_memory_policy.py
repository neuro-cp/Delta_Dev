from memory.working_memory.working_item import WorkingItem
from memory.working_memory.working_memory_policy import WorkingMemoryPolicy


def test_decay_reduces_strength_over_time() -> None:
    policy = WorkingMemoryPolicy(decay_rate=0.9, min_strength=0.01)

    item = WorkingItem(
        key="a",
        payload=None,
        strength=1.0,
        created_step=0,
    )

    decayed = policy.decay(item, current_step=10)
    assert decayed.strength < item.strength


def test_eviction_threshold() -> None:
    policy = WorkingMemoryPolicy(decay_rate=1.0, min_strength=0.5)

    item = WorkingItem(
        key="b",
        payload=None,
        strength=0.4,
        created_step=0,
    )

    assert policy.should_evict(item, current_step=1)
