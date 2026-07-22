from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.live_general_3_learning_mission import (
    LIVE_GENERAL_3_ROOT,
    NEW_RECONCILIATION_COMPETENCE_ID,
    approve_learning_request,
    run_live_general_3_approved_learning_mission,
    run_live_general_3_through_learning,
    run_live_general_3_until_blocked,
)


def _inventory(root: Path) -> tuple[str, ...]:
    return tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))


def test_live_general_3_starts_with_genuine_gap_and_singular_request(tmp_path):
    root = tmp_path / "general3"
    state = run_live_general_3_until_blocked(root=root, reset=True)

    terminal_states = {item["label"]: item["terminal_state"] for item in state["work_items"]}
    assert terminal_states["csv_validation"] == "completed"
    assert terminal_states["json_validation"] == "completed"
    assert terminal_states["cross_format_reconciliation"] == "blocked_learning_required"
    assert terminal_states["dynamic_synthesis"] == "interim_completed"
    assert len(tuple((root / "operator_request").glob("*.json"))) == 1
    assert len(tuple((root / "interim_synthesis").glob("*.json"))) == 1
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 2


def test_live_general_3_blocked_restart_has_zero_reruns(tmp_path):
    root = tmp_path / "general3"
    first = run_live_general_3_until_blocked(root=root, reset=True)
    before = _inventory(root)

    replay = run_live_general_3_until_blocked(root=root, reset=False)
    after = _inventory(root)

    assert replay["replay_suppressed"] is True
    assert replay["artifact_digest"] == first["artifact_digest"]
    assert replay["replay_counters"]["csv_learner"] == 0
    assert replay["replay_counters"]["json_adapter"] == 0
    assert replay["replay_counters"]["interim_synthesis"] == 0
    assert before == after


def test_live_general_3_approval_is_scoped_and_consumed_once(tmp_path):
    root = tmp_path / "general3"
    run_live_general_3_until_blocked(root=root, reset=True)
    approval = approve_learning_request(root=root)
    learning = run_live_general_3_through_learning(root=root)
    replay = run_live_general_3_through_learning(root=root)

    assert approval["operator_disposition"] == "approve_one_bounded_learning_attempt"
    assert learning["approval_id"] == approval["approval_id"]
    assert learning["request_active_after_approval"] is False
    assert learning["approval_scope"] == "cross_format_record_reconciliation_only"
    assert replay["artifact_digest"] == learning["artifact_digest"]
    assert len(tuple((root / "operator_approval").glob("*.json"))) == 1
    assert len(tuple((root / "operator_approval_consumed").glob("*.json"))) == 1


def test_live_general_3_learning_pass_creates_one_untrusted_developmental_competence(tmp_path):
    root = tmp_path / "general3"
    run_live_general_3_until_blocked(root=root, reset=True)
    learning = run_live_general_3_through_learning(root=root)
    competence = json.loads((root / "developmental_competence" / f"{NEW_RECONCILIATION_COMPETENCE_ID}.json").read_text(encoding="utf-8"))

    assert learning["learning_result"] == "passed"
    assert learning["new_competence_id"] == NEW_RECONCILIATION_COMPETENCE_ID
    assert competence["classification"] == "developmentally_learned_competence"
    assert competence["trusted"] is False
    assert competence["promoted"] is False
    assert len(tuple((root / "developmental_competence").glob("*.json"))) == 1


def test_live_general_3_learning_evaluator_and_attempt_are_independent_artifacts(tmp_path):
    root = tmp_path / "general3"
    run_live_general_3_until_blocked(root=root, reset=True)
    learning = run_live_general_3_through_learning(root=root)
    evaluator = json.loads((root / "learning_evaluator" / f"{learning['evaluator_package_id']}.json").read_text(encoding="utf-8"))
    attempt = json.loads((root / "learning_attempt" / f"{learning['learner_attempt_id']}.json").read_text(encoding="utf-8"))

    assert evaluator["sealed_before_learner_attempt"] is True
    assert "expected_matches" in evaluator["hidden_fields"]
    assert "expected_matches" not in json.dumps(attempt)
    assert attempt["evaluator_package_digest"] == evaluator["artifact_digest"]


def test_live_general_3_terminal_passes_with_reconciliation_execution_once(tmp_path):
    root = tmp_path / "general3"
    final = run_live_general_3_approved_learning_mission(root=root, reset=True)

    assert final["terminal_status"] == "LIVE_GENERAL_3_APPROVED_LEARNING_RESUMPTION_PASSED"
    assert final["new_developmental_competence_id"] == NEW_RECONCILIATION_COMPETENCE_ID
    assert final["counts"]["reconciliation_learner"] == 1
    assert final["counts"]["reconciliation_executor"] == 1
    assert final["counts"]["evaluators"]["learning"] == 1
    assert final["counts"]["evaluators"]["reconciliation"] == 1
    assert len(final["evaluation_item_ids"]) == 4
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 4


def test_live_general_3_final_synthesis_is_distinct_from_interim(tmp_path):
    root = tmp_path / "general3"
    final = run_live_general_3_approved_learning_mission(root=root, reset=True)

    assert final["final_synthesis_digest"] != final["interim_synthesis_digest"]
    synthesis = json.loads((root / "final_synthesis" / f"{final['final_synthesis_id']}.json").read_text(encoding="utf-8"))
    assert synthesis["learning_disposition"] == "passed"
    assert synthesis["reconciliation"]["status"] == "passed"
    assert synthesis["reconciliation"]["capability_source"] == "developmentally_learned_competence"


def test_live_general_3_terminal_restart_has_zero_reruns_and_preserves_graph(tmp_path):
    root = tmp_path / "general3"
    first = run_live_general_3_approved_learning_mission(root=root, reset=True)
    before = _inventory(root)

    replay = run_live_general_3_approved_learning_mission(root=root, reset=False)
    after = _inventory(root)

    assert replay["replay_suppressed"] is True
    assert replay["artifact_digest"] == first["artifact_digest"]
    assert replay["replay_counters"] == {
        "csv_learner": 0,
        "json_adapter": 0,
        "interim_synthesis": 0,
        "reconciliation_learner": 0,
        "reconciliation_executor": 0,
        "final_synthesis": 0,
        "csv_evaluator": 0,
        "json_evaluator": 0,
        "learning_evaluator": 0,
        "reconciliation_evaluator": 0,
        "final_synthesis_evaluator": 0,
    }
    assert len(replay["evaluation_item_ids"]) == 4
    assert before == after


def test_live_general_3_preserves_inputs_and_governance_boundaries(tmp_path):
    final = run_live_general_3_approved_learning_mission(root=tmp_path / "general3", reset=True)

    assert final["fixture_inputs_unchanged"] == {"csv": True, "json": True}
    assert final["trusted_admissions"] == 0
    assert final["capability_promotions"] == 0
    assert final["tracked_source_mutation"] is False
    assert final["negative_controls"]["learning"]["positional_matching"] == "failed"
    assert final["negative_controls"]["reconciliation"]["fixture_mutation"] == "integrity_stop"


def test_live_general_3_default_root_is_fresh_disposable_tmp_path():
    assert LIVE_GENERAL_3_ROOT.parts[0] == ".tmp"
    assert LIVE_GENERAL_3_ROOT.name == "live-general-3-approved-learning-v1"
