from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from memory.proto_structural.episode_signature import EpisodeSignature


@dataclass(frozen=True)
class PatternRecord:
    """
    Immutable snapshot of accumulated structural patterns.

    CONTRACT:
    - Descriptive only
    - Serializable
    - Discardable
    """

    pattern_counts: Dict[EpisodeSignature, int]
