from learning.fragility_index.fragility_engine import FragilityEngine

def test_fragility_is_deterministic():
    engine = FragilityEngine()

    a = engine.evaluate(
        coherence={"coherence_index": 0},
        entropy={"entropy_index": 2.0},
        momentum={"momentum_index": 1},
        escalation={"pressure": 3},
    )

    b = engine.evaluate(
        coherence={"coherence_index": 0},
        entropy={"entropy_index": 2.0},
        momentum={"momentum_index": 1},
        escalation={"pressure": 3},
    )

    assert a == b
