"""Durable, shared exact-once lifecycle for approved local-model requests.

This module owns request/result state independently of a live conversation or
continuous mission.  Consumers retain identifiers only; they cannot mutate the
records or invoke the model outside the persisted claim-before-execution path.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.rc2_conversational_mode_router import execute_local_model_answer, select_model_lane


LEDGER_VERSION = 1
LEDGER_FILENAME = "local_model_request_result_ledger.json"
TERMINAL_STATES = frozenset({"completed", "unavailable", "failed", "interrupted", "rejected"})


def default_ledger_root() -> Path:
    configured = os.environ.get("DELTA_LOCAL_MODEL_LEDGER_ROOT", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / ".tmp" / "local_model_request_result_ledger"


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _record_digest(record: Mapping[str, Any], digest_field: str = "record_digest") -> str:
    return _digest({key: value for key, value in record.items() if key != digest_field})


class LocalModelRequestResultLedger:
    """A file-backed authoritative owner for local-model request lifecycles."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else default_ledger_root()
        self.path = self.root / LEDGER_FILENAME
        self._state = self._load_or_empty()
        self._recover_executing_records()

    def _empty_state(self) -> dict[str, Any]:
        return {"ledger_version": LEDGER_VERSION, "requests": {}, "results": {}, "state_digest": ""}

    def _state_with_digest(self, state: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(state)
        payload["state_digest"] = _digest({key: value for key, value in payload.items() if key != "state_digest"})
        return payload

    def _load_or_empty(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._state_with_digest(self._empty_state())
        try:
            state = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("local_model_ledger_state_unreadable") from exc
        if not isinstance(state, dict) or state.get("ledger_version") != LEDGER_VERSION:
            raise RuntimeError("local_model_ledger_schema_mismatch")
        expected = _digest({key: value for key, value in state.items() if key != "state_digest"})
        if state.get("state_digest") != expected:
            raise RuntimeError("local_model_ledger_state_digest_mismatch")
        for record in (state.get("requests") or {}).values():
            if not isinstance(record, dict) or record.get("record_digest") != _record_digest(record):
                raise RuntimeError("local_model_ledger_request_digest_mismatch")
        for result in (state.get("results") or {}).values():
            if not isinstance(result, dict) or result.get("result_digest") != _record_digest(result, "result_digest"):
                raise RuntimeError("local_model_ledger_result_digest_mismatch")
        return state

    def _persist(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        state = self._state_with_digest(self._state)
        encoded = json.dumps(state, indent=2, sort_keys=True) + "\n"
        fd, raw_path = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=self.root)
        temporary = Path(raw_path)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        self._state = state

    @staticmethod
    def _request_identity(*, semantic_identity: str, request_digest: str) -> str:
        return stable_id("shared-local-model-request", semantic_identity, request_digest)

    def _seal_request(self, record: Mapping[str, Any]) -> dict[str, Any]:
        updated = dict(record)
        updated["record_digest"] = _record_digest(updated)
        return updated

    def _seal_result(self, result: Mapping[str, Any]) -> dict[str, Any]:
        updated = dict(result)
        updated["result_digest"] = _record_digest(updated, "result_digest")
        return updated

    def _recover_executing_records(self) -> None:
        changed = False
        for request_id, record in list((self._state.get("requests") or {}).items()):
            if record.get("lifecycle_state") != "executing":
                continue
            updated = dict(record)
            updated.update({
                "lifecycle_state": "interrupted",
                "consumed_state": "terminal",
                "completed_at": utc_now(),
                "failure_classification": "interrupted_after_persisted_execution_claim",
            })
            self._state["requests"][request_id] = self._seal_request(updated)
            changed = True
        if changed:
            self._persist()

    def create_or_reuse_request(
        self,
        *,
        semantic_identity: str,
        question: str,
        requester_type: str,
        requester_reference: str = "",
        mission_id: str = "",
        session_reference: str = "",
        question_objective: str = "",
        lane: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_question = " ".join(str(question).split())
        selected_lane = dict(lane or select_model_lane(normalized_question, "analysis"))
        request_digest = _digest({"semantic_identity": semantic_identity, "question": normalized_question, "requester_type": requester_type, "question_objective": question_objective, "lane": selected_lane})
        existing = self.find_equivalent_request(semantic_identity, request_digest)
        if existing is not None:
            return existing
        request_id = self._request_identity(semantic_identity=semantic_identity, request_digest=request_digest)
        record = {
            "request_id": request_id, "semantic_identity": semantic_identity, "request_digest": request_digest,
            "requester_type": requester_type, "requester_reference": requester_reference, "mission_id": mission_id,
            "session_reference": session_reference, "question": normalized_question, "question_objective": question_objective,
            "selected_lane": selected_lane, "model_identity": str(selected_lane.get("selected_model_id") or selected_lane.get("selected_model") or ""),
            "adapter_identity": "rc2_conversational_mode_router.execute_local_model_answer",
            "authority_state": "operator_approval_required", "lifecycle_state": "pending_operator_approval",
            "execution_claim_id": "", "execution_attempt_count": 0, "consumed_state": "unconsumed",
            "created_at": utc_now(), "approved_at": "", "claimed_at": "", "completed_at": "",
            "failure_classification": "", "result_id": "", "record_version": LEDGER_VERSION,
        }
        self._state["requests"][request_id] = self._seal_request(record)
        self._persist()
        return self.get_request(request_id)

    def get_request(self, request_id: str) -> dict[str, Any]:
        record = (self._state.get("requests") or {}).get(request_id)
        if not isinstance(record, dict):
            raise KeyError(request_id)
        return dict(record)

    def find_equivalent_request(self, semantic_identity: str, request_digest: str) -> dict[str, Any] | None:
        for record in (self._state.get("requests") or {}).values():
            if record.get("semantic_identity") == semantic_identity and record.get("request_digest") == request_digest:
                return dict(record)
        return None

    def approve_request(self, request_id: str, approval_authority: str) -> dict[str, Any]:
        record = self.get_request(request_id)
        state = str(record.get("lifecycle_state") or "")
        if state == "approved":
            return record
        if state != "pending_operator_approval":
            raise RuntimeError("local_model_request_not_approvable")
        record.update({"lifecycle_state": "approved", "authority_state": approval_authority, "approved_at": utc_now()})
        self._state["requests"][request_id] = self._seal_request(record)
        self._persist()
        return self.get_request(request_id)

    def reject_request(self, request_id: str, reason: str = "operator_rejected") -> dict[str, Any]:
        record = self.get_request(request_id)
        if record.get("lifecycle_state") in TERMINAL_STATES:
            return record
        if record.get("lifecycle_state") != "pending_operator_approval":
            raise RuntimeError("local_model_request_not_rejectable")
        record.update({"lifecycle_state": "rejected", "consumed_state": "terminal", "completed_at": utc_now(), "failure_classification": reason})
        self._state["requests"][request_id] = self._seal_request(record)
        self._persist()
        return self.get_request(request_id)

    def claim_execution(self, request_id: str) -> dict[str, Any]:
        record = self.get_request(request_id)
        if record.get("lifecycle_state") != "approved" or int(record.get("execution_attempt_count") or 0) != 0:
            raise RuntimeError("local_model_request_not_claimable")
        record.update({"lifecycle_state": "executing", "execution_claim_id": stable_id("shared-local-model-execution-claim", request_id, utc_now()), "execution_attempt_count": 1, "claimed_at": utc_now(), "consumed_state": "claimed"})
        self._state["requests"][request_id] = self._seal_request(record)
        self._persist()
        return self.get_request(request_id)

    def _terminal(self, request_id: str, *, state: str, result: Mapping[str, Any] | None = None, failure: Mapping[str, Any] | None = None) -> dict[str, Any]:
        record = self.get_request(request_id)
        if record.get("lifecycle_state") in TERMINAL_STATES:
            return record
        if record.get("lifecycle_state") != "executing":
            raise RuntimeError("local_model_request_not_executing")
        now = utc_now()
        result_id = ""
        if result is not None:
            response = str(result.get("answer") or "")
            response_digest = _digest({"response": response})
            result_id = stable_id("shared-local-model-result", request_id, response_digest)
            result_record = {
                "result_id": result_id, "request_id": request_id,
                "model_identity": str(result.get("model_id") or record.get("model_identity") or ""),
                "adapter_identity": str(result.get("execution_adapter") or record.get("adapter_identity") or ""),
                "response_digest": response_digest, "response_reference": response,
                "latency_seconds": float(result.get("latency_seconds") or 0.0),
                "provenance": {"selected_lane": record.get("selected_lane") or {}, "execution_claim_id": record.get("execution_claim_id") or ""},
                "availability_state": "available" if state == "completed" else state,
                "failure_classification": "", "failure_detail": "",
                "execution_started_at": record.get("claimed_at") or "", "execution_completed_at": now,
                "terminal_state": state,
            }
            self._state["results"][result_id] = self._seal_result(result_record)
        detail = dict(failure or {})
        record.update({"lifecycle_state": state, "consumed_state": "terminal", "completed_at": now, "result_id": result_id, "failure_classification": str(detail.get("classification") or "")})
        self._state["requests"][request_id] = self._seal_request(record)
        self._persist()
        return self.get_request(request_id)

    def complete_request(self, request_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
        return self._terminal(request_id, state="completed", result=result)

    def fail_request(self, request_id: str, failure: Mapping[str, Any], *, unavailable: bool = False) -> dict[str, Any]:
        return self._terminal(request_id, state="unavailable" if unavailable else "failed", failure=failure)

    def mark_interrupted_request(self, request_id: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        return self._terminal(request_id, state="interrupted", failure=evidence)

    def execute_claimed_request(self, request_id: str, executor_context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        record = self.claim_execution(request_id)
        context = dict(executor_context or {})
        executor = context.get("executor")
        if executor is None:
            def executor(question: str, lane: dict[str, Any]) -> Mapping[str, Any]:
                return execute_local_model_answer(
                    question,
                    lane,
                    history=context.get("history"),
                    provider_manager=context.get("provider_manager"),
                )
        try:
            result = dict(executor(str(record["question"]), dict(record.get("selected_lane") or {})))
        except Exception as exc:
            return self.fail_request(request_id, {"classification": "local_model_execution_exception", "detail": repr(exc)})
        if not result.get("executed"):
            return self.fail_request(request_id, {"classification": str(result.get("reason") or "local_model_unavailable")}, unavailable=True)
        return self.complete_request(request_id, result)

    def observe_request(self, request_id: str) -> dict[str, Any]:
        return self.get_request(request_id)

    def observe_result(self, result_id: str) -> dict[str, Any]:
        result = (self._state.get("results") or {}).get(result_id)
        if not isinstance(result, dict):
            raise KeyError(result_id)
        return dict(result)

    def export_state(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._state))

    @classmethod
    def restore_state(cls, root: Path | str) -> "LocalModelRequestResultLedger":
        return cls(root)
