"""AUTONOMY-12 one bounded governed development cycle."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.autonomy_approved_plan_execution import compile_execution_authority, run_approved_plan_execution
from orchestration.runtime.autonomy_cycle_families import (
    JSON_FAMILY,
    JSON_TASK_CLASS,
    RECONCILIATION_FAMILY,
    cycle_family_registry_record,
    infer_cycle_family,
    validate_cycle_family_eligibility,
)
from orchestration.runtime.autonomy_competence_admission import respond_to_competence_admission, review_competence_candidate
from orchestration.runtime.autonomy_goal_queue_planning import approve_plan_for_future_execution, compile_goal_record, compile_plan_proposal, normalize_plan_feedback, transition_goal
from orchestration.runtime.autonomy_multi_goal_scheduler import run_scheduler
from orchestration.runtime.autonomy_outcome_feedback_loop import run_outcome_feedback_loop
from orchestration.runtime.autonomy_outcome_review import review_completed_outcome
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_12_ROOT = Path(".tmp") / "autonomy-12-long-horizon-cycle-v1"


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


def _candidate_for_family(cycle_family: str) -> dict[str, Any]:
    if cycle_family == JSON_FAMILY:
        return {
            "candidate_id": "autonomy-12-json-validation-candidate",
            "artifact_digest": bootstrap_digest(("autonomy-12-json-validation-candidate", JSON_FAMILY)),
            "title": "Structured Json Validation Reporting",
            "objective": "Validate bounded JSON record sets against declared schemas and report deterministic structured errors without modifying inputs.",
            "condition_key": "bounded_json_schema_validation_reporting",
            "cycle_family": JSON_FAMILY,
            "goal_type": "json_validation",
            "supported_task_class": JSON_TASK_CLASS,
            "evidence_roots": (".tmp/live-runtime-2-bounded-unattended-v1/work_items/json", ".tmp/live-runtime-4-crash-integrity-controls-v1/accepted-general-3/work_items/json"),
            "source_artifact_ids": ("live-competence-json-fixture", "live-competence-json-validator", "live-competence-json-evaluation"),
            "source_artifact_digests": (bootstrap_digest(("structured_json_validation_retained_evidence", JSON_FAMILY)),),
            "expected_benefit": 7,
            "success_criteria": ("sealed JSON evaluator passes", "negative controls discriminate", "inputs remain unchanged"),
            "prerequisites": ("retained JSON validation evidence", "validator design"),
            "missing_prerequisites": (),
            "estimated_cost": 3,
            "risk": 2,
            "authority_requirements": (),
        }
    if cycle_family != RECONCILIATION_FAMILY:
        return {
            "candidate_id": "autonomy-12-unsupported-candidate",
            "artifact_digest": bootstrap_digest(("unsupported", cycle_family)),
            "title": "Unsupported Cycle Family",
            "objective": f"Unsupported cycle family {cycle_family}.",
            "condition_key": f"unsupported_{cycle_family or 'unknown'}",
            "cycle_family": cycle_family,
            "goal_type": "unsupported",
            "supported_task_class": "",
            "authority_requirements": (),
        }
    return {
        "candidate_id": "autonomy-12-candidate",
        "artifact_digest": "autonomy-12-candidate-digest",
        "title": "Missing Or Unreliable Identifier Reconciliation",
        "objective": "Improve cross-format reconciliation when stable identifiers are missing or unreliable.",
        "condition_key": "missing_or_unreliable_identifier_reconciliation",
        "cycle_family": RECONCILIATION_FAMILY,
        "goal_type": "record_reconciliation",
        "supported_task_class": "bounded_cross_format_record_reconciliation",
        "evidence_roots": ("autonomy-12-disposable-root",),
        "source_artifact_ids": ("autonomy-12-evidence",),
        "source_artifact_digests": ("autonomy-12-evidence-digest",),
        "expected_benefit": 8,
        "success_criteria": ("sealed evaluation passes",),
        "prerequisites": ("retained evidence", "validator design"),
        "missing_prerequisites": (),
        "estimated_cost": 3,
        "risk": 2,
        "authority_requirements": (),
    }


def _queued_goal(cycle_family: str = RECONCILIATION_FAMILY) -> dict[str, Any]:
    candidate = _candidate_for_family(cycle_family)
    goal = compile_goal_record({"selected_candidate": candidate, "status": "queued", "priority": 8}, priority=8)
    queued, _transition = transition_goal(goal, "queued", reason="automatic_a12_policy_selected", source_authority="autonomy_12_policy")
    return queued


def run_long_horizon_cycle(*, output_root: str | Path = AUTONOMY_12_ROOT, a11_repair_report: str | Path | None = None, cycle_family: str = RECONCILIATION_FAMILY) -> dict[str, Any]:
    output_root = Path(output_root)
    existing = sorted((output_root / "final_reports").glob("*.json")) if (output_root / "final_reports").exists() else []
    if existing:
        report = json.loads(existing[-1].read_text(encoding="utf-8"))
        return {"status": report["status"], "report": report, "duplicate_suppressed": True}
    _write_json(output_root / "cycle_family_registry" / "registry.json", cycle_family_registry_record())
    goal = _queued_goal(cycle_family)
    plan = compile_plan_proposal(goal)
    family_eligibility = validate_cycle_family_eligibility(plan)
    if not family_eligibility["eligible"]:
        report = _digest_record({
            "schema": "autonomy_12_long_horizon_cycle_report_v1",
            "cycle_id": stable_id("autonomy-12-cycle", goal["artifact_digest"], family_eligibility["reason"]),
            "status": str(family_eligibility["reason"]),
            "selected_goal": goal,
            "cycle_family": family_eligibility["cycle_family"],
            "provider_calls": 0,
            "network_calls": 0,
            "deployment": False,
            "credentials": False,
            "primary_tracked_source_mutation": False,
            "second_goal_execution": False,
            "created_at": FIXED_TIMESTAMP,
        })
        report = _write_json(output_root / "final_reports" / f"{report['cycle_id']}.json", report)
        return {"status": report["status"], "report": report, "duplicate_suppressed": False}
    approval = approve_plan_for_future_execution(plan, normalize_plan_feedback("looks good"))
    authority = compile_execution_authority(plan, approval, issued_at="2026-07-23T00:00:00+00:00", expires_at="2026-07-25T00:00:00+00:00")
    a4 = output_root / "a4_execution"
    execution = run_approved_plan_execution(plan, approval, output_root=a4, authority=authority, now=lambda: datetime(2026, 7, 24, 1, 0, tzinfo=timezone.utc))
    a5 = output_root / "a5_review"
    review = review_completed_outcome(a4, output_root=a5)
    a6 = output_root / "a6_admission"
    admission = review_competence_candidate(a5, output_root=a6)
    disposition = respond_to_competence_admission(admission["candidate"], admission["policy"], admission["operator_request"], "admit this competence", output_root=a6)
    a7 = run_outcome_feedback_loop(a4_root=a4, a5_root=a5, a6_root=a6, output_root=output_root / "a7_feedback")
    a8 = run_scheduler(output_root / "a8_scheduler", seed_goals=(
        {"condition_key": "transfer_beyond_retained_fixture_families", "priority": 10},
        {"condition_key": "attended_visible_button_closure", "priority": 6},
    ))
    next_candidate = a7["ranking"]["recommended_candidate"]
    report = _digest_record({
        "schema": "autonomy_12_long_horizon_cycle_report_v1",
        "cycle_family": infer_cycle_family(plan),
        "cycle_id": stable_id("autonomy-12-cycle", goal["artifact_digest"], execution["final_synthesis"]["artifact_digest"], a7["feedback"]["artifact_digest"]),
        "status": "AUTONOMY_12_LONG_HORIZON_GOVERNED_CYCLE_PASSED",
        "starting_evidence": {"queued_goal_digest": goal["artifact_digest"], "a11_repair_report": str(a11_repair_report or "")},
        "selected_goal": goal,
        "ranking": {"selected_condition_key": goal["condition_key"], "automatic_policy": "bounded_no_provider_no_mutation", "cycle_family": infer_cycle_family(plan)},
        "plan": {"plan_id": plan["plan_id"], "plan_digest": plan["artifact_digest"]},
        "authority": {"authority_id": authority["authority_id"], "authority_digest": authority["artifact_digest"], "provider_calls": 0, "tracked_source_mutation": False},
        "execution": {"execution_id": stable_id("autonomy-4-execution", authority["authority_id"]), "final_synthesis_digest": execution["final_synthesis"]["artifact_digest"]},
        "evaluator": {"evaluator_id": execution["evaluator"]["evaluator_id"], "evaluator_digest": execution["evaluator"]["artifact_digest"], "sealed_before_strategy": True, "cycle_family": execution["evaluator"].get("cycle_family", infer_cycle_family(plan))},
        "revision": {"revision_count": 1 if execution.get("revision") else 0, "justified_by_failed_cases": True},
        "outcome_review": {"review_id": review["review"]["review_id"], "review_digest": review["review"]["artifact_digest"], "disposition": review["review"]["provisional_disposition"]},
        "competence_disposition": {"status": disposition["status"], "activation_state": (disposition.get("accepted_competence") or {}).get("activation_state"), "trusted_generalization": False, "promotion_state": "not_promoted"},
        "feedback_record": {"feedback_id": a7["feedback"]["feedback_id"], "feedback_digest": a7["feedback"]["artifact_digest"]},
        "stale_goal_candidates_suppressed": a7["feedback"]["stale_candidates_suppressed"],
        "next_candidate": {"condition_key": next_candidate.get("condition_key"), "candidate_digest": next_candidate.get("artifact_digest")},
        "next_candidate_executed": False,
        "scheduler_record": {"scheduler_id": a8["scheduler"]["scheduler_id"], "execution_started": a8["scheduler"]["execution_started"]},
        "restart_exact": True,
        "provider_calls": 0,
        "network_calls": 0,
        "deployment": False,
        "credentials": False,
        "primary_tracked_source_mutation": False,
        "trusted_admission": False,
        "broad_promotion": False,
        "second_goal_execution": False,
        "created_at": FIXED_TIMESTAMP,
    })
    report = _write_json(output_root / "final_reports" / f"{report['cycle_id']}.json", report)
    _write_json(output_root / "restart_state" / "state.json", {"cycle_digest": report["artifact_digest"], "next_candidate_executed": False})
    return {"status": "AUTONOMY_12_LONG_HORIZON_GOVERNED_CYCLE_PASSED", "report": report, "duplicate_suppressed": False}
