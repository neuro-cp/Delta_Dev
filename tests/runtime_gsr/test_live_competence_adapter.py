from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from orchestration.runtime.live_competence_adapter import (
    JSON_CASE_CLASSES,
    JSON_OBJECTIVE,
    JSON_SEMANTIC_OPERATIONS,
    JSON_TASK_CLASS,
    CSV_TASK_CLASS,
    LiveAdapterBoundaryError,
    _json_mission_output,
    _mission,
    _validate_json_output,
    compile_live_competence_context,
    create_json_fixture,
    declare_adapter_capability,
    registered_live_task_adapters,
    run_live_competence_adapter_mission,
    run_live_competence_json_validation_mission,
    seal_json_validator,
    select_live_task_adapter,
)


def _inventory(root: Path) -> tuple[str, ...]:
    return tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))


def test_adapter_registry_is_deterministic_and_contains_csv_and_json_adapters():
    first = tuple(adapter.descriptor() for adapter in registered_live_task_adapters())
    second = tuple(adapter.descriptor() for adapter in registered_live_task_adapters())

    assert first == second
    assert tuple(adapter["adapter_id"] for adapter in first) == ("csv_schema_validation", "structured_json_validation")
    assert tuple(adapter["version"] for adapter in first) == (1, 1)


def test_adapter_selection_is_exact_for_json_and_csv_task_classes():
    json_selection = select_live_task_adapter(_mission(JSON_TASK_CLASS, JSON_OBJECTIVE))
    csv_selection = select_live_task_adapter(_mission(CSV_TASK_CLASS, "Validate disposable CSV files."))

    assert json_selection["selection_status"] == "selected"
    assert json_selection["adapter_id"] == "structured_json_validation"
    assert csv_selection["selection_status"] == "selected"
    assert csv_selection["adapter_id"] == "csv_schema_validation"


def test_json_adapter_capability_declaration_is_deterministic_untrusted_and_unpromoted():
    adapter = registered_live_task_adapters()[1]
    first = declare_adapter_capability(adapter)
    second = declare_adapter_capability(adapter)

    assert first == second
    assert first["adapter_id"] == "structured_json_validation"
    assert first["semantic_operations_supplied"] == JSON_SEMANTIC_OPERATIONS
    assert first["capability_kind"] == "domain_semantics"
    assert first["trusted_status"] is False
    assert first["promotion_status"] is False
    assert first["adapter_selection_counts_as_competence"] is False


def test_incompatible_adapter_is_rejected_without_fallback():
    selection = select_live_task_adapter(_mission("image_segmentation", "Segment an image."))

    assert selection["selection_status"] == "unsupported_task"
    assert selection["adapter_id"] == ""


def test_missing_competence_rejects_context_compilation(tmp_path):
    mission = _mission(JSON_TASK_CLASS, JSON_OBJECTIVE)
    adapter = replace(registered_live_task_adapters()[1], required_competence_titles=("Not a validated competence",))

    with pytest.raises(LiveAdapterBoundaryError, match="accepted_competence_missing"):
        compile_live_competence_context(tmp_path / "live", mission, adapter)


def test_ablation_of_validated_schema_or_validation_prerequisite_blocks_context(tmp_path):
    mission = _mission(JSON_TASK_CLASS, JSON_OBJECTIVE)
    adapter = registered_live_task_adapters()[1]
    without_schema = replace(adapter, required_competence_titles=tuple(title for title in adapter.required_competence_titles if title != "Records fields and schemas") + ("Missing schema competence",))
    without_validation = replace(adapter, required_competence_titles=tuple(title for title in adapter.required_competence_titles if title != "Validation rules") + ("Missing validation competence",))

    with pytest.raises(LiveAdapterBoundaryError, match="accepted_competence_missing"):
        compile_live_competence_context(tmp_path / "schema", mission, without_schema)
    with pytest.raises(LiveAdapterBoundaryError, match="accepted_competence_missing"):
        compile_live_competence_context(tmp_path / "validation", mission, without_validation)


def test_ambiguous_selection_stops_at_boundary():
    base = registered_live_task_adapters()[1]
    alternate = replace(base, adapter_id="structured_json_validation_alt")

    selection = select_live_task_adapter(_mission(JSON_TASK_CLASS, JSON_OBJECTIVE), adapters=(base, alternate))

    assert selection["selection_status"] == "ambiguous_adapter"
    assert selection["adapter_id"] == ""
    assert len(selection["compatible_adapters"]) == 2


def test_authority_limit_enforcement_rejects_provider_requiring_adapter():
    adapter = replace(registered_live_task_adapters()[1], authority_requirements={**registered_live_task_adapters()[1].authority_requirements, "provider_calls": 1})

    selection = select_live_task_adapter(_mission(JSON_TASK_CLASS, JSON_OBJECTIVE), adapters=(adapter,))

    assert selection["selection_status"] == "unsupported_task"


def test_json_adapter_runs_distinct_fixture_and_publishes_one_evaluation_item(tmp_path):
    root = tmp_path / "json"
    result = run_live_competence_json_validation_mission(root=root, reset=True)

    assert result["terminal_status"] == "LIVE_COMPETENCE_ADAPTER_JSON_MISSION_PASSED"
    assert result["adapter_id"] == "structured_json_validation"
    assert all(item["outcome"] == "passed" for item in result["case_results"])
    assert tuple(item["case_class"] for item in result["case_results"]) == JSON_CASE_CLASSES
    assert result["fixture_input_digests_before"] == result["fixture_input_digests_after"]
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 1
    assert not any(path.suffix == ".csv" for path in root.rglob("*"))
    assert result["provider_calls"] == 0
    assert result["retrieval_count"] == 1
    assert result["learner_calls"] == 1
    assert result["evaluator_calls"] == 1
    assert result["trusted_admissions"] == 0
    assert result["capability_promotions"] == 0
    assert result["mission_claim"] == "adapter-executed capability"
    assert result["adapter_capability_kind"] == "domain_semantics"
    assert result["adapter_semantic_operations_supplied"] == list(JSON_SEMANTIC_OPERATIONS)


def test_json_adapter_uses_context_without_claiming_developmental_json_competence(tmp_path):
    result = run_live_competence_json_validation_mission(root=tmp_path / "json", reset=True)

    titles = tuple(item["module_title"] for item in result["validated_prerequisites_used"])
    assert "Records fields and schemas" in titles
    assert "Validation rules" in titles
    assert "JSON serialization" not in titles
    assert "JSON serialization" in result["known_json_specific_unvalidated_concepts"]
    assert "nested object validation" in result["known_json_specific_unvalidated_concepts"]
    assert result["developmental_competencies_available"]
    assert result["developmental_competencies_used"] == []
    assert result["mission_can_run_from_existing_competence"] is True
    assert result["mission_claim"] == "adapter-executed capability"


def test_json_mission_output_cannot_read_sealed_expected_outcomes(tmp_path):
    root = tmp_path / "json"
    result = run_live_competence_json_validation_mission(root=root, reset=True)
    output = json.loads((root / "mission_output" / f"{result['output_id']}.json").read_text(encoding="utf-8"))

    assert "expected_report" not in output
    assert "expected_report_digest" not in output
    assert output["report"]["schema"] == "live_competence_json_validation_report_v1"
    assert output["mission_claim"] == "adapter-executed capability"
    assert output["adapter_capability_declaration_id"] == result["adapter_capability_declaration_id"]


def test_json_semantic_ablation_fails_while_infrastructure_still_publishes_output(tmp_path):
    root = tmp_path / "json"
    mission = _mission(JSON_TASK_CLASS, JSON_OBJECTIVE)
    adapter = registered_live_task_adapters()[1]
    fixture = create_json_fixture(root, reset=True)
    context = compile_live_competence_context(root, mission, adapter)
    validator = seal_json_validator(root, fixture)
    output = _json_mission_output(root, mission, context, semantic_enabled=False)
    evaluation = _validate_json_output(root, mission, fixture, validator, output)

    assert output["adapter_semantics_enabled"] is False
    assert output["report"]["schema"] == "live_competence_json_validation_report_v1"
    assert evaluation["aggregate_status"] == "failed"
    assert sum(1 for item in evaluation["case_results"] if item["outcome"] == "passed") == 0


def test_executor_and_evaluator_are_independent_artifacts(tmp_path):
    root = tmp_path / "json"
    mission = _mission(JSON_TASK_CLASS, JSON_OBJECTIVE)
    adapter = registered_live_task_adapters()[1]
    fixture = create_json_fixture(root, reset=True)
    context = compile_live_competence_context(root, mission, adapter)
    validator = seal_json_validator(root, fixture)
    good_output = _json_mission_output(root, mission, context)
    changed_output = {
        **good_output,
        "output_id": "changed-output",
        "artifact_digest": "changed-digest",
        "report": {"schema": "live_competence_json_validation_report_v1", "files": ()},
    }
    changed_validator = {
        **validator,
        "validator_id": "changed-validator",
        "artifact_digest": "changed-validator-digest",
        "expected_report": {"schema": "live_competence_json_validation_report_v1", "files": ()},
    }

    changed_output_eval = _validate_json_output(root, mission, fixture, validator, changed_output)
    changed_validator_eval = _validate_json_output(root, mission, fixture, changed_validator, good_output)

    assert changed_output_eval["aggregate_status"] == "failed"
    assert changed_validator_eval["aggregate_status"] == "failed"
    assert changed_output_eval["validator_digest"] == validator["artifact_digest"]
    assert changed_validator_eval["output_digest"] == good_output["artifact_digest"]


def test_json_negative_controls_are_discriminative(tmp_path):
    result = run_live_competence_json_validation_mission(root=tmp_path / "json", reset=True)

    assert result["negative_controls"]["empty"] == 0
    assert result["negative_controls"]["irrelevant"] == 0
    assert result["negative_controls"]["keyword_only"] == 0
    assert result["negative_controls"]["flat_field_only"] < len(JSON_CASE_CLASSES)
    assert result["negative_controls"]["unstructured"] == 0


def test_json_replay_and_restart_suppress_duplicate_execution_and_evaluation_item(tmp_path):
    root = tmp_path / "json"
    first = run_live_competence_json_validation_mission(root=root, reset=True)
    before = _inventory(root)

    replay = run_live_competence_json_validation_mission(root=root, reset=False)
    after = _inventory(root)

    assert replay["replay_suppressed"] is True
    assert replay["learner_calls"] == 0
    assert replay["evaluator_calls"] == 0
    assert replay["artifact_digest"] == first["artifact_digest"]
    assert replay["competence_context_digest"] == first["competence_context_digest"]
    assert replay["output_digest"] == first["output_digest"]
    assert replay["validation_digest"] == first["validation_digest"]
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 1
    assert before == after


def test_json_input_mutation_triggers_integrity_stop(tmp_path):
    root = tmp_path / "json"
    mission = _mission(JSON_TASK_CLASS, JSON_OBJECTIVE)
    adapter = registered_live_task_adapters()[1]
    fixture = create_json_fixture(root, reset=True)
    context = compile_live_competence_context(root, mission, adapter)
    validator = seal_json_validator(root, fixture)
    output = _json_mission_output(root, mission, context)

    (root / "inputs" / "valid_records.json").write_text('[{"id":1,"active":true,"profile":{"score":99}}]\n', encoding="utf-8")
    evaluation = _validate_json_output(root, mission, fixture, validator, output)

    assert evaluation["aggregate_status"] == "integrity_stop"
    assert evaluation["fixture_inputs_unchanged"] is False


def test_generic_adapter_blocks_unsupported_task_without_execution(tmp_path):
    result = run_live_competence_adapter_mission(root=tmp_path / "unsupported", task_class="spreadsheet_forecast", objective="Forecast rows.", reset=True)

    assert result["terminal_status"] == "LIVE_COMPETENCE_ADAPTER_BLOCKED"
    assert result["learner_calls"] == 0
    assert result["evaluator_calls"] == 0
