from memory.working_memory.working_item import WorkingItem
from memory.working_memory.working_memory_policy import WorkingMemoryPolicy
from memory.working_memory.working_memory_buffer import WorkingMemoryBuffer


def test_buffer_respects_capacity() -> None:
    policy = WorkingMemoryPolicy(decay_rate=1.0, min_strength=0.0)
    buffer = WorkingMemoryBuffer(capacity=2, policy=policy)

    buffer.insert(WorkingItem("a", None, 1.0, 0))
    buffer.insert(WorkingItem("b", None, 0.9, 0))
    buffer.insert(WorkingItem("c", None, 0.8, 0))

    items = buffer.items()
    assert len(items) == 2
    assert {i.key for i in items} == {"a", "b"}


def test_buffer_decay_and_eviction() -> None:
    
    policy = WorkingMemoryPolicy(decay_rate=0.5, min_strength=0.2)
    buffer = WorkingMemoryBuffer(capacity=5, policy=policy)

    buffer.insert(WorkingItem("x", None, 1.0, 0))
    buffer.step(current_step=3)

    assert len(buffer.items()) == 0
