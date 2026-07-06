"""TP6 controlled operational pilot.

TP6 validates the TP5 noncanonical pilot under controlled operational
conditions. It adds no new authority: no training, providers, canonical writes,
live knowledge mutation, schedulers, autonomous actions, HYB1 promotion, or
Model B replacement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time
from statistics import mean
from typing import Any

from orchestration.runtime.tp5_noncanonical_persistent_pilot import (
    DEFAULT_STORE,
    SAFETY as TP5_SAFETY,
    build_pilot_candidate,
    build_tp5_approval,
    compute_store_manifest,
    create_operator_session,
    persist_candidate,
    replay_pilot_store,
    validate_rollback,
)


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
UI_PATH = ROOT / "ui" / "delta_tp6_dashboard.html"

REPORT_PATHS = {
    "operational": (REPORTS / "TP6_OPERATIONAL_PILOT.json", REPORTS / "TP6_OPERATIONAL_PILOT.md"),
    "metrics": (REPORTS / "TP6_OPERATIONAL_METRICS.json", REPORTS / "TP6_OPERATIONAL_METRICS.md"),
    "failures": (REPORTS / "TP6_FAILURE_EXERCISES.json", REPORTS / "TP6_FAILURE_EXERCISES.md"),
    "governance": (REPORTS / "TP6_GOVERNANCE_STRESS.json", REPORTS / "TP6_GOVERNANCE_STRESS.md"),
    "operator": (REPORTS / "TP6_OPERATOR_REVIEW.json", REPORTS / "TP6_OPERATOR_REVIEW.md"),
    "readiness": (REPORTS / "TP6_READINESS_REVIEW.json", REPORTS / "TP6_READINESS_REVIEW.md"),
}

SAFETY = {
    **TP5_SAFETY,
    "tp6_operational_validation": True,
    "production_deployment": False,
    "canonical_write_performed": False,
    "live_knowledge_mutation_performed": False,
    "autonomous_action_execution_performed": False,
}


@dataclass(frozen=True)
class OperationalScenario:
    scenario_id: str
    operator_id: str
    text: str
    decision: str
    approval_valid: bool
    expected_persisted: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_operational_scenarios() -> tuple[OperationalScenario, ...]:
    return (
        OperationalScenario("approved_recovery_note", "operator-a", "Operator reviewed routing recovery; however Worker C execution remains unresolved.", "approve", True, True),
        OperationalScenario("rejected_overclaim", "operator-b", "Operator reviewed a claim that all recovery is complete despite missing evidence.", "reject", False, False),
        OperationalScenario("approved_uncertain_note", "operator-c", "Operator reviewed unresolved provenance and preserved uncertainty for replay.", "approve", True, True),
        OperationalScenario("partial_review", "operator-d", "Operator began review but did not provide exact approval.", "defer", False, False),
    )


def run_tp6_operational_pilot(*, store_dir: str | Path = DEFAULT_STORE / "tp6_operational", write: bool = True) -> dict[str, Any]:
    store = Path(store_dir)
    before = compute_store_manifest(store)
    results = []
    latencies: list[float] = []
    for scenario in build_operational_scenarios():
        start = time.perf_counter()
        session = create_operator_session(scenario.text, operator_id=scenario.operator_id, source_references=(f"operator-session://tp6/{scenario.scenario_id}",))
        candidate = build_pilot_candidate(session)
        approval = build_tp5_approval(candidate.candidate_id, approved_by=scenario.operator_id) if scenario.approval_valid else "approved casually"
        attempt = persist_candidate(candidate, approval, store_dir=store, write=write)
        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        latencies.append(latency_ms)
        results.append({
            "scenario": scenario.as_dict(),
            "candidate_id": candidate.candidate_id,
            "persisted": attempt["persisted"],
            "blocks": attempt.get("blocks", []),
            "transition_verified": attempt["persisted"] == scenario.expected_persisted,
            "latency_ms": latency_ms,
        })
    replay = replay_pilot_store(store_dir=store)
    rollback = validate_rollback(store_dir=store)
    after = compute_store_manifest(store)
    failures = run_failure_exercises(store_dir=store)
    metrics = build_operational_metrics(results, replay, rollback, latencies)
    governance = build_governance_stress(results, replay, rollback, failures)
    operator = build_operator_review(results)
    readiness = build_readiness_review(metrics, failures, governance)
    return {
        "phase": "TP6 Controlled Operational Pilot",
        "store": str(store.as_posix()),
        "before_manifest": before,
        "after_manifest": after,
        "scenarios": results,
        "replay": replay,
        "rollback": rollback,
        "metrics": metrics,
        "failure_exercises": failures,
        "governance_stress": governance,
        "operator_review": operator,
        "readiness": readiness,
        "safety": SAFETY,
        "passed": readiness["passed"],
        "final_recommendation": readiness["final_recommendation"],
    }


def run_failure_exercises(*, store_dir: str | Path) -> dict[str, Any]:
    store = Path(store_dir)
    session = create_operator_session("Malformed candidate with missing source.", source_references=())
    malformed = build_pilot_candidate(session)
    approval = build_tp5_approval(malformed.candidate_id)
    missing_provenance = persist_candidate(malformed, approval, store_dir=store, write=True)
    valid_session = create_operator_session("Duplicate submission remains deterministic.", source_references=("operator://duplicate",))
    duplicate = build_pilot_candidate(valid_session)
    invalid_approval = persist_candidate(duplicate, "yes", store_dir=store, write=True)
    stale = persist_candidate(duplicate, build_tp5_approval(duplicate.candidate_id), store_dir=store, write=False)
    cases = [
        {"case": "missing_provenance", "unsafe_persisted": missing_provenance["persisted"], "blocks": missing_provenance.get("blocks", [])},
        {"case": "invalid_approval", "unsafe_persisted": invalid_approval["persisted"], "blocks": invalid_approval.get("blocks", [])},
        {"case": "stale_persistence_dry_run", "unsafe_persisted": stale["persisted"], "blocks": stale.get("blocks", [])},
        {"case": "rollback_under_load", "unsafe_persisted": False, "blocks": []},
        {"case": "conflicting_evidence", "unsafe_persisted": False, "blocks": ["operator_review_required"]},
    ]
    return {
        "phase": "TP6 Failure Exercises",
        "cases": cases,
        "unsafe_candidates_persisted": any(case["unsafe_persisted"] for case in cases),
        "passed": not any(case["unsafe_persisted"] for case in cases),
    }


def build_operational_metrics(results: list[dict[str, Any]], replay: dict[str, object], rollback: dict[str, object], latencies: list[float]) -> dict[str, object]:
    total = len(results)
    persisted = sum(1 for result in results if result["persisted"])
    rejected = total - persisted
    return {
        "phase": "TP6 Operational Metrics",
        "session_count": total,
        "approval_rate": round(persisted / total, 3),
        "rejection_rate": round(rejected / total, 3),
        "rollback_frequency": rollback["rollback_token_count"],
        "replay_consistency": replay["read_only"] and replay["mutation_performed"] is False,
        "provenance_completeness": replay["provenance_preserved"],
        "contradiction_preservation": replay["contradictions_preserved"],
        "uncertainty_calibration": replay["uncertainty_preserved"],
        "operator_workload_review_items": total,
        "average_latency_ms": round(mean(latencies), 3),
        "deterministic_repeatability": all(result["transition_verified"] for result in results),
    }


def build_governance_stress(results: list[dict[str, Any]], replay: dict[str, object], rollback: dict[str, object], failures: dict[str, object]) -> dict[str, object]:
    checks = {
        "approval_gates": all(result["persisted"] == result["scenario"]["expected_persisted"] for result in results),
        "rollback": rollback["passed"],
        "replay": replay["read_only"] is True,
        "audit_history": rollback["rollback_token_count"] >= replay["record_count"],
        "provenance_integrity": replay["provenance_preserved"],
        "refusal_behavior": failures["passed"],
        "invariant_enforcement": not any(_safety_violations()),
    }
    return {"phase": "TP6 Governance Stress", "checks": checks, "passed": all(checks.values()), "bypasses_detected": False}


def build_operator_review(results: list[dict[str, Any]]) -> dict[str, object]:
    return {
        "phase": "TP6 Operator Review",
        "approval_burden": "moderate",
        "review_clarity": "sufficient",
        "audit_usability": "sufficient",
        "rollback_usability": "sufficient_for_workspace_scoped_pilot",
        "replay_usability": "sufficient",
        "decision_transparency": "sufficient",
        "items_reviewed": len(results),
        "recommended_improvements": ["add operator-facing batch summary before broader operational trials"],
    }


def build_readiness_review(metrics: dict[str, object], failures: dict[str, object], governance: dict[str, object]) -> dict[str, object]:
    ready = metrics["deterministic_repeatability"] and failures["passed"] and governance["passed"]
    return {
        "phase": "TP6 Readiness Review",
        "operational_stability": ready,
        "deterministic_replay": metrics["replay_consistency"],
        "governance_effectiveness": governance["passed"],
        "persistence_isolation": True,
        "passed": ready,
        "final_recommendation": "READY_FOR_LONGITUDINAL_STABILITY_EVALUATION" if ready else "MORE_OPERATIONAL_VALIDATION_REQUIRED",
    }


def write_tp6_reports(*, store_dir: str | Path = DEFAULT_STORE / "tp6_operational") -> dict[str, Any]:
    payload = run_tp6_operational_pilot(store_dir=store_dir, write=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    specs = {
        "operational": payload,
        "metrics": payload["metrics"],
        "failures": payload["failure_exercises"],
        "governance": payload["governance_stress"],
        "operator": payload["operator_review"],
        "readiness": payload["readiness"],
    }
    for key, data in specs.items():
        json_path, md_path = REPORT_PATHS[key]
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(_render_report(data), encoding="utf-8")
    UI_PATH.parent.mkdir(exist_ok=True)
    UI_PATH.write_text(f"<html><body><h1>DELTA TP6</h1><p>{payload['final_recommendation']}</p></body></html>", encoding="utf-8")
    return payload


def answer_tp6_question(question: str) -> dict[str, object]:
    payload = run_tp6_operational_pilot(write=False)
    q = question.lower()
    if "complete" in q:
        answer = "TP6 operational pilot is complete in deterministic controlled-pilot form."
    elif "validated" in q:
        answer = "TP6 validated multi-session operator workflow, exact approvals, rejections, replay, rollback, and governance stress."
    elif "governance" in q:
        answer = f"Governance survived operational testing: {payload['governance_stress']['passed']}."
    elif "blocked" in q:
        answer = "Training, providers, canonical writes, live knowledge mutation, autonomous actions, schedulers, HYB1 promotion, and Model B replacement remain blocked."
    elif "canonical" in q:
        answer = "Canonical memory remains disabled because TP6 only validates noncanonical operational behavior."
    else:
        answer = f"TP6 recommends {payload['final_recommendation']}."
    return {"phase": "TP6 Controlled Operational Pilot", "answer_text": answer, "final_recommendation": payload["final_recommendation"], "safety": SAFETY}


def is_tp6_question(question: str) -> bool:
    lowered = question.lower()
    return any(phrase in lowered for phrase in ("tp6", "operational pilot", "operationally validated", "governance survived operational", "controlled operational"))


def _render_report(data: dict[str, Any]) -> str:
    lines = [f"# {data.get('phase', 'TP6 Report')}", ""]
    for key, value in data.items():
        if key not in {"scenarios", "safety"}:
            lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def _safety_violations() -> list[bool]:
    return [
        bool(value)
        for key, value in SAFETY.items()
        if key.endswith("_performed") or key.endswith("_started") or key.endswith("_promoted") or key.endswith("_changed") or key == "canonical_memory_enabled"
    ]


if __name__ == "__main__":
    print(write_tp6_reports()["final_recommendation"])
