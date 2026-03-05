from memory.influence_mapping.influence_mapping_adapter import InfluenceMappingAdapter
from memory.recall_execution.recall_execution_result import RecallExecutionInfluence


def test_clamping():
    adapter = InfluenceMappingAdapter()

    influences = [
        RecallExecutionInfluence(semantic_id="sem:test", scaled_pressure=100.0)
    ]

    result = adapter.build_targets(influences)

    assert all(t.magnitude <= 5.0 for t in result)
