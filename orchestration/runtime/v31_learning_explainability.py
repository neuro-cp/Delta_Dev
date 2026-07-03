"""Runtime V3.1 learning proposal explainability."""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_learning_proposal import LearningProposal, build_learning_proposals


REPORT_MD = Path("reports/runtime_v31f_learning_explainability.md")
REPORT_JSON = Path("reports/runtime_v31f_learning_explainability.json")


def explain_learning_proposal(proposal: LearningProposal) -> dict[str, object]:
    blocked_reasons = []
    if not proposal.integrated:
        blocked_reasons.append("proposal_not_integrated")
    if not proposal.eligible_for_gated_integration:
        blocked_reasons.append("admin_approval_or_gate_missing")
    if proposal.eligible_for_gated_integration and not proposal.integrated:
        blocked_reasons.append("awaiting_overwatch_or_owner_override_gate")
    if proposal.review_status == "rejected":
        blocked_reasons.append("review_status_rejected")
    return {
        "proposal_id": proposal.proposal_id,
        "why_proposed": proposal.semantic_summary,
        "why_rejected": "review_status_rejected" if proposal.review_status == "rejected" else "not_rejected",
        "why_blocked": blocked_reasons,
        "review_status": proposal.review_status,
        "integrated": proposal.integrated,
        "eligible_for_gated_integration": proposal.eligible_for_gated_integration,
    }


def build_learning_explainability_report() -> dict[str, object]:
    proposals = build_learning_proposals("I have corrected this preference five times.", review_status="review")
    explanations = [explain_learning_proposal(item) for item in proposals]
    return {
        "phase": "Runtime V3.1F",
        "explanations": explanations,
        "deterministic": True,
        "learning_performed": False,
        "integration_performed": False,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_RUNTIME_V31_TESTS",
    }


def write_learning_explainability_report() -> dict[str, object]:
    data = build_learning_explainability_report()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V3.1F Learning Explainability\n\n"
        "Explains why a proposal exists, why it is blocked, and whether it was rejected. No integration occurs.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    print(write_learning_explainability_report()["final_recommendation"])
