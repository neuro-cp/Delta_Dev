from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.bootstrap_adjacent_learning import ACCEPTED_BOOTSTRAP_E_ROOT
from orchestration.runtime.live_bootstrap_csv_mission import (
    BOOTSTRAP_PREREQUISITE_TITLES,
    DEVELOPMENTAL_COMPETENCE_DIGEST,
    DEVELOPMENTAL_COMPETENCE_ID,
    LIVE_BOOTSTRAP_MISSION_ROOT,
    _mission_output,
    _mission_record,
    _validate_output,
    compile_competence_use_record,
    create_disposable_csv_fixture,
    run_live_bootstrap_csv_validation_mission,
    seal_live_validator,
)


CASE_COUNT = 8


def _json_inventory(root: Path) -> tuple[str, ...]:
    return tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))


def test_live_bootstrap_csv_mission_passes_with_disposable_fixture_and_no_mutation(tmp_path):
    root = tmp_path / "live"
    result = run_live_bootstrap_csv_validation_mission(root=root, reset=True)

    assert result["terminal_status"] == "LIVE_BOOTSTRAP_ATTENDED_MISSION_PASSED"
    assert all(item["outcome"] == "passed" for item in result["case_results"])
    assert result["fixture_input_digests_before"] == result["fixture_input_digests_after"]
    assert (root / "inputs").exists()
    assert (root / "schemas").exists()
    assert result["provider_calls"] == 0
    assert result["retrieval_count"] == 1
    assert result["learner_calls"] == 1
    assert result["evaluator_calls"] == 1
    assert result["trusted_admissions"] == 0
    assert result["capability_promotions"] == 0
    assert not any(path.suffix == ".py" for path in root.rglob("*"))


def test_live_bootstrap_competence_use_is_bound_to_accepted_bootstrap_and_bootstrap_f_competence(tmp_path):
    root = tmp_path / "live"
    result = run_live_bootstrap_csv_validation_mission(root=root, reset=True)

    assert Path(ACCEPTED_BOOTSTRAP_E_ROOT).exists()
    assert tuple(item["module_title"] for item in result["bootstrap_competencies_used"]) == BOOTSTRAP_PREREQUISITE_TITLES
    assert len(result["bootstrap_competencies_used"]) == len(BOOTSTRAP_PREREQUISITE_TITLES)
    assert tuple(result["developmental_competencies_used"]) == (
        {"competence_id": DEVELOPMENTAL_COMPETENCE_ID, "competence_digest": DEVELOPMENTAL_COMPETENCE_DIGEST},
    )

    competence_use_path = root / "competence_use" / f"{result['competence_use_id']}.json"
    competence_use = json.loads(competence_use_path.read_text(encoding="utf-8"))
    assert competence_use["curriculum_root"] == str(ACCEPTED_BOOTSTRAP_E_ROOT)
    assert competence_use["provisional_roots_used"] == []
    assert result["context_packet_id"].startswith("learner-visible-bootstrap-packet-")
    assert result["context_packet_digest"]


def test_live_bootstrap_negative_controls_are_discriminative(tmp_path):
    result = run_live_bootstrap_csv_validation_mission(root=tmp_path / "live", reset=True)

    assert result["negative_controls"]["empty"] == 0
    assert result["negative_controls"]["keyword_only"] == 0
    assert result["negative_controls"]["unstructured"] == 0
    assert result["negative_controls"]["missing_only"] < CASE_COUNT


def test_live_bootstrap_exact_once_replay_suppresses_execution_and_artifact_rewrites(tmp_path):
    root = tmp_path / "live"
    first = run_live_bootstrap_csv_validation_mission(root=root, reset=True)
    before = _json_inventory(root)

    replay = run_live_bootstrap_csv_validation_mission(root=root, reset=False)
    after = _json_inventory(root)

    assert replay["replay_suppressed"] is True
    assert replay["learner_calls"] == 0
    assert replay["evaluator_calls"] == 0
    assert replay["artifact_digest"] == first["artifact_digest"]
    assert replay["validation_digest"] == first["validation_digest"]
    assert before == after


def test_live_bootstrap_fixture_mutation_is_evaluator_integrity_failure(tmp_path):
    root = tmp_path / "live"
    fixture = create_disposable_csv_fixture(root, reset=True)
    validator = seal_live_validator(root, fixture)
    mission = _mission_record(root, fixture, validator)
    competence_use = compile_competence_use_record(root, mission)
    output = _mission_output(root, mission, competence_use)

    (root / "inputs" / "valid.csv").write_text("id,amount,active,note\n1,999,true,mutated\n", encoding="utf-8")
    evaluation = _validate_output(root, mission, fixture, validator, output)

    assert evaluation["aggregate_status"] == "failed"
    assert evaluation["fixture_inputs_unchanged"] is False


def test_live_bootstrap_default_root_is_disposable_tmp_path():
    assert LIVE_BOOTSTRAP_MISSION_ROOT.parts[0] == ".tmp"
