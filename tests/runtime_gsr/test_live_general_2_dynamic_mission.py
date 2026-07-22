from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.live_general_2_dynamic_mission import (
    LIVE_GENERAL_2_ROOT,
    RECONCILIATION_MISSING_CAPABILITY,
    _mission,
    _work_items,
    consume_reconciliation_operator_rejection,
    run_live_general_2_dynamic_resumption_mission,
    run_live_general_2_until_operator_boundary,
)


def _inventory(root: Path) -> tuple[str, ...]:
    return tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))


def test_live_general_2_decomposes_into_exact_four_item_graph():
    mission = _mission()
    items = _work_items(mission)

    assert tuple(item["label"] for item in items) == ("csv_validation", "json_validation", "cross_format_reconciliation", "dynamic_synthesis")
    assert tuple(item["task_class"] for item in items) == ("csv_schema_validation", "structured_json_validation", "cross_format_record_reconciliation", "grounded_dynamic_synthesis")
    assert items[3]["dependencies"] == ("csv_validation", "json_validation", "cross_format_reconciliation")


def test_live_general_2_independent_branches_continue_to_operator_boundary(tmp_path):
    root = tmp_path / "general2"
    state = run_live_general_2_until_operator_boundary(root=root, reset=True)

    terminal = {item["label"]: item["terminal_state"] for item in state["work_items"]}
    assert terminal["csv_validation"] == "completed"
    assert terminal["json_validation"] == "completed"
    assert terminal["cross_format_reconciliation"] == "blocked_learning_required"
    assert terminal["dynamic_synthesis"] == "interim_completed"
    assert len(state["evaluation_item_ids"]) == 2
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 2


def test_live_general_2_reconciliation_gap_is_genuine_and_singular_request(tmp_path):
    root = tmp_path / "general2"
    state = run_live_general_2_until_operator_boundary(root=root, reset=True)

    resolutions = {item["selected_capability_source"] for item in state["capability_resolutions"]}
    assert "missing_capability" in resolutions
    request = json.loads(next((root / "operator_request").glob("*.json")).read_text(encoding="utf-8"))
    assert request["missing_capability"] == RECONCILIATION_MISSING_CAPABILITY
    assert request["status"] == "active"
    assert len(tuple((root / "operator_request").glob("*.json"))) == 1
    assert len(tuple((root / "interim_synthesis").glob("*.json"))) == 1


def test_live_general_2_restart_while_blocked_is_exact(tmp_path):
    root = tmp_path / "general2"
    first = run_live_general_2_until_operator_boundary(root=root, reset=True)
    before = _inventory(root)

    replay = run_live_general_2_until_operator_boundary(root=root, reset=False)
    after = _inventory(root)

    assert replay["replay_suppressed"] is True
    assert replay["artifact_digest"] == first["artifact_digest"]
    assert replay["replay_counters"]["csv_learner"] == 0
    assert replay["replay_counters"]["json_adapter"] == 0
    assert replay["replay_counters"]["interim_synthesis"] == 0
    assert len(tuple((root / "operator_request").glob("*.json"))) == 1
    assert len(tuple((root / "interim_synthesis").glob("*.json"))) == 1
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 2
    assert before == after


def test_live_general_2_operator_rejection_is_consumed_once_and_finalizes(tmp_path):
    root = tmp_path / "general2"
    run_live_general_2_until_operator_boundary(root=root, reset=True)

    final = consume_reconciliation_operator_rejection(root=root)
    replay = consume_reconciliation_operator_rejection(root=root)

    assert final["terminal_status"] == "LIVE_GENERAL_2_DYNAMIC_RESUMPTION_PASSED"
    assert final["operator_disposition"] == "reject_reconciliation_branch"
    assert final["per_item_terminal_states"]["cross_format_reconciliation"] == "rejected"
    assert replay["replay_suppressed"] is True
    assert replay["artifact_digest"] == final["artifact_digest"]
    assert len(tuple((root / "operator_response").glob("*.json"))) == 1
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 4


def test_live_general_2_final_synthesis_does_not_claim_reconciliation_completed(tmp_path):
    root = tmp_path / "general2"
    final = run_live_general_2_dynamic_resumption_mission(root=root, reset=True)
    synthesis = json.loads((root / "final_synthesis" / f"{final['final_synthesis_id']}.json").read_text(encoding="utf-8"))

    assert synthesis["reconciliation"]["status"] == "rejected_by_operator"
    assert "no reconciliation claim established" in " ".join(synthesis["confidence_and_scope_limits"])
    assert synthesis["capability_origin_attribution"]["csv"] == "developmentally_learned_competence"
    assert synthesis["capability_origin_attribution"]["json"] == "declared_adapter_capability"
    assert synthesis["capability_origin_attribution"]["reconciliation"] == "rejected_by_operator"


def test_live_general_2_terminal_restart_exact_and_four_evaluation_items(tmp_path):
    root = tmp_path / "general2"
    first = run_live_general_2_dynamic_resumption_mission(root=root, reset=True)
    before = _inventory(root)

    replay = run_live_general_2_dynamic_resumption_mission(root=root, reset=False)
    after = _inventory(root)

    assert replay["replay_suppressed"] is True
    assert replay["replay_counters"] == {
        "csv_learner": 0,
        "json_adapter": 0,
        "interim_synthesis": 0,
        "reconciliation_learner": 0,
        "reconciliation_executor": 0,
        "final_synthesis": 0,
        "csv_evaluator": 0,
        "json_evaluator": 0,
        "reconciliation_evaluator": 0,
        "final_synthesis_evaluator": 0,
    }
    assert replay["artifact_digest"] == first["artifact_digest"]
    assert len(first["evaluation_item_ids"]) == 4
    assert len(tuple((root / "evaluation_ui").glob("*.json"))) == 4
    assert before == after


def test_live_general_2_preserves_inputs_and_rejects_negative_controls(tmp_path):
    final = run_live_general_2_dynamic_resumption_mission(root=tmp_path / "general2", reset=True)

    assert final["fixture_inputs_unchanged"] == {"csv": True, "json": True}
    assert set(final["negative_controls"]["csv"].values()) == {"failed", "integrity_stop"}
    assert set(final["negative_controls"]["json"].values()) == {"failed", "integrity_stop"}
    assert set(final["negative_controls"]["synthesis"].values()) == {"failed"}
    assert "not_accepted" in set(final["negative_controls"]["reconciliation"].values())
    assert final["negative_controls"]["accepted_evaluation_items_created"] == 0


def test_live_general_2_no_trust_promotion_or_tracked_source_mutation(tmp_path):
    root = tmp_path / "general2"
    final = run_live_general_2_dynamic_resumption_mission(root=root, reset=True)

    assert final["trusted_admissions"] == 0
    assert final["capability_promotions"] == 0
    assert final["tracked_source_mutation"] is False
    for path in (root / "evaluation_ui").glob("*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        assert item["trusted_admission"] is False
        assert item["capability_promotion"] is False


def test_live_general_2_default_root_is_fresh_disposable_tmp_path():
    assert LIVE_GENERAL_2_ROOT.parts[0] == ".tmp"
    assert LIVE_GENERAL_2_ROOT.name == "live-general-2-dynamic-branch-v1"
