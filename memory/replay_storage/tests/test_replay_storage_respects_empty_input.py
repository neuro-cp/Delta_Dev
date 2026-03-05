from memory.replay_storage.replay_storage_pipeline import ReplayStoragePipeline


def test_replay_storage_respects_empty_input():
    pipeline = ReplayStoragePipeline(replay_id="demo")
    result = pipeline.run([])

    assert result.registry_size == 0
