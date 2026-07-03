"""Runtime V3.1 gated integration readiness.

This module defines the control objects required before a learning proposal can
ever become an integration event. It does not perform live memory writes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_learning_opportunity import stable_v31_id
from orchestration.runtime.v31_learning_proposal import LearningProposal, build_learning_proposals


REPORT_MD = Path("reports/runtime_v31g_gated_integration_readiness.md")
REPORT_JSON = Path("reports/runtime_v31g_gated_integration_readiness.json")

EXACT_ADMIN_APPROVAL_PREFIX = "APPROVE_LEARNING_INTEGRATION"


@dataclass(frozen=True)
class AdminApprovalEvent:
    approval_id: str
    proposal_id: str
    approved_by: str
    approval_scope: str
    raw_text: str
    valid: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OverwatchReviewResult:
    review_id: str
    proposal_id: str
    reviewer: str
    result: str
    reason: str
    provider_call_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OwnerOverrideEvent:
    override_id: str
    proposal_id: str
    owner: str
    reason: str
    valid: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GatedIntegrationEvent:
    integration_event_id: str
    source_proposal_id: str
    admin_approver: str
    overwatch_result: str
    override_status: str
    target_store: str
    rollback_token: str
    timestamp: str
    audit_record: dict[str, object]
    allowed: bool
    write_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def parse_admin_approval(text: str, proposal_id: str) -> AdminApprovalEvent:
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    fields = dict(line.split("=", 1) for line in lines[1:] if "=" in line)
    valid = (
        bool(lines)
        and lines[0] == EXACT_ADMIN_APPROVAL_PREFIX
        and fields.get("proposal_id") == proposal_id
        and fields.get("approved_by") == "admin"
        and fields.get("approval_scope") == "single_learning_proposal_only"
    )
    return AdminApprovalEvent(
        approval_id=stable_v31_id("admin-approval", proposal_id, text),
        proposal_id=proposal_id,
        approved_by=fields.get("approved_by", ""),
        approval_scope=fields.get("approval_scope", ""),
        raw_text=text,
        valid=valid,
    )


def build_local_overwatch_result(proposal: LearningProposal, *, allow: bool = False) -> OverwatchReviewResult:
    result = "allow" if allow else "block"
    reason = "local_fixture_allows_review_only" if allow else "external_overwatch_not_run_provider_calls_disabled"
    return OverwatchReviewResult(
        review_id=stable_v31_id("overwatch-review", proposal.proposal_id, result, reason),
        proposal_id=proposal.proposal_id,
        reviewer="local_overwatch_placeholder",
        result=result,
        reason=reason,
        provider_call_performed=False,
    )


def build_owner_override(proposal_id: str, *, reason: str = "") -> OwnerOverrideEvent:
    valid = bool(reason.strip())
    return OwnerOverrideEvent(
        override_id=stable_v31_id("owner-override", proposal_id, reason),
        proposal_id=proposal_id,
        owner="owner",
        reason=reason,
        valid=valid,
    )


def evaluate_gated_integration(
    proposal: LearningProposal,
    approval: AdminApprovalEvent,
    overwatch: OverwatchReviewResult,
    override: OwnerOverrideEvent | None = None,
    *,
    target_store: str = "delta_substrate_store_trial",
) -> GatedIntegrationEvent:
    override_status = "owner_override_allowed" if override and override.valid else "none"
    allowed = approval.valid and (overwatch.result == "allow" or override_status == "owner_override_allowed")
    event_id = stable_v31_id("gated-integration-event", proposal.proposal_id, approval.approval_id, overwatch.review_id, override_status)
    rollback = stable_v31_id("rollback-token", event_id, target_store)
    return GatedIntegrationEvent(
        integration_event_id=event_id,
        source_proposal_id=proposal.proposal_id,
        admin_approver=approval.approved_by,
        overwatch_result=overwatch.result,
        override_status=override_status,
        target_store=target_store,
        rollback_token=rollback,
        timestamp=datetime.now(UTC).replace(microsecond=0).isoformat(),
        audit_record={
            "approval_id": approval.approval_id,
            "overwatch_review_id": overwatch.review_id,
            "override_id": override.override_id if override else "",
            "proposal_review_status": proposal.review_status,
            "integration_requires_live_write_gate": True,
        },
        allowed=allowed,
        write_performed=False,
    )


def build_gated_integration_report() -> dict[str, object]:
    proposal = build_learning_proposals("I have corrected this preference five times.", review_status="admin_approved")[0]
    approval_text = (
        f"{EXACT_ADMIN_APPROVAL_PREFIX}\n"
        f"proposal_id={proposal.proposal_id}\n"
        "approved_by=admin\n"
        "approval_scope=single_learning_proposal_only"
    )
    approval = parse_admin_approval(approval_text, proposal.proposal_id)
    blocked = evaluate_gated_integration(proposal, approval, build_local_overwatch_result(proposal, allow=False))
    overridden = evaluate_gated_integration(
        proposal,
        approval,
        build_local_overwatch_result(proposal, allow=False),
        build_owner_override(proposal.proposal_id, reason="owner_accepts_risk_for_single_trial"),
    )
    return {
        "phase": "Runtime V3.1G",
        "approval_format": EXACT_ADMIN_APPROVAL_PREFIX,
        "proposal": proposal.as_dict(),
        "blocked_without_override": blocked.as_dict(),
        "allowed_with_owner_override": overridden.as_dict(),
        "live_write_performed": False,
        "training_performed": False,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_RUNTIME_V31_SAFETY_CHECKPOINT",
    }


def write_gated_integration_report() -> dict[str, object]:
    data = build_gated_integration_report()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V3.1G Gated Integration Readiness\n\n"
        "Defines admin approval, overwatch review, optional owner override, integration-event audit metadata, target store, and rollback token.\n\n"
        "No live write is performed in V3.1G.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    print(write_gated_integration_report()["final_recommendation"])
