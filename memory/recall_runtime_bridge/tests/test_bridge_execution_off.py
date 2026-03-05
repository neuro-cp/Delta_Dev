from memory.recall_runtime_bridge.recall_runtime_adapter import RecallRuntimeAdapter
from memory.influence_arbitration.influence_packet import InfluencePacket

class DummyGate:
    def apply(self, target, value, identity):
        return identity  # always identity

def test_execution_off():
    adapter = RecallRuntimeAdapter()
    packet = InfluencePacket(targets={"VALUE_BIAS": 5.0})

    result = adapter.apply_packet(packet, DummyGate(), {"VALUE_BIAS": 0.0})

    assert result.applied_targets["VALUE_BIAS"] == 0.0
