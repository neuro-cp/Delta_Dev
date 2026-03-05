from memory.working_memory.working_memory_trace import WorkingMemoryTrace


def test_trace_records_events() -> None:
    trace = WorkingMemoryTrace()

    trace.record(step=1, event="insert", payload={"key": "a"})
    trace.record(step=2, event="evict", payload={"key": "a"})

    records = trace.records()
    assert len(records) == 2
    assert records[0].event == "insert"
    assert records[1].event == "evict"
