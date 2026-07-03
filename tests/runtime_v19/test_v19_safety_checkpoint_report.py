from __future__ import annotations

from orchestration.runtime.v19_safety_checkpoint_report import build_v19_safety_checkpoint, validate_v19_safety_checkpoint, write_v19_safety_checkpoint_report


def test_checkpoint_contains_status_sections():
    data = build_v19_safety_checkpoint()
    assert data["status"]["local_console"] == "command_mode_non_mutating"
    assert data["status"]["recall"] == "candidate_context_only"
    assert validate_v19_safety_checkpoint(data)


def test_pipeline_is_updated():
    data = build_v19_safety_checkpoint()
    assert "UX-FIRST LOCAL DELTA CONSOLE" in data["pipeline_view"]
    assert "SESSION-TO-CANDIDATE MEMORY PROPOSAL FLOW" in data["pipeline_view"]


def test_safety_invariants_false():
    data = build_v19_safety_checkpoint()
    assert all(value is False for value in data["safety_invariants"].values())


def test_report_generation():
    data = write_v19_safety_checkpoint_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_V2_LOCAL_UX_CONSOLIDATION_OR_CONTROLLED_GENERAL_MEMORY_TRIAL"
