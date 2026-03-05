from typing import Dict
from .risk_policy import RiskPolicy


class RiskEngine:
    '''
    Offline risk surface engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = RiskPolicy()

    def evaluate(
        self,
        *,
        envelope: Dict = None,
        drift: Dict = None,
        escalation: Dict = None,
    ) -> Dict[str, object]:
        return self._policy.compute(
            envelope=envelope,
            drift=drift,
            escalation=escalation,
        )
