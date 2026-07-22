"""Inert contracts for governed developmental bootstrap curriculum.

BOOTSTRAP-A owns schema and provenance boundaries only.  It does not install a
curriculum, retrieve evidence, execute learners or evaluators, promote
capabilities, or admit trusted memory.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence
import uuid

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


BOOTSTRAP_MODULE_SCHEMA = "governed_bootstrap_module_v1"
BOOTSTRAP_RELATIONSHIP_SCHEMA = "governed_bootstrap_relationship_v1"
BOOTSTRAP_CURRICULUM_SCHEMA = "governed_bootstrap_curriculum_manifest_v1"
BOOTSTRAP_VALIDATION_SCHEMA = "governed_bootstrap_validation_record_v1"
BOOTSTRAP_COMPETENCE_SCHEMA = "validated_bootstrap_competence_v1"
BOOTSTRAP_INSTALLATION_REQUEST_SCHEMA = "governed_bootstrap_installation_request_v1"

BOOTSTRAP_MODULE_DIRECTORY = "bootstrap_modules"
BOOTSTRAP_RELATIONSHIP_DIRECTORY = "bootstrap_relationships"
BOOTSTRAP_CURRICULUM_DIRECTORY = "bootstrap_curricula"
BOOTSTRAP_VALIDATION_DIRECTORY = "bootstrap_validation_records"
BOOTSTRAP_COMPETENCE_DIRECTORY = "validated_bootstrap_competencies"
BOOTSTRAP_TEMP_DIRECTORY = ".bootstrap_install_tmp"

BOOTSTRAP_ORIGINS = frozenset({
    "operator_installed_bootstrap",
    "autonomously_learned_competence",
})
BOOTSTRAP_STATES = frozenset({
    "operator_installed_bootstrap",
    "bootstrap_available_for_study",
    "validated_bootstrap_competence",
    "autonomously_learned_competence",
    "trusted_capability",
})
RELATIONSHIP_TYPES = frozenset({
    "requires",
    "enables",
    "relates_to",
    "contrasts_with",
    "example_of",
    "counterexample_of",
    "verified_by",
    "revises",
    "prerequisite_for",
    "transfers_to",
})
VALIDATION_OUTCOMES = frozenset({
    "bootstrap_validation_passed",
    "bootstrap_validation_incomplete",
    "bootstrap_validation_failed",
    "bootstrap_validation_integrity_stop",
})


class BootstrapContractError(ValueError):
    """Raised when a bootstrap contract would blur governance boundaries."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def bootstrap_digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _without_digest(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in dict(record).items() if key not in {"artifact_digest", "created_at"}}


def _require_fields(record: Mapping[str, Any], fields: Sequence[str]) -> None:
    missing = tuple(field for field in fields if field not in record)
    if missing:
        raise BootstrapContractError(f"bootstrap_required_field_missing:{','.join(missing)}")


def _as_tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    raise BootstrapContractError("bootstrap_collection_field_invalid")


def _reject_evaluator_hidden(record: Mapping[str, Any]) -> None:
    hidden = {"answer_key", "scoring_rule", "pass_threshold", "rubric", "evaluator_view", "evaluator_hidden"}
    present = tuple(sorted(hidden & set(record.keys())))
    if present:
        raise BootstrapContractError(f"bootstrap_evaluator_hidden_field_rejected:{','.join(present)}")


def make_bootstrap_module(
    *,
    title: str,
    domain: str,
    definition: str,
    version: int = 1,
    authored_by: str = "codex",
    prerequisites: Sequence[str] = (),
    enables: Sequence[str] = (),
    related_modules: Sequence[str] = (),
    contrasts_with: Sequence[str] = (),
    key_components: Sequence[str] = (),
    procedure: Sequence[str] = (),
    worked_examples: Sequence[Mapping[str, Any]] = (),
    counterexamples: Sequence[Mapping[str, Any]] = (),
    failure_modes: Sequence[str] = (),
    verification_methods: Sequence[str] = (),
    scope_limits: Sequence[str] = (),
    source_bindings: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if version < 1:
        raise BootstrapContractError("bootstrap_version_invalid")
    module_id = stable_id("governed-bootstrap-module", domain, title, version)
    record = {
        "schema": BOOTSTRAP_MODULE_SCHEMA,
        "module_id": module_id,
        "version": version,
        "title": title,
        "domain": domain,
        "origin": "operator_installed_bootstrap",
        "authored_by": authored_by,
        "state": "operator_installed_bootstrap",
        "learned_by_delta": False,
        "behaviorally_validated": False,
        "trusted_admission": False,
        "capability_promotion": False,
        "prerequisites": tuple(prerequisites),
        "enables": tuple(enables),
        "related_modules": tuple(related_modules),
        "contrasts_with": tuple(contrasts_with),
        "definition": definition,
        "key_components": tuple(key_components),
        "procedure": tuple(procedure),
        "worked_examples": tuple(dict(item) for item in worked_examples),
        "counterexamples": tuple(dict(item) for item in counterexamples),
        "failure_modes": tuple(failure_modes),
        "verification_methods": tuple(verification_methods),
        "scope_limits": tuple(scope_limits),
        "source_bindings": tuple(dict(item) for item in source_bindings),
        "created_at": utc_now(),
    }
    return validate_bootstrap_module(record)


def validate_bootstrap_module(record: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(record, (
        "schema", "module_id", "version", "title", "domain", "origin", "authored_by",
        "state", "learned_by_delta", "behaviorally_validated", "trusted_admission",
        "capability_promotion", "definition", "prerequisites", "enables",
        "source_bindings",
    ))
    _reject_evaluator_hidden(record)
    normalized = dict(record)
    if normalized["schema"] != BOOTSTRAP_MODULE_SCHEMA:
        raise BootstrapContractError("bootstrap_module_schema_invalid")
    if not str(normalized.get("title") or "").strip() or not str(normalized.get("domain") or "").strip():
        raise BootstrapContractError("bootstrap_module_title_or_domain_missing")
    if normalized["origin"] != "operator_installed_bootstrap":
        raise BootstrapContractError("bootstrap_module_origin_must_be_operator_installed")
    if normalized["state"] not in {"operator_installed_bootstrap", "bootstrap_available_for_study"}:
        raise BootstrapContractError("bootstrap_module_state_invalid")
    if bool(normalized["learned_by_delta"]) or bool(normalized["trusted_admission"]) or bool(normalized["capability_promotion"]):
        raise BootstrapContractError("bootstrap_module_governance_boundary_invalid")
    if bool(normalized["behaviorally_validated"]):
        raise BootstrapContractError("bootstrap_module_initial_validation_must_be_false")
    if int(normalized["version"]) < 1:
        raise BootstrapContractError("bootstrap_module_version_invalid")
    for field in ("prerequisites", "enables", "related_modules", "contrasts_with", "key_components", "procedure", "failure_modes", "verification_methods", "scope_limits"):
        normalized[field] = _as_tuple(normalized.get(field))
    normalized["worked_examples"] = tuple(dict(item) for item in _as_tuple(normalized.get("worked_examples")))
    normalized["counterexamples"] = tuple(dict(item) for item in _as_tuple(normalized.get("counterexamples")))
    normalized["source_bindings"] = tuple(dict(item) for item in _as_tuple(normalized.get("source_bindings")))
    for source_binding in normalized["source_bindings"]:
        if not source_binding.get("source_id") or not source_binding.get("artifact_digest"):
            raise BootstrapContractError("bootstrap_module_source_binding_invalid")
    expected_id = stable_id("governed-bootstrap-module", normalized["domain"], normalized["title"], int(normalized["version"]))
    if str(normalized["module_id"]) != expected_id:
        raise BootstrapContractError("bootstrap_module_id_drift")
    expected_digest = bootstrap_digest(_without_digest(normalized))
    existing_digest = str(normalized.get("artifact_digest") or expected_digest)
    if existing_digest != expected_digest:
        raise BootstrapContractError("bootstrap_module_digest_drift")
    normalized["artifact_digest"] = expected_digest
    return normalized


def make_bootstrap_relationship(*, source_module_id: str, target_module_id: str, relationship_type: str, version: int = 1, rationale: str = "") -> dict[str, Any]:
    record = {
        "schema": BOOTSTRAP_RELATIONSHIP_SCHEMA,
        "relationship_id": stable_id("governed-bootstrap-relationship", source_module_id, relationship_type, target_module_id, version),
        "version": version,
        "source_module_id": source_module_id,
        "target_module_id": target_module_id,
        "relationship_type": relationship_type,
        "rationale": rationale,
        "origin": "operator_installed_bootstrap",
        "learned_by_delta": False,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": utc_now(),
    }
    return validate_bootstrap_relationship(record, known_module_ids={source_module_id, target_module_id})


def validate_bootstrap_relationship(record: Mapping[str, Any], *, known_module_ids: set[str] | frozenset[str]) -> dict[str, Any]:
    _require_fields(record, ("schema", "relationship_id", "version", "source_module_id", "target_module_id", "relationship_type", "origin"))
    normalized = dict(record)
    if normalized["schema"] != BOOTSTRAP_RELATIONSHIP_SCHEMA:
        raise BootstrapContractError("bootstrap_relationship_schema_invalid")
    if normalized["relationship_type"] not in RELATIONSHIP_TYPES:
        raise BootstrapContractError("bootstrap_relationship_type_invalid")
    if normalized["source_module_id"] not in known_module_ids or normalized["target_module_id"] not in known_module_ids:
        raise BootstrapContractError("bootstrap_relationship_module_missing")
    if normalized["source_module_id"] == normalized["target_module_id"] and normalized["relationship_type"] == "requires":
        raise BootstrapContractError("bootstrap_relationship_self_requirement_invalid")
    if bool(normalized.get("learned_by_delta")) or bool(normalized.get("trusted_admission")) or bool(normalized.get("capability_promotion")):
        raise BootstrapContractError("bootstrap_relationship_governance_boundary_invalid")
    expected_id = stable_id("governed-bootstrap-relationship", normalized["source_module_id"], normalized["relationship_type"], normalized["target_module_id"], int(normalized["version"]))
    if str(normalized["relationship_id"]) != expected_id:
        raise BootstrapContractError("bootstrap_relationship_id_drift")
    expected_digest = bootstrap_digest(_without_digest(normalized))
    existing_digest = str(normalized.get("artifact_digest") or expected_digest)
    if existing_digest != expected_digest:
        raise BootstrapContractError("bootstrap_relationship_digest_drift")
    normalized["artifact_digest"] = expected_digest
    return normalized


def make_bootstrap_manifest(*, title: str, version: int, modules: Sequence[Mapping[str, Any]], relationships: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    modules = tuple(sorted((dict(module) for module in modules), key=lambda item: str(item["module_id"])))
    relationships = tuple(sorted((dict(relationship) for relationship in relationships), key=lambda item: str(item["relationship_id"])))
    module_ids = tuple(str(module["module_id"]) for module in modules)
    relationship_ids = tuple(str(relationship["relationship_id"]) for relationship in relationships)
    domains = tuple(sorted({str(module["domain"]) for module in modules}))
    required = {str(rel["source_module_id"]) for rel in relationships if rel["relationship_type"] == "requires"}
    targets = {str(rel["target_module_id"]) for rel in relationships if rel["relationship_type"] == "requires"}
    record = {
        "schema": BOOTSTRAP_CURRICULUM_SCHEMA,
        "curriculum_id": stable_id("governed-bootstrap-curriculum", title, version, module_ids, relationship_ids),
        "version": version,
        "title": title,
        "origin": "operator_installed_bootstrap",
        "authored_by": "codex",
        "bootstrap_installed": True,
        "bootstrap_validated": False,
        "module_ids": module_ids,
        "module_digests": tuple((module["module_id"], module["artifact_digest"]) for module in modules),
        "relationship_ids": relationship_ids,
        "relationship_digests": tuple((relationship["relationship_id"], relationship["artifact_digest"]) for relationship in relationships),
        "domains": domains,
        "module_count": len(module_ids),
        "relationship_count": len(relationship_ids),
        "prerequisite_roots": tuple(sorted(set(module_ids) - required)),
        "leaf_capabilities": tuple(sorted(set(module_ids) - targets)),
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "validated_module_count": 0,
        "autonomously_learned_module_count": 0,
        "trusted_capability_count": 0,
        "completion_marker": "bootstrap_curriculum_installation_complete",
        "created_at": utc_now(),
    }
    return validate_bootstrap_manifest(record, modules=modules, relationships=relationships)


def validate_bootstrap_manifest(record: Mapping[str, Any], *, modules: Sequence[Mapping[str, Any]], relationships: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _require_fields(record, ("schema", "curriculum_id", "version", "module_ids", "relationship_ids", "bootstrap_installed", "bootstrap_validated"))
    normalized = dict(record)
    modules = tuple(sorted((dict(module) for module in modules), key=lambda item: str(item["module_id"])))
    relationships = tuple(sorted((dict(relationship) for relationship in relationships), key=lambda item: str(item["relationship_id"])))
    module_ids = tuple(str(module["module_id"]) for module in modules)
    relationship_ids = tuple(str(relationship["relationship_id"]) for relationship in relationships)
    if normalized["schema"] != BOOTSTRAP_CURRICULUM_SCHEMA:
        raise BootstrapContractError("bootstrap_manifest_schema_invalid")
    if tuple(normalized["module_ids"]) != module_ids or tuple(normalized["relationship_ids"]) != relationship_ids:
        raise BootstrapContractError("bootstrap_manifest_membership_mismatch")
    if tuple(tuple(item) for item in normalized.get("module_digests") or ()) != tuple((module["module_id"], module["artifact_digest"]) for module in modules):
        raise BootstrapContractError("bootstrap_manifest_module_digest_mismatch")
    if tuple(tuple(item) for item in normalized.get("relationship_digests") or ()) != tuple((relationship["relationship_id"], relationship["artifact_digest"]) for relationship in relationships):
        raise BootstrapContractError("bootstrap_manifest_relationship_digest_mismatch")
    if bool(normalized["bootstrap_validated"]):
        raise BootstrapContractError("bootstrap_manifest_validation_must_start_false")
    if int(normalized.get("trusted_admissions") or 0) or int(normalized.get("capability_promotions") or 0):
        raise BootstrapContractError("bootstrap_manifest_governance_boundary_invalid")
    if (
        int(normalized.get("validated_module_count") or 0)
        or int(normalized.get("autonomously_learned_module_count") or 0)
        or int(normalized.get("trusted_capability_count") or 0)
    ):
        raise BootstrapContractError("bootstrap_manifest_counts_must_start_zero")
    known = set(module_ids)
    for relationship in relationships:
        validate_bootstrap_relationship(relationship, known_module_ids=known)
    expected_id = stable_id("governed-bootstrap-curriculum", normalized["title"], int(normalized["version"]), module_ids, relationship_ids)
    if str(normalized["curriculum_id"]) != expected_id:
        raise BootstrapContractError("bootstrap_manifest_id_drift")
    expected_digest = bootstrap_digest(_without_digest(normalized))
    existing_digest = str(normalized.get("artifact_digest") or expected_digest)
    if existing_digest != expected_digest:
        raise BootstrapContractError("bootstrap_manifest_digest_drift")
    normalized["artifact_digest"] = expected_digest
    return normalized


def make_bootstrap_validation_record(*, module_id: str, module_digest: str, outcome: str, evaluator_package_digest: str, evaluation_digest: str, version: int = 1) -> dict[str, Any]:
    record = {
        "schema": BOOTSTRAP_VALIDATION_SCHEMA,
        "validation_id": stable_id("governed-bootstrap-validation", module_id, module_digest, evaluator_package_digest, evaluation_digest, version),
        "version": version,
        "module_id": module_id,
        "module_digest": module_digest,
        "outcome": outcome,
        "evaluator_package_digest": evaluator_package_digest,
        "evaluation_digest": evaluation_digest,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": utc_now(),
    }
    return validate_bootstrap_validation_record(record)


def validate_bootstrap_validation_record(record: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(record, ("schema", "validation_id", "version", "module_id", "module_digest", "outcome", "evaluator_package_digest", "evaluation_digest"))
    normalized = dict(record)
    if normalized["schema"] != BOOTSTRAP_VALIDATION_SCHEMA:
        raise BootstrapContractError("bootstrap_validation_schema_invalid")
    if normalized["outcome"] not in VALIDATION_OUTCOMES:
        raise BootstrapContractError("bootstrap_validation_outcome_invalid")
    if bool(normalized.get("trusted_admission")) or bool(normalized.get("capability_promotion")):
        raise BootstrapContractError("bootstrap_validation_governance_boundary_invalid")
    expected_id = stable_id("governed-bootstrap-validation", normalized["module_id"], normalized["module_digest"], normalized["evaluator_package_digest"], normalized["evaluation_digest"], int(normalized["version"]))
    if str(normalized["validation_id"]) != expected_id:
        raise BootstrapContractError("bootstrap_validation_id_drift")
    expected_digest = bootstrap_digest(_without_digest(normalized))
    existing_digest = str(normalized.get("artifact_digest") or expected_digest)
    if existing_digest != expected_digest:
        raise BootstrapContractError("bootstrap_validation_digest_drift")
    normalized["artifact_digest"] = expected_digest
    return normalized


def make_validated_bootstrap_competence(*, module: Mapping[str, Any], validation: Mapping[str, Any], version: int = 1) -> dict[str, Any]:
    if validation["outcome"] != "bootstrap_validation_passed":
        raise BootstrapContractError("bootstrap_competence_requires_passed_validation")
    record = {
        "schema": BOOTSTRAP_COMPETENCE_SCHEMA,
        "competence_id": stable_id("validated-bootstrap-competence", module["module_id"], validation["validation_id"], version),
        "version": version,
        "module_id": module["module_id"],
        "module_digest": module["artifact_digest"],
        "validation_id": validation["validation_id"],
        "validation_digest": validation["artifact_digest"],
        "state": "validated_bootstrap_competence",
        "origin": "operator_installed_bootstrap",
        "learned_by_delta": False,
        "behaviorally_validated": True,
        "trusted_admission": False,
        "capability_promotion": False,
        "autonomously_learned": False,
        "created_at": utc_now(),
    }
    return validate_validated_bootstrap_competence(record)


def validate_validated_bootstrap_competence(record: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(record, ("schema", "competence_id", "version", "module_id", "module_digest", "validation_id", "validation_digest", "state", "origin"))
    normalized = dict(record)
    if normalized["schema"] != BOOTSTRAP_COMPETENCE_SCHEMA:
        raise BootstrapContractError("bootstrap_competence_schema_invalid")
    if normalized["state"] != "validated_bootstrap_competence":
        raise BootstrapContractError("bootstrap_competence_state_invalid")
    if normalized["origin"] != "operator_installed_bootstrap":
        raise BootstrapContractError("bootstrap_competence_origin_invalid")
    if bool(normalized.get("learned_by_delta")) or bool(normalized.get("autonomously_learned")):
        raise BootstrapContractError("bootstrap_competence_not_autonomously_learned")
    if not bool(normalized.get("behaviorally_validated")):
        raise BootstrapContractError("bootstrap_competence_requires_behavioral_validation")
    if bool(normalized.get("trusted_admission")) or bool(normalized.get("capability_promotion")):
        raise BootstrapContractError("bootstrap_competence_governance_boundary_invalid")
    expected_id = stable_id("validated-bootstrap-competence", normalized["module_id"], normalized["validation_id"], int(normalized["version"]))
    if str(normalized["competence_id"]) != expected_id:
        raise BootstrapContractError("bootstrap_competence_id_drift")
    expected_digest = bootstrap_digest(_without_digest(normalized))
    existing_digest = str(normalized.get("artifact_digest") or expected_digest)
    if existing_digest != expected_digest:
        raise BootstrapContractError("bootstrap_competence_digest_drift")
    normalized["artifact_digest"] = expected_digest
    return normalized


def write_bootstrap_artifact(*, artifact_root: Path, directory: str, artifact_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(artifact_root) / directory / f"{artifact_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = _canonical(payload)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if _canonical(existing) != serialized:
            raise BootstrapContractError("bootstrap_artifact_digest_drift")
        return existing
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(serialized, encoding="utf-8")
    tmp.replace(path)
    return json.loads(path.read_text(encoding="utf-8"))


def make_bootstrap_installation_request(
    *,
    title: str,
    version: int,
    modules: Sequence[Mapping[str, Any]],
    relationships: Sequence[Mapping[str, Any]],
    prerequisite_roots: Sequence[str],
    intended_domains: Sequence[str],
    curriculum_seed: str = "",
    authored_by: str = "codex",
    operator_authorized: bool = True,
) -> dict[str, Any]:
    module_ids = tuple(sorted(str(module["module_id"]) for module in modules))
    relationship_ids = tuple(sorted(str(relationship["relationship_id"]) for relationship in relationships))
    request = {
        "schema": BOOTSTRAP_INSTALLATION_REQUEST_SCHEMA,
        "request_id": stable_id("governed-bootstrap-installation-request", curriculum_seed or title, version, module_ids, relationship_ids),
        "curriculum_seed": curriculum_seed or stable_id("governed-bootstrap-curriculum-seed", title, version),
        "title": title,
        "version": version,
        "modules": tuple(dict(module) for module in modules),
        "relationships": tuple(dict(relationship) for relationship in relationships),
        "prerequisite_roots": tuple(prerequisite_roots),
        "intended_domains": tuple(sorted(str(domain) for domain in intended_domains)),
        "origin": "operator_installed_bootstrap",
        "authored_by": authored_by,
        "operator_authorized": operator_authorized,
        "trusted_admission": False,
        "capability_promotion": False,
        "provider_configuration": {},
        "runtime_authority": {},
        "created_at": utc_now(),
    }
    request["request_digest"] = bootstrap_digest(_without_digest(request))
    return request


def _semantic_edge(relationship: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(relationship["source_module_id"]),
        str(relationship["relationship_type"]),
        str(relationship["target_module_id"]),
    )


def _has_requires_cycle(edges: Sequence[Mapping[str, Any]]) -> bool:
    graph: dict[str, set[str]] = {}
    for edge in edges:
        if edge["relationship_type"] == "requires":
            graph.setdefault(str(edge["source_module_id"]), set()).add(str(edge["target_module_id"]))
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in graph.get(node, set()):
            if visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in tuple(graph))


def preflight_bootstrap_installation(request: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if request.get("schema") != BOOTSTRAP_INSTALLATION_REQUEST_SCHEMA:
        errors.append("installation_request_schema_invalid")
    if not bool(request.get("operator_authorized")):
        errors.append("operator_installation_authorization_missing")
    if request.get("origin") != "operator_installed_bootstrap":
        errors.append("installation_origin_invalid")
    if request.get("runtime_authority") or request.get("provider_configuration"):
        errors.append("installation_request_contains_runtime_or_provider_authority")
    if bool(request.get("trusted_admission")) or bool(request.get("capability_promotion")):
        errors.append("installation_request_governance_boundary_invalid")
    modules: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    try:
        modules = [validate_bootstrap_module(item) for item in request.get("modules") or ()]
    except BootstrapContractError as exc:
        errors.append(str(exc))
    module_ids = tuple(str(module.get("module_id") or "") for module in modules)
    if len(set(module_ids)) != len(module_ids):
        errors.append("module_id_duplicate")
    known = set(module_ids)
    roots = tuple(str(item) for item in request.get("prerequisite_roots") or ())
    if not roots or any(root not in known for root in roots):
        errors.append("manifest_root_missing")
    intended_domains = tuple(sorted(str(item) for item in request.get("intended_domains") or ()))
    actual_domains = tuple(sorted({str(module.get("domain") or "") for module in modules}))
    if intended_domains and intended_domains != actual_domains:
        errors.append("manifest_domain_mismatch")
    for module in modules:
        for field in ("prerequisites", "enables", "related_modules", "contrasts_with"):
            for module_id in module.get(field) or ():
                if str(module_id) not in known:
                    errors.append(f"module_reference_missing:{module['module_id']}:{field}:{module_id}")
    try:
        relationships = [validate_bootstrap_relationship(item, known_module_ids=known) for item in request.get("relationships") or ()]
    except BootstrapContractError as exc:
        errors.append(str(exc))
    relationship_ids = tuple(str(relationship.get("relationship_id") or "") for relationship in relationships)
    if len(set(relationship_ids)) != len(relationship_ids):
        errors.append("relationship_id_duplicate")
    semantic_edges = tuple(_semantic_edge(relationship) for relationship in relationships)
    if len(set(semantic_edges)) != len(semantic_edges):
        errors.append("relationship_semantic_duplicate")
    if _has_requires_cycle(relationships):
        errors.append("requires_cycle_detected")
    incident = {module_id for relationship in relationships for module_id in (str(relationship["source_module_id"]), str(relationship["target_module_id"]))}
    disconnected = tuple(sorted(module_id for module_id in known if module_id not in incident and module_id not in set(roots)))
    if disconnected:
        errors.append("disconnected_module_without_root:" + ",".join(disconnected))
    curriculum_id = stable_id(
        "governed-bootstrap-curriculum",
        str(request.get("title") or ""),
        int(request.get("version") or 0),
        tuple(sorted(module_ids)),
        tuple(sorted(relationship_ids)),
    )
    curriculum_version = int(request.get("version") or 0)
    if not errors:
        modules = [
            validate_bootstrap_module({
                **{key: value for key, value in module.items() if key != "artifact_digest"},
                "curriculum_id": curriculum_id,
                "curriculum_version": curriculum_version,
            })
            for module in modules
        ]
        relationships = [
            validate_bootstrap_relationship(
                {
                    **{key: value for key, value in relationship.items() if key != "artifact_digest"},
                    "curriculum_id": curriculum_id,
                    "curriculum_version": curriculum_version,
                },
                known_module_ids=known,
            )
            for relationship in relationships
        ]
    try:
        manifest = make_bootstrap_manifest(title=str(request["title"]), version=int(request["version"]), modules=modules, relationships=relationships)
    except (BootstrapContractError, KeyError, ValueError) as exc:
        errors.append(str(exc))
        manifest = {}
    return {
        "accepted": not errors,
        "errors": tuple(errors),
        "modules": tuple(sorted(modules, key=lambda item: str(item["module_id"]))),
        "relationships": tuple(sorted(relationships, key=lambda item: str(item["relationship_id"]))),
        "manifest": manifest,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{uuid.uuid4().hex}.tmp"
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(_canonical(payload))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _final_path(root: Path, directory: str, artifact_id: str) -> Path:
    return root / directory / f"{artifact_id}.json"


def _assert_no_drift(path: Path, payload: Mapping[str, Any], reason: str) -> None:
    if path.exists() and _canonical(json.loads(path.read_text(encoding="utf-8"))) != _canonical(payload):
        raise BootstrapContractError(reason)


def install_bootstrap_curriculum(*, artifact_root: Path, request: Mapping[str, Any], fail_at: str = "") -> dict[str, Any]:
    root = Path(artifact_root)
    preflight = preflight_bootstrap_installation(request)
    if not preflight["accepted"]:
        return {"status": "validation_failed", "errors": preflight["errors"], "written": False}
    modules = tuple(dict(item) for item in preflight["modules"])
    relationships = tuple(dict(item) for item in preflight["relationships"])
    manifest = dict(preflight["manifest"])
    for module in modules:
        _assert_no_drift(_final_path(root, BOOTSTRAP_MODULE_DIRECTORY, module["module_id"]), module, "bootstrap_module_artifact_drift")
    for relationship in relationships:
        _assert_no_drift(_final_path(root, BOOTSTRAP_RELATIONSHIP_DIRECTORY, relationship["relationship_id"]), relationship, "bootstrap_relationship_artifact_drift")
    _assert_no_drift(_final_path(root, BOOTSTRAP_CURRICULUM_DIRECTORY, manifest["curriculum_id"]), manifest, "bootstrap_manifest_drift")
    if fail_at == "before_temp":
        raise BootstrapContractError("injected_before_temp")
    temp = root / BOOTSTRAP_TEMP_DIRECTORY / f"{uuid.uuid4().hex}.tmp"
    if temp.exists():
        shutil.rmtree(temp)
    try:
        for module in modules:
            _write_json(temp / BOOTSTRAP_MODULE_DIRECTORY / f"{module['module_id']}.json", module)
        if fail_at == "during_temp":
            raise BootstrapContractError("injected_during_temp")
        for relationship in relationships:
            _write_json(temp / BOOTSTRAP_RELATIONSHIP_DIRECTORY / f"{relationship['relationship_id']}.json", relationship)
        _write_json(temp / BOOTSTRAP_CURRICULUM_DIRECTORY / f"{manifest['curriculum_id']}.json", manifest)
        if fail_at == "before_publication":
            raise BootstrapContractError("injected_before_publication")
        for module in modules:
            final = _final_path(root, BOOTSTRAP_MODULE_DIRECTORY, module["module_id"])
            if not final.exists():
                _write_json(final, module)
        for relationship in relationships:
            final = _final_path(root, BOOTSTRAP_RELATIONSHIP_DIRECTORY, relationship["relationship_id"])
            if not final.exists():
                _write_json(final, relationship)
        manifest_final = _final_path(root, BOOTSTRAP_CURRICULUM_DIRECTORY, manifest["curriculum_id"])
        if not manifest_final.exists():
            _write_json(manifest_final, manifest)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return {
        "status": "installed",
        "curriculum_manifest": manifest,
        "modules": modules,
        "relationships": relationships,
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "validation_records_created": 0,
        "competence_records_created": 0,
    }


def list_installed_bootstrap_curricula(*, artifact_root: Path) -> tuple[str, ...]:
    directory = Path(artifact_root) / BOOTSTRAP_CURRICULUM_DIRECTORY
    if not directory.exists():
        return ()
    return tuple(sorted(path.stem for path in directory.glob("*.json")))


def read_bootstrap_curriculum_manifest(*, artifact_root: Path, curriculum_id: str) -> dict[str, Any]:
    path = _final_path(Path(artifact_root), BOOTSTRAP_CURRICULUM_DIRECTORY, curriculum_id)
    if not path.exists():
        raise BootstrapContractError("bootstrap_manifest_missing")
    return json.loads(path.read_text(encoding="utf-8"))


def load_bootstrap_curriculum_artifacts(*, artifact_root: Path, curriculum_id: str) -> dict[str, Any]:
    root = Path(artifact_root)
    raw_manifest = read_bootstrap_curriculum_manifest(artifact_root=root, curriculum_id=curriculum_id)
    module_ids = tuple(str(item) for item in raw_manifest.get("module_ids") or ())
    relationship_ids = tuple(str(item) for item in raw_manifest.get("relationship_ids") or ())
    modules = tuple(validate_bootstrap_module(json.loads(_final_path(root, BOOTSTRAP_MODULE_DIRECTORY, module_id).read_text(encoding="utf-8"))) for module_id in module_ids)
    relationships = tuple(validate_bootstrap_relationship(json.loads(_final_path(root, BOOTSTRAP_RELATIONSHIP_DIRECTORY, relationship_id).read_text(encoding="utf-8")), known_module_ids=set(module_ids)) for relationship_id in relationship_ids)
    manifest = validate_bootstrap_manifest(
        raw_manifest,
        modules=modules,
        relationships=relationships,
    )
    return {"manifest": manifest, "modules": modules, "relationships": relationships}


def discover_incomplete_bootstrap_installations(*, artifact_root: Path) -> tuple[str, ...]:
    temp_root = Path(artifact_root) / BOOTSTRAP_TEMP_DIRECTORY
    if not temp_root.exists():
        return ()
    return tuple(sorted(path.name for path in temp_root.iterdir() if path.is_dir()))
