from __future__ import annotations
from typing import List
from memory.proto_structural.pattern_statistics import PatternStatistics
from .structural_candidate import StructuralCandidate

class StructuralEligibilityEngine:
    '''
    CONTRACT:
    - Offline only
    - Deterministic
    - No mutation
    - No runtime coupling
    '''

    def __init__(
        self,
        *,
        min_occurrences: int = 3,
        min_relative_frequency: float = 0.6,
    ) -> None:
        self._min_occurrences = min_occurrences
        self._min_relative_frequency = min_relative_frequency

    def evaluate(self, *, stats: PatternStatistics) -> List[StructuralCandidate]:
        candidates: List[StructuralCandidate] = []

        for sig in stats.ordered_signatures:
            occ = stats.counts[sig]
            freq = stats.relative_frequency.get(sig, 0.0)

            if occ >= self._min_occurrences and freq >= self._min_relative_frequency:
                confidence = occ * freq
                candidates.append(
                    StructuralCandidate(
                        signature=sig,
                        occurrences=occ,
                        relative_frequency=freq,
                        confidence_score=confidence,
                    )
                )

        return candidates
