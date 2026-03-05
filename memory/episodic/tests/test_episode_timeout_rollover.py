def test_episode_timeout_rollover():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    policy = EpisodePolicy(
        max_steps_without_decision=3,
        allow_decisionless_episodes=True,
    )
    hook = EpisodeRuntimeHook(policy=policy, tracker=tracker)

    # Step 0: start first episode
    hook.step(step=0, decision_event=False, context_shift=False)
    assert tracker.episode_count() == 1
    assert tracker.active_episode() is not None

    # Step 3: timeout reached → rollover
    hook.step(step=3, decision_event=False, context_shift=False)

    # Should now have two episodes
    assert tracker.episode_count() == 2

    first, second = tracker.all_episodes()
    assert first.closed is True
    assert second.is_active()

    assert first.start_step == 0
    assert second.start_step == 3

    # Trace: start → close → start
    records = trace.records()
    assert len(records) == 3

    assert records[0].event == "start"
    assert records[1].event == "close"
    assert records[2].event == "start"
