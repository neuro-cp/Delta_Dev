from memory.recall_execution.recall_execution_adapter import RecallExecutionAdapter
from memory.replay_recall.recall_bias_suggestion import RecallBiasSuggestion


def test_pressure_maps_directly():
    adapter = RecallExecutionAdapter()

    suggestions = [
        RecallBiasSuggestion(semantic_id="sem:test", pressure=3.0)
    ]

    result = adapter.build_influences(suggestions)

    assert result[0].scaled_pressure == 3.0
