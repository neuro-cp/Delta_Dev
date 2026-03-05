from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from engine.replay.requests.replay_request import ReplayRequest


@dataclass(frozen=True)
class ReplayPlan:
    """
    Immutable replay plan.

    A ReplayPlan describes WHICH episodes were selected for replay
    in response to a ReplayRequest, and WHY.

    This object:
    - Has no authority
    - Does not execute replay
    - Does not imply consolidation
    - Is safe to discard and recompute
    """

    # Originating request (reason, step, urgency)
    request: ReplayRequest

    # Ordered episode IDs selected for replay
    selected_episode_ids: List[str]

    # Eligibility outcomes for all considered episodes
    # (episode_id -> eligibility reason)
    eligibility_reasons: Dict[str, str] = field(default_factory=dict)

    # Optional scheduler metadata (versioning, seed, notes)
    scheduler_metadata: Dict[str, str] = field(default_factory=dict)
