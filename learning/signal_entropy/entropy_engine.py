from typing import Dict
from .entropy_policy import EntropyPolicy


class EntropyEngine:
    '''
    Offline signal entropy engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = EntropyPolicy()

    def evaluate(self, *, signals: Dict = None) -> Dict[str, object]:
        return self._policy.compute(signals)
