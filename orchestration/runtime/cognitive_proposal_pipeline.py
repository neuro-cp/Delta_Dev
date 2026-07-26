"""Staged CognitiveProposal assembly from validated model artifacts."""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.autonomy_governed_primitives import grounding_result
from orchestration.runtime.cognitive_kernel_adapter import validate_typed_abstention


PROHIBITED_AUTHORITY = {"provider", "network", "deployment", "credentials", "primary_source_mutation", "source_mutation"}
PROHIBITED_PATH_MARKERS = ("DELTA-75", "reports/RC4_", ".env", "*")
PROHIBITED_DIAGNOSIS_FIELDS = {
    "implementation_path",
    "focused_test_path",
    "independent_evaluator_path",
    "bounded_strategy",
    "required_authority",
}
PROHIBITED_PATH_SELECTION_FIELDS = {
    "steps",
    "bounded_strategy",
    "expected_behavioral_change",
    "required_authority",
    "prohibited_authority",
}
PROHIBITED_STRATEGY_AUTHORITY = PROHIBITED_AUTHORITY | {"evaluator_mutation", "unrestricted_shell", "unrestricted_execution"}
SUCCESS_CLAIM_MARKERS = ("tests pass", "tests now pass", "defect is fixed", "successfully fixed", "validated", "deployed")


def _nonempty(value: Any) -> bool:
    return value not in (None, "", (), [])


def _path_bad(path: str) -> bool:
    normalized = str(path).replace("\\", "/")
    return (
        any(marker.lower() in normalized.lower() for marker in PROHIBITED_PATH_MARKERS)
        or normalized.endswith("/")
        or "*" in normalized
        or ".." in normalized.split("/")
        or normalized.startswith("/")
        or ":" in normalized
    )


def _file_exists(path: str) -> bool:
    from pathlib import Path

    return Path(path).is_file()


def _source_index(evidence_packet: Mapping[str, Any]) -> dict[tuple[str, str, str], Mapping[str, Any]]:
    return {
        (str(item.get("source_id")), str(item.get("excerpt_id")), str(item.get("path"))): item
        for item in evidence_packet.get("sources", ())
        if isinstance(item, Mapping)
    }


def _tokens(value: Any) -> set[str]:
    text = "".join(ch.lower() if ch.isalnum() else " " for ch in str(value or ""))
    return {part for part in text.split() if len(part) > 3}


def artifact_or_abstention(payload: Mapping[str, Any] | None, expected_type: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"accepted": False, "abstained": False, "reasons": ("missing_object",)}
    abstention = validate_typed_abstention(payload)
    if abstention["accepted"]:
        return {"accepted": True, "abstained": True, "reasons": (), "abstention": abstention}
    if payload.get("result_type") != expected_type:
        return {"accepted": False, "abstained": False, "reasons": ("wrong_result_type",)}
    return {"accepted": True, "abstained": False, "reasons": ()}


def validate_evidence_selection(payload: Mapping[str, Any] | None, evidence_packet: Mapping[str, Any]) -> dict[str, Any]:
    gate = artifact_or_abstention(payload, "evidence_selection")
    if gate["abstained"] or not gate["accepted"]:
        return {**gate, "schema": "evidence_selection_validation_v1"}
    assert payload is not None
    reasons: list[str] = []
    index = _source_index(evidence_packet)
    selected = payload.get("selected_evidence")
    if not isinstance(selected, list) or not selected:
        reasons.append("selected_evidence_required")
    else:
        for item in selected:
            if not isinstance(item, Mapping):
                reasons.append("selected_evidence_item_invalid")
                continue
            key = (str(item.get("source_id")), str(item.get("excerpt_id")), str(item.get("path")))
            if key not in index:
                reasons.append("invented_evidence_reference")
            if not _nonempty(item.get("supported_claim")):
                reasons.append("supported_claim_required")
    if not isinstance(payload.get("missing_claims"), list):
        reasons.append("missing_claims_not_list")
    uncertainty = payload.get("uncertainty")
    if not isinstance(uncertainty, Mapping) or "score" not in uncertainty or not uncertainty.get("reason"):
        reasons.append("uncertainty_required")
    return {
        "accepted": not reasons,
        "abstained": False,
        "reasons": tuple(dict.fromkeys(reasons)),
        "validated_evidence": tuple(selected or ()),
        "schema": "evidence_selection_validation_v1",
    }


def validate_grounded_diagnosis(payload: Mapping[str, Any] | None, evidence_selection: Mapping[str, Any]) -> dict[str, Any]:
    gate = artifact_or_abstention(payload, "grounded_diagnosis")
    if gate["abstained"] or not gate["accepted"]:
        return {**gate, "schema": "grounded_diagnosis_validation_v1"}
    assert payload is not None
    reasons: list[str] = []
    allowed = {
        (str(item.get("source_id")), str(item.get("excerpt_id")), str(item.get("path")))
        for item in evidence_selection.get("selected_evidence", ())
        if isinstance(item, Mapping)
    }
    support_tokens = set()
    for item in evidence_selection.get("selected_evidence", ()):
        if isinstance(item, Mapping):
            support_tokens |= _tokens(item.get("text") or item.get("excerpt") or item.get("supported_claim") or item.get("claim"))
    refs = payload.get("evidence_references")
    if any(field in payload for field in PROHIBITED_DIAGNOSIS_FIELDS):
        reasons.append("diagnosis_contains_downstream_planning")
    if not _nonempty(payload.get("diagnosis")):
        reasons.append("diagnosis_required")
    elif support_tokens and not (_tokens(payload.get("diagnosis")) & support_tokens):
        reasons.append("diagnosis_not_supported_by_evidence")
    if not _nonempty(payload.get("first_incorrect_transition")):
        reasons.append("first_incorrect_transition_required")
    elif support_tokens and not (_tokens(payload.get("first_incorrect_transition")) & support_tokens):
        reasons.append("transition_not_supported_by_evidence")
    if not isinstance(refs, list) or not refs:
        reasons.append("evidence_references_required")
    else:
        for ref in refs:
            if not isinstance(ref, Mapping):
                reasons.append("evidence_reference_invalid")
                continue
            key = (str(ref.get("source_id")), str(ref.get("excerpt_id")), str(ref.get("path")))
            if key not in allowed:
                reasons.append("reference_not_from_stage_1")
            if not _nonempty(ref.get("claim")):
                reasons.append("reference_claim_required")
            elif support_tokens and not (_tokens(ref.get("claim")) & support_tokens):
                reasons.append("reference_claim_not_supported_by_evidence")
    if not isinstance(payload.get("limitations"), list) or not payload.get("limitations"):
        reasons.append("limitations_required")
    uncertainty = payload.get("uncertainty")
    if not isinstance(uncertainty, Mapping) or "score" not in uncertainty or not uncertainty.get("reason"):
        reasons.append("uncertainty_required")
    return {"accepted": not reasons, "abstained": False, "reasons": tuple(dict.fromkeys(reasons)), "schema": "grounded_diagnosis_validation_v1"}


def validate_path_selection(payload: Mapping[str, Any] | None, allowlist: Mapping[str, Any]) -> dict[str, Any]:
    gate = artifact_or_abstention(payload, "path_selection")
    if gate["abstained"] or not gate["accepted"]:
        return {**gate, "schema": "path_selection_validation_v1"}
    assert payload is not None
    reasons: list[str] = []
    implementation = str(payload.get("implementation_path") or "")
    test = str(payload.get("focused_test_path") or "")
    evaluator = str(payload.get("independent_evaluator_path") or "")
    inspected = set(str(item) for item in allowlist.get("inspected_implementation_paths", ()))
    tests = set(str(item) for item in allowlist.get("focused_test_paths", ()))
    evaluators = set(str(item) for item in allowlist.get("independent_evaluator_paths", ()))
    proposed_tests = set(str(item) for item in allowlist.get("permitted_new_test_paths", ()))
    if any(field in payload for field in PROHIBITED_PATH_SELECTION_FIELDS):
        reasons.append("path_selection_contains_downstream_strategy")
    if implementation not in inspected:
        reasons.append("implementation_path_not_inspected")
    if test not in tests and test not in proposed_tests:
        reasons.append("focused_test_path_not_allowed")
    if test in proposed_tests and _path_bad(test):
        reasons.append("proposed_test_path_invalid")
    if evaluator not in evaluators:
        reasons.append("evaluator_path_not_allowed")
    if evaluator == implementation or evaluator == test and not allowlist.get("allow_evaluator_as_test", True):
        reasons.append("evaluator_not_independent")
    if any(_path_bad(path) for path in (implementation, test, evaluator)):
        reasons.append("prohibited_or_broad_path")
    reasons_payload = payload.get("selection_reasons")
    if not isinstance(reasons_payload, Mapping) or not all(_nonempty(reasons_payload.get(key)) for key in ("implementation", "test", "evaluator")):
        reasons.append("selection_reasons_required")
    if not isinstance(payload.get("limitations"), list) or not payload.get("limitations"):
        reasons.append("limitations_required")
    uncertainty = payload.get("uncertainty")
    if not isinstance(uncertainty, Mapping) or "score" not in uncertainty or not uncertainty.get("reason"):
        reasons.append("uncertainty_required")
    return {"accepted": not reasons, "abstained": False, "reasons": tuple(dict.fromkeys(reasons)), "schema": "path_selection_validation_v1"}


def validate_bounded_strategy(
    payload: Mapping[str, Any] | None,
    *,
    path_selection: Mapping[str, Any],
) -> dict[str, Any]:
    gate = artifact_or_abstention(payload, "bounded_strategy")
    if gate["abstained"] or not gate["accepted"]:
        return {**gate, "schema": "bounded_strategy_validation_v1"}
    assert payload is not None
    reasons: list[str] = []
    files_allowed = set(str(item) for item in payload.get("files_allowed", ()) if item)
    tests_allowed = set(str(item) for item in payload.get("tests_allowed", ()) if item)
    implementation = str(path_selection.get("implementation_path") or "")
    test = str(path_selection.get("focused_test_path") or "")
    evaluator = str(path_selection.get("independent_evaluator_path") or "")
    evaluator_payload = str(payload.get("independent_evaluator_path") or evaluator)
    if implementation not in files_allowed:
        reasons.append("implementation_not_in_files_allowed")
    if files_allowed - {implementation}:
        reasons.append("invented_or_unselected_file_allowed")
    if test not in tests_allowed:
        reasons.append("test_not_in_tests_allowed")
    if tests_allowed - {test}:
        reasons.append("invented_or_unselected_test_allowed")
    if evaluator_payload != evaluator:
        reasons.append("evaluator_path_changed")
    if evaluator in files_allowed:
        reasons.append("strategy_modifies_evaluator")
    if evaluator in tests_allowed and evaluator != test:
        reasons.append("strategy_tests_include_evaluator")
    if not isinstance(payload.get("steps"), list) or not payload.get("steps"):
        reasons.append("steps_required")
    else:
        for step in payload.get("steps", ()):
            if not isinstance(step, Mapping):
                reasons.append("step_invalid")
                continue
            target = str(step.get("target_path") or "")
            if target not in {implementation, test}:
                reasons.append("step_target_not_selected")
            if any(_path_bad(str(step.get(field) or "")) for field in ("target_path",)):
                reasons.append("prohibited_or_broad_path")
    if not _nonempty(payload.get("expected_behavioral_change")):
        reasons.append("expected_behavioral_change_required")
    strategy_text = json.dumps({
        "steps": payload.get("steps"),
        "expected_behavioral_change": payload.get("expected_behavioral_change"),
        "limitations": payload.get("limitations"),
    }, sort_keys=True).lower()
    if any(marker in strategy_text for marker in SUCCESS_CLAIM_MARKERS):
        reasons.append("success_claim_prohibited")
    if not isinstance(payload.get("limitations"), list) or not payload.get("limitations"):
        reasons.append("limitations_required")
    uncertainty = payload.get("uncertainty")
    if not isinstance(uncertainty, Mapping) or "score" not in uncertainty or not uncertainty.get("reason"):
        reasons.append("uncertainty_required")
    requested = {str(item).strip().lower() for item in payload.get("required_authority", ())}
    if requested & PROHIBITED_STRATEGY_AUTHORITY:
        reasons.append("prohibited_authority_requested")
    prohibited = {str(item).strip().lower() for item in payload.get("prohibited_authority", ())}
    missing_prohibited = PROHIBITED_STRATEGY_AUTHORITY - prohibited
    if missing_prohibited:
        reasons.append("prohibited_authority_not_explicit")
    if any(_path_bad(path) for path in files_allowed | tests_allowed):
        reasons.append("prohibited_or_broad_path")
    return {"accepted": not reasons, "abstained": False, "reasons": tuple(dict.fromkeys(reasons)), "schema": "bounded_strategy_validation_v1"}


def assemble_cognitive_proposal(
    *,
    problem_id: str,
    diagnosis: Mapping[str, Any],
    path_selection: Mapping[str, Any],
    strategy: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "proposal_type": "cognitive_proposal",
        "problem_id": problem_id,
        "diagnosis": diagnosis.get("diagnosis"),
        "first_incorrect_transition": diagnosis.get("first_incorrect_transition"),
        "implementation_path": path_selection.get("implementation_path"),
        "focused_test_path": path_selection.get("focused_test_path"),
        "independent_evaluator_path": path_selection.get("independent_evaluator_path"),
        "bounded_strategy": tuple(strategy.get("steps") or ()),
        "limitations": tuple(strategy.get("limitations") or diagnosis.get("limitations") or ()),
        "uncertainty": strategy.get("uncertainty") or diagnosis.get("uncertainty"),
        "evidence_references": tuple(diagnosis.get("evidence_references") or ()),
        "required_authority": tuple(strategy.get("required_authority") or ()),
        "prohibited_authority": tuple(strategy.get("prohibited_authority") or ()),
        "proposal_origin": "local_model",
        "model_output_authoritative": False,
    }


def validate_final_proposal(
    proposal: Mapping[str, Any],
    *,
    evidence_references: Sequence[str],
    inspected_paths: Sequence[str],
    evaluator_path: str,
    allowed_authority: Mapping[str, Any],
) -> dict[str, Any]:
    return grounding_result(
        proposal,
        evidence_references=evidence_references,
        inspected_paths=inspected_paths,
        evaluator_path=evaluator_path,
        allowed_authority=allowed_authority,
    )


def artifact_digest(artifact: Mapping[str, Any]) -> str:
    return bootstrap_digest(artifact)


def _evidence_keys_from_stage1(evidence_selection: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        f"{item.get('source_id')}:{item.get('excerpt_id')}"
        for item in evidence_selection.get("selected_evidence", ())
        if isinstance(item, Mapping) and item.get("source_id") and item.get("excerpt_id")
    )


def _evidence_keys(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        source = str(value.get("source_id") or "").strip()
        excerpt = str(value.get("excerpt_id") or "").strip()
        if source and excerpt:
            return (f"{source}:{excerpt}",)
        if source:
            return (source,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        keys: list[str] = []
        for item in value:
            keys.extend(_evidence_keys(item))
        return tuple(keys)
    return ()


def assemble_validated_cognitive_proposal(
    *,
    evidence_selection: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
    path_selection: Mapping[str, Any],
    strategy: Mapping[str, Any],
    source_artifact_digests: Mapping[str, str],
) -> dict[str, Any]:
    digest_payload = {
        "stage1": source_artifact_digests.get("stage1"),
        "stage2": source_artifact_digests.get("stage2"),
        "stage3": source_artifact_digests.get("stage3"),
        "stage4": source_artifact_digests.get("stage4"),
    }
    proposal_id = stable_id("cognitive-proposal", bootstrap_digest(digest_payload))
    return {
        "proposal_id": proposal_id,
        "proposal_type": "cognitive_proposal",
        "problem_id": diagnosis.get("problem_id"),
        "bounded_objective": strategy.get("expected_behavioral_change"),
        "diagnosis": diagnosis.get("diagnosis"),
        "first_incorrect_transition": diagnosis.get("first_incorrect_transition"),
        "implementation_path": path_selection.get("implementation_path"),
        "focused_test_path": path_selection.get("focused_test_path"),
        "independent_evaluator_path": path_selection.get("independent_evaluator_path"),
        "evidence_references": tuple(diagnosis.get("evidence_references") or ()),
        "bounded_strategy": tuple(strategy.get("steps") or ()),
        "expected_behavioral_change": strategy.get("expected_behavioral_change"),
        "limitations": tuple(strategy.get("limitations") or ()),
        "uncertainty": strategy.get("uncertainty"),
        "required_authority": tuple(strategy.get("required_authority") or ()),
        "prohibited_authority": tuple(strategy.get("prohibited_authority") or ()),
        "prohibited_changes": tuple(strategy.get("prohibited_changes") or ()),
        "source_stage_artifacts": dict(digest_payload),
        "assembly_method": "deterministic_structural_mapping_v1",
        "execution_disposition": "grounded_pending_sandbox_authorization",
        "non_executable": True,
        "proposal_origin": "local_model",
        "model_output_authoritative": False,
        "deterministic_runtime_validated": True,
        "provider_calls": 0,
        "network": False,
        "deployment": False,
        "credentials": False,
        "source_mutation": False,
    }


def audit_cognitive_proposal_consistency(
    *,
    evidence_selection: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
    path_selection: Mapping[str, Any],
    strategy: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    problem_ids = {str(item.get("problem_id")) for item in (evidence_selection, diagnosis, path_selection, strategy, proposal) if item.get("problem_id")}
    if len(problem_ids) != 1:
        reasons.append("problem_id_mismatch")
    stage1_keys = set(_evidence_keys_from_stage1(evidence_selection))
    stage2_keys = set(_evidence_keys(diagnosis.get("evidence_references") or ()))
    proposal_keys = set(_evidence_keys(proposal.get("evidence_references") or ()))
    if not stage2_keys or not stage2_keys.issubset(stage1_keys):
        reasons.append("stage2_evidence_not_from_stage1")
    if proposal_keys != stage2_keys:
        reasons.append("proposal_evidence_not_from_stage2")
    if proposal.get("diagnosis") != diagnosis.get("diagnosis"):
        reasons.append("diagnosis_changed")
    if proposal.get("first_incorrect_transition") != diagnosis.get("first_incorrect_transition"):
        reasons.append("transition_changed")
    if proposal.get("implementation_path") != path_selection.get("implementation_path"):
        reasons.append("implementation_path_changed")
    if proposal.get("focused_test_path") != path_selection.get("focused_test_path"):
        reasons.append("focused_test_path_changed")
    if proposal.get("independent_evaluator_path") != path_selection.get("independent_evaluator_path"):
        reasons.append("evaluator_path_changed")
    if tuple(proposal.get("bounded_strategy") or ()) != tuple(strategy.get("steps") or ()):
        reasons.append("strategy_changed")
    if set(proposal.get("required_authority") or ()) != set(strategy.get("required_authority") or ()):
        reasons.append("required_authority_changed")
    if set(proposal.get("prohibited_authority") or ()) != set(strategy.get("prohibited_authority") or ()):
        reasons.append("prohibited_authority_changed")
    if proposal.get("non_executable") is not True:
        reasons.append("proposal_not_marked_non_executable")
    text = json.dumps({
        "bounded_objective": proposal.get("bounded_objective"),
        "expected_behavioral_change": proposal.get("expected_behavioral_change"),
        "bounded_strategy": proposal.get("bounded_strategy"),
        "limitations": proposal.get("limitations"),
    }, sort_keys=True).lower()
    if any(marker in text for marker in SUCCESS_CLAIM_MARKERS):
        reasons.append("success_claim_prohibited")
    if strategy.get("independent_evaluator_path") in set(strategy.get("files_allowed") or ()):
        reasons.append("strategy_mutates_evaluator")
    for path in tuple(strategy.get("files_allowed") or ()) + tuple(strategy.get("tests_allowed") or ()):
        if _path_bad(str(path)):
            reasons.append("prohibited_or_broad_strategy_path")
    return {
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "problem_ids": tuple(sorted(problem_ids)),
        "stage1_evidence_keys": tuple(sorted(stage1_keys)),
        "stage2_evidence_keys": tuple(sorted(stage2_keys)),
        "proposal_evidence_keys": tuple(sorted(proposal_keys)),
    }


def validate_assembled_cognitive_proposal(
    *,
    proposal: Mapping[str, Any],
    evidence_selection: Mapping[str, Any],
    evidence_packet: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
    path_selection: Mapping[str, Any],
    strategy: Mapping[str, Any],
    allowlist: Mapping[str, Any],
    allowed_authority: Mapping[str, Any],
) -> dict[str, Any]:
    stage1 = validate_evidence_selection(evidence_selection, evidence_packet)
    enriched_stage1 = {
        **dict(evidence_selection),
        "selected_evidence": tuple(
            {
                **dict(item),
                "text": next(
                    (
                        str(source.get("excerpt") or source.get("text") or "")
                        for source in evidence_packet.get("sources", ())
                        if isinstance(source, Mapping)
                        and source.get("source_id") == item.get("source_id")
                        and source.get("excerpt_id") == item.get("excerpt_id")
                        and source.get("path") == item.get("path")
                    ),
                    str(item.get("text") or ""),
                ),
            }
            for item in evidence_selection.get("selected_evidence", ())
            if isinstance(item, Mapping)
        ),
    }
    stage2 = validate_grounded_diagnosis(diagnosis, enriched_stage1)
    stage3 = validate_path_selection(path_selection, allowlist)
    stage4 = validate_bounded_strategy(strategy, path_selection=path_selection)
    consistency = audit_cognitive_proposal_consistency(
        evidence_selection=evidence_selection,
        diagnosis=diagnosis,
        path_selection=path_selection,
        strategy=strategy,
        proposal=proposal,
    )
    grounding = validate_final_proposal(
        proposal,
        evidence_references=_evidence_keys_from_stage1(evidence_selection),
        inspected_paths=(str(path_selection.get("implementation_path") or ""),),
        evaluator_path=str(path_selection.get("independent_evaluator_path") or ""),
        allowed_authority=allowed_authority,
    )
    accepted = all(result.get("accepted") for result in (stage1, stage2, stage3, stage4, consistency, grounding))
    return {
        "accepted": accepted,
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
        "stage4": stage4,
        "cross_stage_consistency": consistency,
        "grounding_result": grounding,
        "schema": "cognitive_proposal_assembly_validation_v1",
    }


class CallBudget:
    def __init__(self, maximum: int) -> None:
        self.maximum = maximum
        self.used = 0

    def consume(self) -> bool:
        if self.used >= self.maximum:
            return False
        self.used += 1
        return True

    def to_record(self) -> dict[str, int]:
        return {"maximum": self.maximum, "used": self.used, "remaining": max(0, self.maximum - self.used)}


def build_stage1_internal_request(
    *,
    request_id: str,
    model_id: str,
    problem_id: str,
    evidence_packet: Mapping[str, Any],
    budget: Mapping[str, Any],
) -> dict[str, Any]:
    statement = evidence_packet.get("problem_statement") or evidence_packet.get("statement") or ""
    required_claims = list(evidence_packet.get("required_claims") or evidence_packet.get("required_claim_categories") or ())
    for item in evidence_packet.get("sources", ()):
        if isinstance(item, Mapping):
            for claim in item.get("required_claim_categories") or ():
                if claim not in required_claims:
                    required_claims.append(claim)
    if statement and not required_claims:
        required_claims.append(str(statement))
    return {
        "request_id": request_id,
        "model_id": model_id,
        "stage": 1,
        "budget": dict(budget),
        "problem": {
            "problem_id": problem_id,
            "statement": statement,
            "required_claims": tuple(required_claims),
        },
        "available_evidence": tuple(
            {
                "source_id": item.get("source_id"),
                "excerpt_id": item.get("excerpt_id"),
                "path": item.get("path"),
                "text": item.get("excerpt") or item.get("text") or "",
            }
            for item in evidence_packet.get("sources", ())
            if isinstance(item, Mapping)
        ),
    }


def stage1_model_messages(internal_request: Mapping[str, Any]) -> list[dict[str, str]]:
    problem = internal_request.get("problem") or {}
    evidence = tuple(internal_request.get("available_evidence") or ())
    records = json.dumps(evidence, indent=2, sort_keys=True)
    output_shape = {
        "result_type": "evidence_selection",
        "problem_id": "string",
        "selected_evidence": [{
            "source_id": "string",
            "excerpt_id": "string",
            "path": "string",
            "supported_claim": "string",
        }],
        "missing_claims": ["string"],
        "uncertainty": {"score": 0.0, "reason": "string"},
    }
    user = (
        f"Problem ID: {problem.get('problem_id')}\n\n"
        f"Task: Select the supplied evidence records that support the required claims for this problem.\n\n"
        f"Required claims:\n{json.dumps(problem.get('required_claims') or [], indent=2, sort_keys=True)}\n\n"
        f"AVAILABLE EVIDENCE:\n{records}\n\n"
        f"REQUIRED OUTPUT SHAPE:\n{json.dumps(output_shape, indent=2, sort_keys=True)}\n\n"
        "Return the artifact at the JSON root. Do not include an input wrapper. Do not include a completed answer example."
    )
    return [
        {
            "role": "system",
            "content": (
                "Return exactly one JSON object. The object must be the final artifact at the root. "
                "Do not repeat or wrap the request. Do not use Markdown. Select only supplied evidence records. "
                "Copy source_id, excerpt_id, and path exactly. Do not invent references. "
                "Return a complete typed abstention when evidence is insufficient."
            ),
        },
        {"role": "user", "content": user},
    ]


def stage1_revision_messages(
    *,
    internal_request: Mapping[str, Any],
    validation: Mapping[str, Any],
    response_keys: Sequence[str],
) -> list[dict[str, str]]:
    messages = stage1_model_messages(internal_request)
    structural = (
        "Previous response failed deterministic structure validation. "
        f"Structural errors: {json.dumps(tuple(validation.get('reasons') or ()), sort_keys=True)}. "
        f"Previous root keys: {json.dumps(tuple(response_keys), sort_keys=True)}. "
        "Return a fresh root-level evidence_selection artifact or a complete typed abstention. "
        "Do not echo AVAILABLE EVIDENCE. Do not wrap the artifact. Do not use or infer any evidence not listed."
    )
    return [messages[0], {"role": "user", "content": structural + "\n\n" + messages[1]["content"]}]


def audit_stage1_fixture_integrity(evidence_packet: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    sources = tuple(item for item in evidence_packet.get("sources", ()) if isinstance(item, Mapping))
    if not sources:
        reasons.append("no_sources")
    for item in sources:
        for field in ("source_id", "excerpt_id", "path"):
            if not item.get(field):
                reasons.append(f"missing_{field}")
        if not (item.get("excerpt") or item.get("text")):
            reasons.append("missing_visible_text")
    if any("evaluator" in str(item.get("excerpt") or item.get("text") or "").lower() for item in sources):
        reasons.append("possible_hidden_evaluator_dependency")
    return {
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "source_count": len(sources),
        "stage1_only": True,
    }


def build_stage2_internal_request(
    *,
    request_id: str,
    model_id: str,
    problem_id: str,
    problem_statement: str,
    evidence_selection: Mapping[str, Any],
    evidence_packet: Mapping[str, Any],
    budget: Mapping[str, Any],
) -> dict[str, Any]:
    source_index = _source_index(evidence_packet)
    selected = []
    for item in evidence_selection.get("selected_evidence", ()):
        if not isinstance(item, Mapping):
            continue
        key = (str(item.get("source_id")), str(item.get("excerpt_id")), str(item.get("path")))
        source = source_index.get(key, {})
        selected.append({
            "source_id": item.get("source_id"),
            "excerpt_id": item.get("excerpt_id"),
            "path": item.get("path"),
            "text": source.get("excerpt") or source.get("text") or item.get("text") or "",
            "supported_claim": item.get("supported_claim") or "",
        })
    return {
        "request_id": request_id,
        "model_id": model_id,
        "stage": 2,
        "budget": dict(budget),
        "problem": {
            "problem_id": problem_id,
            "statement": problem_statement,
            "task": "Diagnose the narrow failure boundary supported by the validated selected evidence.",
        },
        "validated_selected_evidence": tuple(selected),
    }


def stage2_model_messages(internal_request: Mapping[str, Any]) -> list[dict[str, str]]:
    problem = internal_request.get("problem") or {}
    selected = tuple(internal_request.get("validated_selected_evidence") or ())
    records = json.dumps(selected, indent=2, sort_keys=True)
    output_shape = {
        "result_type": "grounded_diagnosis",
        "problem_id": "string",
        "diagnosis": "string",
        "first_incorrect_transition": "string",
        "evidence_references": [{
            "source_id": "string",
            "excerpt_id": "string",
            "path": "string",
            "claim": "string",
        }],
        "limitations": ["string"],
        "uncertainty": {"score": 0.0, "reason": "string"},
    }
    user = (
        f"Problem ID: {problem.get('problem_id')}\n\n"
        f"Problem statement:\n{problem.get('statement') or ''}\n\n"
        f"Diagnostic task:\n{problem.get('task') or ''}\n\n"
        f"VALIDATED SELECTED EVIDENCE:\n{records}\n\n"
        f"REQUIRED ROOT OUTPUT:\n{json.dumps(output_shape, indent=2, sort_keys=True)}\n\n"
        "Return the diagnosis artifact at the JSON root. Do not include an input wrapper. "
        "Do not include implementation paths, test paths, evaluator paths, repair strategy, or a completed example."
    )
    return [
        {
            "role": "system",
            "content": (
                "Return exactly one root-level JSON object. Do not repeat or wrap the request. Do not use Markdown. "
                "Base every diagnosis claim only on validated selected evidence. Copy evidence references exactly. "
                "State the first incorrect transition narrowly. Include limitations and uncertainty. "
                "Do not propose a repair. Do not select implementation, test, or evaluator paths. "
                "Return a complete typed abstention when the validated evidence does not support diagnosis."
            ),
        },
        {"role": "user", "content": user},
    ]


def stage2_revision_messages(
    *,
    internal_request: Mapping[str, Any],
    validation: Mapping[str, Any],
    response_keys: Sequence[str],
) -> list[dict[str, str]]:
    messages = stage2_model_messages(internal_request)
    structural = (
        "Previous response failed deterministic structure validation. "
        f"Structural errors: {json.dumps(tuple(validation.get('reasons') or ()), sort_keys=True)}. "
        f"Previous root keys: {json.dumps(tuple(response_keys), sort_keys=True)}. "
        "Return a fresh root-level grounded_diagnosis artifact or a complete typed abstention. "
        "Do not wrap the artifact. Do not infer references not listed in VALIDATED SELECTED EVIDENCE."
    )
    return [messages[0], {"role": "user", "content": structural + "\n\n" + messages[1]["content"]}]


def audit_stage2_fixture_integrity(
    *,
    evidence_selection: Mapping[str, Any],
    evidence_packet: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    selected = tuple(item for item in evidence_selection.get("selected_evidence", ()) if isinstance(item, Mapping))
    source_index = _source_index(evidence_packet)
    if not selected:
        reasons.append("no_selected_evidence")
    visible_text = []
    for item in selected:
        key = (str(item.get("source_id")), str(item.get("excerpt_id")), str(item.get("path")))
        source = source_index.get(key)
        if not source:
            reasons.append("selected_source_missing")
            continue
        text = source.get("excerpt") or source.get("text")
        if not text:
            reasons.append("selected_excerpt_text_missing")
        else:
            visible_text.append(str(text))
    if not visible_text:
        reasons.append("no_visible_selected_text")
    if any("evaluator" in text.lower() for text in visible_text):
        reasons.append("possible_hidden_evaluator_dependency")
    return {
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "selected_count": len(selected),
        "visible_selected_text_count": len(visible_text),
        "stage2_only": True,
    }


def _candidate_records(paths: Sequence[str], *, candidate_type: str, inspected: bool = False, proposed_new_test: bool = False, independent: bool = True, relationship: str = "") -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "candidate_id": f"{candidate_type}-{index}",
            "path": str(path),
            "candidate_type": candidate_type,
            "exists": _file_exists(str(path)),
            "inspected": inspected,
            "permitted": True,
            "proposed_new_test": proposed_new_test,
            "independent": independent,
            "relationship": relationship,
        }
        for index, path in enumerate(paths, start=1)
    )


def build_stage3_internal_request(
    *,
    request_id: str,
    model_id: str,
    problem_id: str,
    problem_statement: str,
    diagnosis: Mapping[str, Any],
    allowlist: Mapping[str, Any],
    budget: Mapping[str, Any],
    implementation_candidates: Sequence[Mapping[str, Any]] | None = None,
    focused_test_candidates: Sequence[Mapping[str, Any]] | None = None,
    evaluator_candidates: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    implementation = tuple(implementation_candidates or _candidate_records(
        tuple(str(path) for path in allowlist.get("inspected_implementation_paths", ())),
        candidate_type="implementation",
        inspected=True,
        relationship="candidate implementation path from inspected allowlist",
    ))
    focused_tests = tuple(focused_test_candidates or (
        *_candidate_records(
            tuple(str(path) for path in allowlist.get("focused_test_paths", ())),
            candidate_type="focused_test",
            relationship="candidate focused test path from allowlist",
        ),
        *_candidate_records(
            tuple(str(path) for path in allowlist.get("permitted_new_test_paths", ())),
            candidate_type="focused_test",
            proposed_new_test=True,
            relationship="explicitly permitted proposed focused test path",
        ),
    ))
    evaluators = tuple(evaluator_candidates or _candidate_records(
        tuple(str(path) for path in allowlist.get("independent_evaluator_paths", ())),
        candidate_type="evaluator",
        independent=True,
        relationship="candidate independent evaluator path from allowlist",
    ))
    return {
        "request_id": request_id,
        "model_id": model_id,
        "stage": 3,
        "budget": dict(budget),
        "problem": {
            "problem_id": problem_id,
            "statement": problem_statement,
            "task": "Select exact allowlisted paths for the diagnosed bounded repair boundary.",
        },
        "validated_grounded_diagnosis": {
            "diagnosis": diagnosis.get("diagnosis"),
            "first_incorrect_transition": diagnosis.get("first_incorrect_transition"),
            "evidence_references": tuple(diagnosis.get("evidence_references") or ()),
            "limitations": tuple(diagnosis.get("limitations") or ()),
            "uncertainty": diagnosis.get("uncertainty") or {},
        },
        "implementation_candidates": implementation,
        "focused_test_candidates": focused_tests,
        "evaluator_candidates": evaluators,
    }


def stage3_model_messages(internal_request: Mapping[str, Any]) -> list[dict[str, str]]:
    problem = internal_request.get("problem") or {}
    diagnosis = internal_request.get("validated_grounded_diagnosis") or {}
    output_shape = {
        "result_type": "path_selection",
        "problem_id": "string",
        "implementation_path": "exact supplied path",
        "focused_test_path": "exact supplied or explicitly proposed path",
        "independent_evaluator_path": "exact supplied path",
        "selection_reasons": {"implementation": "string", "test": "string", "evaluator": "string"},
        "rejected_candidates": [{"path": "exact supplied path", "reason": "string"}],
        "limitations": ["string"],
        "uncertainty": {"score": 0.0, "reason": "string"},
    }
    user = (
        f"Problem ID: {problem.get('problem_id')}\n\n"
        f"Problem statement:\n{problem.get('statement') or ''}\n\n"
        f"Validated grounded diagnosis:\n{json.dumps(diagnosis, indent=2, sort_keys=True)}\n\n"
        f"IMPLEMENTATION CANDIDATES:\n{json.dumps(tuple(internal_request.get('implementation_candidates') or ()), indent=2, sort_keys=True)}\n\n"
        f"FOCUSED-TEST CANDIDATES:\n{json.dumps(tuple(internal_request.get('focused_test_candidates') or ()), indent=2, sort_keys=True)}\n\n"
        f"EVALUATOR CANDIDATES:\n{json.dumps(tuple(internal_request.get('evaluator_candidates') or ()), indent=2, sort_keys=True)}\n\n"
        f"REQUIRED ROOT OUTPUT:\n{json.dumps(output_shape, indent=2, sort_keys=True)}\n\n"
        "Return the path selection artifact at the JSON root. Do not include an input wrapper. "
        "Do not include implementation steps, success claims, authority requests, or a completed example."
    )
    return [
        {
            "role": "system",
            "content": (
                "Return exactly one root-level JSON object. Do not repeat or wrap the request. Do not use Markdown. "
                "Select only exact paths from supplied allowlists. Copy paths exactly. Do not invent a path. "
                "Select one inspected implementation path. Select one focused-test path or explicitly permitted proposed test path. "
                "Select one independent evaluator path. Explain each selection briefly. Do not propose implementation steps. "
                "Do not claim success. Return a complete typed abstention when no valid combination is supportable."
            ),
        },
        {"role": "user", "content": user},
    ]


def stage3_revision_messages(
    *,
    internal_request: Mapping[str, Any],
    validation: Mapping[str, Any],
    response_keys: Sequence[str],
) -> list[dict[str, str]]:
    messages = stage3_model_messages(internal_request)
    structural = (
        "Previous response failed deterministic structure or allowlist validation. "
        f"Structural errors: {json.dumps(tuple(validation.get('reasons') or ()), sort_keys=True)}. "
        f"Previous root keys: {json.dumps(tuple(response_keys), sort_keys=True)}. "
        "Return a fresh root-level path_selection artifact or a complete typed abstention. "
        "Do not wrap the artifact. Do not invent paths. Use only exact paths listed in the candidate sections."
    )
    return [messages[0], {"role": "user", "content": structural + "\n\n" + messages[1]["content"]}]


def audit_stage3_allowlist_integrity(allowlist: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    implementations = tuple(str(path) for path in allowlist.get("inspected_implementation_paths", ()))
    focused_tests = tuple(str(path) for path in allowlist.get("focused_test_paths", ()))
    proposed_tests = tuple(str(path) for path in allowlist.get("permitted_new_test_paths", ()))
    evaluators = tuple(str(path) for path in allowlist.get("independent_evaluator_paths", ()))
    if not implementations:
        reasons.append("no_inspected_implementation_candidates")
    if not focused_tests and not proposed_tests:
        reasons.append("no_focused_test_candidates")
    if not evaluators:
        reasons.append("no_independent_evaluator_candidates")
    for path in implementations:
        if _path_bad(path):
            reasons.append("invalid_implementation_path")
        if not _file_exists(path):
            reasons.append("implementation_path_missing")
    for path in focused_tests:
        if _path_bad(path):
            reasons.append("invalid_focused_test_path")
        if not _file_exists(path):
            reasons.append("focused_test_path_missing")
    for path in proposed_tests:
        if _path_bad(path):
            reasons.append("invalid_proposed_test_path")
    for path in evaluators:
        if _path_bad(path):
            reasons.append("invalid_evaluator_path")
        if not _file_exists(path):
            reasons.append("evaluator_path_missing")
    if any(path in implementations for path in evaluators):
        reasons.append("implementation_evaluator_conflict")
    return {
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "implementation_count": len(implementations),
        "focused_test_count": len(focused_tests),
        "permitted_new_test_count": len(proposed_tests),
        "evaluator_count": len(evaluators),
        "stage3_only": True,
    }


def build_stage4_internal_request(
    *,
    request_id: str,
    model_id: str,
    problem_id: str,
    problem_statement: str,
    diagnosis: Mapping[str, Any],
    path_selection: Mapping[str, Any],
    authority: Mapping[str, Any],
    prohibited_changes: Sequence[str],
    budget: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "model_id": model_id,
        "stage": 4,
        "budget": dict(budget),
        "problem": {
            "problem_id": problem_id,
            "statement": problem_statement,
            "task": "Produce a bounded non-executed repair strategy constrained to the selected paths.",
        },
        "validated_grounded_diagnosis": {
            "diagnosis": diagnosis.get("diagnosis"),
            "first_incorrect_transition": diagnosis.get("first_incorrect_transition"),
            "evidence_references": tuple(diagnosis.get("evidence_references") or ()),
            "limitations": tuple(diagnosis.get("limitations") or ()),
            "uncertainty": diagnosis.get("uncertainty") or {},
        },
        "validated_path_selection": {
            "implementation_path": path_selection.get("implementation_path"),
            "focused_test_path": path_selection.get("focused_test_path"),
            "independent_evaluator_path": path_selection.get("independent_evaluator_path"),
            "selection_reasons": path_selection.get("selection_reasons") or {},
            "limitations": tuple(path_selection.get("limitations") or ()),
            "uncertainty": path_selection.get("uncertainty") or {},
        },
        "allowed_changes": {
            "files_allowed": (path_selection.get("implementation_path"),),
            "tests_allowed": (path_selection.get("focused_test_path"),),
            "independent_evaluator_path": path_selection.get("independent_evaluator_path"),
            "required_authority": tuple(authority.get("required_authority") or ("bounded_local_sandbox",)),
            "prohibited_authority": tuple(authority.get("prohibited_authority") or sorted(PROHIBITED_STRATEGY_AUTHORITY)),
        },
        "prohibited_changes": tuple(prohibited_changes),
    }


def stage4_model_messages(internal_request: Mapping[str, Any]) -> list[dict[str, str]]:
    problem = internal_request.get("problem") or {}
    diagnosis = internal_request.get("validated_grounded_diagnosis") or {}
    paths = internal_request.get("validated_path_selection") or {}
    allowed = internal_request.get("allowed_changes") or {}
    output_shape = {
        "result_type": "bounded_strategy",
        "problem_id": "string",
        "steps": [{"order": 1, "action": "string", "target_path": "exact selected path", "purpose": "string"}],
        "files_allowed": ["exact selected implementation path"],
        "tests_allowed": ["exact selected focused-test path"],
        "independent_evaluator_path": "exact selected evaluator path",
        "expected_behavioral_change": "string",
        "prohibited_changes": ["string"],
        "limitations": ["string"],
        "uncertainty": {"score": 0.0, "reason": "string"},
        "required_authority": ["bounded_local_sandbox"],
        "prohibited_authority": ["provider", "network", "deployment", "credentials", "primary_source_mutation", "source_mutation", "evaluator_mutation", "unrestricted_shell", "unrestricted_execution"],
    }
    user = (
        f"Problem ID: {problem.get('problem_id')}\n\n"
        f"Problem statement:\n{problem.get('statement') or ''}\n\n"
        f"Validated diagnosis:\n{json.dumps(diagnosis, indent=2, sort_keys=True)}\n\n"
        f"Selected implementation path:\n{paths.get('implementation_path')}\n\n"
        f"Selected focused-test path:\n{paths.get('focused_test_path')}\n\n"
        f"Selected independent evaluator path:\n{paths.get('independent_evaluator_path')}\n\n"
        f"Allowed changes:\n{json.dumps(allowed, indent=2, sort_keys=True)}\n\n"
        f"Prohibited changes:\n{json.dumps(tuple(internal_request.get('prohibited_changes') or ()), indent=2, sort_keys=True)}\n\n"
        f"REQUIRED ROOT OUTPUT:\n{json.dumps(output_shape, indent=2, sort_keys=True)}\n\n"
        "Return the bounded strategy artifact at the JSON root. Do not include an input wrapper. "
        "Do not include source code, a patch, a diff, success claims, test-pass claims, final proposal fields, or a completed example."
    )
    return [
        {
            "role": "system",
            "content": (
                "Return exactly one root-level JSON object. Do not repeat or wrap the request. Do not use Markdown. "
                "Use only the selected implementation and test paths. Do not modify the independent evaluator. "
                "Do not introduce additional files. Do not claim success. Do not claim tests passed. "
                "Do not request provider, network, deployment, credential, primary-source, evaluator-mutation, or unrestricted authority. "
                "Produce a bounded ordered strategy only. Include limitations and uncertainty. "
                "Return a complete typed abstention when no safe bounded strategy is supportable."
            ),
        },
        {"role": "user", "content": user},
    ]


def stage4_revision_messages(
    *,
    internal_request: Mapping[str, Any],
    validation: Mapping[str, Any],
    response_keys: Sequence[str],
) -> list[dict[str, str]]:
    messages = stage4_model_messages(internal_request)
    structural = (
        "Previous response failed deterministic structure or bounded-strategy validation. "
        f"Structural errors: {json.dumps(tuple(validation.get('reasons') or ()), sort_keys=True)}. "
        f"Previous root keys: {json.dumps(tuple(response_keys), sort_keys=True)}. "
        "Return a fresh root-level bounded_strategy artifact or a complete typed abstention. "
        "Do not wrap the artifact. Do not add paths. Do not claim success. Do not mutate the evaluator."
    )
    return [messages[0], {"role": "user", "content": structural + "\n\n" + messages[1]["content"]}]


def audit_stage4_fixture_integrity(
    *,
    diagnosis: Mapping[str, Any],
    path_selection: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    implementation = str(path_selection.get("implementation_path") or "")
    test = str(path_selection.get("focused_test_path") or "")
    evaluator = str(path_selection.get("independent_evaluator_path") or "")
    if not _nonempty(diagnosis.get("diagnosis")):
        reasons.append("diagnosis_missing")
    if not _nonempty(diagnosis.get("first_incorrect_transition")):
        reasons.append("transition_missing")
    for field, path in (("implementation", implementation), ("test", test), ("evaluator", evaluator)):
        if not path:
            reasons.append(f"{field}_path_missing")
        elif _path_bad(path):
            reasons.append(f"{field}_path_invalid")
        elif not _file_exists(path):
            reasons.append(f"{field}_path_not_found")
    if evaluator == implementation:
        reasons.append("evaluator_conflicts_with_implementation")
    return {
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "stage4_only": True,
    }
