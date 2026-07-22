from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.live_bootstrap_csv_mission import DEVELOPMENTAL_COMPETENCE_DIGEST, DEVELOPMENTAL_COMPETENCE_ID
from orchestration.runtime.live_general_competence_mission import (
    LIVE_GENERAL_1_ROOT,
    _mission,
    _work_items,
    run_live_general_1_mixed_validation_mission,
)


def _inventory(root: Path) -> tuple[str, ...]:
    return tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))


def test_live_general_1_decomposes_into_exact_three_item_graph():
    mission = _mission()
    items = _work_items(mission)

    assert tuple(item["label"] for item in items) == ("csv_validation", "json_validation", "comparative_synthesis")
    assert tuple(item["task_class"] for item in items) == ("csv_schema_validation", "structured_json_validation", "grounded_comparative_synthesis")
    assert items[2]["dependencies"] == ("csv_validation", "json_validation")


def test_live_general_1_runs_three_items_with_separate_capability_sources(tmp_path):
    root = tmp_path / "general"
    result = run_live_general_1_mixed_validation_mission(root=root, reset=True)

    assert result["terminal_status"] == "LIVE_GENERAL_1_MULTI_ITEM_MISSION_PASSED"
    assert len(result["work_items"]) == 3
    assert len(result["capability_resolutions"]) == 3
    sources = {item["label"]: item["selected_capability_source"] for item in result["capability_resolutions"]}
    assert sources == {
        "csv_validation": "developmentally_learned_competence",
        "json_validation": "declared_adapter_capability",
        "comparative_synthesis": "validated_bootstrap_competence",
    }
    assert result["selected_developmental_competence_id"] == DEVELOPMENTAL_COMPETENCE_ID
    assert result["selected_developmental_competence_digest"] == DEVELOPMENTAL_COMPETENCE_DIGEST
    assert result["selected_adapter_capability_id"] == "live-task-adapter-capability-68fa299e4b7c9a9e"


def test_live_general_1_preserves_csv_and_json_fixture_inputs(tmp_path):
    result = run_live_general_1_mixed_validation_mission(root=tmp_path / "general", reset=True)

    assert result["csv_input_digests_before"] == result["csv_input_digests_after"]
    assert result["json_input_digests_before"] == result["json_input_digests_after"]
    assert result["tracked_source_mutation"] is False


def test_live_general_1_publishes_exactly_one_evaluation_item_per_work_item(tmp_path):
    root = tmp_path / "general"
    result = run_live_general_1_mixed_validation_mission(root=root, reset=True)

    assert len(result["evaluation_item_ids"]) == 3
    assert len(set(result["evaluation_item_ids"])) == 3
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 3
    for path in (root / "evaluation_ui").glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["trusted_admission"] is False
        assert record["capability_promotion"] is False


def test_live_general_1_csv_and_json_validations_pass_all_cases(tmp_path):
    result = run_live_general_1_mixed_validation_mission(root=tmp_path / "general", reset=True)

    assert all(item["outcome"] == "passed" for item in result["outputs"]["csv"]["case_results"])
    assert all(item["outcome"] == "passed" for item in result["outputs"]["json"]["case_results"])
    assert len(result["outputs"]["csv"]["case_results"]) >= 7
    assert len(result["outputs"]["json"]["case_results"]) >= 8


def test_live_general_1_synthesis_is_grounded_and_attribution_safe(tmp_path):
    root = tmp_path / "general"
    result = run_live_general_1_mixed_validation_mission(root=root, reset=True)
    synthesis = json.loads((root / "synthesis_output" / f"{result['outputs']['synthesis']['output_id']}.json").read_text(encoding="utf-8"))

    assert synthesis["capability_origin_attribution"] == {
        "csv": "developmentally_learned_competence",
        "json": "declared_adapter_capability",
        "synthesis": "validated_bootstrap_competence",
    }
    assert "learned JSON competence" in json.dumps(synthesis)
    assert "not learned JSON competence" in json.dumps(synthesis)
    assert all(claim["citations"] for claim in synthesis["claims"])
    assert all(item["outcome"] == "passed" for item in result["outputs"]["synthesis"]["predicate_outcomes"])


def test_live_general_1_negative_controls_fail_without_evaluation_publication(tmp_path):
    root = tmp_path / "general"
    result = run_live_general_1_mixed_validation_mission(root=root, reset=True)

    assert set(result["negative_controls"]["csv"].values()) == {"failed", "integrity_stop"}
    assert set(result["negative_controls"]["json"].values()) == {"failed", "integrity_stop"}
    assert set(result["negative_controls"]["synthesis"].values()) == {"failed"}
    assert result["negative_controls"]["accepted_evaluation_items_created"] == 0
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 3


def test_live_general_1_replay_recovers_without_duplicate_execution_or_items(tmp_path):
    root = tmp_path / "general"
    first = run_live_general_1_mixed_validation_mission(root=root, reset=True)
    before = _inventory(root)

    replay = run_live_general_1_mixed_validation_mission(root=root, reset=False)
    after = _inventory(root)

    assert replay["replay_suppressed"] is True
    assert replay["artifact_digest"] == first["artifact_digest"]
    assert replay["replay_counters"] == {
        "csv_learner": 0,
        "json_adapter": 0,
        "synthesis": 0,
        "csv_evaluator": 0,
        "json_evaluator": 0,
        "synthesis_evaluator": 0,
    }
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 3
    assert before == after


def test_live_general_1_default_root_is_fresh_disposable_tmp_path():
    assert LIVE_GENERAL_1_ROOT.parts[0] == ".tmp"
    assert LIVE_GENERAL_1_ROOT.name == "live-general-1-mixed-validation-v1"
