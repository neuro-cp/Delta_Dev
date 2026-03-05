from memory.influence_arbitration.arbitration_engine import ArbitrationEngine
from memory.influence_mapping.influence_target import InfluenceTarget


def test_priority_order():
    engine = ArbitrationEngine()

    targets = [
        InfluenceTarget("PFC_CONTEXT_GAIN", 1.0),
        InfluenceTarget("VALUE_BIAS", 1.0),
    ]

    packet = engine.build_packet(targets)

    keys = list(packet.targets.keys())
    assert keys[0] == "VALUE_BIAS"
