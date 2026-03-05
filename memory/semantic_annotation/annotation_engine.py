from __future__ import annotations

from typing import Iterable, List
from uuid import uuid4

from memory.episodic.episode_structure import Episode
from memory.semantic.registry import SemanticRegistry
from memory.semantic.query_interface import SemanticQueryInterface
from memory.semantic_annotation.annotation_record import (
    SemanticAnnotationRecord,
)


class SemanticAnnotationEngine:
    """
    Offline semantic → episodic annotation engine.

    This engine:
    - operates ONLY on closed episodes
    - runs ONLY during replay / offline analysis
    - produces immutable annotation records
    - NEVER mutates episodes or semantics
    - NEVER influences runtime behavior

    It is a descriptive labeling tool, not a learning system.
    """

    def __init__(
        self,
        *,
        semantic_registry: SemanticRegistry,
        policy_version: str = "v0",
        schema_version: str = "v0",
    ) -> None:
        self._registry = semantic_registry
        self._query = SemanticQueryInterface(semantic_registry)
        self._policy_version = policy_version
        self._schema_version = schema_version

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def annotate_episodes(
        self,
        episodes: Iterable[Episode],
    ) -> List[SemanticAnnotationRecord]:
        """
        Annotate a collection of episodes.

        Only CLOSED episodes are considered.
        Each annotation is additive and immutable.
        """
        annotations: List[SemanticAnnotationRecord] = []

        for ep in episodes:
            if not ep.closed:
                continue

            annotations.extend(self._annotate_single_episode(ep))

        return annotations

    # --------------------------------------------------
    # Per-episode annotation
    # --------------------------------------------------

    def _annotate_single_episode(
        self,
        episode: Episode,
    ) -> List[SemanticAnnotationRecord]:
        """
        Produce semantic annotations for a single episode.

        Deterministic, read-only, and policy-compliant.
        """
        records: List[SemanticAnnotationRecord] = []

        # Example annotation: frequency-based labeling
        freq_summary = self._query.frequency_summary()
        total_patterns = freq_summary.summary.get("frequency", 0)

        descriptor = (
            "episode resembles previously observed decision patterns"
            if episode.decision_count > 0
            else "episode resembles silent or non-decisional episodes"
        )

        records.append(
            SemanticAnnotationRecord(
                annotation_id=str(uuid4()),
                episode_id=episode.episode_id,
                annotation_type="semantic_pattern_match",
                source_semantic_ids=[
                    r.semantic_id for r in self._registry.records
                ],
                policy_version=self._policy_version,
                schema_version=self._schema_version,
                applied_during_replay=True,
                episode_closed=True,
                descriptor=descriptor,
                metrics={
                    "episode_decision_count": episode.decision_count,
                    "known_semantic_patterns": total_patterns,
                },
                confidence=None,
                tags={},
                notes=None,
            )
        )

        return records
