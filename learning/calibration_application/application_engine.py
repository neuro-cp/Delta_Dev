from typing import Dict
from .application_policy import CalibrationApplicationPolicy


class CalibrationApplicationEngine:
    '''
    Offline calibration application engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = CalibrationApplicationPolicy()

    def evaluate(
        self,
        *,
        proposed_adjustment: int = 0,
        allowed_adjustment: int = 0,
    ) -> Dict[str, object]:
        return self._policy.compute(
            proposed_adjustment=proposed_adjustment,
            allowed_adjustment=allowed_adjustment,
        )
