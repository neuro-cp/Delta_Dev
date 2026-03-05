from __future__ import annotations

from typing import Iterable, List

from learning.schemas.learning_delta import LearningDelta
from learning.schemas.learning_proposal import LearningProposal


class InvalidProposalGenerator:
    """
    Deliberately emits an invalid proposal to prove audit hard-failure.

    CONTRACT:
    - Deterministic
    - Replay-idempotent
    - Intentionally violates boundedness
    """

    def generate(
        self,
        *,
        replay_id: str,
        semantic_ids: Iterable[str],
    ) -> List[LearningProposal]:
        # Emit exactly one invalid proposal, always
        delta = LearningDelta(
            target="semantic_frequency:__invalid__",
            delta_type="additive",
            magnitude=1.0,  # irrelevant; bounded=False is the violation
            metadata={"source": "invalid_proposal_generator"},
        )

        proposal = LearningProposal(
            proposal_id="invalid:unbounded",
            source_replay_id=replay_id,
            deltas=[delta],
            confidence=1.0,
            justification={"type": "intentional_failure"},
            bounded=False,              # <-- violation
            replay_consistent=True,
            audit_tags=["invalid", "test_only"],
        )

        return [proposal]
##validated##