"""AUTONOMY-3 durable goal queue and proposal-only plan construction."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP, compile_operator_request_card


AUTONOMY_3_ROOT = Path(".tmp") / "autonomy-3-goal-queue-planning-v1"
AUTONOMY_3_STATUS = "AUTONOMY_3_PLAN_WAITING_FOR_OPERATOR"
ALLOWED_QUEUE_STATES = {
    "approved",
    "queued",
    "planning",
    "waiting_for_operator",
    "paused",
    "deferred",
    "blocked_dependency",
    "blocked_capability",
    "rejected",
    "superseded",
    "completed",
}
VALID_TRANSITIONS = {
    "approved": {"queued"},
    "queued": {"planning", "deferred", "blocked_dependency", "blocked_capability"},
    "planning": {"waiting_for_operator"},
    "waiting_for_operator": {"queued", "paused", "rejected"},
}
PROHIBITED_AUTHORITY = {"network_expansion", "tracked_source_mutation", "deployment", "credentials", "trusted_admission", "capability_promotion"}


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(payload)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return data


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def normalize_objective(text: str) -> str:
    return " ".join(str(text).lower().strip().split())


def compile_goal_record(selection: Mapping[str, Any], *, priority: int = 0) -> dict[str, Any]:
    candidate = dict(selection.get("selected_candidate") or {})
    objective = str(candidate.get("objective") or selection.get("objective") or "")
    condition_key = str(candidate.get("condition_key") or selection.get("selected_condition_key") or "")
    record = {
        "schema": "autonomy_3_goal_queue_record_v1",
        "goal_id": stable_id("autonomy-3-goal", selection.get("selected_candidate_id"), selection.get("ranking_digest"), objective),
        "selected_candidate_id": str(selection.get("selected_candidate_id") or candidate.get("candidate_id") or ""),
        "selected_candidate_digest": str(selection.get("selected_candidate_digest") or candidate.get("artifact_digest") or ""),
        "ranking_id": str(selection.get("ranking_id") or ""),
        "ranking_digest": str(selection.get("ranking_digest") or ""),
        "operator_preference_record": dict(selection.get("operator_preference_record") or {}),
        "operator_selection_record": dict(selection),
        "title": str(candidate.get("title") or selection.get("title") or condition_key.replace("_", " ").title()),
        "objective": objective,
        "normalized_objective": normalize_objective(objective),
        "condition_key": condition_key,
        "cycle_family": str(candidate.get("cycle_family") or ""),
        "goal_type": str(candidate.get("goal_type") or ""),
        "supported_task_class": str(candidate.get("supported_task_class") or ""),
        "evidence_roots": tuple(candidate.get("evidence_roots") or ()),
        "source_artifact_ids": tuple(candidate.get("source_artifact_ids") or ()),
        "source_artifact_digests": tuple(candidate.get("source_artifact_digests") or ()),
        "expected_benefit": int(candidate.get("expected_benefit") or 0),
        "success_criteria": tuple(candidate.get("success_criteria") or ()),
        "prerequisites": tuple(candidate.get("prerequisites") or ()),
        "missing_prerequisites": tuple(candidate.get("missing_prerequisites") or ()),
        "estimated_cost": int(candidate.get("estimated_cost") or 0),
        "risk": int(candidate.get("risk") or 0),
        "authority_requirements": tuple(candidate.get("authority_requirements") or ()),
        "current_queue_state": "approved",
        "priority": int(priority),
        "execution_started": False,
        "learning_started": False,
        "trusted": False,
        "promoted": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def transition_goal(goal: Mapping[str, Any], next_state: str, *, reason: str, source_authority: str) -> tuple[dict[str, Any], dict[str, Any]]:
    previous = str(goal.get("current_queue_state") or "")
    if next_state not in ALLOWED_QUEUE_STATES:
        raise ValueError("queue_state_invalid")
    if next_state not in VALID_TRANSITIONS.get(previous, set()):
        raise ValueError("queue_transition_invalid")
    updated = _digest_record({**dict(goal), "current_queue_state": next_state})
    transition = _digest_record({
        "schema": "autonomy_3_goal_queue_transition_v1",
        "transition_id": stable_id("autonomy-3-transition", goal.get("goal_id"), previous, next_state, reason),
        "goal_id": goal["goal_id"],
        "previous_state": previous,
        "next_state": next_state,
        "reason": reason,
        "source_authority": source_authority,
        "created_at": FIXED_TIMESTAMP,
    })
    return updated, transition


def dedupe_or_plan_disposition(goal: Mapping[str, Any], existing_goals: Sequence[Mapping[str, Any]], resolved_conditions: Sequence[str] = ()) -> dict[str, Any]:
    condition = str(goal.get("condition_key") or "")
    objective = str(goal.get("normalized_objective") or normalize_objective(str(goal.get("objective") or "")))
    for existing in existing_goals:
        if existing.get("selected_candidate_digest") == goal.get("selected_candidate_digest") or existing.get("normalized_objective") == objective or existing.get("condition_key") == condition:
            return _digest_record({"schema": "autonomy_3_goal_planning_disposition_v1", "goal_id": goal["goal_id"], "disposition": "duplicate_suppressed", "matched_goal_id": existing.get("goal_id", ""), "created_at": FIXED_TIMESTAMP})
    if condition in set(resolved_conditions):
        return _digest_record({"schema": "autonomy_3_goal_planning_disposition_v1", "goal_id": goal["goal_id"], "disposition": "resolved_before_planning", "created_at": FIXED_TIMESTAMP})
    if PROHIBITED_AUTHORITY.intersection(tuple(goal.get("authority_requirements") or ())):
        return _digest_record({"schema": "autonomy_3_goal_planning_disposition_v1", "goal_id": goal["goal_id"], "disposition": "blocked_prohibited_authority", "created_at": FIXED_TIMESTAMP})
    return _digest_record({"schema": "autonomy_3_goal_planning_disposition_v1", "goal_id": goal["goal_id"], "disposition": "eligible_for_planning", "created_at": FIXED_TIMESTAMP})


def select_goal_for_planning(goals: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    eligible = [dict(goal) for goal in goals if goal.get("current_queue_state") == "queued"]
    if not eligible:
        return None
    return sorted(eligible, key=lambda goal: (-int(goal.get("priority") or 0), str(goal.get("created_at") or ""), str(goal.get("goal_id"))))[0]


def _work_graph_for(goal: Mapping[str, Any], *, budget: Mapping[str, Any] | None = None, preference: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
    budget = dict(budget or {})
    low_budget = int(budget.get("max_work_items") or 6) <= 4 or preference and preference.get("priority") == "low_cost"
    condition = str(goal.get("condition_key") or "")
    if "maint" in condition or "summary" in condition:
        specs = [
            ("inspect_reports", "Inspect retained summaries and operator-visible reports", "evidence_inspection"),
            ("define_quality_checks", "Define readability and provenance checks", "independent_evaluation"),
            ("draft_update", "Construct a bounded summary improvement proposal", "candidate_design"),
            ("evaluate_update", "Evaluate the draft against clarity and overclaim controls", "independent_evaluation"),
            ("final_synthesis", "Synthesize limits and next decision", "final_synthesis"),
        ]
    else:
        specs = [
            ("inspect_competence", "Inspect current accepted competence and limits", "evidence_inspection"),
            ("define_cases", "Define behavioral success and sealed evaluator cases", "independent_evaluation"),
            ("gather_retained_evidence", "Gather retained/local evidence for the gap", "evidence_inspection"),
            ("construct_strategy", "Construct one bounded candidate strategy", "candidate_design"),
            ("evaluate_strategy", "Evaluate exact, negative, adversarial, and transfer cases", "independent_evaluation"),
            ("final_synthesis", "Synthesize findings and limitations", "final_synthesis"),
        ]
    if low_budget:
        specs = [specs[0], specs[1], specs[-1]]
    missing = tuple(goal.get("missing_prerequisites") or ())
    items = []
    if missing:
        items.append(("resolve_prerequisite", {
            "schema": "autonomy_3_plan_work_item_v1",
            "work_item_id": stable_id("autonomy-3-work-item", goal["goal_id"], 1, "resolve_prerequisite"),
            "title": f"Resolve or block missing prerequisite: {', '.join(missing)}",
            "objective": f"Resolve or block missing prerequisite: {', '.join(missing)}",
            "task_class": "prerequisite_analysis",
            "prerequisites": tuple(goal.get("prerequisites") or ()),
            "capability_source": "missing_capability_analysis",
            "expected_output": "prerequisite_disposition_artifact",
            "validator": {
                "validator_id": stable_id("autonomy-3-validator", goal["goal_id"], "resolve_prerequisite"),
                "evaluator_source": "operator_review_or_sealed_local_evaluator",
                "evaluator_authoring_boundary": "defined before candidate execution",
                "hidden_case_categories": ("positive", "negative", "boundary", "adversarial", "transfer"),
                "leakage_controls": ("learner cannot see expected outputs",),
                "negative_controls": True,
                "transfer_cases": True,
                "competence_creation_conditions": "future gate only after independent pass",
                "failure_disposition": "blocked_capability",
            },
            "dependencies": (),
            "authority_needed": (),
            "mutation_surface": "none",
            "estimated_cost": 1,
            "stop_condition": "validator_unavailable_or_budget_exhausted",
            "disposition_if_blocked": "blocked_capability",
        }))
    for index, (key, title, task_class) in enumerate(specs, start=len(items) + 1):
        dependencies = () if index == 1 else (stable_id("autonomy-3-work-item", goal["goal_id"], index - 1, items[-1][0] if items else ""),)
        item = {
            "schema": "autonomy_3_plan_work_item_v1",
            "work_item_id": stable_id("autonomy-3-work-item", goal["goal_id"], index, key),
            "title": title,
            "objective": title,
            "task_class": task_class,
            "prerequisites": tuple(goal.get("prerequisites") or ()),
            "capability_source": "retained_or_missing_capability_analysis" if task_class != "independent_evaluation" else "sealed_independent_evaluator",
            "expected_output": f"{key}_artifact",
            "validator": {
                "validator_id": stable_id("autonomy-3-validator", goal["goal_id"], key),
                "evaluator_source": "operator_review_or_sealed_local_evaluator",
                "evaluator_authoring_boundary": "defined before candidate execution",
                "hidden_case_categories": ("positive", "negative", "boundary", "adversarial", "transfer"),
                "leakage_controls": ("learner cannot see expected outputs",),
                "negative_controls": True,
                "transfer_cases": True,
                "competence_creation_conditions": "future gate only after independent pass",
                "failure_disposition": "revision_required_or_blocked",
            },
            "dependencies": dependencies,
            "authority_needed": (),
            "mutation_surface": "none",
            "estimated_cost": 1,
            "stop_condition": "validator_unavailable_or_budget_exhausted",
            "disposition_if_blocked": "blocked_capability" if task_class == "prerequisite_analysis" else "revision_requested",
        }
        items.append((key, item))
    return tuple(_digest_record(item) for _, item in items)


def compile_plan_proposal(
    goal: Mapping[str, Any],
    *,
    budget: Mapping[str, Any] | None = None,
    preference: Mapping[str, Any] | None = None,
    prior_plan: Mapping[str, Any] | None = None,
    requested_changes: Sequence[str] = (),
) -> dict[str, Any]:
    if goal.get("current_queue_state") not in {"queued", "planning", "waiting_for_operator"}:
        raise ValueError("goal_not_planning_eligible")
    work_items = _work_graph_for(goal, budget=budget, preference=preference)
    if not all((item.get("validator") or {}).get("evaluator_authoring_boundary") for item in work_items):
        raise ValueError("plan_validation_missing")
    authority = {
        "provider_calls": 0,
        "retrievals": 3,
        "learning_attempts": 1,
        "execution_attempts": 0,
        "tracked_source_mutation": False,
        "network": False,
        "deployment": False,
        "credentials": False,
        "trusted_admission": False,
        "capability_promotion": False,
        "scheduler_cycles": 0,
    }
    return _digest_record({
        "schema": "autonomy_3_plan_proposal_v1",
        "plan_id": stable_id("autonomy-3-plan", goal["goal_id"], goal["artifact_digest"], prior_plan.get("artifact_digest") if prior_plan else "", tuple(requested_changes), budget or {}, preference or {}),
        "goal_id": goal["goal_id"],
        "goal_digest": goal["artifact_digest"],
        "normalized_objective": goal["normalized_objective"],
        "source_evidence": tuple(goal.get("source_artifact_digests") or ()),
        "cycle_family": str(goal.get("cycle_family") or ""),
        "goal_type": str(goal.get("goal_type") or ""),
        "supported_task_class": str(goal.get("supported_task_class") or ""),
        "required_capabilities": tuple(goal.get("prerequisites") or ()),
        "accepted_capabilities_available": tuple(item for item in tuple(goal.get("prerequisites") or ()) if item not in tuple(goal.get("missing_prerequisites") or ())),
        "installed_unvalidated_study_material": (),
        "missing_capabilities": tuple(goal.get("missing_prerequisites") or ()),
        "unresolved_questions": ("operator must approve any future execution authority",),
        "proposed_work_items": work_items,
        "dependency_graph": tuple({"work_item_id": item["work_item_id"], "dependencies": item["dependencies"]} for item in work_items),
        "validation_strategy": tuple({"work_item_id": item["work_item_id"], "validator": item["validator"]} for item in work_items),
        "estimated_budgets": {"work_items": len(work_items), **dict(budget or {})},
        "authority_requirements": authority,
        "mutation_surface": "none",
        "network_requirements": False,
        "provider_requirements": 0,
        "learning_requirements": "future approval only",
        "stop_conditions": ("validator_unavailable", "budget_exhausted", "operator_declined"),
        "rollback_or_abandonment_criteria": ("no execution artifacts are created in this gate",),
        "expected_outputs": tuple(item["expected_output"] for item in work_items),
        "confidence": 0.72,
        "limitations": ("proposal only", "no execution authority"),
        "plan_status": "waiting_for_operator",
        "prior_plan_id": prior_plan.get("plan_id", "") if prior_plan else "",
        "prior_plan_digest": prior_plan.get("artifact_digest", "") if prior_plan else "",
        "requested_changes": tuple(requested_changes),
        "execution_started": False,
        "learning_started": False,
        "provider_calls": 0,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    })


def compile_plan_review_request(plan: Mapping[str, Any]) -> dict[str, Any]:
    request = {
        "schema": "autonomy_3_plan_review_request_v1",
        "request_id": stable_id("autonomy-3-plan-review", plan["plan_id"], plan["artifact_digest"]),
        "goal_id": plan["goal_id"],
        "goal_title": "Plan next queued goal",
        "title": "I created a plan for this goal",
        "what_delta_wants": f"Review a {len(tuple(plan.get('proposed_work_items') or ())) }-step plan for later execution.",
        "why": "Planning is ready for operator review; approval records future-execution readiness only.",
        "missing_information_or_capability": ", ".join(plan.get("missing_capabilities") or ()) or "No missing prerequisite named.",
        "files_or_resources": tuple(plan.get("source_evidence") or ()),
        "may_change": "Only plan review records. No mission, worker, provider, learning, or source mutation starts.",
        "provider_or_network_use": "No provider calls and no network expansion.",
        "learning_attempts": 0,
        "limits": dict(plan.get("authority_requirements") or {}),
        "recommended_action": "Approve plan for later execution",
        "if_declined": "The goal stays queued or paused without an executable plan.",
        "mission_id": plan["plan_id"],
        "work_item_id": plan["goal_id"],
        "plan_id": plan["plan_id"],
        "plan_digest": plan["artifact_digest"],
        "active_plan_version": plan["plan_id"],
        "goal_digest": plan["goal_digest"],
        "work_graph_digest": bootstrap_digest(tuple(plan.get("proposed_work_items") or ())),
        "budget_digest": bootstrap_digest(plan.get("estimated_budgets") or {}),
        "authority_limits_digest": bootstrap_digest(plan.get("authority_requirements") or {}),
        "created_at": FIXED_TIMESTAMP,
    }
    card = compile_operator_request_card(request)
    integrity_payload = {
        "request_id": request["request_id"],
        "plan_id": request["plan_id"],
        "plan_digest": request["plan_digest"],
        "active_plan_version": request["active_plan_version"],
        "goal_id": request["goal_id"],
        "goal_digest": request["goal_digest"],
        "complete_work_graph": tuple(plan.get("proposed_work_items") or ()),
        "budget": plan.get("estimated_budgets") or {},
        "authority_limits": plan.get("authority_requirements") or {},
    }
    full_request = {
        **request,
        "card_digest": card["artifact_digest"],
        "request_integrity_digest": bootstrap_digest(integrity_payload),
    }
    return _digest_record(full_request)


def normalize_plan_feedback(text: str) -> dict[str, Any]:
    normalized = " ".join(text.lower().strip().split())
    if normalized in {"approve the plan", "looks good", "approve plan"}:
        intent = "approve"
    elif normalized in {"pause this goal", "pause"}:
        intent = "pause"
    elif normalized in {"decline this plan", "decline plan", "no"}:
        intent = "decline"
    elif "reduce" in normalized or "lower budget" in normalized or "no provider calls" in normalized or "revise" in normalized:
        intent = "revise"
    elif "explain" in normalized:
        intent = "explain"
    else:
        intent = "ambiguous"
    return {"schema": "autonomy_3_plan_feedback_intent_v1", "raw_text": text, "normalized_text": normalized, "intent": intent, "requires_clarification": intent == "ambiguous"}


def approve_plan_for_future_execution(plan: Mapping[str, Any], feedback: Mapping[str, Any]) -> dict[str, Any]:
    if feedback.get("intent") != "approve":
        raise ValueError("plan_approval_requires_approve_intent")
    return _digest_record({
        "schema": "autonomy_3_plan_future_execution_approval_v1",
        "approval_id": stable_id("autonomy-3-plan-approval", plan["plan_id"], feedback),
        "plan_id": plan["plan_id"],
        "plan_digest": plan["artifact_digest"],
        "plan_status": "approved_for_future_execution",
        "operator_feedback": dict(feedback),
        "execution_started": False,
        "learning_started": False,
        "provider_calls": 0,
        "worker_started": False,
        "mission_started": False,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    })
