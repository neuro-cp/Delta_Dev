"""Inert contracts for governed developmental bootstrap curriculum.

BOOTSTRAP-A owns schema and provenance boundaries only.  It does not install a
curriculum, retrieve evidence, execute learners or evaluators, promote
capabilities, or admit trusted memory.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


BOOTSTRAP_MODULE_SCHEMA = "governed_bootstrap_module_v1"
BOOTSTRAP_RELATIONSHIP_SCHEMA = "governed_bootstrap_relationship_v1"
BOOTSTRAP_CURRICULUM_SCHEMA = "governed_bootstrap_curriculum_manifest_v1"
BOOTSTRAP_VALIDATION_SCHEMA = "governed_bootstrap_validation_record_v1"
BOOTSTRAP_COMPETENCE_SCHEMA = "validated_bootstrap_competence_v1"

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
        "relationship_ids": relationship_ids,
        "domains": domains,
        "module_count": len(module_ids),
        "relationship_count": len(relationship_ids),
        "prerequisite_roots": tuple(sorted(set(module_ids) - required)),
        "leaf_capabilities": tuple(sorted(set(module_ids) - targets)),
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "created_at": utc_now(),
    }
    return validate_bootstrap_manifest(record, modules=modules, relationships=relationships)


def validate_bootstrap_manifest(record: Mapping[str, Any], *, modules: Sequence[Mapping[str, Any]], relationships: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _require_fields(record, ("schema", "curriculum_id", "version", "module_ids", "relationship_ids", "bootstrap_installed", "bootstrap_validated"))
    normalized = dict(record)
    module_ids = tuple(str(module["module_id"]) for module in modules)
    relationship_ids = tuple(str(relationship["relationship_id"]) for relationship in relationships)
    if normalized["schema"] != BOOTSTRAP_CURRICULUM_SCHEMA:
        raise BootstrapContractError("bootstrap_manifest_schema_invalid")
    if tuple(normalized["module_ids"]) != module_ids or tuple(normalized["relationship_ids"]) != relationship_ids:
        raise BootstrapContractError("bootstrap_manifest_membership_mismatch")
    if bool(normalized["bootstrap_validated"]):
        raise BootstrapContractError("bootstrap_manifest_validation_must_start_false")
    if int(normalized.get("trusted_admissions") or 0) or int(normalized.get("capability_promotions") or 0):
        raise BootstrapContractError("bootstrap_manifest_governance_boundary_invalid")
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

