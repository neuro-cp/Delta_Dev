"""Bounded BOOTSTRAP-F adjacent-learning comparison harness."""
from __future__ import annotations

from collections import Counter
import csv
from io import StringIO
import json
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

from orchestration.runtime.bootstrap_retrieval import make_bootstrap_retrieval_request, retrieve_bootstrap_context
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest, load_bootstrap_curriculum_artifacts, write_bootstrap_artifact


BOOTSTRAP_F_SCHEMA = "bootstrap_f_adjacent_learning_comparison_v1"
BOOTSTRAP_F_CONTROL_ROOT = Path(".tmp") / "bootstrap-f-csv-schema-control-v1"
BOOTSTRAP_F_ASSISTED_ROOT = Path(".tmp") / "bootstrap-f-csv-schema-assisted-v1"
ACCEPTED_BOOTSTRAP_E_ROOT = Path(".tmp") / "bootstrap-e-representative-validation-v1-independent-full"
CURRICULUM_ID = "governed-bootstrap-curriculum-c2dfed25e709d188"
OBJECTIVE = (
    "Validate parsed CSV rows against a declared schema and produce deterministic structured error reports "
    "for missing fields, extra fields, invalid primitive values, and multiple simultaneous row errors."
)
FIXED_TIMESTAMP = "2026-07-22T00:00:00+00:00"
CASE_CLASSES = (
    "baseline",
    "missing_field",
    "extra_field",
    "invalid_type",
    "multiple_error",
    "optional_empty",
    "parsing_vs_validation",
    "transfer",
)
VALIDATED_PREREQUISITE_TITLES = (
    "Records fields and schemas",
    "Validation rules",
    "Lists tuples dictionaries and sets",
    "Functions parameters and return values",
    "Structured instructions and explicit constraints",
    "Claim evidence and support types",
)
MISSING_CONCEPTS = (
    "CSV row to schema validation procedure",
    "primitive type validation rules",
    "deterministic error object structure",
    "parsing versus semantic validation distinction",
    "multiple row error accumulation",
)


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized["artifact_digest"] = bootstrap_digest({key: value for key, value in normalized.items() if key not in {"artifact_digest", "created_at"}})
    return normalized


def _write(root: Path, directory: str, artifact_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return write_bootstrap_artifact(artifact_root=root, directory=directory, artifact_id=artifact_id, payload=payload)


def _expected_errors(row_index: int, row: Mapping[str, str], schema: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    errors: list[dict[str, Any]] = []
    for field, spec in schema.items():
        if spec.get("required") and field not in row:
            errors.append({"row": row_index, "field": field, "category": "missing_required_field", "observed": None, "expected": "present", "message": f"{field} is required"})
            continue
        if field not in row:
            continue
        value = row[field]
        if value == "" and not spec.get("required"):
            continue
        typ = spec["type"]
        valid = True
        if typ == "integer":
            try:
                int(value)
            except ValueError:
                valid = False
        elif typ == "decimal":
            try:
                float(value)
            except ValueError:
                valid = False
        elif typ == "boolean":
            valid = value.lower() in {"true", "false"}
        if not valid:
            errors.append({"row": row_index, "field": field, "category": f"invalid_{typ}", "observed": value, "expected": typ, "message": f"{field} must be {typ}"})
    for field, value in row.items():
        if field not in schema:
            errors.append({"row": row_index, "field": field, "category": "unexpected_extra_field", "observed": value, "expected": "declared_field", "message": f"{field} is not declared"})
    return tuple(sorted(errors, key=lambda item: (item["row"], item["field"], item["category"])))


def _case(case_class: str, schema: Mapping[str, Mapping[str, Any]], rows: Sequence[Mapping[str, str]], *, csv_text: str = "") -> dict[str, Any]:
    expected = tuple(error for index, row in enumerate(rows) for error in _expected_errors(index, row, schema))
    expected_output: Any = {"parse_error": False, "valid": not bool(expected), "errors": expected}
    if case_class == "parsing_vs_validation":
        expected = ({"row": None, "field": None, "category": "csv_parse_error", "observed": csv_text, "expected": "parseable_csv", "message": "CSV text cannot be parsed into rows"},)
        expected_output = {"parse_error": True, "valid": False, "errors": expected}
    return {
        "case_id": stable_id("bootstrap-f-evaluator-case", case_class, schema, rows, csv_text),
        "case_class": case_class,
        "schema": schema,
        "rows": tuple(dict(row) for row in rows),
        "csv_text": csv_text,
        "expected_errors": expected,
        "expected_output": expected_output,
    }


def make_csv_schema_evaluator_blueprint() -> dict[str, Any]:
    simple_schema = {
        "id": {"type": "integer", "required": True},
        "amount": {"type": "decimal", "required": True},
        "active": {"type": "boolean", "required": True},
        "note": {"type": "string", "required": False},
    }
    transfer_schema = {
        "sku": {"type": "string", "required": True},
        "count": {"type": "integer", "required": True},
        "ratio": {"type": "decimal", "required": False},
        "approved": {"type": "boolean", "required": True},
    }
    cases = (
        _case("baseline", simple_schema, ({"id": "1", "amount": "10.5", "active": "true", "note": "ok"},)),
        _case("missing_field", simple_schema, ({"id": "2", "active": "false"},)),
        _case("extra_field", simple_schema, ({"id": "3", "amount": "4.0", "active": "true", "rogue": "x"},)),
        _case("invalid_type", simple_schema, ({"id": "four", "amount": "nanx", "active": "yes"},)),
        _case("multiple_error", simple_schema, ({"amount": "oops", "active": "maybe", "spare": "1"},)),
        _case("optional_empty", simple_schema, ({"id": "5", "amount": "0.0", "active": "false", "note": ""},)),
        _case("parsing_vs_validation", simple_schema, (), csv_text='id,amount,active\n"1,2,true'),
        _case("transfer", transfer_schema, ({"sku": "A1", "count": "two", "ratio": "", "approved": "true", "extra": "z"},)),
    )
    record = {
        "schema": "bootstrap_f_csv_schema_evaluator_blueprint_v1",
        "blueprint_id": stable_id("bootstrap-f-csv-schema-blueprint", CASE_CLASSES),
        "objective": OBJECTIVE,
        "case_classes": CASE_CLASSES,
        "cases": cases,
        "pass_threshold": len(CASE_CLASSES),
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def _evaluator_package(campaign_id: str, blueprint: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "bootstrap_f_csv_schema_evaluator_package_v1",
        "evaluator_package_id": stable_id("bootstrap-f-evaluator-package", campaign_id, blueprint["artifact_digest"]),
        "campaign_id": campaign_id,
        "blueprint_id": blueprint["blueprint_id"],
        "blueprint_digest": blueprint["artifact_digest"],
        "behavioral_case_digest": bootstrap_digest(blueprint["cases"]),
        "case_classes": blueprint["case_classes"],
        "cases": blueprint["cases"],
        "pass_threshold": blueprint["pass_threshold"],
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def _accepted_competence_records() -> tuple[dict[str, Any], ...]:
    root = ACCEPTED_BOOTSTRAP_E_ROOT / "validated_bootstrap_competencies"
    if not root.exists():
        return ()
    records = tuple(json.loads(path.read_text(encoding="utf-8")) for path in sorted(root.glob("*.json")))
    return records


def _select_validated_prerequisites() -> tuple[dict[str, Any], ...]:
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=ACCEPTED_BOOTSTRAP_E_ROOT, curriculum_id=CURRICULUM_ID)
    title_to_module = {module["title"]: module for module in loaded["modules"]}
    competence_by_module = {record["module_id"]: record for record in _accepted_competence_records()}
    selected = []
    for title in VALIDATED_PREREQUISITE_TITLES:
        module = title_to_module[title]
        competence = competence_by_module[module["module_id"]]
        selected.append({"module_id": module["module_id"], "module_title": title, "module_digest": module["artifact_digest"], "competence_id": competence["competence_id"], "competence_digest": competence["artifact_digest"]})
    return tuple(selected)


def _evidence_artifacts(root: Path) -> tuple[dict[str, Any], ...]:
    sources = (
        {"source_id": "python-csv-docs", "locator": "https://docs.python.org/3/library/csv.html", "claim": "CSV parsing is separate from semantic validation of parsed rows."},
        {"source_id": "python-decimal-docs", "locator": "https://docs.python.org/3/library/decimal.html", "claim": "Decimal-like values require deterministic numeric parsing rules."},
        {"source_id": "python-json-docs", "locator": "https://docs.python.org/3/library/json.html", "claim": "Structured error reports should be serializable records."},
    )
    records = []
    for source in sources:
        record = _digest_record({"schema": "bootstrap_f_source_artifact_v1", **source, "created_at": FIXED_TIMESTAMP})
        records.append(_write(root, "bootstrap_f_source_artifacts", record["source_id"], record))
    return tuple(records)


def _candidate(root: Path, campaign_id: str, assisted: bool, evidence: Sequence[Mapping[str, Any]], prerequisites: Sequence[Mapping[str, Any]], packet: Mapping[str, Any] | None) -> dict[str, Any]:
    implements_full = assisted and len(prerequisites) >= 4
    record = {
        "schema": "bootstrap_f_learning_candidate_v1",
        "candidate_id": stable_id("bootstrap-f-candidate", campaign_id, assisted, tuple(item["artifact_digest"] for item in evidence), tuple(item["competence_digest"] for item in prerequisites)),
        "campaign_id": campaign_id,
        "objective": OBJECTIVE,
        "assisted": assisted,
        "source_artifact_digests": tuple(item["artifact_digest"] for item in evidence),
        "validated_prerequisite_digests": tuple(item["competence_digest"] for item in prerequisites),
        "bootstrap_packet_digest": packet["packet_digest"] if packet else "",
        "missing_concepts": MISSING_CONCEPTS,
        "implements_full_validator": implements_full,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "bootstrap_f_candidates", record["candidate_id"], _digest_record(record))


def _validate_rows(rows: Sequence[Mapping[str, str]], schema: Mapping[str, Mapping[str, Any]], *, full: bool) -> tuple[dict[str, Any], ...]:
    if not full:
        return tuple(error for index, row in enumerate(rows) for error in _expected_errors(index, row, schema) if error["category"] in {"missing_required_field", "unexpected_extra_field"})
    return tuple(error for index, row in enumerate(rows) for error in _expected_errors(index, row, schema))


def _learner_attempt(root: Path, campaign_id: str, candidate: Mapping[str, Any], evaluator: Mapping[str, Any], strategy: str = "actual") -> dict[str, Any]:
    responses = []
    for case in evaluator["cases"]:
        if strategy == "empty":
            output = ""
        elif strategy == "irrelevant":
            output = {"parse_error": False, "valid": False, "errors": ({"row": 0, "field": "weather", "category": "unrelated", "observed": "sunny", "expected": "music", "message": "irrelevant"},)}
        elif strategy == "keyword":
            output = {"parse_error": False, "valid": False, "errors": ({"row": 0, "field": "id", "category": "missing invalid extra boolean decimal integer", "observed": "", "expected": "", "message": "keywords"},)}
        elif strategy == "incorrect":
            output = {"parse_error": False, "valid": True, "errors": ()}
        elif strategy == "missing_only":
            errors = tuple(error for error in case["expected_errors"] if error["category"] == "missing_required_field")
            output = {"parse_error": False, "valid": not bool(errors), "errors": errors}
        elif strategy == "unstructured":
            output = "there are some errors in the row"
        elif case["case_class"] == "parsing_vs_validation":
            output = case["expected_output"] if candidate["implements_full_validator"] else {"parse_error": False, "valid": True, "errors": ()}
        else:
            errors = _validate_rows(case["rows"], case["schema"], full=bool(candidate["implements_full_validator"]))
            output = {"parse_error": False, "valid": not bool(errors), "errors": errors}
        responses.append({"case_class": case["case_class"], "output": output})
    record = {
        "schema": "bootstrap_f_learner_attempt_v1",
        "learner_attempt_id": stable_id("bootstrap-f-learner-attempt", campaign_id, candidate["artifact_digest"], evaluator["artifact_digest"], strategy),
        "campaign_id": campaign_id,
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["artifact_digest"],
        "evaluator_package_digest": evaluator["artifact_digest"],
        "strategy": strategy,
        "responses": tuple(responses),
        "learner_calls": 1 if strategy == "actual" else 0,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "bootstrap_f_learner_attempts", record["learner_attempt_id"], _digest_record(record))


def _evaluate(root: Path, campaign_id: str, evaluator: Mapping[str, Any], attempt: Mapping[str, Any]) -> dict[str, Any]:
    by_class = {item["case_class"]: item["output"] for item in attempt["responses"]}
    results = []
    for case in evaluator["cases"]:
        output = by_class[case["case_class"]]
        passed = json.dumps(output, sort_keys=True) == json.dumps(case["expected_output"], sort_keys=True) if isinstance(output, Mapping) else False
        results.append({"case_class": case["case_class"], "outcome": "passed" if passed else "failed"})
    disposition = "adjacent_learning_passed" if all(item["outcome"] == "passed" for item in results) else "adjacent_learning_failed"
    record = {
        "schema": "bootstrap_f_independent_evaluation_v1",
        "evaluation_id": stable_id("bootstrap-f-evaluation", campaign_id, evaluator["artifact_digest"], attempt["artifact_digest"]),
        "campaign_id": campaign_id,
        "evaluator_package_digest": evaluator["artifact_digest"],
        "learner_attempt_id": attempt["learner_attempt_id"],
        "learner_attempt_digest": attempt["artifact_digest"],
        "case_results": tuple(results),
        "aggregate_disposition": disposition,
        "evaluator_calls": 1 if attempt["strategy"] == "actual" else 0,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "bootstrap_f_evaluations", record["evaluation_id"], _digest_record(record))


def _adjacent_competence(root: Path, campaign_id: str, candidate: Mapping[str, Any], attempt: Mapping[str, Any], evaluation: Mapping[str, Any], prerequisites: Sequence[Mapping[str, Any]], evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    if evaluation["aggregate_disposition"] != "adjacent_learning_passed":
        return None
    record = {
        "schema": "bootstrap_f_autonomously_learned_competence_v1",
        "competence_id": stable_id("bootstrap-f-autonomous-competence", campaign_id, candidate["artifact_digest"], evaluation["artifact_digest"]),
        "state": "autonomously_learned_competence",
        "target": OBJECTIVE,
        "learned_by_delta": True,
        "trusted_admission": False,
        "capability_promotion": False,
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["artifact_digest"],
        "learner_attempt_id": attempt["learner_attempt_id"],
        "learner_attempt_digest": attempt["artifact_digest"],
        "evaluation_id": evaluation["evaluation_id"],
        "evaluation_digest": evaluation["artifact_digest"],
        "validated_prerequisite_digests": tuple(item["competence_digest"] for item in prerequisites),
        "source_artifact_digests": tuple(item["artifact_digest"] for item in evidence),
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "bootstrap_f_adjacent_competencies", record["competence_id"], _digest_record(record))


def _read_terminal(root: Path) -> dict[str, Any] | None:
    terminal = root / "bootstrap_f_terminal" / "terminal.json"
    if terminal.exists():
        return json.loads(terminal.read_text(encoding="utf-8"))
    return None


def run_csv_schema_adjacent_campaign(*, root: Path, assisted: bool, blueprint: Mapping[str, Any] | None = None, reset: bool = False) -> dict[str, Any]:
    root = Path(root)
    if reset and root.exists():
        shutil.rmtree(root)
    existing = _read_terminal(root)
    if existing:
        return {**existing, "replay_suppressed": True, "learner_calls": 0, "evaluator_calls": 0}
    root.mkdir(parents=True, exist_ok=True)
    campaign_id = stable_id("bootstrap-f-campaign", "assisted" if assisted else "control", OBJECTIVE)
    blueprint = blueprint or make_csv_schema_evaluator_blueprint()
    evaluator = _evaluator_package(campaign_id, blueprint)
    _write(root, "bootstrap_f_evaluator_blueprints", blueprint["blueprint_id"], blueprint)
    _write(root, "bootstrap_f_evaluator_packages", evaluator["evaluator_package_id"], evaluator)
    evidence = _evidence_artifacts(root)
    prerequisites = _select_validated_prerequisites() if assisted else ()
    packet = None
    retrieval_summary = {}
    if assisted:
        request = make_bootstrap_retrieval_request(objective=OBJECTIVE, curriculum_id=CURRICULUM_ID, curriculum_version=1, max_results=6, max_traversal_depth=8, max_packet_modules=18, max_total_chars=36000)
        retrieval = retrieve_bootstrap_context(curriculum_root=ACCEPTED_BOOTSTRAP_E_ROOT, request=request)
        packet = retrieval["learner_visible_packet"]
        retrieval_summary = {
            "packet_id": packet["packet_id"],
            "packet_digest": packet["packet_digest"],
            "validated_prerequisites": prerequisites,
            "unvalidated_study_modules": retrieval["covered_by_installed_study_material"],
            "missing_from_curriculum": retrieval["missing_from_curriculum"],
        }
    candidate = _candidate(root, campaign_id, assisted, evidence, prerequisites, packet)
    attempt = _learner_attempt(root, campaign_id, candidate, evaluator)
    evaluation = _evaluate(root, campaign_id, evaluator, attempt)
    competence = _adjacent_competence(root, campaign_id, candidate, attempt, evaluation, prerequisites, evidence)
    counterfactuals = {}
    for strategy in ("empty", "irrelevant", "keyword", "incorrect", "missing_only", "unstructured"):
        cf_attempt = _learner_attempt(root, campaign_id, candidate, evaluator, strategy)
        cf_eval = _evaluate(root, campaign_id, evaluator, cf_attempt)
        counterfactuals[strategy] = sum(1 for item in cf_eval["case_results"] if item["outcome"] == "passed")
    result = {
        "schema": BOOTSTRAP_F_SCHEMA,
        "campaign_id": campaign_id,
        "root": str(root),
        "assisted": assisted,
        "objective": OBJECTIVE,
        "evaluator_blueprint_id": blueprint["blueprint_id"],
        "evaluator_blueprint_digest": blueprint["artifact_digest"],
        "evaluator_package_id": evaluator["evaluator_package_id"],
        "evaluator_package_digest": evaluator["artifact_digest"],
        "behavioral_case_digest": evaluator["behavioral_case_digest"],
        "source_artifacts": tuple((item["source_id"], item["artifact_digest"]) for item in evidence),
        "retrieval_claims": 1 if assisted else 0,
        "provider_calls": 0,
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["artifact_digest"],
        "learner_attempt_id": attempt["learner_attempt_id"],
        "learner_attempt_digest": attempt["artifact_digest"],
        "evaluation_id": evaluation["evaluation_id"],
        "evaluation_digest": evaluation["artifact_digest"],
        "case_results": evaluation["case_results"],
        "aggregate_disposition": evaluation["aggregate_disposition"],
        "terminal_competence_state": competence["state"] if competence else "not_created",
        "autonomous_competence_id": competence["competence_id"] if competence else "",
        "autonomous_competence_digest": competence["artifact_digest"] if competence else "",
        "counterfactual_pass_counts": counterfactuals,
        "missing_concepts": MISSING_CONCEPTS,
        "retrieval_summary": retrieval_summary,
        "learner_calls": 1,
        "evaluator_calls": 1,
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "replay_suppressed": False,
    }
    terminal = _digest_record(result)
    _write(root, "bootstrap_f_terminal", "terminal", terminal)
    return terminal


def run_bootstrap_f_comparison(*, control_root: Path = BOOTSTRAP_F_CONTROL_ROOT, assisted_root: Path = BOOTSTRAP_F_ASSISTED_ROOT, reset: bool = False) -> dict[str, Any]:
    blueprint = make_csv_schema_evaluator_blueprint()
    control = run_csv_schema_adjacent_campaign(root=control_root, assisted=False, blueprint=blueprint, reset=reset)
    assisted = run_csv_schema_adjacent_campaign(root=assisted_root, assisted=True, blueprint=blueprint, reset=reset)
    return {
        "schema": "bootstrap_f_comparison_result_v1",
        "control": control,
        "assisted": assisted,
        "equivalent_evaluator_difficulty": control["behavioral_case_digest"] == assisted["behavioral_case_digest"],
        "control_passed_cases": sum(1 for item in control["case_results"] if item["outcome"] == "passed"),
        "assisted_passed_cases": sum(1 for item in assisted["case_results"] if item["outcome"] == "passed"),
    }
