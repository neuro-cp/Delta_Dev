from typing import Dict
from .envelope_policy import ContainmentEnvelopePolicy


class ContainmentEnvelopeEngine:
    '''
    Offline containment envelope engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = ContainmentEnvelopePolicy()

    def evaluate(
        self,
        *,
        fragility: Dict = None,
        max_adjustment: int = 10,
    ) -> Dict[str, object]:
        return self._policy.compute(
            fragility=fragility,
            max_adjustment=max_adjustment,
        )
