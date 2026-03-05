from learning.meta_oversight.oversight_engine import OversightEngine

def test_oversight_aggregation_consistency():
    engine = OversightEngine()

    result = engine.evaluate(
        escalation={"pressure": 5},
        execution={"p1": 2, "p2": 3},
        drive={"score": 4},
    )

    assert result["aggregate_index"] == 14
