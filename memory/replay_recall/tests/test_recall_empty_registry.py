from memory.replay_recall.replay_recall_pipeline import ReplayRecallPipeline
from memory.replay_recall.recall_query import RecallQuery


def test_recall_empty_registry():
    pipeline = ReplayRecallPipeline()
    query = RecallQuery(active_regions=set(), decision_present=False)

    result = pipeline.run([], query)

    assert result == []
