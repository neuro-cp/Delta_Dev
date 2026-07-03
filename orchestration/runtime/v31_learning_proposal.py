"""Runtime V3.1 structured learning proposal objects."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_learning_opportunity import LearningOpportunity, detect_learning_opportunities, stable_v31_id


REPORT_MD = Path("reports/runtime_v31b_structured_learning_proposals.md")
REPORT_JSON = Path("reports/runtime_v31b_structured_learning_proposals.json")

PROPOSAL_STATES = (
    "draft",
    "review",
    "admin_approved",
    "overwatch_allowed",
    "overwatch_blocked",
    "owner_override_allowed",
    "integrated",
    "rolled_back",
    "rejected",
)


@dataclass(frozen=True)
class LearningProposal:
    proposal_id: str
    source_references: tuple[str, ...]
    semantic_summary: str
    confidence: float
    conflicts: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    risk_assessment: str
    rollback_plan: str
    review_status: str
    integrated: bool = False
    eligible_for_gated_integration: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["source_references"] = list(self.source_references)
        data["conflicts"] = list(self.conflicts)
        data["supporting_evidence"] = list(self.supporting_evidence)
        return data


def proposal_from_opportunity(opportunity: LearningOpportunity, *, review_status: str = "draft") -> LearningProposal:
    if review_status not in PROPOSAL_STATES:
        raise ValueError(f"Unsupported proposal review status: {review_status}")
    return LearningProposal(
        proposal_id=stable_v31_id("learning-proposal", opportunity.id, review_status),
        source_references=(opportunity.id,),
        semantic_summary=f"Review {opportunity.category}: {opportunity.reason}",
        confidence=opportunity.confidence,
        conflicts=("unreviewed_conflicts_unknown",) if opportunity.category == "contradiction_cluster" else (),
        supporting_evidence=(opportunity.source,),
        risk_assessment="review_only_no_integration",
        rollback_plan="No rollback required because no integration or memory mutation occurs.",
        review_status=review_status,
        integrated=False,
        eligible_for_gated_integration=review_status
        in ("admin_approved", "overwatch_allowed", "owner_override_allowed", "integrated"),
    )


def build_learning_proposals(text: str, *, review_status: str = "draft") -> list[LearningProposal]:
    return [proposal_from_opportunity(item, review_status=review_status) for item in detect_learning_opportunities(text)]


def build_structured_learning_proposal_report() -> dict[str, object]:
    proposals = build_learning_proposals("I have corrected this preference five times.", review_status="review")
    approved = build_learning_proposals("Approve this learning proposal.", review_status="admin_approved")
    return {
        "phase": "Runtime V3.1B",
        "proposals": [item.as_dict() for item in proposals],
        "admin_approved_example": [item.as_dict() for item in approved],
        "admin_approved_means_automatic_integration": False,
        "admin_approved_means_eligible_for_gated_integration": True,
        "learning_performed": False,
        "integration_performed": False,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_COGNITIVE_TIMELINE",
    }


def write_structured_learning_proposal_report() -> dict[str, object]:
    data = build_structured_learning_proposal_report()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V3.1B Structured Learning Proposal Objects\n\n"
        "LearningProposal objects can enter gated review states. Admin approval makes a proposal eligible for gated integration, not automatically integrated.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    print(write_structured_learning_proposal_report()["final_recommendation"])
