"""One-call, operator-approved exploration of an explicit graph association.

This coordinator intentionally owns only operation state.  Conversation owns
approval, the shared ledger owns model execution, and the provisional graph
owns the resulting evidence record.
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
    record_associative_insight,
)


SCHEMA_VERSION = "approved_association_exploration_v1"
FILENAME = "approved_association_explorations.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AssociationExploration:
    exploration_id: str
    candidate_id: str
    originating_thread_id: str
    source_record_ids: tuple[str, ...]
    relation_edge_ids: tuple[str, ...]
    approval_request_id: str
    inquiry_question: str
    source_context: tuple[str, ...] = ()
    lifecycle_state: str = "exploration_queued"
    ledger_request_id: str = ""
    ledger_result_id: str = ""
    insight_experience_id: str = ""
    failure_reason: str = ""
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = SCHEMA_VERSION


def state_path(runtime_root: str | Path) -> Path:
    return Path(runtime_root) / "interactive-cognition" / FILENAME


def load_explorations(runtime_root: str | Path) -> tuple[AssociationExploration, ...]:
    path = state_path(runtime_root)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(AssociationExploration(
        exploration_id=str(item["exploration_id"]), candidate_id=str(item["candidate_id"]),
        originating_thread_id=str(item.get("originating_thread_id") or ""),
        source_record_ids=tuple(item.get("source_record_ids") or ()), relation_edge_ids=tuple(item.get("relation_edge_ids") or ()),
        approval_request_id=str(item.get("approval_request_id") or ""), source_context=tuple(item.get("source_context") or ()), inquiry_question=str(item.get("inquiry_question") or ""),
        lifecycle_state=str(item.get("lifecycle_state") or "exploration_queued"), ledger_request_id=str(item.get("ledger_request_id") or ""),
        ledger_result_id=str(item.get("ledger_result_id") or ""), insight_experience_id=str(item.get("insight_experience_id") or ""),
        failure_reason=str(item.get("failure_reason") or ""), created_at=str(item.get("created_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
    ) for item in payload.get("explorations", ()) if isinstance(item, Mapping))


def save_explorations(runtime_root: str | Path, records: tuple[AssociationExploration, ...]) -> None:
    path = state_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": SCHEMA_VERSION, "explorations": [asdict(item) for item in records]}
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def build_inquiry_question(graph: ProvisionalSemanticGraphState, source_ids: tuple[str, ...], edge_ids: tuple[str, ...]) -> str:
    versions = {item.claim_version_id: item.exact_text for item in graph.claim_versions}
    excerpts = [versions.get(item, item)[:240] for item in source_ids]
    return (
        "Explore only the explicit dependency below. Do not introduce unrelated topics or claim validation. "
        "Return exactly one JSON object with these five string fields and nothing else: "
        "shared_structure, possible_implication, relation_limits, uncertainty, suggested_next_question. "
        "Each field must be grounded in both source records. "
        "The uncertainty field must name a concrete condition the source records do not establish; do not say there is no uncertainty. "
        f"Source records: {excerpts}. Relation edges: {list(edge_ids)}."
    )


def queue_exploration(
    runtime_root: str | Path, graph: ProvisionalSemanticGraphState, *, candidate_id: str, originating_thread_id: str,
    source_record_ids: tuple[str, ...], relation_edge_ids: tuple[str, ...], approval_request_id: str,
) -> AssociationExploration:
    records = load_explorations(runtime_root)
    existing = next((item for item in records if item.candidate_id == candidate_id), None)
    if existing is not None:
        return existing
    now = utc_now()
    versions = {item.claim_version_id: item.exact_text for item in graph.claim_versions}
    record = AssociationExploration(
        exploration_id=stable_id("association-exploration", candidate_id, approval_request_id), candidate_id=candidate_id,
        originating_thread_id=originating_thread_id, source_record_ids=source_record_ids, relation_edge_ids=relation_edge_ids,
        approval_request_id=approval_request_id,
        source_context=tuple(versions.get(item, item)[:240] for item in source_record_ids),
        inquiry_question=build_inquiry_question(graph, source_record_ids, relation_edge_ids),
        created_at=now, updated_at=now,
    )
    save_explorations(runtime_root, records + (record,))
    return record


def execute_once(
    runtime_root: str | Path, graph: ProvisionalSemanticGraphState, exploration: AssociationExploration,
    *, executor: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> tuple[AssociationExploration, ProvisionalSemanticGraphState]:
    """Execute the one allowed call and return a graph with an insight only on valid output."""
    ledger = LocalModelRequestResultLedger(Path(runtime_root) / "model-ledger")
    request = ledger.create_or_reuse_request(
        semantic_identity=exploration.exploration_id, question=exploration.inquiry_question,
        requester_type="approved_association_exploration", requester_reference=exploration.candidate_id,
        question_objective="one bounded provisional association inquiry",
    )
    if request["lifecycle_state"] == "pending_operator_approval":
        request = ledger.approve_request(request["request_id"], f"approved_association:{exploration.approval_request_id}")
    now = utc_now()
    running = replace(exploration, lifecycle_state="exploration_running", ledger_request_id=request["request_id"], updated_at=now)
    if request["lifecycle_state"] == "approved":
        request = ledger.execute_claimed_request(
            request["request_id"],
            {"executor": executor or _execute_source_bound_inquiry},
        )
    if request["lifecycle_state"] != "completed":
        lifecycle = "exploration_interrupted_indeterminate" if request["lifecycle_state"] == "interrupted" else "exploration_failed"
        return replace(running, lifecycle_state=lifecycle, failure_reason=str(request.get("failure_classification") or request["lifecycle_state"]), updated_at=utc_now()), graph
    result = ledger.observe_result(str(request["result_id"]))
    insight = _parse_insight(str(result.get("response_reference") or ""), exploration)
    if insight is None:
        return replace(running, lifecycle_state="exploration_blocked", ledger_result_id=str(result["result_id"]), failure_reason="typed_output_invalid", updated_at=utc_now()), graph
    updated_graph, experience_id = record_associative_insight(graph, exploration=exploration, insight=insight, ledger_result=result)
    return replace(running, lifecycle_state="explored_pending_consolidation", ledger_result_id=str(result["result_id"]), insight_experience_id=experience_id, updated_at=utc_now()), updated_graph


def _parse_insight(raw: str, exploration: AssociationExploration) -> dict[str, str] | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        labels = (
            ("shared_structure", "shared[_ ]structure"),
            ("possible_implication", "possible[_ ]implication"),
            ("relation_limits", "relation[_ ]limits"),
            ("uncertainty", "uncertainty"),
            ("suggested_next_question", "suggested[_ ]next[_ ]question"),
        )
        data = {}
        for index, (key, label) in enumerate(labels):
            following = "|".join(item[1] for item in labels[index + 1:]) or "$"
            match = re.search(
                rf"(?:^|[.;\n])\s*{label}\s*(?:is|refers to|suggests|exists|could be)?\s*:?\s*(.+?)(?=(?:[.;\n]\s*(?:{following})\b)|$)",
                raw,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                data[key] = match.group(1).strip(" .")
    required = ("shared_structure", "possible_implication", "relation_limits", "uncertainty", "suggested_next_question")
    if not isinstance(data, Mapping) or any(not str(data.get(key) or "").strip() for key in required):
        return None
    combined = " ".join(str(data[key]) for key in required).lower()
    if (
        "validated" in combined
        or "operator approved" in combined
        or re.search(r"\bcertain(?:ty)?\b", combined)
        or re.search(r"\b(?:no|without)\s+(?:material\s+)?uncertainty\b", combined)
    ):
        return None
    response_tokens = set(re.findall(r"[a-z]{5,}", combined))
    source_anchor_sets = [
        {
            token
            for token in re.findall(r"[a-z]{5,}", source.lower())
            if token not in {"about", "after", "against", "between", "claim", "could", "does", "from", "into", "local", "record", "records", "source", "that", "their", "there", "these", "through", "water", "where", "which", "would"}
        }
        for source in exploration.source_context
    ]
    if any(anchors and not anchors.intersection(response_tokens) for anchors in source_anchor_sets):
        return None
    return {key: " ".join(str(data[key]).split())[:1200] for key in required}


def _execute_source_bound_inquiry(question: str, lane: Mapping[str, Any]) -> Mapping[str, Any]:
    """Use the existing exact-prompt cognitive lane for non-chat operation output."""
    model_name = str(lane.get("selected_model") or "")
    if not model_name:
        return {"executed": False, "reason": "no_local_model_available"}
    return execute_local_model_inference(
        model_name=model_name,
        prompt=question,
        task_type="active_cognitive_json_operation",
        metadata={
            "route": "approved_association_exploration",
            "lane": lane.get("lane"),
            "execution_lane": "cognitive_operation",
            "operation_type": "approved_association_exploration",
        },
        execution_adapter="approved_association_exploration.exact_prompt",
    )
