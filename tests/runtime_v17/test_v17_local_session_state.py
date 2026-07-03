from __future__ import annotations

from orchestration.runtime.v17_local_session_state import add_local_session_turn, clear_local_session, validate_local_session_safe
from orchestration.runtime.v17_local_session_state_report import write_local_session_state_report


def test_multi_turn_context_works_locally(tmp_path):
    one = add_local_session_turn("s1", "What is Model B?", tmp_path)
    two = add_local_session_turn("s1", "Is HYB1 active?", tmp_path)
    assert len(two["session"]["turns"]) == 2
    assert "What is Model B?" in two["context_window"]["summary"]
    assert validate_local_session_safe(one)
    assert validate_local_session_safe(two)


def test_session_is_non_canonical_and_clear_removes(tmp_path):
    add_local_session_turn("s1", "hello", tmp_path)
    assert clear_local_session("s1", tmp_path) is True
    assert clear_local_session("s1", tmp_path) is False


def test_no_memory_recall_training_action_or_model_change(tmp_path):
    payload = add_local_session_turn("s1", "What is HYB1?", tmp_path)
    flags = payload["invariant_flags"]
    assert flags["canonical_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["action_execution_performed"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["hyb1_default_activation_enabled"] is False


def test_report_generation():
    data = write_local_session_state_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_PROVIDER_ASSISTED_UNKNOWN_ANSWER_PATH"
