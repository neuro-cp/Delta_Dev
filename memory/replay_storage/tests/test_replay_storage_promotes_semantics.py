from memory.replay_storage.replay_storage_pipeline import ReplayStoragePipeline


class DummyBundle:
    replay_id = "demo"


def test_replay_storage_promotes_semantics():
    pipeline = ReplayStoragePipeline(replay_id="demo")
    bundle = DummyBundle()

    result = pipeline.run([bundle])

    assert isinstance(result.promoted_semantic_ids, list)
