from learning.drive_bias.drive_bias_engine import DriveBiasEngine
from learning.drive_bias.drive_signal import DriveSignal
from learning.schemas.learning_proposal import LearningProposal


def test_drive_bias_scoring_consistency():
    engine = DriveBiasEngine()

    proposal = LearningProposal(
        proposal_id="p1",
        source_replay_id="r1",
        deltas=[type("D", (), {"target": "t1"})()],
        confidence=0.5,
        justification={},
        bounded=True,
        replay_consistent=True,
    )

    drive = DriveSignal("d1", 2.0, "test")

    scores = engine.compute([proposal], [drive])

    assert scores["p1"] == 1.0
