from typing import Iterable, List

from memory.recall_execution.recall_execution_result import (
    RecallExecutionInfluence,
)

from .influence_target import InfluenceTarget
from .influence_mapping_policy import InfluenceMappingPolicy


class InfluenceMappingAdapter:

    def build_targets(
        self,
        influences: Iterable[RecallExecutionInfluence],
    ) -> List[InfluenceTarget]:

        targets = []

        for influence in influences:
            value_mag = influence.scaled_pressure * InfluenceMappingPolicy.VALUE_SCALE
            context_mag = influence.scaled_pressure * InfluenceMappingPolicy.CONTEXT_SCALE

            if value_mag > InfluenceMappingPolicy.MAX_MAGNITUDE:
                value_mag = InfluenceMappingPolicy.MAX_MAGNITUDE

            if context_mag > InfluenceMappingPolicy.MAX_MAGNITUDE:
                context_mag = InfluenceMappingPolicy.MAX_MAGNITUDE

            targets.append(
                InfluenceTarget(
                    target_type="VALUE_BIAS",
                    magnitude=value_mag,
                )
            )

            targets.append(
                InfluenceTarget(
                    target_type="PFC_CONTEXT_GAIN",
                    magnitude=context_mag,
                )
            )

        return sorted(targets, key=lambda t: t.magnitude, reverse=True)
