from __future__ import annotations

from typing import Optional

from memory.working_memory.working_memory_runtime_hook import (
    WorkingMemoryRuntimeHook,
)
from memory.attention.attention_ingest import AttentionIngest
from memory.attention.attention_field import AttentionField
from memory.drive.drive_field import DriveField


class CognitiveScheduler:
    """
    Deterministic cognitive scheduler.

    CONTRACT:
    - Orchestrates memory-layer stepping
    - No runtime mutation
    - No decision authority
    - No bias application (suggestions only)
    """

    def __init__(
        self,
        *,
        working_memory_hook: WorkingMemoryRuntimeHook,
        attention_ingest: AttentionIngest,
        attention_field: AttentionField,
        drive_field: DriveField,
    ) -> None:
        self._wm_hook = working_memory_hook
        self._attention_ingest = attention_ingest
        self._attention_field = attention_field
        self._drive_field = drive_field

    def step(self, *, current_step: int) -> None:
        """
        Advance cognitive subsystems for a single timestep.

        ORDER (locked):
        1. Update working-memory timebase
        2. Ingest attention proposals
        3. Step attention dynamics
        4. Step drive dynamics
        """

        # --------------------------------------------------
        # 1. Update WM timebase (read-only)
        # --------------------------------------------------
        self._wm_hook.step(current_step=current_step)

        # --------------------------------------------------
        # 2. Ingest attention proposals (read-only)
        # --------------------------------------------------
        self._attention_ingest.ingest()

        # --------------------------------------------------
        # 3. Step attention dynamics
        # --------------------------------------------------
        self._attention_field.step(current_step=current_step)

        # --------------------------------------------------
        # 4. Step drive dynamics (slow field)
        # --------------------------------------------------
        self._drive_field.step(current_step=current_step)
