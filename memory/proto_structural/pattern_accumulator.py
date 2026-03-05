from __future__ import annotations

from collections import Counter
from typing import Iterable

from memory.proto_structural.episode_signature import EpisodeSignature
from memory.proto_structural.pattern_record import PatternRecord


class PatternAccumulator:
    """
    Offline accumulator of recurring EpisodeSignatures.

    CONTRACT:
    - Counts only
    - No decay
    - No thresholds
    - No authority
    """

    def __init__(self) -> None:
        self._counter: Counter[EpisodeSignature] = Counter()

    def ingest(self, signatures: Iterable[EpisodeSignature]) -> None:
        for sig in signatures:
            self._counter[sig] += 1

    def snapshot(self) -> PatternRecord:
        return PatternRecord(pattern_counts=dict(self._counter))
