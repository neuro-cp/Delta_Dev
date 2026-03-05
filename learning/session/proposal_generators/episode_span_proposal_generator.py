from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List, Tuple

from learning.schemas.learning_delta import LearningDelta
from learning.schemas.learning_proposal import LearningProposal


class EpisodeSpanProposalGenerator:
    """
    Proposes a bounded persistence adjustment based on
    distinct episode span per semantic.

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
        semantic_episode_pairs: Iterable[Tuple[str, int]],
    ) -> List[LearningProposal]:
        spans = defaultdict(set)
        for semantic_id, episode_id in semantic_episode_pairs:
            spans[semantic_id].add(episode_id)

        eligible = [
            semantic_id
            for semantic_id, eps in spans.items()
            if len(eps) >= 2
        ]

        if not eligible:
            return []

        semantic_id = sorted(eligible)[0]
        span_count = len(spans[semantic_id])

        delta = LearningDelta(
            target=f"semantic_persistence:{semantic_id}",
            delta_type="additive",
            magnitude=self.MAX_MAGNITUDE,
            metadata={
                "episode_span": span_count,
                "source": "episode_span_proposal_generator",
            },
        )

        proposal = LearningProposal(
            proposal_id=f"span:{semantic_id}",
            source_replay_id=replay_id,
            deltas=[delta],
            confidence=min(1.0, span_count / 10.0),
            justification={
                "type": "episode_span",
                "semantic_id": semantic_id,
                "episode_span": span_count,
            },
            bounded=True,
            replay_consistent=True,
            audit_tags=["episode_span", "replay_stable"],
        )

        return [proposal]
