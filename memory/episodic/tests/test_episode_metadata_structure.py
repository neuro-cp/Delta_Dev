from memory.episodic.episode_structure import Episode


def test_episode_decision_metadata_and_duration():
    ep = Episode(
        episode_id=1,
        start_step=10,
        start_time=1.0,
    )

    # --------------------------------------------------
    # First decision anchors metadata
    # --------------------------------------------------
    ep.mark_decision(
        step=15,
        time=1.5,
        winner="D1",
        confidence=0.8,
    )

    assert ep.decision_count == 1
    assert ep.winner == "D1"
    assert ep.confidence == 0.8

    # --------------------------------------------------
    # Second decision appends only
    # --------------------------------------------------
    ep.mark_decision(
        step=20,
        time=2.0,
        winner="D2",          # should NOT overwrite
        confidence=0.3,
    )

    assert ep.decision_count == 2
    assert ep.winner == "D1"
    assert ep.confidence == 0.8

    # --------------------------------------------------
    # Close episode
    # --------------------------------------------------
    ep.close(
        step=30,
        time=3.0,
    )

    assert ep.closed is True
    assert ep.duration_steps == 20
    assert ep.duration_time == 2.0
