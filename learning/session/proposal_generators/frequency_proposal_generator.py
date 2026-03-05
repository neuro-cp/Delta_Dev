from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from learning.schemas.learning_delta import LearningDelta
from learning.schemas.learning_proposal import LearningProposal


class FrequencyProposalGenerator:
    """
    Minimal, replay-stable proposal generator.

    PURPOSE:
    - Verify learning plumbing end-to-end
    - Emit at most ONE proposal
    - Based on simple recurrence counting

    CONTRACT:
    - Deterministic
    - Replay-idempotent
    - Fully bounded
    - No authority
    """

    MAX_MAGNITUDE = 0.01

    def generate(
        self,
        *,
        replay_id: str,
        semantic_ids: Iterable[str],
    ) -> List[LearningProposal]:
        """
        Generate a frequency-based learning proposal.

        Input:
        - semantic_ids: iterable of semantic identifiers observed across replay

        Output:
        - [] or [LearningProposal]
        """

        counts = Counter(semantic_ids)

        # Find any semantic that appears more than once
        recurrent = [
            semantic_id for semantic_id, count in counts.items()
            if count >= 2
        ]

        if not recurrent:
            return []

        # Deterministically select the first (sorted for stability)
        semantic_id = sorted(recurrent)[0]
        recurrence_count = counts[semantic_id]

        delta = LearningDelta(
            target=f"semantic_frequency:{semantic_id}",
            delta_type="additive",
            magnitude=self.MAX_MAGNITUDE,
            metadata={
                "recurrence_count": recurrence_count,
                "source": "frequency_proposal_generator",
            },
        )

        proposal = LearningProposal(
            proposal_id=f"freq:{semantic_id}",
            source_replay_id=replay_id,
            deltas=[delta],
            confidence=min(1.0, recurrence_count / 10.0),
            justification={
                "type": "semantic_recurrence",
                "semantic_id": semantic_id,
                "recurrence_count": recurrence_count,
            },
            bounded=True,
            replay_consistent=True,
            audit_tags=["frequency", "replay_stable"],
        )

        return [proposal]
