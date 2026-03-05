from learning.fragility_index.fragility_engine import FragilityEngine

def test_fragility_calculation_logic():
    engine = FragilityEngine()

    result = engine.evaluate(
        coherence={"coherence_index": 0},
        entropy={"entropy_index": 2.0},
        momentum={"momentum_index": 1},
        escalation={"pressure": 3},
    )

    assert result["fragility_index"] == 6.0
