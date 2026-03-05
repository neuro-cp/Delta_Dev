from __future__ import annotations

from typing import Iterable, List

from learning.schemas.learning_delta import LearningDelta
from learning.schemas.learning_proposal import LearningProposal

from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.pattern_statistics import PatternStatisticsBuilder
from memory.proto_learning.structural_eligibility.structural_eligibility_engine import (
    StructuralEligibilityEngine,
)


class StructuralPatternProposalGenerator:
    """
    Proposal generator based on structural recurrence eligibility.

    CONTRACT:
    - Deterministic
    - Replay-idempotent
    - Fully bounded
    - No authority
    - Uses proto-structural eligibility layer
    """

    MAX_MAGNITUDE = 0.01

    def __init__(self) -> None:
        self._eligibility_engine = StructuralEligibilityEngine()

    def generate(
        self,
        *,
        replay_id: str,
        pattern_counts: dict,
    ) -> List[LearningProposal]:
        """
        Input:
        - pattern_counts: Dict[EpisodeSignature, int]

        Output:
        - [] or [LearningProposal]
        """

        if not pattern_counts:
            return []

        record = PatternRecord(pattern_counts=pattern_counts)
        stats = PatternStatisticsBuilder().build(record=record)

        candidates = self._eligibility_engine.evaluate(stats=stats)

        if not candidates:
            return []

        # Deterministically select highest confidence candidate
        selected = sorted(
            candidates,
            key=lambda c: (-c.confidence_score, c.signature.as_canonical_tuple()),
        )[0]

        canonical_sig = selected.signature.as_canonical_tuple()

        delta = LearningDelta(
            target=f"structural_pattern:{canonical_sig}",
            delta_type="additive",
            magnitude=self.MAX_MAGNITUDE,
            metadata={
                "occurrences": selected.occurrences,
                "relative_frequency": selected.relative_frequency,
                "source": "structural_pattern_proposal_generator",
            },
        )

        proposal = LearningProposal(
            proposal_id=f"struct:{hash(canonical_sig)}",
            source_replay_id=replay_id,
            deltas=[delta],
            confidence=min(1.0, selected.confidence_score),
            justification={
                "type": "structural_recurrence",
                "signature": canonical_sig,
                "occurrences": selected.occurrences,
                "relative_frequency": selected.relative_frequency,
            },
            bounded=True,
            replay_consistent=True,
            audit_tags=["structural", "replay_stable"],
        )

        return [proposal]