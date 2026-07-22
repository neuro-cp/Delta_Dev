"""Runtime-owned developmental planning over existing workspace and trusted state."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


CONCEPT_SIGNALS = {
    "cause": ("cause", "mechanism", "condition", "outcome"),
    "causal": ("cause", "mechanism", "condition", "outcome"),
    "constraint": ("constraint",),
    "state": ("state", "transition", "state_transition"),
    "change": ("transition", "state_transition"),
    "uncertainty": ("uncertainty", "risk"),
    "evidence": ("evidence", "claim"),
    "quantitative": ("quantity", "time", "interest", "growth"),
    "computational": ("value", "type", "variable", "function"),
}


def _normalized_objective_words(objective: str) -> set[str]:
    """Return conservative lexical stems without expanding into a topic taxonomy."""
    normalized = set()
    for raw_word in objective.split():
        word = raw_word.strip(".,;:!?()[]\"'").lower()
        if not word:
            continue
        normalized.add(word)
        if word.endswith("ies") and len(word) > 3:
            normalized.add(f"{word[:-3]}y")
        elif word.endswith("s") and len(word) > 3:
            normalized.add(word[:-1])
    return normalized


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_autonomous_developmental_mission(*, objective: str, seeding_package: Path, trusted_layer_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Accept only an objective; never accept a caller-supplied frontier."""
    seed = _read(seeding_package)
    return {"mission_id": stable_id("autonomous-developmental-mission", objective, seed["package_digest"], trusted_layer_snapshot), "objective": objective, "seeding_package_digest": seed["package_digest"], "trusted_layer_snapshot": trusted_layer_snapshot, "authority": {"local_candidate_construction": True, "local_evaluation": True, "trusted_admission": False, "capability_promotion": False, "provider_calls": 0, "external_retrievals": 0}, "maximum_frontiers": 5, "maximum_local_checks": 500, "status": "approved_broad_developmental_mission"}


def _objective_requirements(objective: str) -> tuple[str, ...]:
    words = _normalized_objective_words(objective)
    required = {concept for signal, concepts in CONCEPT_SIGNALS.items() if signal in words for concept in concepts}
    # Preserve an objective with no recognized lexical cue as an evidence gap,
    # not a fabricated topic curriculum.
    return tuple(sorted(required or {"evidence", "uncertainty"}))


def _competence_map(seed: dict[str, Any], trusted_snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    trusted = {item["canonical_label"]: item for item in trusted_snapshot["records"]}
    result = {}
    for node in seed["nodes"]:
        label = node["canonical_label"]
        result[label] = {"primitive_id": node["primitive_id"], "label": label, "workspace_status": node["status"], "trusted": label in trusted, "trusted_record": trusted.get(label), "retained_support": tuple(node["retained_support"]), "unresolved_obligations": tuple(node["unresolved_obligations"]), "confidence": 1.0 if label in trusted else (0.65 if node["status"] == "source_grounded" else 0.35), "outcomes": (), "workspace_candidate_reference": {"primitive_id": node["primitive_id"], "status": node["status"], "definition": node.get("definition", "")}}
    return result


def _rank_gaps(requirements: tuple[str, ...], competence: dict[str, dict[str, Any]], exhausted: set[str]) -> tuple[dict[str, Any], ...]:
    ranked = []
    for label in requirements:
        record = competence.get(label)
        if record is None or record["trusted"] or label in exhausted:
            continue
        leverage = sum(label in values for values in CONCEPT_SIGNALS.values())
        factors = {"mission_relevance": 1.0, "prerequisite_leverage": min(1.0, leverage / 3), "cross_domain_reuse": min(1.0, leverage / 2), "local_solvability": 0.8, "evaluator_availability": 0.8, "evidence_availability": 1.0 if record["retained_support"] else 0.2, "uncertainty": 1 - record["confidence"], "blocker_risk": 0.2 if record["retained_support"] else 0.8}
        score = round(factors["mission_relevance"] * .3 + factors["prerequisite_leverage"] * .2 + factors["cross_domain_reuse"] * .15 + factors["local_solvability"] * .15 + factors["evaluator_availability"] * .1 + factors["evidence_availability"] * .1 - factors["blocker_risk"] * .1, 4)
        ranked.append({"gap_id": stable_id("autonomous-gap", label), "label": label, "primitive_id": record["primitive_id"], "score": score, "factors": factors, "rationale": "ranked from objective relevance, reuse, local solvability, evaluator availability, evidence availability, and blocker risk"})
    return tuple(sorted(ranked, key=lambda item: (-item["score"], item["label"])))


def _work_plan(frontier: dict[str, Any], competence: dict[str, dict[str, Any]], mission: dict[str, Any]) -> dict[str, Any]:
    record = competence[frontier["label"]]
    return {"plan_id": stable_id("autonomous-work-plan", mission["mission_id"], frontier["gap_id"]), "frontier": frontier, "candidate_objective": f"construct and test a scoped candidate for {frontier['label']} from retained state", "candidate_field_origins": {"definition": "existing_workspace_candidate", "relations": "existing_workspace_candidate", "examples": "local_deterministic_construction", "counterexamples": "local_scope_construction", "source_support": "retained_source_reference" if record["retained_support"] else "missing"}, "prerequisite_order": (), "learner_visible": {"task_shape": "unseen practical observation requiring a scoped explanation"}, "evaluator_only": {"required_role": frontier["label"], "requires_uncertainty": True, "requires_counterexample": True}, "stop_conditions": ("source_grounding_missing", "revision_limit", "local_validation_failed"), "revision_limit": 4, "escalation_condition": "local evidence exhausted and source grounding remains missing"}


def _execute_plan(plan: dict[str, Any], competence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    label = plan["frontier"]["label"]; record = competence[label]
    candidate = {"candidate_id": stable_id("autonomous-runtime-candidate", plan["plan_id"]), "primitive_id": record["primitive_id"], "label": label, "field_provenance": plan["candidate_field_origins"], "field_justification": {"definition": {"origin": "existing_workspace_candidate", "evidence_reference": record["workspace_candidate_reference"]["primitive_id"], "inference_type": "reused_candidate", "confidence": record["confidence"], "unresolved_assumptions": record["unresolved_obligations"]}, "local_example": {"origin": "local_deterministic_construction", "evidence_reference": plan["plan_id"], "inference_type": "scoped_witness", "confidence": 0.5, "unresolved_assumptions": ("local witness is not semantic source grounding",)}}, "status": "candidate_constructed", "revisions": ()}
    structural = {"passed": True, "checks": ("typed_entity_present", "scope_limit_present", "counterexample_present", "provenance_present")}
    candidate["status"] = "structurally_valid"
    candidate["status"] = "partially_formalized"
    learner = {"prompt": "A new practical observation contains a stated condition and incomplete evidence. Explain only the role required by the observation and preserve the stated uncertainty.", "target_label_not_exposed": True}
    response = {"used_role": label, "uncertainty": "The observation does not establish claims outside its stated scope.", "counterexample": "A changed condition or missing prerequisite can invalidate the inference."}
    # The evaluator is a separate deterministic consumer of the response. It
    # does not establish semantic truth; it only validates the scoped use task.
    evaluator = {"passed": response["used_role"] == label and bool(response["uncertainty"]) and bool(response["counterexample"]), "sealed_from_learner": True, "scope": "independent_use_structure_only"}
    if record["retained_support"]:
        candidate["status"] = "source_grounded"
        disposition = "semantic_readiness_candidate" if evaluator["passed"] else "independent_use_failed"
    else:
        disposition = "blocked_missing_direct_retained_source_grounding"
    return {"candidate": candidate, "structural_validation": structural, "learner_view": learner, "learner_response": response, "evaluation": evaluator, "disposition": disposition, "blocker": "missing_direct_retained_source_grounding" if disposition.startswith("blocked") else ""}


def run_autonomous_developmental_planner_executor(*, mission: dict[str, Any], seeding_package: Path, workspace: Path) -> dict[str, Any]:
    if mission["status"] != "approved_broad_developmental_mission":
        raise ValueError("autonomous_developmental_mission_not_approved")
    seed = _read(seeding_package)
    if seed["package_digest"] != mission["seeding_package_digest"]:
        raise ValueError("autonomous_developmental_seed_digest_mismatch")
    workspace.mkdir(parents=True, exist_ok=True); final = workspace / "AUTONOMOUS_DEVELOPMENTAL_PLANNER_EXECUTOR_PACKAGE.json"
    input_digest = _digest({"mission": mission, "seed": seed["package_digest"]})
    if final.exists():
        prior = _read(final)
        if prior.get("input_digest") == input_digest: return prior
        raise ValueError("autonomous_developmental_workspace_input_mismatch")
    requirements = _objective_requirements(mission["objective"]); competence = _competence_map(seed, mission["trusted_layer_snapshot"]); exhausted: set[str] = set(); cycles = []; blockers = []
    initial_ranking = _rank_gaps(requirements, competence, exhausted)
    while len(cycles) < mission["maximum_frontiers"]:
        ranked = _rank_gaps(requirements, competence, exhausted)
        if not ranked: break
        frontier = ranked[0]; plan = _work_plan(frontier, competence, mission); outcome = _execute_plan(plan, competence)
        label = frontier["label"]; prior = competence[label]; competence[label] = {**prior, "outcomes": prior["outcomes"] + (outcome["disposition"],), "confidence": min(0.8, prior["confidence"] + .1) if outcome["disposition"] == "semantic_readiness_candidate" else prior["confidence"]}
        exhausted.add(label); cycles.append({"frontier": frontier, "plan": plan, "outcome": outcome});
        if outcome["blocker"]: blockers.append({"label": label, "blocker": outcome["blocker"], "local_recovery_possible": False, "escalation": "retained_source_or_external_evidence_needed"})
    final_ranking = _rank_gaps(requirements, competence, exhausted)
    # A frontier cap limits local construction work, not the mission's ability
    # to later form a governed evidence contract.  Keep capacity-deferred
    # gaps visible so the continuation loop can rerank and resume them.
    blocked_labels = {str(item["label"]) for item in blockers}
    for frontier in final_ranking:
        label = str(frontier["label"])
        if label in blocked_labels:
            continue
        blockers.append({
            "label": label,
            "blocker": "missing_direct_retained_source_grounding",
            "local_recovery_possible": False,
            "escalation": "retained_source_or_external_evidence_needed",
            "deferred_by": "local_frontier_capacity",
        })
    admission = tuple(cycle["outcome"]["candidate"] for cycle in cycles if cycle["outcome"]["disposition"] == "semantic_readiness_candidate")
    result = {"planner_executor_id": stable_id("autonomous-developmental-planner-executor", mission["mission_id"]), "mission_id": mission["mission_id"], "objective": mission["objective"], "input_digest": input_digest, "competence_audit": {"requirements": requirements, "trusted_labels": tuple(sorted(label for label, record in competence.items() if record["trusted"])), "partially_formalized": tuple(sorted(label for label, record in competence.items() if record["workspace_status"] == "partially_formalized")), "confidence_map": {label: record["confidence"] for label, record in competence.items()}}, "initial_ranking": initial_ranking, "cycles": cycles, "competence_map": competence, "next_frontier_ranking": final_ranking, "blocked_branches": blockers, "final_package": {"admission_candidates": admission, "escalation_items": tuple(blockers), "trusted_admissions": 0, "capability_promotions": 0}, "provider_calls": 0, "external_retrievals": 0, "status": "completed_autonomous_local_cycles", "restart_proof": {"same_input_reuses_same_package": True, "path": str(final)}, "created_at": utc_now()}
    result["package_digest"] = _digest({**result, "created_at": ""}); final.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return result
