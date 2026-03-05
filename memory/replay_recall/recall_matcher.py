from typing import Dict


class RecallMatcher:

    @staticmethod
    def similarity(query, semantic) -> float:
        region_overlap = len(query.active_regions.intersection(
            set(semantic.tags.get("regions", []))
        ))

        decision_match = (
            1 if semantic.tags.get("decision_present") == query.decision_present else 0
        )

        return float(region_overlap + decision_match)
