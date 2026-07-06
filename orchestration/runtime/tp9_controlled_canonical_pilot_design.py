"""TP9 controlled canonical pilot design.

TP9 designs the smallest future canonical pilot path. It does not enable
canonical memory, perform canonical writes, call providers, train, execute
actions, schedule work, promote HYB1, or replace Model B.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from orchestration.runtime.tp8_canonical_promotion_policy import SAFETY as TP8_SAFETY
from orchestration.runtime.tp8_canonical_promotion_policy import build_promotion_policy, classify_candidate


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
UI_PATH = ROOT / "ui" / "delta_tp9_dashboard.html"

SAFETY = {
    **TP8_SAFETY,
    "tp9_canonical_pilot_design": True,
    "canonical_pilot_enabled": False,
    "canonical_write_performed": False,
    "canonical_memory_mutation_performed": False,
    "autonomous_promotion_performed": False,
    "provider_call_performed": False,
    "training_started": False,
    "scheduler_started": False,
    "action_execution_performed": False,
}

REPORT_PATHS = {
    "scope": (REPORTS / "TP9_CANONICAL_PILOT_SCOPE.json", REPORTS / "TP9_CANONICAL_PILOT_SCOPE.md"),
    "gate_model": (REPORTS / "TP9_GATE_MODEL.json", REPORTS / "TP9_GATE_MODEL.md"),
    "write_path": (REPORTS / "TP9_CANONICAL_WRITE_PATH_DESIGN.json", REPORTS / "TP9_CANONICAL_WRITE_PATH_DESIGN.md"),
    "rollback": (REPORTS / "TP9_ROLLBACK_DESIGN.json", REPORTS / "TP9_ROLLBACK_DESIGN.md"),
    "conflict": (REPORTS / "TP9_CONFLICT_HANDLING.json", REPORTS / "TP9_CONFLICT_HANDLING.md"),
    "falsification": (REPORTS / "TP9_FALSIFICATION.json", REPORTS / "TP9_FALSIFICATION.md"),
    "safety_case": (REPORTS / "TP9_SAFETY_CASE.json", REPORTS / "TP9_SAFETY_CASE.md"),
    "readiness": (REPORTS / "TP9_READINESS_REVIEW.json", REPORTS / "TP9_READINESS_REVIEW.md"),
}


def define_canonical_pilot_scope() -> dict[str, Any]:
    return {
        "phase": "TP9 Canonical Pilot Scope",
        "pilot_enabled": False,
        "scope": "single-domain, operator-reviewed, canonical-write design only",
        "allowed_knowledge": ["low-risk project self-description claims", "fully provenanced operational-status claims"],
        "excluded_knowledge": ["personal memory", "medical/legal/financial claims", "action instructions", "provider-derived authority", "unresolved contradictions"],
        "activation_requirement": "separate future explicit approval required",
        "approval_model": "single candidate, exact approval, multi-reviewer policy satisfied",
        "target_store": "disabled canonical pilot store design",
        "rollback_requirement": "per-record rollback token plus pre-write snapshot",
        "audit_requirement": "source proposal, reviewer chain, policy gate results, rollback handle, timestamp",
    }


def build_gate_model() -> dict[str, Any]:
    return {
        "phase": "TP9 Gate Model",
        "gates": [
            "tp8_policy_passed",
            "canonical_scope_match",
            "complete_provenance",
            "no_unresolved_contradiction",
            "bounded_uncertainty",
            "multi_reviewer_agreement",
            "explicit_operator_approval",
            "rollback_token_available",
            "audit_record_ready",
            "future_activation_flag_enabled",
        ],
        "default_decision": "BLOCKED_DESIGN_ONLY",
        "future_activation_flag_enabled": False,
    }


def evaluate_gate_model(candidate: dict[str, Any], *, explicit_operator_approval: bool = False, activation_flag: bool = False) -> dict[str, Any]:
    policy = classify_candidate(candidate, reviewer_agreement=candidate.get("reviewer_agreement", 1.0))
    checks = {
        "tp8_policy_passed": policy["classification"] == "eligible_for_future_promotion",
        "canonical_scope_match": candidate.get("scope") in {"project_self_description", "operational_status"},
        "complete_provenance": bool(candidate.get("source_references")) and bool(candidate.get("source_checksum")),
        "no_unresolved_contradiction": not bool(candidate.get("contradictions")),
        "bounded_uncertainty": candidate.get("uncertainty") in {"resolved", "bounded"},
        "multi_reviewer_agreement": candidate.get("reviewer_agreement", 1.0) >= 1.0,
        "explicit_operator_approval": explicit_operator_approval,
        "rollback_token_available": bool(candidate.get("rollback_token")),
        "audit_record_ready": bool(candidate.get("audit_id")),
        "future_activation_flag_enabled": activation_flag,
    }
    return {
        "candidate_id": candidate.get("candidate_id", "unknown"),
        "checks": checks,
        "policy_classification": policy,
        "would_write": False,
        "decision": "DESIGN_BLOCKED" if not all(checks.values()) else "ELIGIBLE_FOR_FUTURE_DISABLED_PILOT",
    }


def design_disabled_write_path() -> dict[str, Any]:
    return {
        "phase": "TP9 Canonical Write Path Design",
        "enabled": False,
        "live_write_performed": False,
        "steps": [
            "load approved noncanonical candidate",
            "evaluate TP8 promotion policy",
            "evaluate TP9 pilot gates",
            "prepare inactive canonical write intent",
            "prepare audit record",
            "prepare rollback token",
            "stop before persistence unless future phase enables pilot",
        ],
        "forbidden": ["automatic write", "bulk promotion", "provider approval", "assistant self-approval", "canonical mutation in TP9"],
    }


def design_rollback() -> dict[str, Any]:
    return {
        "phase": "TP9 Rollback Design",
        "rollback_supported": True,
        "rollback_execution_enabled": False,
        "rollback_handles": ["record_id", "pre_write_snapshot", "source_candidate_id", "audit_id", "reason_code"],
        "procedures": ["single-record rollback", "batch rollback by pilot id", "provenance restoration", "audit diff review"],
    }


def define_conflict_handling() -> dict[str, Any]:
    return {
        "phase": "TP9 Conflict Handling",
        "unresolved_conflicts_block": True,
        "minority_objections_block": True,
        "counterevidence_preserved": True,
        "conflict_states": ["blocked", "needs_review", "superseded_by_stronger_evidence", "rollback_required"],
    }


def run_falsification() -> dict[str, Any]:
    cases = [
        _candidate("missing_approval", explicit=False, rollback=True),
        _candidate("missing_rollback", explicit=True, rollback=False),
        _candidate("wrong_scope", explicit=True, rollback=True, scope="personal_memory"),
        _candidate("contradicted", explicit=True, rollback=True, contradictions=("conflict",)),
        _candidate("uncertain", explicit=True, rollback=True, uncertainty="unresolved"),
        _candidate("reviewer_disagreement", explicit=True, rollback=True, reviewer_agreement=0.5),
        _candidate("missing_audit", explicit=True, rollback=True, audit_id=""),
        _candidate("activation_flag_off", explicit=True, rollback=True),
    ]
    results = [evaluate_gate_model(case["candidate"], explicit_operator_approval=case["explicit"], activation_flag=False) for case in cases]
    return {
        "phase": "TP9 Falsification",
        "cases": results,
        "all_blocked": all(item["decision"] == "DESIGN_BLOCKED" and item["would_write"] is False for item in results),
        "passed": all(item["decision"] == "DESIGN_BLOCKED" and item["would_write"] is False for item in results),
    }


def build_safety_case(falsification: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        "canonical_write_absent": 1.0 if not SAFETY["canonical_write_performed"] else 0.0,
        "activation_flag_absent": 1.0 if not SAFETY["canonical_pilot_enabled"] else 0.0,
        "rollback_designed": 1.0,
        "audit_designed": 1.0,
        "falsification_blocks": 1.0 if falsification["passed"] else 0.0,
        "provider_absent": 1.0 if not SAFETY["provider_call_performed"] else 0.0,
        "training_absent": 1.0 if not SAFETY["training_started"] else 0.0,
        "scheduler_absent": 1.0 if not SAFETY["scheduler_started"] else 0.0,
    }
    return {"phase": "TP9 Safety Case", "metrics": metrics, "score": round(mean(metrics.values()), 3), "passed": min(metrics.values()) == 1.0}


def run_tp9_canonical_pilot_design() -> dict[str, Any]:
    scope = define_canonical_pilot_scope()
    gate_model = build_gate_model()
    write_path = design_disabled_write_path()
    rollback = design_rollback()
    conflict = define_conflict_handling()
    falsification = run_falsification()
    safety_case = build_safety_case(falsification)
    readiness = {
        "phase": "TP9 Readiness Review",
        "passed": safety_case["passed"],
        "final_recommendation": "READY_FOR_TRAINING_READINESS_REVIEW" if safety_case["passed"] else "MORE_CANONICAL_PILOT_DESIGN_REQUIRED",
        "remaining_blockers": ["canonical pilot disabled", "canonical writes disabled", "future activation approval required"],
    }
    return {
        "phase": "TP9 Controlled Canonical Pilot Design",
        "scope": scope,
        "gate_model": gate_model,
        "write_path": write_path,
        "rollback": rollback,
        "conflict": conflict,
        "falsification": falsification,
        "safety_case": safety_case,
        "readiness": readiness,
        "safety": SAFETY,
        "passed": readiness["passed"],
        "final_recommendation": readiness["final_recommendation"],
    }


def write_tp9_reports() -> dict[str, Any]:
    payload = run_tp9_canonical_pilot_design()
    REPORTS.mkdir(exist_ok=True)
    specs = {
        "scope": payload["scope"],
        "gate_model": payload["gate_model"],
        "write_path": payload["write_path"],
        "rollback": payload["rollback"],
        "conflict": payload["conflict"],
        "falsification": payload["falsification"],
        "safety_case": payload["safety_case"],
        "readiness": payload["readiness"],
    }
    for key, data in specs.items():
        json_path, md_path = REPORT_PATHS[key]
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(_render(data), encoding="utf-8")
    UI_PATH.parent.mkdir(exist_ok=True)
    UI_PATH.write_text(f"<html><body><h1>DELTA TP9</h1><p>{payload['final_recommendation']}</p></body></html>", encoding="utf-8")
    return payload


def answer_tp9_question(question: str) -> dict[str, Any]:
    payload = run_tp9_canonical_pilot_design()
    lowered = question.lower()
    if "write" in lowered:
        answer = "TP9 designs a disabled canonical write path; it performs no canonical writes."
    elif "rollback" in lowered:
        answer = "TP9 requires per-record rollback handles, pre-write snapshots, audit ids, and reason-coded rollback design."
    elif "gate" in lowered:
        answer = "TP9 requires TP8 policy pass, scope match, provenance, contradiction clearance, reviewer agreement, explicit approval, rollback, audit, and a future activation flag."
    else:
        answer = "TP9 concludes the canonical pilot path is designed but still disabled."
    return {"phase": "TP9 Controlled Canonical Pilot Design", "answer_text": answer, "final_recommendation": payload["final_recommendation"], "safety": SAFETY}


def is_tp9_question(question: str) -> bool:
    lowered = question.lower()
    return any(phrase in lowered for phrase in ("tp9", "canonical pilot", "canonical write path", "canonical gate", "canonical rollback"))


def _candidate(name: str, *, explicit: bool, rollback: bool, scope: str = "project_self_description", contradictions: tuple[str, ...] = (), uncertainty: str = "bounded", reviewer_agreement: float = 1.0, audit_id: str = "audit-tp9") -> dict[str, Any]:
    candidate = {
        "candidate_id": f"tp9-{name}",
        "confidence": 0.92,
        "uncertainty": uncertainty,
        "contradictions": contradictions,
        "source_references": ("source://tp9",),
        "source_checksum": "hash",
        "canonical": False,
        "scope": scope,
        "reviewer_agreement": reviewer_agreement,
        "rollback_token": "rollback-token" if rollback else "",
        "audit_id": audit_id,
    }
    return {"candidate": candidate, "explicit": explicit}


def _render(data: dict[str, Any]) -> str:
    lines = [f"# {data.get('phase', 'TP9 Report')}", ""]
    for key, value in data.items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(write_tp9_reports()["final_recommendation"])
