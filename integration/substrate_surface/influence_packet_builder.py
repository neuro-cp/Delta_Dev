from dataclasses import dataclass
from typing import Optional

from integration.transformation.structured_signal import StructuredCognitiveSignal
from integration.substrate_surface.role_matrix import RoleMatrix
from integration.substrate_surface.mode_behavior_policy import ModeBehaviorPolicy
from integration.substrate_surface.confidence_weighting_policy import ConfidenceWeightingPolicy


@dataclass(frozen=True)
class InfluencePacket:
    target: str
    magnitude: float
    role: str
    mode: str
    confidence: Optional[float]
    advisory: bool = True


class InfluencePacketBuilder:
    """
    Pure advisory packet builder.

    Does not inject.
    Does not execute.
    Does not access runtime.
    """

    @staticmethod
    def build(signal: StructuredCognitiveSignal, base_magnitude: float) -> list[InfluencePacket]:
        allowed = RoleMatrix.allowed_targets(signal.role)

        packets = []

        for target in allowed:
            magnitude = base_magnitude

            magnitude = ModeBehaviorPolicy.apply(signal.mode, magnitude)
            magnitude = ConfidenceWeightingPolicy.apply(magnitude, signal.confidence)

            if magnitude > 0.0:
                packets.append(
                    InfluencePacket(
                        target=target,
                        magnitude=magnitude,
                        role=signal.role,
                        mode=signal.mode,
                        confidence=signal.confidence,
                    )
                )

        return packets
