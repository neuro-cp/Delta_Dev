from memory.replay_recall.replay_recall_pipeline import ReplayRecallPipeline
from memory.replay_recall.recall_query import RecallQuery


class FakeSemantic:
    semantic_id = "sem:test"
    recurrence_count = 3
    tags = {"regions": ["PFC"], "decision_present": True}


def test_recall_is_deterministic():
    pipeline = ReplayRecallPipeline()
    query = RecallQuery(active_regions={"PFC"}, decision_present=True)

    r1 = pipeline.run([FakeSemantic()], query)
    r2 = pipeline.run([FakeSemantic()], query)

    assert r1 == r2
