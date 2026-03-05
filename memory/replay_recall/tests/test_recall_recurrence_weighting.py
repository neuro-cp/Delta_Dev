from memory.replay_recall.replay_recall_pipeline import ReplayRecallPipeline
from memory.replay_recall.recall_query import RecallQuery


class FakeSemantic:
    semantic_id = "sem:test"
    recurrence_count = 5
    tags = {"regions": ["PFC"], "decision_present": False}


def test_recall_recurrence_weighting():
    pipeline = ReplayRecallPipeline()

    query = RecallQuery(active_regions={"PFC"}, decision_present=False)

    result = pipeline.run([FakeSemantic()], query)

    assert result[0].pressure == 10.0
