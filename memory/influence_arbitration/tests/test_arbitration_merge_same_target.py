from memory.influence_arbitration.arbitration_engine import ArbitrationEngine
from memory.influence_mapping.influence_target import InfluenceTarget


def test_merge():
    engine = ArbitrationEngine()

    targets = [
        InfluenceTarget("VALUE_BIAS", 2.0),
        InfluenceTarget("VALUE_BIAS", 3.0),
    ]

    packet = engine.build_packet(targets)

    assert packet.targets["VALUE_BIAS"] == 5.0
