from memory.replay_storage.replay_storage_pipeline import ReplayStoragePipeline


class DummyBundle:
    replay_id = "demo"


def test_replay_storage_is_deterministic():
    pipeline = ReplayStoragePipeline(replay_id="demo")
    bundle = DummyBundle()

    result1 = pipeline.run([bundle])
    result2 = pipeline.run([bundle])

    assert result1.promoted_semantic_ids == result2.promoted_semantic_ids
