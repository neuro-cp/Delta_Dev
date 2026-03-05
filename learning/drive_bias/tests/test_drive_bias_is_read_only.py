from learning.drive_bias.drive_bias_engine import DriveBiasEngine
from learning.drive_bias.drive_signal import DriveSignal
from learning.schemas.learning_proposal import LearningProposal


def test_drive_bias_is_read_only():
    engine = DriveBiasEngine()

    proposal = LearningProposal(
        proposal_id="p1",
        source_replay_id="r1",
        deltas=[type("D", (), {"target": "t1"})()],
        confidence=1.0,
        justification={},
        bounded=True,
        replay_consistent=True,
    )

    drive = DriveSignal("d1", 1.0, "test")

    before = proposal.confidence
    engine.compute([proposal], [drive])
    after = proposal.confidence

    assert before == after
