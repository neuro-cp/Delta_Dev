from memory.influence_arbitration.arbitration_engine import ArbitrationEngine
from memory.influence_mapping.influence_target import InfluenceTarget


def test_deterministic():
    engine = ArbitrationEngine()

    targets = [
        InfluenceTarget("VALUE_BIAS", 2.0),
        InfluenceTarget("PFC_CONTEXT_GAIN", 1.0),
    ]

    p1 = engine.build_packet(targets)
    p2 = engine.build_packet(targets)

    assert p1 == p2
