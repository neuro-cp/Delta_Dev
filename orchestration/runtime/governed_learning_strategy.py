"""Evidence-bound learning-strategy compilation.

This module owns immutable strategy records and validation only.  It never
retrieves a source, calls a model, scores an evaluator, or updates capability
state.  The continuous controller owns persistence and operator boundaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


_FORBIDDEN_KEYS = frozenset({
    "answer_key", "scoring_rule", "rubric", "threshold", "pass_threshold",
    "required_concepts", "forbidden_concepts", "evaluator_provenance",
    "evaluator_view", "evaluation_predicate", "study_resources",
})
LEARNING_STRATEGY_VERSION = 4
_STOP_TERMS = frozenset({
    "about", "also", "and", "answer", "are", "brief", "case", "claim", "complex",
    "consider", "describe", "detail", "dimension", "does", "each", "error", "every",
    "existence", "explain", "explanation", "finite", "focus", "for", "from", "full", "given", "going",
    "have", "how", "idea", "identify", "include", "inner", "into", "its", "key", "learner", "main",
    "guarantee", "matrix", "nature", "operator", "product", "properties", "property", "provide", "prompt",
    "represent", "response", "should", "sketch", "space", "specialize", "spectral", "state", "statement", "such", "suppose",
    "that", "the", "theorem", "their", "this", "unitary", "unseen", "what", "with", "without", "would",
    "your", "you",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _terms(value: Any) -> set[str]:
    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z-]{2,}", str(value or "").lower()):
        term = raw.strip("-")
        if term in _STOP_TERMS:
            continue
        if term.endswith("ies"):
            term = term[:-3] + "y"
        elif term.endswith("s") and len(term) > 4 and not term.endswith("us"):
            term = term[:-1]
        if term.endswith("ization"):
            term = term[:-7]
        elif term.endswith("izable"):
            term = term[:-6]
        if term not in _STOP_TERMS:
            terms.add(term)
    return terms


def _contains_forbidden(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(str(key) in _FORBIDDEN_KEYS or _contains_forbidden(item) for key, item in value.items())
    if isinstance(value, (tuple, list)):
        return any(_contains_forbidden(item) for item in value)
    return False


def learner_visible_strategy_packet(learning_state: Mapping[str, Any]) -> dict[str, Any]:
    """Extract only the evidence a learner may use to plan its next study step."""

    state = dict(learning_state)
    mission = dict(state.get("mission") or {})
    bundle = dict(state.get("retained_bundle") or {})
    resources = tuple(dict(item) for item in (bundle.get("study_resources") or ()) if isinstance(item, Mapping))
    attempts = tuple(dict(item) for item in (state.get("attempts") or ()) if isinstance(item, Mapping))
    evaluations = tuple(dict(item) for item in (state.get("evaluations") or ()) if isinstance(item, Mapping))
    recovery = dict(state.get("teaching_material_recovery") or {})
    artifact = dict(recovery.get("artifact") or {})
    latest = attempts[-1] if attempts else {}
    public_cases: list[dict[str, Any]] = []
    for record in latest.get("task_records") or ():
        if not isinstance(record, Mapping):
            continue
        public_cases.append({
            "case_id": str(record.get("case_id") or record.get("task_id") or ""),
            "case_category": str(record.get("case_kind") or ""),
            "visible_prompt": str(record.get("visible_prompt") or ""),
            "response_format": dict(record.get("response_schema") or {}),
            "learner_response": dict(record.get("candidate_response") or {}),
            "insufficiency": str(record.get("evidence_sufficiency") or ""),
            "missing_evidence_terms": tuple(str(item) for item in (record.get("missing_retained_evidence_terms") or ())),
            "evidence_ref": str(record.get("output_digest") or ""),
        })
    payload = {
        "mission": {
            "mission_id": str(mission.get("mission_id") or ""),
            "goal_id": str(mission.get("goal_id") or ""),
            "topic": str(mission.get("topic") or ""),
            "target_capability": str(mission.get("primary_capability_target") or ""),
            "assessment_dimension": str((evaluations[-1] if evaluations else {}).get("capability_dimension") or ""),
            "allowed_resource_classes": tuple(str(item) for item in (mission.get("allowed_resource_classes") or ())),
            "excluded_resource_classes": tuple(str(item) for item in (mission.get("excluded_resource_classes") or ())),
            "attempt_budget": int(mission.get("attempt_budget") or 0),
        },
        "teaching_resources": tuple({
            "resource_id": str(item.get("resource_id") or ""),
            "topic": str(item.get("topic") or ""),
            "study_facts": tuple(str(fact) for fact in (item.get("study_facts") or ())),
            "study_components": tuple(str(component) for component in (item.get("study_components") or ())),
            "supports_dimensions": tuple(str(dim) for dim in (item.get("supports_dimensions") or ())),
        } for item in resources),
        "public_failed_cases": tuple(public_cases),
        "attempt_id": str(latest.get("attempt_id") or ""),
        "evaluation_id": str((evaluations[-1] if evaluations else {}).get("evaluation_id") or ""),
        "evaluation_disposition": str((evaluations[-1] if evaluations else {}).get("disposition") or ""),
        "available_resource_classes": (
            "retained_local_evidence", "retained_exact_source", "deterministic_local_analysis",
            "local_model_advisory", "operator_supplied_teaching_resource", "exact_source_external_retrieval",
        ),
        "retained_exact_source": {
            "source_id": str(artifact.get("source_identity") or recovery.get("source_record_id") or ""),
            "source_locator": str(artifact.get("source_locator") or recovery.get("source_locator") or ""),
            "source_digest": str(artifact.get("source_digest") or recovery.get("source_digest") or ""),
        },
    }
    if _contains_forbidden(payload):
        raise ValueError("learner strategy packet contains evaluator-only material")
    payload["evidence_digest"] = _digest(payload)
    return payload


@dataclass(frozen=True)
class GovernedLearningStrategy:
    strategy_id: str
    strategy_version: int
    mission_id: str
    goal_id: str
    topic: str
    target_capability: str
    assessment_dimension: str
    source_attempt_id: str
    source_evaluation_id: str
    retained_artifact_ids: tuple[str, ...]
    evidence_digest: str
    semantic_identity: str
    authoring_method: str
    status: str
    knowledge_inventory: tuple[dict[str, Any], ...]
    failure_diagnosis: tuple[dict[str, Any], ...]
    prerequisite_hypotheses: tuple[dict[str, Any], ...]
    learning_questions: tuple[dict[str, Any], ...]
    ranked_resource_plan: tuple[dict[str, Any], ...]
    study_plan: tuple[dict[str, Any], ...]
    verification_plan: Mapping[str, Any]
    authority_candidates: tuple[dict[str, Any], ...]
    stop_and_fallback_conditions: tuple[dict[str, Any], ...]
    created_at: str
    strategy_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compile_governed_learning_strategy(packet: Mapping[str, Any]) -> GovernedLearningStrategy:
    """Compile a bounded deterministic proposal from public learning evidence."""

    source = dict(packet)
    mission = dict(source.get("mission") or {})
    evidence_digest = str(source.get("evidence_digest") or _digest(source))
    resources = tuple(dict(item) for item in (source.get("teaching_resources") or ()) if isinstance(item, Mapping))
    facts = tuple(str(fact) for item in resources for fact in (item.get("study_facts") or ()))
    components = tuple(str(item) for resource in resources for item in (resource.get("study_components") or ()))
    evidence_terms = _terms(" ".join(facts + components))
    resource_ids = tuple(str(item.get("resource_id") or "") for item in resources if item.get("resource_id"))
    retained_source = dict(source.get("retained_exact_source") or {})
    knowledge = tuple({
        "claim_id": stable_id("learning-supported-claim", resource_id, fact),
        "claim": fact,
        "support_state": "supported",
        "confidence": 0.8,
        "evidence_refs": (resource_id,),
    } for resource_id, resource in ((str(item.get("resource_id") or ""), item) for item in resources) for fact in (resource.get("study_facts") or ()))
    diagnoses: list[dict[str, Any]] = []
    hypotheses: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    missing_frequency: dict[str, int] = {}
    case_missing: list[tuple[dict[str, Any], tuple[str, ...]]] = []
    for case in source.get("public_failed_cases") or ():
        item = dict(case)
        prompt_terms = _terms(item.get("visible_prompt"))
        explicit_missing = {
            term
            for value in (item.get("missing_evidence_terms") or ())
            for term in _terms(value)
        }
        missing = tuple(sorted(explicit_missing | (prompt_terms - evidence_terms)))
        case_missing.append((item, missing))
        for term in missing:
            missing_frequency[term] = missing_frequency.get(term, 0) + 1
    preferred_terms = tuple(sorted(missing_frequency, key=lambda term: (-missing_frequency[term], -len(term), term))[:8])
    preferred_set = set(preferred_terms)
    for item, missing in case_missing:
        cause = "missing_factual_evidence" if missing else "inability_to_apply_known_facts"
        diagnosis_id = stable_id("learning-failure-diagnosis", evidence_digest, item.get("case_id"), cause)
        diagnoses.append({
            "diagnosis_id": diagnosis_id,
            "case_id": str(item.get("case_id") or ""),
            "case_category": str(item.get("case_category") or ""),
            "public_prompt_operation": _operation(item.get("visible_prompt")),
            "learner_response": item.get("learner_response") or {},
            "relevant_response_evidence": tuple(facts),
            "failure_category": cause,
            "missing_evidence_terms": missing,
            "confidence": 0.75 if missing else 0.55,
            "evidence_refs": tuple(filter(None, (str(item.get("evidence_ref") or ""), str(source.get("attempt_id") or "")))),
        })
        for term in (term for term in missing if term in preferred_set):
            prerequisite_id = stable_id("learning-prerequisite-hypothesis", mission.get("mission_id"), term)
            if any(existing["prerequisite_id"] == prerequisite_id for existing in hypotheses):
                continue
            hypothesis = {
                "prerequisite_id": prerequisite_id,
                "statement": f"Understand the role and scope of {term} for the target capability.",
                "blocking_reason": f"Learner-visible case {item.get('case_id')} uses {term}, which retained evidence does not support.",
                "evidence_refs": (diagnosis_id,),
                "confidence": 0.7,
                "support_state": "unsupported",
                "dependencies": (),
                "estimated_learning_value": 0.7,
                "estimated_effort": 0.35,
                "estimated_information_gain": 0.75,
                "estimated_risk": 0.08,
                "uncertainty": "hypothesis derived from learner-visible prompt/evidence mismatch",
            }
            hypotheses.append(hypothesis)
            questions.append({
                "question_id": stable_id("learning-question", prerequisite_id),
                "question": f"What does {term} mean, how does it relate to {mission.get('target_capability') or mission.get('topic')}, and what conditions bound that relationship?",
                "prerequisite_ids": (prerequisite_id,),
                "expected_evidence_type": "provenanced teaching explanation with a bounded example or scope statement",
                "plan_change_reason": "A grounded answer determines whether the learner can revise the affected response without fabrication.",
                "sufficiency_condition": f"A retained or approved source directly explains {term} and its relation to the target capability.",
                "preferred_resource_classes": ("retained_exact_source", "deterministic_local_analysis"),
                "fallback_resource_classes": ("operator_supplied_teaching_resource", "exact_source_external_retrieval", "local_model_advisory"),
                "estimated_cost": 0.0,
                "estimated_effort": 0.2,
                "uncertainty": "source coverage is not yet established",
            })
    questions = questions[:8]
    hypotheses = hypotheses[:8]
    retained_sufficient = not hypotheses
    actions = [
        {
            "action_id": stable_id("learning-resource-action", evidence_digest, "retained_local_evidence"),
            "resource_class": "retained_local_evidence",
            "question_ids": tuple(item["question_id"] for item in questions),
            "rank": 1.0,
            "status": "selected" if retained_sufficient else "considered_insufficient",
            "authority_required": False,
            "rationale": "Already retained evidence is lowest cost and was checked before requesting new authority.",
            "fallback": "request_narrower_authority_if_questions_remain_unanswered",
        },
        {
            "action_id": stable_id("learning-resource-action", evidence_digest, "retained_exact_source"),
            "resource_class": "retained_exact_source",
            "question_ids": tuple(item["question_id"] for item in questions),
            "rank": 0.8,
            "status": "recommended" if hypotheses else "not_needed",
            "authority_required": True,
            "rationale": "The retained artifact is insufficient; reconsulting the same provenanced source is narrower than source expansion.",
            "source_identity": str(retained_source.get("source_id") or ""),
            "source_locator": str(retained_source.get("source_locator") or ""),
            "source_digest": str(retained_source.get("source_digest") or ""),
            "fallback": "source_insufficiency_report_then_operator_scoped_resource_choice",
        },
        {
            "action_id": stable_id("learning-resource-action", evidence_digest, "local_model_advisory"),
            "resource_class": "local_model_advisory",
            "question_ids": tuple(item["question_id"] for item in questions),
            "rank": 0.45,
            "status": "fallback_only" if hypotheses else "not_needed",
            "authority_required": True,
            "rationale": "Advisory synthesis is considered only after retained evidence and exact-source coverage are insufficient.",
            "fallback": "defer_or_request_operator_supplied_teaching_resource",
        },
    ]
    selected_action = next((item for item in actions if item["status"] == "selected"), next(item for item in actions if item["status"] == "recommended"))
    authority = () if not selected_action["authority_required"] else ({
        "authority_request_id": stable_id("learning-strategy-authority", evidence_digest, selected_action["resource_class"]),
        "action_type": selected_action["resource_class"],
        "scope": "answer only the strategy-bound learner questions using the retained exact source",
        "source_identity": selected_action.get("source_identity") or "",
        "source_locator": selected_action.get("source_locator") or "",
        "source_digest": selected_action.get("source_digest") or "",
        "question_ids": selected_action["question_ids"],
        "maximum_calls_or_retrievals": 1,
        "cost_boundary": "one bounded approved action",
        "stopping_condition": "all strategy questions answered or source insufficiency recorded",
        "prohibited_actions": ("provider_call_without_approval", "broad_research", "capability_update", "sealed_evaluator_access"),
        "retained_evidence_insufficiency": True,
    },)
    study_plan = tuple({
        "operation_id": stable_id("learning-study-operation", question["question_id"]),
        "operation": "construct_grounded_explanation_and_scope_example",
        "question_ids": (question["question_id"],),
        "rationale": "Selected because the learner-visible failure is an unsupported explanation or application.",
    } for question in questions)
    verification = {
        "readiness_conditions": (
            "each high-priority question has a cited learner-visible answer",
            "each hypothesis is supported, rejected, or unresolved",
            "revised responses differ by prompt operation rather than repeating one summary",
            "no claim depends on absent evidence",
        ),
        "promotion_prohibited": True,
        "sealed_evaluation_required_for_capability": True,
    }
    stop_conditions = (
        {"condition": "selected source does not answer a question", "outcome": "record_source_insufficiency_and_pause_for_narrower_authority"},
        {"condition": "no grounded question remains", "outcome": "defer_or_return_to_agenda_without_learning_retry"},
        {"condition": "budget or authority is absent", "outcome": "await_operator_authority"},
    )
    semantic = _digest({"mission_id": mission.get("mission_id"), "evidence": evidence_digest, "questions": tuple(item["question_id"] for item in questions)})
    body = {
        "strategy_version": LEARNING_STRATEGY_VERSION, "mission_id": mission.get("mission_id"), "semantic": semantic,
        "knowledge": knowledge, "diagnoses": diagnoses, "hypotheses": hypotheses, "questions": questions,
        "actions": actions, "authority": authority,
    }
    return GovernedLearningStrategy(
        strategy_id=stable_id("governed-learning-strategy", LEARNING_STRATEGY_VERSION, semantic), strategy_version=LEARNING_STRATEGY_VERSION,
        mission_id=str(mission.get("mission_id") or ""), goal_id=str(mission.get("goal_id") or ""),
        topic=str(mission.get("topic") or ""), target_capability=str(mission.get("target_capability") or ""),
        assessment_dimension=str(mission.get("assessment_dimension") or ""), source_attempt_id=str(source.get("attempt_id") or ""),
        source_evaluation_id=str(source.get("evaluation_id") or ""), retained_artifact_ids=resource_ids,
        evidence_digest=evidence_digest, semantic_identity=semantic, authoring_method="deterministic_learner_visible_evidence_compilation",
        status="learning_strategy_validated_candidate", knowledge_inventory=knowledge, failure_diagnosis=tuple(diagnoses),
        prerequisite_hypotheses=tuple(hypotheses), learning_questions=tuple(questions), ranked_resource_plan=tuple(actions),
        study_plan=study_plan, verification_plan=verification, authority_candidates=authority,
        stop_and_fallback_conditions=stop_conditions, created_at=utc_now(), strategy_digest=_digest(body),
    )


def _operation(prompt: Any) -> str:
    text = str(prompt or "").lower()
    if "prove" in text or "proof" in text:
        return "proof_or_derivation"
    if "error" in text or "claim" in text or "false" in text:
        return "scope_or_misconception_analysis"
    if "suppose" in text or "given" in text or "consider" in text:
        return "bounded_application"
    return "concept_explanation"


def validate_governed_learning_strategy(strategy: Mapping[str, Any], packet: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed when a plan exceeds its public evidence or authority boundary."""

    item = dict(strategy)
    source = dict(packet)
    errors: list[str] = []
    if _contains_forbidden(item):
        errors.append("evaluator_only_material_present")
    if str(item.get("mission_id") or "") != str(dict(source.get("mission") or {}).get("mission_id") or ""):
        errors.append("mission_binding_mismatch")
    if str(item.get("evidence_digest") or "") != str(source.get("evidence_digest") or ""):
        errors.append("evidence_digest_mismatch")
    evidence_refs = {str(source.get("attempt_id") or ""), str(source.get("evaluation_id") or "")}
    evidence_refs.update(str(item.get("resource_id") or "") for item in (source.get("teaching_resources") or ()) if isinstance(item, Mapping))
    for claim in item.get("knowledge_inventory") or ():
        if not set(str(ref) for ref in (claim.get("evidence_refs") or ())).issubset(evidence_refs):
            errors.append("unsupported_knowledge_claim")
    hypotheses = {str(hypothesis.get("prerequisite_id") or "") for hypothesis in (item.get("prerequisite_hypotheses") or ())}
    diagnosis_ids = {str(diagnosis.get("diagnosis_id") or "") for diagnosis in (item.get("failure_diagnosis") or ())}
    for hypothesis in item.get("prerequisite_hypotheses") or ():
        if not set(str(ref) for ref in (hypothesis.get("evidence_refs") or ())).issubset(diagnosis_ids):
            errors.append("ungrounded_prerequisite_hypothesis")
    question_ids = {str(question.get("question_id") or "") for question in (item.get("learning_questions") or ())}
    for question in item.get("learning_questions") or ():
        if not str(question.get("question") or "").strip() or not set(question.get("prerequisite_ids") or ()).issubset(hypotheses):
            errors.append("invalid_learning_question")
        if "everything" in str(question.get("question") or "").lower():
            errors.append("broad_learning_question")
    for action in item.get("ranked_resource_plan") or ():
        if not set(action.get("question_ids") or ()).issubset(question_ids):
            errors.append("resource_action_without_question")
    for authority in item.get("authority_candidates") or ():
        if not str(authority.get("scope") or "").strip() or int(authority.get("maximum_calls_or_retrievals") or 0) > 1:
            errors.append("unbounded_authority_candidate")
    if item.get("verification_plan", {}).get("promotion_prohibited") is not True:
        errors.append("internal_verification_may_not_promote_capability")
    return {"accepted": not errors, "errors": tuple(dict.fromkeys(errors)), "validation_digest": _digest({"strategy": item.get("strategy_id"), "errors": errors}), "validated_at": utc_now()}
