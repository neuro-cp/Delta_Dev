from pathlib import Path


BASE = Path("integration/tests/substrate_surface")
BASE.mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str):
    path.write_text(content.strip() + "\n", encoding="utf-8")


# ------------------------------
# __init__.py
# ------------------------------

write_file(BASE / "__init__.py", "")


# ------------------------------
# test_role_matrix.py
# ------------------------------

write_file(
    BASE / "test_role_matrix.py",
    """
from integration.substrate_surface.role_matrix import RoleMatrix


def test_role_matrix_restricts_targets():
    targets = RoleMatrix.allowed_targets("simulation_evaluator")

    assert "VALUE_BIAS" in targets
    assert "PFC_CONTEXT_GAIN" not in targets
"""
)


# ------------------------------
# test_mode_behavior_policy.py
# ------------------------------

write_file(
    BASE / "test_mode_behavior_policy.py",
    """
from integration.substrate_surface.mode_behavior_policy import ModeBehaviorPolicy


def test_mode_clamps_magnitude():
    magnitude = 0.9

    clamped = ModeBehaviorPolicy.apply("passive", magnitude)

    assert clamped == 0.25
"""
)


# ------------------------------
# test_confidence_weighting_policy.py
# ------------------------------

write_file(
    BASE / "test_confidence_weighting_policy.py",
    """
from integration.substrate_surface.confidence_weighting_policy import ConfidenceWeightingPolicy


def test_confidence_attenuates():
    magnitude = 1.0
    confidence = 0.5

    adjusted = ConfidenceWeightingPolicy.apply(magnitude, confidence)

    assert adjusted == 0.5


def test_confidence_never_amplifies():
    magnitude = 0.6
    confidence = 1.5  # should be clamped

    adjusted = ConfidenceWeightingPolicy.apply(magnitude, confidence)

    assert adjusted <= magnitude
"""
)


# ------------------------------
# test_influence_packet_builder.py
# ------------------------------

write_file(
    BASE / "test_influence_packet_builder.py",
    """
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
"""
)

print("Substrate surface tests installed successfully.")