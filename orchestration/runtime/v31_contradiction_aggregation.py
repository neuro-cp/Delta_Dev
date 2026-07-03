"""Runtime V3.1 contradiction aggregation.

Aggregation collects competing observations into review bundles. It does not
resolve contradictions or mutate knowledge.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_learning_opportunity import stable_v31_id


REPORT_MD = Path("reports/runtime_v31d_contradiction_aggregation.md")
REPORT_JSON = Path("reports/runtime_v31d_contradiction_aggregation.json")


@dataclass(frozen=True)
class ContradictionObservation:
    topic: str
    source: str
    claim: str
    confidence: float


@dataclass(frozen=True)
class ContradictionReviewBundle:
    bundle_id: str
    topic: str
    sources: tuple[str, ...]
    frequency: int
    average_confidence: float
    observations: tuple[ContradictionObservation, ...]
    resolved: bool = False
    requires_review: bool = True

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["sources"] = list(self.sources)
        data["observations"] = [asdict(item) for item in self.observations]
        return data


def aggregate_contradictions(observations: list[ContradictionObservation]) -> list[ContradictionReviewBundle]:
    grouped: dict[str, list[ContradictionObservation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.topic].append(observation)
    bundles = []
    for topic, items in sorted(grouped.items()):
        sources = tuple(sorted({item.source for item in items}))
        avg = sum(item.confidence for item in items) / len(items)
        bundles.append(
            ContradictionReviewBundle(
                bundle_id=stable_v31_id("contradiction-review-bundle", topic, len(items), sources),
                topic=topic,
                sources=sources,
                frequency=len(items),
                average_confidence=round(avg, 4),
                observations=tuple(items),
            )
        )
    return bundles


def sample_contradiction_observations() -> list[ContradictionObservation]:
    return [
        ContradictionObservation("user_preference_color", "local_interaction", "favorite color is blue", 0.6),
        ContradictionObservation("user_preference_color", "local_interaction", "favorite color is green", 0.6),
        ContradictionObservation("workflow_order", "demo_trace", "review precedes approval", 0.82),
    ]


def build_contradiction_aggregation_report() -> dict[str, object]:
    bundles = aggregate_contradictions(sample_contradiction_observations())
    return {
        "phase": "Runtime V3.1D",
        "bundles": [bundle.as_dict() for bundle in bundles],
        "resolution_performed": False,
        "memory_mutation_performed": False,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_LEARNING_REVIEW_CONSOLE",
    }


def write_contradiction_aggregation_report() -> dict[str, object]:
    data = build_contradiction_aggregation_report()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V3.1D Contradiction Aggregation\n\n"
        "Competing observations are grouped into review bundles only. No contradiction resolution or memory mutation occurs.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    print(write_contradiction_aggregation_report()["final_recommendation"])
