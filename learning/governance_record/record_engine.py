from typing import Dict
from .record_policy import GovernanceRecordPolicy


class GovernanceRecordEngine:
    '''
    Offline governance record engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def __init__(self):
        self._policy = GovernanceRecordPolicy()

    def evaluate(
        self,
        *,
        fragility: Dict = None,
        envelope: Dict = None,
        application: Dict = None,
    ) -> Dict[str, object]:
        return self._policy.compute(
            fragility=fragility,
            envelope=envelope,
            application=application,
        )
