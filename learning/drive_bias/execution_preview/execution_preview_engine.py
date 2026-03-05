from typing import Iterable, List, Dict
from learning.schemas.learning_proposal import LearningProposal
from .execution_preview_policy import ExecutionPreviewPolicy

class ExecutionPreviewEngine:
    '''
    Offline execution preview engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def __init__(self):
        self._policy = ExecutionPreviewPolicy()

    def preview(
        self,
        *,
        proposals: Iterable[LearningProposal],
        promotable_ids: Iterable[str],
    ) -> Dict[str, int]:

        return self._policy.compute_surface(
            proposals=list(proposals),
            promotable_ids=list(promotable_ids),
        )
