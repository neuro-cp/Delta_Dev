from __future__ import annotations

import json
from pathlib import Path

from orchestration.bootstrap_curriculum.foundational_curriculum_v1 import install_foundational_curriculum_v1
from orchestration.runtime.bootstrap_retrieval import (
    BOOTSTRAP_PACKET_SCHEMA,
    BOOTSTRAP_RETRIEVAL_REQUEST_SCHEMA,
    make_bootstrap_retrieval_request,
    resolve_bootstrap_context,
    retrieve_bootstrap_context,
)
from orchestration.runtime.developmental_bootstrap import (
    BOOTSTRAP_COMPETENCE_DIRECTORY,
    BOOTSTRAP_VALIDATION_DIRECTORY,
    bootstrap_digest,
    load_bootstrap_curriculum_artifacts,
    make_bootstrap_validation_record,
    make_validated_bootstrap_competence,
    write_bootstrap_artifact,
)


CURRICULUM_ID = "governed-bootstrap-curriculum-c2dfed25e709d188"


def _install_root(tmp_path: Path) -> Path:
    root = tmp_path / "bootstrap-d-curriculum"
    install_foundational_curriculum_v1(artifact_root=root, reset=True)
    return root


def _request(objective: str, *, max_depth: int = 6, max_results: int = 4, max_modules: int = 24, max_total_chars: int = 40000) -> dict:
    return make_bootstrap_retrieval_request(
        objective=objective,
        curriculum_id=CURRICULUM_ID,
        curriculum_version=1,
        max_results=max_results,
        max_traversal_depth=max_depth,
        max_packet_modules=max_modules,
        max_total_chars=max_total_chars,
    )


def _titles(root: Path) -> dict[str, str]:
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=root, curriculum_id=CURRICULUM_ID)
    return {module["module_id"]: module["title"] for module in loaded["modules"]}


def _selected_titles(root: Path, result: dict) -> tuple[str, ...]:
    titles = _titles(root)
    return tuple(titles[module_id] for module_id in result["selected_modules"])


def test_exact_retrieval_matches_foundational_modules(tmp_path):
    root = _install_root(tmp_path)

    csv = retrieve_bootstrap_context(curriculum_root=root, request=_request("CSV parsing"))
    json_records = retrieve_bootstrap_context(curriculum_root=root, request=_request("JSON records"))
    goal = retrieve_bootstrap_context(curriculum_root=root, request=_request("goal decomposition"))
    percentage = retrieve_bootstrap_context(curriculum_root=root, request=_request("percentage reasoning"))

    assert _titles(root)[csv["direct_matches"][0]["module_id"]] == "CSV tabular parsing"
    assert {"JSON serialization", "Records fields and schemas", "Serialization and parsing"}.issubset(set(_selected_titles(root, json_records)))
    assert _titles(root)[goal["direct_matches"][0]["module_id"]] == "Goal decomposition and prerequisite discovery"
    assert _titles(root)[percentage["direct_matches"][0]["module_id"]] == "Fractions ratios and percentages"
    assert csv["schema"].endswith("_v1")
    assert csv["provider_calls"] == csv["learner_calls"] == csv["evaluator_calls"] == 0


def test_prerequisite_traversal_is_stable_bounded_and_duplicate_free(tmp_path):
    root = _install_root(tmp_path)
    csv = retrieve_bootstrap_context(curriculum_root=root, request=_request("CSV parsing", max_depth=8))
    json_records = retrieve_bootstrap_context(curriculum_root=root, request=_request("JSON records", max_depth=8))
    state_machines = retrieve_bootstrap_context(curriculum_root=root, request=_request("Python state machines", max_depth=8))

    csv_titles = set(_selected_titles(root, csv))
    assert {"Values types strings and numbers", "Paths and file reading", "Records fields and schemas", "Serialization and parsing", "CSV tabular parsing", "Tabular data"}.issubset(csv_titles)
    json_titles = set(_selected_titles(root, json_records))
    assert {"Values types strings and numbers", "Records fields and schemas", "Serialization and parsing", "Hierarchical data", "JSON serialization"}.issubset(json_titles)
    state_titles = set(_selected_titles(root, state_machines))
    assert {"Queued active blocked and completed states", "Booleans and conditions", "Sequence ordering and state machines", "Terminal states and integrity stops"}.issubset(state_titles)
    assert len(csv["selected_modules"]) == len(set(csv["selected_modules"]))
    assert csv["selected_modules"] == retrieve_bootstrap_context(curriculum_root=root, request=_request("CSV parsing", max_depth=8))["selected_modules"]
    shallow = retrieve_bootstrap_context(curriculum_root=root, request=_request("CSV parsing", max_depth=1))
    assert len(shallow["prerequisite_modules"]) < len(csv["prerequisite_modules"])


def test_cross_domain_retrieval_paths(tmp_path):
    root = _install_root(tmp_path)
    schema_validation = retrieve_bootstrap_context(curriculum_root=root, request=_request("CSV schema validation", max_depth=8))
    evidence_qa = retrieve_bootstrap_context(curriculum_root=root, request=_request("evidence-grounded question answering", max_depth=8))
    revision = retrieve_bootstrap_context(curriculum_root=root, request=_request("revision after failure", max_depth=8))

    assert {"Schema validation in Python", "Booleans and conditions", "Records fields and schemas", "Validation rules"}.issubset(set(_selected_titles(root, schema_validation)))
    assert {"Evidence grounded question answering", "Source provenance and source artifacts", "Summarization and scoped explanation"}.issubset(set(_selected_titles(root, evidence_qa)))
    assert {"Revision after failure", "Feedback interpretation and progress monitoring"}.issubset(set(_selected_titles(root, revision)))


def test_validation_classification_remains_distinct_from_learning_or_trust(tmp_path):
    root = _install_root(tmp_path)
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=root, curriculum_id=CURRICULUM_ID)
    module = next(item for item in loaded["modules"] if item["title"] == "CSV tabular parsing")

    baseline = retrieve_bootstrap_context(curriculum_root=root, request=_request("CSV parsing"))
    baseline_class = next(item for item in baseline["classifications"] if item["module_id"] == module["module_id"])
    assert baseline_class["validation_state_label"] == "installed_unvalidated_bootstrap"
    assert baseline_class["curriculum_coverage"] is True
    assert baseline_class["eligible_as_study_material"] is True
    assert baseline_class["eligible_as_demonstrated_prerequisite"] is False
    assert baseline_class["unresolved_as_demonstrated_competence"] is True
    assert module["module_id"] in baseline["covered_by_installed_study_material"]
    assert module["module_id"] in baseline["unresolved_as_demonstrated_competence"]
    assert module["module_id"] not in baseline["covered_by_validated_bootstrap_competence"]
    assert baseline["missing_from_curriculum"] == ()

    validation = make_bootstrap_validation_record(
        module_id=module["module_id"],
        module_digest=module["artifact_digest"],
        outcome="bootstrap_validation_passed",
        evaluator_package_digest="sealed-fixture",
        evaluation_digest="evaluation-fixture",
    )
    write_bootstrap_artifact(
        artifact_root=root,
        directory=BOOTSTRAP_VALIDATION_DIRECTORY,
        artifact_id=validation["validation_id"],
        payload=validation,
    )
    with_validation = retrieve_bootstrap_context(curriculum_root=root, request=_request("CSV parsing"))
    validation_class = next(item for item in with_validation["classifications"] if item["module_id"] == module["module_id"])
    assert validation_class["validation_outcomes"] == ("bootstrap_validation_passed",)
    assert validation_class["validation_state_label"] == "installed_unvalidated_bootstrap"
    assert validation_class["eligible_as_demonstrated_prerequisite"] is False
    assert module["module_id"] in with_validation["unresolved_as_demonstrated_competence"]

    competence = make_validated_bootstrap_competence(module=module, validation=validation)
    write_bootstrap_artifact(
        artifact_root=root,
        directory=BOOTSTRAP_COMPETENCE_DIRECTORY,
        artifact_id=competence["competence_id"],
        payload=competence,
    )
    with_competence = retrieve_bootstrap_context(
        curriculum_root=root,
        request=_request("CSV parsing"),
        autonomously_learned=({"concept": "CSV parsing", "state": "autonomously_learned_competence"},),
    )
    competence_class = next(item for item in with_competence["classifications"] if item["module_id"] == module["module_id"])
    assert competence_class["validation_state_label"] == "validated_bootstrap_competence"
    assert competence_class["learned_by_delta"] is False
    assert competence_class["behaviorally_validated"] is True
    assert competence_class["eligible_as_demonstrated_prerequisite"] is True
    assert competence_class["unresolved_as_demonstrated_competence"] is False
    assert module["module_id"] in with_competence["covered_by_validated_bootstrap_competence"]
    assert module["module_id"] not in with_competence["unresolved_as_demonstrated_competence"]
    assert with_competence["autonomously_learned_matches"] == ({"concept": "CSV parsing", "state": "autonomously_learned_competence"},)
    assert with_competence["covered_by_autonomously_learned_competence"] == ("CSV parsing",)
    assert with_competence["trusted_admissions"] == with_competence["capability_promotions"] == 0


def test_packet_safety_budgeting_and_digest_are_deterministic(tmp_path):
    root = _install_root(tmp_path)
    request = _request("CSV schema validation", max_depth=8, max_modules=3, max_total_chars=2400)
    first = retrieve_bootstrap_context(curriculum_root=root, request=request)
    second = retrieve_bootstrap_context(curriculum_root=root, request=request)
    packet = first["learner_visible_packet"]
    packet_text = json.dumps(packet, sort_keys=True)

    assert packet["schema"] == BOOTSTRAP_PACKET_SCHEMA
    assert packet["packet_digest"] == second["learner_visible_packet"]["packet_digest"]
    assert len(packet["modules"]) <= 3
    assert packet["omitted_modules"]
    assert first["covered_by_installed_study_material"]
    assert first["unresolved_as_demonstrated_competence"]
    assert "answer_key" not in packet_text
    assert "sealed_prompt" not in packet_text
    assert "scoring_rule" not in packet_text
    assert "pass_threshold" not in packet_text
    assert "trusted_admission" not in packet_text
    assert "capability_promotion" not in packet_text


def test_retrieval_is_deterministic_across_term_order_restart_and_no_mutation(tmp_path):
    root = _install_root(tmp_path)
    before = tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))
    first = retrieve_bootstrap_context(curriculum_root=root, request=_request("CSV schema validation"))
    reordered = retrieve_bootstrap_context(curriculum_root=root, request=_request("validation schema CSV"))
    repeated = retrieve_bootstrap_context(curriculum_root=root, request=_request("CSV schema validation"))
    resolved = resolve_bootstrap_context(
        runtime_root=tmp_path / "runtime",
        objective="CSV schema validation",
        curriculum_root=root,
        retrieval_policy={"curriculum_id": CURRICULUM_ID, "curriculum_version": 1, "max_traversal_depth": 6},
    )
    after = tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))

    assert first["selected_modules"] == repeated["selected_modules"]
    assert set(first["selected_modules"]) == set(reordered["selected_modules"])
    assert first["result_digest"] == repeated["result_digest"]
    assert resolved["curriculum_id"] == CURRICULUM_ID
    assert before == after
    assert first["validation_records_created"] == first["competence_records_created"] == 0
    assert first["trusted_admissions"] == first["capability_promotions"] == 0


def test_request_schema_rejects_authority_and_missing_state_is_reported(tmp_path):
    root = _install_root(tmp_path)
    request = _request("quizzacious floobnork")
    assert request["schema"] == BOOTSTRAP_RETRIEVAL_REQUEST_SCHEMA
    result = retrieve_bootstrap_context(curriculum_root=root, request=request)
    assert "quizzaciou" in result["missing_from_curriculum"]
    assert "floobnork" in result["missing_from_curriculum"]
    assert result["covered_by_installed_study_material"] == ()
    assert result["unresolved_as_demonstrated_competence"] == ()
    assert result["recommended_evidence_targets"]

    digest = bootstrap_digest({"request": request["request_digest"]})
    assert isinstance(digest, str)
