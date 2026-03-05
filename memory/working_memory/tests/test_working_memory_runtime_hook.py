from memory.working_memory.working_item import WorkingItem
from memory.working_memory.working_memory_policy import WorkingMemoryPolicy
from memory.working_memory.working_memory_buffer import WorkingMemoryBuffer
from memory.working_memory.working_memory_runtime_hook import (
    WorkingMemoryRuntimeHook,
)


def test_runtime_hook_snapshot() -> None:
    policy = WorkingMemoryPolicy(decay_rate=1.0, min_strength=0.0)
    buffer = WorkingMemoryBuffer(capacity=5, policy=policy)

    buffer.insert(WorkingItem("a", None, 1.0, 0))
    buffer.insert(WorkingItem("b", None, 2.0, 0))

    hook = WorkingMemoryRuntimeHook(buffer=buffer)
    snap = hook.snapshot()

    assert snap["count"] == 2
    assert snap["total_strength"] == 3.0
    assert set(snap["keys"]) == {"a", "b"}
