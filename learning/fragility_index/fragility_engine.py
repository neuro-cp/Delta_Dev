from typing import Dict
from .fragility_policy import FragilityPolicy


class FragilityEngine:
    '''
    Offline fragility engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = FragilityPolicy()

    def evaluate(
        self,
        *,
        coherence: Dict = None,
        entropy: Dict = None,
        momentum: Dict = None,
        escalation: Dict = None,
    ) -> Dict[str, object]:
        return self._policy.compute(
            coherence=coherence,
            entropy=entropy,
            momentum=momentum,
            escalation=escalation,
        )
