from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, FrozenSet


@dataclass(frozen=True)
class EpisodeSignature:
    """
    Immutable, hashable description of episode *structure*.

    CONTRACT:
    - Structural only
    - No semantic meaning
    - No evaluation
    - No authority
    """

    # Basic structure
    length_steps: int
    event_count: int

    # Structural composition
    event_types: FrozenSet[str]
    region_ids: FrozenSet[str]

    # Transition shape
    transition_counts: Tuple[Tuple[str, str, int], ...]

    def as_canonical_tuple(self) -> tuple:
        """
        Canonical representation for hashing / comparison.
        """
        return (
            self.length_steps,
            self.event_count,
            tuple(sorted(self.event_types)),
            tuple(sorted(self.region_ids)),
            tuple(sorted(self.transition_counts)),
        )
