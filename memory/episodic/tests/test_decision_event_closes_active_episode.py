def test_decision_event_closes_active_episode():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    policy = EpisodePolicy()
    hook = EpisodeRuntimeHook(policy=policy, tracker=tracker)

    # Step 0: implicit episode start
    hook.step(
        step=0,
        decision_event=False,
        context_shift=False,
    )

    assert tracker.active_episode() is not None
    assert tracker.episode_count() == 1

    # Step 5: decision event
    hook.step(
        step=5,
        decision_event=True,
        context_shift=False,
    )

    # Episode should now be closed
    assert tracker.active_episode() is None
    assert tracker.episode_count() == 1

    ep = tracker.last_episode()
    assert ep is not None
    assert ep.closed is True
    assert ep.start_step == 0
    assert ep.decision_step == 5

    # Trace should show start then close
    records = trace.records()
    assert len(records) == 2

    start_rec, close_rec = records
    assert start_rec.event == "start"
    assert close_rec.event == "close"
    assert close_rec.duration == 5
