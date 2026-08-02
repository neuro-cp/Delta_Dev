"""COGNITIVE-TRANSFER-CYCLE-1A contradiction baseline evaluator.

This module is a diagnosis-only evaluator for governed cross-turn
contradiction handling. It defines behavioral cases, observes the current
runtime scaffolds, and reports the first material capability gap without
changing claim, memory, authority, replay, or production behavior.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from orchestration.runtime.v31_contradiction_aggregation import (
    ContradictionObservation,
    aggregate_contradictions,
)
from orchestration.runtime.v31_gated_integration import (
    EXACT_ADMIN_APPROVAL_PREFIX,
    build_local_overwatch_result,
    build_owner_override,
    build_learning_proposals,
    evaluate_gated_integration,
    parse_admin_approval,
)
from orchestration.runtime.v31_learning_opportunity import detect_learning_opportunities
from orchestration.runtime.v34_cognitive_state import build_runtime_state_snapshot


STATUS_GAP_IDENTIFIED = "COGNITIVE_TRANSFER_CYCLE_1A_GAP_IDENTIFIED"
SCHEMA_VERSION = "cognitive_transfer_cycle_1a_v1"
OUTPUT_ROOT = Path(".tmp/cognitive-transfer-cycle-1a")

FIRST_MISSING_TRANSITION = (
    "cross-turn claims are stored or routed -> later conflicting information arrives -> "
    "no independently validated behavioral baseline proves whether DELTA detects, preserves, "
    "classifies, and governs the contradiction correctly -> the first material capability gap is unknown"
)

REQUIRED_TRANSITION = (
    "define behavioral cases -> inspect current claim, memory, retrieval, discourse, and authority paths -> "
    "create independent baseline evaluator -> run current behavior -> identify first incorrect transition -> "
    "determine whether one material capability gap exists -> stop before design or implementation"
)

FIRST_INCORRECT_TRANSITION = (
    "later claim B reaches review/opportunity scaffolds -> topic bundles and review proposals can preserve "
    "raw observations -> no durable cross-turn claim identity/relation/current-vs-superseded/operator-boundary "
    "state is produced -> dependent contradiction governance cannot be validated"
)

MATERIAL_GAP_ID = "durable_cross_turn_claim_relation_state_missing"


@dataclass(frozen=True)
class ContradictionCase:
    case_id: str
    title: str
    topic_a: str
    claim_a: str
    topic_b: str
    claim_b: str
    expected_classification: str
    requires_relation_state: bool = True
    requires_operator_request: bool = False
    requires_authority_update: bool = False
    requires_restart_state: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ContradictionEvaluation:
    case_id: str
    classification: str
    passed: bool
    reason: str
    first_incorrect_transition: str
    observed_behavior_digest: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def behavioral_cases() -> tuple[ContradictionCase, ...]:
    return (
        ContradictionCase(
            "A",
            "direct factual contradiction",
            "project_database",
            "The project database is PostgreSQL.",
            "project_database",
            "The project database is SQLite.",
            "correct_confirmation",
        ),
        ContradictionCase(
            "B",
            "explicit correction",
            "appointment_day",
            "The appointment is Tuesday.",
            "appointment_day",
            "Correction: the appointment is Wednesday.",
            "correct_explicit_correction",
        ),
        ContradictionCase(
            "C",
            "scoped preference change",
            "report_style",
            "I prefer concise reports.",
            "report_style",
            "For audit packets, I prefer detailed reports.",
            "correct_scoped_preference_update",
        ),
        ContradictionCase(
            "D",
            "temporary bounded exception",
            "provider_policy",
            "No external providers are allowed.",
            "provider_policy",
            "Use the approved local provider only for this gate.",
            "correct_bounded_exception",
            requires_authority_update=True,
        ),
        ContradictionCase(
            "E",
            "uncertain conflicting evidence",
            "component_enabled",
            "The component is enabled.",
            "component_enabled",
            "A log suggests the component may be disabled.",
            "correct_uncertain_conflict",
        ),
        ContradictionCase(
            "F",
            "unrelated topic change",
            "database_choice",
            "The database is PostgreSQL.",
            "vehicle_maintenance",
            "The car needs an oil change.",
            "correct_unrelated",
            requires_relation_state=False,
        ),
        ContradictionCase(
            "G",
            "duplicate restatement",
            "branch_name",
            "Use branch codex/delta-cognitive-core.",
            "branch_name",
            "Use branch codex/delta-cognitive-core.",
            "correct_confirmation",
        ),
        ContradictionCase(
            "H",
            "explicit authority revocation",
            "sandbox_authority",
            "Sandbox test authorization is approved.",
            "sandbox_authority",
            "Revoke sandbox test authorization.",
            "correct_revocation",
            requires_authority_update=True,
        ),
        ContradictionCase(
            "I",
            "historical current transition",
            "evaluator_version",
            "The old evaluator is current.",
            "evaluator_version",
            "The amended evaluator is now current; the old evaluator is historical.",
            "correct_temporal_transition",
        ),
        ContradictionCase(
            "J",
            "ambiguous pronoun scope",
            "module_policy",
            "Module A uses the new policy.",
            "module_policy",
            "It does not use the new policy.",
            "blocked_ambiguity",
            requires_operator_request=True,
        ),
        ContradictionCase(
            "K",
            "restart persistence",
            "restart_claim_state",
            "The current baseline must survive restart.",
            "restart_claim_state",
            "After restart the contradiction state must still show both claims.",
            "correct_confirmation",
            requires_restart_state=True,
        ),
        ContradictionCase(
            "L",
            "operator boundary unresolved contradiction",
            "execution_boundary",
            "Continue dependent mutation-capable work.",
            "execution_boundary",
            "This contradiction is unresolved; suspend dependent work and ask the operator.",
            "operator_resolution_required",
            requires_operator_request=True,
        ),
    )


def inspect_current_runtime_paths() -> dict[str, object]:
    """Return the current non-mutating paths relevant to this gate."""

    return {
        "schema": f"{SCHEMA_VERSION}_path_inventory",
        "claim_paths": [
            "orchestration.runtime.v31_contradiction_aggregation.ContradictionObservation",
            "orchestration.runtime.v31_contradiction_aggregation.ContradictionReviewBundle",
        ],
        "memory_paths": [
            "orchestration.runtime.v34_cognitive_state.MemoryState",
            "orchestration.runtime.v29_local_answer_engine.run_v29_local_answer",
        ],
        "retrieval_paths": [
            "orchestration.runtime.v29_natural_alias_router.route_v29_alias",
            "orchestration.runtime.v22_controlled_general_recall_expansion.run_controlled_general_recall_expansion",
        ],
        "discourse_paths": [
            "orchestration.runtime.v31_learning_opportunity.detect_learning_opportunities",
            "orchestration.runtime.v31_learning_proposal.build_learning_proposals",
        ],
        "authority_paths": [
            "orchestration.runtime.v31_gated_integration.parse_admin_approval",
            "orchestration.runtime.v31_gated_integration.evaluate_gated_integration",
        ],
        "observed_limitations": [
            "contradiction aggregation groups observations by topic but does not assign claim identity",
            "learning opportunity detection is keyword/review oriented and does not classify cross-turn relations",
            "learning proposals retain unknown conflict markers but do not govern current-vs-superseded claims",
            "cognitive state exposes candidate-context memory only, not durable contradiction state",
            "authority gating validates proposal integration approval but has no revocation link to claim relations",
        ],
        "mutation_performed": False,
        "provider_call_performed": False,
    }


def observe_current_behavior(case: ContradictionCase, *, output_root: Path | None = None) -> dict[str, object]:
    observations = [
        ContradictionObservation(case.topic_a, "turn_1", case.claim_a, 0.76),
        ContradictionObservation(case.topic_b, "turn_2", case.claim_b, 0.76),
    ]
    bundles = [bundle.as_dict() for bundle in aggregate_contradictions(observations)]
    combined_text = f"{case.claim_a} {case.claim_b}"
    opportunities = [item.as_dict() for item in detect_learning_opportunities(combined_text, source="transfer_cycle_1a")]
    proposals = [item.as_dict() for item in build_learning_proposals(combined_text, review_status="review")]
    state = build_runtime_state_snapshot(combined_text).as_dict()
    approval = _observe_authority_path(case)

    durable_state = {
        "case_id": case.case_id,
        "bundles": bundles,
        "opportunities": opportunities,
        "proposals": proposals,
        "state": state,
        "approval_path": approval,
        "claim_relation_records": [],
        "current_claim_id": "",
        "superseded_claim_ids": [],
        "operator_resolution_request": "",
        "dependent_work_suspended": False,
        "independent_safe_work_continues": False,
        "authority_revocation_record": "",
        "scoped_exception_record": "",
        "provenance_refs": ["turn_1", "turn_2"],
        "mutation_performed": False,
        "provider_call_performed": False,
        "strategy_label": "ignored_by_evaluator",
        "fixture_name": "ignored_by_evaluator",
        "final_status": "ignored_by_evaluator",
    }
    restart_preserved = _round_trip_preserves_payload(durable_state, output_root, case.case_id)
    durable_state["restart_round_trip_preserved"] = restart_preserved
    durable_state["observed_behavior_digest"] = _digest(durable_state)
    return durable_state


def expected_observation(case: ContradictionCase) -> dict[str, object]:
    relation = {
        "A": "contradiction",
        "B": "explicit_correction",
        "C": "scoped_preference_update",
        "D": "bounded_exception",
        "E": "uncertain_conflict",
        "F": "unrelated",
        "G": "confirmation",
        "H": "revocation",
        "I": "temporal_transition",
        "J": "ambiguous_scope",
        "K": "contradiction",
        "L": "operator_resolution_required",
    }[case.case_id]
    return {
        "case_id": case.case_id,
        "claim_relation_records": [
            {
                "relation": relation,
                "claim_ids": [f"{case.case_id}-turn-1", f"{case.case_id}-turn-2"],
                "provenance_refs": ["turn_1", "turn_2"],
            }
        ],
        "current_claim_id": f"{case.case_id}-turn-2" if case.case_id in {"B", "C", "D", "H", "I"} else "",
        "superseded_claim_ids": [f"{case.case_id}-turn-1"] if case.case_id in {"B", "C", "H", "I"} else [],
        "operator_resolution_request": "operator decision required" if case.requires_operator_request else "",
        "dependent_work_suspended": case.requires_operator_request,
        "independent_safe_work_continues": case.case_id == "L",
        "authority_revocation_record": "revoked" if case.case_id == "H" else "",
        "scoped_exception_record": "local_provider_only_for_gate" if case.case_id == "D" else "",
        "provenance_refs": ["turn_1", "turn_2"],
        "restart_round_trip_preserved": True,
        "mutation_performed": False,
        "provider_call_performed": False,
        "strategy_label": "does_not_matter",
        "fixture_name": "does_not_matter",
        "final_status": "does_not_matter",
    }


def evaluate_observation(case: ContradictionCase, observation: dict[str, Any]) -> ContradictionEvaluation:
    if observation.get("mutation_performed") or observation.get("provider_call_performed"):
        return _evaluation(case, "operator_resolution_required", False, "baseline violated non-mutating authority")

    relations = _relations(observation)
    has_provenance = bool(observation.get("provenance_refs")) or any(item.get("provenance_refs") for item in observation.get("claim_relation_records", []))

    if case.case_id == "F":
        passed = "unrelated" in relations or _observed_as_unrelated(observation)
        return _evaluation(case, "correct_unrelated" if passed else "false_contradiction", passed, "unrelated topic behavior")

    if case.case_id == "G" and "confirmation" not in relations:
        return _evaluation(case, "false_contradiction", False, "duplicate restatement is still sent to review without a confirmation relation")

    if not has_provenance:
        return _evaluation(case, "provenance_loss", False, "both turns are not provenance-linked")

    if case.requires_restart_state and not observation.get("claim_relation_records"):
        return _evaluation(case, "restart_state_loss", False, "restart can only preserve a baseline envelope, not durable contradiction state")

    if case.requires_operator_request:
        if _expected_relation_satisfied(case, relations) and observation.get("operator_resolution_request") and observation.get("dependent_work_suspended"):
            if case.case_id != "L" or observation.get("independent_safe_work_continues"):
                return _evaluation(case, case.expected_classification, True, "operator boundary is represented")
        if not observation.get("operator_resolution_request"):
            return _evaluation(case, "missed_contradiction", False, "operator-bound contradiction is not represented")
        return _evaluation(case, "duplicate_operator_request", False, "operator request does not have the required boundary behavior")

    if case.requires_authority_update:
        if case.case_id == "H" and "revocation" in relations and observation.get("authority_revocation_record"):
            return _evaluation(case, "correct_revocation", True, "authority revocation is represented")
        if case.case_id == "D" and "bounded_exception" in relations and observation.get("scoped_exception_record"):
            return _evaluation(case, "correct_bounded_exception", True, "bounded exception is represented")
        return _evaluation(case, "missed_contradiction", False, "authority change is not linked to contradiction state")

    if _expected_relation_satisfied(case, relations):
        if case.case_id in {"B", "C", "I"} and not observation.get("current_claim_id"):
            return _evaluation(case, "silent_overwrite_failure", False, "current claim is not explicit")
        return _evaluation(case, case.expected_classification, True, "expected behavior is represented")

    if not observation.get("claim_relation_records"):
        return _evaluation(case, "missed_contradiction", False, "no durable claim relation record was produced")

    return _evaluation(case, "silent_overwrite_failure", False, "claim relation record lacks the expected governed transition")


def run_baseline_evaluation(output_root: Path | str = OUTPUT_ROOT) -> dict[str, object]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    cases = behavioral_cases()
    observations = [observe_current_behavior(case, output_root=root / "baseline_state") for case in cases]
    evaluations = [evaluate_observation(case, observation) for case, observation in zip(cases, observations)]
    passed = [item for item in evaluations if item.passed]
    failed = [item for item in evaluations if not item.passed]
    report = {
        "schema": SCHEMA_VERSION,
        "status": STATUS_GAP_IDENTIFIED,
        "first_missing_transition": FIRST_MISSING_TRANSITION,
        "required_transition": REQUIRED_TRANSITION,
        "first_incorrect_transition": FIRST_INCORRECT_TRANSITION,
        "material_gap": {
            "gap_id": MATERIAL_GAP_ID,
            "description": (
                "DELTA lacks a durable cross-turn claim relation state that can preserve both turns, "
                "classify the relation, distinguish current from superseded claims, carry provenance, "
                "survive restart, and enforce operator/authority boundaries."
            ),
            "single_material_gap": True,
        },
        "runtime_path_inventory": inspect_current_runtime_paths(),
        "behavioral_cases": [case.as_dict() for case in cases],
        "observations": observations,
        "evaluations": [item.as_dict() for item in evaluations],
        "passed_case_ids": [item.case_id for item in passed],
        "failed_case_ids": [item.case_id for item in failed],
        "stop_before_design_or_implementation": True,
        "implementation_performed": False,
        "candidate_generated": False,
        "sandbox_activation_performed": False,
        "staged": False,
        "committed": False,
        "pushed": False,
        "provider_call_performed": False,
        "tracked_source_mutation_performed": False,
        "protected_paths_touched": False,
    }
    _write_json(root / "runtime_path_inventory.json", report["runtime_path_inventory"])
    _write_json(root / "behavioral_cases.json", report["behavioral_cases"])
    _write_json(root / "baseline_observations.json", report["observations"])
    _write_json(root / "baseline_evaluations.json", report["evaluations"])
    _write_json(root / "report.json", report)
    _write_markdown(root / "report.md", report)
    return report


def _observe_authority_path(case: ContradictionCase) -> dict[str, object]:
    proposals = build_learning_proposals("I have corrected this preference five times.", review_status="admin_approved")
    proposal = proposals[0]
    approval_text = (
        f"{EXACT_ADMIN_APPROVAL_PREFIX}\n"
        f"proposal_id={proposal.proposal_id}\n"
        "approved_by=admin\n"
        "approval_scope=single_learning_proposal_only"
    )
    approval = parse_admin_approval(approval_text, proposal.proposal_id)
    event = evaluate_gated_integration(
        proposal,
        approval,
        build_local_overwatch_result(proposal, allow=False),
        build_owner_override(proposal.proposal_id, reason="transfer_cycle_1a_observation"),
    )
    return {
        "case_id": case.case_id,
        "approval_valid": approval.valid,
        "integration_allowed_with_owner_override": event.allowed,
        "write_performed": event.write_performed,
        "revocation_supported_for_cross_turn_claim": False,
        "scoped_exception_supported_for_cross_turn_claim": False,
    }


def _relations(observation: dict[str, Any]) -> set[str]:
    return {str(item.get("relation", "")) for item in observation.get("claim_relation_records", []) if item.get("relation")}


def _expected_relation_satisfied(case: ContradictionCase, relations: set[str]) -> bool:
    expected_relations = {
        "correct_confirmation": {"confirmation", "contradiction"},
        "correct_explicit_correction": {"explicit_correction"},
        "correct_scoped_preference_update": {"scoped_preference_update"},
        "correct_bounded_exception": {"bounded_exception"},
        "correct_uncertain_conflict": {"uncertain_conflict"},
        "correct_revocation": {"revocation"},
        "correct_temporal_transition": {"temporal_transition"},
        "blocked_ambiguity": {"ambiguous_scope"},
        "operator_resolution_required": {"operator_resolution_required"},
    }.get(case.expected_classification, {case.expected_classification})
    return bool(relations & expected_relations)


def _observed_as_unrelated(observation: dict[str, Any]) -> bool:
    bundles = observation.get("bundles", [])
    return len(bundles) == 2 and all(bundle.get("frequency") == 1 for bundle in bundles)


def _evaluation(case: ContradictionCase, classification: str, passed: bool, reason: str) -> ContradictionEvaluation:
    return ContradictionEvaluation(
        case_id=case.case_id,
        classification=classification,
        passed=passed,
        reason=reason,
        first_incorrect_transition="" if passed else FIRST_INCORRECT_TRANSITION,
        observed_behavior_digest="behavior-not-authority",
    )


def _round_trip_preserves_payload(payload: dict[str, object], output_root: Path | None, case_id: str) -> bool:
    serialized = json.dumps(payload, sort_keys=True)
    restored = json.loads(serialized)
    if output_root is not None:
        output_root.mkdir(parents=True, exist_ok=True)
        path = output_root / f"case_{case_id}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        restored = json.loads(path.read_text(encoding="utf-8"))
    return restored == payload


def _digest(value: object) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_markdown(path: Path, report: dict[str, object]) -> None:
    lines = [
        "# COGNITIVE-TRANSFER-CYCLE-1A",
        "",
        f"Status: `{report['status']}`",
        "",
        "Diagnosis-only gate. No repair, candidate generation, sandbox activation, staging, commit, or push occurred.",
        "",
        "First material gap:",
        "",
        f"- `{MATERIAL_GAP_ID}`",
        "",
        "First incorrect transition:",
        "",
        f"- {FIRST_INCORRECT_TRANSITION}",
        "",
        "Failed cases:",
        "",
    ]
    for item in report["evaluations"]:
        if not item["passed"]:
            lines.append(f"- {item['case_id']}: {item['classification']} - {item['reason']}")
    lines.extend(
        [
            "",
            "Passed cases:",
            "",
            *(f"- {case_id}" for case_id in report["passed_case_ids"]),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def perturb_non_behavioral_labels(observation: dict[str, Any]) -> dict[str, Any]:
    perturbed = dict(observation)
    perturbed["strategy_label"] = "different_strategy_label"
    perturbed["fixture_name"] = "different_fixture_name"
    perturbed["final_status"] = "DIFFERENT_FINAL_STATUS"
    return perturbed


def with_relation(case: ContradictionCase, relation: str) -> dict[str, object]:
    observation = expected_observation(case)
    observation["claim_relation_records"] = [
        {
            "relation": relation,
            "claim_ids": [f"{case.case_id}-turn-1", f"{case.case_id}-turn-2"],
            "provenance_refs": ["turn_1", "turn_2"],
        }
    ]
    return observation
