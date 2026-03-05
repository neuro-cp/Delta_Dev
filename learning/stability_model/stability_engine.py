from typing import List, Dict
from .stability_policy import StabilityPolicy


class StabilityEngine:
    '''
    Offline stability modeling engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = StabilityPolicy()

    def evaluate(self, *, evaluation_history: List[Dict]) -> Dict[str, object]:
        return self._policy.compute(evaluation_history)
