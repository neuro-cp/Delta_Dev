"""Generic attended live mission adapter registry and JSON validation mission."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any, Callable, Mapping, Sequence

from orchestration.runtime.bootstrap_adjacent_learning import ACCEPTED_BOOTSTRAP_E_ROOT, CURRICULUM_ID
from orchestration.runtime.bootstrap_retrieval import make_bootstrap_retrieval_request, retrieve_bootstrap_context
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest, load_bootstrap_curriculum_artifacts, write_bootstrap_artifact
from orchestration.runtime.live_bootstrap_csv_mission import (
    DEVELOPMENTAL_COMPETENCE_DIGEST,
    DEVELOPMENTAL_COMPETENCE_ID,
    LIVE_BOOTSTRAP_MISSION_ROOT,
    run_live_bootstrap_csv_validation_mission,
)


LIVE_COMPETENCE_ADAPTER_ROOT = Path(".tmp") / "live-bootstrap-json-validation-v1"
FIXED_TIMESTAMP = "2026-07-22T00:00:00+00:00"
JSON_TASK_CLASS = "structured_json_validation"
CSV_TASK_CLASS = "csv_schema_validation"
JSON_OBJECTIVE = (
    "Validate a disposable set of JSON records against supplied schemas, report missing fields, "
    "unexpected fields, invalid primitive types, and nested structure violations without modifying the input records."
)
JSON_PREREQUISITE_TITLES = (
    "Records fields and schemas",
    "Validation rules",
    "Lists tuples dictionaries and sets",
    "Functions parameters and return values",
    "Structured instructions and explicit constraints",
    "Claim evidence and support types",
)
JSON_CASE_CLASSES = (
    "valid_record_set",
    "missing_required_field",
    "unexpected_field",
    "invalid_integer",
    "invalid_boolean",
    "invalid_nested_object",
    "multiple_error_record",
    "optional_null",
    "malformed_json",
    "unsupported_schema_version",
    "provenance_completeness",
)
JSON_SEMANTIC_OPERATIONS = (
    "missing required field detection",
    "unexpected field detection",
    "integer validation without boolean coercion",
    "boolean validation",
    "nested object validation",
    "optional null handling",
    "multiple error accumulation",
    "deterministic error structure",
)


@dataclass(frozen=True)
class LiveTaskAdapter:
    adapter_id: str
    version: int
    supported_task_classes: tuple[str, ...]
    required_competence_titles: tuple[str, ...]
    fixture_input_contract: str
    output_contract: str
    validator_contract: str
    authority_requirements: Mapping[str, Any]
    mutation_surface: tuple[str, ...]
    network_requirements: tuple[str, ...]
    priority: int
    compatibility: Callable[[Mapping[str, Any], Mapping[str, Any]], bool]
    executor: Callable[[Path, Mapping[str, Any], bool], Mapping[str, Any]]

    def descriptor(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "version": self.version,
            "supported_task_classes": self.supported_task_classes,
            "required_competence_titles": self.required_competence_titles,
            "fixture_input_contract": self.fixture_input_contract,
            "output_contract": self.output_contract,
            "validator_contract": self.validator_contract,
            "authority_requirements": dict(self.authority_requirements),
            "mutation_surface": self.mutation_surface,
            "network_requirements": self.network_requirements,
            "priority": self.priority,
        }


class LiveAdapterBoundaryError(ValueError):
    """Raised when a live mission would cross a bounded adapter boundary."""


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized["artifact_digest"] = bootstrap_digest({key: value for key, value in normalized.items() if key not in {"artifact_digest", "created_at"}})
    return normalized


def _write(root: Path, directory: str, artifact_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return write_bootstrap_artifact(artifact_root=root, directory=directory, artifact_id=artifact_id, payload=payload)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_digest(path: Path) -> str:
    return bootstrap_digest(path.read_text(encoding="utf-8"))


def _accepted_competence_by_title() -> dict[str, dict[str, Any]]:
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=ACCEPTED_BOOTSTRAP_E_ROOT, curriculum_id=CURRICULUM_ID)
    module_by_id = {module["module_id"]: module for module in loaded["modules"]}
    title_by_id = {module["module_id"]: module["title"] for module in loaded["modules"]}
    competence_dir = ACCEPTED_BOOTSTRAP_E_ROOT / "validated_bootstrap_competencies"
    records = tuple(_read_json(path) for path in sorted(competence_dir.glob("*.json")))
    result = {}
    for record in records:
        module = module_by_id[record["module_id"]]
        result[title_by_id[record["module_id"]]] = {
            "module_id": record["module_id"],
            "module_title": module["title"],
            "module_digest": module["artifact_digest"],
            "competence_id": record["competence_id"],
            "competence_digest": record["artifact_digest"],
        }
    return result


def declare_adapter_capability(adapter: LiveTaskAdapter, *, root: Path | None = None) -> dict[str, Any]:
    if adapter.adapter_id == "structured_json_validation":
        operations = JSON_SEMANTIC_OPERATIONS
        capability_kind = "domain_semantics"
        unresolved = ("JSON semantics are adapter-owned implementation capability, not learned or trusted competence",)
        implementation_paths = ("_json_report", "_json_errors", "_type_valid")
    else:
        operations = ("adapter selection", "bounded execution", "artifact publication", "authority enforcement")
        capability_kind = "infrastructure"
        unresolved = ()
        implementation_paths = ()
    record = {
        "schema": "live_task_adapter_capability_declaration_v1",
        "declaration_id": stable_id("live-task-adapter-capability", adapter.adapter_id, adapter.version, operations),
        "adapter_id": adapter.adapter_id,
        "adapter_version": adapter.version,
        "semantic_operations_supplied": operations,
        "source_path": "orchestration/runtime/live_competence_adapter.py",
        "implementation_paths": implementation_paths,
        "test_path": "tests/runtime_gsr/test_live_competence_adapter.py",
        "authority_surface": dict(adapter.authority_requirements),
        "capability_kind": capability_kind,
        "competence_prerequisites": adapter.required_competence_titles,
        "unresolved_semantic_dependencies": unresolved,
        "validation_status": "focused_tests_passed_when_checkpointed",
        "trusted_status": False,
        "promotion_status": False,
        "adapter_selection_counts_as_competence": False,
        "created_at": FIXED_TIMESTAMP,
    }
    declared = _digest_record(record)
    if root is None:
        return declared
    return _write(Path(root), "adapter_capability", declared["declaration_id"], declared)


def _select_competence_titles(titles: Sequence[str]) -> tuple[dict[str, Any], ...]:
    by_title = _accepted_competence_by_title()
    missing = tuple(title for title in titles if title not in by_title)
    if missing:
        raise LiveAdapterBoundaryError(f"accepted_competence_missing:{','.join(missing)}")
    return tuple(by_title[title] for title in titles)


def _mission(task_class: str, objective: str, input_contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    record = {
        "schema": "live_competence_operator_approved_mission_v1",
        "mission_id": stable_id("live-competence-mission", task_class, objective, input_contract or {}),
        "task_class": task_class,
        "objective": objective,
        "input_contract": dict(input_contract or {}),
        "operator_approved": True,
        "authority_limits": {
            "provider_calls": 0,
            "retrievals": 1,
            "learner_attempts": 1,
            "evaluations": 1,
            "network": False,
            "tracked_source_mutation": False,
            "input_mutation": False,
            "credential_access": False,
        },
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def _authority_compatible(adapter: LiveTaskAdapter, mission: Mapping[str, Any]) -> bool:
    limits = mission["authority_limits"]
    requirements = adapter.authority_requirements
    return (
        int(requirements.get("provider_calls", 0)) <= int(limits["provider_calls"])
        and int(requirements.get("retrievals", 0)) <= int(limits["retrievals"])
        and int(requirements.get("learner_attempts", 0)) <= int(limits["learner_attempts"])
        and int(requirements.get("evaluations", 0)) <= int(limits["evaluations"])
        and bool(requirements.get("network", False)) is False
        and bool(requirements.get("tracked_source_mutation", False)) is False
        and bool(requirements.get("input_mutation", False)) is False
        and bool(requirements.get("credential_access", False)) is False
    )


def _csv_compatible(adapter: LiveTaskAdapter, mission: Mapping[str, Any]) -> bool:
    return mission["task_class"] in adapter.supported_task_classes and _authority_compatible(adapter, mission)


def _json_compatible(adapter: LiveTaskAdapter, mission: Mapping[str, Any]) -> bool:
    return mission["task_class"] in adapter.supported_task_classes and _authority_compatible(adapter, mission)


def _csv_executor(root: Path, _mission_record: Mapping[str, Any], reset: bool) -> Mapping[str, Any]:
    return run_live_bootstrap_csv_validation_mission(root=root or LIVE_BOOTSTRAP_MISSION_ROOT, reset=reset)


def _json_schema_records() -> dict[str, dict[str, Any]]:
    base = {
        "id": {"type": "integer", "required": True},
        "active": {"type": "boolean", "required": True},
        "profile": {"type": "object", "required": True, "schema": {"score": {"type": "integer", "required": True}}},
        "note": {"type": "string", "required": False, "nullable": True},
    }
    return {name: base for name in (
        "valid_records.json",
        "missing_required.json",
        "unexpected_field.json",
        "invalid_integer.json",
        "invalid_boolean.json",
        "invalid_nested_object.json",
        "multiple_error.json",
        "optional_null.json",
        "malformed_json.json",
    )}


def create_json_fixture(root: Path, *, reset: bool = False) -> dict[str, Any]:
    root = Path(root)
    if reset and root.exists():
        shutil.rmtree(root)
    input_dir = root / "inputs"
    schema_dir = root / "schemas"
    input_dir.mkdir(parents=True, exist_ok=True)
    schema_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "valid_records.json": [{"id": 1, "active": True, "profile": {"score": 9}, "note": "ok"}],
        "missing_required.json": [{"active": False, "profile": {"score": 3}}],
        "unexpected_field.json": [{"id": 2, "active": True, "profile": {"score": 5}, "rogue": "x"}],
        "invalid_integer.json": [{"id": "four", "active": True, "profile": {"score": 5}}],
        "invalid_boolean.json": [{"id": 4, "active": "yes", "profile": {"score": 5}}],
        "invalid_nested_object.json": [{"id": 5, "active": True, "profile": "not-object"}],
        "multiple_error.json": [{"active": "maybe", "profile": {"score": "high"}, "rogue": "x"}],
        "optional_null.json": [{"id": 7, "active": False, "profile": {"score": 0}, "note": None}],
        "unsupported_schema_version.json": [{"id": 8, "active": True, "profile": {"score": 1}}],
    }
    for name, payload in payloads.items():
        path = input_dir / name
        if not path.exists():
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    malformed = input_dir / "malformed_json.json"
    if not malformed.exists():
        malformed.write_text('[{"id": 9, "active": true, "profile": {"score": 2}}\n', encoding="utf-8")
    for name, schema in _json_schema_records().items():
        path = schema_dir / f"{name}.schema.json"
        if not path.exists():
            path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    unsupported = schema_dir / "unsupported_schema_version.json.schema.json"
    if not unsupported.exists():
        unsupported.parent.mkdir(parents=True, exist_ok=True)
        unsupported.write_text(json.dumps({"__schema_version__": "2", "fields": _json_schema_records()["valid_records.json"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    input_digests = tuple(sorted((path.name, _file_digest(path)) for path in input_dir.glob("*.json")))
    schema_digests = tuple(sorted((path.name, _file_digest(path)) for path in schema_dir.glob("*.json")))
    record = {
        "schema": "live_competence_json_fixture_v1",
        "fixture_id": stable_id("live-competence-json-fixture", input_digests, schema_digests),
        "root": str(root),
        "input_digests": input_digests,
        "schema_digests": schema_digests,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "mission_fixture", record["fixture_id"], _digest_record(record))


def _type_valid(value: Any, expected_type: str, *, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "object":
        return isinstance(value, dict)
    return False


def _json_errors(record: Mapping[str, Any], schema: Mapping[str, Mapping[str, Any]], file_name: str, row: int = 1, prefix: str = "") -> tuple[dict[str, Any], ...]:
    errors: list[dict[str, Any]] = []
    for field, spec in schema.items():
        path = f"{prefix}.{field}" if prefix else field
        if spec.get("required") and field not in record:
            errors.append({"file": file_name, "row": row, "path": path, "category": "missing_required_field", "observed": None, "expected": "present", "message": f"{path} is required"})
            continue
        if field not in record:
            continue
        value = record[field]
        if not _type_valid(value, spec["type"], nullable=bool(spec.get("nullable"))):
            errors.append({"file": file_name, "row": row, "path": path, "category": f"invalid_{spec['type']}", "observed": value, "expected": spec["type"], "message": f"{path} must be {spec['type']}"})
            continue
        if spec["type"] == "object":
            errors.extend(_json_errors(value, spec.get("schema", {}), file_name, row=row, prefix=path))
    for field, value in record.items():
        path = f"{prefix}.{field}" if prefix else field
        if field not in schema:
            errors.append({"file": file_name, "row": row, "path": path, "category": "unexpected_field", "observed": value, "expected": "declared_field", "message": f"{path} is not declared"})
    return tuple(sorted(errors, key=lambda item: (item["file"], item["row"], item["path"], item["category"])))


def _json_report(root: Path) -> dict[str, Any]:
    files = []
    for input_path in sorted((root / "inputs").glob("*.json")):
        schema = _read_json(root / "schemas" / f"{input_path.name}.schema.json")
        errors: list[dict[str, Any]] = []
        if schema.get("__schema_version__") not in {None, "1"}:
            errors.append({"file": input_path.name, "row": None, "path": "__schema_version__", "category": "unsupported_schema_version", "observed": schema.get("__schema_version__"), "expected": "1", "message": "schema version is unsupported"})
            files.append({"file": input_path.name, "valid": False, "errors": tuple(errors), "recommendations": tuple(f"Review {error['path']} in {input_path.name}" for error in errors)})
            continue
        try:
            records = _read_json(input_path)
        except json.JSONDecodeError as exc:
            errors.append({"file": input_path.name, "row": None, "path": "$", "category": "malformed_json", "observed": exc.msg, "expected": "parseable_json", "message": "JSON text cannot be parsed"})
            files.append({"file": input_path.name, "valid": False, "errors": tuple(errors), "recommendations": tuple(f"Review {error['path']} in {input_path.name}" for error in errors)})
            continue
        for index, record in enumerate(records, start=1):
            errors.extend(_json_errors(record, schema, input_path.name, row=index))
        files.append({"file": input_path.name, "valid": not bool(errors), "errors": tuple(errors), "recommendations": tuple(f"Review {error['path']} in {input_path.name}" for error in errors)})
    return {"schema": "live_competence_json_validation_report_v1", "files": tuple(files)}


def _json_report_without_semantics(_root: Path) -> dict[str, Any]:
    return {"schema": "live_competence_json_validation_report_v1", "files": ()}


def seal_json_validator(root: Path, fixture: Mapping[str, Any]) -> dict[str, Any]:
    expected = _json_report(Path(fixture["root"]))
    record = {
        "schema": "live_competence_json_validator_v1",
        "validator_id": stable_id("live-competence-json-validator", fixture["artifact_digest"], expected),
        "fixture_id": fixture["fixture_id"],
        "fixture_digest": fixture["artifact_digest"],
        "expected_report_digest": bootstrap_digest(expected),
        "expected_report": expected,
        "case_classes": JSON_CASE_CLASSES,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "sealed_validation", record["validator_id"], _digest_record(record))


def registered_live_task_adapters() -> tuple[LiveTaskAdapter, ...]:
    common_authority = {
        "provider_calls": 0,
        "retrievals": 1,
        "learner_attempts": 1,
        "evaluations": 1,
        "network": False,
        "tracked_source_mutation": False,
        "input_mutation": False,
        "credential_access": False,
    }
    return (
        LiveTaskAdapter(
            adapter_id="csv_schema_validation",
            version=1,
            supported_task_classes=(CSV_TASK_CLASS,),
            required_competence_titles=("Records fields and schemas", "Validation rules", "CSV tabular parsing"),
            fixture_input_contract="disposable_csv_files_plus_json_schemas",
            output_contract="deterministic_csv_validation_report",
            validator_contract="sealed_csv_expected_report",
            authority_requirements=common_authority,
            mutation_surface=(),
            network_requirements=(),
            priority=10,
            compatibility=_csv_compatible,
            executor=_csv_executor,
        ),
        LiveTaskAdapter(
            adapter_id="structured_json_validation",
            version=1,
            supported_task_classes=(JSON_TASK_CLASS,),
            required_competence_titles=JSON_PREREQUISITE_TITLES,
            fixture_input_contract="disposable_json_record_sets_plus_json_schemas",
            output_contract="deterministic_json_validation_report",
            validator_contract="sealed_json_expected_report",
            authority_requirements=common_authority,
            mutation_surface=(),
            network_requirements=(),
            priority=20,
            compatibility=_json_compatible,
            executor=_json_executor,
        ),
    )


def select_live_task_adapter(mission: Mapping[str, Any], adapters: Sequence[LiveTaskAdapter] | None = None) -> dict[str, Any]:
    registry = tuple(adapters or registered_live_task_adapters())
    compatible = tuple(adapter for adapter in registry if adapter.compatibility(adapter, mission))
    if not compatible:
        return {
            "schema": "live_competence_adapter_selection_v1",
            "selection_status": "unsupported_task",
            "reason": "no_compatible_adapter",
            "mission_id": mission["mission_id"],
            "adapter_id": "",
            "adapter_version": 0,
            "compatible_adapters": (),
            "created_at": FIXED_TIMESTAMP,
        }
    by_priority = sorted(compatible, key=lambda adapter: (adapter.priority, adapter.adapter_id, adapter.version))
    tied = tuple(adapter for adapter in by_priority if adapter.priority == by_priority[0].priority)
    if len(tied) > 1:
        return {
            "schema": "live_competence_adapter_selection_v1",
            "selection_status": "ambiguous_adapter",
            "reason": "multiple_adapters_share_highest_priority",
            "mission_id": mission["mission_id"],
            "adapter_id": "",
            "adapter_version": 0,
            "compatible_adapters": tuple(adapter.descriptor() for adapter in tied),
            "created_at": FIXED_TIMESTAMP,
        }
    selected = by_priority[0]
    return {
        "schema": "live_competence_adapter_selection_v1",
        "selection_status": "selected",
        "reason": "stable_priority_then_identity",
        "mission_id": mission["mission_id"],
        "adapter_id": selected.adapter_id,
        "adapter_version": selected.version,
        "compatible_adapters": tuple(adapter.descriptor() for adapter in compatible),
        "created_at": FIXED_TIMESTAMP,
    }


def compile_live_competence_context(root: Path, mission: Mapping[str, Any], adapter: LiveTaskAdapter) -> dict[str, Any]:
    selected_bootstrap = _select_competence_titles(adapter.required_competence_titles)
    capability = declare_adapter_capability(adapter, root=root)
    request = make_bootstrap_retrieval_request(objective=mission["objective"], curriculum_id=CURRICULUM_ID, curriculum_version=1, max_results=8, max_traversal_depth=8, max_packet_modules=18, max_total_chars=36000)
    retrieval = retrieve_bootstrap_context(curriculum_root=ACCEPTED_BOOTSTRAP_E_ROOT, request=request)
    packet = retrieval["learner_visible_packet"]
    available_developmental = ({"competence_id": DEVELOPMENTAL_COMPETENCE_ID, "competence_digest": DEVELOPMENTAL_COMPETENCE_DIGEST, "used_for_required_competence": False},)
    record = {
        "schema": "live_competence_context_v1",
        "context_id": stable_id("live-competence-context", mission["mission_id"], adapter.adapter_id, adapter.version, tuple(item["competence_digest"] for item in selected_bootstrap), packet["packet_digest"]),
        "mission_id": mission["mission_id"],
        "mission_digest": mission["artifact_digest"],
        "normalized_objective": mission["objective"],
        "requested_task_class": mission["task_class"],
        "selected_adapter_id": adapter.adapter_id,
        "selected_adapter_version": adapter.version,
        "adapter_capability_declaration_id": capability["declaration_id"],
        "adapter_capability_declaration_digest": capability["artifact_digest"],
        "adapter_semantic_operations_supplied": capability["semantic_operations_supplied"],
        "adapter_capability_kind": capability["capability_kind"],
        "adapter_selection_counts_as_competence": False,
        "accepted_validated_bootstrap_competencies": selected_bootstrap,
        "accepted_developmental_competencies": available_developmental,
        "selected_developmental_competencies": (),
        "installed_unvalidated_study_modules": retrieval["covered_by_installed_study_material"],
        "known_json_specific_unvalidated_concepts": ("JSON serialization", "Hierarchical data", "nested object validation"),
        "unresolved_concepts": retrieval["missing_from_curriculum"],
        "missing_required_competence": (),
        "mission_can_run_from_existing_competence": True,
        "mission_claim": "adapter-executed capability",
        "retrieval_policy": request,
        "context_packet_id": packet["packet_id"],
        "context_packet_digest": packet["packet_digest"],
        "packet_source_digests": tuple(packet.get("module_digests", ())),
        "authority_limits": mission["authority_limits"],
        "created_at": FIXED_TIMESTAMP,
    }
    with_digest = _digest_record(record)
    with_digest["context_digest"] = with_digest["artifact_digest"]
    return _write(root, "competence_context", with_digest["context_id"], with_digest)


def _json_mission_output(root: Path, mission: Mapping[str, Any], context: Mapping[str, Any], *, semantic_enabled: bool = True) -> dict[str, Any]:
    report = _json_report(root) if semantic_enabled else _json_report_without_semantics(root)
    record = {
        "schema": "live_competence_json_mission_output_v1",
        "output_id": stable_id("live-competence-json-output", mission["mission_id"], context["artifact_digest"], semantic_enabled),
        "mission_id": mission["mission_id"],
        "context_id": context["context_id"],
        "selected_adapter_id": context["selected_adapter_id"],
        "adapter_capability_declaration_id": context["adapter_capability_declaration_id"],
        "mission_claim": context["mission_claim"],
        "adapter_semantics_enabled": semantic_enabled,
        "report": report,
        "recommendations_mutate_inputs": False,
        "learner_calls": 1,
        "provider_calls": 0,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "mission_output", record["output_id"], _digest_record(record))


def _case_map() -> dict[str, str]:
    return {
        "valid_record_set": "valid_records.json",
        "missing_required_field": "missing_required.json",
        "unexpected_field": "unexpected_field.json",
        "invalid_integer": "invalid_integer.json",
        "invalid_boolean": "invalid_boolean.json",
        "invalid_nested_object": "invalid_nested_object.json",
        "multiple_error_record": "multiple_error.json",
        "optional_null": "optional_null.json",
        "malformed_json": "malformed_json.json",
        "unsupported_schema_version": "unsupported_schema_version.json",
    }


def _validate_json_output(root: Path, mission: Mapping[str, Any], fixture: Mapping[str, Any], validator: Mapping[str, Any], output: Mapping[str, Any], *, integrity_status: str = "evaluated") -> dict[str, Any]:
    after_digests = tuple(sorted((path.name, _file_digest(path)) for path in (root / "inputs").glob("*.json")))
    before_digests = tuple((item[0], item[1]) for item in fixture["input_digests"])
    report = output["report"]
    report_is_structured = isinstance(report, Mapping) and report.get("schema") == "live_competence_json_validation_report_v1" and isinstance(report.get("files"), (tuple, list))
    report_by_file = {item["file"]: item for item in report["files"]} if report_is_structured else {}
    expected_by_file = {item["file"]: item for item in validator["expected_report"]["files"]}
    cases = []
    for case_class, file_name in _case_map().items():
        passed = file_name in report_by_file and file_name in expected_by_file and json.dumps(report_by_file[file_name], sort_keys=True) == json.dumps(expected_by_file[file_name], sort_keys=True)
        cases.append({"case_class": case_class, "outcome": "passed" if passed else "failed"})
    provenance_complete = report_is_structured and set(report_by_file) == set(expected_by_file) and all(
        all(all(key in error for key in ("file", "row", "path", "category", "message")) for error in tuple(item.get("errors") or ()))
        for item in tuple(report.get("files") or ())
    )
    cases.append({"case_class": "provenance_completeness", "outcome": "passed" if provenance_complete else "failed"})
    unchanged = after_digests == before_digests
    passed = unchanged and report_is_structured and all(item["outcome"] == "passed" for item in cases)
    aggregate = "integrity_stop" if not unchanged or integrity_status == "integrity_stop" else ("passed" if passed else "failed")
    record = {
        "schema": "live_competence_json_evaluation_result_v1",
        "evaluation_id": stable_id("live-competence-json-evaluation", mission["mission_id"], validator["artifact_digest"], output["artifact_digest"], after_digests),
        "mission_id": mission["mission_id"],
        "output_id": output["output_id"],
        "output_digest": output["artifact_digest"],
        "validator_id": validator["validator_id"],
        "validator_digest": validator["artifact_digest"],
        "case_results": tuple(cases),
        "fixture_inputs_unchanged": unchanged,
        "deterministic_report_structure": bool(report_is_structured),
        "aggregate_status": aggregate,
        "evaluator_calls": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "evaluation", record["evaluation_id"], _digest_record(record))


def _negative_controls(root: Path, mission: Mapping[str, Any], fixture: Mapping[str, Any], validator: Mapping[str, Any]) -> dict[str, int]:
    expected = validator["expected_report"]
    expected_files = tuple(expected["files"])
    flat_only_files = []
    for item in expected_files:
        flat_only_files.append({**item, "errors": tuple(error for error in item["errors"] if "." not in error["path"])})
    controls = {
        "empty": {"schema": "live_competence_json_validation_report_v1", "files": ()},
        "irrelevant": {"schema": "live_competence_json_validation_report_v1", "files": ({"file": "weather.json", "valid": True, "errors": (), "recommendations": ()},)},
        "keyword_only": {"schema": "live_competence_json_validation_report_v1", "files": ({"file": "keywords", "valid": False, "errors": ({"category": "missing unexpected invalid nested boolean integer"},), "recommendations": ()},)},
        "flat_field_only": {"schema": "live_competence_json_validation_report_v1", "files": tuple(flat_only_files)},
        "unstructured": "all records look mostly valid except a few problems",
    }
    results = {}
    for name, report in controls.items():
        output = {"schema": "negative_control", "output_id": stable_id("live-competence-json-negative", mission["mission_id"], name), "mission_id": mission["mission_id"], "report": report, "artifact_digest": bootstrap_digest((name, report))}
        evaluation = _validate_json_output(root, mission, fixture, validator, output)
        results[name] = sum(1 for item in evaluation["case_results"] if item["outcome"] == "passed")
    return results


def _evaluation_item(root: Path, mission: Mapping[str, Any], selection: Mapping[str, Any], context: Mapping[str, Any], output: Mapping[str, Any], validator: Mapping[str, Any], evaluation: Mapping[str, Any]) -> dict[str, Any]:
    disposition = {
        "passed": "LIVE_COMPETENCE_ADAPTER_JSON_MISSION_PASSED",
        "failed": "LIVE_COMPETENCE_ADAPTER_JSON_MISSION_FAILED",
        "integrity_stop": "LIVE_COMPETENCE_ADAPTER_INTEGRITY_STOP",
    }[evaluation["aggregate_status"]]
    record = {
        "schema": "evaluation_ui_item_v1",
        "evaluation_item_id": stable_id("live-competence-evaluation-item", mission["mission_id"], selection["adapter_id"], evaluation["artifact_digest"]),
        "mission_id": mission["mission_id"],
        "adapter_id": selection["adapter_id"],
        "adapter_version": selection["adapter_version"],
        "competence_context_id": context["context_id"],
        "competence_context_digest": context["artifact_digest"],
        "adapter_capability_declaration_id": context["adapter_capability_declaration_id"],
        "adapter_capability_declaration_digest": context["adapter_capability_declaration_digest"],
        "mission_claim": context["mission_claim"],
        "output_id": output["output_id"],
        "output_digest": output["artifact_digest"],
        "validator_id": validator["validator_id"],
        "validator_digest": validator["artifact_digest"],
        "evaluation_id": evaluation["evaluation_id"],
        "evaluation_digest": evaluation["artifact_digest"],
        "case_results": evaluation["case_results"],
        "aggregate_disposition": disposition,
        "authority_summary": mission["authority_limits"],
        "mutation_summary": {"tracked_source_mutation": False, "fixture_input_mutation": not evaluation["fixture_inputs_unchanged"]},
        "trusted_admission": False,
        "capability_promotion": False,
        "status": "available",
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "evaluation_ui", record["evaluation_item_id"], _digest_record(record))


def _terminal(root: Path) -> dict[str, Any] | None:
    path = root / "terminal" / "terminal.json"
    if path.exists():
        return _read_json(path)
    return None


def _json_executor(root: Path, mission: Mapping[str, Any], reset: bool) -> Mapping[str, Any]:
    return run_live_competence_json_validation_mission(root=root, mission=mission, reset=reset)


def run_live_competence_json_validation_mission(*, root: Path = LIVE_COMPETENCE_ADAPTER_ROOT, mission: Mapping[str, Any] | None = None, reset: bool = False) -> dict[str, Any]:
    root = Path(root)
    if reset and root.exists():
        shutil.rmtree(root)
    existing = _terminal(root)
    if existing:
        return {**existing, "replay_suppressed": True, "learner_calls": 0, "evaluator_calls": 0}
    mission_record = _digest_record(dict(mission or _mission(JSON_TASK_CLASS, JSON_OBJECTIVE)))
    mission_record = _write(root, "mission", mission_record["mission_id"], mission_record)
    selection = select_live_task_adapter(mission_record)
    selection = _write(root, "adapter_selection", stable_id("live-competence-selection", mission_record["mission_id"], selection["selection_status"], selection["adapter_id"]), _digest_record(selection))
    if selection["selection_status"] != "selected":
        terminal = {
            "schema": "live_competence_adapter_terminal_v1",
            "mission_id": mission_record["mission_id"],
            "mission_digest": mission_record["artifact_digest"],
            "adapter_selection_id": selection["artifact_id"] if "artifact_id" in selection else selection.get("selection_id", ""),
            "selection_status": selection["selection_status"],
            "terminal_status": "LIVE_COMPETENCE_ADAPTER_BLOCKED",
            "provider_calls": 0,
            "retrieval_count": 0,
            "learner_calls": 0,
            "evaluator_calls": 0,
            "trusted_admissions": 0,
            "capability_promotions": 0,
            "created_at": FIXED_TIMESTAMP,
        }
        return _write(root, "terminal", "terminal", _digest_record(terminal))
    adapter = next(item for item in registered_live_task_adapters() if item.adapter_id == selection["adapter_id"] and item.version == selection["adapter_version"])
    context = compile_live_competence_context(root, mission_record, adapter)
    if context["missing_required_competence"]:
        terminal = {
            "schema": "live_competence_adapter_terminal_v1",
            "mission_id": mission_record["mission_id"],
            "mission_digest": mission_record["artifact_digest"],
            "selection": selection,
            "competence_context_id": context["context_id"],
            "competence_context_digest": context["artifact_digest"],
            "terminal_status": "LIVE_COMPETENCE_ADAPTER_LEARNING_REQUIRED",
            "provider_calls": 0,
            "retrieval_count": 1,
            "learner_calls": 0,
            "evaluator_calls": 0,
            "trusted_admissions": 0,
            "capability_promotions": 0,
            "created_at": FIXED_TIMESTAMP,
        }
        return _write(root, "terminal", "terminal", _digest_record(terminal))
    fixture = create_json_fixture(root, reset=False)
    validator = seal_json_validator(root, fixture)
    output = _json_mission_output(root, mission_record, context)
    evaluation = _validate_json_output(root, mission_record, fixture, validator, output)
    evaluation_item = _evaluation_item(root, mission_record, selection, context, output, validator, evaluation)
    negative_controls = _negative_controls(root, mission_record, fixture, validator)
    status = evaluation_item["aggregate_disposition"]
    terminal = {
        "schema": "live_competence_adapter_terminal_v1",
        "mission_id": mission_record["mission_id"],
        "mission_digest": mission_record["artifact_digest"],
        "adapter_id": adapter.adapter_id,
        "adapter_version": adapter.version,
        "selection_status": selection["selection_status"],
        "selection_digest": selection["artifact_digest"],
        "fixture_id": fixture["fixture_id"],
        "fixture_digest": fixture["artifact_digest"],
        "fixture_input_digests_before": fixture["input_digests"],
        "fixture_input_digests_after": tuple(sorted((path.name, _file_digest(path)) for path in (root / "inputs").glob("*.json"))),
        "competence_context_id": context["context_id"],
        "competence_context_digest": context["artifact_digest"],
        "adapter_capability_declaration_id": context["adapter_capability_declaration_id"],
        "adapter_capability_declaration_digest": context["adapter_capability_declaration_digest"],
        "adapter_semantic_operations_supplied": context["adapter_semantic_operations_supplied"],
        "adapter_capability_kind": context["adapter_capability_kind"],
        "mission_claim": context["mission_claim"],
        "validated_prerequisites_used": context["accepted_validated_bootstrap_competencies"],
        "developmental_competencies_available": context["accepted_developmental_competencies"],
        "developmental_competencies_used": context["selected_developmental_competencies"],
        "installed_unvalidated_study_modules": context["installed_unvalidated_study_modules"],
        "known_json_specific_unvalidated_concepts": context["known_json_specific_unvalidated_concepts"],
        "missing_concepts": context["unresolved_concepts"],
        "mission_can_run_from_existing_competence": context["mission_can_run_from_existing_competence"],
        "context_packet_id": context["context_packet_id"],
        "context_packet_digest": context["context_packet_digest"],
        "output_id": output["output_id"],
        "output_digest": output["artifact_digest"],
        "validator_id": validator["validator_id"],
        "validator_digest": validator["artifact_digest"],
        "validation_id": evaluation["evaluation_id"],
        "validation_digest": evaluation["artifact_digest"],
        "case_results": evaluation["case_results"],
        "evaluation_item_id": evaluation_item["evaluation_item_id"],
        "evaluation_item_digest": evaluation_item["artifact_digest"],
        "evaluation_item_status": evaluation_item["status"],
        "negative_controls": negative_controls,
        "runtime_state_sequence": ("mission_accepted", "adapter_selected", "competence_context_resolved", "fixture_inspection_completed", "independent_validation_available", "attended_stop"),
        "provider_calls": 0,
        "retrieval_count": 1,
        "learner_calls": 1,
        "evaluator_calls": 1,
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "terminal_status": status,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "terminal", "terminal", _digest_record(terminal))


def run_live_competence_adapter_mission(*, root: Path, task_class: str, objective: str, reset: bool = False) -> dict[str, Any]:
    mission = _mission(task_class, objective)
    selection = select_live_task_adapter(mission)
    if selection["selection_status"] != "selected":
        terminal = {
            "schema": "live_competence_adapter_terminal_v1",
            "mission_id": mission["mission_id"],
            "mission_digest": mission["artifact_digest"],
            "selection_status": selection["selection_status"],
            "terminal_status": "LIVE_COMPETENCE_ADAPTER_BLOCKED",
            "provider_calls": 0,
            "retrieval_count": 0,
            "learner_calls": 0,
            "evaluator_calls": 0,
            "trusted_admissions": 0,
            "capability_promotions": 0,
            "created_at": FIXED_TIMESTAMP,
        }
        return _write(Path(root), "terminal", "terminal", _digest_record(terminal))
    adapter = next(item for item in registered_live_task_adapters() if item.adapter_id == selection["adapter_id"] and item.version == selection["adapter_version"])
    return dict(adapter.executor(root, mission, reset))
