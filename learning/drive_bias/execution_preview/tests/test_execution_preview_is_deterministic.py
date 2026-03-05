from learning.drive_bias.execution_preview.execution_preview_engine import ExecutionPreviewEngine
from learning.schemas.learning_proposal import LearningProposal

def test_execution_preview_is_deterministic():
    engine = ExecutionPreviewEngine()

    p = LearningProposal(
        proposal_id="p1",
        source_replay_id="r1",
        deltas=[],
        confidence=1.0,
        justification={},
        bounded=True,
        replay_consistent=True,
    )

    a = engine.preview(proposals=[p], promotable_ids=["p1"])
    b = engine.preview(proposals=[p], promotable_ids=["p1"])

    assert a == b
