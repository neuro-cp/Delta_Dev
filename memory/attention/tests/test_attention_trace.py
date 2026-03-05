from memory.attention.attention_trace import AttentionTrace


def test_attention_trace_records() -> None:
    trace = AttentionTrace()

    trace.record(step=1, event="add", payload={"key": "a"})
    trace.record(step=2, event="decay", payload={"key": "a"})

    records = trace.records()
    assert len(records) == 2
    assert records[0].event == "add"
    assert records[1].event == "decay"
