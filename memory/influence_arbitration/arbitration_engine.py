from typing import Iterable
from collections import defaultdict

from memory.influence_mapping.influence_target import InfluenceTarget

from .arbitration_policy import ArbitrationPolicy
from .influence_packet import InfluencePacket


class ArbitrationEngine:

    def build_packet(self, targets: Iterable[InfluenceTarget]) -> InfluencePacket:

        if not targets:
            return InfluencePacket(targets={})

        merged = defaultdict(float)

        # Merge same target types
        for t in targets:
            merged[t.target_type] += t.magnitude

        # Apply total clamp
        total = sum(merged.values())

        if total > ArbitrationPolicy.MAX_TOTAL_MAGNITUDE:
            scale = ArbitrationPolicy.MAX_TOTAL_MAGNITUDE / total
            for k in merged:
                merged[k] *= scale

        # Enforce deterministic ordering
        ordered = {
            k: merged[k]
            for k in ArbitrationPolicy.PRIORITY_ORDER
            if k in merged
        }

        return InfluencePacket(targets=ordered)
