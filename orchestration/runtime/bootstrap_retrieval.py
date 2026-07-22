"""Read-only bootstrap curriculum retrieval for developmental planning."""
from __future__ import annotations

from collections import defaultdict, deque
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import (
    BOOTSTRAP_COMPETENCE_DIRECTORY,
    BOOTSTRAP_CURRICULUM_DIRECTORY,
    BOOTSTRAP_MODULE_DIRECTORY,
    BOOTSTRAP_VALIDATION_DIRECTORY,
    BootstrapContractError,
    bootstrap_digest,
    load_bootstrap_curriculum_artifacts,
    validate_bootstrap_validation_record,
    validate_validated_bootstrap_competence,
)


BOOTSTRAP_RETRIEVAL_REQUEST_SCHEMA = "bootstrap_graph_retrieval_request_v1"
BOOTSTRAP_RETRIEVAL_RESULT_SCHEMA = "bootstrap_graph_retrieval_result_v1"
BOOTSTRAP_PACKET_SCHEMA = "learner_visible_bootstrap_packet_v1"

BOOTSTRAP_CLASSIFICATIONS = frozenset({
    "installed_unvalidated_bootstrap",
    "validated_bootstrap_competence",
    "autonomously_learned_competence",
    "unavailable_or_missing",
})

TOKEN_ALIASES = {
    "percentage": "percent",
    "percentages": "percent",
    "percentag": "percent",
    "schema": "schema",
    "schemas": "schema",
    "machine": "machine",
    "machines": "machine",
}
OBJECTIVE_STOPWORDS = frozenset({"reasoning", "reason", "using", "use", "learn", "learning"})

DEFAULT_ALLOWED_RELATIONSHIP_TYPES = ("requires", "prerequisite_for", "enables", "transfers_to", "relates_to")
PACKET_ALLOWED_FIELDS = (
    "module_id",
    "title",
    "domain",
    "definition",
    "key_components",
    "procedure",
    "worked_examples",
    "counterexamples",
    "failure_modes",
    "verification_methods",
    "scope_limits",
    "prerequisites",
    "validation_state",
    "source_bindings",
)
FORBIDDEN_PACKET_FIELDS = frozenset({
    "answer_key",
    "sealed_prompt",
    "scoring_rule",
    "pass_threshold",
    "rubric",
    "evaluator_view",
    "evaluator_hidden",
    "trusted_admission",
    "capability_promotion",
})


class BootstrapRetrievalError(ValueError):
    """Raised when a read-only bootstrap retrieval contract is invalid."""


def _tokens(value: Any) -> tuple[str, ...]:
    text = " ".join(str(item) for item in value) if isinstance(value, tuple | list) else str(value)
    raw = re.findall(r"[a-z0-9]+", text.lower().replace("_", " "))
    normalized: list[str] = []
    for token in raw:
        if len(token) > 4 and token.endswith("ing"):
            token = token[:-3]
        elif len(token) > 3 and token.endswith("es"):
            token = token[:-2]
        elif len(token) > 3 and token.endswith("s"):
            token = token[:-1]
        token = TOKEN_ALIASES.get(token, token)
        if token not in OBJECTIVE_STOPWORDS:
            normalized.append(token)
    return tuple(dict.fromkeys(normalized))


def make_bootstrap_retrieval_request(
    *,
    objective: str,
    curriculum_id: str,
    curriculum_version: int,
    domain_hints: Sequence[str] = (),
    max_results: int = 8,
    max_traversal_depth: int = 2,
    allowed_relationship_types: Sequence[str] = DEFAULT_ALLOWED_RELATIONSHIP_TYPES,
    include_unvalidated_for_study: bool = True,
    require_validated_prerequisites: bool = False,
    max_packet_modules: int = 12,
    max_chars_per_module: int = 1200,
    max_total_chars: int = 8000,
) -> dict[str, Any]:
    if not objective.strip():
        raise BootstrapRetrievalError("bootstrap_retrieval_objective_missing")
    request = {
        "schema": BOOTSTRAP_RETRIEVAL_REQUEST_SCHEMA,
        "request_id": stable_id("bootstrap-retrieval-request", objective, curriculum_id, curriculum_version, tuple(sorted(domain_hints))),
        "normalized_objective": " ".join(_tokens(objective)),
        "objective_tokens": _tokens(objective),
        "domain_hints": tuple(sorted(str(item) for item in domain_hints)),
        "max_results": int(max_results),
        "max_traversal_depth": int(max_traversal_depth),
        "allowed_relationship_types": tuple(allowed_relationship_types),
        "include_unvalidated_for_study": bool(include_unvalidated_for_study),
        "require_validated_prerequisites": bool(require_validated_prerequisites),
        "curriculum_id": curriculum_id,
        "curriculum_version": int(curriculum_version),
        "max_packet_modules": int(max_packet_modules),
        "max_chars_per_module": int(max_chars_per_module),
        "max_total_chars": int(max_total_chars),
    }
    request["request_digest"] = bootstrap_digest({key: value for key, value in request.items() if key != "request_digest"})
    return request


def _module_terms(module: Mapping[str, Any]) -> dict[str, set[str]]:
    return {
        "title": set(_tokens(module["title"])),
        "key_components": set(_tokens(module.get("key_components") or ())),
        "definition": set(_tokens(module.get("definition") or "")),
        "domain": set(_tokens(module.get("domain") or "")),
    }


def _read_json_files(directory: Path) -> tuple[dict[str, Any], ...]:
    if not directory.exists():
        return ()
    records = []
    for path in sorted(directory.glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return tuple(records)


def _validation_indexes(root: Path, module_ids: set[str]) -> tuple[dict[str, tuple[dict, ...]], dict[str, tuple[dict, ...]]]:
    validations: dict[str, list[dict]] = defaultdict(list)
    for record in _read_json_files(root / BOOTSTRAP_VALIDATION_DIRECTORY):
        validation = validate_bootstrap_validation_record(record)
        if validation["module_id"] in module_ids:
            validations[validation["module_id"]].append(validation)
    competencies: dict[str, list[dict]] = defaultdict(list)
    for record in _read_json_files(root / BOOTSTRAP_COMPETENCE_DIRECTORY):
        competence = validate_validated_bootstrap_competence(record)
        if competence["module_id"] in module_ids:
            competencies[competence["module_id"]].append(competence)
    return (
        {key: tuple(sorted(value, key=lambda item: item["validation_id"])) for key, value in validations.items()},
        {key: tuple(sorted(value, key=lambda item: item["competence_id"])) for key, value in competencies.items()},
    )


def _classify_module(module: Mapping[str, Any], validations: Mapping[str, tuple[dict, ...]], competencies: Mapping[str, tuple[dict, ...]]) -> dict[str, Any]:
    module_id = str(module["module_id"])
    validation_records = validations.get(module_id, ())
    competence_records = competencies.get(module_id, ())
    if competence_records:
        label = "validated_bootstrap_competence"
        demonstrated = True
    else:
        label = "installed_unvalidated_bootstrap"
        demonstrated = False
    return {
        "module_id": module_id,
        "validation_state_label": label,
        "curriculum_coverage": True,
        "installation_origin": module["origin"],
        "behaviorally_validated": demonstrated,
        "validation_outcomes": tuple(record["outcome"] for record in validation_records),
        "competence_ids": tuple(record["competence_id"] for record in competence_records),
        "trusted_status": False,
        "eligible_as_demonstrated_prerequisite": demonstrated,
        "eligible_as_study_material": label in {"installed_unvalidated_bootstrap", "validated_bootstrap_competence"},
        "learned_by_delta": False,
        "unresolved_as_demonstrated_competence": not demonstrated,
        "missing_from_curriculum": False,
    }


def _relationship_indexes(relationships: Sequence[Mapping[str, Any]]) -> tuple[dict[str, tuple[dict, ...]], dict[str, tuple[dict, ...]]]:
    outgoing: dict[str, list[dict]] = defaultdict(list)
    incoming: dict[str, list[dict]] = defaultdict(list)
    for relationship in relationships:
        outgoing[str(relationship["source_module_id"])].append(dict(relationship))
        incoming[str(relationship["target_module_id"])].append(dict(relationship))
    return (
        {key: tuple(sorted(value, key=lambda item: item["relationship_id"])) for key, value in outgoing.items()},
        {key: tuple(sorted(value, key=lambda item: item["relationship_id"])) for key, value in incoming.items()},
    )


def _score_module(module: Mapping[str, Any], request: Mapping[str, Any], outgoing: Mapping[str, tuple[dict, ...]], incoming: Mapping[str, tuple[dict, ...]], module_by_id: Mapping[str, Mapping[str, Any]]) -> tuple[int, tuple[str, ...]]:
    objective = str(request["normalized_objective"])
    query = set(request["objective_tokens"])
    terms = _module_terms(module)
    title_text = " ".join(_tokens(module["title"]))
    score = 0
    reasons: list[str] = []
    if objective == str(module["module_id"]).lower():
        score += 1000
        reasons.append("exact_module_id")
    if objective == title_text:
        score += 700
        reasons.append("exact_title")
    elif query and query.issubset(terms["title"]):
        score += 550
        reasons.append("near_title")
    title_overlap = len(query & terms["title"])
    key_overlap = len(query & terms["key_components"])
    definition_overlap = len(query & terms["definition"])
    domain_overlap = len(query & terms["domain"])
    if title_overlap:
        score += 120 * title_overlap
        reasons.append("title_overlap")
    if key_overlap:
        score += 80 * key_overlap
        reasons.append("key_component_overlap")
    if definition_overlap:
        score += 30 * definition_overlap
        reasons.append("definition_overlap")
    if domain_overlap:
        score += 20 * domain_overlap
        reasons.append("domain_overlap")
    if str(module["domain"]) in set(request.get("domain_hints") or ()):
        score += 60
        reasons.append("domain_hint")
    for relationship in (*outgoing.get(module["module_id"], ()), *incoming.get(module["module_id"], ())):
        other_id = relationship["target_module_id"] if relationship["source_module_id"] == module["module_id"] else relationship["source_module_id"]
        other = module_by_id.get(other_id)
        if not other:
            continue
        other_terms = _module_terms(other)
        if relationship["relationship_type"] == "enables" and query & other_terms["title"]:
            score += 40
            reasons.append("directly_enabled_capability")
        if relationship["relationship_type"] == "transfers_to" and query & other_terms["title"]:
            score += 35
            reasons.append("transfers_to_capability")
    return score, tuple(dict.fromkeys(reasons))


def _traverse_prerequisites(selected_ids: Sequence[str], relationships: Sequence[Mapping[str, Any]], max_depth: int, allowed_types: set[str]) -> tuple[tuple[str, ...], tuple[dict, ...], tuple[str, ...]]:
    prereq_edges: dict[str, list[dict]] = defaultdict(list)
    missing: set[str] = set()
    for relationship in relationships:
        rel_type = relationship["relationship_type"]
        if rel_type == "requires" and rel_type in allowed_types:
            prereq_edges[relationship["source_module_id"]].append(dict(relationship))
        elif rel_type == "prerequisite_for" and rel_type in allowed_types:
            prereq_edges[relationship["target_module_id"]].append(dict(relationship))
    queue = deque((module_id, 0, ()) for module_id in selected_ids)
    visited = set(selected_ids)
    prerequisites: list[str] = []
    paths: list[dict] = []
    while queue:
        module_id, depth, path = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in sorted(prereq_edges.get(module_id, ()), key=lambda item: item["relationship_id"]):
            target = edge["target_module_id"] if edge["relationship_type"] == "requires" else edge["source_module_id"]
            next_path = (*path, edge["relationship_id"])
            if target in visited:
                continue
            visited.add(target)
            prerequisites.append(target)
            paths.append({
                "from_module_id": module_id,
                "to_module_id": target,
                "relationship_id": edge["relationship_id"],
                "relationship_type": edge["relationship_type"],
                "depth": depth + 1,
                "path": next_path,
            })
            queue.append((target, depth + 1, next_path))
    return tuple(prerequisites), tuple(paths), tuple(sorted(missing))


def _adjacent_modules(selected_ids: Sequence[str], relationships: Sequence[Mapping[str, Any]], allowed_types: set[str]) -> tuple[dict, ...]:
    adjacent_types = {"enables", "transfers_to", "relates_to"} & allowed_types
    selected = set(selected_ids)
    adjacent: dict[str, dict] = {}
    for relationship in relationships:
        if relationship["relationship_type"] not in adjacent_types:
            continue
        if relationship["source_module_id"] in selected:
            adjacent.setdefault(relationship["target_module_id"], {
                "module_id": relationship["target_module_id"],
                "relationship_id": relationship["relationship_id"],
                "relationship_type": relationship["relationship_type"],
                "direction": "outgoing",
            })
        elif relationship["target_module_id"] in selected:
            adjacent.setdefault(relationship["source_module_id"], {
                "module_id": relationship["source_module_id"],
                "relationship_id": relationship["relationship_id"],
                "relationship_type": relationship["relationship_type"],
                "direction": "incoming",
            })
    return tuple(sorted(adjacent.values(), key=lambda item: (item["module_id"], item["relationship_id"])))


def _truncate_payload(payload: dict[str, Any], max_chars: int) -> tuple[dict[str, Any], tuple[str, ...]]:
    omitted: list[str] = []
    result = dict(payload)
    for field in ("worked_examples", "counterexamples", "procedure", "key_components", "failure_modes", "verification_methods", "source_bindings"):
        if len(json.dumps(result, sort_keys=True, default=str)) <= max_chars:
            break
        if result.get(field):
            result[field] = ()
            omitted.append(field)
    if len(json.dumps(result, sort_keys=True, default=str)) > max_chars and result.get("definition"):
        result["definition"] = str(result["definition"])[: max(80, max_chars // 4)] + "...[truncated]"
        omitted.append("definition")
    return result, tuple(omitted)


def compile_learner_visible_bootstrap_packet(
    *,
    curriculum_manifest: Mapping[str, Any],
    modules: Sequence[Mapping[str, Any]],
    classifications: Mapping[str, Mapping[str, Any]],
    graph_paths: Sequence[Mapping[str, Any]],
    max_modules: int,
    max_chars_per_module: int,
    max_total_chars: int,
) -> dict[str, Any]:
    selected: list[dict] = []
    omitted_modules: list[str] = []
    omitted_fields: dict[str, tuple[str, ...]] = {}
    total_chars = 0
    for module in modules:
        if len(selected) >= max_modules:
            omitted_modules.append(module["module_id"])
            continue
        payload = {field: module.get(field, ()) for field in PACKET_ALLOWED_FIELDS if field in module}
        payload["validation_state"] = classifications[module["module_id"]]["validation_state_label"]
        payload = {key: value for key, value in payload.items() if key not in FORBIDDEN_PACKET_FIELDS}
        truncated, fields = _truncate_payload(payload, max_chars_per_module)
        size = len(json.dumps(truncated, sort_keys=True, default=str))
        if total_chars + size > max_total_chars:
            omitted_modules.append(module["module_id"])
            continue
        total_chars += size
        selected.append(truncated)
        if fields:
            omitted_fields[module["module_id"]] = fields
    packet = {
        "schema": BOOTSTRAP_PACKET_SCHEMA,
        "packet_id": stable_id("learner-visible-bootstrap-packet", curriculum_manifest["curriculum_id"], tuple(module["module_id"] for module in selected), tuple(path["relationship_id"] for path in graph_paths)),
        "curriculum_id": curriculum_manifest["curriculum_id"],
        "curriculum_digest": curriculum_manifest["artifact_digest"],
        "selected_module_digests": tuple((module["module_id"], module["artifact_digest"]) for module in modules if module["module_id"] in {item["module_id"] for item in selected}),
        "modules": tuple(selected),
        "graph_path_evidence": tuple(dict(path) for path in graph_paths),
        "validation_state_classifications": tuple((module_id, classifications[module_id]["validation_state_label"]) for module_id in sorted(classifications)),
        "max_modules": max_modules,
        "max_chars_per_module": max_chars_per_module,
        "max_total_chars": max_total_chars,
        "total_chars": total_chars,
        "omitted_modules": tuple(omitted_modules),
        "omitted_fields": tuple(sorted((module_id, fields) for module_id, fields in omitted_fields.items())),
    }
    packet["packet_digest"] = bootstrap_digest({key: value for key, value in packet.items() if key != "packet_digest"})
    return packet


def retrieve_bootstrap_context(*, curriculum_root: Path, request: Mapping[str, Any], autonomously_learned: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    if request.get("schema") != BOOTSTRAP_RETRIEVAL_REQUEST_SCHEMA:
        raise BootstrapRetrievalError("bootstrap_retrieval_request_schema_invalid")
    if any(request.get(field) for field in ("provider_configuration", "runtime_authority", "trusted_admission", "capability_promotion")):
        raise BootstrapRetrievalError("bootstrap_retrieval_request_contains_authority")
    root = Path(curriculum_root)
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=root, curriculum_id=str(request["curriculum_id"]))
    manifest = loaded["manifest"]
    if int(manifest["version"]) != int(request["curriculum_version"]):
        raise BootstrapRetrievalError("bootstrap_retrieval_curriculum_version_mismatch")
    modules = tuple(dict(module) for module in loaded["modules"])
    relationships = tuple(dict(relationship) for relationship in loaded["relationships"])
    module_by_id = {module["module_id"]: module for module in modules}
    outgoing, incoming = _relationship_indexes(relationships)
    scored = []
    for module in modules:
        score, reasons = _score_module(module, request, outgoing, incoming, module_by_id)
        if score > 0:
            scored.append((score, module["module_id"], reasons))
    scored.sort(key=lambda item: (-item[0], item[1]))
    direct_ids = tuple(module_id for _, module_id, _ in scored[: int(request["max_results"])])
    allowed_types = set(request.get("allowed_relationship_types") or ())
    prerequisite_ids, graph_paths, missing_refs = _traverse_prerequisites(direct_ids, relationships, int(request["max_traversal_depth"]), allowed_types)
    adjacent = _adjacent_modules((*direct_ids, *prerequisite_ids), relationships, allowed_types)
    ordered_ids = tuple(dict.fromkeys((*prerequisite_ids, *direct_ids, *(item["module_id"] for item in adjacent))))
    validations, competencies = _validation_indexes(root, set(module_by_id))
    classifications = {
        module_id: _classify_module(module_by_id[module_id], validations, competencies)
        for module_id in ordered_ids
        if module_id in module_by_id
    }
    missing_from_curriculum = tuple(
        sorted(token for token in request["objective_tokens"] if not any(token in _tokens(module["title"]) or token in _tokens(module.get("definition") or "") for module in modules))
    )
    selected_modules = tuple(module_by_id[module_id] for module_id in ordered_ids if module_id in module_by_id)
    packet = compile_learner_visible_bootstrap_packet(
        curriculum_manifest=manifest,
        modules=selected_modules,
        classifications=classifications,
        graph_paths=graph_paths,
        max_modules=int(request["max_packet_modules"]),
        max_chars_per_module=int(request["max_chars_per_module"]),
        max_total_chars=int(request["max_total_chars"]),
    )
    autonomous_matches = tuple(
        dict(record) for record in autonomously_learned
        if set(_tokens(record.get("title") or record.get("concept") or "")) & set(request["objective_tokens"])
    )
    covered_by_installed_study_material = tuple(sorted(
        module_id for module_id, item in classifications.items()
        if item["validation_state_label"] == "installed_unvalidated_bootstrap" and item["eligible_as_study_material"]
    ))
    covered_by_validated_bootstrap_competence = tuple(sorted(
        module_id for module_id, item in classifications.items()
        if item["validation_state_label"] == "validated_bootstrap_competence"
    ))
    covered_by_autonomously_learned_competence = tuple(sorted(
        str(record.get("competence_id") or record.get("concept") or record.get("title") or "")
        for record in autonomous_matches
        if record.get("state") == "autonomously_learned_competence"
    ))
    unresolved_as_demonstrated_competence = tuple(sorted(
        module_id for module_id, item in classifications.items()
        if item["unresolved_as_demonstrated_competence"]
    ))
    result = {
        "schema": BOOTSTRAP_RETRIEVAL_RESULT_SCHEMA,
        "result_id": stable_id("bootstrap-retrieval-result", request["request_digest"], manifest["artifact_digest"], tuple(ordered_ids), packet["packet_digest"]),
        "request_digest": request["request_digest"],
        "curriculum_id": manifest["curriculum_id"],
        "curriculum_digest": manifest["artifact_digest"],
        "direct_matches": tuple({
            "module_id": module_id,
            "score": score,
            "ranking_reasons": reasons,
        } for score, module_id, reasons in scored[: int(request["max_results"])]),
        "prerequisite_modules": tuple(prerequisite_ids),
        "adjacent_modules": adjacent,
        "selected_modules": tuple(module["module_id"] for module in selected_modules),
        "graph_paths": graph_paths,
        "missing_references": missing_refs,
        "traversal_depth": int(request["max_traversal_depth"]),
        "classifications": tuple(classifications[module_id] for module_id in sorted(classifications)),
        "validated_prerequisite_modules": tuple(sorted(module_id for module_id, item in classifications.items() if item["eligible_as_demonstrated_prerequisite"])),
        "unvalidated_study_modules": tuple(sorted(module_id for module_id, item in classifications.items() if item["validation_state_label"] == "installed_unvalidated_bootstrap")),
        "covered_by_installed_study_material": covered_by_installed_study_material,
        "covered_by_validated_bootstrap_competence": covered_by_validated_bootstrap_competence,
        "covered_by_autonomously_learned_competence": covered_by_autonomously_learned_competence,
        "unresolved_as_demonstrated_competence": unresolved_as_demonstrated_competence,
        "missing_from_curriculum": missing_from_curriculum,
        "unresolved_concepts": missing_from_curriculum,
        "recommended_evidence_targets": (
            *(f"behavioral validation for module {module_id}" for module_id in unresolved_as_demonstrated_competence),
            *(f"curriculum coverage for concept {token}" for token in missing_from_curriculum),
        ),
        "suggested_validation_prerequisites": tuple(sorted(module_id for module_id, item in classifications.items() if not item["eligible_as_demonstrated_prerequisite"])),
        "autonomously_learned_matches": autonomous_matches,
        "learner_visible_packet": packet,
        "provider_calls": 0,
        "learner_calls": 0,
        "evaluator_calls": 0,
        "validation_records_created": 0,
        "competence_records_created": 0,
        "trusted_admissions": 0,
        "capability_promotions": 0,
    }
    result["result_digest"] = bootstrap_digest({key: value for key, value in result.items() if key != "result_digest"})
    return result


def resolve_bootstrap_context(*, runtime_root: Path, objective: str, curriculum_root: Path, retrieval_policy: Mapping[str, Any]) -> dict[str, Any]:
    del runtime_root
    manifest_ids = tuple(sorted(path.stem for path in (Path(curriculum_root) / BOOTSTRAP_CURRICULUM_DIRECTORY).glob("*.json")))
    if not manifest_ids:
        raise BootstrapRetrievalError("bootstrap_retrieval_curriculum_missing")
    curriculum_id = str(retrieval_policy.get("curriculum_id") or manifest_ids[0])
    manifest = json.loads((Path(curriculum_root) / BOOTSTRAP_CURRICULUM_DIRECTORY / f"{curriculum_id}.json").read_text(encoding="utf-8"))
    request = make_bootstrap_retrieval_request(
        objective=objective,
        curriculum_id=curriculum_id,
        curriculum_version=int(retrieval_policy.get("curriculum_version") or manifest["version"]),
        domain_hints=tuple(retrieval_policy.get("domain_hints") or ()),
        max_results=int(retrieval_policy.get("max_results") or 8),
        max_traversal_depth=int(retrieval_policy.get("max_traversal_depth") or 2),
        allowed_relationship_types=tuple(retrieval_policy.get("allowed_relationship_types") or DEFAULT_ALLOWED_RELATIONSHIP_TYPES),
        include_unvalidated_for_study=bool(retrieval_policy.get("include_unvalidated_for_study", True)),
        require_validated_prerequisites=bool(retrieval_policy.get("require_validated_prerequisites", False)),
        max_packet_modules=int(retrieval_policy.get("max_packet_modules") or 12),
        max_chars_per_module=int(retrieval_policy.get("max_chars_per_module") or 1200),
        max_total_chars=int(retrieval_policy.get("max_total_chars") or 8000),
    )
    return retrieve_bootstrap_context(curriculum_root=curriculum_root, request=request)
