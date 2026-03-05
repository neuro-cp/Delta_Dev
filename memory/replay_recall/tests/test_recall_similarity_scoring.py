from memory.replay_recall.replay_recall_pipeline import ReplayRecallPipeline
from memory.replay_recall.recall_query import RecallQuery


class FakeSemantic:
    semantic_id = "sem:test"
    recurrence_count = 1
    tags = {"regions": ["PFC"], "decision_present": True}


def test_recall_similarity_scoring():
    pipeline = ReplayRecallPipeline()

    query = RecallQuery(active_regions={"PFC"}, decision_present=True)

    result = pipeline.run([FakeSemantic()], query)

    assert len(result) == 1
    assert result[0].pressure > 0
