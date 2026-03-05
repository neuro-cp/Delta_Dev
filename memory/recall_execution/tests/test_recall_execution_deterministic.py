from memory.recall_execution.recall_execution_adapter import RecallExecutionAdapter
from memory.replay_recall.recall_bias_suggestion import RecallBiasSuggestion


def test_deterministic_behavior():
    adapter = RecallExecutionAdapter()

    suggestions = [
        RecallBiasSuggestion(semantic_id="sem:test", pressure=5.0)
    ]

    r1 = adapter.build_influences(suggestions)
    r2 = adapter.build_influences(suggestions)

    assert r1 == r2
