from __future__ import annotations

from typing import Dict, List

from engine.replay.requests.replay_request import ReplayRequest
from engine.replay.scheduling.replay_eligibility_policy import ReplayEligibilityPolicy
from engine.replay.scheduling.replay_plan import ReplayPlan


class ReplayScheduler:
    """
    Deterministic replay scheduler.

    Given:
    - A ReplayRequest
    - Episode metadata

    Produces:
    - A ReplayPlan (or rejection)

    This scheduler:
    - Selects WHICH episodes may be replayed
    - Enforces scarcity and ordering
    - Is fully inspectable and reproducible

    It does NOT:
    - Execute replay
    - Choose replay mode (REM/NREM/etc)
    - Influence runtime or memory
    """

    def __init__(
        self,
        *,
        max_episodes: int = 5,
    ) -> None:
        self._max_episodes = max_episodes

    def schedule(
        self,
        request: ReplayRequest,
        episodes_meta: Dict[str, Dict[str, float]],
    ) -> ReplayPlan:
        """
        Construct a replay plan in response to a replay request.
        """

        eligible: List[str] = []
        reasons: Dict[str, str] = {}

        # --------------------------------------------------
        # Eligibility filtering (pure, deterministic)
        # --------------------------------------------------
        for episode_id, meta in episodes_meta.items():
            ok, reason = ReplayEligibilityPolicy.is_episode_eligible(
                meta,
                min_length=2,  # exclude trivial 1-step episodes
            )
            if ok:
                eligible.append(episode_id)
            reasons[episode_id] = reason

        # --------------------------------------------------
        # Deterministic ordering: newest episodes first
        # --------------------------------------------------
        eligible_sorted = sorted(
            eligible,
            key=lambda eid: episodes_meta[eid].get("end_step", 0),
            reverse=True,
        )

        selected = eligible_sorted[: self._max_episodes]

        # --------------------------------------------------
        # Immutable replay plan
        # --------------------------------------------------
        return ReplayPlan(
            request=request,
            selected_episode_ids=selected,
            eligibility_reasons=reasons,
        )
