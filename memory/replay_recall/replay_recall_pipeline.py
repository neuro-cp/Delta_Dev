from typing import Iterable, List

from .recall_matcher import RecallMatcher
from .recall_weighting import RecallWeighting
from .recall_bias_suggestion import RecallBiasSuggestion


class ReplayRecallPipeline:

    def run(self, registry: Iterable, query) -> List[RecallBiasSuggestion]:

        suggestions = []

        for semantic in registry:
            similarity = RecallMatcher.similarity(query, semantic)

            if similarity <= 0:
                continue

            pressure = RecallWeighting.weight(
                similarity=similarity,
                recurrence_count=semantic.recurrence_count,
            )

            suggestions.append(
                RecallBiasSuggestion(
                    semantic_id=semantic.semantic_id,
                    pressure=pressure,
                )
            )

        return sorted(
            suggestions,
            key=lambda s: s.pressure,
            reverse=True,
        )
