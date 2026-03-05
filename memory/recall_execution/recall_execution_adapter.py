from typing import Iterable, List

from memory.replay_recall.recall_bias_suggestion import RecallBiasSuggestion

from .recall_execution_policy import RecallExecutionPolicy
from .recall_execution_result import RecallExecutionInfluence


class RecallExecutionAdapter:

    def build_influences(
        self,
        suggestions: Iterable[RecallBiasSuggestion],
    ) -> List[RecallExecutionInfluence]:

        influences = []

        for suggestion in suggestions:
            scaled = suggestion.pressure * RecallExecutionPolicy.SCALING_FACTOR

            if scaled > RecallExecutionPolicy.MAX_PRESSURE:
                scaled = RecallExecutionPolicy.MAX_PRESSURE

            influences.append(
                RecallExecutionInfluence(
                    semantic_id=suggestion.semantic_id,
                    scaled_pressure=scaled,
                )
            )

        return sorted(
            influences,
            key=lambda i: i.scaled_pressure,
            reverse=True,
        )
