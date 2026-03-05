from typing import List, Dict
from .drift_policy import DriftPolicy


class DriftEngine:
    '''
    Offline drift monitoring engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = DriftPolicy()

    def evaluate(self, *, stability_history: List[Dict]) -> Dict[str, object]:
        return self._policy.compute(stability_history)
