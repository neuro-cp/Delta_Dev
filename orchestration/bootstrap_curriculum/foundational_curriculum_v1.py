from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import shutil
from typing import Any

from orchestration.runtime.developmental_bootstrap import (
    BOOTSTRAP_COMPETENCE_DIRECTORY,
    BOOTSTRAP_VALIDATION_DIRECTORY,
    discover_incomplete_bootstrap_installations,
    install_bootstrap_curriculum,
    list_installed_bootstrap_curricula,
    load_bootstrap_curriculum_artifacts,
    make_bootstrap_installation_request,
    preflight_bootstrap_installation,
)

from .foundational_modules_v1 import CURRICULUM_SEED, CURRICULUM_TITLE, CURRICULUM_VERSION, DOMAINS, build_foundational_modules_v1
from .foundational_relationships_v1 import build_foundational_relationships_v1


INSTALLATION_ROOT = Path(".tmp") / "bootstrap-c-foundational-curriculum-v1"
EXPECTED_MODULE_RANGE = range(72, 97)
EXPECTED_RELATIONSHIP_RANGE = range(180, 301)


def build_foundational_curriculum_v1() -> dict[str, Any]:
    modules = build_foundational_modules_v1()
    relationships = build_foundational_relationships_v1(modules)
    roots = tuple(module["module_id"] for module in modules if not module.get("prerequisites"))
    request = make_bootstrap_installation_request(
        title=CURRICULUM_TITLE,
        version=CURRICULUM_VERSION,
        modules=modules,
        relationships=relationships,
        prerequisite_roots=roots,
        intended_domains=DOMAINS,
        curriculum_seed=CURRICULUM_SEED,
    )
    return {"modules": modules, "relationships": relationships, "roots": roots, "request": request}


def _requires_cycle(relationships: tuple[dict, ...]) -> bool:
    graph: dict[str, set[str]] = defaultdict(set)
    for relationship in relationships:
        if relationship["relationship_type"] == "requires":
            graph[relationship["source_module_id"]].add(relationship["target_module_id"])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for target in graph.get(node, set()):
            if visit(target):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in tuple(graph))


def validate_foundational_curriculum_quality(curriculum: dict[str, Any]) -> dict[str, Any]:
    modules = tuple(curriculum["modules"])
    relationships = tuple(curriculum["relationships"])
    module_ids = {module["module_id"] for module in modules}
    errors: list[str] = []
    if len(modules) not in EXPECTED_MODULE_RANGE:
        errors.append("module_count_out_of_range")
    if len(relationships) not in EXPECTED_RELATIONSHIP_RANGE:
        errors.append("relationship_count_out_of_range")
    if set(module["domain"] for module in modules) != set(DOMAINS):
        errors.append("domain_coverage_incomplete")
    title_keys = [(module["domain"], module["title"]) for module in modules]
    if len(set(title_keys)) != len(title_keys):
        errors.append("duplicate_title_within_domain")
    for module in modules:
        if module["origin"] != "operator_installed_bootstrap" or module["learned_by_delta"] or module["behaviorally_validated"]:
            errors.append(f"module_provenance_invalid:{module['module_id']}")
        if module["trusted_admission"] or module["capability_promotion"]:
            errors.append(f"module_governance_boundary_invalid:{module['module_id']}")
        if not module.get("definition") or len(str(module["definition"]).split()) < 8:
            errors.append(f"blank_or_overly_broad_definition:{module['module_id']}")
        if not module.get("scope_limits"):
            errors.append(f"scope_limit_missing:{module['module_id']}")
        if not module.get("verification_methods"):
            errors.append(f"verification_method_missing:{module['module_id']}")
        if not module.get("source_bindings"):
            errors.append(f"source_binding_missing:{module['module_id']}")
        for source_binding in module.get("source_bindings") or ():
            if not source_binding.get("source_id") or not source_binding.get("source_type") or not source_binding.get("artifact_digest"):
                errors.append(f"source_binding_invalid:{module['module_id']}")
        for field in ("prerequisites", "enables", "related_modules", "contrasts_with"):
            for reference in module.get(field) or ():
                if reference not in module_ids:
                    errors.append(f"module_reference_unresolved:{module['module_id']}:{reference}")
    semantic_edges = [(relationship["source_module_id"], relationship["relationship_type"], relationship["target_module_id"]) for relationship in relationships]
    if len(set(semantic_edges)) != len(semantic_edges):
        errors.append("duplicate_semantic_relationship")
    for relationship in relationships:
        if relationship["source_module_id"] not in module_ids or relationship["target_module_id"] not in module_ids:
            errors.append(f"relationship_endpoint_unresolved:{relationship['relationship_id']}")
    if _requires_cycle(relationships):
        errors.append("requires_cycle")
    roots = tuple(module["module_id"] for module in modules if not module.get("prerequisites"))
    root_domains = {module["domain"] for module in modules if module["module_id"] in roots}
    if root_domains != set(DOMAINS):
        errors.append("domain_root_missing")
    connected_ids = {item for edge in semantic_edges for item in (edge[0], edge[2])}
    for module in modules:
        if module["module_id"] not in roots and module["module_id"] not in connected_ids:
            errors.append(f"orphan_module:{module['module_id']}")
    incoming = defaultdict(list)
    for source, relationship_type, target in semantic_edges:
        if relationship_type in {"requires", "enables"}:
            incoming[target].append(source)
    for module in modules:
        if module["module_id"] not in roots and not incoming[module["module_id"]]:
            errors.append(f"non_root_without_incoming_support:{module['module_id']}")
    cross_domain = tuple(
        relationship for relationship in relationships
        if next(module["domain"] for module in modules if module["module_id"] == relationship["source_module_id"])
        != next(module["domain"] for module in modules if module["module_id"] == relationship["target_module_id"])
    )
    source_breakdown = Counter(binding["source_type"] for module in modules for binding in module.get("source_bindings") or ())
    domains = Counter(module["domain"] for module in modules)
    return {
        "accepted": not errors,
        "errors": tuple(errors),
        "module_count": len(modules),
        "relationship_count": len(relationships),
        "domains": dict(sorted(domains.items())),
        "root_count": len(roots),
        "cross_domain_relationship_count": len(cross_domain),
        "source_binding_breakdown": dict(sorted(source_breakdown.items())),
    }


def install_foundational_curriculum_v1(*, artifact_root: Path = INSTALLATION_ROOT, reset: bool = False) -> dict[str, Any]:
    root = Path(artifact_root)
    if reset and root.exists():
        shutil.rmtree(root)
    curriculum = build_foundational_curriculum_v1()
    quality = validate_foundational_curriculum_quality(curriculum)
    if not quality["accepted"]:
        return {"status": "quality_failed", "quality": quality}
    preflight = preflight_bootstrap_installation(curriculum["request"])
    if not preflight["accepted"]:
        return {"status": "preflight_failed", "preflight": preflight, "quality": quality}
    installed = install_bootstrap_curriculum(artifact_root=root, request=curriculum["request"])
    loaded = load_bootstrap_curriculum_artifacts(
        artifact_root=root,
        curriculum_id=installed["curriculum_manifest"]["curriculum_id"],
    )
    replay = install_bootstrap_curriculum(artifact_root=root, request=curriculum["request"])
    discovered = list_installed_bootstrap_curricula(artifact_root=root)
    validation_files = tuple((root / BOOTSTRAP_VALIDATION_DIRECTORY).glob("*.json")) if (root / BOOTSTRAP_VALIDATION_DIRECTORY).exists() else ()
    competence_files = tuple((root / BOOTSTRAP_COMPETENCE_DIRECTORY).glob("*.json")) if (root / BOOTSTRAP_COMPETENCE_DIRECTORY).exists() else ()
    return {
        "status": "installed",
        "artifact_root": str(root),
        "quality": quality,
        "preflight": preflight,
        "installed": installed,
        "loaded": loaded,
        "replay": replay,
        "discovered": discovered,
        "incomplete": discover_incomplete_bootstrap_installations(artifact_root=root),
        "validation_record_count": len(validation_files),
        "competence_record_count": len(competence_files),
    }
