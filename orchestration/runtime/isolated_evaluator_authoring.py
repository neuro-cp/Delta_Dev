"""Strict request and response contracts for isolated evaluator authoring.

The authoring model receives only an evaluation specification.  It never sees
learner work or teaching material, and a valid response is retained as sealed
evaluator material rather than a learner-visible resource.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


PROTOCOL = "isolated_evaluator_authoring_v3"
EXECUTION_CONTRACT_VERSION = "sealed_evaluator_execution_v3"
CASE_KINDS = ("baseline", "control", "held_out", "adversarial", "transfer")
FULFILLMENT_TYPE = "operator_sealed_evaluator_fulfillment"
FORBIDDEN_RESPONSE_FIELDS = frozenset({
    "study_resources",
    "teaching_content",
    "teaching_notes",
    "learner_answer",
    "candidate_answer",
    "candidate_output",
    "prior_attempted_solution",
    "runtime_state",
})
_FORBIDDEN_RESPONSE_KEYS = FORBIDDEN_RESPONSE_FIELDS | frozenset({
    "study_resource",
    "teaching_source_content",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(_normalized(value))


def _complete_scoring_rule(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and _nonempty_string(value.get("procedure"))
        and _nonempty_string(value.get("pass_condition"))
    )


def sealed_evaluator_execution_errors(
    sealed_package: Mapping[str, Any],
    *,
    target_capability: str,
    assessment_dimension: str,
) -> tuple[str, ...]:
    """Return deterministic execution-contract failures without mutating a package."""

    if str(sealed_package.get("execution_contract_version") or "") != EXECUTION_CONTRACT_VERSION:
        return ("unsupported_execution_contract_version",)
    errors: list[str] = []
    for case in sealed_package.get("sealed_evaluation_cases") or ():
        if not isinstance(case, Mapping):
            errors.append("case_not_object")
            continue
        if str(case.get("target_capability") or "") != target_capability:
            errors.append("target_capability_binding_missing_or_mismatched")
        if str(case.get("assessment_dimension") or "") != assessment_dimension:
            errors.append("assessment_dimension_binding_missing_or_mismatched")
        learner = dict(case.get("learner_view") or {})
        if not _nonempty_string(learner.get("instruction")) or not isinstance(learner.get("input_data"), Mapping):
            errors.append("learner_execution_input_missing")
        if not isinstance(learner.get("response_schema"), Mapping) or not _nonempty_string(learner.get("response_schema", {}).get("response_kind")):
            errors.append("learner_response_schema_missing")
        evaluator = dict(case.get("evaluator_view") or {})
        predicate = dict(evaluator.get("deterministic_predicate") or {})
        if predicate.get("type") != "required_concept_coverage" or not isinstance(predicate.get("required_concepts"), (list, tuple)) or not predicate.get("required_concepts"):
            errors.append("deterministic_scoring_predicate_missing_or_unsupported")
    return tuple(sorted(set(errors)))


def _placeholder_response_example() -> dict[str, Any]:
    """Show response shape without supplying evaluator answers for this mission."""

    return {
        "fulfillment_type": FULFILLMENT_TYPE,
        "source_identity": "placeholder-independent-evaluator",
        "source_reference": "provider://placeholder/isolated-evaluator",
        "source_digest": "placeholder-source-digest",
        "provenance": {
            "authoring_method": "independent_evaluator_authoring",
            "independence_statement": "placeholder content was not supplied to the learner",
        },
        "topic": "<echo topic from capability_specification>",
        "target_capability": "<echo target_capability from capability_specification>",
        "independent_evaluator": {
            "evaluator_identity": "placeholder-evaluator-id",
            "teaching_source_isolated": True,
        },
        "candidate_mutable": False,
        "authoring_provenance": {
            "provider": "<echo provider>",
            "model": "<echo model>",
            "input_packet_digest": "<echo input_packet_digest>",
            "request_id": "<echo request_id>",
            "timestamp": "<provider timestamp>",
        },
        "sealed_evaluation_cases": [
            {
                "case_id": f"placeholder-{kind}-001",
                "case_kind": kind,
                "task_type": "placeholder_independent_task",
                "learner_view": {
                    "category": kind,
                    "prompt": "Placeholder learner prompt; replace with a self-contained non-secret task.",
                    "response_format": "placeholder structured response",
                    "constraints": [],
                },
                "evaluator_view": {
                    "answer_key": None,
                    "scoring_rule": {
                        "procedure": "placeholder deterministic procedure; replace with a complete evaluator procedure",
                        "pass_condition": "placeholder pass condition; replace with a complete evaluator condition",
                    },
                    "rubric": ["placeholder evaluator criterion"],
                    "pass_threshold": 1.0,
                    "provenance": {"evaluator_case_author": "placeholder"},
                },
            }
            for kind in CASE_KINDS
        ],
    }


def openai_evaluator_authoring_json_schema(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return the strict native Structured Outputs schema for one authoring call."""

    capability = dict(request.get("input_packet", {}).get("capability_specification") or {})
    provenance = dict(request.get("input_packet", {}).get("authoring_provenance_required") or {})
    nullable_matrix = {"anyOf": [
        {"type": "object", "additionalProperties": False, "required": ("rows",), "properties": {"rows": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}}}},
        {"type": "null"},
    ]}
    nullable_vector = {"anyOf": [
        {"type": "object", "additionalProperties": False, "required": ("values",), "properties": {"values": {"type": "array", "items": {"type": "number"}}}},
        {"type": "null"},
    ]}
    input_data_schema = {
        "type": "object", "additionalProperties": False,
        "required": ("input_kind", "prompt_context", "matrix_data", "vector_data", "scalar_parameters"),
        "properties": {
            "input_kind": {"type": "string", "enum": ["text_context", "matrix", "vector", "scalar_parameters"]},
            "prompt_context": {"type": ["string", "null"]},
            "matrix_data": nullable_matrix,
            "vector_data": nullable_vector,
            "scalar_parameters": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ("name", "value"), "properties": {"name": {"type": "string"}, "value": {"type": "number"}}}},
        },
    }
    response_schema = {
        "type": "object", "additionalProperties": False,
        "required": ("response_kind", "required_fields", "allow_additional_fields", "max_response_words"),
        "properties": {
            "response_kind": {"type": "string", "enum": ["text_explanation", "structured_concept_response"]},
            "required_fields": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ("field_name", "field_type"), "properties": {"field_name": {"type": "string"}, "field_type": {"type": "string", "enum": ["text", "concept_list"]}}}},
            "allow_additional_fields": {"type": "boolean", "const": False},
            "max_response_words": {"type": ["integer", "null"]},
        },
    }
    predicate_schema = {"type": "object", "additionalProperties": False, "required": ("type", "required_concepts", "forbidden_concepts", "minimum_coverage"), "properties": {"type": {"type": "string", "const": "required_concept_coverage"}, "required_concepts": {"type": "array", "items": {"type": "string"}}, "forbidden_concepts": {"type": "array", "items": {"type": "string"}}, "minimum_coverage": {"type": "number"}}}
    case_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ("case_id", "case_kind", "task_type", "target_capability", "assessment_dimension", "execution_contract_version", "learner_view", "evaluator_view"),
        "properties": {
            "case_id": {"type": "string"},
            "case_kind": {"type": "string", "enum": list(CASE_KINDS)},
            "task_type": {"type": "string"},
            "target_capability": {"type": "string", "const": str(capability.get("target_capability") or "")},
            "assessment_dimension": {"type": "string"},
            "execution_contract_version": {"type": "string", "const": EXECUTION_CONTRACT_VERSION},
            "learner_view": {
                "type": "object", "additionalProperties": False,
                "required": ("category", "prompt", "response_format", "constraints", "instruction", "input_data", "response_schema"),
                "properties": {
                    "category": {"type": "string", "enum": list(CASE_KINDS)},
                    "prompt": {"type": "string"},
                    "response_format": {"type": "string"},
                    "constraints": {"type": "array", "items": {"type": "string"}},
                    "instruction": {"type": "string"},
                    "input_data": input_data_schema,
                    "response_schema": response_schema,
                },
            },
            "evaluator_view": {
                "type": "object", "additionalProperties": False,
                "required": ("answer_key", "scoring_rule", "deterministic_predicate", "rubric", "pass_threshold", "provenance"),
                "properties": {
                    "answer_key": {"type": ("string", "null")},
                    "scoring_rule": {
                        "anyOf": (
                            {
                                "type": "object", "additionalProperties": False,
                                "required": ("procedure", "pass_condition"),
                                "properties": {"procedure": {"type": "string"}, "pass_condition": {"type": "string"}},
                            },
                            {"type": "null"},
                        ),
                    },
                    "deterministic_predicate": predicate_schema,
                    "rubric": {"type": "array", "items": {"type": "string"}},
                    "pass_threshold": {"type": "number"},
                    "provenance": {"type": "object", "additionalProperties": False, "required": ("evaluator_case_author",), "properties": {"evaluator_case_author": {"type": "string"}}},
                },
            },
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": (
            "fulfillment_type", "source_identity", "source_reference", "source_digest", "provenance", "execution_contract_version",
            "topic", "target_capability", "independent_evaluator", "candidate_mutable",
            "authoring_provenance", "sealed_evaluation_cases",
        ),
        "properties": {
            "fulfillment_type": {"type": "string", "const": FULFILLMENT_TYPE},
            "execution_contract_version": {"type": "string", "const": EXECUTION_CONTRACT_VERSION},
            "source_identity": {"type": "string"},
            "source_reference": {"type": "string"},
            "source_digest": {"type": "string"},
            "provenance": {
                "type": "object", "additionalProperties": False,
                "required": ("authoring_method", "independence_statement"),
                "properties": {
                    "authoring_method": {"type": "string"},
                    "independence_statement": {"type": "string"},
                },
            },
            "topic": {"type": "string", "const": str(capability.get("topic") or "")},
            "target_capability": {"type": "string", "const": str(capability.get("target_capability") or "")},
            "independent_evaluator": {
                "type": "object", "additionalProperties": False,
                "required": ("evaluator_identity", "teaching_source_isolated"),
                "properties": {
                    "evaluator_identity": {"type": "string"},
                    "teaching_source_isolated": {"type": "boolean", "const": True},
                },
            },
            "candidate_mutable": {"type": "boolean", "const": False},
            "authoring_provenance": {
                "type": "object", "additionalProperties": False,
                "required": ("provider", "model", "input_packet_digest", "request_id", "timestamp"),
                "properties": {
                    "provider": {"type": "string", "const": str(provenance.get("provider") or "")},
                    "model": {"type": "string", "const": str(provenance.get("model") or "")},
                    "input_packet_digest": {"type": "string", "const": str(provenance.get("input_packet_digest") or "")},
                    "request_id": {"type": "string", "const": str(provenance.get("request_id") or "")},
                    "timestamp": {"type": "string"},
                },
            },
            "sealed_evaluation_cases": {"type": "array", "minItems": len(CASE_KINDS), "items": case_schema},
        },
    }


def _forbidden_keys(value: Any) -> set[str]:
    """Find prohibited payload keys at any nesting level.

    Checking only the top-level response would let a provider hide teaching or
    learner data inside provenance, a case payload, or a scoring rule record.
    The protocol forbids those keys everywhere, while leaving arbitrary answer
    *content* to the sealed evaluator package.
    """

    if isinstance(value, Mapping):
        found = {str(key) for key in value if str(key) in _FORBIDDEN_RESPONSE_KEYS}
        for nested in value.values():
            found.update(_forbidden_keys(nested))
        return found
    if isinstance(value, (tuple, list)):
        found: set[str] = set()
        for nested in value:
            found.update(_forbidden_keys(nested))
        return found
    return set()


def compile_isolated_evaluator_authoring_request(
    *,
    mission_id: str,
    requirement: Mapping[str, Any],
    provider: str,
    model: str,
    attempt_nonce: str = "",
) -> dict[str, Any]:
    """Compile a provider-neutral, evaluator-only request with no learner data."""

    capability_spec = {
        "topic": _normalized(requirement.get("topic")),
        "target_capability": _normalized(requirement.get("target_capability")),
        "assessment_dimension": _normalized(requirement.get("assessment_dimension") or requirement.get("target_capability")),
        "target_behavior": _normalized(requirement.get("target_behavior")),
    }
    input_packet = {
        "protocol": PROTOCOL,
        "execution_contract_version": EXECUTION_CONTRACT_VERSION,
        "authoring_role": "independent_sealed_evaluator_author",
        "capability_specification": capability_spec,
        "required_case_categories": CASE_KINDS,
        "schema_requirements": {
            "fulfillment_type": FULFILLMENT_TYPE,
            "required_fields": (
                "source_identity",
                "source_reference",
                "source_digest",
                "provenance",
                "topic",
                "target_capability",
                "independent_evaluator",
                "candidate_mutable",
                "sealed_evaluation_cases",
            ),
            "candidate_mutable": False,
            "study_resources_permitted": False,
            "field_types": {
                "source_identity": "nonempty_string",
                "source_reference": "nonempty_string",
                "source_digest": "nonempty_string",
                "provenance": "nonempty_object",
                "topic": "nonempty_string",
                "target_capability": "nonempty_string",
                "candidate_mutable": "boolean_false",
                "independent_evaluator": {
                    "type": "object",
                    "required_fields": {
                        "evaluator_identity": "nonempty_string",
                        "teaching_source_isolated": "boolean_true",
                    },
                },
                "authoring_provenance": {
                    "type": "object",
                    "required_fields": {
                        "provider": "nonempty_string",
                        "model": "nonempty_string",
                        "input_packet_digest": "nonempty_string",
                        "request_id": "nonempty_string",
                        "timestamp": "nonempty_string",
                    },
                },
                "sealed_evaluation_cases": {
                    "type": "array_of_objects",
                    "item_required_fields": {
                        "case_id": "nonempty_string",
                        "case_kind": "baseline|control|held_out|adversarial|transfer",
                        "task_type": "nonempty_string",
                        "learner_view": {"category": "matches_case_kind", "prompt": "nonempty_string", "response_format": "nonempty_string", "constraints": "array_of_nonsecret_strings"},
                        "evaluator_view": {"answer_key_or_complete_scoring_rule": "required", "rubric": "array_of_nonempty_strings", "pass_threshold": "number_in_0_to_1", "provenance": "nonempty_object"},
                    },
                },
            },
            "required_object_examples": {
                "independent_evaluator": {
                    "evaluator_identity": "isolated-evaluator-identifier",
                    "teaching_source_isolated": True,
                },
                "provenance": {"authoring_method": "independent_evaluator_authoring"},
                "authoring_provenance": {
                    "provider": "exact_provider_from_request",
                    "model": "exact_model_from_request",
                    "input_packet_digest": "exact_input_packet_digest_from_request",
                    "request_id": "exact_request_id_from_request",
                    "timestamp": "provider_generated_timestamp",
                },
            },
        },
        "scoring_criteria": {
            "each_case_requires": ("case_id", "case_kind", "task_type"),
            "learner_view_requirement": "each case must contain an explicit learner_view with category, prompt, response_format, and only non-secret constraints",
            "answer_key_requirement": "each evaluator_view must contain answer_key or scoring_rule; a scoring_rule requires procedure and pass_condition",
            "coverage_requirement": "one or more cases for every required category",
            "execution_requirement": "every case must bind target_capability and assessment_dimension, provide learner instruction/input_data/response_schema, and evaluator_view.deterministic_predicate={type: required_concept_coverage, required_concepts: [nonempty strings], forbidden_concepts: [strings]}",
        },
        "independence_constraints": (
            "do_not_include_or_request_learner_answers",
            "do_not_include_teaching_material_or_study_resources",
            "do_not_reference_hidden_runtime_state",
            "author_response_is_not_capability_evidence_until_sealed_evaluation_passes",
        ),
        "excluded_input_classes": (
            "learner_candidate_answer",
            "learner_internal_study_notes",
            "teaching_source_content",
            "prior_attempted_solutions",
            "unrelated_hidden_runtime_state",
        ),
        "pre_dispatch_schema_checklist": (
            "root fulfillment_type is exactly operator_sealed_evaluator_fulfillment",
            "independent_evaluator, provenance, and authoring_provenance are objects, never booleans",
            "candidate_mutable is exactly false and study_resources is absent",
            "five case kinds are present and every case has separated learner_view and evaluator_view objects",
            "every case has execution_contract_version, target_capability, assessment_dimension, learner input/response schema, and required_concept_coverage predicate",
            "learner_view requires category, nonempty prompt, and nonempty response_format; evaluator_view contains the answer key, scoring rule, rubric, threshold, and provenance",
            "return JSON only with no markdown or prose outside the root object",
        ),
        "response_shape_example": _placeholder_response_example(),
    }
    semantic_identity = _digest({"mission_id": mission_id, "requirement": requirement.get("semantic_identity"), "packet": input_packet, "provider": provider, "model": model, "attempt_nonce": attempt_nonce})
    request_id = stable_id("isolated-evaluator-authoring-request", semantic_identity)
    # The provider needs stable values it can actually echo. A full prompt
    # digest cannot be embedded in its own prompt without a circular digest.
    input_packet_digest = _digest(input_packet)
    input_packet["authoring_provenance_required"] = {
        "provider": provider,
        "model": model,
        "request_id": request_id,
        "input_packet_digest": input_packet_digest,
        "timestamp": "provider_generated_timestamp",
    }
    system_prompt = (
        "You author an isolated evaluation package, not teaching material. Return one JSON object only, "
        "with no markdown fence, prefix, suffix, or prose outside that object. independent_evaluator, provenance, "
        "and authoring_provenance must each be JSON objects, never booleans, strings, arrays, or null. "
        "Use fulfillment_type exactly operator_sealed_evaluator_fulfillment. Every case must contain an answer_key "
        "or a scoring_rule object with both procedure and pass_condition. Every case must contain a learner_view "
        "with category, prompt, response_format, and non-secret constraints, plus a separate evaluator_view with the "
        "answer key, scoring rule, deterministic required_concept_coverage predicate, rubric, pass threshold, and evaluator provenance. "
        "Each learner_view must include instruction, input_data, and a response_schema object. Complete the checklist before responding. "
        "Do not include explanations, study resources, learner answers, candidate answers, or authority claims."
    )
    user_prompt = json.dumps(input_packet, sort_keys=True, separators=(",", ":"))
    prompt_digest = _digest({"system": system_prompt, "user": user_prompt})
    return {
        "request_id": request_id,
        "protocol": PROTOCOL,
        "semantic_identity": semantic_identity,
        # A replacement request is a new one-use authority packet after a
        # terminal claim.  Preserve its nonce so dispatch can revalidate the
        # exact packet that the operator approved.
        "attempt_nonce": attempt_nonce,
        "mission_id": mission_id,
        "provider": provider,
        "model": model,
        "input_packet": input_packet,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "prompt_digest": prompt_digest,
        "input_packet_digest": input_packet_digest,
        "output_contract": {
            "response_format": "strict_json_object",
            "required_case_categories": CASE_KINDS,
            "native_json_schema": openai_evaluator_authoring_json_schema({
                "input_packet": input_packet,
            }),
            "forbidden_response_fields": tuple(sorted(FORBIDDEN_RESPONSE_FIELDS)),
            "sealed_from_learner_before_attempt": True,
        },
        "created_at": utc_now(),
    }


def validate_provider_authored_evaluator_response(
    request: Mapping[str, Any],
    response: Mapping[str, Any] | str,
) -> dict[str, Any]:
    """Validate schema, scope, provenance, and evaluator/learner separation."""

    errors: list[str] = []
    try:
        material = json.loads(response) if isinstance(response, str) else response
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"accepted": False, "errors": ("response_not_valid_json_object",), "sealed_package": {}}
    if not isinstance(material, Mapping):
        return {"accepted": False, "errors": ("response_not_valid_json_object",), "sealed_package": {}}
    material = dict(material)
    present_forbidden = sorted(_forbidden_keys(material))
    if present_forbidden:
        errors.append("forbidden_learner_or_teaching_field_present")
    if material.get("fulfillment_type") != FULFILLMENT_TYPE:
        errors.append("invalid_fulfillment_type")
    capability = dict(request.get("input_packet", {}).get("capability_specification") or {})
    if _normalized(material.get("topic")) != capability.get("topic"):
        errors.append("topic_mismatch")
    if _normalized(material.get("target_capability")) != capability.get("target_capability"):
        errors.append("target_capability_mismatch")
    if material.get("candidate_mutable") is not False:
        errors.append("candidate_must_not_mutate_evaluator")
    if request.get("protocol") == PROTOCOL and material.get("execution_contract_version") != EXECUTION_CONTRACT_VERSION:
        errors.append("execution_contract_version_unsupported")
    evaluator_value = material.get("independent_evaluator")
    evaluator = dict(evaluator_value) if isinstance(evaluator_value, Mapping) else {}
    if evaluator_value is not None and not isinstance(evaluator_value, Mapping):
        errors.append("independent_evaluator_not_object")
    required_provenance = ("provider", "model", "input_packet_digest", "request_id", "timestamp")
    provenance_value = material.get("authoring_provenance")
    provenance = dict(provenance_value) if isinstance(provenance_value, Mapping) else {}
    if provenance_value is not None and not isinstance(provenance_value, Mapping):
        errors.append("authoring_provenance_not_object")
    if any(not _nonempty_string(provenance.get(field)) for field in required_provenance):
        errors.append("authoring_provenance_incomplete")
    elif (
        provenance.get("provider") != request.get("provider")
        or provenance.get("model") != request.get("model")
        or provenance.get("input_packet_digest") != request.get("input_packet_digest")
        or provenance.get("request_id") != request.get("request_id")
    ):
        errors.append("authoring_provenance_mismatch")
    if not _nonempty_string(evaluator.get("evaluator_identity")) or evaluator.get("teaching_source_isolated") is not True:
        errors.append("independent_evaluator_not_proven")
    raw_cases = material.get("sealed_evaluation_cases")
    if not isinstance(raw_cases, (tuple, list)):
        errors.append("sealed_evaluation_cases_not_array_of_objects")
        raw_cases = ()
    cases = tuple(item for item in raw_cases if isinstance(item, Mapping))
    if len(cases) != len(raw_cases):
        errors.append("sealed_evaluation_cases_not_array_of_objects")
    kinds = {str(item.get("case_kind") or item.get("kind") or "") for item in cases}
    if set(CASE_KINDS) - kinds:
        errors.append("required_case_coverage_missing")
    for case in cases:
        if not _nonempty_string(case.get("case_id")) or not _nonempty_string(case.get("task_type")):
            errors.append("case_identity_or_task_missing")
            break
        learner_view = case.get("learner_view")
        evaluator_view = case.get("evaluator_view")
        if not isinstance(learner_view, Mapping):
            errors.append("case_learner_view_not_object")
            break
        if str(learner_view.get("category") or "") != str(case.get("case_kind") or ""):
            errors.append("case_learner_category_mismatch")
            break
        if not _nonempty_string(learner_view.get("prompt")):
            errors.append("case_learner_prompt_missing")
            break
        if not _nonempty_string(learner_view.get("response_format")):
            errors.append("case_learner_response_format_missing")
            break
        if not isinstance(evaluator_view, Mapping):
            errors.append("case_evaluator_view_not_object")
            break
        if not (_nonempty_string(evaluator_view.get("answer_key")) or _complete_scoring_rule(evaluator_view.get("scoring_rule"))):
            errors.append("case_answer_key_or_scoring_rule_missing")
            break
        rubric = evaluator_view.get("rubric")
        if not isinstance(rubric, (tuple, list)) or not rubric or not all(_nonempty_string(item) for item in rubric):
            errors.append("case_evaluator_rubric_missing")
            break
        threshold = evaluator_view.get("pass_threshold")
        if not isinstance(threshold, (int, float)) or not 0.0 <= float(threshold) <= 1.0:
            errors.append("case_evaluator_pass_threshold_invalid")
            break
        if not isinstance(evaluator_view.get("provenance"), Mapping) or not evaluator_view.get("provenance"):
            errors.append("case_evaluator_provenance_missing")
            break
        if any(field in case for field in ("learner_answer", "candidate_answer", "study_resource")):
            errors.append("case_contains_forbidden_learner_or_teaching_field")
            break
        if request.get("protocol") == PROTOCOL:
            if str(case.get("execution_contract_version") or "") != EXECUTION_CONTRACT_VERSION:
                errors.append("case_execution_contract_version_unsupported")
                break
            if _normalized(case.get("target_capability")) != capability.get("target_capability"):
                errors.append("case_target_capability_mismatch")
                break
            if not _nonempty_string(case.get("assessment_dimension")):
                errors.append("case_assessment_dimension_missing")
                break
            if not _nonempty_string(learner_view.get("instruction")) or not isinstance(learner_view.get("input_data"), Mapping):
                errors.append("case_learner_execution_input_missing")
                break
            response_schema = learner_view.get("response_schema")
            if not isinstance(response_schema, Mapping) or not _nonempty_string(response_schema.get("response_kind")):
                errors.append("case_learner_response_schema_missing")
                break
            predicate = evaluator_view.get("deterministic_predicate")
            if not isinstance(predicate, Mapping) or predicate.get("type") != "required_concept_coverage" or not isinstance(predicate.get("required_concepts"), (tuple, list)) or not predicate.get("required_concepts"):
                errors.append("case_deterministic_scoring_predicate_missing_or_unsupported")
                break
    for field in ("source_identity", "source_reference", "source_digest"):
        if not _nonempty_string(material.get(field)):
            errors.append(f"missing_{field}")
    provenance_record = material.get("provenance")
    if not isinstance(provenance_record, Mapping):
        errors.append("provenance_not_object")
    elif not provenance_record:
        errors.append("provenance_missing")
    accepted = not errors
    sealed_package = {}
    if accepted:
        sealed_package = {
            **material,
            "sealed_package_id": stable_id("provider-authored-sealed-evaluator", request.get("request_id"), material.get("source_digest")),
            "authoring_request_prompt_digest": request.get("prompt_digest"),
            "sealed_from_learner_before_attempt": True,
            "learner_visible_metadata": {
                "topic": material["topic"],
                "target_capability": material["target_capability"],
                "case_categories": CASE_KINDS,
                "answer_key_exposed": False,
            },
            "execution_contract_version": material.get("execution_contract_version") if material.get("execution_contract_version") else request.get("input_packet", {}).get("execution_contract_version"),
        }
    return {
        "accepted": accepted,
        "errors": tuple(sorted(set(errors))),
        "sealed_package": sealed_package,
        "response_digest": _digest(material),
    }


def project_learner_visible_evaluation_cases(
    sealed_package: Mapping[str, Any],
) -> dict[str, Any]:
    """Project only learner-safe prompts from an already sealed evaluator.

    The caller never receives keys, scoring rules, provenance, or thresholds.
    A package without an explicit prompt and response format is not silently
    converted into a generic exercise.
    """

    projected: list[dict[str, str]] = []
    errors: list[str] = []
    for raw in sealed_package.get("sealed_evaluation_cases") or ():
        if not isinstance(raw, Mapping):
            errors.append("case_not_object")
            continue
        learner_view = raw.get("learner_view")
        prompt = str(dict(learner_view).get("prompt") or "").strip() if isinstance(learner_view, Mapping) else ""
        response_format = str(dict(learner_view).get("response_format") or "").strip() if isinstance(learner_view, Mapping) else ""
        if not prompt:
            errors.append("missing_learner_visible_evaluation_prompt")
            continue
        if not response_format:
            errors.append("missing_learner_response_format")
            continue
        projected.append({
            "case_id": str(raw.get("case_id") or ""),
            "case_category": str(dict(learner_view).get("category") or ""),
            "prompt": prompt,
            "response_format": response_format,
            "constraints": tuple(str(item) for item in (dict(learner_view).get("constraints") or ())),
        })
    return {
        "accepted": not errors and bool(projected),
        "errors": tuple(sorted(set(errors))),
        "learner_cases": tuple(projected),
    }


__all__ = [
    "CASE_KINDS",
    "FULFILLMENT_TYPE",
    "FORBIDDEN_RESPONSE_FIELDS",
    "PROTOCOL",
    "compile_isolated_evaluator_authoring_request",
    "openai_evaluator_authoring_json_schema",
    "project_learner_visible_evaluation_cases",
    "validate_provider_authored_evaluator_response",
]
