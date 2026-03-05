from typing import Dict, List
from learning.schemas.learning_proposal import LearningProposal
from .drive_signal import DriveSignal
from .drive_bias_policy import DriveBiasPolicy


class DriveBiasEngine:
    """Computes advisory bias scores without mutation."""

    def __init__(self) -> None:
        self._policy = DriveBiasPolicy()

    def compute(
        self,
        proposals: List[LearningProposal],
        drives: List[DriveSignal],
    ) -> Dict[str, float]:

        scores: Dict[str, float] = {}

        for proposal in proposals:
            total = 0.0
            for drive in drives:
                total += self._policy.score(proposal, drive)
            scores[proposal.proposal_id] = total

        return scores
