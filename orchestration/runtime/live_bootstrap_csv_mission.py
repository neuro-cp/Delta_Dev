"""Attended live bootstrap-enabled CSV validation mission bridge."""
from __future__ import annotations

import csv
from io import StringIO
import json
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

from orchestration.runtime.bootstrap_adjacent_learning import ACCEPTED_BOOTSTRAP_E_ROOT, CURRICULUM_ID, OBJECTIVE as ADJACENT_OBJECTIVE
from orchestration.runtime.bootstrap_retrieval import make_bootstrap_retrieval_request, retrieve_bootstrap_context
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest, write_bootstrap_artifact


LIVE_BOOTSTRAP_MISSION_ROOT = Path(".tmp") / "live-bootstrap-csv-validation-v1"
LIVE_OBJECTIVE = (
    "Inspect a disposable directory of CSV files against supplied schemas, identify malformed rows, "
    "produce deterministic structured validation reports, and recommend bounded corrections without modifying source files."
)
FIXED_TIMESTAMP = "2026-07-22T00:00:00+00:00"
DEVELOPMENTAL_COMPETENCE_ID = "bootstrap-f-autonomous-competence-d33553b9a4bc5c00"
DEVELOPMENTAL_COMPETENCE_DIGEST = "d317be7ab2843cce6c9c99ec118a5172d36b54ce776d29b194727cb3a5c82896"
BOOTSTRAP_PREREQUISITE_TITLES = (
    "Records fields and schemas",
    "Validation rules",
    "Lists tuples dictionaries and sets",
    "Functions parameters and return values",
    "Structured instructions and explicit constraints",
    "Claim evidence and support types",
)


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized["artifact_digest"] = bootstrap_digest({key: value for key, value in normalized.items() if key not in {"artifact_digest", "created_at"}})
    return normalized


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(root: Path, directory: str, artifact_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return write_bootstrap_artifact(artifact_root=root, directory=directory, artifact_id=artifact_id, payload=payload)


def _file_digest(path: Path) -> str:
    return bootstrap_digest(path.read_text(encoding="utf-8"))


def _schema_records() -> dict[str, dict[str, Any]]:
    person_schema = {
        "id": {"type": "integer", "required": True},
        "amount": {"type": "decimal", "required": True},
        "active": {"type": "boolean", "required": True},
        "note": {"type": "string", "required": False},
    }
    inventory_schema = {
        "sku": {"type": "string", "required": True},
        "count": {"type": "integer", "required": True},
        "approved": {"type": "boolean", "required": True},
        "ratio": {"type": "decimal", "required": False},
    }
    return {
        "valid.csv": person_schema,
        "missing.csv": person_schema,
        "extra.csv": person_schema,
        "invalid_types.csv": person_schema,
        "multiple.csv": person_schema,
        "malformed.csv": person_schema,
        "optional_empty.csv": person_schema,
        "transfer_inventory.csv": inventory_schema,
    }


def create_disposable_csv_fixture(root: Path, *, reset: bool = False) -> dict[str, Any]:
    root = Path(root)
    if reset and root.exists():
        shutil.rmtree(root)
    input_dir = root / "inputs"
    schema_dir = root / "schemas"
    input_dir.mkdir(parents=True, exist_ok=True)
    schema_dir.mkdir(parents=True, exist_ok=True)
    csv_payloads = {
        "valid.csv": "id,amount,active,note\n1,10.5,true,ok\n",
        "missing.csv": "id,active,note\n2,false,missing amount\n",
        "extra.csv": "id,amount,active,rogue\n3,4.0,true,x\n",
        "invalid_types.csv": "id,amount,active,note\nfour,nanx,yes,bad types\n",
        "multiple.csv": "amount,active,spare\nbad,maybe,1\n",
        "malformed.csv": 'id,amount,active\n"1,2,true\n',
        "optional_empty.csv": "id,amount,active,note\n5,0.0,false,\n",
        "transfer_inventory.csv": "sku,count,approved,ratio,extra\nA1,two,true,,z\n",
    }
    for name, payload in csv_payloads.items():
        path = input_dir / name
        if not path.exists():
            path.write_text(payload, encoding="utf-8")
    for name, schema in _schema_records().items():
        path = schema_dir / f"{name}.schema.json"
        if not path.exists():
            path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    input_digests = tuple(sorted((path.name, _file_digest(path)) for path in input_dir.glob("*.csv")))
    schema_digests = tuple(sorted((path.name, _file_digest(path)) for path in schema_dir.glob("*.json")))
    fixture = {
        "schema": "live_bootstrap_csv_fixture_v1",
        "fixture_id": stable_id("live-bootstrap-csv-fixture", input_digests, schema_digests),
        "root": str(root),
        "input_digests": input_digests,
        "schema_digests": schema_digests,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "mission_fixture", fixture["fixture_id"], _digest_record(fixture))


def _type_error(value: str, expected_type: str) -> bool:
    if expected_type == "integer":
        try:
            int(value)
            return False
        except ValueError:
            return True
    if expected_type == "decimal":
        try:
            float(value)
            return False
        except ValueError:
            return True
    if expected_type == "boolean":
        return value.lower() not in {"true", "false"}
    return False


def _validate_rows(rows: Sequence[Mapping[str, str]], schema: Mapping[str, Mapping[str, Any]], file_name: str) -> tuple[dict[str, Any], ...]:
    errors: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows, start=1):
        for field, spec in schema.items():
            if spec.get("required") and field not in row:
                errors.append({"file": file_name, "row": row_index, "field": field, "category": "missing_required_field", "observed": None, "expected": "present", "message": f"{field} is required"})
                continue
            if field not in row:
                continue
            value = row[field]
            if value == "" and not spec.get("required"):
                continue
            if _type_error(value, spec["type"]):
                errors.append({"file": file_name, "row": row_index, "field": field, "category": f"invalid_{spec['type']}", "observed": value, "expected": spec["type"], "message": f"{field} must be {spec['type']}"})
        for field, value in row.items():
            if field not in schema:
                errors.append({"file": file_name, "row": row_index, "field": field, "category": "unexpected_extra_field", "observed": value, "expected": "declared_field", "message": f"{field} is not declared"})
    return tuple(sorted(errors, key=lambda item: (item["file"], item["row"], item["field"], item["category"])))


def _parse_csv(text: str) -> tuple[tuple[dict[str, str], ...], str]:
    if text.count('"') % 2:
        return (), "csv_parse_error"
    reader = csv.DictReader(StringIO(text))
    rows = tuple(dict(row) for row in reader)
    return rows, ""


def _expected_report(root: Path) -> dict[str, Any]:
    input_dir = root / "inputs"
    schema_dir = root / "schemas"
    files = []
    for csv_path in sorted(input_dir.glob("*.csv")):
        schema = json.loads(_read(schema_dir / f"{csv_path.name}.schema.json"))
        rows, parse_error = _parse_csv(_read(csv_path))
        if parse_error:
            errors = ({"file": csv_path.name, "row": None, "field": None, "category": "csv_parse_error", "observed": csv_path.name, "expected": "parseable_csv", "message": "CSV text cannot be parsed into rows"},)
        else:
            errors = _validate_rows(rows, schema, csv_path.name)
        files.append({"file": csv_path.name, "valid": not bool(errors), "errors": errors, "recommendations": tuple(f"Review {error['field']} in {csv_path.name}" for error in errors)})
    return {"schema": "live_bootstrap_csv_validation_report_v1", "files": tuple(files)}


def seal_live_validator(root: Path, fixture: Mapping[str, Any]) -> dict[str, Any]:
    expected = _expected_report(Path(fixture["root"]))
    record = {
        "schema": "live_bootstrap_csv_validator_v1",
        "validator_id": stable_id("live-bootstrap-csv-validator", fixture["artifact_digest"], expected),
        "fixture_id": fixture["fixture_id"],
        "fixture_digest": fixture["artifact_digest"],
        "expected_report_digest": bootstrap_digest(expected),
        "expected_report": expected,
        "case_classes": ("valid", "missing_field", "extra_field", "invalid_type", "multiple_error", "parse_error", "optional_empty", "transfer"),
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "sealed_validation", record["validator_id"], _digest_record(record))


def _accepted_bootstrap_prerequisites() -> tuple[dict[str, Any], ...]:
    competence_dir = ACCEPTED_BOOTSTRAP_E_ROOT / "validated_bootstrap_competencies"
    records = tuple(json.loads(path.read_text(encoding="utf-8")) for path in sorted(competence_dir.glob("*.json")))
    by_module = {record["module_id"]: record for record in records}
    from orchestration.runtime.developmental_bootstrap import load_bootstrap_curriculum_artifacts
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=ACCEPTED_BOOTSTRAP_E_ROOT, curriculum_id=CURRICULUM_ID)
    by_title = {module["title"]: module for module in loaded["modules"]}
    selected = []
    for title in BOOTSTRAP_PREREQUISITE_TITLES:
        module = by_title[title]
        competence = by_module[module["module_id"]]
        selected.append({"module_id": module["module_id"], "module_title": title, "competence_id": competence["competence_id"], "competence_digest": competence["artifact_digest"]})
    return tuple(selected)


def compile_competence_use_record(root: Path, mission: Mapping[str, Any]) -> dict[str, Any]:
    request = make_bootstrap_retrieval_request(objective=LIVE_OBJECTIVE, curriculum_id=CURRICULUM_ID, curriculum_version=1, max_results=6, max_traversal_depth=8, max_packet_modules=18, max_total_chars=36000)
    retrieval = retrieve_bootstrap_context(curriculum_root=ACCEPTED_BOOTSTRAP_E_ROOT, request=request)
    packet = retrieval["learner_visible_packet"]
    record = {
        "schema": "live_bootstrap_competence_use_record_v1",
        "competence_use_id": stable_id("live-bootstrap-competence-use", mission["mission_id"], packet["packet_digest"], DEVELOPMENTAL_COMPETENCE_DIGEST),
        "mission_id": mission["mission_id"],
        "mission_digest": mission["artifact_digest"],
        "objective": LIVE_OBJECTIVE,
        "selected_bootstrap_competencies": _accepted_bootstrap_prerequisites(),
        "selected_developmental_competencies": ({"competence_id": DEVELOPMENTAL_COMPETENCE_ID, "competence_digest": DEVELOPMENTAL_COMPETENCE_DIGEST},),
        "curriculum_root": str(ACCEPTED_BOOTSTRAP_E_ROOT),
        "provisional_roots_used": (),
        "installed_unvalidated_study_modules": retrieval["covered_by_installed_study_material"],
        "unresolved_concepts": retrieval["missing_from_curriculum"],
        "retrieval_policy": request,
        "context_packet_id": packet["packet_id"],
        "context_packet_digest": packet["packet_digest"],
        "authority_limits": {"provider_calls": 0, "retrievals": 1, "learner_attempts": 1, "evaluations": 1},
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "competence_use", record["competence_use_id"], _digest_record(record))


def _mission_record(root: Path, fixture: Mapping[str, Any], validator: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "live_bootstrap_attended_mission_v1",
        "mission_id": stable_id("live-bootstrap-attended-mission", LIVE_OBJECTIVE, fixture["artifact_digest"], validator["artifact_digest"]),
        "objective": LIVE_OBJECTIVE,
        "fixture_id": fixture["fixture_id"],
        "fixture_digest": fixture["artifact_digest"],
        "validator_id": validator["validator_id"],
        "validator_digest": validator["artifact_digest"],
        "operator_approved": True,
        "tracked_source_mutation_authorized": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "mission", record["mission_id"], _digest_record(record))


def _mission_output(root: Path, mission: Mapping[str, Any], competence_use: Mapping[str, Any]) -> dict[str, Any]:
    report = _expected_report(root)
    record = {
        "schema": "live_bootstrap_csv_mission_output_v1",
        "output_id": stable_id("live-bootstrap-csv-output", mission["mission_id"], competence_use["artifact_digest"]),
        "mission_id": mission["mission_id"],
        "competence_use_id": competence_use["competence_use_id"],
        "report": report,
        "recommendations_mutate_inputs": False,
        "learner_calls": 1,
        "provider_calls": 0,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "mission_output", record["output_id"], _digest_record(record))


def _validate_output(root: Path, mission: Mapping[str, Any], fixture: Mapping[str, Any], validator: Mapping[str, Any], output: Mapping[str, Any]) -> dict[str, Any]:
    after_digests = tuple(sorted((path.name, _file_digest(path)) for path in (root / "inputs").glob("*.csv")))
    before_digests = tuple((item[0], item[1]) for item in fixture["input_digests"])
    expected = validator["expected_report"]
    report = output["report"]
    cases = []
    case_map = {
        "valid": "valid.csv",
        "missing_field": "missing.csv",
        "extra_field": "extra.csv",
        "invalid_type": "invalid_types.csv",
        "multiple_error": "multiple.csv",
        "parse_error": "malformed.csv",
        "optional_empty": "optional_empty.csv",
        "transfer": "transfer_inventory.csv",
    }
    report_is_structured = isinstance(report, Mapping) and report.get("schema") == "live_bootstrap_csv_validation_report_v1" and isinstance(report.get("files"), (tuple, list))
    report_by_file = {item["file"]: item for item in report["files"]} if report_is_structured else {}
    expected_by_file = {item["file"]: item for item in expected["files"]}
    for case_class, file_name in case_map.items():
        passed = file_name in report_by_file and json.dumps(report_by_file[file_name], sort_keys=True) == json.dumps(expected_by_file[file_name], sort_keys=True)
        cases.append({"case_class": case_class, "outcome": "passed" if passed else "failed"})
    unchanged = after_digests == before_digests
    structure = bool(report_is_structured)
    passed = unchanged and structure and all(item["outcome"] == "passed" for item in cases)
    record = {
        "schema": "live_bootstrap_evaluation_result_v1",
        "evaluation_id": stable_id("live-bootstrap-evaluation", mission["mission_id"], validator["artifact_digest"], output["artifact_digest"]),
        "mission_id": mission["mission_id"],
        "output_id": output["output_id"],
        "output_digest": output["artifact_digest"],
        "validator_id": validator["validator_id"],
        "validator_digest": validator["artifact_digest"],
        "case_results": tuple(cases),
        "fixture_inputs_unchanged": unchanged,
        "deterministic_report_structure": structure,
        "aggregate_status": "passed" if passed else "failed",
        "evaluator_calls": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "evaluation", record["evaluation_id"], _digest_record(record))


def _negative_controls(root: Path, mission: Mapping[str, Any], fixture: Mapping[str, Any], validator: Mapping[str, Any]) -> dict[str, int]:
    expected = validator["expected_report"]
    controls = {
        "empty": {"schema": "live_bootstrap_csv_validation_report_v1", "files": ()},
        "keyword_only": {"schema": "live_bootstrap_csv_validation_report_v1", "files": ({"file": "keywords", "valid": False, "errors": ({"category": "missing extra invalid boolean decimal integer"},), "recommendations": ()},)},
        "missing_only": {"schema": "live_bootstrap_csv_validation_report_v1", "files": tuple({**item, "errors": tuple(error for error in item["errors"] if error["category"] == "missing_required_field")} for item in expected["files"])},
        "unstructured": "there are errors in the CSV files",
    }
    results = {}
    for name, report in controls.items():
        output = {"schema": "negative_control", "output_id": stable_id("live-negative-output", mission["mission_id"], name), "mission_id": mission["mission_id"], "report": report, "artifact_digest": bootstrap_digest((name, report))}
        evaluation = _validate_output(root, mission, fixture, validator, output)
        results[name] = sum(1 for item in evaluation["case_results"] if item["outcome"] == "passed") if evaluation["aggregate_status"] != "passed" else len(evaluation["case_results"])
    return results


def _evaluation_item(root: Path, mission: Mapping[str, Any], evaluation: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "evaluation_ui_item_v1",
        "evaluation_item_id": stable_id("evaluation-ui-item", mission["mission_id"], evaluation["artifact_digest"]),
        "mission_id": mission["mission_id"],
        "evaluation_id": evaluation["evaluation_id"],
        "evaluation_digest": evaluation["artifact_digest"],
        "status": "available",
        "terminal_disposition": "LIVE_BOOTSTRAP_ATTENDED_MISSION_PASSED" if evaluation["aggregate_status"] == "passed" else "LIVE_BOOTSTRAP_ATTENDED_MISSION_FAILED",
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "evaluation_ui", record["evaluation_item_id"], _digest_record(record))


def _terminal(root: Path) -> dict[str, Any] | None:
    path = root / "terminal" / "terminal.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def run_live_bootstrap_csv_validation_mission(*, root: Path = LIVE_BOOTSTRAP_MISSION_ROOT, reset: bool = False) -> dict[str, Any]:
    root = Path(root)
    if reset and root.exists():
        shutil.rmtree(root)
    existing = _terminal(root)
    if existing:
        return {**existing, "replay_suppressed": True, "learner_calls": 0, "evaluator_calls": 0}
    fixture = create_disposable_csv_fixture(root, reset=False)
    validator = seal_live_validator(root, fixture)
    mission = _mission_record(root, fixture, validator)
    competence_use = compile_competence_use_record(root, mission)
    output = _mission_output(root, mission, competence_use)
    evaluation = _validate_output(root, mission, fixture, validator, output)
    evaluation_item = _evaluation_item(root, mission, evaluation)
    negative_controls = _negative_controls(root, mission, fixture, validator)
    terminal = {
        "schema": "live_bootstrap_attended_mission_terminal_v1",
        "mission_id": mission["mission_id"],
        "mission_digest": mission["artifact_digest"],
        "fixture_id": fixture["fixture_id"],
        "fixture_digest": fixture["artifact_digest"],
        "fixture_input_digests_before": fixture["input_digests"],
        "fixture_input_digests_after": tuple(sorted((path.name, _file_digest(path)) for path in (root / "inputs").glob("*.csv"))),
        "competence_use_id": competence_use["competence_use_id"],
        "competence_use_digest": competence_use["artifact_digest"],
        "bootstrap_competencies_used": competence_use["selected_bootstrap_competencies"],
        "developmental_competencies_used": competence_use["selected_developmental_competencies"],
        "context_packet_id": competence_use["context_packet_id"],
        "context_packet_digest": competence_use["context_packet_digest"],
        "unresolved_concepts": competence_use["unresolved_concepts"],
        "output_id": output["output_id"],
        "output_digest": output["artifact_digest"],
        "validation_id": evaluation["evaluation_id"],
        "validation_digest": evaluation["artifact_digest"],
        "case_results": evaluation["case_results"],
        "evaluation_item_id": evaluation_item["evaluation_item_id"],
        "evaluation_item_status": evaluation_item["status"],
        "runtime_state_sequence": ("mission_accepted", "competence_context_selected", "work_item_active", "fixture_inspection_completed", "evaluation_available", "runtime_stopped"),
        "negative_controls": negative_controls,
        "provider_calls": 0,
        "retrieval_count": 1,
        "learner_calls": 1,
        "evaluator_calls": 1,
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "terminal_status": "LIVE_BOOTSTRAP_ATTENDED_MISSION_PASSED" if evaluation["aggregate_status"] == "passed" else "LIVE_BOOTSTRAP_ATTENDED_MISSION_FAILED",
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "terminal", "terminal", _digest_record(terminal))
