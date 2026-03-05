from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from engine.replay.scheduling.replay_plan import ReplayPlan


@dataclass(frozen=True)
class ReplayPlanDiff:
    """
    Descriptive diff between two ReplayPlans.

    Answers:
    - Did the selected episodes change?
    - Did ordering change?
    - Did eligibility reasons change?

    No policy. No interpretation.
    """

    same_selection: bool
    same_ordering: bool

    added_episode_ids: List[str]
    removed_episode_ids: List[str]

    eligibility_reason_changes: Dict[str, Dict[str, str]]


def diff_replay_plans(
    a: ReplayPlan,
    b: ReplayPlan,
) -> ReplayPlanDiff:
    a_sel = list(a.selected_episode_ids)
    b_sel = list(b.selected_episode_ids)

    a_set = set(a_sel)
    b_set = set(b_sel)

    added = sorted(b_set - a_set)
    removed = sorted(a_set - b_set)

    same_selection = a_set == b_set
    same_ordering = a_sel == b_sel

    reason_changes: Dict[str, Dict[str, str]] = {}

    all_ids = set(a.eligibility_reasons.keys()) | set(b.eligibility_reasons.keys())
    for eid in all_ids:
        ra = a.eligibility_reasons.get(eid)
        rb = b.eligibility_reasons.get(eid)
        if ra != rb:
            reason_changes[eid] = {
                "before": ra,
                "after": rb,
            }

    return ReplayPlanDiff(
        same_selection=same_selection,
        same_ordering=same_ordering,
        added_episode_ids=added,
        removed_episode_ids=removed,
        eligibility_reason_changes=reason_changes,
    )
