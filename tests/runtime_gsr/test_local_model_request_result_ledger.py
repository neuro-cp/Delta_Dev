from __future__ import annotations

import json

import pytest

from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


LANE = {"available": True, "lane": "reasoning", "selected_model_id": "local-test-model"}


def _request(ledger: LocalModelRequestResultLedger, *, semantic: str = "need-a") -> dict:
    return ledger.create_or_reuse_request(
        semantic_identity=semantic,
        question="Explain an isolated concept.",
        requester_type="test",
        requester_reference="test-reference",
        mission_id="mission-a",
        lane=LANE,
    )


def _executor(calls: list[str]):
    def run(question: str, lane: dict) -> dict:
        calls.append(question)
        return {"executed": True, "answer": "bounded local answer", "model_id": lane["selected_model_id"]}
    return run


def test_create_reuse_and_materially_distinct_request_are_durable(tmp_path):
    ledger = LocalModelRequestResultLedger(tmp_path)
    first = _request(ledger)
    assert _request(ledger)["request_id"] == first["request_id"]
    assert _request(ledger, semantic="need-b")["request_id"] != first["request_id"]
    assert (tmp_path / "local_model_request_result_ledger.json").exists()


def test_claim_is_persisted_before_single_execution_and_result_is_repeatable(tmp_path):
    ledger = LocalModelRequestResultLedger(tmp_path)
    request = _request(ledger)
    ledger.approve_request(request["request_id"], "operator_approved_one_use")
    calls: list[str] = []
    completed = ledger.execute_claimed_request(request["request_id"], {"executor": _executor(calls)})
    assert calls == ["Explain an isolated concept."]
    assert completed["lifecycle_state"] == "completed"
    result = ledger.observe_result(completed["result_id"])
    assert ledger.observe_result(completed["result_id"]) == result
    assert result["response_digest"]
    with pytest.raises(RuntimeError, match="not_claimable"):
        ledger.claim_execution(request["request_id"])


def test_claim_persistence_failure_prevents_executor(monkeypatch, tmp_path):
    ledger = LocalModelRequestResultLedger(tmp_path)
    request = _request(ledger)
    ledger.approve_request(request["request_id"], "operator")
    calls: list[str] = []
    monkeypatch.setattr(ledger, "_persist", lambda: (_ for _ in ()).throw(OSError("disk blocked")))
    with pytest.raises(OSError):
        ledger.execute_claimed_request(request["request_id"], {"executor": _executor(calls)})
    assert calls == []


def test_result_persistence_failure_recovers_as_interrupted_without_retry(monkeypatch, tmp_path):
    ledger = LocalModelRequestResultLedger(tmp_path)
    request = _request(ledger)
    ledger.approve_request(request["request_id"], "operator")
    ledger.claim_execution(request["request_id"])
    monkeypatch.setattr(ledger, "_persist", lambda: (_ for _ in ()).throw(OSError("result disk blocked")))
    with pytest.raises(OSError):
        ledger.complete_request(request["request_id"], {"executed": True, "answer": "answer", "model_id": "model"})
    restored = LocalModelRequestResultLedger(tmp_path)
    record = restored.get_request(request["request_id"])
    assert record["lifecycle_state"] == "interrupted"
    assert record["execution_attempt_count"] == 1
    with pytest.raises(RuntimeError, match="not_claimable"):
        restored.claim_execution(request["request_id"])


@pytest.mark.parametrize("terminal, result", [("failed", None), ("unavailable", None), ("completed", {"executed": True, "answer": "ok", "model_id": "m"})])
def test_terminal_records_restore_without_retry(tmp_path, terminal, result):
    ledger = LocalModelRequestResultLedger(tmp_path)
    request = _request(ledger)
    ledger.approve_request(request["request_id"], "operator")
    ledger.claim_execution(request["request_id"])
    if terminal == "completed":
        saved = ledger.complete_request(request["request_id"], result or {})
    else:
        saved = ledger.fail_request(request["request_id"], {"classification": terminal}, unavailable=terminal == "unavailable")
    restored = LocalModelRequestResultLedger.restore_state(tmp_path)
    assert restored.get_request(request["request_id"])["lifecycle_state"] == saved["lifecycle_state"]
    assert restored.get_request(request["request_id"])["execution_attempt_count"] == 1


def test_execution_failure_records_error_detail_and_attempt_state(tmp_path):
    ledger = LocalModelRequestResultLedger(tmp_path)
    request = _request(ledger)
    ledger.approve_request(request["request_id"], "operator")

    terminal = ledger.execute_claimed_request(
        request["request_id"],
        {"executor": lambda _question, _lane: {"executed": False, "reason": "local_model_runtime_unavailable"}},
    )

    assert terminal["lifecycle_state"] == "unavailable"
    assert terminal["failure_classification"] == "local_model_runtime_unavailable"
    assert terminal["failure_detail"] == "local_model_runtime_unavailable"
    assert terminal["error_present"] is True
    assert terminal["execution_started"] is True
    assert terminal["result_id"] == ""


def test_pending_and_approved_restore_and_executing_fails_closed(tmp_path):
    pending_root, approved_root, executing_root = (tmp_path / name for name in ("pending", "approved", "executing"))
    pending = LocalModelRequestResultLedger(pending_root)
    pending_request = _request(pending)
    assert LocalModelRequestResultLedger(pending_root).get_request(pending_request["request_id"])["lifecycle_state"] == "pending_operator_approval"
    approved = LocalModelRequestResultLedger(approved_root)
    approved_request = _request(approved)
    approved.approve_request(approved_request["request_id"], "operator")
    assert LocalModelRequestResultLedger(approved_root).get_request(approved_request["request_id"])["lifecycle_state"] == "approved"
    executing = LocalModelRequestResultLedger(executing_root)
    executing_request = _request(executing)
    executing.approve_request(executing_request["request_id"], "operator")
    executing.claim_execution(executing_request["request_id"])
    assert LocalModelRequestResultLedger(executing_root).get_request(executing_request["request_id"])["lifecycle_state"] == "interrupted"


def test_corrupt_state_fails_closed(tmp_path):
    path = tmp_path / "local_model_request_result_ledger.json"
    path.write_text(json.dumps({"ledger_version": 1, "requests": {}, "results": {}, "state_digest": "bad"}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="digest_mismatch"):
        LocalModelRequestResultLedger(tmp_path)
