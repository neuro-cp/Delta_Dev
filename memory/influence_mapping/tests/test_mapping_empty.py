from memory.influence_mapping.influence_mapping_adapter import InfluenceMappingAdapter


def test_empty_input():
    adapter = InfluenceMappingAdapter()
    result = adapter.build_targets([])

    assert result == []
