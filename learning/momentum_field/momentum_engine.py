from typing import List, Dict
from .momentum_policy import MomentumPolicy


class MomentumEngine:
    '''
    Offline structural momentum engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = MomentumPolicy()

    def evaluate(self, *, stability_history: List[Dict] = None) -> Dict[str, object]:
        return self._policy.compute(stability_history)
