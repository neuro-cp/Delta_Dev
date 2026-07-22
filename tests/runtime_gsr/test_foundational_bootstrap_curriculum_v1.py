from __future__ import annotations

import shutil

from orchestration.bootstrap_curriculum.foundational_curriculum_v1 import (
    DOMAINS,
    EXPECTED_MODULE_RANGE,
    EXPECTED_RELATIONSHIP_RANGE,
    INSTALLATION_ROOT,
    build_foundational_curriculum_v1,
    install_foundational_curriculum_v1,
    validate_foundational_curriculum_quality,
)
from orchestration.runtime.developmental_bootstrap import (
    BOOTSTRAP_COMPETENCE_DIRECTORY,
    BOOTSTRAP_TEMP_DIRECTORY,
    BOOTSTRAP_VALIDATION_DIRECTORY,
    discover_incomplete_bootstrap_installations,
    install_bootstrap_curriculum,
    list_installed_bootstrap_curricula,
    load_bootstrap_curriculum_artifacts,
    preflight_bootstrap_installation,
)


def test_foundational_suite_construction_covers_required_domains_and_boundaries():
    curriculum = build_foundational_curriculum_v1()
    modules = curriculum["modules"]
    quality = validate_foundational_curriculum_quality(curriculum)

    assert quality["accepted"] is True
    assert len(modules) in EXPECTED_MODULE_RANGE
    assert set(quality["domains"]) == set(DOMAINS)
    assert all(count > 0 for count in quality["domains"].values())
    assert len({module["module_id"] for module in modules}) == len(modules)
    assert len({(module["domain"], module["title"]) for module in modules}) == len(modules)
    assert all(module["origin"] == "operator_installed_bootstrap" for module in modules)
    assert all(module["authored_by"] == "codex" for module in modules)
    assert all(module["learned_by_delta"] is False for module in modules)
    assert all(module["behaviorally_validated"] is False for module in modules)
    assert all(module["trusted_admission"] is False for module in modules)
    assert all(module["capability_promotion"] is False for module in modules)
    assert all(module["scope_limits"] for module in modules)
    assert all(module["verification_methods"] for module in modules)
    assert all(module["source_bindings"] for module in modules)
    assert "operator_authored_framework" in quality["source_binding_breakdown"]
    assert "python_official_documentation" in quality["source_binding_breakdown"]


def test_foundational_graph_integrity_and_cross_domain_links():
    curriculum = build_foundational_curriculum_v1()
    modules = curriculum["modules"]
    relationships = curriculum["relationships"]
    module_ids = {module["module_id"] for module in modules}
    roots = set(curriculum["roots"])
    quality = validate_foundational_curriculum_quality(curriculum)
    semantic_edges = {(item["source_module_id"], item["relationship_type"], item["target_module_id"]) for item in relationships}

    assert len(relationships) in EXPECTED_RELATIONSHIP_RANGE
    assert len(semantic_edges) == len(relationships)
    assert all(relationship["source_module_id"] in module_ids and relationship["target_module_id"] in module_ids for relationship in relationships)
    assert quality["root_count"] == len(DOMAINS)
    assert quality["cross_domain_relationship_count"] >= 12
    assert quality["accepted"] is True
    incoming_support = {
        relationship["target_module_id"]
        for relationship in relationships
        if relationship["relationship_type"] in {"requires", "enables"}
    }
    assert all(module["module_id"] in roots or module["module_id"] in incoming_support for module in modules)
    by_title = {module["title"]: module["module_id"] for module in modules}
    required_links = (
        ("Evidence sufficiency and semantic support", "requires", "Claim evidence and support types"),
        ("Revision after failure", "requires", "Feedback interpretation and progress monitoring"),
        ("Booleans and conditions", "requires", "Logical operators"),
        ("CSV tabular parsing", "requires", "Tabular data"),
        ("Schema validation in Python", "requires", "Validation rules"),
        ("Comparison and falsification", "requires", "Hypotheses variables and controls"),
        ("Evidence grounded question answering", "requires", "Source provenance and source artifacts"),
    )
    for source, relationship_type, target in required_links:
        assert (by_title[source], relationship_type, by_title[target]) in semantic_edges


def test_foundational_curriculum_installs_replays_and_restarts_from_tmp_root(tmp_path):
    root = tmp_path / "bootstrap-c-root"
    result = install_foundational_curriculum_v1(artifact_root=root, reset=True)
    manifest = result["installed"]["curriculum_manifest"]

    assert result["status"] == "installed"
    assert manifest["version"] == 1
    assert manifest["module_count"] == result["quality"]["module_count"]
    assert manifest["relationship_count"] == result["quality"]["relationship_count"]
    assert result["loaded"]["manifest"]["artifact_digest"] == manifest["artifact_digest"]
    assert result["replay"]["curriculum_manifest"]["artifact_digest"] == manifest["artifact_digest"]
    assert result["discovered"] == (manifest["curriculum_id"],)
    assert result["incomplete"] == ()
    assert result["validation_record_count"] == 0
    assert result["competence_record_count"] == 0

    restarted = load_bootstrap_curriculum_artifacts(artifact_root=root, curriculum_id=manifest["curriculum_id"])
    assert restarted["manifest"]["artifact_digest"] == manifest["artifact_digest"]
    assert list_installed_bootstrap_curricula(artifact_root=root) == (manifest["curriculum_id"],)

    orphan = root / BOOTSTRAP_TEMP_DIRECTORY / "orphan.tmp"
    orphan.mkdir(parents=True)
    assert discover_incomplete_bootstrap_installations(artifact_root=root) == ("orphan.tmp",)
    assert list_installed_bootstrap_curricula(artifact_root=root) == (manifest["curriculum_id"],)


def test_foundational_installation_preserves_governance_boundaries_and_reorder_determinism(tmp_path):
    curriculum = build_foundational_curriculum_v1()
    preflight = preflight_bootstrap_installation(curriculum["request"])
    first = install_bootstrap_curriculum(artifact_root=tmp_path, request=curriculum["request"])
    reversed_request = {
        **curriculum["request"],
        "modules": tuple(reversed(tuple(curriculum["request"]["modules"]))),
        "relationships": tuple(reversed(tuple(curriculum["request"]["relationships"]))),
    }
    second = install_bootstrap_curriculum(artifact_root=tmp_path, request=reversed_request)
    loaded = load_bootstrap_curriculum_artifacts(
        artifact_root=tmp_path,
        curriculum_id=first["curriculum_manifest"]["curriculum_id"],
    )

    assert preflight["accepted"] is True
    assert first["curriculum_manifest"]["artifact_digest"] == second["curriculum_manifest"]["artifact_digest"]
    assert all(module["learned_by_delta"] is False for module in loaded["modules"])
    assert all(module["behaviorally_validated"] is False for module in loaded["modules"])
    assert all(module["trusted_admission"] is False for module in loaded["modules"])
    assert all(module["capability_promotion"] is False for module in loaded["modules"])
    assert not (tmp_path / BOOTSTRAP_VALIDATION_DIRECTORY).exists()
    assert not (tmp_path / BOOTSTRAP_COMPETENCE_DIRECTORY).exists()


def test_foundational_default_installation_root_is_disposable_tmp():
    assert INSTALLATION_ROOT.parts[0] == ".tmp"
    if INSTALLATION_ROOT.exists():
        shutil.rmtree(INSTALLATION_ROOT)
    result = install_foundational_curriculum_v1(reset=True)
    manifest = result["installed"]["curriculum_manifest"]
    assert result["status"] == "installed"
    assert list_installed_bootstrap_curricula(artifact_root=INSTALLATION_ROOT) == (manifest["curriculum_id"],)
