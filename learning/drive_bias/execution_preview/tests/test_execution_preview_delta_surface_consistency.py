from learning.drive_bias.execution_preview.execution_preview_engine import ExecutionPreviewEngine
from learning.schemas.learning_proposal import LearningProposal

def test_execution_preview_delta_surface_consistency():
    engine = ExecutionPreviewEngine()

    p = LearningProposal(
        proposal_id="p1",
        source_replay_id="r1",
        deltas=[object(), object()],
        confidence=1.0,
        justification={},
        bounded=True,
        replay_consistent=True,
    )

    result = engine.preview(proposals=[p], promotable_ids=["p1"])
    assert result["p1"] == 2
