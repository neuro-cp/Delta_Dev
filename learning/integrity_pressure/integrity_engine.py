from typing import Dict
from .integrity_policy import IntegrityPolicy


class IntegrityEngine:
    '''
    Offline integrity pressure engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = IntegrityPolicy()

    def evaluate(self, *, stability: Dict, drift: Dict) -> Dict[str, object]:
        return self._policy.compute(stability=stability, drift=drift)
