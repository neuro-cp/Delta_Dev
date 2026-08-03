"""One operator-approved, source-bound curiosity inquiry through the shared ledger."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.local_model_execution_adapter import execute_local_model_inference
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger
from orchestration.runtime.provisional_semantic_consolidation import ProvisionalSemanticGraphState, record_associative_insight

SCHEMA_VERSION = "approved_curiosity_inquiry_v1"
FILENAME = "approved_curiosity_inquiries.json"
FIELDS = (
    "question_addressed",
    "evidence_considered",
    "bounded_answer",
    "uncertainty",
    "evidence_still_missing",
    "next_question",
)


@dataclass(frozen=True)
class CuriosityInquiry:
    inquiry_id: str
    candidate_id: str
    source_record_ids: tuple[str, ...]
    approval_request_id: str
    inquiry_question: str
    source_context: str = ""
    lifecycle_state: str = "curiosity_inquiry_queued"
    ledger_request_id: str = ""
    ledger_result_id: str = ""
    insight_experience_id: str = ""
    failure_reason: str = ""
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = SCHEMA_VERSION


def state_path(runtime_root: str | Path) -> Path:
    return Path(runtime_root) / "interactive-cognition" / FILENAME


def load_inquiries(runtime_root: str | Path) -> tuple[CuriosityInquiry, ...]:
    path = state_path(runtime_root)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(CuriosityInquiry(**{name: item.get(name, "") for name in CuriosityInquiry.__dataclass_fields__}) for item in payload.get("inquiries", ()) if isinstance(item, Mapping))


def save_inquiries(runtime_root: str | Path, records: tuple[CuriosityInquiry, ...]) -> None:
    path = state_path(runtime_root); path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent); temporary = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"schema_version": SCHEMA_VERSION, "inquiries": [asdict(item) for item in records]}, handle, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True); raise


def queue_inquiry(runtime_root: str | Path, graph: ProvisionalSemanticGraphState, *, candidate_id: str, source_record_ids: tuple[str, ...], approval_request_id: str, proposed_action: str, source_context: str = "") -> CuriosityInquiry:
    existing = next((item for item in load_inquiries(runtime_root) if item.candidate_id == candidate_id), None)
    if existing:
        return existing
    labels = {item.claim_version_id: item.exact_text[:240] for item in graph.claim_versions}
    question = (
        "Investigate only the bounded uncertainty below. Do not validate a claim or introduce a standing goal. "
        "Return JSON only with " + ", ".join(FIELDS) + ". "
        f"Observed pressure: {source_context or 'No additional source context was recorded.'} "
        f"Source records: {[labels.get(item, item) for item in source_record_ids]}. Approved action: {proposed_action}."
    )
    now = utc_now()
    record = CuriosityInquiry(
        stable_id("approved-curiosity-inquiry", candidate_id, approval_request_id),
        candidate_id,
        source_record_ids,
        approval_request_id,
        question,
        " ".join(source_context.split())[:1200],
        created_at=now,
        updated_at=now,
    )
    save_inquiries(runtime_root, load_inquiries(runtime_root) + (record,))
    return record


def execute_once(runtime_root: str | Path, graph: ProvisionalSemanticGraphState, inquiry: CuriosityInquiry, *, executor: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None) -> tuple[CuriosityInquiry, ProvisionalSemanticGraphState]:
    ledger = LocalModelRequestResultLedger(Path(runtime_root) / "model-ledger")
    request = ledger.create_or_reuse_request(semantic_identity=inquiry.inquiry_id, question=inquiry.inquiry_question, requester_type="approved_curiosity_inquiry", requester_reference=inquiry.candidate_id, question_objective="one bounded provisional curiosity inquiry")
    if request["lifecycle_state"] == "pending_operator_approval":
        request = ledger.approve_request(request["request_id"], f"approved_curiosity:{inquiry.approval_request_id}")
    running = replace(inquiry, lifecycle_state="curiosity_inquiry_running", ledger_request_id=str(request["request_id"]), updated_at=utc_now())
    if request["lifecycle_state"] == "approved":
        request = ledger.execute_claimed_request(request["request_id"], {"executor": executor or _execute})
    if request["lifecycle_state"] != "completed":
        return replace(running, lifecycle_state="curiosity_inquiry_failed", failure_reason=str(request.get("failure_classification") or request["lifecycle_state"]), updated_at=utc_now()), graph
    result = ledger.observe_result(str(request["result_id"]))
    try:
        parsed = json.loads(str(result.get("response_reference") or ""))
    except json.JSONDecodeError:
        parsed = {}
    if not isinstance(parsed, Mapping) or any(not str(parsed.get(field) or "").strip() for field in FIELDS):
        return replace(running, lifecycle_state="curiosity_inquiry_blocked", ledger_result_id=str(result["result_id"]), failure_reason="typed_output_invalid", updated_at=utc_now()), graph
    bridge = type("CuriosityBridge", (), {"exploration_id": inquiry.inquiry_id, "source_record_ids": inquiry.source_record_ids, "relation_edge_ids": (), "candidate_id": inquiry.candidate_id, "approval_request_id": inquiry.approval_request_id, "ledger_request_id": running.ledger_request_id})()
    graph, insight_id = record_associative_insight(
        graph,
        exploration=bridge,
        insight={
            "shared_structure": str(parsed["question_addressed"]),
            "evidence_considered": str(parsed["evidence_considered"]),
            "bounded_answer": str(parsed["bounded_answer"]),
            "possible_implication": str(parsed["bounded_answer"]),
            "relation_limits": str(parsed["evidence_still_missing"]),
            "uncertainty": str(parsed["uncertainty"]),
            "suggested_next_question": str(parsed["next_question"]),
        },
        ledger_result=result,
    )
    return replace(running, lifecycle_state="curiosity_inquiry_pending_consolidation", ledger_result_id=str(result["result_id"]), insight_experience_id=insight_id, updated_at=utc_now()), graph


def _execute(question: str, lane: Mapping[str, Any]) -> Mapping[str, Any]:
    model_name = str(lane.get("selected_model") or "")
    if not model_name:
        return {"executed": False, "reason": "no_local_model_available"}
    return execute_local_model_inference(model_name=model_name, prompt=question, task_type="active_cognitive_json_operation", metadata={"route": "approved_curiosity_inquiry", "execution_lane": "cognitive_operation", "operation_type": "approved_curiosity_inquiry"}, execution_adapter="approved_curiosity_inquiry.exact_prompt")


__all__ = ["CuriosityInquiry", "execute_once", "load_inquiries", "queue_inquiry", "save_inquiries"]
