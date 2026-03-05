from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SemanticActivationRecord:
    """
    Immutable snapshot of semantic activation levels.

    Descriptive only.
    No authority.
    Safe to discard and recompute.
    """

    # ontology_term -> activation level (unnormalized, >= 0)
    activations: Dict[str, float]

    # offline step or window index used to compute this snapshot
    snapshot_index: int
