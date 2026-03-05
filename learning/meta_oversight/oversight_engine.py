from typing import Dict
from .oversight_policy import OversightPolicy


class OversightEngine:
    '''
    Offline meta oversight engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = OversightPolicy()

    def evaluate(
        self,
        *,
        escalation: Dict = None,
        execution: Dict = None,
        drive: Dict = None,
    ) -> Dict[str, object]:
        return self._policy.compute(
            escalation=escalation,
            execution=execution,
            drive=drive,
        )
