from __future__ import annotations

import json

import pytest

from orchestration.runtime.developmental_bootstrap import (
    BOOTSTRAP_COMPETENCE_DIRECTORY,
    BOOTSTRAP_CURRICULUM_DIRECTORY,
    BOOTSTRAP_MODULE_DIRECTORY,
    BOOTSTRAP_RELATIONSHIP_DIRECTORY,
    BOOTSTRAP_TEMP_DIRECTORY,
    BOOTSTRAP_VALIDATION_DIRECTORY,
    BootstrapContractError,
    discover_incomplete_bootstrap_installations,
    install_bootstrap_curriculum,
    list_installed_bootstrap_curricula,
    load_bootstrap_curriculum_artifacts,
    make_bootstrap_installation_request,
    make_bootstrap_module,
    make_bootstrap_relationship,
    preflight_bootstrap_installation,
    read_bootstrap_curriculum_manifest,
    validate_bootstrap_manifest,
)


def _module(title: str, domain: str, *, prerequisites: tuple[str, ...] = ()) -> dict:
    return make_bootstrap_module(
        title=title,
        domain=domain,
        definition=f"{title} is a fixture concept for installer mechanics.",
        prerequisites=prerequisites,
        key_components=("definition", "example", "boundary"),
        worked_examples=({"prompt": f"Use {title}.", "response": f"Apply {title} with retained evidence."},),
        counterexamples=({"prompt": f"Misuse {title}.", "response": "Treat installed scaffolding as validated competence."},),
        verification_methods=("Confirm the artifact is operator installed and unvalidated.",),
        scope_limits=("Fixture content is not the real bootstrap curriculum.",),
    )


def _fixture_modules() -> tuple[dict, ...]:
    evidence = _module("Evidence versus assertion", "evidence")
    examples = _module("Examples and counterexamples", "learning")
    strings = _module("Python strings", "python")
    files = _module("Python files", "python")
    csv = _module(
        "Python CSV",
        "python",
        prerequisites=(strings["module_id"], files["module_id"]),
    )
    return evidence, examples, strings, files, csv


def _fixture_relationships(modules: tuple[dict, ...]) -> tuple[dict, ...]:
    by_title = {module["title"]: module for module in modules}
    return (
        make_bootstrap_relationship(
            source_module_id=by_title["Python CSV"]["module_id"],
            target_module_id=by_title["Python strings"]["module_id"],
            relationship_type="requires",
            rationale="CSV parsing requires string handling.",
        ),
        make_bootstrap_relationship(
            source_module_id=by_title["Python CSV"]["module_id"],
            target_module_id=by_title["Python files"]["module_id"],
            relationship_type="requires",
            rationale="CSV parsing requires file reading and writing.",
        ),
        make_bootstrap_relationship(
            source_module_id=by_title["Examples and counterexamples"]["module_id"],
            target_module_id=by_title["Evidence versus assertion"]["module_id"],
            relationship_type="enables",
            rationale="Examples help distinguish assertions from evidence.",
        ),
        make_bootstrap_relationship(
            source_module_id=by_title["Evidence versus assertion"]["module_id"],
            target_module_id=by_title["Examples and counterexamples"]["module_id"],
            relationship_type="relates_to",
            rationale="Evidence and examples are mutually clarifying.",
        ),
    )


def _request(
    *,
    modules: tuple[dict, ...] | None = None,
    relationships: tuple[dict, ...] | None = None,
    roots: tuple[str, ...] | None = None,
) -> dict:
    selected_modules = modules or _fixture_modules()
    selected_relationships = relationships or _fixture_relationships(selected_modules)
    if roots is None:
        roots = tuple(module["module_id"] for module in selected_modules if module["title"] != "Python CSV")
    return make_bootstrap_installation_request(
        title="Fixture bootstrap curriculum",
        version=1,
        modules=selected_modules,
        relationships=selected_relationships,
        prerequisite_roots=roots,
        intended_domains=tuple(sorted({module["domain"] for module in selected_modules})),
        curriculum_seed="fixture-bootstrap-curriculum",
    )


def _json_files(root, directory: str) -> tuple:
    path = root / directory
    if not path.exists():
        return ()
    return tuple(sorted(path.glob("*.json")))


def test_installer_success_publishes_modules_relationships_and_manifest_only(tmp_path):
    request = _request()

    result = install_bootstrap_curriculum(artifact_root=tmp_path, request=request)

    assert result["status"] == "installed"
    manifest = result["curriculum_manifest"]
    assert list_installed_bootstrap_curricula(artifact_root=tmp_path) == (manifest["curriculum_id"],)
    assert len(_json_files(tmp_path, BOOTSTRAP_MODULE_DIRECTORY)) == len(result["modules"])
    assert len(_json_files(tmp_path, BOOTSTRAP_RELATIONSHIP_DIRECTORY)) == len(result["relationships"])
    assert _json_files(tmp_path, BOOTSTRAP_CURRICULUM_DIRECTORY) == (
        tmp_path / BOOTSTRAP_CURRICULUM_DIRECTORY / f"{manifest['curriculum_id']}.json",
    )
    assert _json_files(tmp_path, BOOTSTRAP_VALIDATION_DIRECTORY) == ()
    assert _json_files(tmp_path, BOOTSTRAP_COMPETENCE_DIRECTORY) == ()
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=tmp_path, curriculum_id=manifest["curriculum_id"])
    assert loaded["manifest"]["artifact_digest"] == manifest["artifact_digest"]
    assert tuple((module["module_id"], module["artifact_digest"]) for module in loaded["modules"]) == tuple(manifest["module_digests"])
    assert tuple((relationship["relationship_id"], relationship["artifact_digest"]) for relationship in loaded["relationships"]) == tuple(manifest["relationship_digests"])
    assert all(module["origin"] == "operator_installed_bootstrap" for module in loaded["modules"])
    assert all(module["curriculum_id"] == manifest["curriculum_id"] for module in loaded["modules"])
    assert all(module["curriculum_version"] == manifest["version"] for module in loaded["modules"])
    assert all(not module["learned_by_delta"] and not module["behaviorally_validated"] for module in loaded["modules"])
    assert result["trusted_admissions"] == result["capability_promotions"] == 0
    assert result["validation_records_created"] == result["competence_records_created"] == 0


def test_installer_replay_and_reordered_input_are_exact_once(tmp_path):
    request = _request()
    first = install_bootstrap_curriculum(artifact_root=tmp_path, request=request)
    second = install_bootstrap_curriculum(artifact_root=tmp_path, request=request)
    reordered = _request(
        modules=tuple(reversed(tuple(request["modules"]))),
        relationships=tuple(reversed(tuple(request["relationships"]))),
        roots=tuple(reversed(tuple(request["prerequisite_roots"]))),
    )
    third = install_bootstrap_curriculum(artifact_root=tmp_path, request=reordered)

    assert first["curriculum_manifest"]["curriculum_id"] == second["curriculum_manifest"]["curriculum_id"] == third["curriculum_manifest"]["curriculum_id"]
    assert first["curriculum_manifest"]["artifact_digest"] == second["curriculum_manifest"]["artifact_digest"] == third["curriculum_manifest"]["artifact_digest"]
    assert len(_json_files(tmp_path, BOOTSTRAP_MODULE_DIRECTORY)) == len(first["modules"])
    assert len(_json_files(tmp_path, BOOTSTRAP_RELATIONSHIP_DIRECTORY)) == len(first["relationships"])
    assert len(_json_files(tmp_path, BOOTSTRAP_CURRICULUM_DIRECTORY)) == 1


def test_installer_rejects_missing_references_before_writes(tmp_path):
    modules = _fixture_modules()
    broken_prereq = {**modules[-1], "prerequisites": ("missing-module",)}
    del broken_prereq["artifact_digest"]
    missing_prereq = _request(modules=(*modules[:-1], broken_prereq))
    assert install_bootstrap_curriculum(artifact_root=tmp_path, request=missing_prereq)["status"] == "validation_failed"

    relationship = dict(_fixture_relationships(modules)[0])
    relationship["target_module_id"] = "missing-module"
    missing_endpoint = _request(modules=modules, relationships=(relationship,))
    assert install_bootstrap_curriculum(artifact_root=tmp_path, request=missing_endpoint)["status"] == "validation_failed"

    missing_root = _request(modules=modules, roots=("missing-module",))
    assert install_bootstrap_curriculum(artifact_root=tmp_path, request=missing_root)["status"] == "validation_failed"

    assert _json_files(tmp_path, BOOTSTRAP_MODULE_DIRECTORY) == ()
    assert _json_files(tmp_path, BOOTSTRAP_RELATIONSHIP_DIRECTORY) == ()
    assert _json_files(tmp_path, BOOTSTRAP_CURRICULUM_DIRECTORY) == ()


def test_installer_rejects_requires_cycle_but_allows_relates_to_cycle(tmp_path):
    first = _module("Cycle first", "graph")
    second = _module("Cycle second", "graph")
    requires_cycle = (
        make_bootstrap_relationship(source_module_id=first["module_id"], target_module_id=second["module_id"], relationship_type="requires"),
        make_bootstrap_relationship(source_module_id=second["module_id"], target_module_id=first["module_id"], relationship_type="requires"),
    )
    rejected = install_bootstrap_curriculum(
        artifact_root=tmp_path / "requires",
        request=_request(modules=(first, second), relationships=requires_cycle, roots=(first["module_id"], second["module_id"])),
    )
    assert rejected["status"] == "validation_failed"
    assert "requires_cycle_detected" in rejected["errors"]

    relates_cycle = (
        make_bootstrap_relationship(source_module_id=first["module_id"], target_module_id=second["module_id"], relationship_type="relates_to"),
        make_bootstrap_relationship(source_module_id=second["module_id"], target_module_id=first["module_id"], relationship_type="relates_to"),
    )
    accepted = install_bootstrap_curriculum(
        artifact_root=tmp_path / "relates",
        request=_request(modules=(first, second), relationships=relates_cycle, roots=(first["module_id"], second["module_id"])),
    )
    assert accepted["status"] == "installed"


def test_installer_rejects_module_relationship_and_manifest_drift(tmp_path):
    request = _request()
    install_bootstrap_curriculum(artifact_root=tmp_path, request=request)

    modules = tuple(request["modules"])
    changed_module = make_bootstrap_module(
        title=modules[0]["title"],
        domain=modules[0]["domain"],
        definition="Changed fixture content under the same module ID and version.",
    )
    with pytest.raises(BootstrapContractError, match="bootstrap_module_artifact_drift"):
        install_bootstrap_curriculum(artifact_root=tmp_path, request=_request(modules=(changed_module, *modules[1:])))

    changed_relationship = make_bootstrap_relationship(
        source_module_id=request["relationships"][0]["source_module_id"],
        target_module_id=request["relationships"][0]["target_module_id"],
        relationship_type=request["relationships"][0]["relationship_type"],
        rationale="Changed rationale under the same relationship ID.",
    )
    with pytest.raises(BootstrapContractError, match="bootstrap_relationship_artifact_drift"):
        install_bootstrap_curriculum(
            artifact_root=tmp_path,
            request=_request(modules=modules, relationships=(changed_relationship, *tuple(request["relationships"])[1:])),
        )

    manifest_path = next((tmp_path / BOOTSTRAP_CURRICULUM_DIRECTORY).glob("*.json"))
    tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered["title"] = "Tampered manifest"
    manifest_path.write_text(json.dumps(tampered, sort_keys=True), encoding="utf-8")
    with pytest.raises(BootstrapContractError, match="bootstrap_manifest_drift"):
        install_bootstrap_curriculum(artifact_root=tmp_path, request=request)


def test_installer_atomic_failures_do_not_publish_manifest_and_discovery_ignores_temp(tmp_path):
    request = _request()
    for fail_at in ("before_temp", "during_temp", "before_publication"):
        root = tmp_path / fail_at
        with pytest.raises(BootstrapContractError, match=f" injected_{fail_at}".strip()):
            install_bootstrap_curriculum(artifact_root=root, request=request, fail_at=fail_at)
        assert list_installed_bootstrap_curricula(artifact_root=root) == ()
        assert _json_files(root, BOOTSTRAP_CURRICULUM_DIRECTORY) == ()

    orphan = tmp_path / "orphaned" / BOOTSTRAP_TEMP_DIRECTORY / "fixture.tmp"
    orphan.mkdir(parents=True)
    assert discover_incomplete_bootstrap_installations(artifact_root=tmp_path / "orphaned") == ("fixture.tmp",)
    assert list_installed_bootstrap_curricula(artifact_root=tmp_path / "orphaned") == ()


def test_discovery_reports_integrity_failure_on_published_artifact_mismatch(tmp_path):
    result = install_bootstrap_curriculum(artifact_root=tmp_path, request=_request())
    manifest = result["curriculum_manifest"]
    module_path = tmp_path / BOOTSTRAP_MODULE_DIRECTORY / f"{manifest['module_ids'][0]}.json"
    tampered = json.loads(module_path.read_text(encoding="utf-8"))
    tampered["definition"] = "Digest mismatch after publication."
    module_path.write_text(json.dumps(tampered, sort_keys=True), encoding="utf-8")

    with pytest.raises(BootstrapContractError, match="bootstrap_module_digest_drift"):
        load_bootstrap_curriculum_artifacts(artifact_root=tmp_path, curriculum_id=manifest["curriculum_id"])


def test_preflight_rejects_authority_fields_and_serialization_round_trip_is_stable():
    request = _request()
    accepted = preflight_bootstrap_installation(request)
    restored = json.loads(json.dumps(accepted["manifest"], sort_keys=True))
    assert validate_bootstrap_manifest(restored, modules=accepted["modules"], relationships=accepted["relationships"])["artifact_digest"] == accepted["manifest"]["artifact_digest"]

    authority_request = {**request, "runtime_authority": {"execute": True}}
    result = preflight_bootstrap_installation(authority_request)
    assert result["accepted"] is False
    assert "installation_request_contains_runtime_or_provider_authority" in result["errors"]

    manifest = read_bootstrap_curriculum_manifest
    assert callable(manifest)
