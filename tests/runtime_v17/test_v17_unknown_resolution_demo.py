from __future__ import annotations

from scripts.delta_v17_unknown_resolution_demo import build_unknown_resolution_demo, validate_unknown_resolution_demo_safe, write_unknown_resolution_demo_report


def test_demo_has_required_turns():
    data = build_unknown_resolution_demo()
    kinds = [turn["kind"] for turn in data["turns"]]
    assert kinds == [
        "local_known_question",
        "local_unknown_question",
        "provider_assisted_request_dry_run",
        "user_correction",
        "memory_candidate_pressure",
        "answer_synthesis_draft",
    ]
    assert validate_unknown_resolution_demo_safe(data)


def test_provider_request_is_dry_run():
    data = build_unknown_resolution_demo()
    provider_turn = data["turns"][2]
    assert provider_turn["decision"]["provider_call_performed"] is False
    assert provider_turn["provider_request"]["api_key_redacted"] is True
    assert validate_unknown_resolution_demo_safe(data)


def test_memory_candidate_pressure_does_not_write():
    data = build_unknown_resolution_demo()
    proposal = data["turns"][4]["memory_candidate_proposal"]
    assert proposal["canonical_write_performed"] is False
    assert proposal["requires_explicit_approval"] is True
    assert validate_unknown_resolution_demo_safe(data)


def test_no_training_recall_action_hyb1_or_scheduler():
    data = build_unknown_resolution_demo()
    flags = data["invariant_flags"]
    assert flags["training_triggered"] is False
    assert flags["recall_mutated"] is False
    assert flags["action_execution_performed"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["scheduler_enabled"] is False


def test_report_generation():
    data = write_unknown_resolution_demo_report()
    assert data["final_recommendation"] == "PROCEED_EVIDENCE_QUALITY_EVALUATION_HARNESS"
    assert validate_unknown_resolution_demo_safe(data)
