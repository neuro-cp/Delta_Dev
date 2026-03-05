from typing import Iterable, Dict, List
from learning.schemas.learning_proposal import LearningProposal
from .cognitive_evaluation_policy import CognitiveEvaluationPolicy


class CognitiveEvaluationEngine:
    '''
    Offline cognitive evaluation engine.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    - No runtime access
    '''

    def __init__(self):
        self._policy = CognitiveEvaluationPolicy()

    def evaluate(
        self,
        *,
        proposals: Iterable[LearningProposal],
        bias_scores: Dict[str, float],
        selected_ids: List[str],
        promotable_ids: List[str],
        delta_surface: Dict[str, int],
    ) -> Dict[str, object]:

        return self._policy.integrate(
            proposals=list(proposals),
            bias_scores=bias_scores,
            selected_ids=list(selected_ids),
            promotable_ids=list(promotable_ids),
            delta_surface=dict(delta_surface),
        )
