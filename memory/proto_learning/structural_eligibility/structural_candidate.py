from __future__ import annotations
from dataclasses import dataclass
from memory.proto_structural.episode_signature import EpisodeSignature

@dataclass(frozen=True)
class StructuralCandidate:
    signature: EpisodeSignature
    occurrences: int
    relative_frequency: float
    confidence_score: float
