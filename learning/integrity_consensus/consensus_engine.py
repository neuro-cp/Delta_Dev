from typing import Dict
from .consensus_policy import ConsensusPolicy


class ConsensusEngine:
    '''
    Offline integrity consensus engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = ConsensusPolicy()

    def evaluate(
        self,
        *,
        escalation: Dict = None,
        oversight: Dict = None,
        calibration: Dict = None,
    ) -> Dict[str, object]:
        return self._policy.compute(
            escalation=escalation,
            oversight=oversight,
            calibration=calibration,
        )
