from learning.meta_oversight.oversight_engine import OversightEngine

def test_oversight_empty_inputs():
    engine = OversightEngine()

    result = engine.evaluate()

    assert result["aggregate_index"] == 0
