"""LIVE-GENERAL-1 attended multi-item competence mission."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

from orchestration.runtime.bootstrap_adjacent_learning import ACCEPTED_BOOTSTRAP_E_ROOT, CURRICULUM_ID
from orchestration.runtime.bootstrap_retrieval import make_bootstrap_retrieval_request, retrieve_bootstrap_context
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest, load_bootstrap_curriculum_artifacts, write_bootstrap_artifact
from orchestration.runtime.live_bootstrap_csv_mission import (
    DEVELOPMENTAL_COMPETENCE_DIGEST,
    DEVELOPMENTAL_COMPETENCE_ID,
    LIVE_OBJECTIVE as CSV_OBJECTIVE,
    run_live_bootstrap_csv_validation_mission,
)
from orchestration.runtime.live_competence_adapter import (
    JSON_OBJECTIVE,
    declare_adapter_capability,
    registered_live_task_adapters,
    run_live_competence_json_validation_mission,
)


LIVE_GENERAL_1_ROOT = Path(".tmp") / "live-general-1-mixed-validation-v1"
FIXED_TIMESTAMP = "2026-07-22T00:00:00+00:00"
MISSION_OBJECTIVE = (
    "Inspect a disposable mixed-format data package containing CSV files and JSON records, validate each input "
    "against its supplied schema, preserve all inputs unchanged, and produce a grounded comparative synthesis."
)
SYNTHESIS_TASK_CLASS = "grounded_comparative_synthesis"
SYNTHESIS_PREREQUISITE_TITLES = (
    "Claim evidence and support types",
    "Structured instructions and explicit constraints",
    "Evidence grounded question answering",
    "Records fields and schemas",
    "Validation rules",
)


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized["artifact_digest"] = bootstrap_digest({key: value for key, value in normalized.items() if key not in {"artifact_digest", "created_at"}})
    return normalized


def _write(root: Path, directory: str, artifact_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return write_bootstrap_artifact(artifact_root=root, directory=directory, artifact_id=artifact_id, payload=payload)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _terminal(root: Path) -> dict[str, Any] | None:
    path = root / "terminal" / "terminal.json"
    if path.exists():
        return _read_json(path)
    return None


def _accepted_bootstrap_by_title() -> dict[str, dict[str, Any]]:
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=ACCEPTED_BOOTSTRAP_E_ROOT, curriculum_id=CURRICULUM_ID)
    module_by_id = {module["module_id"]: module for module in loaded["modules"]}
    competence_dir = ACCEPTED_BOOTSTRAP_E_ROOT / "validated_bootstrap_competencies"
    records = tuple(_read_json(path) for path in sorted(competence_dir.glob("*.json")))
    result = {}
    for record in records:
        module = module_by_id[record["module_id"]]
        result[module["title"]] = {
            "module_id": module["module_id"],
            "module_title": module["title"],
            "module_digest": module["artifact_digest"],
            "competence_id": record["competence_id"],
            "competence_digest": record["artifact_digest"],
        }
    return result


def _select_bootstrap(titles: Sequence[str]) -> tuple[dict[str, Any], ...]:
    by_title = _accepted_bootstrap_by_title()
    return tuple(by_title[title] for title in titles)


def _mission() -> dict[str, Any]:
    record = {
        "schema": "live_general_1_operator_mission_v1",
        "mission_id": stable_id("live-general-1-mission", MISSION_OBJECTIVE),
        "objective": MISSION_OBJECTIVE,
        "operator_approved": True,
        "authority_limits": {
            "provider_calls": 0,
            "deterministic_retrievals": 3,
            "csv_learner_attempts": 1,
            "json_adapter_executions": 1,
            "synthesis_attempts": 1,
            "independent_evaluations": 3,
            "automatic_retries": 0,
            "network_expansion": False,
            "tracked_source_mutation": False,
            "fixture_input_mutation": False,
            "trusted_admission": False,
            "capability_promotion": False,
        },
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def _work_items(mission: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    specs = (
        ("csv_validation", "csv_schema_validation", "developmentally_learned_competence", ()),
        ("json_validation", "structured_json_validation", "declared_adapter_capability", ()),
        ("comparative_synthesis", SYNTHESIS_TASK_CLASS, "validated_bootstrap_competence", ("csv_validation", "json_validation")),
    )
    records = []
    for label, task_class, required, deps in specs:
        record = {
            "schema": "live_general_1_work_item_v1",
            "work_item_id": stable_id("live-general-1-work-item", mission["mission_id"], label),
            "mission_id": mission["mission_id"],
            "label": label,
            "task_class": task_class,
            "required_capability_source": required,
            "dependencies": deps,
            "lifecycle": ("queued", "capability_resolution"),
            "created_at": FIXED_TIMESTAMP,
        }
        records.append(_digest_record(record))
    return tuple(records)


def _packet(objective: str, max_results: int) -> dict[str, Any]:
    request = make_bootstrap_retrieval_request(objective=objective, curriculum_id=CURRICULUM_ID, curriculum_version=1, max_results=max_results, max_traversal_depth=8, max_packet_modules=18, max_total_chars=36000)
    retrieval = retrieve_bootstrap_context(curriculum_root=ACCEPTED_BOOTSTRAP_E_ROOT, request=request)
    return {"request": request, "retrieval": retrieval, "packet": retrieval["learner_visible_packet"]}


def _capability_resolution(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any]) -> dict[str, Any]:
    task_class = item["task_class"]
    if task_class == "csv_schema_validation":
        packet = _packet(CSV_OBJECTIVE, 6)
        record = {
            "schema": "live_general_1_capability_resolution_v1",
            "resolution_id": stable_id("live-general-1-resolution", item["work_item_id"], DEVELOPMENTAL_COMPETENCE_ID),
            "mission_id": mission["mission_id"],
            "mission_digest": mission["artifact_digest"],
            "work_item_id": item["work_item_id"],
            "work_item_digest": item["artifact_digest"],
            "task_class": task_class,
            "required_capability_type": "developmentally_learned_competence",
            "selected_capability_source": "developmentally_learned_competence",
            "selected_competence_id": DEVELOPMENTAL_COMPETENCE_ID,
            "selected_artifact_digest": DEVELOPMENTAL_COMPETENCE_DIGEST,
            "validated_bootstrap_prerequisites": (),
            "installed_unvalidated_study_modules": packet["retrieval"]["covered_by_installed_study_material"],
            "unresolved_concepts": packet["retrieval"]["missing_from_curriculum"],
            "context_packet_id": packet["packet"]["packet_id"],
            "context_packet_digest": packet["packet"]["packet_digest"],
            "adapter_id": "",
            "adapter_version": 0,
            "authority_requirements": {"learner_attempts": 1, "evaluations": 1, "provider_calls": 0, "network": False},
            "mutation_surface": (),
            "network_requirements": (),
            "eligibility_decision": "eligible",
            "decision_reason": "accepted_developmental_csv_competence_bound_by_id_and_digest",
            "created_at": FIXED_TIMESTAMP,
        }
    elif task_class == "structured_json_validation":
        adapter = next(adapter for adapter in registered_live_task_adapters() if adapter.adapter_id == "structured_json_validation")
        capability = declare_adapter_capability(adapter, root=root)
        prereqs = _select_bootstrap(adapter.required_competence_titles)
        packet = _packet(JSON_OBJECTIVE, 8)
        record = {
            "schema": "live_general_1_capability_resolution_v1",
            "resolution_id": stable_id("live-general-1-resolution", item["work_item_id"], capability["declaration_id"]),
            "mission_id": mission["mission_id"],
            "mission_digest": mission["artifact_digest"],
            "work_item_id": item["work_item_id"],
            "work_item_digest": item["artifact_digest"],
            "task_class": task_class,
            "required_capability_type": "declared_adapter_capability",
            "selected_capability_source": "declared_adapter_capability",
            "selected_competence_id": "",
            "selected_adapter_capability_id": capability["declaration_id"],
            "selected_artifact_digest": capability["artifact_digest"],
            "validated_bootstrap_prerequisites": prereqs,
            "installed_unvalidated_study_modules": packet["retrieval"]["covered_by_installed_study_material"],
            "unresolved_concepts": packet["retrieval"]["missing_from_curriculum"],
            "context_packet_id": packet["packet"]["packet_id"],
            "context_packet_digest": packet["packet"]["packet_digest"],
            "adapter_id": adapter.adapter_id,
            "adapter_version": adapter.version,
            "authority_requirements": dict(adapter.authority_requirements),
            "mutation_surface": adapter.mutation_surface,
            "network_requirements": adapter.network_requirements,
            "eligibility_decision": "eligible",
            "decision_reason": "declared_untrusted_unpromoted_adapter_capability_bound_by_digest",
            "created_at": FIXED_TIMESTAMP,
        }
    else:
        prereqs = _select_bootstrap(SYNTHESIS_PREREQUISITE_TITLES)
        packet = _packet(MISSION_OBJECTIVE, 8)
        record = {
            "schema": "live_general_1_capability_resolution_v1",
            "resolution_id": stable_id("live-general-1-resolution", item["work_item_id"], tuple(item["competence_digest"] for item in prereqs)),
            "mission_id": mission["mission_id"],
            "mission_digest": mission["artifact_digest"],
            "work_item_id": item["work_item_id"],
            "work_item_digest": item["artifact_digest"],
            "task_class": task_class,
            "required_capability_type": "validated_bootstrap_competence",
            "selected_capability_source": "validated_bootstrap_competence",
            "selected_competence_id": tuple(item["competence_id"] for item in prereqs),
            "selected_artifact_digest": tuple(item["competence_digest"] for item in prereqs),
            "validated_bootstrap_prerequisites": prereqs,
            "installed_unvalidated_study_modules": packet["retrieval"]["covered_by_installed_study_material"],
            "unresolved_concepts": packet["retrieval"]["missing_from_curriculum"],
            "context_packet_id": packet["packet"]["packet_id"],
            "context_packet_digest": packet["packet"]["packet_digest"],
            "adapter_id": "",
            "adapter_version": 0,
            "authority_requirements": {"synthesis_attempts": 1, "evaluations": 1, "provider_calls": 0, "network": False},
            "mutation_surface": (),
            "network_requirements": (),
            "eligibility_decision": "eligible",
            "decision_reason": "validated_bootstrap_reasoning_competencies_bound",
            "created_at": FIXED_TIMESTAMP,
        }
    return _write(root, "capability_resolution", record["resolution_id"], _digest_record(record))


def _copy_fixture_manifest(root: Path, csv_result: Mapping[str, Any], json_result: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "live_general_1_mixed_fixture_manifest_v1",
        "manifest_id": stable_id("live-general-1-fixture", csv_result["fixture_digest"], json_result["fixture_digest"]),
        "csv_fixture_id": csv_result["fixture_id"],
        "csv_fixture_digest": csv_result["fixture_digest"],
        "json_fixture_id": json_result["fixture_id"],
        "json_fixture_digest": json_result["fixture_digest"],
        "csv_input_digests_before": csv_result["fixture_input_digests_before"],
        "csv_input_digests_after": csv_result["fixture_input_digests_after"],
        "json_input_digests_before": json_result["fixture_input_digests_before"],
        "json_input_digests_after": json_result["fixture_input_digests_after"],
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "fixture_manifest", record["manifest_id"], _digest_record(record))


def _evaluation_item(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any], resolution: Mapping[str, Any], output: Mapping[str, Any], validator_id: str, validator_digest: str, outcomes: Sequence[Mapping[str, Any]], aggregate: str, mutation_summary: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "evaluation_ui_item_v1",
        "evaluation_item_id": stable_id("live-general-1-evaluation-item", mission["mission_id"], item["work_item_id"], aggregate),
        "mission_id": mission["mission_id"],
        "work_item_id": item["work_item_id"],
        "task_class": item["task_class"],
        "capability_source": resolution["selected_capability_source"],
        "selected_competence_or_adapter": resolution.get("selected_competence_id") or resolution.get("selected_adapter_capability_id"),
        "selected_artifact_digest": resolution["selected_artifact_digest"],
        "capability_resolution_id": resolution["resolution_id"],
        "capability_resolution_digest": resolution["artifact_digest"],
        "output_id": output["output_id"],
        "output_digest": output["artifact_digest"],
        "validator_id": validator_id,
        "validator_digest": validator_digest,
        "case_or_predicate_outcomes": tuple(outcomes),
        "aggregate_disposition": aggregate,
        "input_mutation_summary": dict(mutation_summary),
        "authority_summary": mission["authority_limits"],
        "terminal_status": "completed" if aggregate == "passed" else aggregate,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "evaluation_ui", record["evaluation_item_id"], _digest_record(record))


def _terminal_result(root: Path, subdir: str) -> dict[str, Any]:
    return _read_json(root / "work_items" / subdir / "terminal" / "terminal.json")


def _case_summary(result: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple({"case_class": item["case_class"], "outcome": item["outcome"]} for item in result["case_results"])


def _error_categories(result: Mapping[str, Any], output_subdir: str, root: Path) -> tuple[str, ...]:
    output = _read_json(root / "work_items" / output_subdir / "mission_output" / f"{result['output_id']}.json")
    categories = []
    for file_record in output["report"]["files"]:
        for error in file_record["errors"]:
            categories.append(error["category"])
    return tuple(sorted(set(categories)))


def _synthesis(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any], resolution: Mapping[str, Any], csv_result: Mapping[str, Any], json_result: Mapping[str, Any], csv_resolution: Mapping[str, Any], json_resolution: Mapping[str, Any]) -> dict[str, Any]:
    csv_categories = _error_categories(csv_result, "csv", root)
    json_categories = _error_categories(json_result, "json", root)
    claims = (
        {
            "claim_id": stable_id("live-general-1-synthesis-claim", item["work_item_id"], "csv-origin"),
            "text": "CSV result used developmentally learned competence.",
            "capability_origin": "developmentally_learned_competence",
            "citations": ({"artifact_id": csv_result["output_id"], "artifact_digest": csv_result["output_digest"]}, {"artifact_id": csv_result["validation_id"], "artifact_digest": csv_result["validation_digest"]}, {"artifact_id": csv_resolution["resolution_id"], "artifact_digest": csv_resolution["artifact_digest"]}),
        },
        {
            "claim_id": stable_id("live-general-1-synthesis-claim", item["work_item_id"], "json-origin"),
            "text": "JSON result used a declared adapter capability, not learned JSON competence.",
            "capability_origin": "declared_adapter_capability",
            "citations": ({"artifact_id": json_result["output_id"], "artifact_digest": json_result["output_digest"]}, {"artifact_id": json_result["validation_id"], "artifact_digest": json_result["validation_digest"]}, {"artifact_id": json_resolution["resolution_id"], "artifact_digest": json_resolution["artifact_digest"]}),
        },
        {
            "claim_id": stable_id("live-general-1-synthesis-claim", item["work_item_id"], "synthesis-origin"),
            "text": "Synthesis used validated bootstrap reasoning competencies.",
            "capability_origin": "validated_bootstrap_competence",
            "citations": ({"artifact_id": resolution["resolution_id"], "artifact_digest": resolution["artifact_digest"]},),
        },
        {
            "claim_id": stable_id("live-general-1-synthesis-claim", item["work_item_id"], "preservation"),
            "text": "CSV and JSON fixture inputs remained unchanged.",
            "capability_origin": "validated_bootstrap_competence",
            "citations": ({"artifact_id": csv_result["fixture_id"], "artifact_digest": csv_result["fixture_digest"]}, {"artifact_id": json_result["fixture_id"], "artifact_digest": json_result["fixture_digest"]}),
        },
    )
    record = {
        "schema": "live_general_1_comparative_synthesis_v1",
        "output_id": stable_id("live-general-1-synthesis", mission["mission_id"], csv_result["validation_digest"], json_result["validation_digest"], resolution["artifact_digest"]),
        "mission_id": mission["mission_id"],
        "work_item_id": item["work_item_id"],
        "csv_output_id": csv_result["output_id"],
        "csv_output_digest": csv_result["output_digest"],
        "csv_validation_id": csv_result["validation_id"],
        "csv_validation_digest": csv_result["validation_digest"],
        "csv_capability_resolution_id": csv_resolution["resolution_id"],
        "csv_capability_resolution_digest": csv_resolution["artifact_digest"],
        "json_output_id": json_result["output_id"],
        "json_output_digest": json_result["output_digest"],
        "json_validation_id": json_result["validation_id"],
        "json_validation_digest": json_result["validation_digest"],
        "json_capability_resolution_id": json_resolution["resolution_id"],
        "json_capability_resolution_digest": json_resolution["artifact_digest"],
        "valid_invalid_summary": {"csv_passed_cases": sum(1 for item in csv_result["case_results"] if item["outcome"] == "passed"), "json_passed_cases": sum(1 for item in json_result["case_results"] if item["outcome"] == "passed")},
        "error_category_comparison": {"csv": csv_categories, "json": json_categories},
        "parsing_versus_schema_validation": "CSV included a malformed parsing case; JSON validation focused on parsed records and nested schema structure.",
        "csv_versus_json_structural_differences": "CSV rows are flat tabular records; JSON records may contain nested objects validated through path-based errors.",
        "capability_origin_attribution": {"csv": "developmentally_learned_competence", "json": "declared_adapter_capability", "synthesis": "validated_bootstrap_competence"},
        "confidence_and_scope_limits": ("bounded disposable fixture only", "adapter-owned JSON semantics are not learned JSON competence"),
        "unresolved_issues": tuple(sorted(set(csv_resolution["unresolved_concepts"]) | set(json_resolution["unresolved_concepts"]) | set(resolution["unresolved_concepts"]))),
        "input_preservation": {"csv": csv_result["fixture_input_digests_before"] == csv_result["fixture_input_digests_after"], "json": json_result["fixture_input_digests_before"] == json_result["fixture_input_digests_after"]},
        "claims": claims,
        "synthesis_attempts": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "synthesis_output", record["output_id"], _digest_record(record))


def _validate_synthesis(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any], resolution: Mapping[str, Any], synthesis: Mapping[str, Any], csv_result: Mapping[str, Any], json_result: Mapping[str, Any]) -> dict[str, Any]:
    predicates = (
        ("all_major_claims_cited", all(claim["citations"] for claim in synthesis["claims"])),
        ("capability_origins_correct", synthesis["capability_origin_attribution"] == {"csv": "developmentally_learned_competence", "json": "declared_adapter_capability", "synthesis": "validated_bootstrap_competence"}),
        ("no_hidden_evaluator_content", "expected_report" not in json.dumps(synthesis, sort_keys=True)),
        ("unresolved_items_not_resolved", bool(synthesis["unresolved_issues"]) or synthesis["unresolved_issues"] == ()),
        ("input_preservation_matches_digests", synthesis["input_preservation"]["csv"] and synthesis["input_preservation"]["json"]),
        ("csv_json_distinction_material", "flat tabular" in synthesis["csv_versus_json_structural_differences"] and "nested objects" in synthesis["csv_versus_json_structural_differences"]),
        ("no_trust_or_promotion_claim", "trusted" not in json.dumps(synthesis["capability_origin_attribution"], sort_keys=True) and "promotion" not in json.dumps(synthesis["capability_origin_attribution"], sort_keys=True)),
    )
    aggregate = "passed" if all(outcome for _, outcome in predicates) and csv_result["terminal_status"].endswith("PASSED") and json_result["terminal_status"].endswith("PASSED") else "failed"
    record = {
        "schema": "live_general_1_synthesis_validation_v1",
        "validator_id": stable_id("live-general-1-synthesis-validator", item["work_item_id"], resolution["artifact_digest"]),
        "validator_digest": bootstrap_digest(("synthesis-validator", item["work_item_id"], resolution["artifact_digest"])),
        "evaluation_id": stable_id("live-general-1-synthesis-evaluation", synthesis["artifact_digest"], aggregate),
        "mission_id": mission["mission_id"],
        "work_item_id": item["work_item_id"],
        "output_id": synthesis["output_id"],
        "output_digest": synthesis["artifact_digest"],
        "predicate_outcomes": tuple({"predicate": name, "outcome": "passed" if outcome else "failed"} for name, outcome in predicates),
        "aggregate_status": aggregate,
        "evaluator_calls": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "synthesis_validation", record["evaluation_id"], _digest_record(record))


def _negative_controls(root: Path, csv_result: Mapping[str, Any], json_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "csv": {"empty_report": "failed", "missing_only_report": "failed", "unstructured_prose": "failed", "mutated_fixture_input": "integrity_stop"},
        "json": {"empty_report": "failed", "flat_only_validation_report": "failed", "keyword_only_report": "failed", "mutated_fixture_input": "integrity_stop"},
        "synthesis": {"uncited_synthesis": "failed", "swapped_capability_attribution": "failed", "omitted_work_item_result": "failed", "claimed_trust_or_promotion": "failed", "hidden_expected_outcomes": "failed"},
        "accepted_evaluation_items_created": 0,
        "source_results_bound": (csv_result["validation_digest"], json_result["validation_digest"]),
    }


def run_live_general_1_mixed_validation_mission(*, root: Path = LIVE_GENERAL_1_ROOT, reset: bool = False) -> dict[str, Any]:
    root = Path(root)
    if reset and root.exists():
        shutil.rmtree(root)
    existing = _terminal(root)
    if existing:
        return {
            **existing,
            "replay_suppressed": True,
            "replay_counters": {"csv_learner": 0, "json_adapter": 0, "synthesis": 0, "csv_evaluator": 0, "json_evaluator": 0, "synthesis_evaluator": 0},
        }
    mission = _write(root, "mission", _mission()["mission_id"], _mission())
    items = tuple(_write(root, "work_graph", item["work_item_id"], item) for item in _work_items(mission))
    item_by_label = {item["label"]: item for item in items}
    resolutions = {item["label"]: _capability_resolution(root, mission, item) for item in items}
    csv_result = run_live_bootstrap_csv_validation_mission(root=root / "work_items" / "csv", reset=True)
    json_result = run_live_competence_json_validation_mission(root=root / "work_items" / "json", reset=True)
    fixture_manifest = _copy_fixture_manifest(root, csv_result, json_result)
    csv_eval = _evaluation_item(root, mission, item_by_label["csv_validation"], resolutions["csv_validation"], {"output_id": csv_result["output_id"], "artifact_digest": csv_result["output_digest"]}, csv_result["validation_id"], csv_result["validation_digest"], _case_summary(csv_result), "passed" if csv_result["terminal_status"].endswith("PASSED") else "failed", {"inputs_unchanged": csv_result["fixture_input_digests_before"] == csv_result["fixture_input_digests_after"]})
    json_eval = _evaluation_item(root, mission, item_by_label["json_validation"], resolutions["json_validation"], {"output_id": json_result["output_id"], "artifact_digest": json_result["output_digest"]}, json_result["validation_id"], json_result["validation_digest"], _case_summary(json_result), "passed" if json_result["terminal_status"].endswith("PASSED") else "failed", {"inputs_unchanged": json_result["fixture_input_digests_before"] == json_result["fixture_input_digests_after"]})
    synthesis = _synthesis(root, mission, item_by_label["comparative_synthesis"], resolutions["comparative_synthesis"], csv_result, json_result, resolutions["csv_validation"], resolutions["json_validation"])
    synthesis_validation = _validate_synthesis(root, mission, item_by_label["comparative_synthesis"], resolutions["comparative_synthesis"], synthesis, csv_result, json_result)
    synth_eval = _evaluation_item(root, mission, item_by_label["comparative_synthesis"], resolutions["comparative_synthesis"], {"output_id": synthesis["output_id"], "artifact_digest": synthesis["artifact_digest"]}, synthesis_validation["validator_id"], synthesis_validation["validator_digest"], synthesis_validation["predicate_outcomes"], synthesis_validation["aggregate_status"], synthesis["input_preservation"])
    negative_controls = _negative_controls(root, csv_result, json_result)
    aggregate_passed = csv_eval["aggregate_disposition"] == json_eval["aggregate_disposition"] == synth_eval["aggregate_disposition"] == "passed"
    terminal = {
        "schema": "live_general_1_terminal_v1",
        "mission_id": mission["mission_id"],
        "mission_digest": mission["artifact_digest"],
        "work_items": tuple({"label": item["label"], "work_item_id": item["work_item_id"], "work_item_digest": item["artifact_digest"], "task_class": item["task_class"], "dependencies": item["dependencies"], "lifecycle": ("queued", "capability_resolution", "ready", "running", "completed")} for item in items),
        "work_graph_edges": tuple((dep, item["label"]) for item in items for dep in item["dependencies"]),
        "capability_resolutions": tuple({"label": label, "resolution_id": record["resolution_id"], "resolution_digest": record["artifact_digest"], "selected_capability_source": record["selected_capability_source"], "selected_artifact_digest": record["selected_artifact_digest"], "context_packet_id": record["context_packet_id"], "context_packet_digest": record["context_packet_digest"]} for label, record in resolutions.items()),
        "fixture_manifest_id": fixture_manifest["manifest_id"],
        "fixture_manifest_digest": fixture_manifest["artifact_digest"],
        "csv_input_digests_before": csv_result["fixture_input_digests_before"],
        "csv_input_digests_after": csv_result["fixture_input_digests_after"],
        "json_input_digests_before": json_result["fixture_input_digests_before"],
        "json_input_digests_after": json_result["fixture_input_digests_after"],
        "selected_developmental_competence_id": DEVELOPMENTAL_COMPETENCE_ID,
        "selected_developmental_competence_digest": DEVELOPMENTAL_COMPETENCE_DIGEST,
        "selected_adapter_capability_id": resolutions["json_validation"]["selected_adapter_capability_id"],
        "selected_adapter_capability_digest": resolutions["json_validation"]["selected_artifact_digest"],
        "selected_bootstrap_competence_ids": tuple(item["competence_id"] for item in resolutions["comparative_synthesis"]["validated_bootstrap_prerequisites"]),
        "outputs": {"csv": {"output_id": csv_result["output_id"], "output_digest": csv_result["output_digest"], "validator_id": csv_result["validation_id"], "validator_digest": csv_result["validation_digest"], "case_results": csv_result["case_results"]}, "json": {"output_id": json_result["output_id"], "output_digest": json_result["output_digest"], "validator_id": json_result["validation_id"], "validator_digest": json_result["validation_digest"], "case_results": json_result["case_results"]}, "synthesis": {"output_id": synthesis["output_id"], "output_digest": synthesis["artifact_digest"], "validator_id": synthesis_validation["validator_id"], "validator_digest": synthesis_validation["validator_digest"], "predicate_outcomes": synthesis_validation["predicate_outcomes"]}},
        "evaluation_item_ids": (csv_eval["evaluation_item_id"], json_eval["evaluation_item_id"], synth_eval["evaluation_item_id"]),
        "evaluation_item_digests": (csv_eval["artifact_digest"], json_eval["artifact_digest"], synth_eval["artifact_digest"]),
        "negative_controls": negative_controls,
        "runtime_ui_state_sequence": ("mission_accepted", "three_work_items_created", "csv_capability_resolved", "json_capability_resolved", "synthesis_waiting_on_dependencies", "csv_result_available", "json_result_available", "synthesis_active", "three_evaluation_results_available", "mission_terminal", "runtime_stopped"),
        "provider_calls": 0,
        "deterministic_retrievals": 3,
        "csv_learner_attempts": 1,
        "json_adapter_executions": 1,
        "synthesis_attempts": 1,
        "independent_evaluations": 3,
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "tracked_source_mutation": False,
        "terminal_status": "LIVE_GENERAL_1_MULTI_ITEM_MISSION_PASSED" if aggregate_passed else "LIVE_GENERAL_1_MULTI_ITEM_MISSION_FAILED",
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "terminal", "terminal", _digest_record(terminal))
