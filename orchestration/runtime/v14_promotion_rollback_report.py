from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_promotion_rollback import (
    RUNTIME_V14V_INVARIANT_FLAGS,
    PromotionCandidateType,
    PromotionDecisionOutcome,
    PromotionSafetyStatus,
    RollbackDecisionOutcome,
    RuntimeDefaultChangeBlockerType,
    create_promotion_candidate,
    create_promotion_decision,
    create_promotion_evidence_packet,
    create_promotion_human_review_requirement,
    create_promotion_rollback_audit_record,
    create_promotion_rollback_report_entry,
    create_promotion_rollback_plan,
    create_promotion_safety_gate,
    create_rollback_decision,
    create_runtime_default_change_blocker,
)


REPORT_MD = Path("reports/runtime_v14v_promotion_rollback_decision_design.md")
REPORT_JSON = Path("reports/runtime_v14v_promotion_rollback_decision_design.json")


def build_promotion_rollback_report_data() -> dict[str, object]:
    candidate = create_promotion_candidate(
        candidate_name="HYB1",
        candidate_type=PromotionCandidateType.HYB1_RUNTIME_VARIANT,
        baseline_reference_id="runtime-v13-model-b",
        comparison_reference_ids=("runtime-v14u-artifact-comparison",),
        evidence_reference_ids=("runtime-v13-hyb1-validation",),
        safety_reference_ids=("runtime-v14u-safety-review",),
        rollback_reference_ids=("model-b-default-baseline",),
    )
    evidence = create_promotion_evidence_packet(
        candidate=candidate,
        comparison_summary="HYB1 improved reasoning noise/drift in opt-in validation while preserving planning and grounding.",
        improvement_summary="noise 7->5, reasoning drift 4->2, cases improved 2, cases regressed 0",
        regression_summary="promotion still blocked pending explicit review and rollback design",
        safety_summary="Model B remains default; HYB1 dormant/env-gated",
        uncertainty_summary="comparison evidence is not authority",
        sufficient_for_review=True,
    )
    safety_gate = create_promotion_safety_gate(
        candidate=candidate,
        required_reviews=("human-review", "rollback-review", "safety-review"),
        invariant_failures=(),
        unresolved_regressions=("promotion-review-missing",),
        missing_requirements=("human-review", "rollback-plan-approval"),
        safety_status=PromotionSafetyStatus.HUMAN_REVIEW_REQUIRED,
    )
    human_review = create_promotion_human_review_requirement(
        candidate=candidate,
        required_actor="human operator",
        review_reason="HYB1 cannot trial or promote from automated scorecard evidence alone.",
    )
    rollback_plan = create_promotion_rollback_plan(
        candidate=candidate,
        rollback_strategy="restore Model B default if any future gated trial regresses",
        rollback_trigger_conditions=("grounding_regression", "planning_regression", "safety_invariant_failure"),
    )
    promotion_decision = create_promotion_decision(
        candidate=candidate,
        outcome=PromotionDecisionOutcome.ELIGIBLE_FOR_FUTURE_GATED_TRIAL_DESIGN,
        rationale="HYB1 has positive opt-in evidence but remains dormant until human review and rollback requirements are satisfied.",
        invariant_status="promotion/default-change/runtime-activation flags remain false",
    )
    rollback_decision = create_rollback_decision(
        candidate=candidate,
        rollback_plan=rollback_plan,
        outcome=RollbackDecisionOutcome.ROLLBACK_DESIGN_ONLY,
        rationale="rollback cannot execute because HYB1 is not active.",
    )
    blocker = create_runtime_default_change_blocker(
        candidate=candidate,
        blocker_type=RuntimeDefaultChangeBlockerType.CANDIDATE_STILL_DORMANT,
        rationale="HYB1 remains dormant/env-gated and cannot become default in V1.4V.",
        required_resolution="future explicit human promotion/rollback phase",
    )
    audit = create_promotion_rollback_audit_record(
        candidate=candidate,
        blocker_ids=(blocker.blocker_id,),
        audit_summary="promotion/rollback decision design only; no activation or promotion",
        decision=promotion_decision,
        rollback_decision=rollback_decision,
        evidence_packet=evidence,
        safety_gate=safety_gate,
    )
    report_entry = create_promotion_rollback_report_entry(
        candidate=candidate,
        evidence_summary=evidence.improvement_summary,
        safety_summary="safety gate unsatisfied; HYB1 remains dormant",
        human_review_summary="human review required and unsatisfied",
        rollback_summary="rollback plan required; not ready or executed",
        blocker_summary="default change blocker unresolved",
        promotion_decision_summary=promotion_decision.outcome.value,
        rollback_decision_summary=rollback_decision.outcome.value,
        unresolved_gaps=("human review missing", "rollback approval missing", "promotion review missing"),
        recommended_next_review_step="final V1.4 safety closure report",
    )
    return {
        "phase": "Runtime V1.4V",
        "title": "Promotion / Rollback Decision Design",
        "status": "promotion-rollback-design-only_no-promotion_no-default-change_no-rollback-execution",
        "final_recommendation": "PROCEED_FINAL_V14_SAFETY_CLOSURE_REPORT",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v14_promotion_rollback.py",
            "orchestration/runtime/v14_promotion_rollback_report.py",
            "tests/runtime_v14/test_v14_promotion_rollback_decision_design.py",
            "reports/runtime_v14v_promotion_rollback_decision_design.md",
            "reports/runtime_v14v_promotion_rollback_decision_design.json",
            "docs/runtime_v14v_promotion_rollback_decision_prompt.txt",
        ],
        "invariant_flags": dict(RUNTIME_V14V_INVARIANT_FLAGS),
        "candidate": candidate.as_dict(),
        "evidence_packet": evidence.as_dict(),
        "safety_gate": safety_gate.as_dict(),
        "human_review": human_review.as_dict(),
        "rollback_plan": rollback_plan.as_dict(),
        "promotion_decision": promotion_decision.as_dict(),
        "rollback_decision": rollback_decision.as_dict(),
        "default_change_blocker": blocker.as_dict(),
        "audit": audit.as_dict(),
        "report_entry": report_entry.as_dict(),
        "safety_boundaries": [
            "promotion decision design is not promotion",
            "rollback decision design is not rollback execution",
            "HYB1 candidate is not default runtime",
            "comparison improvement is not authority",
        ],
        "inactive_systems": [
            "promotion",
            "runtime activation",
            "HYB1 default activation",
            "Model B default changes",
            "rollback execution",
            "training/fine-tuning/weight updates",
            "dataset export",
            "artifact creation/promotion",
            "provider/tool/action calls",
            "memory/canonical/recall mutation",
            "schedulers/background rollout",
        ],
        "test_status": "run py_compile and tests/runtime_v14 to verify",
    }


def write_promotion_rollback_report() -> dict[str, object]:
    data = build_promotion_rollback_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4V - Promotion / Rollback Decision Design",
        "",
        "Runtime V1.4V defines inert HYB1 promotion/rollback decision scaffolding. It does not promote HYB1, activate HYB1 by default, change Model B, execute rollback, train, call providers/tools, or mutate memory.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Safety Boundaries",
        "",
    ]
    lines.extend(f"- {item}" for item in data["safety_boundaries"])
    lines.extend(["", "## Invariant Flags", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in data["invariant_flags"].items())
    lines.extend(["", "## Continuation Checkpoint", ""])
    lines.append(
        "Runtime V1.4V is promotion-rollback-design-only. HYB1 remains dormant/env-gated, Model B remains default, and no promotion/default-change/rollback execution/training/provider/tool/action/memory path was added."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_promotion_rollback_report()
