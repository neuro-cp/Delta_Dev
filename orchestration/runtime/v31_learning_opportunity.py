"""Runtime V3.1 learning opportunity detection.

Detection is not learning. This module recognizes local interaction patterns
that could become reviewable learning opportunities, but every opportunity is
explicitly ineligible for learning/integration.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants


REPORT_MD = Path("reports/runtime_v31a_learning_opportunity_detection.md")
REPORT_JSON = Path("reports/runtime_v31a_learning_opportunity_detection.json")


@dataclass(frozen=True)
class LearningOpportunity:
    id: str
    source: str
    reason: str
    confidence: float
    category: str
    evidence_count: int
    recommended_action: str
    requires_review: bool
    eligible_for_learning: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def stable_v31_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def detect_learning_opportunities(text: str, *, source: str = "local_manual_interaction") -> list[LearningOpportunity]:
    normalized = " ".join(str(text).lower().split())
    opportunities: list[LearningOpportunity] = []

    def add(category: str, reason: str, confidence: float, evidence_count: int, recommended_action: str) -> None:
        opportunities.append(
            LearningOpportunity(
                id=stable_v31_id("learning-opportunity", source, category, normalized),
                source=source,
                reason=reason,
                confidence=confidence,
                category=category,
                evidence_count=evidence_count,
                recommended_action=recommended_action,
                requires_review=True,
                eligible_for_learning=False,
            )
        )

    if any(token in normalized for token in ("corrected", "correction", "wrong again", "fixed this")):
        add("repeated_correction", "The interaction references correction pressure that may deserve review.", 0.74, 1, "create_review_proposal")
    if any(token in normalized for token in ("preference", "favorite", "i prefer", "my preferred")):
        count = 5 if "five" in normalized or "5" in normalized else 1
        add("repeated_user_preference", "The interaction may contain a user preference that requires explicit review before any memory path.", 0.68, count, "create_review_proposal")
    if any(token in normalized for token in ("unknown", "do not know", "can't answer", "cannot answer", "unresolved")):
        add("unresolved_unknown", "The interaction references an unresolved unknown that may need future evidence.", 0.62, 1, "track_as_review_only_gap")
    if any(token in normalized for token in ("contradiction", "conflict", "inconsistent", "but earlier")):
        add("contradiction_cluster", "The interaction indicates competing observations that should be grouped, not resolved automatically.", 0.7, 2, "create_contradiction_review_bundle")
    if not opportunities and any(token in normalized for token in ("learn", "learning", "should delta")):
        add("general_learning_request", "The user asked what DELTA should learn; this becomes a reviewable opportunity only.", 0.5, 1, "create_review_proposal")

    return opportunities


def build_learning_opportunity_report() -> dict[str, object]:
    samples = [
        "What should DELTA learn from this interaction?",
        "I have corrected this preference five times.",
        "This unknown remained unresolved.",
        "There is a contradiction between these observations.",
    ]
    return {
        "phase": "Runtime V3.1A",
        "samples": [
            {"input": sample, "opportunities": [item.as_dict() for item in detect_learning_opportunities(sample)]}
            for sample in samples
        ],
        "learning_performed": False,
        "integration_performed": False,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_STRUCTURED_LEARNING_PROPOSAL_OBJECTS",
    }


def write_learning_opportunity_report() -> dict[str, object]:
    data = build_learning_opportunity_report()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V3.1A Learning Opportunity Detection\n\n"
        "Detects possible learning opportunities as reviewable objects only. No learning or integration is performed.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    print(write_learning_opportunity_report()["final_recommendation"])
