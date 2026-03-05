from memory.influence_arbitration.arbitration_engine import ArbitrationEngine


def test_empty():
    engine = ArbitrationEngine()
    packet = engine.build_packet([])

    assert packet.targets == {}
