from typing import Dict
from .gate_policy import GovernanceGatePolicy


class GovernanceGateEngine:
    '''
    Offline governance gate engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = GovernanceGatePolicy()

    def evaluate(self, *, record: Dict = None) -> Dict[str, object]:
        return self._policy.compute(record)
