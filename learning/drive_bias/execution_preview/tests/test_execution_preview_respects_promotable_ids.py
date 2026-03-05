from learning.drive_bias.execution_preview.execution_preview_engine import ExecutionPreviewEngine
from learning.schemas.learning_proposal import LearningProposal

def test_execution_preview_respects_promotable_ids():
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

    result = engine.preview(proposals=[p], promotable_ids=[])
    assert result == {}
