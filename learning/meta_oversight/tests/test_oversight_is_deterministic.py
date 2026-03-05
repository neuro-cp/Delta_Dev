from learning.meta_oversight.oversight_engine import OversightEngine

def test_oversight_is_deterministic():
    engine = OversightEngine()

    a = engine.evaluate(
        escalation={"pressure": 3},
        execution={"p1": 2},
        drive={"score": 1},
    )

    b = engine.evaluate(
        escalation={"pressure": 3},
        execution={"p1": 2},
        drive={"score": 1},
    )

    assert a == b
