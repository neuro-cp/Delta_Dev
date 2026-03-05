from __future__ import annotations

from typing import Dict, Optional

from engine.sleep.orchestration.sleep_request import SleepRequest
from engine.sleep.orchestration.sleep_profile import SleepProfile
from engine.sleep.orchestration.sleep_decision import SleepDecision
from engine.sleep.orchestration.sleep_eligibility_policy import SleepEligibilityPolicy

from engine.inspection.diffing.diff_report import DiffReport


class SleepOrchestrator:
    """
    Policy-only orchestration layer for sleep/replay.

    This layer:
    - decides WHEN sleep is allowed
    - selects WHICH sleep profile to use
    - may consult inspection diffs (read-only)

    It does NOT execute replay or influence runtime.
    """

    def __init__(
        self,
        *,
        profiles: Dict[str, SleepProfile],
        min_interval: int = 100,
    ) -> None:
        self._profiles = profiles
        self._min_interval = min_interval

    def decide(
        self,
        *,
        request: SleepRequest,
        current_step: int,
        last_sleep_step: int | None,
        inspection_diff: Optional[DiffReport] = None,
    ) -> SleepDecision | None:
        """
        Decide whether to initiate sleep and which profile to use.

        inspection_diff is advisory only.
        """

        allowed, reason = SleepEligibilityPolicy.is_sleep_allowed(
            last_sleep_step=last_sleep_step,
            current_step=current_step,
            min_interval=self._min_interval,
        )

        if not allowed:
            return None

        # --------------------------------------------------
        # Base policy: trigger-driven profile selection
        # --------------------------------------------------
        if request.trigger.trigger_type in ("overload", "instability"):
            profile = self._profiles["nrem_heavy"]
        elif request.trigger.trigger_type == "circadian":
            profile = self._profiles["mixed"]
        else:
            profile = self._profiles["nap"]

        # --------------------------------------------------
        # Diff-informed bias (read-only, optional)
        # --------------------------------------------------
        if inspection_diff is not None:
            if inspection_diff.cognition_changed:
                # Prefer consolidation-friendly sleep if available
                if "nrem_heavy" in self._profiles:
                    profile = self._profiles["nrem_heavy"]

        return SleepDecision(
            profile_name=profile.name,
            selected_replay_modes=profile.allowed_replay_modes,
            episode_budget=profile.max_episodes,
            justification=(
                f"trigger={request.trigger.trigger_type}, "
                f"eligible={reason}, "
                f"cognition_changed="
                f"{inspection_diff.cognition_changed if inspection_diff else 'n/a'}"
            ),
        )
