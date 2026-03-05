from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class SemanticDiff:
    added_terms: Tuple[str, ...]
    removed_terms: Tuple[str, ...]
    changed_activations: Dict[str, Tuple[float, float]]  # term -> (before, after)


@dataclass(frozen=True)
class StructuralPatternDiff:
    added_signatures: Tuple[Tuple, ...]
    removed_signatures: Tuple[Tuple, ...]
    count_deltas: Dict[Tuple, int]  # signature -> delta


@dataclass(frozen=True)
class TagDiff:
    added_tags: Tuple[str, ...]
    removed_tags: Tuple[str, ...]
    changed_tags: Tuple[str, ...]


@dataclass(frozen=True)
class LearningBundleDiff:
    """
    Read-only diff between two LearningInputBundles.

    CONTRACT:
    - Observational only
    - Deterministic
    - No mutation of inputs
    - No learning or authority
    """
    has_difference: bool
    summary: Any = None
