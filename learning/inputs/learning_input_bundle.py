from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Any


@dataclass(frozen=True)
class LearningInputBundle:
    """
    Immutable, offline learning input bundle.

    CONTRACT:
    - Derived offline only
    - Deterministic ordering (builder enforced)
    - Serializable-friendly (no custom objects required)
    - No authority, no mutation, safe to discard

    Notes:
    - This bundle intentionally does NOT invent mappings that are not present
      in artifacts. (e.g., it does not infer semantic↔episode pairing unless
      explicitly supplied.)
    """

    # Identity / provenance
    replay_id: str

    # Episodes (identity only; ordering canonicalized)
    episode_ids: Tuple[int, ...]

    # Semantic observations (multiset-style list; canonicalized)
    semantic_ids: Tuple[str, ...]

    # Optional explicit semantic↔episode evidence (canonicalized)
    semantic_episode_pairs: Tuple[Tuple[str, int], ...] = field(default_factory=tuple)

    # Semantic activation snapshots (canonicalized summary form)
    # Each entry: (snapshot_index, ((term, activation), ...sorted...))
    semantic_activation_snapshots: Tuple[
        Tuple[int, Tuple[Tuple[str, float], ...]],
        ...
    ] = field(default_factory=tuple)

    # Proto-structural pattern counts (canonicalized)
    # Each entry: (signature_tuple, count)
    pattern_counts: Tuple[Tuple[Tuple[Any, ...], int], ...] = field(default_factory=tuple)

    # Optional free-form tags (immutable, hash-safe)
    tags: Tuple[Tuple[str, Any], ...] = field(default_factory=tuple)
