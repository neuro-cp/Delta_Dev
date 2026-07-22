from __future__ import annotations

import json

import pytest

from orchestration.runtime.developmental_bootstrap import (
    BOOTSTRAP_STATES,
    RELATIONSHIP_TYPES,
    BootstrapContractError,
    make_bootstrap_manifest,
    make_bootstrap_module,
    make_bootstrap_relationship,
    make_bootstrap_validation_record,
    make_validated_bootstrap_competence,
    validate_bootstrap_manifest,
    validate_bootstrap_module,
    validate_bootstrap_relationship,
    validate_bootstrap_validation_record,
    validate_validated_bootstrap_competence,
    write_bootstrap_artifact,
)


def _module(title: str = "Evidence versus assertion", domain: str = "evidence") -> dict:
    return make_bootstrap_module(
        title=title,
        domain=domain,
        definition="A claim is a statement; evidence is retained support for it.",
        key_components=("claim", "evidence", "support"),
        verification_methods=("Given a statement, identify what retained source would support it.",),
        scope_limits=("Operator-installed curriculum is scaffolding, not learned competence.",),
    )


def test_bootstrap_module_is_operator_installed_not_learned_or_trusted():
    module = _module()

    assert module["origin"] == "operator_installed_bootstrap"
    assert module["state"] == "operator_installed_bootstrap"
    assert module["learned_by_delta"] is False
    assert module["behaviorally_validated"] is False
    assert module["trusted_admission"] is False
    assert module["capability_promotion"] is False
    assert "artifact_digest" in module

    tampered = {**module, "learned_by_delta": True}
    with pytest.raises(BootstrapContractError, match="governance_boundary"):
        validate_bootstrap_module(tampered)


def test_bootstrap_module_rejects_evaluator_hidden_fields_and_requires_version():
    module = _module()
    with pytest.raises(BootstrapContractError, match="evaluator_hidden"):
        validate_bootstrap_module({**module, "answer_key": {"hidden": True}})
    missing_version = dict(module)
    del missing_version["version"]
    with pytest.raises(BootstrapContractError, match="required_field"):
        validate_bootstrap_module(missing_version)


def test_bootstrap_ids_digests_and_serialization_are_deterministic(tmp_path):
    first = _module()
    second = _module()

    assert first["module_id"] == second["module_id"]
    assert first["artifact_digest"] == second["artifact_digest"]
    encoded = json.dumps(first, sort_keys=True)
    restored = validate_bootstrap_module(json.loads(encoded))
    assert restored["artifact_digest"] == first["artifact_digest"]

    written = write_bootstrap_artifact(
        artifact_root=tmp_path,
        directory="bootstrap_modules",
        artifact_id=first["module_id"],
        payload=first,
    )
    assert validate_bootstrap_module(written)["artifact_digest"] == first["artifact_digest"]
    replayed = write_bootstrap_artifact(
        artifact_root=tmp_path,
        directory="bootstrap_modules",
        artifact_id=first["module_id"],
        payload=second,
    )
    assert validate_bootstrap_module(replayed)["artifact_digest"] == first["artifact_digest"]
    drifted = {**first, "definition": "Changed content under the same module ID."}
    with pytest.raises(BootstrapContractError, match="artifact_digest_drift"):
        write_bootstrap_artifact(
            artifact_root=tmp_path,
            directory="bootstrap_modules",
            artifact_id=first["module_id"],
            payload=drifted,
        )


def test_relationship_contract_validates_type_and_missing_module_ids():
    source = _module("Source provenance")
    target = _module("Accepted excerpts")
    relationship = make_bootstrap_relationship(
        source_module_id=source["module_id"],
        target_module_id=target["module_id"],
        relationship_type="requires",
        rationale="Accepted excerpts require source provenance.",
    )

    assert relationship["relationship_type"] == "requires"
    assert relationship["trusted_admission"] is False
    assert relationship["capability_promotion"] is False
    assert "requires" in RELATIONSHIP_TYPES

    with pytest.raises(BootstrapContractError, match="relationship_type_invalid"):
        validate_bootstrap_relationship({**relationship, "relationship_type": "magically_implies"}, known_module_ids={source["module_id"], target["module_id"]})
    with pytest.raises(BootstrapContractError, match="module_missing"):
        validate_bootstrap_relationship(relationship, known_module_ids={source["module_id"]})


def test_manifest_distinguishes_installed_from_validated_and_resolves_graph():
    source = _module("Source provenance")
    target = _module("Accepted excerpts")
    relationship = make_bootstrap_relationship(
        source_module_id=source["module_id"],
        target_module_id=target["module_id"],
        relationship_type="requires",
    )
    manifest = make_bootstrap_manifest(
        title="Foundational bootstrap contracts",
        version=1,
        modules=(source, target),
        relationships=(relationship,),
    )

    assert manifest["bootstrap_installed"] is True
    assert manifest["bootstrap_validated"] is False
    assert manifest["trusted_admissions"] == manifest["capability_promotions"] == 0
    assert manifest["module_count"] == 2
    assert manifest["relationship_count"] == 1

    with pytest.raises(BootstrapContractError, match="validation_must_start_false"):
        validate_bootstrap_manifest({**manifest, "bootstrap_validated": True}, modules=(source, target), relationships=(relationship,))


def test_validation_record_and_competence_do_not_create_trusted_or_autonomous_learning():
    module = _module("CSV parsing", "python")
    validation = make_bootstrap_validation_record(
        module_id=module["module_id"],
        module_digest=module["artifact_digest"],
        outcome="bootstrap_validation_passed",
        evaluator_package_digest="sealed-digest",
        evaluation_digest="evaluation-digest",
    )
    competence = make_validated_bootstrap_competence(module=module, validation=validation)

    assert validation["trusted_admission"] is False
    assert validation["capability_promotion"] is False
    assert competence["state"] == "validated_bootstrap_competence"
    assert competence["origin"] == "operator_installed_bootstrap"
    assert competence["learned_by_delta"] is False
    assert competence["autonomously_learned"] is False
    assert competence["trusted_admission"] is False
    assert competence["capability_promotion"] is False

    with pytest.raises(BootstrapContractError, match="not_autonomously_learned"):
        validate_validated_bootstrap_competence({**competence, "learned_by_delta": True})
    with pytest.raises(BootstrapContractError, match="outcome_invalid"):
        validate_bootstrap_validation_record({**validation, "outcome": "trusted_capability"})
    incomplete = make_bootstrap_validation_record(
        module_id=module["module_id"],
        module_digest=module["artifact_digest"],
        outcome="bootstrap_validation_incomplete",
        evaluator_package_digest="sealed-digest",
        evaluation_digest="different-evaluation",
    )
    with pytest.raises(BootstrapContractError, match="requires_passed_validation"):
        make_validated_bootstrap_competence(module=module, validation=incomplete)


def test_bootstrap_state_names_are_explicit_and_not_collapsed():
    assert {
        "operator_installed_bootstrap",
        "bootstrap_available_for_study",
        "validated_bootstrap_competence",
        "autonomously_learned_competence",
        "trusted_capability",
    }.issubset(BOOTSTRAP_STATES)
