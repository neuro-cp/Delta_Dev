"""Shared governed-development primitives for AUTONOMY phases."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


PRIMITIVE_SCHEMA = "autonomy_governed_primitives_v1"
KERNEL_PRIMITIVES = (
    "Artifact",
    "EvidencePacket",
    "CognitiveProposal",
    "GroundingResult",
    "Goal",
    "Plan",
    "Evaluator",
    "Authority",
    "WorkItem",
    "Transition",
    "Execution",
    "Review",
    "Competence",
    "OperatorRequest",
)
DETERMINISTIC_RESPONSIBILITIES = (
    "authority_and_permissions",
    "state_transitions",
    "digests_and_provenance",
    "budgets_and_expiration",
    "locking_and_journals",
    "schema_validation",
    "evaluator_isolation",
    "filesystem_boundaries",
    "competence_lifecycle",
    "final_action_authorization",
)
COGNITIVE_RESPONSIBILITIES = (
    "goal_interpretation",
    "mission_decomposition",
    "task_requirement_hypotheses",
    "candidate_composition_suggestions",
    "implementation_path_hypotheses",
    "contradiction_interpretation",
    "evaluator_design_proposals",
    "strategy_revision_proposals",
    "semantic_evidence_ranking",
    "narrow_capability_statement_drafts",
)


def digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def governance_kernel_contract(*, phase: str) -> dict[str, Any]:
    return digest_record({
        "schema": "autonomy_governance_kernel_contract_v1",
        "phase": phase,
        "primitive_schema": PRIMITIVE_SCHEMA,
        "kernel_primitives": KERNEL_PRIMITIVES,
        "deterministic_responsibilities": DETERMINISTIC_RESPONSIBILITIES,
        "cognitive_responsibilities": COGNITIVE_RESPONSIBILITIES,
        "architecture_rule": "models_propose_and_interpret_code_constrains_executes_records_and_verifies",
        "bespoke_module_risk": "new capability families should be data specifications over these primitives where possible",
        "created_at": FIXED_TIMESTAMP,
    })


def capability_family_spec(
    family: str,
    *,
    input_schema: str,
    output_schema: str,
    evaluator_builder: str,
    strategy_interface: str,
    authority_requirements: Mapping[str, Any],
    failure_states: Sequence[str],
    revision_policy: str,
) -> dict[str, Any]:
    return digest_record({
        "schema": "autonomy_capability_family_spec_v1",
        "family": family,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "eligible_competence": family,
        "evaluator_builder": evaluator_builder,
        "strategy_interface": strategy_interface,
        "authority_requirements": dict(authority_requirements),
        "failure_states": tuple(failure_states),
        "revision_policy": revision_policy,
        "runtime_primitives": KERNEL_PRIMITIVES,
        "created_at": FIXED_TIMESTAMP,
    })


def cognitive_proposal_contract(
    proposal: Mapping[str, Any],
    *,
    allowed_origin_modes: Sequence[str],
    required_fields: Sequence[str],
) -> dict[str, Any]:
    missing = [field for field in required_fields if not proposal.get(field)]
    origin = str(proposal.get("proposal_origin") or proposal.get("advisory_mode") or "")
    reasons: list[str] = []
    if origin not in set(allowed_origin_modes):
        reasons.append("unsupported_proposal_origin")
    if missing:
        reasons.append("missing_required_cognitive_fields")
    if proposal.get("deterministic_runtime_validated") is False:
        reasons.append("not_validated_by_deterministic_runtime")
    if proposal.get("model_output_authoritative") is True:
        reasons.append("model_output_authority_rejected")
    return digest_record({
        "schema": "autonomy_cognitive_proposal_contract_v1",
        "proposal_id": proposal.get("advisory_output_id") or stable_id("autonomy-cognitive-proposal", bootstrap_digest(proposal)),
        "proposal_origin": origin,
        "accepted": not reasons,
        "reasons": tuple(reasons),
        "required_fields": tuple(required_fields),
        "missing_fields": tuple(missing),
        "allowed_origin_modes": tuple(allowed_origin_modes),
        "deterministic_runtime_remains_authoritative": True,
        "created_at": FIXED_TIMESTAMP,
    })


def _proposal_value(proposal: Mapping[str, Any], canonical: str, *aliases: str) -> Any:
    for key in (canonical, *aliases):
        value = proposal.get(key)
        if value not in (None, "", (), []):
            return value
    return None


def _evidence_reference_keys(value: Any) -> tuple[str, ...]:
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
            keys.extend(_evidence_reference_keys(item))
        return tuple(keys)
    return ()


def _evidence_reference_paths(value: Any) -> tuple[str, ...]:
    if isinstance(value, Mapping) and value.get("path"):
        return (str(value["path"]),)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        paths: list[str] = []
        for item in value:
            paths.extend(_evidence_reference_paths(item))
        return tuple(paths)
    return ()


def _prohibited_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return "delta-75" in normalized or "reports/rc4_" in normalized or normalized.endswith("/.env") or normalized == ".env"


def grounding_result(
    proposal: Mapping[str, Any],
    *,
    evidence_references: Sequence[str],
    inspected_paths: Sequence[str],
    evaluator_path: str,
    allowed_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a typed model proposal without treating the model as authority."""

    reasons: list[str] = []
    required = (
        "diagnosis",
        "first_incorrect_transition",
        "implementation_path",
        "focused_test_path",
        "independent_evaluator_path",
        "bounded_strategy",
        "limitations",
        "uncertainty",
        "evidence_references",
    )
    normalized_proposal = {
        **dict(proposal),
        "implementation_path": _proposal_value(proposal, "implementation_path", "inspected_implementation_path"),
        "focused_test_path": _proposal_value(proposal, "focused_test_path", "proposed_focused_test_path"),
        "independent_evaluator_path": _proposal_value(proposal, "independent_evaluator_path"),
    }
    contract = cognitive_proposal_contract(
        normalized_proposal,
        allowed_origin_modes=("local_model",),
        required_fields=required,
    )
    if not contract["accepted"]:
        reasons.extend(str(reason) for reason in contract["reasons"])
    implementation_path = str(_proposal_value(proposal, "inspected_implementation_path", "implementation_path") or "")
    focused_test_path = str(_proposal_value(proposal, "proposed_focused_test_path", "focused_test_path") or "")
    evaluator = str(_proposal_value(proposal, "independent_evaluator_path") or "")
    if _prohibited_path(implementation_path) or _prohibited_path(focused_test_path) or _prohibited_path(evaluator):
        reasons.append("prohibited_path_rejected")
    if implementation_path not in set(inspected_paths):
        reasons.append("uninspected_implementation_path")
    if evaluator != evaluator_path:
        reasons.append("independent_evaluator_path_mismatch")
    cited = set(_evidence_reference_keys(proposal.get("evidence_references") or ()))
    if not cited or not cited.issubset(set(str(item) for item in evidence_references)):
        reasons.append("ungrounded_evidence_reference")
    cited_paths = set(_evidence_reference_paths(proposal.get("evidence_references") or ()))
    if cited_paths and not cited_paths.issubset(set(inspected_paths)):
        reasons.append("evidence_path_not_inspected")
    if not focused_test_path:
        reasons.append("missing_focused_test_path")
    for key in ("provider_calls", "network", "deployment", "credentials", "source_mutation"):
        if proposal.get(key) not in (None, False, 0) and not allowed_authority.get(key):
            reasons.append(f"authority_expansion_{key}")
    for authority in tuple(proposal.get("required_authority") or ()):
        normalized = str(authority).strip().lower()
        if normalized in {"provider", "network", "deployment", "credentials", "primary_source_mutation", "source_mutation"}:
            reasons.append(f"authority_expansion_{normalized}")
    if proposal.get("model_output_authoritative") is True:
        reasons.append("model_output_authority_rejected")
    return digest_record({
        "schema": "autonomy_grounding_result_v1",
        "proposal_id": proposal.get("proposal_id") or proposal.get("advisory_output_id") or stable_id("cognitive-proposal", bootstrap_digest(proposal)),
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "cognitive_proposal_contract": contract,
        "evidence_references": tuple(evidence_references),
        "inspected_paths": tuple(inspected_paths),
        "evaluator_path": evaluator_path,
        "allowed_authority": dict(allowed_authority),
        "deterministic_runtime_remains_authoritative": True,
        "created_at": FIXED_TIMESTAMP,
    })
