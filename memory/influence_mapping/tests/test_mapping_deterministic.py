from memory.influence_mapping.influence_mapping_adapter import InfluenceMappingAdapter
from memory.recall_execution.recall_execution_result import RecallExecutionInfluence


def test_deterministic():
    adapter = InfluenceMappingAdapter()

    influences = [
        RecallExecutionInfluence(semantic_id="sem:test", scaled_pressure=3.0)
    ]

    r1 = adapter.build_targets(influences)
    r2 = adapter.build_targets(influences)

    assert r1 == r2
