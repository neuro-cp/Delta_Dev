from memory.recall_execution.recall_execution_adapter import RecallExecutionAdapter


def test_empty_input_returns_empty():
    adapter = RecallExecutionAdapter()
    result = adapter.build_influences([])

    assert result == []
