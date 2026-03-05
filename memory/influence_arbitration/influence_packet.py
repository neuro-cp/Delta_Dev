from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class InfluencePacket:
    targets: Dict[str, float]
