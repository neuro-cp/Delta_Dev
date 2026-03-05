def test_context_shift_forces_episode_boundary():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    policy = EpisodePolicy()
    hook = EpisodeRuntimeHook(policy=policy, tracker=tracker)

    # Step 0: start episode
    hook.step(step=0, decision_event=False, context_shift=False)
    assert tracker.episode_count() == 1
    assert tracker.active_episode() is not None

    # Step 7: context shift
    hook.step(step=7, decision_event=False, context_shift=True)

    assert tracker.episode_count() == 2

    first, second = tracker.all_episodes()
    assert first.closed is True
    assert second.is_active()

    assert first.start_step == 0
    assert second.start_step == 7

    records = trace.records()
    assert len(records) == 3

    start0, close0, start1 = records
    assert start0.event == "start"
    assert close0.event == "close"
    assert close0.reason == "context_shift"
    assert start1.event == "start"
    assert start1.reason == "context_shift"
