import json
import subprocess
import sys
from pathlib import Path

import pytest

from orchestration.runtime.autonomy_advisory_assistance import _write_json, request_bounded_advice
from orchestration.runtime.cognitive_evaluator_qualification import evaluate_stale_pass_observation
from orchestration.runtime.cognitive_replay_validity import (
    advisory_source_digest,
    build_advisory_replay_record,
    construct_record,
    deterministic_duplicate_key,
    persist_consumed_before_success,
    read_record,
    replay_context_from_advisory,
    replay_validity_record_path,
    write_record,
)


PASSED = "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"
STOP = "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP"


def _request(scope: str = "scope-1") -> dict[str, object]:
    return {"advisory_request_id": f"request-{scope}", "artifact_digest": f"request-digest-{scope}", "a17_packet_digest": scope, "duplicate_key": f"boundary-{scope}"}


def _output() -> dict[str, object]:
    return {"advisory_output_id": "output-1", "artifact_digest": "artifact-digest", "schema": "autonomy_18_advisory_output_v1"}


def _audit() -> dict[str, object]:
    return {"accepted": True, "artifact_digest": "audit-digest", "created_at": "2026-07-25T00:00:00Z"}


def _existing(root: Path, *, scope: str = "scope-1") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "advisory_output.json", _output())
    _write_json(root / "advisory_request.json", _request(scope))
    _write_json(root / "grounding_audit.json", _audit())
    _write_json(root / "report.json", {"status": PASSED})


def _record(scope: str = "scope-1", **overrides):
    base = build_advisory_replay_record(advisory_output=_output(), advisory_request=_request(scope), grounding_audit=_audit(), source_digest=advisory_source_digest())
    data = base.as_record()
    data.update(overrides)
    return construct_record(
        artifact_id=data["artifact_id"],
        artifact_digest=data["artifact_digest"],
        evidence_scope_id=data["evidence_scope_id"],
        source_digest=data["source_digest"],
        validated_at=data["validated_at"],
        validation_disposition=data["validation_disposition"],
        rejection_record_id=data["rejection_record_id"],
        rejection_disposition=data["rejection_disposition"],
        accepted_boundary_id=data["accepted_boundary_id"],
        accepted_boundary_consumed=data["accepted_boundary_consumed"],
        consumed_at=data["consumed_at"],
        consumer_id=data["consumer_id"],
        producer_id=data["producer_id"],
        provenance_refs=data["provenance_refs"],
        authority_scope=data["authority_scope"],
    )


def _run_subprocess_replay(root: Path) -> dict[str, object]:
    code = (
        "import json, sys; "
        "from pathlib import Path; "
        "from orchestration.runtime.autonomy_advisory_assistance import request_bounded_advice; "
        "result=request_bounded_advice(Path(sys.argv[1])); "
        "print(json.dumps({'status': result.get('status'), 'reason': result.get('reason'), 'replay_validity': result.get('replay_validity')}, sort_keys=True))"
    )
    completed = subprocess.run((sys.executable, "-c", code, str(root)), check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def test_activation_current_success_then_immediate_and_restart_replay_block(tmp_path):
    root = tmp_path / "runtime-state" / "current"
    _existing(root)
    write_record(replay_validity_record_path(root), _record())
    first = request_bounded_advice(root)
    immediate = request_bounded_advice(root)
    restarted = _run_subprocess_replay(root)
    stored = read_record(replay_validity_record_path(root))
    assert first["status"] == PASSED
    assert first["replay_validity"]["disposition"] == "eligible_current"
    assert stored.accepted_boundary_consumed is True
    assert immediate["status"] == STOP and immediate["reason"] == "blocked_already_consumed"
    assert restarted["status"] == STOP and restarted["reason"] == "blocked_already_consumed"


def test_activation_typed_negative_cases_survive_restart(tmp_path):
    cases = [
        ("rejected", _record(rejection_record_id="reject-1", rejection_disposition="explicitly_rejected"), "blocked_rejected"),
        ("stale", _record(source_digest="old-source"), "blocked_stale"),
        ("missing_provenance", _record(provenance_refs=()), "blocked_missing_provenance"),
        ("invalid", _record(validation_disposition="unknown"), "blocked_invalid_validation_state"),
    ]
    for name, record, reason in cases:
        root = tmp_path / "runtime-state" / name
        _existing(root)
        write_record(replay_validity_record_path(root), record)
        first = request_bounded_advice(root)
        restarted = _run_subprocess_replay(root)
        assert first["status"] == STOP and first["reason"] == reason
        assert restarted["status"] == STOP and restarted["reason"] == reason


def test_activation_corrupt_state_never_becomes_eligible(tmp_path):
    root = tmp_path / "runtime-state" / "corrupt"
    _existing(root)
    replay_validity_record_path(root).write_text("{bad", encoding="utf-8")
    result = request_bounded_advice(root)
    restarted = _run_subprocess_replay(root)
    assert result["status"] == STOP and result["reason"] == "replay_validity_record_corrupt"
    assert restarted["status"] == STOP and restarted["reason"] == "replay_validity_record_corrupt"


def test_activation_distinct_evidence_scope_has_distinct_identity(tmp_path):
    first = _record("scope-1")
    second = _record("scope-2")
    first_context = replay_context_from_advisory(record=first, advisory_request=_request("scope-1"), source_digest=advisory_source_digest())
    second_context = replay_context_from_advisory(record=second, advisory_request=_request("scope-2"), source_digest=advisory_source_digest())
    assert deterministic_duplicate_key(first, first_context) != deterministic_duplicate_key(second, second_context)


def test_activation_persistence_failure_prevents_success(monkeypatch, tmp_path):
    from orchestration.runtime import cognitive_replay_validity

    record = _record()
    context = replay_context_from_advisory(record=record, advisory_request=_request(), source_digest=advisory_source_digest())

    def fail_write(_path, _record):
        raise OSError("controlled failure")

    monkeypatch.setattr(cognitive_replay_validity, "write_record", fail_write)
    consumed, result = persist_consumed_before_success(tmp_path / "record.json", record, context)
    assert consumed is None
    assert result.disposition == "blocked_persistence_failure"


def test_activation_unchanged_evaluator_classifies_corrected_behavior():
    retained = evaluate_stale_pass_observation({"status": PASSED})
    corrected = evaluate_stale_pass_observation({"status": STOP, "reason": "blocked_already_consumed"})
    assert retained["classification"] == "stale_pass_detected"
    assert corrected["classification"] == "valid_blocked_behavior"
    assert corrected["implementation_symbol_used"] is False
