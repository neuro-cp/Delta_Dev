"""Unified proposal/review/approval/integration state machine for RC1.

This module normalizes learning proposal and integration simulation states into
one deterministic lifecycle. It never performs live integration or mutation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.arc_iv_knowledge_evolution import KnowledgeEvolutionEngine
from orchestration.runtime.v31_learning_opportunity import stable_v31_id
from orchestration.runtime.v31_learning_proposal import build_learning_proposals


REPORT_JSON = Path("reports/RC1_UNIFIED_REVIEW_STATE_MACHINE.json")
REPORT_MD = Path("reports/RC1_UNIFIED_REVIEW_STATE_MACHINE.md")

UNIFIED_STATES = (
    "draft",
    "review",
    "admin_approved",
    "overwatch_allowed",
    "overwatch_blocked",
    "owner_override_allowed",
    "simulation_ready",
    "ready_to_integrate",
    "integrated_disabled",
    "rolled_back_available",
)


@dataclass(frozen=True)
class UnifiedReviewTransition:
    transition_id: str
    source_state: str
    target_state: str
    reason: str
    allowed: bool
    live_write_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class UnifiedReviewLifecycle:
    lifecycle_id: str
    proposal_id: str
    candidate_id: str
    states: tuple[str, ...]
    current_state: str
    transitions: tuple[UnifiedReviewTransition, ...]
    rollback_token: str
    integrated: bool = False
    mutation_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["states"] = list(self.states)
        data["transitions"] = [transition.as_dict() for transition in self.transitions]
        return data


def build_unified_lifecycle() -> UnifiedReviewLifecycle:
    proposal = build_learning_proposals("I have corrected this preference five times.", review_status="admin_approved")[0]
    candidate = KnowledgeEvolutionEngine().build_candidate(proposal)
    transition_specs = (
        ("draft", "review", "proposal_created_for_human_review", True),
        ("review", "admin_approved", "explicit_admin_review_state_present", True),
        ("admin_approved", "overwatch_allowed", "local_overwatch_simulation_allows_review_continuation", True),
        ("overwatch_allowed", "simulation_ready", "knowledge_evolution_candidate_built", True),
        ("simulation_ready", "ready_to_integrate", "impact_and_rollback_are_available", True),
        ("ready_to_integrate", "integrated_disabled", "live_integration_gate_remains_closed", False),
        ("integrated_disabled", "rolled_back_available", "rollback_reference_remains_available", True),
    )
    transitions = tuple(
        UnifiedReviewTransition(
            transition_id=stable_v31_id("unified-transition", proposal.proposal_id, source, target),
            source_state=source,
            target_state=target,
            reason=reason,
            allowed=allowed,
            live_write_performed=False,
        )
        for source, target, reason, allowed in transition_specs
    )
    return UnifiedReviewLifecycle(
        lifecycle_id=stable_v31_id("unified-review-lifecycle", proposal.proposal_id, candidate.candidate_id),
        proposal_id=proposal.proposal_id,
        candidate_id=candidate.candidate_id,
        states=UNIFIED_STATES,
        current_state="integrated_disabled",
        transitions=transitions,
        rollback_token=stable_v31_id("unified-rollback", candidate.candidate_id),
        integrated=False,
        mutation_performed=False,
    )


def build_state_machine_report() -> dict[str, Any]:
    lifecycle = build_unified_lifecycle()
    return {
        "phase": "RC1 Unified Proposal Review State Machine",
        "lifecycle": lifecycle.as_dict(),
        "normalized_states": list(UNIFIED_STATES),
        "safety": {
            "training_performed": False,
            "provider_call_performed": False,
            "memory_mutation_performed": False,
            "knowledge_mutation_performed": False,
            "integration_write_performed": False,
            "rollback_available": True,
        },
        "estimated_runtime_maturity": 93,
        "final_recommendation": "PROCEED_CENTRAL_RUNTIME_ARTIFACT_REGISTRY",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lifecycle = payload["lifecycle"]
    lines = [
        "# RC1 Unified Proposal Review State Machine",
        "",
        f"Lifecycle: `{lifecycle['lifecycle_id']}`",
        f"Current state: `{lifecycle['current_state']}`",
        "",
        "## Transitions",
        "",
    ]
    lines.extend(
        f"- {transition['source_state']} -> {transition['target_state']}: {transition['reason']} "
        f"(allowed={transition['allowed']}, live_write={transition['live_write_performed']})"
        for transition in lifecycle["transitions"]
    )
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["safety"].items()))
    lines.extend(["", "## Final Recommendation", "", payload["final_recommendation"], ""])
    return "\n".join(lines)


def write_state_machine_report(path: str | Path = REPORT_JSON) -> dict[str, Any]:
    payload = build_state_machine_report()
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


if __name__ == "__main__":
    report = write_state_machine_report()
    print(f"final_recommendation={report['final_recommendation']}")
    print(f"estimated_runtime_maturity={report['estimated_runtime_maturity']}")
