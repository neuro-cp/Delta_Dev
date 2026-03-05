from typing import Dict
from learning.schemas.learning_proposal import LearningProposal
from .drive_signal import DriveSignal


class DriveBiasPolicy:
    """Pure scoring policy. No mutation."""

    def score(
        self,
        proposal: LearningProposal,
        drive: DriveSignal,
    ) -> float:
        # Simple deterministic bias function
        return proposal.confidence * drive.magnitude
