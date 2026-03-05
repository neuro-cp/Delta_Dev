from memory.influence_arbitration.arbitration_engine import ArbitrationEngine
from memory.influence_mapping.influence_target import InfluenceTarget


def test_clamp():
    engine = ArbitrationEngine()

    targets = [
        InfluenceTarget("VALUE_BIAS", 10.0),
        InfluenceTarget("PFC_CONTEXT_GAIN", 10.0),
    ]

    packet = engine.build_packet(targets)

    assert sum(packet.targets.values()) <= 8.0
