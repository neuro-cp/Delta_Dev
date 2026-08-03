"""One bounded, operator-approved structural analogy exploration.

This deliberately reuses the shared local-model ledger and the provisional
semantic graph.  It owns only durable operation lifecycle state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.local_model_execution_adapter import execute_local_model_inference
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger
from orchestration.runtime.provisional_semantic_consolidation import ProvisionalSemanticGraphState, record_associative_insight


SCHEMA_VERSION = "approved_structural_analogy_exploration_v1"
FILENAME = "approved_structural_analogy_explorations.json"
_FIELDS = (
    "shared_structure", "source_domain_interpretation", "target_domain_interpretation",
    "possible_implication", "failure_boundary", "uncertainty",
    "evidence_still_missing", "next_question",
)


@dataclass(frozen=True)
class StructuralAnalogyExploration:
    exploration_id: str
    candidate_id: str
    source_pattern_id: str
    target_pattern_id: str
    source_record_ids: tuple[str, ...]
    target_record_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    approval_request_id: str
    inquiry_question: str
    lifecycle_state: str = "analogy_exploration_queued"
    ledger_request_id: str = ""
    ledger_result_id: str = ""
    insight_experience_id: str = ""
    failure_reason: str = ""
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = SCHEMA_VERSION


def state_path(runtime_root: str | Path) -> Path:
    return Path(runtime_root) / "interactive-cognition" / FILENAME


def load_explorations(runtime_root: str | Path) -> tuple[StructuralAnalogyExploration, ...]:
    path = state_path(runtime_root)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        StructuralAnalogyExploration(**{name: item.get(name, "") for name in StructuralAnalogyExploration.__dataclass_fields__})
        for item in payload.get("explorations", ()) if isinstance(item, Mapping)
    )


def save_explorations(runtime_root: str | Path, records: tuple[StructuralAnalogyExploration, ...]) -> None:
    path = state_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"schema_version": SCHEMA_VERSION, "explorations": [asdict(item) for item in records]}, handle, indent=2, sort_keys=True)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def build_inquiry_question(
    graph: ProvisionalSemanticGraphState, *, source_record_ids: tuple[str, ...], target_record_ids: tuple[str, ...], relation_ids: tuple[str, ...],
) -> str:
    versions = {item.claim_version_id: item.exact_text for item in graph.claim_versions}
    source = [versions.get(item, item)[:220] for item in source_record_ids]
    target = [versions.get(item, item)[:220] for item in target_record_ids]
    return (
        "Compare the two functional patterns below without asserting factual equivalence or validation. "
        "Return JSON only with these string fields: " + ", ".join(_FIELDS) + ". "
        "The failure_boundary and uncertainty must be concrete. The failure_boundary must contrast "
        "a source-domain mechanism, assumption, scale, or failure mode with the target domain; "
        "do not merely restate a risk shared by both domains. "
        f"Source domain records: {source}. Target domain records: {target}. Matched relation IDs: {list(relation_ids)}."
    )


def queue_exploration(
    runtime_root: str | Path, graph: ProvisionalSemanticGraphState, *, candidate_id: str, source_pattern_id: str, target_pattern_id: str,
    source_record_ids: tuple[str, ...], target_record_ids: tuple[str, ...], relation_ids: tuple[str, ...], approval_request_id: str,
) -> StructuralAnalogyExploration:
    records = load_explorations(runtime_root)
    existing = next((item for item in records if item.candidate_id == candidate_id), None)
    if existing:
        return existing
    now = utc_now()
    record = StructuralAnalogyExploration(
        exploration_id=stable_id("structural-analogy-exploration", candidate_id, approval_request_id), candidate_id=candidate_id,
        source_pattern_id=source_pattern_id, target_pattern_id=target_pattern_id, source_record_ids=source_record_ids,
        target_record_ids=target_record_ids, relation_ids=relation_ids, approval_request_id=approval_request_id,
        inquiry_question=build_inquiry_question(graph, source_record_ids=source_record_ids, target_record_ids=target_record_ids, relation_ids=relation_ids),
        created_at=now, updated_at=now,
    )
    save_explorations(runtime_root, records + (record,))
    return record


def execute_once(
    runtime_root: str | Path, graph: ProvisionalSemanticGraphState, exploration: StructuralAnalogyExploration,
    *, executor: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> tuple[StructuralAnalogyExploration, ProvisionalSemanticGraphState]:
    ledger = LocalModelRequestResultLedger(Path(runtime_root) / "model-ledger")
    request = ledger.create_or_reuse_request(
        semantic_identity=exploration.exploration_id, question=exploration.inquiry_question,
        requester_type="approved_structural_analogy_exploration", requester_reference=exploration.candidate_id,
        question_objective="one bounded provisional structural analogy inquiry",
    )
    if request["lifecycle_state"] == "pending_operator_approval":
        request = ledger.approve_request(request["request_id"], f"approved_structural_analogy:{exploration.approval_request_id}")
    running = replace(exploration, lifecycle_state="analogy_exploration_running", ledger_request_id=str(request["request_id"]), updated_at=utc_now())
    if request["lifecycle_state"] == "approved":
        request = ledger.execute_claimed_request(request["request_id"], {"executor": executor or _execute_inquiry})
    if request["lifecycle_state"] != "completed":
        state = "analogy_exploration_interrupted" if request["lifecycle_state"] == "interrupted" else "analogy_exploration_failed"
        return replace(running, lifecycle_state=state, failure_reason=str(request.get("failure_classification") or request["lifecycle_state"]), updated_at=utc_now()), graph
    result = ledger.observe_result(str(request["result_id"]))
    parsed = _parse(str(result.get("response_reference") or ""))
    if parsed is None:
        return replace(running, lifecycle_state="analogy_exploration_blocked", ledger_result_id=str(result["result_id"]), failure_reason="typed_output_invalid", updated_at=utc_now()), graph
    # The existing graph helper is intentionally reused: the analogy remains a
    # model-produced provisional experience and receives no relation admission.
    bridge = type("AnalogyBridge", (), {
        "exploration_id": exploration.exploration_id, "source_record_ids": exploration.source_record_ids + exploration.target_record_ids,
        "relation_edge_ids": exploration.relation_ids, "candidate_id": exploration.candidate_id,
        "approval_request_id": exploration.approval_request_id, "ledger_request_id": running.ledger_request_id,
    })()
    graph, insight_id = record_associative_insight(graph, exploration=bridge, insight={
        "shared_structure": parsed["shared_structure"], "possible_implication": parsed["possible_implication"],
        "relation_limits": parsed["failure_boundary"], "uncertainty": parsed["uncertainty"], "suggested_next_question": parsed["next_question"],
    }, ledger_result=result)
    return replace(running, lifecycle_state="analogy_explored_pending_consolidation", ledger_result_id=str(result["result_id"]), insight_experience_id=insight_id, updated_at=utc_now()), graph


def _parse(raw: str) -> dict[str, str] | None:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, Mapping) or any(not str(value.get(field) or "").strip() for field in _FIELDS):
        return None
    combined = " ".join(str(value[field]) for field in _FIELDS).lower()
    if "validated" in combined or "no uncertainty" in combined or "without uncertainty" in combined:
        return None
    boundary = " ".join(str(value["failure_boundary"]).lower().split())
    contrast_markers = ("unlike", "whereas", "differ", "different", "not equivalent", "rather than", "in contrast", "physical")
    if not any(marker in boundary for marker in contrast_markers):
        return None
    return {field: " ".join(str(value[field]).split())[:1200] for field in _FIELDS}


def _execute_inquiry(question: str, lane: Mapping[str, Any]) -> Mapping[str, Any]:
    model_name = str(lane.get("selected_model") or "")
    if not model_name:
        return {"executed": False, "reason": "no_local_model_available"}
    return execute_local_model_inference(
        model_name=model_name, prompt=question, task_type="active_cognitive_json_operation",
        metadata={"route": "approved_structural_analogy_exploration", "lane": lane.get("lane"), "execution_lane": "cognitive_operation", "operation_type": "approved_structural_analogy_exploration"},
        execution_adapter="approved_structural_analogy_exploration.exact_prompt",
    )


__all__ = ["StructuralAnalogyExploration", "build_inquiry_question", "execute_once", "load_explorations", "queue_exploration", "save_explorations"]
