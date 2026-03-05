from __future__ import annotations

from typing import Dict, Tuple


class ReplayEligibilityPolicy:
    """
    Pure, stateless eligibility rules for replay.

    This policy:
    - Examines episode metadata
    - Applies deterministic rules
    - Returns eligibility decisions with explanations

    It does NOT:
    - Track history
    - Encode semantics
    - Assign importance
    - Mutate episodes
    """

    @staticmethod
    def is_episode_eligible(
        episode_meta: Dict[str, float],
        *,
        min_length: int = 1,
        min_decisions: int = 0,
    ) -> Tuple[bool, str]:
        """
        Determine whether an episode is eligible for replay.

        Parameters
        ----------
        episode_meta:
            Dictionary of episode-level metadata (length, decisions, etc.)

        Returns
        -------
        (eligible, reason)
        """

        length = int(episode_meta.get("length", 0))
        decisions = int(episode_meta.get("decision_count", 0))

        if length < min_length:
            return False, "episode_too_short"

        if decisions < min_decisions:
            return False, "insufficient_decisions"

        return True, "eligible"
