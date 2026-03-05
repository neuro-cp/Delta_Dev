from __future__ import annotations

from typing import Iterable

from memory.attention.attention_item import AttentionItem
from memory.attention.attention_source import AttentionSource
from memory.working_memory.working_memory_runtime_hook import (
    WorkingMemoryRuntimeHook,
)


class WorkingMemoryAttentionSource(AttentionSource):
    """
    Attention source backed by Working Memory.

    CONTRACT:
    - Read-only
    - No mutation of working memory
    - Strength maps directly to attention gain
    """

    def __init__(
        self,
        *,
        wm_hook: WorkingMemoryRuntimeHook,
    ) -> None:
        self._wm_hook = wm_hook

    def propose(self) -> Iterable[AttentionItem]:
        snapshot = self._wm_hook.snapshot()

        current_step = snapshot["current_step"]
        items = snapshot["items"]

        for item in items:
            yield AttentionItem(
                key=item["key"],
                gain=item["strength"],
                created_step=current_step,
                source="working_memory",
            )
