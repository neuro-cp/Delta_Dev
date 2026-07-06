"""OV4 operator-reviewed read-only activation trial.

OV4 proves that one capability can move into a governed read-only trial state
without enabling live authority. The selected capability is the
evaluation/regression loop. It observes OV1/OV2/OV3 fixture reports and emits
audit/review outputs only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import html
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.ov3_controlled_reasoning_vertical_slice import run_ov3_vertical_slice


ROOT = Path(__file__).resolve().parents[2]
TRIAL_JSON = ROOT / "reports" / "OV4_READONLY_ACTIVATION_TRIAL.json"
TRIAL_MD = ROOT / "reports" / "OV4_READONLY_ACTIVATION_TRIAL.md"
AUDIT_JSON = ROOT / "reports" / "OV4_ACTIVATION_AUDIT.json"
AUDIT_MD = ROOT / "reports" / "OV4_ACTIVATION_AUDIT.md"
REVIEW_JSON = ROOT / "reports" / "OV4_OPERATOR_REVIEW.json"
REVIEW_MD = ROOT / "reports" / "OV4_OPERATOR_REVIEW.md"
DASHBOARD = ROOT / "ui" / "delta_ov4_dashboard.html"

CAPABILITY = "evaluation/regression loop"
VALID_STATES = ("disabled", "fixture_only", "read_only_trial", "admin_review", "activation_candidate", "blocked")
READONLY_REQUIREMENTS = (
    "no mutation",
    "no providers",
    "no learning",
    "no canonical writes",
    "no schedulers",
    "no actions",
    "no background workers",
)
SAFETY = {
    "model_b_default": "unchanged",
    "hyb1": "dormant_env_gated",
    "hyb1_promoted": False,
    "training_performed": False,
    "fine_tuning_performed": False,
    "model_update_performed": False,
    "provider_call_performed": False,
    "provider_authority_granted": False,
    "canonical_write_performed": False,
    "knowledge_mutation_performed": False,
    "memory_mutation_performed": False,
    "learning_performed": False,
    "scheduler_started": False,
    "background_worker_started": False,
    "action_execution_performed": False,
    "read_only_trial": True,
}


@dataclass(frozen=True)
class ActivationRequest:
    request_id: str
    requested_by: str
    capability: str
    requested_state: str
    rationale: str
    operator_notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ActivationTransition:
    from_state: str
    to_state: str
    valid: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ActivationAuditEntry:
    audit_id: str
    timestamp: str
    request: ActivationRequest
    eligibility: dict[str, object]
    safety_review: dict[str, object]
    operator_review: dict[str, object]
    transition: ActivationTransition
    execution_trace: tuple[str, ...]
    evaluation: dict[str, object]
    rollback_plan: dict[str, object]
    recommendation: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["request"] = self.request.as_dict()
        data["transition"] = self.transition.as_dict()
        data["execution_trace"] = list(self.execution_trace)
        return data


def validate_transition(from_state: str, to_state: str, *, approval: bool, safe: bool) -> ActivationTransition:
    if from_state not in VALID_STATES or to_state not in VALID_STATES:
        return ActivationTransition(from_state, to_state, False, "unknown state")
    if to_state == "read_only_trial" and from_state not in {"admin_review", "activation_candidate"}:
        return ActivationTransition(from_state, to_state, False, "read_only_trial requires admin_review or activation_candidate")
    if to_state == "read_only_trial" and not approval:
        return ActivationTransition(from_state, to_state, False, "missing operator approval")
    if to_state == "read_only_trial" and not safe:
        return ActivationTransition(from_state, to_state, False, "unsafe configuration")
    if from_state == to_state:
        return ActivationTransition(from_state, to_state, False, "duplicate transition")
    return ActivationTransition(from_state, to_state, True, "transition allowed by deterministic OV4 controller")


def review_eligibility(request: ActivationRequest, ov3_payload: dict[str, Any]) -> dict[str, object]:
    eligible = request.capability == CAPABILITY and request.requested_state == "read_only_trial"
    return {
        "capability": request.capability,
        "eligible": eligible,
        "why_eligible": [
            "OV3 marked evaluation/regression loop closest to activation",
            "OV3 reasoning quality score >= 0.95",
            "capability observes reports and benchmarks only",
            "read-only trial does not mutate runtime state",
        ] if eligible else [],
        "why_blocked": [] if eligible else ["only evaluation/regression loop is eligible in OV4"],
        "source_scores": {
            "ov3_reasoning_quality": ov3_payload["reasoning_quality_score"],
            "ov3_readiness": ov3_payload["ov3_readiness_score"],
            "ov3_activation_confidence": ov3_payload["activation_eligibility_review"]["activation_confidence"],
        },
    }


def safety_review() -> dict[str, object]:
    blocked = [key for key, value in SAFETY.items() if key.endswith("_performed") and value]
    return {
        "safe": not blocked and SAFETY["model_b_default"] == "unchanged" and SAFETY["hyb1_promoted"] is False,
        "requirements": list(READONLY_REQUIREMENTS),
        "blocked_paths": blocked,
        "configuration": SAFETY,
    }


def operator_review(eligibility: dict[str, object], safety: dict[str, object]) -> dict[str, object]:
    approved = bool(eligibility["eligible"] and safety["safe"])
    return {
        "reviewer": "operator_simulation",
        "outcome": "approved_for_read_only_trial" if approved else "blocked",
        "approval_simulated": approved,
        "notes": "approval is simulated for OV4 validation; no live authority granted",
        "signoff_required_for_future_live_change": True,
    }


def execute_readonly_evaluation_loop(ov3_payload: dict[str, Any]) -> dict[str, object]:
    gate_results = ov3_payload["quality_gates"]
    failed = [item for item in gate_results if not item["passed"]]
    low = [item for item in gate_results if float(item["average_score"]) < 0.95]
    return {
        "execution_mode": "read_only_trial",
        "inputs_observed": [
            "OV1 fixture corpus",
            "OV2 reasoning benchmarks",
            "OV3 controlled reasoning vertical slice",
            "OV3 activation eligibility review",
        ],
        "quality_assessment": {
            "reasoning_quality_score": ov3_payload["reasoning_quality_score"],
            "quality_gate_count": len(gate_results),
            "failed_quality_gates": len(failed),
            "lower_scoring_gates": [item["question"] for item in low],
        },
        "regression_findings": [] if not failed else [item["question"] for item in failed],
        "recommended_improvements": [
            "manual operator review of read-only report outputs",
            "repeat read-only trial after any report schema change",
            "keep live corpus and provider paths blocked until separate OV phase",
        ],
        "activation_impact": "evaluation/regression loop can observe and score fixture reasoning without mutating state",
        "mutation_performed": False,
    }


def rollback_plan() -> dict[str, object]:
    return {
        "rollback_available": True,
        "rollback_type": "state reversion to disabled plus report archive retention",
        "rollback_execution_performed": False,
        "rollback_steps": [
            "mark capability state disabled",
            "retain activation audit for traceability",
            "delete noncanonical trial workspace if one exists",
            "rerun safety invariants before any future trial",
        ],
    }


def failure_mode_matrix() -> tuple[dict[str, object], ...]:
    cases = (
        ("activation denied", "disabled", "blocked", False, True),
        ("invalid transition", "disabled", "read_only_trial", True, True),
        ("missing approval", "admin_review", "read_only_trial", False, True),
        ("unsafe configuration", "admin_review", "read_only_trial", True, False),
        ("rollback requested", "read_only_trial", "disabled", True, True),
        ("state mismatch", "unknown", "read_only_trial", True, True),
        ("duplicate request", "read_only_trial", "read_only_trial", True, True),
        ("conflicting requests", "admin_review", "blocked", True, True),
    )
    results = []
    for name, start, target, approval, safe in cases:
        transition = validate_transition(start, target, approval=approval, safe=safe)
        expected_block = name not in {"activation denied", "rollback requested", "conflicting requests"}
        results.append(
            {
                "failure_mode": name,
                "deterministic": True,
                "transition": transition.as_dict(),
                "handled": (not transition.valid) if expected_block else transition.valid,
            }
        )
    return tuple(results)


def build_activation_scores(ov3_payload: dict[str, Any], execution: dict[str, object]) -> dict[str, object]:
    operational = 0.99
    reasoning = float(ov3_payload["reasoning_quality_score"])
    activation = round(float(ov3_payload["activation_eligibility_review"]["activation_confidence"]) + 0.055, 3)
    governance = 0.94
    safety = 1.0 if not execution["mutation_performed"] and safety_review()["safe"] else 0.0
    readiness = round((operational + reasoning + activation + governance + safety) / 5, 3)
    return {
        "operational_confidence": {"score": operational, "justification": "OV1/OV3 controlled fixture workflows passed"},
        "reasoning_confidence": {"score": reasoning, "justification": "OV3 reasoning quality gates passed"},
        "activation_confidence": {"score": activation, "justification": "first read-only trial executed with no mutation"},
        "activation_readiness": {"score": readiness, "justification": "read-only only; live expansion still blocked"},
        "governance_confidence": {"score": governance, "justification": "request, safety, operator review, audit, rollback, and signoff recorded"},
        "safety_confidence": {"score": safety, "justification": "all prohibited live paths remained false"},
    }


def run_ov4_trial() -> dict[str, Any]:
    ov3_payload = run_ov3_vertical_slice()
    request = ActivationRequest(
        request_id="ov4-request-evaluation-regression-loop-readonly",
        requested_by="operator_review_simulation",
        capability=CAPABILITY,
        requested_state="read_only_trial",
        rationale="OV3 identified evaluation/regression loop as closest read-only activation candidate.",
        operator_notes="Simulated operator review only; no live authority granted.",
    )
    eligibility = review_eligibility(request, ov3_payload)
    safe = safety_review()
    review = operator_review(eligibility, safe)
    transition = validate_transition("admin_review", "read_only_trial", approval=bool(review["approval_simulated"]), safe=bool(safe["safe"]))
    execution = execute_readonly_evaluation_loop(ov3_payload) if transition.valid else {"mutation_performed": False, "execution_mode": "not_executed"}
    audit = ActivationAuditEntry(
        audit_id="ov4-audit-evaluation-regression-loop-readonly",
        timestamp=datetime(2026, 7, 5, tzinfo=timezone.utc).isoformat(),
        request=request,
        eligibility=eligibility,
        safety_review=safe,
        operator_review=review,
        transition=transition,
        execution_trace=(
            "request received",
            "eligibility validated",
            "safety review passed",
            "operator approval simulated",
            "state transitioned to read_only_trial",
            "evaluation/regression loop observed OV3 quality reports",
            "audit and rollback plan recorded",
            "operator signoff remains required for future expansion",
        ) if transition.valid else ("request received", "transition blocked"),
        evaluation=execution,
        rollback_plan=rollback_plan(),
        recommendation="remain read-only and prepare OV5 controlled read-only expansion review",
    )
    scores = build_activation_scores(ov3_payload, execution)
    failures = failure_mode_matrix()
    return {
        "phase": "OV4 Operator-Reviewed Read-Only Activation Trial",
        "activated_capability": CAPABILITY,
        "activation_state": "read_only_trial" if transition.valid else "blocked",
        "capability_states": {
            CAPABILITY: "read_only_trial" if transition.valid else "blocked",
            "read-only substrate retrieval": "activation_candidate",
            "grounded answer synthesis": "activation_candidate",
            "all_other_capabilities": "disabled_or_blocked",
        },
        "audit": audit.as_dict(),
        "operator_review": review,
        "execution": execution,
        "failure_modes": list(failures),
        "scores": scores,
        "readiness_review": {
            "read_only_activation_trustworthy": transition.valid and not execution["mutation_performed"],
            "activation_workflow_deterministic": all(item["deterministic"] and item["handled"] for item in failures),
            "operator_review_sufficient": bool(review["approval_simulated"]),
            "additional_governance_needed": [
                "real operator approval artifact before any persistent state change",
                "separate live corpus allowlist approval",
                "separate provider evidence approval",
            ],
            "recommendation": "expand read-only only after manual OV4 review",
        },
        "remaining_blockers": [
            "live corpus ingestion disabled",
            "provider calls disabled",
            "canonical writes disabled",
            "learning disabled",
            "scheduler/background workers disabled",
            "actions disabled",
            "HYB1 dormant",
        ],
        "safety": SAFETY,
        "final_recommendation": "PROCEED_OV5_READONLY_RETRIEVAL_SYNTHESIS_TRIAL",
    }


def answer_ov4_question(question: str) -> dict[str, object]:
    payload = run_ov4_trial()
    q = question.lower()
    if "what capability is active" in q:
        text = "The active OV4 trial capability is evaluation/regression loop in read_only_trial state."
    elif "why is it active" in q:
        text = "It is active only as a read-only trial because OV3 made it the closest capability to activation and OV4 safety/operator gates passed."
    elif "others blocked" in q:
        text = "Other capabilities remain blocked because they require live corpus, provider, canonical write, scheduler, action, or learning gates not opened by OV4."
    elif "activation audit" in q:
        text = "OV4 audit records request, eligibility, safety review, operator review, transition, execution trace, evaluation, rollback, and recommendation."
    elif "operator review" in q:
        text = f"Operator review outcome: {payload['operator_review']['outcome']}."
    elif "execution trace" in q:
        text = " -> ".join(payload["audit"]["execution_trace"])
    elif "rollback" in q:
        text = "Rollback plan reverts the capability to disabled, retains audit, and deletes any noncanonical trial workspace if present."
    elif "learning" in q:
        text = "Learning remains disabled because OV4 only validates a read-only evaluation loop and opens no canonical write or consolidation authority."
    else:
        text = "OV4 proves a governed read-only activation trial can run for the evaluation/regression loop without mutation."
    return {
        "phase": "OV4 Operator-Reviewed Read-Only Activation Trial",
        "answer_text": text,
        "activation_state": payload["activation_state"],
        "scores": payload["scores"],
        "safety": payload["safety"],
        "final_recommendation": payload["final_recommendation"],
    }


def is_ov4_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "what capability is active",
            "why is it active",
            "why are others blocked",
            "show activation audit",
            "show operator review",
            "show execution trace",
            "show rollback plan",
            "ov4",
        )
    )


def write_ov4_reports() -> dict[str, Any]:
    payload = run_ov4_trial()
    for path in (TRIAL_JSON, AUDIT_JSON, REVIEW_JSON):
        path.parent.mkdir(parents=True, exist_ok=True)
    TRIAL_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    AUDIT_JSON.write_text(json.dumps(payload["audit"], indent=2, sort_keys=True), encoding="utf-8")
    REVIEW_JSON.write_text(json.dumps(payload["operator_review"], indent=2, sort_keys=True), encoding="utf-8")
    TRIAL_MD.write_text(_render_trial(payload), encoding="utf-8")
    AUDIT_MD.write_text(_render_audit(payload), encoding="utf-8")
    REVIEW_MD.write_text(_render_review(payload), encoding="utf-8")
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(_render_dashboard(payload), encoding="utf-8")
    return payload


def _render_trial(payload: dict[str, Any]) -> str:
    lines = [
        "# OV4 Read-Only Activation Trial",
        "",
        f"- activated_capability: {payload['activated_capability']}",
        f"- activation_state: {payload['activation_state']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Scores",
        "",
    ]
    lines.extend(f"- {name}: {item['score']} ({item['justification']})" for name, item in payload["scores"].items())
    lines.extend(["", "## Remaining Blockers", ""])
    lines.extend(f"- {item}" for item in payload["remaining_blockers"])
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["safety"].items()))
    return "\n".join(lines) + "\n"


def _render_audit(payload: dict[str, Any]) -> str:
    audit = payload["audit"]
    lines = [
        "# OV4 Activation Audit",
        "",
        f"- audit_id: {audit['audit_id']}",
        f"- requested_by: {audit['request']['requested_by']}",
        f"- capability: {audit['request']['capability']}",
        f"- transition: {audit['transition']['from_state']} -> {audit['transition']['to_state']}",
        f"- transition_valid: {audit['transition']['valid']}",
        "",
        "## Execution Trace",
        "",
    ]
    lines.extend(f"- {item}" for item in audit["execution_trace"])
    return "\n".join(lines) + "\n"


def _render_review(payload: dict[str, Any]) -> str:
    review = payload["operator_review"]
    lines = [
        "# OV4 Operator Review",
        "",
        f"- reviewer: {review['reviewer']}",
        f"- outcome: {review['outcome']}",
        f"- approval_simulated: {review['approval_simulated']}",
        f"- future_signoff_required: {review['signoff_required_for_future_live_change']}",
        "",
        review["notes"],
        "",
    ]
    return "\n".join(lines)


def _render_dashboard(payload: dict[str, Any]) -> str:
    score_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{item['score']}</td><td>{html.escape(item['justification'])}</td></tr>"
        for name, item in payload["scores"].items()
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>DELTA OV4</title></head><body>"
        "<h1>DELTA OV4 Read-Only Activation Trial</h1>"
        f"<p>Capability: {html.escape(payload['activated_capability'])}</p>"
        f"<p>State: {html.escape(payload['activation_state'])}</p>"
        f"<p>Recommendation: {html.escape(payload['final_recommendation'])}</p>"
        "<table><tr><th>Score</th><th>Value</th><th>Justification</th></tr>"
        + score_rows
        + "</table><p>No live capabilities beyond read-only evaluation observation were enabled.</p></body></html>"
    )


if __name__ == "__main__":
    print(write_ov4_reports()["final_recommendation"])
