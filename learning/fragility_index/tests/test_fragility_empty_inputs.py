from learning.fragility_index.fragility_engine import FragilityEngine

def test_fragility_empty_inputs():
    engine = FragilityEngine()

    result = engine.evaluate()

    assert result["fragility_index"] == 0
