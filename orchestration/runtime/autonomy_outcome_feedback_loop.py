"""AUTONOMY-7 feedback from reviewed outcomes into goal discovery."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.autonomy_goal_prioritization import compile_ranking
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_7_ROOT = Path(".tmp") / "autonomy-7-outcome-feedback-v1"


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return dict(payload)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _latest(root: Path, rel: str) -> dict[str, Any] | None:
    files = sorted((root / rel).glob("*.json")) if (root / rel).exists() else []
    return _read_json(files[-1]) if files else None


def _latest_input_plan(root: Path) -> dict[str, Any]:
    plans = sorted((root / "inputs").glob("*.plan.json")) if (root / "inputs").exists() else []
    return _read_json(plans[-1]) if plans else {}


def _goal_evidence(root: Path, name: str, **overrides: object) -> Path:
    record = {
        "schema": "autonomy_2_counterfactual_goal_evidence_v1",
        "artifact_id": name,
        "artifact_digest": stable_id("autonomy-7-evidence-digest", name, overrides),
        "signal_type": "unresolved_capability_gap",
        "condition_key": name,
        "title": name.replace("_", " ").title(),
        "objective": f"Improve {name.replace('_', ' ')}.",
        "unresolved_condition": f"{name} remains unresolved",
        "current_capability_state": "unresolved",
        "prerequisites": ("retained A4/A5/A6 evidence",),
        "missing_prerequisites": (),
        "estimated_work_class": "bounded_developmental_goal",
        "expected_benefit": 6,
        "operator_relevance": 6,
        "urgency": 0,
        "evidence_strength": 6,
        "readiness": 6,
        "estimated_cost": 4,
        "risk": 4,
        "reversibility": 8,
        "recurrence": 1,
        "authority_requirements": (),
        **overrides,
    }
    _write_json(root / f"{name}.json", record)
    return root


def run_outcome_feedback_loop(
    *,
    a4_root: str | Path,
    a5_root: str | Path,
    a6_root: str | Path,
    output_root: str | Path = AUTONOMY_7_ROOT,
) -> dict[str, Any]:
    output_root = Path(output_root)
    a4_root = Path(a4_root)
    a5_root = Path(a5_root)
    a6_root = Path(a6_root)
    existing = _latest(output_root, "feedback_records")
    if existing:
        ranking = _latest(output_root, "rankings") or {}
        return {"status": "AUTONOMY_7_OUTCOME_FEEDBACK_LOOP_PASSED", "feedback": existing, "ranking": ranking, "duplicate_suppressed": True}
    final = _latest(a4_root, "final_synthesis") or {}
    plan = _latest_input_plan(a4_root)
    review = _latest(a5_root, "reviews") or {}
    accepted = _latest(a6_root, "accepted_competencies")
    response = _latest(a6_root, "responses") or {}
    if not final or not review:
        feedback = _digest_record({
            "schema": "autonomy_7_feedback_record_v1",
            "feedback_id": stable_id("autonomy-7-feedback", str(a4_root), str(a5_root), "missing_evidence"),
            "goal_transition": "unresolved",
            "integrity_stop": True,
            "first_missing_transition": "missing_a4_or_a5_review",
            "created_at": FIXED_TIMESTAMP,
        })
        _write_json(output_root / "feedback_records" / f"{feedback['feedback_id']}.json", feedback)
        return {"status": "AUTONOMY_7_OUTCOME_FEEDBACK_LOOP_INTEGRITY_STOP", "feedback": feedback}
    admitted = bool(accepted and accepted.get("admission_status") == "accepted_bounded_competence")
    goal_transition = "resolved" if admitted else "retained_provisional"
    resolved_condition = str(plan.get("condition_key") or "missing_or_unreliable_identifier_reconciliation")
    resolved = (resolved_condition,) if admitted else ()
    unresolved = tuple(review.get("remaining_limitations") or ()) + (() if admitted else ("competence_not_admitted",))
    capability_state = _digest_record({
        "schema": "autonomy_7_capability_state_transition_v1",
        "capability_state_id": stable_id("autonomy-7-capability-state", review.get("review_id"), accepted.get("competence_id") if accepted else response.get("response_id")),
        "source_a6_disposition": "accepted_bounded_competence" if admitted else str(response.get("operator_action") or "retained_provisional"),
        "condition_state": "accepted_bounded_inactive" if admitted else "provisional_evidence_only",
        "activation_state": accepted.get("activation_state") if accepted else "not_admitted",
        "trusted_generalization": False,
        "promotion_state": "not_promoted",
        "created_at": FIXED_TIMESTAMP,
    })
    evidence_root = output_root / "next_goal_evidence"
    if admitted:
        _goal_evidence(
            evidence_root,
            resolved_condition,
            already_resolved=True,
            resolves_conditions=(resolved_condition,),
            current_capability_state="accepted_bounded_inactive",
            expected_benefit=0,
        )
    _goal_evidence(
        evidence_root,
        "transfer_beyond_retained_fixture_families",
        title="Transfer Beyond Retained Fixture Families",
        objective="Evaluate whether bounded reconciliation transfers beyond retained fixture families.",
        unresolved_condition="A6 competence does not prove performance beyond retained fixture families.",
        current_capability_state="limitation_retained",
        expected_benefit=8,
        evidence_strength=7,
        readiness=8,
        estimated_cost=3,
        risk=3,
    )
    _goal_evidence(
        evidence_root,
        "attended_visible_button_closure",
        title="Attended Visible Button Closure",
        objective="Complete the separately unresolved attended visible-button evidence pilot.",
        unresolved_condition="A4 attended visible-button closure remains separately unresolved.",
        current_capability_state="ui_evidence_gap",
        expected_benefit=6,
        evidence_strength=8,
        readiness=7,
        estimated_cost=4,
        risk=3,
    )
    ranking = compile_ranking(evidence_roots=(evidence_root,), goal_store=output_root / "closed_goals")
    feedback = _digest_record({
        "schema": "autonomy_7_feedback_record_v1",
        "feedback_id": stable_id("autonomy-7-feedback", final.get("artifact_digest"), review.get("artifact_digest"), accepted.get("artifact_digest") if accepted else response.get("artifact_digest")),
        "source_a4_execution": final.get("synthesis_id"),
        "source_a4_execution_digest": final.get("artifact_digest"),
        "source_a5_review": review.get("review_id"),
        "source_a5_review_digest": review.get("artifact_digest"),
        "source_a6_disposition": "accepted_bounded_competence" if admitted else "retained_provisional",
        "resolved_condition_keys": resolved,
        "unresolved_condition_keys": unresolved,
        "new_limitations": tuple(review.get("remaining_limitations") or ()),
        "stale_candidates_suppressed": (resolved_condition,) if admitted else (),
        "active_candidates_retained": tuple(candidate.get("condition_key") for candidate in tuple(ranking.get("candidates") or ()) if candidate.get("eligibility_disposition") == "eligible"),
        "goal_transition": goal_transition,
        "capability_state_transition": capability_state,
        "next_goal_discovery_input": str(evidence_root),
        "execution_started": False,
        "provider_calls": 0,
        "network_calls": 0,
        "source_mutation": False,
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "capability_state" / f"{capability_state['capability_state_id']}.json", capability_state)
    feedback = _write_json(output_root / "feedback_records" / f"{feedback['feedback_id']}.json", feedback)
    ranking = _write_json(output_root / "rankings" / f"{ranking['ranking_id']}.json", ranking)
    return {"status": "AUTONOMY_7_OUTCOME_FEEDBACK_LOOP_PASSED", "feedback": feedback, "ranking": ranking, "duplicate_suppressed": False}
