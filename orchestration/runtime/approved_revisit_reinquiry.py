"""One-call reinquiry for an operator-approved consolidation revisit.

This is deliberately only an operation record.  Review truth remains in the
provisional graph, operator approval remains a chat request, and execution
remains in the shared local-model ledger.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Callable, Mapping

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.local_model_execution_adapter import execute_local_model_inference
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger
from orchestration.runtime.provisional_semantic_consolidation import (
    ProvisionalSemanticGraphState,
    SemanticExperience,
    record_revised_associative_insight,
)


SCHEMA_VERSION = "approved_revisit_reinquiry_v1"
FILENAME = "approved_revisit_reinquiries.json"


@dataclass(frozen=True)
class RevisitReinquiry:
    reinquiry_id: str
    candidate_id: str
    approval_request_id: str
    original_insight_id: str
    review_id: str
    packet_id: str
    overlay_id: str
    source_context: str
    inquiry_question: str
    lifecycle_state: str = "revisit_queued"
    ledger_request_id: str = ""
    ledger_result_id: str = ""
    revised_insight_id: str = ""
    failure_reason: str = ""
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = SCHEMA_VERSION


def state_path(runtime_root: str | Path) -> Path:
    return Path(runtime_root) / "interactive-cognition" / FILENAME


def load_reinquiries(runtime_root: str | Path) -> tuple[RevisitReinquiry, ...]:
    path = state_path(runtime_root)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(RevisitReinquiry(**{key: item.get(key, "") for key in RevisitReinquiry.__dataclass_fields__}) for item in payload.get("reinquiries", ()) if isinstance(item, Mapping))


def save_reinquiries(runtime_root: str | Path, records: tuple[RevisitReinquiry, ...]) -> None:
    path = state_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"schema_version": SCHEMA_VERSION, "reinquiries": [asdict(item) for item in records]}, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def queue_reinquiry(runtime_root: str | Path, *, candidate_id: str, approval_request_id: str, original_insight_id: str, review_id: str, packet_id: str, overlay_id: str, weakness: str, source_context: str = "") -> RevisitReinquiry:
    records = load_reinquiries(runtime_root)
    existing = next((item for item in records if item.candidate_id == candidate_id), None)
    if existing:
        return existing
    now = utc_now()
    record = RevisitReinquiry(
        reinquiry_id=stable_id("approved-revisit-reinquiry", candidate_id, approval_request_id, review_id),
        candidate_id=candidate_id, approval_request_id=approval_request_id, original_insight_id=original_insight_id,
        review_id=review_id, packet_id=packet_id, overlay_id=overlay_id,
        source_context=" ".join(str(source_context).split())[:1800],
        inquiry_question=("Return JSON only with revised_proposition, retained_supported_portion, discarded_or_corrected_portion, evidence_still_missing, uncertainty, and possible_next_question. "
                          f"Revise this provisional insight without claiming validation. Original provisional context: {source_context[:1200]}. Review weakness: {weakness}"),
        created_at=now, updated_at=now,
    )
    save_reinquiries(runtime_root, records + (record,))
    return record


def execute_once(runtime_root: str | Path, graph: ProvisionalSemanticGraphState, reinquiry: RevisitReinquiry, *, executor: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None) -> tuple[RevisitReinquiry, ProvisionalSemanticGraphState]:
    ledger = LocalModelRequestResultLedger(Path(runtime_root) / "model-ledger")
    request = ledger.create_or_reuse_request(semantic_identity=reinquiry.reinquiry_id, question=reinquiry.inquiry_question, requester_type="approved_revisit_reinquiry", requester_reference=reinquiry.candidate_id, question_objective="one bounded provisional revision inquiry")
    if request["lifecycle_state"] == "pending_operator_approval":
        request = ledger.approve_request(request["request_id"], f"approved_revisit:{reinquiry.approval_request_id}")
    running = replace(reinquiry, lifecycle_state="revisit_running", ledger_request_id=str(request["request_id"]), updated_at=utc_now())
    if request["lifecycle_state"] == "approved":
        request = ledger.execute_claimed_request(request["request_id"], {"executor": executor or _execute_revisit_inquiry})
    if request["lifecycle_state"] != "completed":
        state = "revisit_interrupted_indeterminate" if request["lifecycle_state"] == "interrupted" else "revisit_failed_execution"
        return replace(running, lifecycle_state=state, failure_reason=str(request.get("failure_classification") or request["lifecycle_state"]), updated_at=utc_now()), graph
    result = ledger.observe_result(str(request["result_id"]))
    parsed = _parse(str(result.get("response_reference") or ""), reinquiry)
    if parsed is None:
        return replace(running, lifecycle_state="revisit_blocked_invalid_output", ledger_result_id=str(result["result_id"]), failure_reason="typed_output_invalid", updated_at=utc_now()), graph
    insight_id = stable_id("semantic-experience", "revised-associative-insight", reinquiry.reinquiry_id)
    if not any(item.experience_id == insight_id for item in graph.experiences):
        content = json.dumps(parsed, sort_keys=True)
        experience = SemanticExperience(
            insight_id, "local_model_output", "model_generated_revised_provisional_insight", content,
            (reinquiry.original_insight_id, reinquiry.review_id, reinquiry.packet_id, reinquiry.overlay_id, reinquiry.candidate_id),
            utc_now(), "sha256:" + sha256(content.encode("utf-8")).hexdigest(),
            {"record_kind": "revised_provisional_associative_insight", "epistemic_state": "pending_consolidation", "revises_insight_id": reinquiry.original_insight_id, "review_id": reinquiry.review_id, "packet_id": reinquiry.packet_id, "overlay_id": reinquiry.overlay_id, "ledger_request_id": running.ledger_request_id, "ledger_result_id": str(result["result_id"])},
        )
        graph, _ = record_revised_associative_insight(
            graph,
            experience=experience,
            original_insight_id=reinquiry.original_insight_id,
        )
    return replace(running, lifecycle_state="revisited_pending_consolidation", ledger_result_id=str(result["result_id"]), revised_insight_id=insight_id, updated_at=utc_now()), graph


def _parse(raw: str, reinquiry: RevisitReinquiry) -> dict[str, str] | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        labels = (
            ("revised_proposition", "revised[_ ]proposition"),
            ("retained_supported_portion", "retained[_ ]supported[_ ]portion"),
            ("discarded_or_corrected_portion", "discarded[_ ]or[_ ]corrected[_ ]portion"),
            ("evidence_still_missing", "evidence[_ ]still[_ ]missing"),
            ("uncertainty", "uncertainty"),
            ("possible_next_question", "possible[_ ]next[_ ]question"),
            ("possible_implication", "possible[_ ]implication"),
            ("relation_limits", "relation[_ ]limits"),
        )
        data = {}
        for match in re.finditer(r"(?:^|[.;\n])\s*([a-z_ ]+)\s*:\s*(.+?)(?=(?:[.;\n]\s*[a-z_ ]+\s*:)|$)", raw, flags=re.IGNORECASE | re.DOTALL):
            field = re.sub(r"[^a-z]", "", match.group(1).lower())
            for key, label in labels:
                if re.sub(r"[^a-z]", "", re.sub(r"\[.*?\]", "", label)) == field:
                    data[key] = match.group(2).strip(" .")
                    break
    # The established association contract uses these two labels for the same
    # revision dimensions. Normalize them before enforcing the revisit schema.
    if not str(data.get("retained_supported_portion") or "").strip() and str(data.get("possible_implication") or "").strip():
        data["retained_supported_portion"] = data["possible_implication"]
    if not str(data.get("discarded_or_corrected_portion") or "").strip() and str(data.get("relation_limits") or "").strip():
        data["discarded_or_corrected_portion"] = data["relation_limits"]
    keys = ("revised_proposition", "retained_supported_portion", "discarded_or_corrected_portion", "evidence_still_missing", "uncertainty", "possible_next_question")
    if not isinstance(data, Mapping) or any(not str(data.get(key) or "").strip() for key in keys): return None
    combined = " ".join(str(data[key]) for key in keys).lower()
    if "validated" in combined or "operator approved" in combined or re.search(r"\bcertain(?:ty)?\b", combined): return None
    anchors = {token for token in re.findall(r"[a-z]{5,}", reinquiry.source_context.lower()) if token not in {"original", "provisional", "possible", "relation", "review", "through", "because"}}
    if anchors and not anchors.intersection(re.findall(r"[a-z]{5,}", combined)):
        return None
    return {key: " ".join(str(data[key]).split())[:1200] for key in keys}


def _execute_revisit_inquiry(question: str, lane: Mapping[str, Any]) -> Mapping[str, Any]:
    """Use the shared exact-prompt cognitive lane for the revisit schema."""
    model_name = str(lane.get("selected_model") or "")
    if not model_name:
        return {"executed": False, "reason": "no_local_model_available"}
    return execute_local_model_inference(
        model_name=model_name,
        prompt=question,
        task_type="active_cognitive_json_operation",
        metadata={
            "route": "approved_revisit_reinquiry",
            "lane": lane.get("lane"),
            "execution_lane": "cognitive_operation",
            "operation_type": "approved_revisit_reinquiry",
        },
        execution_adapter="approved_revisit_reinquiry.exact_prompt",
    )
