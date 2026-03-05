from typing import Dict
from .escalation_policy import EscalationPolicy


class EscalationEngine:
    '''
    Offline governance escalation engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = EscalationPolicy()

    def evaluate(self, *, integrity: Dict) -> Dict[str, object]:
        return self._policy.compute(integrity)
