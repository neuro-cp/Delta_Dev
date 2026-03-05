from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Dict, Optional

from memory.semantic_annotation.annotation_record import (
    SemanticAnnotationRecord,
)


@dataclass(frozen=True)
class AnnotationRegistry:
    """
    Read-only registry for semantic annotations.

    This is a passive index.
    It does NOT:
    - interpret annotations
    - rank annotations
    - merge annotations
    - influence runtime behavior
    """

    _records: List[SemanticAnnotationRecord]

    # --------------------------------------------------
    # Construction
    # --------------------------------------------------

    @classmethod
    def from_records(
        cls,
        records: Iterable[SemanticAnnotationRecord],
    ) -> AnnotationRegistry:
        """
        Construct a registry from annotation records.

        Records are copied defensively.
        """
        return cls(list(records))

    # --------------------------------------------------
    # Accessors
    # --------------------------------------------------

    @property
    def records(self) -> List[SemanticAnnotationRecord]:
        """
        Return all annotation records.

        Returned list is a shallow copy.
        """
        return list(self._records)

    def by_episode(self, episode_id: int) -> List[SemanticAnnotationRecord]:
        """
        Return annotations associated with a specific episode.
        """
        return [
            r for r in self._records
            if r.episode_id == episode_id
        ]

    def by_type(self, annotation_type: str) -> List[SemanticAnnotationRecord]:
        """
        Return annotations matching a given annotation type.
        """
        return [
            r for r in self._records
            if r.annotation_type == annotation_type
        ]

    def summary(self) -> Dict[str, int]:
        """
        Return a count summary by annotation type.
        """
        counts: Dict[str, int] = {}
        for r in self._records:
            counts[r.annotation_type] = counts.get(r.annotation_type, 0) + 1
        return counts
