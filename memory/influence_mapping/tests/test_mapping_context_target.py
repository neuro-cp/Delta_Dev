from memory.influence_mapping.influence_mapping_adapter import InfluenceMappingAdapter
from memory.recall_execution.recall_execution_result import RecallExecutionInfluence


def test_context_mapping():
    adapter = InfluenceMappingAdapter()

    influences = [
        RecallExecutionInfluence(semantic_id="sem:test", scaled_pressure=4.0)
    ]

    result = adapter.build_targets(influences)

    assert any(t.target_type == "PFC_CONTEXT_GAIN" for t in result)
