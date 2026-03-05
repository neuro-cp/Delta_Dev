import pytest

from integration.transformation.structured_signal import StructuredCognitiveSignal
from integration.substrate_surface.influence_packet_builder import InfluencePacketBuilder


def test_influence_packet_builder_respects_role():
    signal = StructuredCognitiveSignal(
        semantic_tokens=["alpha"],
        quantitative_fields={},
        role="simulation_evaluator",
        mode="active",
        confidence=1.0,
    )

    packets = InfluencePacketBuilder.build(signal, base_magnitude=1.0)

    targets = [p.target for p in packets]

    assert "VALUE_BIAS" in targets
    assert "PFC_CONTEXT_GAIN" not in targets


def test_zero_magnitude_produces_no_packets():
    signal = StructuredCognitiveSignal(
        semantic_tokens=["alpha"],
        quantitative_fields={},
        role="simulation_evaluator",
        mode="passive",
        confidence=0.0,
    )

    packets = InfluencePacketBuilder.build(signal, base_magnitude=1.0)

    assert packets == []


def test_influence_packet_is_immutable():
    signal = StructuredCognitiveSignal(
        semantic_tokens=["alpha"],
        quantitative_fields={},
        role="simulation_evaluator",
        mode="active",
        confidence=1.0,
    )

    packets = InfluencePacketBuilder.build(signal, base_magnitude=1.0)

    packet = packets[0]

    with pytest.raises(Exception):
        packet.magnitude = 0.0
