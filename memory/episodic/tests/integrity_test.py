def test_episode_starts_when_none_active():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    policy = EpisodePolicy()
    hook = EpisodeRuntimeHook(policy=policy, tracker=tracker)

    # Step 0: no episode exists yet
    signal = hook.step(
        step=0,
        decision_event=False,
        context_shift=False,
    )

    # Episode should now exist
    assert tracker.episode_count() == 1
    ep = tracker.active_episode()
    assert ep is not None
    assert ep.start_step == 0
    assert ep.is_active()

    # Policy should have suggested a start
    assert signal is not None
    assert signal.start_new is True
    assert signal.close_active is False
    assert signal.reason == "no_active_episode"

    # Trace should record exactly one start
    records = trace.records()
    assert len(records) == 1
    rec = records[0]
    assert rec.event == "start"
    assert rec.step == 0
