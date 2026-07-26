import json
from pathlib import Path

import pytest

from orchestration.runtime.autonomy_advisory_assistance import (
    _write_json,
    request_bounded_advice,
)
from orchestration.runtime.cognitive_evaluator_qualification import evaluate_stale_pass_observation
from orchestration.runtime.cognitive_replay_validity import (
    advisory_source_digest,
    build_advisory_replay_record,
    construct_record,
    deterministic_duplicate_key,
    evaluate_replay_validity,
    persist_consumed_before_success,
    read_record,
    replay_context_from_advisory,
    replay_validity_record_path,
    write_record,
)
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


PASSED = "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"
STOP = "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP"


def _request() -> dict[str, object]:
    return {
        "advisory_request_id": "request-1",
        "artifact_digest": "request-digest",
        "a17_packet_digest": "scope-1",
        "duplicate_key": "boundary-1",
    }


def _output() -> dict[str, object]:
    return {"advisory_output_id": "output-1", "artifact_digest": "artifact-digest", "schema": "autonomy_18_advisory_output_v1"}


def _audit() -> dict[str, object]:
    return {"accepted": True, "artifact_digest": "audit-digest", "created_at": "2026-07-25T00:00:00Z"}


def _write_existing(root: Path, *, report_status: str = PASSED, audit: dict[str, object] | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "advisory_output.json", _output())
    _write_json(root / "advisory_request.json", _request())
    _write_json(root / "grounding_audit.json", audit or _audit())
    _write_json(root / "report.json", {"status": report_status})


def _record(**overrides):
    base = build_advisory_replay_record(
        advisory_output=_output(),
        advisory_request=_request(),
        grounding_audit=_audit(),
        source_digest=advisory_source_digest(),
    )
    if not overrides:
        return base
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


def test_producer_record_creation_and_authority():
    record = _record()
    assert record.producer_id == "autonomy_18_validated_advisory_producer"
    assert record.validation_disposition == "validated_current"
    assert record.authority_scope == "inert_replay_validity_contract_only"
    assert record.provenance_refs


def test_explicit_validation_and_rejection_transition():
    current = _record()
    rejected = _record(rejection_record_id="reject-1", rejection_disposition="explicitly_rejected")
    assert evaluate_replay_validity(current, replay_context_from_advisory(record=current, advisory_request=_request(), source_digest=advisory_source_digest())).disposition == "eligible_current"
    assert evaluate_replay_validity(rejected, replay_context_from_advisory(record=rejected, advisory_request=_request(), source_digest=advisory_source_digest())).disposition == "blocked_rejected"


def test_source_invalidation_and_blocked_stale_behavior(tmp_path):
    _write_existing(tmp_path)
    stale = _record(source_digest="old-source")
    write_record(replay_validity_record_path(tmp_path), stale)
    result = request_bounded_advice(tmp_path)
    assert result["status"] == STOP
    assert result["reason"] == "blocked_stale"


def test_consumer_eligible_current_success_persists_before_success(tmp_path):
    _write_existing(tmp_path)
    write_record(replay_validity_record_path(tmp_path), _record())
    result = request_bounded_advice(tmp_path)
    stored = read_record(replay_validity_record_path(tmp_path))
    assert result["status"] == PASSED
    assert result["replay_validity"]["disposition"] == "eligible_current"
    assert stored.accepted_boundary_consumed is True


def test_generation_path_success_consumes_then_restart_blocks(packet_factory, tmp_path):
    packet = packet_factory(tmp_path)
    result = request_bounded_advice(tmp_path / "a18", packet=packet)
    replay = request_bounded_advice(tmp_path / "a18", packet=packet)
    assert result["status"] == PASSED
    assert read_record(replay_validity_record_path(tmp_path / "a18")).accepted_boundary_consumed is True
    assert replay["status"] == STOP
    assert replay["reason"] == "blocked_already_consumed"


def test_blocked_rejected_missing_provenance_and_invalid_validation(tmp_path):
    cases = [
        (_record(rejection_record_id="reject-1", rejection_disposition="explicitly_rejected"), "blocked_rejected"),
        (_record(provenance_refs=()), "blocked_missing_provenance"),
        (_record(validation_disposition="unknown"), "blocked_invalid_validation_state"),
    ]
    for index, (record, reason) in enumerate(cases):
        root = tmp_path / str(index)
        _write_existing(root)
        write_record(replay_validity_record_path(root), record)
        result = request_bounded_advice(root)
        assert result["status"] == STOP
        assert result["reason"] == reason


def test_one_time_consumption_idempotent_helper_and_distinct_replay_block(tmp_path):
    record = _record()
    context = replay_context_from_advisory(record=record, advisory_request=_request(), source_digest=advisory_source_digest())
    consumed, eligibility = persist_consumed_before_success(tmp_path / "record.json", record, context)
    assert eligibility.disposition == "eligible_current"
    assert consumed is not None
    again, blocked = persist_consumed_before_success(tmp_path / "record.json", consumed, context)
    assert again is None
    assert blocked.disposition == "blocked_already_consumed"


def test_duplicate_replay_identity_and_scope_distinction():
    record = _record()
    context = replay_context_from_advisory(record=record, advisory_request=_request(), source_digest=advisory_source_digest())
    key = deterministic_duplicate_key(record, context)
    duplicate = replay_context_from_advisory(record=record, advisory_request=_request(), source_digest=advisory_source_digest(), seen_duplicate_keys=(key,))
    changed_scope = replay_context_from_advisory(record=record, advisory_request={**_request(), "a17_packet_digest": "scope-2"}, source_digest=advisory_source_digest())
    assert evaluate_replay_validity(record, duplicate).disposition == "blocked_duplicate_replay"
    assert deterministic_duplicate_key(record, changed_scope) != key


def test_persistence_failure_blocks_success(monkeypatch, tmp_path):
    from orchestration.runtime import cognitive_replay_validity

    record = _record()
    context = replay_context_from_advisory(record=record, advisory_request=_request(), source_digest=advisory_source_digest())

    def fail_write(_path, _record):
        raise OSError("disk full")

    monkeypatch.setattr(cognitive_replay_validity, "write_record", fail_write)
    consumed, result = persist_consumed_before_success(tmp_path / "record.json", record, context)
    assert consumed is None
    assert result.disposition == "blocked_persistence_failure"


def test_restart_reconstruction_for_consumed_rejected_stale_and_corrupt(tmp_path):
    consumed_root = tmp_path / "consumed"
    _write_existing(consumed_root)
    write_record(replay_validity_record_path(consumed_root), _record())
    assert request_bounded_advice(consumed_root)["status"] == PASSED
    assert request_bounded_advice(consumed_root)["reason"] == "blocked_already_consumed"

    rejected_root = tmp_path / "rejected"
    _write_existing(rejected_root)
    write_record(replay_validity_record_path(rejected_root), _record(rejection_record_id="reject-1", rejection_disposition="explicitly_rejected"))
    assert request_bounded_advice(rejected_root)["reason"] == "blocked_rejected"

    stale_root = tmp_path / "stale"
    _write_existing(stale_root)
    write_record(replay_validity_record_path(stale_root), _record(source_digest="old"))
    assert request_bounded_advice(stale_root)["reason"] == "blocked_stale"

    corrupt_root = tmp_path / "corrupt"
    _write_existing(corrupt_root)
    replay_validity_record_path(corrupt_root).write_text("{bad", encoding="utf-8")
    assert request_bounded_advice(corrupt_root)["reason"] == "replay_validity_record_corrupt"


def test_missing_record_no_longer_stale_passes(tmp_path):
    _write_existing(tmp_path)
    result = request_bounded_advice(tmp_path)
    assert result["status"] == STOP
    assert result["reason"] == "replay_validity_record_missing"


def test_evaluator_digest_immutability_and_no_evaluator_authority():
    digest = json.loads(Path(".tmp/cognitive-evaluator-qualification-1/evaluator_source_digest.json").read_text(encoding="utf-8"))["digest"]
    assert digest == "ee33648e27532241b9078791a48f694c408c320d00041166c1863317742a0f73"
    observation = {"status": STOP, "reason": "blocked_already_consumed"}
    result = evaluate_stale_pass_observation(observation)
    assert result["classification"] == "valid_blocked_behavior"
    assert result["implementation_symbol_used"] is False


def test_no_arbitrary_freshness_threshold_or_payload_similarity_identity():
    source = Path("orchestration/runtime/autonomy_advisory_assistance.py").read_text(encoding="utf-8").lower()
    assert "freshness_seconds" not in source
    assert "max_age" not in source
    assert "payload_similarity" not in source


def test_proposal_and_amendment_immutability():
    amendment = json.loads(Path(".tmp/cognitive-replay-validity-contract-1/proposal_amendment_record.json").read_text(encoding="utf-8"))
    assert amendment["amendment_id"] == "cognitive-replay-validity-amendment-ffd2c0c8d7c3cd4b"
    assert amendment["amendment_digest"] == "9f7f5df0d1fc23b78a62b0c88416f0a5d026fc100b48d330d8fdf90865dec2d1"


@pytest.fixture
def packet_factory():
    from orchestration.runtime.autonomy_local_evidence import acquire_local_evidence, select_real_gap
    from orchestration.runtime.autonomy_mixed_mission import run_mixed_mission
    from tests.runtime_gsr.test_autonomy_13_task_scoped_activation import _competence_roots

    def make(tmp_path):
        roots = _competence_roots(tmp_path)
        mission_root = tmp_path / "mission"
        run_mixed_mission(mission_root, competence_roots=roots)
        gap = select_real_gap(mission_root / "gaps")
        return acquire_local_evidence(tmp_path / "a17", gap=gap)["packet"]

    return make
