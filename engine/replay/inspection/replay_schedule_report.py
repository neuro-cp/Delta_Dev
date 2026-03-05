from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from engine.replay.scheduling.replay_plan import ReplayPlan


@dataclass(frozen=True)
class ReplayScheduleReport:
    """
    Human-facing inspection artifact for replay scheduling.

    This report exists to answer:
    - Why was replay requested?
    - Why was it admitted?
    - What was selected?
    - What was excluded?

    It is:
    - Descriptive only
    - Non-authoritative
    - Safe to delete and regenerate
    """

    request_reason: str
    requested_step: int | None

    selected_episode_ids: List[str]
    excluded_episode_ids: List[str]

    eligibility_reasons: Dict[str, str]

    @staticmethod
    def from_plan(plan: ReplayPlan) -> "ReplayScheduleReport":
        selected = set(plan.selected_episode_ids)
        all_ids = set(plan.eligibility_reasons.keys())
        excluded = sorted(all_ids - selected)

        return ReplayScheduleReport(
            request_reason=plan.request.reason,
            requested_step=plan.request.requested_step,
            selected_episode_ids=list(plan.selected_episode_ids),
            excluded_episode_ids=excluded,
            eligibility_reasons=dict(plan.eligibility_reasons),
        )
