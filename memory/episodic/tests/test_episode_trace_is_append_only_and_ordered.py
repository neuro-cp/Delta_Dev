def test_episode_trace_is_append_only_and_ordered():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    policy = EpisodePolicy(max_steps_without_decision=1)
    hook = EpisodeRuntimeHook(policy=policy, tracker=tracker)

    # Generate two episodes via timeout rollover
    hook.step(step=0, decision_event=False, context_shift=False)
    hook.step(step=1, decision_event=False, context_shift=False)

    records_1 = trace.records()
    assert len(records_1) == 3  # start, close, start

    # Attempt to mutate the returned list
    records_1.pop()

    # Re-fetch records; internal trace must be unchanged
    records_2 = trace.records()
    assert len(records_2) == 3

    # Verify ordering
    assert records_2[0].event == "start"
    assert records_2[1].event == "close"
    assert records_2[2].event == "start"

    # Verify immutability (dataclass frozen)
    rec = records_2[0]
    try:
        rec.event = "mutated"
        assert False, "EpisodeTraceRecord should be immutable"
    except Exception:
        pass

