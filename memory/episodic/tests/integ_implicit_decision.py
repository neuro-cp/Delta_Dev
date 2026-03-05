def test_implicit_episode_on_decision():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    policy = EpisodePolicy()
    hook = EpisodeRuntimeHook(policy=policy, tracker=tracker)

    # Step 10: decision occurs with no active episode
    hook.step(
        step=10,
        decision_event=True,
        context_shift=False,
    )

    assert tracker.episode_count() == 1
    ep = tracker.active_episode()
    assert ep is not None
    assert ep.start_step == 10
    assert ep.has_decision()
    assert ep.decision_step == 10

    records = trace.records()
    assert len(records) == 1
    assert records[0].event == "start"
    assert records[0].step == 10
