from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


@dataclass(frozen=True)
class PatternStatistics:
    """
    Distributional facts about structural recurrence.

    CONTRACT:
    - Descriptive only
    - No thresholds
    - No evaluation
    - No authority
    """

    total_signatures: int
    total_occurrences: int
    counts: Dict[EpisodeSignature, int]
    relative_frequency: Dict[EpisodeSignature, float]
    ordered_signatures: List[EpisodeSignature]


class PatternStatisticsBuilder:
    """
    Offline analyzer: PatternRecord → PatternStatistics.

    CONTRACT:
    - Read-only
    - Deterministic
    - No interpretation
    """

    def build(self, *, record: PatternRecord) -> PatternStatistics:
        counts = dict(record.pattern_counts)

        total_occurrences = sum(counts.values())
        total_signatures = len(counts)

        if total_occurrences == 0:
            relative_frequency: Dict[EpisodeSignature, float] = {}
        else:
            relative_frequency = {
                sig: count / total_occurrences
                for sig, count in counts.items()
            }

        ordered_signatures = sorted(
            counts.keys(),
            key=lambda sig: counts[sig],
            reverse=True,
        )

        return PatternStatistics(
            total_signatures=total_signatures,
            total_occurrences=total_occurrences,
            counts=counts,
            relative_frequency=relative_frequency,
            ordered_signatures=ordered_signatures,
        )