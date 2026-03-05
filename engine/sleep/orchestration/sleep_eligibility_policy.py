from __future__ import annotations

from typing import Tuple


class SleepEligibilityPolicy:
    """
    Read-only policy deciding whether sleep is allowed.
    """

    @staticmethod
    def is_sleep_allowed(
        *,
        last_sleep_step: int | None,
        current_step: int,
        min_interval: int = 100,
    ) -> Tuple[bool, str]:
        """
        Determine if sleep is allowed at this time.
        """

        if last_sleep_step is None:
            return True, "no_prior_sleep"

        if current_step - last_sleep_step < min_interval:
            return False, "too_soon_since_last_sleep"

        return True, "eligible"
