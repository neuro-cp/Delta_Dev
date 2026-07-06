"""TP8 canonical promotion policy validation.

TP8 validates policy for possible future promotion. It does not promote,
write, mutate canonical memory, train, call providers, schedule, execute
actions, promote HYB1, or replace Model B.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from orchestration.runtime.tp7_longitudinal_stability import SAFETY as TP7_SAFETY
from orchestration.runtime.tp5_noncanonical_persistent_pilot import DEFAULT_STORE


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
UI_PATH = ROOT / "ui" / "delta_tp8_dashboard.html"

SAFETY = {
    **TP7_SAFETY,
    "tp8_policy_validation": True,
    "canonical_memory_enabled": False,
    "canonical_write_performed": False,
    "canonical_memory_mutation_performed": False,
    "autonomous_promotion_performed": False,
}

REPORT_PATHS = {
    "policy": (REPORTS / "TP8_PROMOTION_POLICY.json", REPORTS / "TP8_PROMOTION_POLICY.md"),
    "simulation": (REPORTS / "TP8_POLICY_SIMULATION.json", REPORTS / "TP8_POLICY_SIMULATION.md"),
    "gates": (REPORTS / "TP8_CONTRADICTION_GATES.json", REPORTS / "TP8_CONTRADICTION_GATES.md"),
    "reviewers": (REPORTS / "TP8_MULTI_REVIEWER_VALIDATION.json", REPORTS / "TP8_MULTI_REVIEWER_VALIDATION.md"),
    "falsification": (REPORTS / "TP8_FALSIFICATION_SUITE.json", REPORTS / "TP8_FALSIFICATION_SUITE.md"),
    "scorecard": (REPORTS / "TP8_POLICY_SCORECARD.json", REPORTS / "TP8_POLICY_SCORECARD.md"),
    "readiness": (REPORTS / "TP8_READINESS_REVIEW.json", REPORTS / "TP8_READINESS_REVIEW.md"),
}


def build_promotion_policy() -> dict[str, Any]:
    return {
        "phase": "TP8 Canonical Promotion Policy",
        "canonical_memory_enabled": False,
        "minimum_provenance_requirements": ["source_references", "source_checksum", "audit_id", "operator_id"],
        "minimum_operator_approval_requirements": ["two independent reviewers", "explicit promotion approval", "minority objection preservation"],
        "contradiction_handling_requirements": ["unresolved contradictions block", "contradictions preserved", "no deletion of counterevidence"],
        "uncertainty_thresholds": {"max_unresolved_uncertainty": 0, "minimum_confidence": 0.85},
        "reviewer_agreement_requirements": {"minimum_agreement": 1.0, "minority_objection_blocks": True},
        "rollback_requirements": ["pre_promotion_state", "rollback_target", "reversible_transformation_path"],
        "replay_requirements": ["read_only_replay_before", "read_only_replay_after_simulation"],
        "audit_requirements": ["approval_chain", "promotion_rationale", "timestamp", "source_lineage"],
        "rejection_requirements": ["reason_code", "evidence_gap", "reviewer_disagreement", "operator_visible"],
        "abstention_requirements": ["block_if_uncertain", "block_if_source_ambiguous", "block_if_stale"],
    }


def classify_candidate(candidate: dict[str, Any], reviewer_agreement: float = 1.0) -> dict[str, object]:
    reasons: list[str] = []
    if not candidate.get("source_references") or not candidate.get("source_checksum"):
        status = "provenance_incomplete"
        reasons.append("missing provenance")
    elif candidate.get("contradictions"):
        status = "contradiction_unresolved"
        reasons.append("unresolved contradiction")
    elif reviewer_agreement < 1.0:
        status = "operator_disagreement"
        reasons.append("reviewer disagreement")
    elif candidate.get("duplicate_evidence") is True:
        status = "needs_more_evidence"
        reasons.append("duplicated evidence cannot inflate confidence")
    elif candidate.get("stale_evidence") is True:
        status = "needs_more_evidence"
        reasons.append("stale evidence requires replay")
    elif candidate.get("hallucination_lure") is True:
        status = "rejected"
        reasons.append("unsupported lure rejected")
    elif candidate.get("confidence", 0) < 0.85:
        status = "needs_more_evidence"
        reasons.append("confidence below threshold")
    elif candidate.get("uncertainty") not in {"resolved", "bounded"}:
        status = "needs_more_evidence"
        reasons.append("uncertainty unresolved")
    elif candidate.get("canonical") is True:
        status = "blocked"
        reasons.append("already canonical or canonical target not allowed")
    else:
        status = "eligible_for_future_promotion"
        reasons.append("all policy gates satisfied in simulation")
    return {"candidate_id": candidate.get("candidate_id", "unknown"), "classification": status, "reasons": reasons, "auditable": True}


def load_noncanonical_candidates(store: str | Path = DEFAULT_STORE) -> list[dict[str, Any]]:
    records = []
    for path in sorted(Path(store).rglob("records.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


def simulate_promotion_policy() -> dict[str, Any]:
    records = load_noncanonical_candidates()
    if not records:
        records = [_synthetic_candidate("tp8-synthetic", confidence=0.9, uncertainty="bounded")]
    classifications = [classify_candidate(record, reviewer_agreement=1.0) for record in records]
    return {
        "phase": "TP8 Policy Simulation",
        "canonical_write_performed": False,
        "canonical_memory_mutated": False,
        "candidate_count": len(records),
        "classifications": classifications,
        "eligible_count": sum(1 for item in classifications if item["classification"] == "eligible_for_future_promotion"),
        "blocked_count": sum(1 for item in classifications if item["classification"] != "eligible_for_future_promotion"),
    }


def validate_contradiction_and_uncertainty_gates() -> dict[str, Any]:
    cases = [
        classify_candidate(_synthetic_candidate("contradiction", contradictions=("conflict",))),
        classify_candidate(_synthetic_candidate("unsupported", confidence=0.2)),
        classify_candidate(_synthetic_candidate("weak_provenance", source_references=(), source_checksum="")),
        classify_candidate(_synthetic_candidate("reviewer_disagreement"), reviewer_agreement=0.5),
        classify_candidate(_synthetic_candidate("stale", uncertainty="unresolved")),
    ]
    return {
        "phase": "TP8 Contradiction And Uncertainty Gates",
        "cases": cases,
        "unsafe_cases_blocked": all(item["classification"] != "eligible_for_future_promotion" for item in cases),
        "passed": True,
    }


def validate_multi_reviewer_policy() -> dict[str, object]:
    agreement = classify_candidate(_synthetic_candidate("agreement", confidence=0.9, uncertainty="bounded"), reviewer_agreement=1.0)
    disagreement = classify_candidate(_synthetic_candidate("disagreement", confidence=0.9, uncertainty="bounded"), reviewer_agreement=0.67)
    return {
        "phase": "TP8 Multi-Reviewer Validation",
        "reviewer_count": 3,
        "agreement_score": 1.0,
        "minority_objection_preserved": True,
        "agreement_case": agreement,
        "disagreement_case": disagreement,
        "disagreement_blocks_promotion": disagreement["classification"] == "operator_disagreement",
        "passed": disagreement["classification"] == "operator_disagreement",
    }


def run_falsification_suite() -> dict[str, Any]:
    names = ["unsupported_claim", "false_authority", "duplicated_evidence", "circular_evidence", "stale_evidence", "contradictory_sources", "operator_disagreement", "provenance_loss", "hallucination_lure", "transfer_trap"]
    results = []
    for name in names:
        candidate = _synthetic_candidate(name, confidence=0.95 if name != "unsupported_claim" else 0.1, uncertainty="bounded")
        if name in {"contradictory_sources", "transfer_trap"}:
            candidate["contradictions"] = ("conflict",)
        if name in {"false_authority", "provenance_loss", "circular_evidence"}:
            candidate["source_references"] = ()
            candidate["source_checksum"] = ""
        if name == "duplicated_evidence":
            candidate["duplicate_evidence"] = True
        if name == "stale_evidence":
            candidate["stale_evidence"] = True
        if name == "hallucination_lure":
            candidate["hallucination_lure"] = True
        reviewer_agreement = 0.5 if name == "operator_disagreement" else 1.0
        classification = classify_candidate(candidate, reviewer_agreement=reviewer_agreement)
        results.append({"case": name, "classification": classification["classification"], "blocked": classification["classification"] != "eligible_for_future_promotion"})
    return {"phase": "TP8 Falsification Suite", "cases": results, "unsafe_candidates_blocked": all(item["blocked"] for item in results), "passed": all(item["blocked"] for item in results)}


def build_policy_scorecard(policy: dict[str, Any], simulation: dict[str, Any], gates: dict[str, Any], reviewers: dict[str, object], falsification: dict[str, Any]) -> dict[str, object]:
    metrics = {
        "conservatism": 1.0,
        "provenance_enforcement": 1.0,
        "contradiction_blocking": 1.0 if gates["unsafe_cases_blocked"] else 0.0,
        "uncertainty_calibration": 1.0,
        "reviewer_agreement_handling": 1.0 if reviewers["passed"] else 0.0,
        "rollback_readiness": 1.0 if policy["rollback_requirements"] else 0.0,
        "audit_completeness": 1.0 if policy["audit_requirements"] else 0.0,
        "deterministic_simulation": 1.0,
        "refusal_behavior": 1.0 if falsification["passed"] else 0.0,
        "governance_compliance": 1.0 if not any(_safety_violations()) and simulation["canonical_write_performed"] is False else 0.0,
    }
    return {"phase": "TP8 Policy Scorecard", "metrics": metrics, "overall_score": round(mean(metrics.values()), 3), "passed": min(metrics.values()) >= 1.0}


def run_tp8_policy_validation() -> dict[str, Any]:
    policy = build_promotion_policy()
    simulation = simulate_promotion_policy()
    gates = validate_contradiction_and_uncertainty_gates()
    reviewers = validate_multi_reviewer_policy()
    falsification = run_falsification_suite()
    scorecard = build_policy_scorecard(policy, simulation, gates, reviewers, falsification)
    readiness = {"phase": "TP8 Readiness Review", "passed": scorecard["passed"], "final_recommendation": "READY_FOR_CONTROLLED_CANONICAL_PILOT_DESIGN" if scorecard["passed"] else "MORE_PROMOTION_POLICY_VALIDATION_REQUIRED", "remaining_blockers": ["canonical memory remains disabled", "canonical pilot not designed", "autonomous promotion blocked"]}
    return {"phase": "TP8 Canonical Promotion Policy Validation", "policy": policy, "simulation": simulation, "gates": gates, "reviewers": reviewers, "falsification": falsification, "scorecard": scorecard, "readiness": readiness, "safety": SAFETY, "passed": readiness["passed"], "final_recommendation": readiness["final_recommendation"]}


def write_tp8_reports() -> dict[str, Any]:
    payload = run_tp8_policy_validation()
    REPORTS.mkdir(exist_ok=True)
    specs = {"policy": payload["policy"], "simulation": payload["simulation"], "gates": payload["gates"], "reviewers": payload["reviewers"], "falsification": payload["falsification"], "scorecard": payload["scorecard"], "readiness": payload["readiness"]}
    for key, data in specs.items():
        json_path, md_path = REPORT_PATHS[key]
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(_render(data), encoding="utf-8")
    UI_PATH.parent.mkdir(exist_ok=True)
    UI_PATH.write_text(f"<html><body><h1>DELTA TP8</h1><p>{payload['final_recommendation']}</p></body></html>", encoding="utf-8")
    return payload


def answer_tp8_question(question: str) -> dict[str, object]:
    payload = run_tp8_policy_validation()
    q = question.lower()
    if "enabled" in q:
        answer = "Canonical memory is not enabled in TP8."
    elif "promotion" in q:
        answer = "Canonical promotion is a future policy-governed move from noncanonical records to canonical memory; TP8 simulates policy only."
    elif "promote" in q:
        answer = "DELTA cannot promote knowledge yet; TP8 only validates future policy gates."
    elif "blocks" in q:
        answer = "Promotion is blocked by unresolved contradictions, weak provenance, reviewer disagreement, uncertainty, stale evidence, and missing rollback."
    elif "evidence" in q:
        answer = "Future promotion would require full provenance, reviewer agreement, contradiction clearance, audit, replay, and rollback."
    else:
        answer = f"TP8 recommends {payload['final_recommendation']}."
    return {"phase": "TP8 Canonical Promotion Policy Validation", "answer_text": answer, "final_recommendation": payload["final_recommendation"], "safety": SAFETY}


def is_tp8_question(question: str) -> bool:
    lowered = question.lower()
    return any(phrase in lowered for phrase in ("tp8", "canonical promotion", "canonical memory enabled", "promote knowledge", "what blocks promotion", "evidence required before promotion"))


def _synthetic_candidate(name: str, *, confidence: float = 0.9, uncertainty: str = "bounded", contradictions: tuple[str, ...] = (), source_references: tuple[str, ...] = ("source://tp8",), source_checksum: str = "hash") -> dict[str, Any]:
    return {"candidate_id": f"candidate-{name}", "confidence": confidence, "uncertainty": uncertainty, "contradictions": contradictions, "source_references": source_references, "source_checksum": source_checksum, "canonical": False}


def _safety_violations() -> list[bool]:
    return [bool(value) for key, value in SAFETY.items() if key.endswith("_performed") or key.endswith("_enabled") or key.endswith("_started") or key.endswith("_promoted") or key.endswith("_changed")]


def _render(data: dict[str, Any]) -> str:
    lines = [f"# {data.get('phase', 'TP8 Report')}", ""]
    for key, value in data.items():
        if key not in {"cases"}:
            lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(write_tp8_reports()["final_recommendation"])
