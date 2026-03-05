from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

from memory.semantic.registry import SemanticRegistry
from memory.semantic.records import SemanticRecord


@dataclass(frozen=True)
class SemanticQueryResult:
    """
    Immutable result of a semantic query.

    This object is descriptive only.
    It carries NO authority and is not cached.
    """

    pattern_type: str
    summary: Dict[str, Any]


class SemanticQueryInterface:
    """
    Read-only semantic query adapter.

    Enforces Semantic Query Policy mechanically.
    This interface:
    - does NOT rank
    - does NOT recommend
    - does NOT score actions
    - does NOT influence runtime

    It exposes only descriptive accessors.
    """

    def __init__(self, registry: SemanticRegistry):
        self._registry = registry

    # --------------------------------------------------
    # Allowed queries
    # --------------------------------------------------

    def frequency_summary(self) -> SemanticQueryResult:
        """
        Return a descriptive frequency summary.

        This reports counts only.
        """
        summary = self._registry.summary()

        return SemanticQueryResult(
            pattern_type="frequency",
            summary=dict(summary),
        )

    def count_by_type(self, pattern_type: str) -> SemanticQueryResult:
        """
        Return count of semantic records by pattern type.
        """
        records = self._registry.by_type(pattern_type)

        return SemanticQueryResult(
            pattern_type=pattern_type,
            summary={
                "count": len(records),
            },
        )

    def has_pattern(self, semantic_id: str) -> bool:
        """
        Presence/absence check only.

        No metadata returned.
        """
        return self._registry.by_id(semantic_id) is not None

    # --------------------------------------------------
    # Explicitly forbidden surfaces (by omission)
    # --------------------------------------------------
    # No ranking
    # No preference
    # No utility
    # No recommendation
