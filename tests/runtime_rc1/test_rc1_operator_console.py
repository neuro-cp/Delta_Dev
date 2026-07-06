from __future__ import annotations

import json

from orchestration.runtime.rc1_operator_console import (
    answer_operator_question,
    append_observation,
    approve_propositions,
    build_observation_entry,
    build_cognitive_state,
    build_operator_snapshot,
    extract_propositions,
    preview_evidence_ingest,
    validate_console_safe,
)
from orchestration.runtime.rc1_operator_console_report import build_operator_console_report


def test_operator_console_snapshot_is_safe():
    snapshot = build_operator_snapshot()
    assert validate_console_safe(snapshot)
    flags = snapshot["console_flags"]
    assert flags["provider_calls_enabled"] is False
    assert flags["training_enabled"] is False
    assert flags["canonical_writes_enabled"] is False
    assert flags["autonomous_actions_enabled"] is False


def test_operator_question_uses_local_routes_only():
    answer = answer_operator_question("What is DELTA Runtime v4.0 RC1?")
    assert answer["route"] == "rc1_release_candidate"
    assert answer["provider_calls_performed"] is False
    assert answer["training_performed"] is False
    assert answer["canonical_write_performed"] is False
    assert "release-candidate" in answer["answer"] or "release candidate" in answer["answer"]


def test_evidence_paste_preview_does_not_persist_or_upload():
    preview = preview_evidence_ingest("Evidence line one\nEvidence line two")
    assert preview["nonempty_lines"] == 2
    assert preview["persisted"] is False
    assert preview["canonical_write_performed"] is False
    assert preview["provider_calls_performed"] is False


def test_extract_propositions_is_review_only():
    extracted = extract_propositions("The sky is blue.\nProject Frontier has AI workers.")
    assert extracted["candidate_count"] == 2
    assert extracted["persisted"] is False
    assert extracted["canonical_write_performed"] is False
    assert extracted["candidates"][1]["claim"] == "Project Frontier has AI workers."


def test_approve_propositions_writes_only_local_noncanonical_store(tmp_path, monkeypatch):
    import orchestration.runtime.rc1_operator_console as console

    monkeypatch.setattr(console, "PROPOSITION_LOG", tmp_path / "props.jsonl")
    monkeypatch.setattr(console, "EVIDENCE_LOG", tmp_path / "evidence.jsonl")
    monkeypatch.setattr(console, "REPLAY_LOG", tmp_path / "replay.jsonl")
    extracted = extract_propositions("Project Frontier has AI workers.")
    result = approve_propositions(extracted["candidates"])
    state = build_cognitive_state()
    answer = answer_operator_question("What do you know about Frontier?")
    assert result["approved_count"] == 1
    assert result["canonical_write_performed"] is False
    assert result["provider_calls_performed"] is False
    assert state["noncanonical_propositions"] == 1
    assert state["replay_queue"] == 1
    assert answer["route"] == "rc1_noncanonical_substrate"
    assert "Project Frontier has AI workers." in answer["answer"]


def test_observation_logging_is_local_operational_log_only(tmp_path):
    entry = build_observation_entry("operator_friction", "The review button was unclear.", "P3")
    result = append_observation(entry, tmp_path / "observations.jsonl")
    assert result["written"] is True
    assert result["local_operational_log_only"] is True
    assert result["canonical_write_performed"] is False
    stored = json.loads((tmp_path / "observations.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert stored["category"] == "operator_friction"


def test_operator_console_report_is_safe():
    report = build_operator_console_report()
    assert report["safe"] is True
    assert "cognitive state home screen" in report["features"]
    assert "text paste evidence preview" in report["features"]
    assert "deterministic proposition extraction" in report["features"]
    assert "operator-approved noncanonical substrate write" in report["features"]
    assert report["final_recommendation"] == "USE_RC1_OPERATOR_CONSOLE_FOR_CONTROLLED_OPERATIONAL_OBSERVATION"
