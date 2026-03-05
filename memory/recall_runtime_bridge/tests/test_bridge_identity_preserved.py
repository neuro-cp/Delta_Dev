from memory.recall_runtime_bridge.recall_runtime_adapter import RecallRuntimeAdapter
from memory.influence_arbitration.influence_packet import InfluencePacket

class DummyGate:
    def apply(self, target, value, identity):
        return identity

def test_identity_preserved():
    adapter = RecallRuntimeAdapter()
    packet = InfluencePacket(targets={"VALUE_BIAS": 3.0})

    result = adapter.apply_packet(packet, DummyGate(), {"VALUE_BIAS": 2.0})

    assert result.applied_targets["VALUE_BIAS"] == 2.0
