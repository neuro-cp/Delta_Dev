from memory.recall_runtime_bridge.recall_runtime_adapter import RecallRuntimeAdapter
from memory.influence_arbitration.influence_packet import InfluencePacket

class DummyGate:
    def apply(self, target, value, identity):
        return value

def test_deterministic():
    adapter = RecallRuntimeAdapter()
    packet = InfluencePacket(targets={"VALUE_BIAS": 4.0})

    r1 = adapter.apply_packet(packet, DummyGate(), {"VALUE_BIAS": 0.0})
    r2 = adapter.apply_packet(packet, DummyGate(), {"VALUE_BIAS": 0.0})

    assert r1 == r2
