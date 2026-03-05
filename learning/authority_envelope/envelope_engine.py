from typing import Dict
from .envelope_policy import EnvelopePolicy


class EnvelopeEngine:
    '''
    Offline authority envelope engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = EnvelopePolicy()

    def evaluate(
        self,
        *,
        consensus: Dict = None,
        escalation: Dict = None,
        calibration: Dict = None,
    ) -> Dict[str, object]:
        return self._policy.compute(
            consensus=consensus,
            escalation=escalation,
            calibration=calibration,
        )
