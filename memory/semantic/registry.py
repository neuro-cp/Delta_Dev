from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Dict, Optional

from memory.semantic.records import SemanticRecord


@dataclass(frozen=True)
class SemanticRegistry:
    """
    Read-only registry of semantic records.

    The registry is a passive catalog.
    It does NOT:
    - interpret semantics
    - rank semantics
    - merge semantics
    - influence runtime behavior

    It exists solely to organize and expose
    immutable SemanticRecord objects.
    """

    _records: List[SemanticRecord]

    # --------------------------------------------------
    # Construction helpers
    # --------------------------------------------------

    @classmethod
    def from_records(
        cls,
        records: Iterable[SemanticRecord],
    ) -> SemanticRegistry:
        """
        Construct a registry from semantic records.

        Records are copied defensively to preserve immutability.
        """
        return cls(list(records))

    # --------------------------------------------------
    # Accessors
    # --------------------------------------------------

    @property
    def records(self) -> List[SemanticRecord]:
        """
        Return all semantic records.

        Returned list is a shallow copy.
        """
        return list(self._records)

    def by_type(self, pattern_type: str) -> List[SemanticRecord]:
        """
        Return all semantic records matching a pattern type.
        """
        return [
            r for r in self._records
            if r.pattern_type == pattern_type
        ]

    def by_id(self, semantic_id: str) -> Optional[SemanticRecord]:
        """
        Lookup a semantic record by semantic_id.
        """
        for r in self._records:
            if r.semantic_id == semantic_id:
                return r
        return None

    def summary(self) -> Dict[str, int]:
        """
        Return a simple count summary by pattern type.

        No weighting, ranking, or interpretation.
        """
        counts: Dict[str, int] = {}
        for r in self._records:
            counts[r.pattern_type] = counts.get(r.pattern_type, 0) + 1
        return counts
