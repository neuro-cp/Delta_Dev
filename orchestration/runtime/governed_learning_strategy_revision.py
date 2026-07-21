"""Evidence-bound revisions for partially sufficient learning resources."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


_FORBIDDEN_KEYS = frozenset({
    "answer_key", "scoring_rule", "rubric", "threshold", "pass_threshold",
    "required_concepts", "forbidden_concepts", "evaluator_provenance",
    "evaluator_view", "evaluation_predicate", "study_resources",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _contains_forbidden(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(str(key) in _FORBIDDEN_KEYS or _contains_forbidden(item) for key, item in value.items())
    if isinstance(value, (tuple, list)):
        return any(_contains_forbidden(item) for item in value)
    return False


def compile_governed_learning_strategy_resource_revision(
    *,
    strategy: Mapping[str, Any],
    acquisition_result: Mapping[str, Any],
    available_resource_classes: Sequence[str],
    retained_source_inventory: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Create a source-neutral next-resource proposal from sufficiency evidence."""

    question_ids = tuple(str(item.get("question_id") or "") for item in (strategy.get("learning_questions") or ()) if isinstance(item, Mapping))
    sufficiency = tuple(dict(item) for item in (acquisition_result.get("question_sufficiency") or ()) if isinstance(item, Mapping))
    by_question = {str(item.get("question_id") or ""): item for item in sufficiency}
    answered = tuple(question_id for question_id in question_ids if by_question.get(question_id, {}).get("status") == "answered")
    unresolved = tuple(question_id for question_id in question_ids if by_question.get(question_id, {}).get("status") != "answered")
    result_digest = str(acquisition_result.get("result_digest") or _digest(acquisition_result))
    evidence_digest = str(strategy.get("evidence_digest") or "")
    source_inventory = tuple({
        "source_identity": str(item.get("source_identity") or ""),
        "source_locator": str(item.get("source_locator") or ""),
        "source_digest": str(item.get("source_digest") or ""),
    } for item in retained_source_inventory if isinstance(item, Mapping))
    decisions = tuple({
        "question_id": question_id,
        "disposition": "retained_unchanged" if question_id in unresolved else "answered_by_acquisition",
        "reason": (
            str(by_question.get(question_id, {}).get("missing_information") or "")
            if question_id in unresolved
            else "acquisition retained direct learner-visible support"
        ),
    } for question_id in question_ids)
    available = set(str(item) for item in available_resource_classes)
    candidates = (
        {
            "candidate_id": stable_id("learning-strategy-revision-resource", result_digest, "retained_local_evidence"),
            "resource_class": "retained_local_evidence",
            "question_ids": unresolved,
            "eligibility": "insufficient",
            "expected_information_gain": 0.0,
            "estimated_cost": 0.0,
            "authority_required": False,
            "rationale": "The acquisition record itself identifies these questions as unanswered by retained learner-visible evidence.",
        },
        {
            "candidate_id": stable_id("learning-strategy-revision-resource", result_digest, "deterministic_local_analysis"),
            "resource_class": "deterministic_local_analysis",
            "question_ids": unresolved,
            "eligibility": "insufficient_for_teaching_evidence",
            "expected_information_gain": 0.1,
            "estimated_cost": 0.05,
            "authority_required": False,
            "rationale": "Local analysis can classify the evidence gap but cannot create missing learner-visible source evidence.",
        },
        {
            "candidate_id": stable_id("learning-strategy-revision-resource", result_digest, "retained_exact_source"),
            "resource_class": "retained_exact_source",
            "question_ids": unresolved,
            "eligibility": "exhausted_for_unresolved_questions",
            "expected_information_gain": 0.0,
            "estimated_cost": 0.0,
            "authority_required": False,
            "rationale": "The completed exact-source result is retained as direct evidence that these questions remain unanswered.",
        },
        {
            "candidate_id": stable_id("learning-strategy-revision-resource", result_digest, "narrow_source_discovery"),
            "resource_class": "narrow_source_discovery",
            "question_ids": unresolved,
            "eligibility": "recommended" if unresolved else "not_needed",
            "expected_information_gain": 0.7 if unresolved else 0.0,
            "estimated_cost": 0.2 if unresolved else 0.0,
            "authority_required": bool(unresolved),
            "rationale": "No other retained source is evidenced as sufficient; discover candidates before any new source retrieval.",
            "discovery_constraints": {
                "question_ids": unresolved,
                "domain": str(strategy.get("topic") or ""),
                "acceptable_source_types": ("authoritative_course_material", "open_access_reference"),
                "maximum_result_count": 3,
                "automatic_retrieval_prohibited": True,
                "provider_use_prohibited": True,
            },
        },
        {
            "candidate_id": stable_id("learning-strategy-revision-resource", result_digest, "operator_supplied_teaching_resource"),
            "resource_class": "operator_supplied_teaching_resource",
            "question_ids": unresolved,
            "eligibility": "fallback_only" if unresolved else "not_needed",
            "expected_information_gain": 0.55 if unresolved else 0.0,
            "estimated_cost": 0.1 if unresolved else 0.0,
            "authority_required": True,
            "rationale": "An operator may provide bounded teaching evidence if narrow discovery is not authorized or is insufficient.",
        },
    )
    ranked = tuple(sorted(candidates, key=lambda item: (-float(item["expected_information_gain"]), float(item["estimated_cost"]), str(item["candidate_id"]))))
    selected = next((item for item in ranked if item["eligibility"] == "recommended"), None)
    revision_id = stable_id("governed-learning-strategy-revision", strategy.get("strategy_id"), result_digest)
    authority_request = {}
    if selected:
        constraints = dict(selected["discovery_constraints"])
        authority_request = {
            "request_id": stable_id("learning-strategy-resource-revision-authority", revision_id, selected["candidate_id"]),
            "request_kind": "governed_learning_strategy_resource_revision_authority",
            "status": "pending",
            "strategy_id": strategy.get("strategy_id"),
            "revision_id": revision_id,
            "evidence_digest": evidence_digest,
            "acquisition_result_digest": result_digest,
            "action_type": "narrow_source_discovery",
            "scope": "discover at most three source candidates for the unresolved strategy questions; do not retrieve any discovered source",
            "authority_scope": "discover at most three source candidates for the unresolved strategy questions; do not retrieve any discovered source",
            "question_ids": unresolved,
            "discovery_constraints": constraints,
            "permitted_responses": (
                "approve_learning_strategy_resource_revision_authority",
                "reject_learning_strategy_resource_revision_authority",
                "defer_learning_strategy_resource_revision_authority",
                "ask_for_clarification",
            ),
            "authority_granted": False,
            "prohibited_actions": (
                "source_retrieval", "broad_research", "provider_call", "learner_retry", "evaluator_run",
                "capability_update", "pcm_action", "git_action", "deployment",
            ),
            "created_at": utc_now(),
        }
    revision = {
        "revision_id": revision_id,
        "revision_version": 1,
        "strategy_id": strategy.get("strategy_id"),
        "strategy_evidence_digest": evidence_digest,
        "acquisition_result_id": acquisition_result.get("acquisition_result_id"),
        "acquisition_result_digest": result_digest,
        "answered_question_ids": answered,
        "unresolved_question_ids": unresolved,
        "question_decisions": decisions,
        "retained_source_inventory": source_inventory,
        "available_resource_classes": tuple(sorted(available)),
        "ranked_resource_candidates": ranked,
        "selected_candidate_id": selected.get("candidate_id") if selected else "",
        "authority_request": authority_request,
        "stopping_conditions": (
            "no source is teaching evidence until retrieved and provenance-validated",
            "do not retry the learner before each unresolved question has sufficient learner-visible support",
            "stop if no bounded authority candidate remains",
        ),
        "verification_conditions": (
            "every retained claim maps to one learner-authored question",
            "every unresolved question retains its insufficiency reason",
            "learner retry and capability promotion remain prohibited",
        ),
        "learner_attempt_unjustified": bool(unresolved),
        "capability_update_prohibited": True,
        "created_at": utc_now(),
    }
    revision["revision_digest"] = _digest(revision)
    return revision


def validate_governed_learning_strategy_resource_revision(
    revision: Mapping[str, Any],
    *,
    strategy: Mapping[str, Any],
    acquisition_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed on ungrounded resources, leakage, or altered question state."""

    errors: list[str] = []
    if _contains_forbidden(revision):
        errors.append("evaluator_only_material_present")
    if str(revision.get("strategy_id") or "") != str(strategy.get("strategy_id") or ""):
        errors.append("strategy_binding_mismatch")
    expected_digest = str(acquisition_result.get("result_digest") or _digest(acquisition_result))
    if str(revision.get("acquisition_result_digest") or "") != expected_digest:
        errors.append("acquisition_result_digest_mismatch")
    expected_questions = tuple(str(item.get("question_id") or "") for item in (strategy.get("learning_questions") or ()) if isinstance(item, Mapping))
    preserved = tuple(revision.get("answered_question_ids") or ()) + tuple(revision.get("unresolved_question_ids") or ())
    if set(preserved) != set(expected_questions) or len(preserved) != len(expected_questions):
        errors.append("question_state_not_preserved")
    sufficiency = {str(item.get("question_id") or ""): str(item.get("status") or "") for item in (acquisition_result.get("question_sufficiency") or ()) if isinstance(item, Mapping)}
    if any(sufficiency.get(question_id) != "answered" for question_id in revision.get("answered_question_ids") or ()):
        errors.append("unanswered_question_marked_answered")
    if any(sufficiency.get(question_id) == "answered" for question_id in revision.get("unresolved_question_ids") or ()):
        errors.append("answered_question_marked_unresolved")
    request = dict(revision.get("authority_request") or {})
    if request:
        if request.get("action_type") != "narrow_source_discovery" or request.get("source_locator"):
            errors.append("fabricated_or_non_narrow_source_authority")
        if request.get("authority_granted"):
            errors.append("authority_self_granted")
        if request.get("discovery_constraints", {}).get("automatic_retrieval_prohibited") is not True:
            errors.append("automatic_retrieval_not_prohibited")
    if not revision.get("learner_attempt_unjustified"):
        errors.append("learner_retry_not_prohibited")
    if not revision.get("capability_update_prohibited"):
        errors.append("capability_update_not_prohibited")
    return {"accepted": not errors, "errors": tuple(errors)}
