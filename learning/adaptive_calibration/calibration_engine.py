from typing import Dict
from .calibration_policy import CalibrationPolicy


class CalibrationEngine:
    '''
    Offline adaptive calibration engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = CalibrationPolicy()

    def evaluate(
        self,
        *,
        stability: Dict = None,
        drift: Dict = None,
        escalation: Dict = None,
    ) -> Dict[str, object]:
        return self._policy.compute(
            stability=stability,
            drift=drift,
            escalation=escalation,
        )
