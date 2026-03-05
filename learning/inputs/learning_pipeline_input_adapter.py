from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

from learning.inputs.learning_input_builder import LearningInputBuilder
from learning.inputs.learning_input_bundle import LearningInputBundle

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord


class LearningPipelineInputAdapter:
    """
    Thin boundary adapter that declares which OFFLINE artifacts
    learning is allowed to see.

    CONTRACT:
    - Accepts inspection-surface artifacts only
    - No inference, no thresholds, no mutation
    - Delegates normalization to LearningInputBuilder
    """

    def __init__(self) -> None:
        self._builder = LearningInputBuilder()

    def from_inspection_surface(
        self,
        *,
        replay_id: str,
        semantic_activation_records: Optional[Sequence[SemanticActivationRecord]] = None,
        pattern_record: Optional[PatternRecord] = None,
        semantic_episode_pairs: Optional[Iterable[Tuple[str, int]]] = None,
        tags: Optional[dict] = None,
    ) -> LearningInputBundle:
        """
        Build a LearningInputBundle from artifacts that inspection already aggregates.

        NOTE:
        - We intentionally do NOT accept trace/replay/runtime objects here.
        - semantic_episode_pairs are included ONLY if provenance already exists.
        """
        return self._builder.build(
            replay_id=replay_id,
            semantic_records=list(semantic_activation_records) if semantic_activation_records else None,
            pattern_record=pattern_record,
            semantic_episode_pairs=semantic_episode_pairs,
            tags=tags,
        )
