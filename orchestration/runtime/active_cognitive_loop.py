"""Active cognitive loop for DELTA's first integrated cognition marathon.

The loop is intentionally compact. It persists attention, bounded working
memory metadata, typed cognitive operations, hypotheses, outcomes, learning,
and next-focus decisions as one restartable episode state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

from integration.model_runtime.model_registry import list_available_models
from integration.model_runtime.execution_lanes import ModelExecutionLane
from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.local_model_execution_adapter import execute_local_model_inference


SCHEMA_VERSION = "active_cognitive_architecture_marathon_1_v1"
PROMPT_SCHEMA_VERSION = "active_cognitive_prompt_qualification_1_v1"
DEFAULT_STATE_PATH = Path("data") / "runtime" / "active_cognitive_loop" / "state.json"
OPERATION_TYPES = (
    "interpret_state",
    "prioritize_focus",
    "formulate_hypothesis",
    "reformulate_node_specific_hypothesis",
    "repair_node_specific_hypothesis_format",
    "identify_evidence_need",
    "compare_evidence",
    "challenge_hypothesis",
    "revise_hypothesis",
    "propose_plan",
    "revise_plan",
    "reflect_on_outcome",
    "summarize_learning",
    "select_next_focus",
    "request_operator_resolution",
    "declare_blocked_capability",
    "declare_insufficient_evidence",
)
HYPOTHESIS_OPERATIONS = frozenset({
    "formulate_hypothesis",
    "reformulate_node_specific_hypothesis",
    "repair_node_specific_hypothesis_format",
})
_SUPPLEMENTAL_FRONTIER_REJECTION_REASONS = frozenset({
    "node_completion_missing_expected_observation",
})
CONFIDENCE_STATES = (
    "tentative",
    "plausible",
    "supported",
    "strongly_supported",
    "contested",
    "weakened",
    "unsupported",
    "falsified",
    "unresolved",
)
HYPOTHESIS_LIFECYCLE_STATES = (
    "active",
    "revised",
    "superseded",
    "rejected",
    "falsified",
    "dormant",
    "resolved",
)
LOOP_STATES = (
    "idle",
    "selecting_focus",
    "assembling_working_memory",
    "awaiting_model",
    "grounding_result",
    "planning_action",
    "awaiting_authority",
    "executing_action",
    "observing_outcome",
    "revising",
    "persisting",
    "paused_budget",
    "blocked_operator_decision",
    "blocked_capability_gap",
    "blocked_insufficient_evidence",
    "completed",
    "failed_integrity",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, default=list) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    source: str
    summary: str
    content: str = ""
    kind: str = "local_evidence"
    exists: bool = True
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CognitiveGoal:
    goal_id: str
    summary: str
    expected_state: str
    observed_state: str = ""
    priority: str = "operator_requested"
    schema_version: str = SCHEMA_VERSION

    def discrepancy(self) -> str:
        if not self.observed_state:
            return "observed_state_missing"
        if self.expected_state.lower() in self.observed_state.lower():
            return "no_material_discrepancy"
        return "expected_state_not_yet_observed"

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateFocus:
    focus_id: str
    description: str
    source: str
    related_goal_ids: tuple[str, ...]
    urgency: str
    expected_value: str
    evidence_need: str
    authority_need: str
    capability_need: str
    blocking_state: str
    salience_explanation: str
    creation_sequence: int
    salience_categories: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AttentionState:
    attention_state_id: str
    active_focus_id: str = ""
    active_focus_summary: str = ""
    active_goal_ids: tuple[str, ...] = ()
    candidate_focuses: tuple[CandidateFocus, ...] = ()
    salience_reasons: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    interruption_priority: str = "none"
    interruption_reason: str = ""
    return_condition: str = ""
    focus_started_at: str = ""
    last_progress_at: str = ""
    progress_summary: str = ""
    stagnation_count: int = 0
    continuation_reason: str = ""
    switch_reason: str = ""
    abandonment_reason: str = ""
    previous_focus_ids: tuple[str, ...] = ()
    cycle_sequence: int = 0
    transition_journal: tuple[Mapping[str, Any], ...] = ()
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkingMemoryPacket:
    packet_id: str
    cycle_id: str
    active_goal: Mapping[str, Any]
    active_focus: Mapping[str, Any]
    current_hypotheses: tuple[Mapping[str, Any], ...]
    relevant_evidence: tuple[Mapping[str, Any], ...]
    conflicting_evidence: tuple[Mapping[str, Any], ...]
    recent_actions: tuple[Mapping[str, Any], ...]
    observed_outcomes: tuple[Mapping[str, Any], ...]
    unresolved_questions: tuple[str, ...]
    operator_constraints: tuple[str, ...]
    authority_state: str
    capability_limits: tuple[str, ...]
    prior_cycle_summary: str
    size_budget: int
    omitted_items_summary: str
    provenance_refs: tuple[str, ...]
    construction_rationale: str
    packet_digest: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CognitiveOperationRequest:
    operation_id: str
    cycle_id: str
    operation_type: str
    working_memory_packet_digest: str
    goal_id: str
    focus_id: str
    task: str
    expected_output_schema: Mapping[str, Any]
    evidence_constraints: tuple[str, ...]
    authority_constraints: tuple[str, ...]
    budget: Mapping[str, Any]
    retry_allowance: int
    model_identity: str
    provenance: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CognitiveOperationResult:
    operation_id: str
    operation_result_type: str
    interpretation: str
    evidence_refs: tuple[str, ...]
    contrary_evidence_considered: tuple[str, ...]
    uncertainty: str
    assumptions: tuple[str, ...]
    recommended_state_transition: str
    recommended_action: str
    next_evidence_need: str
    next_focus_proposal: str
    raw_model_output: str
    model_identity: str
    accepted: bool
    expected_observations: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    evaluation_state: str = "not_evaluated"
    evaluation_reasons: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptSnapshot:
    prompt_snapshot_id: str
    prompt_schema_version: str
    operation_request: Mapping[str, Any]
    operation_type: str
    cycle_id: str
    goal_id: str
    focus_id: str
    working_memory_packet_id: str
    working_memory_packet_digest: str
    prompt_text: str
    prompt_byte_digest: str
    prompt_length: int
    evidence_ids_supplied: tuple[str, ...]
    contrary_evidence_ids_supplied: tuple[str, ...]
    expected_response_schema: Mapping[str, Any]
    authority_constraints: tuple[str, ...]
    model_identity: str
    request_identity: str
    retry_sequence: int = 0
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptedOperationResponse:
    raw_response: str
    raw_response_digest: str
    adapted_response: Mapping[str, Any]
    adapter_transformations: tuple[str, ...]
    adapter_rejection_reasons: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OperationResponseEvaluation:
    passed: bool
    failure_classifications: tuple[str, ...]
    positive_observations: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CognitiveOperationSchema:
    operation_type: str
    schema_id: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    allowed_transitions: tuple[str, ...]
    evidence_fields: tuple[str, ...]
    string_array_fields: tuple[str, ...]
    nonempty_string_fields: tuple[str, ...]
    recommended_operation_field: str = ""
    checkpoint_required: bool = True
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HypothesisRecord:
    hypothesis_id: str
    statement: str
    scope: str
    originating_goal_id: str
    originating_focus_id: str
    evidence_for: tuple[str, ...] = ()
    evidence_against: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    expected_observations: tuple[str, ...] = ()
    confidence_state: str = "tentative"
    lifecycle_state: str = "active"
    revision_parent_id: str = ""
    revision_reason: str = ""
    created_at: str = ""
    revised_at: str = ""
    disposition: str = "under_review"
    provenance: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LoopCycle:
    cycle_id: str
    sequence: int
    focus_id: str
    operation_id: str
    packet_digest: str
    outcome_id: str = ""
    summary: str = ""
    completed: bool = False
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActiveCognitiveEpisodeState:
    episode_id: str
    title: str
    loop_state: str
    goals: tuple[CognitiveGoal, ...]
    evidence: tuple[EvidenceRef, ...] = ()
    attention: AttentionState | None = None
    hypotheses: tuple[HypothesisRecord, ...] = ()
    working_memory_packets: tuple[WorkingMemoryPacket, ...] = ()
    operation_requests: tuple[CognitiveOperationRequest, ...] = ()
    operation_results: tuple[CognitiveOperationResult, ...] = ()
    cycles: tuple[LoopCycle, ...] = ()
    actions: tuple[Mapping[str, Any], ...] = ()
    outcomes: tuple[Mapping[str, Any], ...] = ()
    learning_updates: tuple[Mapping[str, Any], ...] = ()
    budgets: Mapping[str, Any] = field(default_factory=dict)
    model_call_count: int = 0
    useful_artifacts: tuple[Mapping[str, Any], ...] = ()
    pending_operator_requests: tuple[Mapping[str, Any], ...] = ()
    next_focus_candidates: tuple[CandidateFocus, ...] = ()
    completed: bool = False
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        if self.attention is None:
            record["attention"] = None
        return record


class ActiveCognitiveLoopError(RuntimeError):
    pass


ModelRunner = Callable[[CognitiveOperationRequest, WorkingMemoryPacket], Mapping[str, Any]]


class ScriptedSemanticModel:
    """A local test/dry-run model adapter that returns typed semantic outputs.

    Production use should pass a runner backed by ProviderManager or the local
    model ledger. Tests use this adapter to exercise the governing loop without
    booting a GGUF model.
    """

    model_identity = "scripted-local-semantic-adapter:test-only"

    def __call__(self, request: CognitiveOperationRequest, packet: WorkingMemoryPacket) -> Mapping[str, Any]:
        focus = str(packet.active_focus.get("description") or "")
        frontier_node = dict(packet.active_focus.get("active_frontier_node") or {})
        evidence = [str(item.get("evidence_id") or "") for item in packet.relevant_evidence]
        contrary = [str(item.get("evidence_id") or "") for item in packet.conflicting_evidence]
        if request.operation_type in HYPOTHESIS_OPERATIONS:
            label = str(frontier_node.get("label") or focus)
            interpretation = (
                f"{label} depends on site conditions, component constraints, and operating demand "
                "because each changes the practical design decision."
            )
            transition = "propose_hypothesis"
        elif request.operation_type == "challenge_hypothesis":
            interpretation = f"Contrary evidence changes the hypothesis: {focus} needs a narrower plan before action."
            transition = "weaken_hypothesis"
        elif request.operation_type == "revise_hypothesis":
            interpretation = f"Revise the hypothesis for {focus}: preserve the useful part, drop the unsupported expectation, and choose a smaller next step."
            transition = "revise_hypothesis"
        elif request.operation_type == "summarize_learning":
            interpretation = f"Learning: {focus} should be advanced only with evidence-linked next steps and explicit restart state."
            transition = "summarize_learning"
        else:
            interpretation = f"For {focus}, the next useful operation is to compare evidence and choose one bounded step."
            transition = "continue_focus"
        response = {
            "operation_result_type": request.operation_type + "_result",
            "interpretation": interpretation,
            "evidence_refs": evidence[:3],
            "contrary_evidence_considered": contrary[:3],
            "uncertainty": "bounded_by_available_local_evidence",
            "assumptions": ["local evidence is complete for this bounded episode"],
            "recommended_state_transition": transition,
            "recommended_action": "produce_useful_artifact" if request.operation_type in {"propose_plan", "revise_plan"} else "continue_cognitive_cycle",
            "next_evidence_need": "inspect focused local evidence" if not evidence else "",
            "next_focus_proposal": "select the next unresolved focus with available evidence",
            "raw_model_output": interpretation,
            "model_identity": self.model_identity,
        }
        if request.operation_type in HYPOTHESIS_OPERATIONS:
            response.update({
                "hypothesis_statement": interpretation,
                "scope": str(frontier_node.get("label") or focus),
                "supporting_evidence_refs": evidence[:3],
                "expected_observations": ["changing one concrete condition changes the design decision"],
            })
        return response


class LedgerBackedCognitiveModelRunner:
    """Runs cognitive operations through DELTA's shared local-model ledger."""

    model_identity = "shared-local-model-ledger:active-cognitive-loop"

    def __init__(
        self,
        *,
        ledger: Any,
        provider_manager: Any | None = None,
        authority_reason: str = "operator_authorized_active_cognitive_loop",
        snapshot_root: str | Path | None = None,
        request_identity_suffix: str = "",
        retry_sequence: int = 0,
    ) -> None:
        self.ledger = ledger
        self.provider_manager = provider_manager
        self.authority_reason = authority_reason
        self.snapshot_root = Path(snapshot_root) if snapshot_root is not None else None
        self.request_identity_suffix = request_identity_suffix
        self.retry_sequence = retry_sequence

    def __call__(self, request: CognitiveOperationRequest, packet: WorkingMemoryPacket) -> Mapping[str, Any]:
        snapshot = compile_operation_prompt_snapshot(
            request,
            packet,
            retry_sequence=self.retry_sequence,
            request_identity_suffix=self.request_identity_suffix,
        )
        if self.snapshot_root is not None:
            _write_prompt_snapshot(self.snapshot_root, snapshot)
        ledger_record = self.ledger.create_or_reuse_request(
            semantic_identity=snapshot.request_identity,
            question=snapshot.prompt_text,
            requester_type="active_cognitive_loop",
            requester_reference=request.operation_id,
            mission_id=request.goal_id,
            mission_information_need_identity=request.focus_id,
            session_reference=packet.cycle_id,
            question_objective=request.operation_type,
        )
        request_id = str(ledger_record["request_id"])
        ledger_state = str(ledger_record.get("lifecycle_state") or "")
        if ledger_state == "completed" and ledger_record.get("result_id"):
            terminal = ledger_record
        elif ledger_state == "pending_operator_approval":
            self.ledger.approve_request(request_id, self.authority_reason)
            terminal = self.ledger.execute_claimed_request(
                request_id,
                {"executor": lambda question, lane: self._execute_exact_prompt(question, lane, operation_type=request.operation_type)},
            )
        elif ledger_state == "approved":
            terminal = self.ledger.execute_claimed_request(
                request_id,
                {"executor": lambda question, lane: self._execute_exact_prompt(question, lane, operation_type=request.operation_type)},
            )
        else:
            terminal = ledger_record
        result_id = str(terminal.get("result_id") or "")
        if str(terminal.get("lifecycle_state") or "") != "completed" or not result_id:
            return _operation_unavailable_result(request, terminal, packet)
        ledger_result = self.ledger.observe_result(result_id)
        raw_text = str(ledger_result.get("response_reference") or "")
        adapted = adapt_operation_response(raw_text)
        if self.snapshot_root is not None:
            _write_response_snapshot(self.snapshot_root, snapshot, terminal, ledger_result, adapted)
        parsed = _runtime_payload_from_operation_response(request.operation_type, dict(adapted.adapted_response))
        parsed = _canonicalize_active_frontier_scope(packet, parsed)
        if adapted.adapter_rejection_reasons:
            parsed.setdefault("adapter_rejection_reasons", adapted.adapter_rejection_reasons)
        parsed.setdefault("raw_model_output", raw_text)
        parsed.setdefault("model_identity", str(ledger_result.get("model_identity") or self.model_identity))
        parsed.setdefault("operation_result_type", request.operation_type + "_result")
        return parsed

    def _execute_exact_prompt(self, question: str, lane: dict[str, Any], *, operation_type: str = "") -> Mapping[str, Any]:
        if self.provider_manager is None:
            return {
                "executed": False,
                "reason": "provider_manager_required_for_exact_active_cognitive_prompt",
            }
        model_names = _bounded_local_model_attempt_order(lane)
        if not model_names:
            return {"executed": False, "reason": "no_local_model_available"}
        attempts: list[dict[str, Any]] = []
        last_error = ""
        for model_name in model_names[:2]:
            result = execute_local_model_inference(
                model_name=model_name,
                prompt=question,
                task_type="active_cognitive_json_operation",
                metadata={
                    "route": "active_cognitive_loop",
                    "lane": lane.get("lane"),
                    "execution_lane": ModelExecutionLane.COGNITIVE_OPERATION.value,
                    "operation_type": operation_type,
                },
                provider_manager=self.provider_manager,
                execution_adapter="active_cognitive_loop.exact_prompt",
            )
            if not result.get("executed"):
                last_error = str(result.get("reason") or "local_model_execution_failed")
                attempts.append({"model_name": model_name, "executed": True, "succeeded": False, "error": last_error, "adapter": result.get("execution_adapter")})
                continue
            answer = str(result.get("answer") or "").strip()
            attempts.append({"model_name": model_name, "executed": True, "succeeded": bool(answer), "adapter": result.get("execution_adapter")})
            if not answer:
                last_error = "empty_model_answer"
                continue
            return {
                "executed": True,
                "available": True,
                "answer": answer,
                "confidence_score": float(result.get("confidence_score") or 0.0),
                "model_id": str(result.get("model_id") or model_name),
                "latency_seconds": float(result.get("latency_seconds") or 0.0),
                "response_tokens": int(result.get("response_tokens") or 0),
                "prompt_sent": question,
                "execution_adapter": str(result.get("execution_adapter") or "active_cognitive_loop.exact_prompt"),
                "provider_calls_performed": False,
                "model_attempts": attempts,
            }
        return {
            "executed": False,
            "available": True,
            "answer": "",
            "reason": last_error or "local_model_execution_failed",
            "prompt_sent": question,
            "execution_adapter": "active_cognitive_loop.exact_prompt",
            "provider_calls_performed": False,
            "model_attempts": attempts,
        }


def _bounded_local_model_attempt_order(lane: Mapping[str, Any]) -> tuple[str, ...]:
    selected = str(lane.get("selected_model") or "")
    ordered: list[str] = [selected] if selected else []
    selected_family = str(lane.get("model_family") or "").lower()
    models = list_available_models()
    for preferred_family in ("llama", "qwen", "mistral", "phi4", "phi3"):
        if preferred_family == selected_family:
            continue
        for key, spec in sorted(models.items()):
            if key in ordered or spec.name in ordered:
                continue
            if spec.family != preferred_family or "text" not in spec.capabilities:
                continue
            if not Path(spec.path).exists():
                continue
            ordered.append(key)
            return tuple(ordered)
    return tuple(ordered)


def _operation_unavailable_result(
    request: CognitiveOperationRequest,
    terminal: Mapping[str, Any],
    packet: WorkingMemoryPacket,
) -> dict[str, Any]:
    failure = str(terminal.get("failure_classification") or "local_model_unavailable")
    detail = str(terminal.get("failure_detail") or failure)
    allowed = _allowed_transitions_for_operation(request.operation_type)
    transition = "declare_insufficient_evidence" if "declare_insufficient_evidence" in allowed else allowed[0]
    evidence_refs = tuple(str(item.get("evidence_id") or "") for item in packet.relevant_evidence if item.get("evidence_id"))
    base = {
        "operation_result_type": request.operation_type + "_unavailable",
        "interpretation": f"Local model execution did not complete: {detail}",
        "evidence_refs": evidence_refs,
        "contrary_evidence_considered": (),
        "uncertainty": failure,
        "recommended_state_transition": transition,
        "raw_model_output": json.dumps(terminal, sort_keys=True, default=str),
        "model_identity": str(terminal.get("model_identity") or "shared-local-model-ledger:active-cognitive-loop"),
    }
    if request.operation_type in HYPOTHESIS_OPERATIONS:
        base.update({
            "hypothesis_statement": "No supported hypothesis was formed because local model execution did not complete.",
            "scope": str(packet.active_focus.get("description") or packet.active_goal.get("summary") or "active focus"),
            "supporting_evidence_refs": evidence_refs,
            "assumptions": ["No concept progress should be accepted without model output or evidence."],
            "expected_observations": ["A later successful local execution or bounded fallback should produce a typed result."],
        })
    return base


def _active_frontier_node_from_evidence(
    evidence: Sequence[EvidenceRef],
    focus: CandidateFocus,
) -> EvidenceRef | None:
    focus_refs = set(focus.evidence_refs)
    return next((item for item in evidence if item.kind == "knowledge_frontier_node" and item.evidence_id in focus_refs), None)


def _frontier_node_prompt_metadata(node: EvidenceRef | None) -> dict[str, Any]:
    if node is None:
        return {}
    try:
        content = json.loads(node.content or "{}")
    except json.JSONDecodeError:
        content = {}
    return {
        "node_id": node.evidence_id,
        "label": str(content.get("label") or node.summary),
        "parent_node_id": str(content.get("parent_id") or ""),
        "completion_criterion_reference": str(content.get("completion_criterion_reference") or ""),
        "minimum_contribution_contract": dict(content.get("minimum_contribution_contract") or {}),
        "evidence_need": str(content.get("evidence_need") or ""),
        "unresolved_questions": tuple(str(item) for item in content.get("unresolved_questions", ()) if str(item)),
        "existing_node_claim_ids": tuple(str(item) for item in content.get("extracted_claim_ids", ()) if str(item)),
        "existing_node_concept_ids": tuple(str(item) for item in content.get("extracted_concept_ids", ()) if str(item)),
        "dependency_node_ids": tuple(
            str(item)
            for item in (content.get("dependency_node_ids") or content.get("dependencies") or ())
            if str(item)
        ),
    }


def _frontier_dependency_hypotheses(
    state: ActiveCognitiveEpisodeState,
    node_metadata: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    """Return accepted prior claims only for dependencies explicitly declared by this node."""
    dependency_ids = {str(item) for item in node_metadata.get("dependency_node_ids", ()) if str(item)}
    if not dependency_ids:
        return ()
    dependency_focuses = {
        stable_id("focus", state.episode_id, dependency_id)
        for dependency_id in dependency_ids
    }
    return tuple(
        {
            "node_id": next(
                (
                    dependency_id
                    for dependency_id in dependency_ids
                    if stable_id("focus", state.episode_id, dependency_id) == hypothesis.originating_focus_id
                ),
                "",
            ),
            "statement": hypothesis.statement[:320],
        }
        for hypothesis in state.hypotheses
        if hypothesis.originating_focus_id in dependency_focuses and hypothesis.statement
    )


def _semantic_digest(text: str) -> str:
    tokens = sorted(_semantic_tokens(text))
    return _digest({"semantic_tokens": tokens})


def _semantic_tokens(text: str) -> set[str]:
    stop = {
        "about", "active", "address", "and", "available", "backup", "battery", "batteries", "because", "between",
        "during", "evidence", "for", "frontier", "goal", "knowledge", "local", "model", "node", "outages", "residential",
        "resolve", "system", "systems", "that", "their", "there", "these", "this", "using",
        "with", "without", "which", "what", "when", "where", "from", "into", "they", "work", "synthesis",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", str(text).lower())
        if token not in stop
    }


def _semantic_similarity(left: str, right: str) -> float:
    left_tokens = _semantic_tokens(left)
    right_tokens = _semantic_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))


def _knowledge_result_text(raw: Mapping[str, Any]) -> str:
    parts: list[str] = [
        str(raw.get("scope") or ""),
        str(raw.get("hypothesis_statement") or ""),
        str(raw.get("interpretation") or ""),
        str(raw.get("uncertainty") or ""),
    ]
    parts.extend(str(item) for item in raw.get("assumptions", ()) if str(item))
    parts.extend(str(item) for item in raw.get("expected_observations", ()) if str(item))
    return " ".join(parts)


def _knowledge_hypothesis_text(raw: Mapping[str, Any]) -> str:
    return str(raw.get("hypothesis_statement") or raw.get("interpretation") or "").strip()


def _knowledge_contract_contribution_rejections(contract: Mapping[str, Any], statement: str) -> tuple[str, ...]:
    lowered = statement.lower()
    kind = str(contract.get("contribution_kind") or "explanatory_relation")
    required_terms = {
        str(item).strip().lower()
        for item in contract.get("required_topic_terms", ())
        if str(item).strip()
    }
    statement_terms = _semantic_tokens(statement)
    if required_terms and not (required_terms & statement_terms):
        return ("node_completion_contract_missing:required_topic_terms",)
    actions = {
        token for token in (
            "address", "check", "clean", "clear", "cover", "drain", "empty", "inspect",
            "maintain", "remove", "repair", "replace", "screen", "seal", "secure", "test", "treat",
        )
        if token in lowered
    }
    if kind == "recurring_actions_with_consequence":
        if len(actions) < int(contract.get("minimum_action_count") or 2) or not any(marker in lowered for marker in ("prevent", "avoid", "reduce", "protect", "ensure")):
            return ("node_completion_contract_missing:recurring_actions_with_consequence",)
    if kind == "threshold_and_safe_mitigation":
        threshold = any(marker in lowered for marker in ("exceed", "full", "capacity", "threshold", "limit"))
        route = any(marker in lowered for marker in ("route", "direct", "drain", "discharge", "divert", "away", "hose", "pipe", "channel"))
        concrete_destination = any(marker in lowered for marker in ("away", "storm", "drain", "ground", "foundation", "structure", "erosion", "splash", "safe area"))
        mitigation = route and concrete_destination
        if not (threshold and mitigation):
            return ("node_completion_contract_missing:threshold_and_safe_mitigation",)
    if kind == "sizing_relation":
        sizing_terms = sum(
            marker in lowered
            for marker in ("capacity", "volume", "size", "demand", "load", "usage", "duration", "runtime", "rate", "area")
        )
        if sizing_terms < 2:
            return ("node_completion_contract_missing:sizing_relation",)
    if kind == "mechanism_path":
        capture = any(marker in lowered for marker in ("collect", "catch", "capture", "intake", "inlet"))
        transfer = any(marker in lowered for marker in ("flow", "route", "channel", "convey", "transfer", "downspout", "gutter"))
        if not (capture and transfer):
            return ("node_completion_contract_missing:mechanism_path",)
    if kind == "prevention_intervention":
        intervention = bool(actions) or any(marker in lowered for marker in ("mesh", "lid", "larvicide"))
        hazard = any(marker in lowered for marker in ("mosquito", "larva", "larvae", "breeding", "egg", "standing water"))
        causal_block = any(marker in lowered for marker in ("prevent", "block", "stop", "keep", "deny", "reduce", "avoid", "limit", "cannot access"))
        if not (intervention and hazard and causal_block):
            return ("node_completion_contract_missing:prevention_intervention",)
    return ()


def _knowledge_contract_prompt_hint(contract: Mapping[str, Any]) -> str:
    required_terms = tuple(str(item).strip() for item in contract.get("required_topic_terms", ()) if str(item).strip())
    required_hint = (
        " Name at least one active topic term: " + ", ".join(required_terms) + "."
        if required_terms else ""
    )
    relation_hint = (
        " In hypothesis_statement, state the relationship explicitly with a connector such as because, through, leads to, controls, depends on, represents, corresponds to, or prevents; listing roles alone is not enough."
        if contract.get("requires_explanatory_relation") else ""
    )
    observation_hint = (
        " Include one concrete expected_observations entry that describes an observable application or consequence of the relationship."
        if contract.get("requires_expected_observation") else ""
    )
    kind = str(contract.get("contribution_kind") or "explanatory_relation")
    if kind == "mechanism_path":
        return "For a mechanism-path node, explain the route or transfer path from source through intermediate component into storage or output." + relation_hint + observation_hint + required_hint
    if kind == "threshold_and_safe_mitigation":
        return "For an overflow or threshold node, name the threshold condition and the concrete route or destination that safely carries excess flow away." + relation_hint + observation_hint + required_hint
    if kind == "prevention_intervention":
        return "For a prevention node, name the concrete intervention, the hazard being prevented, and how the intervention blocks or reduces that hazard." + relation_hint + observation_hint + required_hint
    if kind == "sizing_relation":
        return "For a sizing node, relate at least two sizing variables such as capacity, demand, rate, duration, load, area, or usage." + relation_hint + observation_hint + required_hint
    if kind == "recurring_actions_with_consequence":
        return "For a maintenance node, name recurring actions and the consequence they prevent or reduce." + relation_hint + observation_hint + required_hint
    return "Provide a concrete explanatory relation rather than a relevant but static label." + relation_hint + observation_hint + required_hint


def _knowledge_independent_evaluation(
    packet: WorkingMemoryPacket,
    raw: Mapping[str, Any],
) -> tuple[str, tuple[str, ...]]:
    """A deterministic local evaluator that cannot inherit the proposer's acceptance decision."""
    if str(packet.active_focus.get("source") or "") != "knowledge_frontier":
        return "not_evaluated", ()
    text = _knowledge_result_text(raw).lower()
    capacity = re.search(r"\b(\d+(?:\.\d+)?)\s*[- ]?gallons?\b", text)
    people = re.search(r"(?:family of|for)\s+(\d+)\s+(?:people|persons|adults)", text)
    if people is None:
        number_words = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8"}
        word_match = re.search(r"family of\s+(one|two|three|four|five|six|seven|eight)\b", text)
        if word_match:
            people = re.match(r"(\d+)", number_words[word_match.group(1)])
    days = re.search(r"(?:over|during|for)\s+(?:a\s+)?(\d+)\s*[- ]?days?\b", text)
    daily_rate = re.search(r"(\d+(?:\.\d+)?)\s*gallons?\s*(?:per|/)\s*person\s*(?:per|/)\s*day", text)
    if capacity and people and days and daily_rate:
        available = float(capacity.group(1))
        required = float(people.group(1)) * float(days.group(1)) * float(daily_rate.group(1))
        if available < required:
            return "contradicted", (f"arithmetic_capacity_shortfall:{available:g}_lt_{required:g}",)
    if not _knowledge_hypothesis_text(raw):
        return "insufficient_evidence", ("missing_candidate_proposition",)
    return "supported", ("deterministic_local_plausibility_pass",)


def _knowledge_completion_sufficiency_rejections(
    packet: WorkingMemoryPacket,
    raw: Mapping[str, Any],
) -> tuple[str, ...]:
    if str(packet.active_focus.get("source") or "") != "knowledge_frontier":
        return ()
    node = dict(packet.active_focus.get("active_frontier_node") or {})
    contract = dict(node.get("minimum_contribution_contract") or {})
    if not contract:
        return ()
    statement = " ".join(
        part for part in (
            _knowledge_hypothesis_text(raw),
            str(raw.get("interpretation") or "").strip(),
        )
        if part
    )
    lowered = statement.lower()
    generic_terms = {
        "air", "critical", "desired", "effective", "effectively", "efficient", "efficiency", "home", "house",
        "important", "issue", "issues", "larger", "moisture", "necessary", "operation", "operations", "properly",
        "required", "residential", "smaller", "space", "spaces", "system", "systems", "water", "whole",
    }
    specific_terms = _semantic_tokens(statement) - _semantic_tokens(str(node.get("label") or "")) - generic_terms
    minimum_terms = int(contract.get("minimum_specific_terms") or 0)
    rejections: list[str] = []
    if minimum_terms and len(specific_terms) < minimum_terms:
        rejections.append("node_completion_insufficient_specific_content")
    if contract.get("requires_explanatory_relation"):
        relation_markers = (
            "because", "when", "therefore", "caus", "lead", "depend", "determin", "constrain", "limit", "require", "must",
            "prevent", "adjust", "control", "compress", "flow", "drain", "circulat", "integrat", "affect",
            "represent", "correspond", "relate", "connect", "through",
        )
        if not any(marker in lowered for marker in relation_markers):
            rejections.append("node_completion_missing_explanatory_relation")
    if contract.get("requires_expected_observation") and not tuple(
        str(item).strip()
        for item in raw.get("expected_observations", ())
        if str(item).strip()
    ):
        rejections.append("node_completion_missing_expected_observation")
    if contract.get("reject_importance_only") and re.search(r"\b(?:is|are)\s+(?:critical|important|necessary|required)\b", lowered):
        rejections.append("node_completion_generic_importance_assertion")
    rejections.extend(_knowledge_contract_contribution_rejections(contract, statement))
    return tuple(dict.fromkeys(rejections))


def _knowledge_cross_node_context_rejections(
    packet: WorkingMemoryPacket,
    raw: Mapping[str, Any],
) -> tuple[str, ...]:
    if str(packet.active_focus.get("source") or "") != "knowledge_frontier":
        return ()
    node = dict(packet.active_focus.get("active_frontier_node") or {})
    active_tokens = _semantic_tokens(
        " ".join(
            (
                str(node.get("label") or ""),
                str(node.get("completion_criterion_reference") or ""),
            )
        )
    )
    generic_terms = {
        "air", "because", "critical", "desired", "effective", "effectively", "efficient", "efficiency", "home",
        "house", "important", "issue", "issues", "larger", "moisture", "necessary", "operation", "operations",
        "properly", "required", "residential", "smaller", "space", "spaces", "system", "systems", "water", "whole",
    }
    candidate_tokens = _semantic_tokens(_knowledge_hypothesis_text(raw)) - active_tokens - generic_terms
    if len(candidate_tokens) < 4:
        return ()
    active_focus_id = str(packet.active_focus.get("focus_id") or "")
    for target in tuple(packet.active_focus.get("prohibited_duplicate_targets") or ()):
        if str(target.get("originating_focus_id") or "") == active_focus_id:
            continue
        prior_tokens = {str(token) for token in target.get("statement_tokens", ()) if str(token)} - generic_terms
        overlap = candidate_tokens & prior_tokens
        new_terms = candidate_tokens - prior_tokens
        if len(overlap) >= 4 and len(overlap) > len(new_terms):
            return ("cross_node_context_dominates_active_contribution",)
    active_specific = active_tokens - generic_terms
    for sibling in tuple(packet.active_focus.get("sibling_frontier_nodes") or ()):
        if not isinstance(sibling, Mapping):
            continue
        sibling_tokens = _semantic_tokens(
            str(sibling.get("label") or "") + " " + str(sibling.get("completion_criterion_reference") or "")
        ) - generic_terms
        sibling_overlap = candidate_tokens & sibling_tokens
        active_overlap = candidate_tokens & active_specific
        if len(sibling_overlap) >= 2 and len(sibling_overlap) > len(active_overlap):
            return ("sibling_frontier_node_dominates_active_contribution",)
    return ()


def _frontier_attempt_counts(state: ActiveCognitiveEpisodeState) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    results = {result.operation_id: result for result in state.operation_results}
    for cycle in state.cycles:
        result = results.get(cycle.operation_id)
        bucket = counts.setdefault(cycle.focus_id, {"accepted": 0, "rejected": 0})
        if result and result.accepted:
            bucket["accepted"] += 1
        elif result:
            bucket["rejected"] += 1
    return counts


def _frontier_attempt_records(
    state: ActiveCognitiveEpisodeState,
    focus_id: str,
) -> tuple[tuple[CognitiveOperationRequest, CognitiveOperationResult], ...]:
    requests = {request.operation_id: request for request in state.operation_requests}
    results = {result.operation_id: result for result in state.operation_results}
    records: list[tuple[CognitiveOperationRequest, CognitiveOperationResult]] = []
    for cycle in state.cycles:
        if cycle.focus_id != focus_id:
            continue
        request = requests.get(cycle.operation_id)
        result = results.get(cycle.operation_id)
        if request is not None and result is not None:
            records.append((request, result))
    return tuple(records)


def _retry_output_schema_invalid(request: CognitiveOperationRequest, result: CognitiveOperationResult) -> bool:
    return (
        request.operation_type == "reformulate_node_specific_hypothesis"
        and "retry_output_schema_invalid" in result.rejection_reasons
    )


def discover_model_inventory() -> dict[str, Any]:
    models = list_available_models()
    return {
        "available_model_count": len(models),
        "models": [
            {
                "registry_key": key,
                "model_id": spec.name,
                "path": str(spec.path),
                "family": spec.family,
                "provider": spec.provider,
                "capabilities": tuple(spec.capabilities),
                "size_bytes": spec.size_bytes,
                "exists": Path(spec.path).exists(),
            }
            for key, spec in sorted(models.items())
        ],
        "preferred_general_model": _preferred_model(("qwen3-5-9b", "qwen", "llama", "mistral", "phi3"), models),
        "preferred_code_model": _preferred_model(("coder", "qwen"), models),
    }


def initialize_episode(
    *,
    title: str,
    goal_summary: str,
    expected_state: str,
    evidence: Sequence[EvidenceRef | Mapping[str, Any]] = (),
    state_path: str | Path | None = None,
) -> ActiveCognitiveEpisodeState:
    goal = CognitiveGoal(
        goal_id=stable_id("active-cognitive-goal", title, goal_summary),
        summary=goal_summary,
        expected_state=expected_state,
    )
    episode_id = stable_id("active-cognitive-episode", title, goal.goal_id)
    attention = AttentionState(attention_state_id=stable_id("active-attention", episode_id))
    normalized_evidence = tuple(_evidence(item) for item in evidence)
    state = ActiveCognitiveEpisodeState(
        episode_id=episode_id,
        title=title,
        loop_state="idle",
        goals=(goal,),
        evidence=normalized_evidence,
        attention=attention,
        budgets={"max_cycles": 8, "max_model_calls": 6, "max_actions": 4, "max_packet_items": 8},
    )
    if state_path is not None:
        write_episode_state(state_path, state)
    return state


def run_cognitive_cycle(
    state: ActiveCognitiveEpisodeState,
    *,
    model_runner: ModelRunner | None = None,
    requested_operation: str | None = None,
) -> ActiveCognitiveEpisodeState:
    _validate_state(state)
    if state.completed:
        return state
    max_model_calls = state.budgets.get("max_model_calls")
    max_cycles = state.budgets.get("max_cycles")
    if max_model_calls is not None and state.model_call_count >= int(max_model_calls):
        return replace(state, loop_state="paused_budget")
    if max_cycles is not None and len(state.cycles) >= int(max_cycles):
        return replace(state, loop_state="paused_budget")
    runner = model_runner or ScriptedSemanticModel()
    sequence = len(state.cycles) + 1
    candidates = generate_candidate_focuses(state)
    if not candidates:
        return replace(state, loop_state="blocked_insufficient_evidence")
    attention = select_attention(state, candidates)
    state = replace(state, attention=attention, next_focus_candidates=candidates, loop_state="assembling_working_memory")
    packet = build_working_memory_packet(state, sequence=sequence)
    operation_type = requested_operation or select_operation_type(state, packet)
    request = build_operation_request(state, packet, operation_type=operation_type, model_identity=getattr(runner, "model_identity", "local_model_runner"))
    raw = runner(request, packet)
    result = validate_model_result(request, packet, raw)
    state = apply_operation_result(state, packet, request, result, sequence=sequence)
    _validate_state(state)
    return state


def run_episode(
    state: ActiveCognitiveEpisodeState,
    *,
    model_runner: ModelRunner | None = None,
    cycles: int = 3,
) -> ActiveCognitiveEpisodeState:
    current = state
    for _ in range(cycles):
        if current.loop_state in {"paused_budget", "blocked_operator_decision", "blocked_capability_gap", "blocked_insufficient_evidence", "failed_integrity", "completed"}:
            break
        current = run_cognitive_cycle(current, model_runner=model_runner)
    return current


def generate_candidate_focuses(state: ActiveCognitiveEpisodeState) -> tuple[CandidateFocus, ...]:
    goal = state.goals[0]
    unresolved = tuple(
        item for item in state.hypotheses if item.lifecycle_state == "active" and item.confidence_state in {"tentative", "contested", "weakened", "unresolved"}
    )
    focuses: list[CandidateFocus] = []
    frontier_nodes = tuple(item for item in state.evidence if item.kind == "knowledge_frontier_node")
    if frontier_nodes:
        attempt_counts = _frontier_attempt_counts(state)
        for index, node in enumerate(frontier_nodes, start=1):
            node_focus_id = stable_id("focus", state.episode_id, node.evidence_id)
            counts = attempt_counts.get(node_focus_id, {})
            attempts = _frontier_attempt_records(state, node_focus_id)
            latest_attempt = attempts[-1] if attempts else None
            node_source = str(node.source or "")
            is_operator_followup = node_source == "teaching_followup"
            is_linked_prerequisite = node_source == "teaching_prerequisite"
            format_repair = bool(
                latest_attempt
                and _retry_output_schema_invalid(*latest_attempt)
                and not any(request.operation_type == "repair_node_specific_hypothesis_format" for request, _result in attempts)
            )
            if counts.get("accepted", 0) or (counts.get("rejected", 0) >= 2 and not format_repair):
                continue
            label = node.summary.replace("Knowledge frontier node", "Frontier node", 1)
            retrying = counts.get("rejected", 0) == 1
            repair_description = f"Repair response format for knowledge frontier: {label}"
            focuses.append(CandidateFocus(
                focus_id=node_focus_id,
                description=repair_description if format_repair else f"{'Retry' if retrying else 'Resolve'} knowledge frontier: {label}",
                source="knowledge_frontier",
                related_goal_ids=(goal.goal_id,),
                # A newly asked in-scope teaching question is an explicit
                # foreground obligation.  It must run before the unattended
                # curriculum backlog, while still using the same frontier and
                # shared model ledger as every other knowledge node.
                urgency="critical" if is_operator_followup else "high" if retrying or is_linked_prerequisite or index == 1 else "medium",
                expected_value="concept_progress",
                evidence_need=(
                    "re-emit a complete typed replacement hypothesis for the same frontier node"
                    if format_repair else
                    "retry with a narrowed node-specific contribution and avoid the rejected hypothesis"
                    if retrying else "local evidence and typed model synthesis for this frontier node"
                ),
                authority_need="none_for_local_analysis",
                capability_need="local_model_semantic_operation",
                blocking_state=(
                    "format_repair_after_retry_schema_failure" if format_repair
                    else "retry_after_rejection" if retrying else ""
                ),
                salience_explanation=(
                    "The retry response omitted required fields; repair its typed replacement once before blocking the node."
                    if format_repair else
                    "A prior response for this frontier node was rejected; retry once with narrower instructions."
                    if retrying else "Knowledge acquisition advances by selecting the next unresolved frontier node."
                ),
                creation_sequence=len(state.cycles) + index,
                salience_categories=("operator_priority", "knowledge_frontier", "expected_concept_progress"),
                evidence_refs=("operator-natural-goal", node.evidence_id),
            ))
        return _dedupe_focuses(focuses)
    base_categories = ("operator_priority", "goal_discrepancy", "expected_useful_progress")
    focuses.append(CandidateFocus(
        focus_id=stable_id("focus", state.episode_id, goal.goal_id, "primary", len(state.cycles)),
        description=f"Resolve discrepancy for goal: {goal.summary}",
        source="goal_discrepancy",
        related_goal_ids=(goal.goal_id,),
        urgency="medium",
        expected_value="useful_progress",
        evidence_need="local evidence supporting or challenging the goal",
        authority_need="none_for_local_analysis",
        capability_need="local_model_semantic_operation",
        blocking_state="",
        salience_explanation=f"Goal discrepancy is {goal.discrepancy()} and the episode needs a useful outcome.",
        creation_sequence=len(state.cycles) + 1,
        salience_categories=base_categories,
        evidence_refs=tuple(item.evidence_id for item in state.evidence[:3]),
    ))
    if unresolved:
        hyp = unresolved[-1]
        focuses.append(CandidateFocus(
            focus_id=stable_id("focus", state.episode_id, hyp.hypothesis_id, "challenge", len(state.cycles)),
            description=f"Challenge or revise hypothesis: {hyp.statement[:180]}",
            source="hypothesis_revision",
            related_goal_ids=(hyp.originating_goal_id,),
            urgency="high" if hyp.evidence_against else "medium",
            expected_value="belief_revision",
            evidence_need="contrary and supporting evidence",
            authority_need="none_for_local_analysis",
            capability_need="semantic comparison",
            blocking_state="",
            salience_explanation="An active hypothesis needs evidence-linked revision before action.",
            creation_sequence=len(state.cycles) + 1,
            salience_categories=("unresolved_hypothesis", "evidence_revision", "expected_useful_progress"),
            evidence_refs=hyp.evidence_for + hyp.evidence_against,
        ))
    return _dedupe_focuses(focuses)


def select_attention(state: ActiveCognitiveEpisodeState, candidates: Sequence[CandidateFocus]) -> AttentionState:
    prior = state.attention or AttentionState(attention_state_id=stable_id("active-attention", state.episode_id))
    selected = _rank_focuses(candidates)[0] if candidates else None
    if selected is None:
        return replace(prior, stagnation_count=prior.stagnation_count + 1, continuation_reason="no_candidate_focus_available")
    transition = "continue_focus" if selected.focus_id == prior.active_focus_id else ("establish_focus" if not prior.active_focus_id else "switch_focus")
    now = utc_now()
    journal = prior.transition_journal + ({
        "transition": transition,
        "focus_id": selected.focus_id,
        "sequence": prior.cycle_sequence + 1,
        "at": now,
        "reason": selected.salience_explanation,
    },)
    previous = prior.previous_focus_ids
    if prior.active_focus_id and prior.active_focus_id != selected.focus_id:
        previous = tuple(dict.fromkeys(previous + (prior.active_focus_id,)))
    return replace(
        prior,
        active_focus_id=selected.focus_id,
        active_focus_summary=selected.description,
        active_goal_ids=selected.related_goal_ids,
        candidate_focuses=tuple(candidates),
        salience_reasons=(selected.salience_explanation, *selected.salience_categories),
        evidence_refs=selected.evidence_refs,
        unresolved_questions=tuple(item for item in prior.unresolved_questions if item),
        focus_started_at=prior.focus_started_at or now,
        last_progress_at=now,
        progress_summary="selected focus for cognitive operation",
        stagnation_count=0 if transition != "continue_focus" else prior.stagnation_count,
        continuation_reason=selected.salience_explanation if transition == "continue_focus" else "",
        switch_reason=selected.salience_explanation if transition == "switch_focus" else "",
        previous_focus_ids=previous,
        cycle_sequence=prior.cycle_sequence + 1,
        transition_journal=journal,
    )


def interrupt_focus(
    state: ActiveCognitiveEpisodeState,
    *,
    reason: str,
    priority: str = "operator",
    return_condition: str = "resume when interruption is resolved",
) -> ActiveCognitiveEpisodeState:
    attention = state.attention
    if attention is None or not attention.active_focus_id:
        raise ActiveCognitiveLoopError("attention_not_selected")
    now = utc_now()
    journal = attention.transition_journal + ({
        "transition": "interrupt_focus",
        "focus_id": attention.active_focus_id,
        "sequence": attention.cycle_sequence + 1,
        "at": now,
        "reason": reason,
        "priority": priority,
        "return_condition": return_condition,
    },)
    updated_attention = replace(
        attention,
        interruption_priority=priority,
        interruption_reason=reason,
        return_condition=return_condition,
        last_progress_at=now,
        progress_summary="focus interrupted with durable return condition",
        cycle_sequence=attention.cycle_sequence + 1,
        transition_journal=journal,
    )
    return replace(state, attention=updated_attention, loop_state="blocked_operator_decision")


def resume_focus(state: ActiveCognitiveEpisodeState, *, reason: str = "interruption resolved") -> ActiveCognitiveEpisodeState:
    attention = state.attention
    if attention is None or not attention.active_focus_id:
        raise ActiveCognitiveLoopError("attention_not_selected")
    if not attention.interruption_reason:
        raise ActiveCognitiveLoopError("focus_not_interrupted")
    now = utc_now()
    journal = attention.transition_journal + ({
        "transition": "resume_focus",
        "focus_id": attention.active_focus_id,
        "sequence": attention.cycle_sequence + 1,
        "at": now,
        "reason": reason,
        "return_condition": attention.return_condition,
    },)
    updated_attention = replace(
        attention,
        interruption_priority="none",
        interruption_reason="",
        return_condition="",
        last_progress_at=now,
        progress_summary="focus resumed",
        continuation_reason=reason,
        cycle_sequence=attention.cycle_sequence + 1,
        transition_journal=journal,
    )
    return replace(state, attention=updated_attention, loop_state="selecting_focus")


def abandon_focus(state: ActiveCognitiveEpisodeState, *, reason: str) -> ActiveCognitiveEpisodeState:
    attention = state.attention
    if attention is None or not attention.active_focus_id:
        raise ActiveCognitiveLoopError("attention_not_selected")
    now = utc_now()
    prior_focus = attention.active_focus_id
    journal = attention.transition_journal + ({
        "transition": "abandon_focus",
        "focus_id": prior_focus,
        "sequence": attention.cycle_sequence + 1,
        "at": now,
        "reason": reason,
    },)
    updated_attention = replace(
        attention,
        active_focus_id="",
        active_focus_summary="",
        active_goal_ids=(),
        evidence_refs=(),
        unresolved_questions=attention.unresolved_questions + (f"abandoned focus requires replacement: {reason}",),
        abandonment_reason=reason,
        previous_focus_ids=tuple(dict.fromkeys(attention.previous_focus_ids + (prior_focus,))),
        last_progress_at=now,
        progress_summary="focus abandoned and queued for replacement",
        cycle_sequence=attention.cycle_sequence + 1,
        transition_journal=journal,
    )
    return replace(state, attention=updated_attention, loop_state="selecting_focus")


def complete_focus(state: ActiveCognitiveEpisodeState, *, summary: str) -> ActiveCognitiveEpisodeState:
    attention = state.attention
    if attention is None or not attention.active_focus_id:
        raise ActiveCognitiveLoopError("attention_not_selected")
    now = utc_now()
    journal = attention.transition_journal + ({
        "transition": "complete_focus",
        "focus_id": attention.active_focus_id,
        "sequence": attention.cycle_sequence + 1,
        "at": now,
        "reason": summary,
    },)
    artifact = {
        "artifact_id": stable_id("focus-completion", state.episode_id, attention.active_focus_id, summary),
        "artifact_type": "focus_completion_summary",
        "summary": summary,
        "focus_id": attention.active_focus_id,
        "created_at": now,
    }
    updated_attention = replace(
        attention,
        progress_summary=summary,
        last_progress_at=now,
        cycle_sequence=attention.cycle_sequence + 1,
        transition_journal=journal,
    )
    return replace(
        state,
        attention=updated_attention,
        useful_artifacts=state.useful_artifacts + (artifact,),
        loop_state="completed",
        completed=True,
    )


def build_working_memory_packet(state: ActiveCognitiveEpisodeState, *, sequence: int) -> WorkingMemoryPacket:
    attention = state.attention
    if attention is None or not attention.active_focus_id:
        raise ActiveCognitiveLoopError("attention_not_selected")
    goal = state.goals[0]
    focus = next((item for item in attention.candidate_focuses if item.focus_id == attention.active_focus_id), None)
    if focus is None:
        raise ActiveCognitiveLoopError("active_focus_missing")
    budget = int(state.budgets.get("max_packet_items", 8) or 8)
    relevant, conflicting = _select_evidence_for_focus(state, focus, budget=budget)
    is_frontier = focus.source == "knowledge_frontier"
    if is_frontier:
        current_hypotheses = tuple(item.as_record() for item in state.hypotheses if item.originating_focus_id == focus.focus_id)[-3:]
    else:
        current_hypotheses = tuple(item.as_record() for item in state.hypotheses[-3:])
    recent_actions = tuple(dict(item) for item in state.actions[-3:])
    outcomes = tuple(dict(item) for item in state.outcomes[-3:])
    focus_record = focus.as_record()
    if is_frontier:
        node = _active_frontier_node_from_evidence(relevant, focus)
        node_metadata = _frontier_node_prompt_metadata(node)
        prior_rejections = tuple(
            result
            for result in state.operation_results
            if not result.accepted
            and any(cycle.operation_id == result.operation_id and cycle.focus_id == focus.focus_id for cycle in state.cycles)
        )
        retry_requires_new_proposition = not (
            prior_rejections
            and all(
                set(result.rejection_reasons)
                and set(result.rejection_reasons) <= _SUPPLEMENTAL_FRONTIER_REJECTION_REASONS
                for result in prior_rejections[-2:]
            )
        )
        focus_record = {
            **focus_record,
            "active_frontier_node": node_metadata,
            "sibling_frontier_nodes": tuple(
                _frontier_node_prompt_metadata(candidate)
                for candidate in state.evidence
                if candidate.kind == "knowledge_frontier_node" and candidate.evidence_id != node.evidence_id
            ),
            "explicit_dependencies": _frontier_dependency_hypotheses(state, node_metadata),
            "prohibited_duplicate_targets": tuple(
                {
                    "hypothesis_id": item.hypothesis_id,
                    "statement_digest": _semantic_digest(item.statement),
                    "statement": item.statement,
                    "statement_excerpt": item.statement[:220],
                    "statement_tokens": tuple(sorted(_semantic_tokens(item.statement))),
                    "originating_focus_id": item.originating_focus_id,
                }
                for item in state.hypotheses
                if item.originating_focus_id != focus.focus_id
            ) + tuple(
                {
                    "hypothesis_id": result.operation_id,
                    "statement_digest": _semantic_digest(result.interpretation),
                    "statement": result.interpretation,
                    "statement_excerpt": result.interpretation[:220],
                    "statement_tokens": tuple(sorted(_semantic_tokens(result.interpretation))),
                    "originating_focus_id": focus.focus_id,
                    "rejection_reasons": result.rejection_reasons,
                }
                for result in prior_rejections[-2:]
                if result.interpretation and retry_requires_new_proposition
            ),
            "prior_rejection_reasons": tuple(reason for result in prior_rejections[-2:] for reason in result.rejection_reasons),
            "retry_rejected_hypotheses": tuple(
                str(result.interpretation)[:320]
                for result in prior_rejections[-2:]
                if result.interpretation
            ),
            "retry_attempt": len(prior_rejections) + 1 if prior_rejections else 0,
            "retry_requires_new_proposition": retry_requires_new_proposition,
        }
    omitted = max(0, len(state.evidence) + len(state.hypotheses) + len(state.actions) + len(state.outcomes) - budget)
    cycle_id = stable_id("active-cognitive-cycle", state.episode_id, sequence)
    core = {
        "cycle_id": cycle_id,
        "goal_id": goal.goal_id,
        "focus_id": focus.focus_id,
        "hypotheses": current_hypotheses,
        "relevant_evidence": tuple(item.as_record() for item in relevant),
        "conflicting_evidence": tuple(item.as_record() for item in conflicting),
        "recent_actions": recent_actions,
        "outcomes": outcomes,
    }
    packet_digest = _digest(core)
    return WorkingMemoryPacket(
        packet_id=stable_id("working-memory-packet", cycle_id, packet_digest),
        cycle_id=cycle_id,
        active_goal=goal.as_record(),
        active_focus=focus_record,
        current_hypotheses=current_hypotheses,
        relevant_evidence=tuple(item.as_record() for item in relevant),
        conflicting_evidence=tuple(item.as_record() for item in conflicting),
        recent_actions=recent_actions,
        observed_outcomes=outcomes,
        unresolved_questions=attention.unresolved_questions,
        operator_constraints=("no network", "no protected paths", "no commit", "bounded local actions only"),
        authority_state="authorized_for_local_cognitive_marathon",
        capability_limits=("model calls budgeted", "source mutation requires explicit bounded patch authority"),
        prior_cycle_summary=state.cycles[-1].summary if state.cycles else "",
        size_budget=budget,
        omitted_items_summary=f"{omitted} older or less relevant items omitted by packet budget",
        provenance_refs=tuple(dict.fromkeys(focus.evidence_refs + tuple(item.evidence_id for item in relevant) + tuple(item.evidence_id for item in conflicting))),
        construction_rationale="bounded by active focus, goal discrepancy, recency, evidence provenance, and operation need"
        if not is_frontier
        else "bounded by the active knowledge frontier node; unrelated prior hypotheses are excluded from current_hypotheses and listed only as duplicate targets",
        packet_digest=packet_digest,
    )


def select_operation_type(state: ActiveCognitiveEpisodeState, packet: WorkingMemoryPacket) -> str:
    if str(packet.active_focus.get("source") or "") == "knowledge_frontier":
        if str(packet.active_focus.get("blocking_state") or "") == "format_repair_after_retry_schema_failure":
            return "repair_node_specific_hypothesis_format"
        return (
            "reformulate_node_specific_hypothesis"
            if int(packet.active_focus.get("retry_attempt") or 0) > 0
            else "formulate_hypothesis"
        )
    if not state.hypotheses:
        return "formulate_hypothesis"
    latest = state.hypotheses[-1]
    if latest.evidence_against and latest.confidence_state not in {"weakened", "falsified"}:
        if latest.confidence_state in {"contested", "unsupported"}:
            return "summarize_learning"
        return "challenge_hypothesis"
    if latest.confidence_state == "weakened":
        return "revise_hypothesis"
    if latest.confidence_state in {"contested", "supported"} or len(state.cycles) >= 2:
        return "summarize_learning"
    return "compare_evidence"


def build_operation_request(
    state: ActiveCognitiveEpisodeState,
    packet: WorkingMemoryPacket,
    *,
    operation_type: str,
    model_identity: str,
) -> CognitiveOperationRequest:
    if operation_type not in OPERATION_TYPES:
        raise ActiveCognitiveLoopError("unsupported_operation_type")
    expected_output_schema = {
        "operation_result_type": "string",
        "interpretation": "string",
        "evidence_refs": "list",
        "contrary_evidence_considered": "list",
        "uncertainty": "string",
        "recommended_state_transition": "string",
    }
    if operation_type in HYPOTHESIS_OPERATIONS:
        expected_output_schema = {
            "hypothesis_statement": "string",
            "scope": "string",
            "supporting_evidence_refs": "list",
            "assumptions": "list",
            "expected_observations": "list",
            "uncertainty": "string",
            "recommended_state_transition": "string",
        }
    return CognitiveOperationRequest(
        operation_id=stable_id("cognitive-operation", packet.cycle_id, operation_type, packet.packet_digest),
        cycle_id=packet.cycle_id,
        operation_type=operation_type,
        working_memory_packet_digest=packet.packet_digest,
        goal_id=str(packet.active_goal["goal_id"]),
        focus_id=str(packet.active_focus["focus_id"]),
        task=f"Perform {operation_type} for the active focus using only referenced evidence.",
        expected_output_schema=expected_output_schema,
        evidence_constraints=packet.provenance_refs,
        authority_constraints=packet.operator_constraints,
        budget={"max_response_words": 220, "max_retries": 1},
        retry_allowance=1,
        model_identity=model_identity,
        provenance=(packet.packet_id,),
    )


def validate_model_result(
    request: CognitiveOperationRequest,
    packet: WorkingMemoryPacket,
    raw: Mapping[str, Any],
) -> CognitiveOperationResult:
    evidence_ids = {str(item.get("evidence_id") or "") for item in packet.relevant_evidence + packet.conflicting_evidence}
    refs = tuple(str(item) for item in raw.get("evidence_refs", ()) if str(item))
    if not refs:
        refs = tuple(str(item) for item in raw.get("supporting_evidence_refs", ()) if str(item))
    contrary = tuple(str(item) for item in raw.get("contrary_evidence_considered", ()) if str(item))
    refs = _attach_active_frontier_ref_when_aligned(packet, raw, refs)
    rejection: list[str] = []
    if str(raw.get("operation_result_type") or "").endswith("_unavailable"):
        rejection.append("local_model_execution_blocked")
    if request.operation_type in {"reformulate_node_specific_hypothesis", "repair_node_specific_hypothesis_format"}:
        missing_retry_fields = tuple(
            field
            for field in ("hypothesis_statement", "scope", "supporting_evidence_refs")
            if not raw.get(field)
        )
        if missing_retry_fields:
            rejection.append("retry_output_schema_invalid")
            rejection.append("retry_output_schema_missing:" + ",".join(missing_retry_fields))
    if not str(raw.get("interpretation") or "").strip():
        rejection.append("missing_interpretation")
    rejection.extend(str(item) for item in raw.get("adapter_rejection_reasons", ()) if str(item))
    if str(raw.get("uncertainty") or "") == "model_output_was_not_json":
        rejection.append("model_output_not_typed_json")
    invented = tuple(ref for ref in refs + contrary if ref and ref not in evidence_ids)
    if invented:
        rejection.append("unsupported_evidence_reference:" + ",".join(invented))
    if packet.conflicting_evidence and request.operation_type in {"compare_evidence", "challenge_hypothesis"} and not contrary:
        rejection.append("contrary_evidence_not_considered")
    if str(raw.get("recommended_state_transition") or "") == "final_status_success":
        rejection.append("self_certified_success")
    if str(raw.get("recommended_state_transition") or "") == "declare_blocked_capability":
        rejection.append("local_model_execution_blocked")
    transition = str(raw.get("recommended_state_transition") or "")
    if transition and transition not in set(_allowed_transitions_for_operation(request.operation_type)):
        rejection.append("invalid_state_transition")
    rejection.extend(_knowledge_frontier_alignment_rejections(packet, raw, refs))
    rejection.extend(_knowledge_completion_sufficiency_rejections(packet, raw))
    rejection.extend(_knowledge_cross_node_context_rejections(packet, raw))
    evaluation_state, evaluation_reasons = _knowledge_independent_evaluation(packet, raw)
    if evaluation_state in {"contradicted", "insufficient_evidence"}:
        rejection.extend("independent_evaluation_" + reason for reason in evaluation_reasons)
    return CognitiveOperationResult(
        operation_id=request.operation_id,
        operation_result_type=str(raw.get("operation_result_type") or request.operation_type + "_result"),
        interpretation=str(raw.get("interpretation") or ""),
        evidence_refs=refs,
        contrary_evidence_considered=contrary,
        uncertainty=str(raw.get("uncertainty") or "not_stated"),
        assumptions=tuple(str(item) for item in raw.get("assumptions", ()) if str(item)),
        recommended_state_transition=str(raw.get("recommended_state_transition") or ""),
        recommended_action=str(raw.get("recommended_action") or ""),
        next_evidence_need=str(raw.get("next_evidence_need") or ""),
        next_focus_proposal=str(raw.get("next_focus_proposal") or ""),
        raw_model_output=str(raw.get("raw_model_output") or raw.get("interpretation") or ""),
        model_identity=str(raw.get("model_identity") or request.model_identity),
        accepted=not rejection,
        expected_observations=tuple(str(item) for item in raw.get("expected_observations", ()) if str(item)),
        rejection_reasons=tuple(rejection),
        evaluation_state=evaluation_state,
        evaluation_reasons=evaluation_reasons,
    )


def _attach_active_frontier_ref_when_aligned(
    packet: WorkingMemoryPacket,
    raw: Mapping[str, Any],
    refs: Sequence[str],
) -> tuple[str, ...]:
    if str(packet.active_focus.get("source") or "") != "knowledge_frontier":
        return tuple(refs)
    node = dict(packet.active_focus.get("active_frontier_node") or {})
    node_id = str(node.get("node_id") or "")
    if not node_id or node_id in set(refs):
        return tuple(refs)
    label = str(node.get("label") or "")
    criterion = str(node.get("completion_criterion_reference") or "")
    evidence_need = str(node.get("evidence_need") or "")
    result_text = _knowledge_hypothesis_text(raw)
    scope = str(raw.get("scope") or raw.get("recommended_action") or "")
    interpretation = _knowledge_hypothesis_text(raw)
    label_tokens = _semantic_tokens(label)
    controlling_tokens = label_tokens | _semantic_tokens(criterion + " " + evidence_need)
    result_tokens = _semantic_tokens(result_text)
    scope_tokens = _semantic_tokens(scope)
    if controlling_tokens and (
        controlling_tokens & (result_tokens | scope_tokens)
        or _semantic_similarity(result_text, " ".join(controlling_tokens)) >= 0.18
    ):
        return tuple(dict.fromkeys(tuple(refs) + (node_id,)))
    return tuple(refs)


def _knowledge_frontier_alignment_rejections(
    packet: WorkingMemoryPacket,
    raw: Mapping[str, Any],
    refs: Sequence[str],
) -> tuple[str, ...]:
    if str(packet.active_focus.get("source") or "") != "knowledge_frontier":
        return ()
    node = dict(packet.active_focus.get("active_frontier_node") or {})
    node_id = str(node.get("node_id") or "")
    label = str(node.get("label") or "")
    criterion = str(node.get("completion_criterion_reference") or "")
    evidence_need = str(node.get("evidence_need") or "")
    result_text = _knowledge_hypothesis_text(raw)
    scope = str(raw.get("scope") or raw.get("recommended_action") or "")
    interpretation = _knowledge_hypothesis_text(raw)
    rejections: list[str] = []
    packet_evidence_ids = {str(item.get("evidence_id") or "") for item in packet.relevant_evidence + packet.conflicting_evidence}
    if not node_id:
        rejections.append("active_frontier_node_missing_from_packet")
    if node_id and node_id not in set(refs):
        rejections.append("active_node_evidence_not_cited")
    wrong_refs = tuple(ref for ref in refs if ref not in packet_evidence_ids)
    if wrong_refs:
        rejections.append("evidence_reference_not_in_packet:" + ",".join(wrong_refs))
    label_tokens = _semantic_tokens(label)
    criterion_tokens = _semantic_tokens(criterion + " " + evidence_need)
    result_tokens = _semantic_tokens(result_text)
    interpretation_tokens = _semantic_tokens(interpretation)
    scope_tokens = _semantic_tokens(scope)
    scope_matches_label = bool(label_tokens & scope_tokens)
    scope_matches_contract = bool(criterion_tokens & scope_tokens)
    if re.fullmatch(r"(?:knowledge-)?frontier-node-[a-z0-9]+", scope.lower()):
        rejections.append("scope_uses_internal_frontier_node_id")
    if label_tokens and not (label_tokens & interpretation_tokens) and not scope_matches_label:
        rejections.append("scope_not_aligned_with_active_node")
    controlling_tokens = label_tokens | criterion_tokens
    if controlling_tokens and not (controlling_tokens & interpretation_tokens) and not (scope_matches_label or scope_matches_contract):
        rejections.append("interpretation_not_node_specific")
    prior_targets = tuple(packet.active_focus.get("prohibited_duplicate_targets") or ())
    result_digest = _semantic_digest(result_text)
    result_tokens = _semantic_tokens(result_text)
    for target in prior_targets:
        prior = str(target.get("statement") or target.get("statement_excerpt") or "")
        prior_digest = str(target.get("statement_digest") or "")
        prior_tokens = {str(token) for token in target.get("statement_tokens", ()) if str(token)}
        token_similarity = (
            len(result_tokens & prior_tokens) / max(1, len(result_tokens | prior_tokens))
            if result_tokens and prior_tokens
            else 0.0
        )
        if (
            prior_digest and prior_digest == result_digest
            or prior and _semantic_similarity(result_text, prior) >= 0.72
            or token_similarity >= 0.72
        ):
            rejections.append("duplicate_prior_node_contribution")
            break
    if label_tokens and interpretation_tokens and not (label_tokens & interpretation_tokens) and not (scope_matches_label or scope_matches_contract) and _semantic_similarity(result_text, " ".join(label_tokens | criterion_tokens)) < 0.18:
        rejections.append("no_new_node_specific_contribution")
    return tuple(dict.fromkeys(rejections))


def apply_operation_result(
    state: ActiveCognitiveEpisodeState,
    packet: WorkingMemoryPacket,
    request: CognitiveOperationRequest,
    result: CognitiveOperationResult,
    *,
    sequence: int,
) -> ActiveCognitiveEpisodeState:
    if not result.accepted:
        global_failure = any(reason == "local_model_execution_blocked" for reason in result.rejection_reasons)
        cycle = LoopCycle(
            cycle_id=packet.cycle_id,
            sequence=sequence,
            focus_id=request.focus_id,
            operation_id=request.operation_id,
            packet_digest=packet.packet_digest,
            summary="model result rejected: " + ",".join(result.rejection_reasons),
            completed=True,
        )
        return replace(
            state,
            loop_state=(
                "selecting_focus"
                if str(packet.active_focus.get("source") or "") == "knowledge_frontier" and not global_failure
                else "blocked_insufficient_evidence"
            ),
            working_memory_packets=state.working_memory_packets + (packet,),
            operation_requests=state.operation_requests + (request,),
            operation_results=state.operation_results + (result,),
            cycles=state.cycles + (cycle,),
            model_call_count=state.model_call_count + 1,
        )

    hypotheses = state.hypotheses
    outcomes = state.outcomes
    learning = state.learning_updates
    artifacts = state.useful_artifacts
    active_focus = dict(packet.active_focus)
    goal_id = str(packet.active_goal["goal_id"])
    focus_id = str(active_focus["focus_id"])
    now = utc_now()
    transition = result.recommended_state_transition
    if transition == "propose_hypothesis" or not hypotheses:
        hypothesis = HypothesisRecord(
            hypothesis_id=stable_id("hypothesis", state.episode_id, focus_id, result.interpretation),
            statement=result.interpretation,
            scope=str(active_focus.get("description") or ""),
            originating_goal_id=goal_id,
            originating_focus_id=focus_id,
            evidence_for=result.evidence_refs,
            evidence_against=result.contrary_evidence_considered,
            assumptions=result.assumptions,
            expected_observations=("local evidence should support a bounded useful step",),
            confidence_state="plausible" if result.evidence_refs else "tentative",
            lifecycle_state="active",
            created_at=now,
            disposition="needs_challenge",
            provenance=(request.operation_id,),
        )
        hypotheses = hypotheses + (hypothesis,)
    elif transition in {"weaken_hypothesis", "revise_hypothesis"}:
        parent = hypotheses[-1]
        weakened_parent = replace(
            parent,
            confidence_state="weakened",
            lifecycle_state="revised",
            revised_at=now,
            revision_reason="contrary evidence or model challenge required revision",
        )
        revised = HypothesisRecord(
            hypothesis_id=stable_id("hypothesis", state.episode_id, parent.hypothesis_id, result.interpretation),
            statement=result.interpretation,
            scope=parent.scope,
            originating_goal_id=parent.originating_goal_id,
            originating_focus_id=parent.originating_focus_id,
            evidence_for=tuple(dict.fromkeys(parent.evidence_for + result.evidence_refs)),
            evidence_against=tuple(dict.fromkeys(parent.evidence_against + result.contrary_evidence_considered)),
            assumptions=result.assumptions,
            expected_observations=("revised smaller step should match local evidence",),
            confidence_state="contested" if result.contrary_evidence_considered else "supported",
            lifecycle_state="active",
            revision_parent_id=parent.hypothesis_id,
            revision_reason=result.interpretation,
            created_at=now,
            revised_at=now,
            disposition="revised_from_evidence",
            provenance=(request.operation_id,),
        )
        hypotheses = hypotheses[:-1] + (weakened_parent, revised)
    elif transition in {"add_supporting_evidence", "add_conflicting_evidence"} and hypotheses:
        parent = hypotheses[-1]
        hypotheses = hypotheses[:-1] + (replace(
            parent,
            evidence_for=tuple(dict.fromkeys(parent.evidence_for + result.evidence_refs)),
            evidence_against=tuple(dict.fromkeys(parent.evidence_against + result.contrary_evidence_considered)),
            confidence_state="contested" if result.contrary_evidence_considered else "supported",
            revised_at=now,
            revision_reason=result.interpretation,
            provenance=tuple(dict.fromkeys(parent.provenance + (request.operation_id,))),
        ),)
    elif transition in {"reject_hypothesis", "falsify_hypothesis"} and hypotheses:
        parent = hypotheses[-1]
        hypotheses = hypotheses[:-1] + (replace(
            parent,
            evidence_against=tuple(dict.fromkeys(parent.evidence_against + result.contrary_evidence_considered)),
            confidence_state="falsified" if transition == "falsify_hypothesis" else "unsupported",
            lifecycle_state="falsified" if transition == "falsify_hypothesis" else "rejected",
            revised_at=now,
            revision_reason=result.interpretation,
            disposition=transition,
            provenance=tuple(dict.fromkeys(parent.provenance + (request.operation_id,))),
        ),)
    elif request.operation_type == "summarize_learning":
        learning = learning + ({
            "learning_id": stable_id("learning", state.episode_id, request.operation_id),
            "summary": result.interpretation,
            "evidence_refs": result.evidence_refs,
            "created_at": now,
        },)
        artifacts = artifacts + ({
            "artifact_id": stable_id("useful-artifact", state.episode_id, request.operation_id),
            "artifact_type": "cognitive_episode_summary",
            "summary": result.interpretation,
            "evidence_refs": result.evidence_refs,
        },)
    outcome = {
        "outcome_id": stable_id("outcome", state.episode_id, request.operation_id),
        "operation_id": request.operation_id,
        "observed": result.interpretation[:500],
        "expected": request.task,
        "discrepancy": "revised" if transition in {"weaken_hypothesis", "revise_hypothesis", "reject_hypothesis", "falsify_hypothesis"} else "progress_observed",
        "created_at": now,
    }
    outcomes = outcomes + (outcome,)
    cycle = LoopCycle(
        cycle_id=packet.cycle_id,
        sequence=sequence,
        focus_id=request.focus_id,
        operation_id=request.operation_id,
        packet_digest=packet.packet_digest,
        outcome_id=str(outcome["outcome_id"]),
        summary=result.interpretation[:240],
        completed=True,
    )
    completed = bool(learning and artifacts and len(hypotheses) >= 1)
    next_attention = state.attention
    next_candidates = state.next_focus_candidates
    if str(packet.active_focus.get("source") or "") == "knowledge_frontier":
        provisional = replace(
            state,
            operation_requests=state.operation_requests + (request,),
            operation_results=state.operation_results + (result,),
            cycles=state.cycles + (cycle,),
        )
        remaining_candidates = generate_candidate_focuses(provisional)
        prior_attention = state.attention or AttentionState(attention_state_id=stable_id("active-attention", state.episode_id))
        next_attention = replace(
            prior_attention,
            active_focus_id="",
            active_focus_summary="",
            candidate_focuses=remaining_candidates,
            evidence_refs=(),
            continuation_reason="accepted_frontier_node_removed_from_retry_queue",
        )
        next_candidates = remaining_candidates
    return replace(
        state,
        loop_state="completed" if completed else "persisting",
        hypotheses=hypotheses,
        working_memory_packets=state.working_memory_packets + (packet,),
        operation_requests=state.operation_requests + (request,),
        operation_results=state.operation_results + (result,),
        cycles=state.cycles + (cycle,),
        outcomes=outcomes,
        learning_updates=learning,
        useful_artifacts=artifacts,
        model_call_count=state.model_call_count + 1,
        completed=completed,
        attention=next_attention,
        next_focus_candidates=next_candidates,
    )


def write_episode_state(path: str | Path, state: ActiveCognitiveEpisodeState) -> None:
    _validate_state(state)
    _atomic_write(Path(path), state.as_record())


def read_episode_state(path: str | Path) -> ActiveCognitiveEpisodeState:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActiveCognitiveLoopError("corrupt_active_cognitive_loop_state") from exc
    return _state_from_mapping(data)


def active_loop_snapshot(state: ActiveCognitiveEpisodeState) -> dict[str, Any]:
    max_cycles = state.budgets.get("max_cycles")
    max_model_calls = state.budgets.get("max_model_calls")
    attention = state.attention
    latest_hypothesis = state.hypotheses[-1] if state.hypotheses else None
    return {
        "episode_id": state.episode_id,
        "title": state.title,
        "loop_state": state.loop_state,
        "current_goal": state.goals[0].summary if state.goals else "",
        "current_focus": attention.active_focus_summary if attention else "",
        "why_focus": tuple(attention.salience_reasons if attention else ()),
        "current_operation": state.operation_requests[-1].operation_type if state.operation_requests else "",
        "evidence_considered": tuple(item.evidence_id for item in state.evidence[:5]),
        "hypothesis_state": latest_hypothesis.as_record() if latest_hypothesis else {},
        "last_observed_outcome": state.outcomes[-1] if state.outcomes else {},
        "next_intended_step": _next_step(state),
        "blocked_authority_state": state.pending_operator_requests[-1] if state.pending_operator_requests else {},
        "budget_remaining": {
            "cycles": None if max_cycles is None else int(max_cycles) - len(state.cycles),
            "model_calls": None if max_model_calls is None else int(max_model_calls) - state.model_call_count,
        },
        "completed": state.completed,
    }


def evaluate_cognitive_episode(state: ActiveCognitiveEpisodeState) -> dict[str, Any]:
    failures: list[str] = []
    if state.model_call_count < 2:
        failures.append("no_model_cognition")
    if not state.working_memory_packets:
        failures.append("unbounded_context")
    elif any(packet.size_budget > 20 for packet in state.working_memory_packets):
        failures.append("context_dump_failure")
    if not state.hypotheses:
        failures.append("unsupported_hypothesis")
    if not any(item.revision_parent_id or item.confidence_state in {"weakened", "contested", "falsified"} for item in state.hypotheses):
        failures.append("no_evidence_revision")
    if not state.useful_artifacts and not any("useful" in str(outcome.get("discrepancy") or "") for outcome in state.outcomes):
        failures.append("no_useful_outcome")
    if len({cycle.cycle_id for cycle in state.cycles}) != len(state.cycles):
        failures.append("duplicate_cycle")
    if len({request.operation_id for request in state.operation_requests}) != len(state.operation_requests):
        failures.append("duplicate_model_call")
    if state.completed and not state.learning_updates:
        failures.append("fabricated_learning")
    if any("final_status" in packet.prior_cycle_summary.lower() for packet in state.working_memory_packets):
        failures.append("self_certified_success")
    return {
        "passed": not failures,
        "failure_classifications": tuple(failures),
        "observable": active_loop_snapshot(state),
        "model_call_count": state.model_call_count,
        "cycle_count": len(state.cycles),
        "useful_artifact_count": len(state.useful_artifacts),
    }


def operation_schema_for(operation_type: str) -> CognitiveOperationSchema:
    schemas = operation_schema_registry()
    try:
        return schemas[operation_type]
    except KeyError as exc:
        raise ActiveCognitiveLoopError("unknown_operation_schema") from exc


def operation_schema_registry() -> dict[str, CognitiveOperationSchema]:
    default = CognitiveOperationSchema(
        operation_type="default",
        schema_id="operation-schema-default-compare-compatible-v1",
        required_fields=(
            "operation_result_type",
            "interpretation",
            "evidence_refs",
            "contrary_evidence_considered",
            "uncertainty",
            "assumptions",
            "recommended_state_transition",
            "recommended_action",
            "next_evidence_need",
            "next_focus_proposal",
        ),
        optional_fields=(),
        allowed_transitions=(),
        evidence_fields=("evidence_refs", "contrary_evidence_considered"),
        string_array_fields=("evidence_refs", "contrary_evidence_considered", "assumptions"),
        nonempty_string_fields=("interpretation", "uncertainty", "recommended_state_transition"),
    )
    registry = {
        "interpret_state": CognitiveOperationSchema(
            operation_type="interpret_state",
            schema_id="operation-schema-interpret-state-v1",
            required_fields=(
                "state_summary",
                "salient_observations",
                "evidence_refs",
                "unresolved_questions",
                "uncertainty",
                "recommended_next_operation",
            ),
            optional_fields=(),
            allowed_transitions=(
                "prioritize_focus",
                "formulate_hypothesis",
                "identify_evidence_need",
                "compare_evidence",
                "declare_insufficient_evidence",
            ),
            evidence_fields=("evidence_refs",),
            string_array_fields=("salient_observations", "evidence_refs", "unresolved_questions"),
            nonempty_string_fields=("state_summary", "uncertainty", "recommended_next_operation"),
            recommended_operation_field="recommended_next_operation",
        ),
        "prioritize_focus": CognitiveOperationSchema(
            operation_type="prioritize_focus",
            schema_id="operation-schema-prioritize-focus-v1",
            required_fields=("selected_focus_id", "selection_reason", "supporting_evidence_refs", "rejected_focus_ids", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("select_next_focus", "continue_focus", "request_operator_resolution"),
            evidence_fields=("supporting_evidence_refs",),
            string_array_fields=("supporting_evidence_refs", "rejected_focus_ids"),
            nonempty_string_fields=("selected_focus_id", "selection_reason", "uncertainty", "recommended_state_transition"),
        ),
        "formulate_hypothesis": CognitiveOperationSchema(
            operation_type="formulate_hypothesis",
            schema_id="operation-schema-formulate-hypothesis-v1",
            required_fields=("hypothesis_statement", "scope", "supporting_evidence_refs", "assumptions", "expected_observations", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("propose_hypothesis", "declare_insufficient_evidence"),
            evidence_fields=("supporting_evidence_refs",),
            string_array_fields=("supporting_evidence_refs", "assumptions", "expected_observations"),
            nonempty_string_fields=("hypothesis_statement", "scope", "uncertainty", "recommended_state_transition"),
        ),
        "reformulate_node_specific_hypothesis": CognitiveOperationSchema(
            operation_type="reformulate_node_specific_hypothesis",
            schema_id="operation-schema-reformulate-node-specific-hypothesis-v1",
            required_fields=("hypothesis_statement", "scope", "supporting_evidence_refs", "assumptions", "expected_observations", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("propose_hypothesis", "declare_insufficient_evidence"),
            evidence_fields=("supporting_evidence_refs",),
            string_array_fields=("supporting_evidence_refs", "assumptions", "expected_observations"),
            nonempty_string_fields=("hypothesis_statement", "scope", "uncertainty", "recommended_state_transition"),
        ),
        "repair_node_specific_hypothesis_format": CognitiveOperationSchema(
            operation_type="repair_node_specific_hypothesis_format",
            schema_id="operation-schema-repair-node-specific-hypothesis-format-v1",
            required_fields=("hypothesis_statement", "scope", "supporting_evidence_refs", "assumptions", "expected_observations", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("propose_hypothesis", "declare_insufficient_evidence"),
            evidence_fields=("supporting_evidence_refs",),
            string_array_fields=("supporting_evidence_refs", "assumptions", "expected_observations"),
            nonempty_string_fields=("hypothesis_statement", "scope", "uncertainty", "recommended_state_transition"),
        ),
        "identify_evidence_need": CognitiveOperationSchema(
            operation_type="identify_evidence_need",
            schema_id="operation-schema-identify-evidence-need-v1",
            required_fields=(
                "target_claim_or_decision",
                "known_evidence_refs",
                "missing_fact",
                "why_missing_fact_matters",
                "acceptable_evidence_source",
                "bounded_retrieval_action",
                "stop_condition",
                "uncertainty",
                "recommended_state_transition",
            ),
            optional_fields=(),
            allowed_transitions=("request_evidence",),
            evidence_fields=("known_evidence_refs",),
            string_array_fields=("known_evidence_refs",),
            nonempty_string_fields=(
                "target_claim_or_decision",
                "missing_fact",
                "why_missing_fact_matters",
                "acceptable_evidence_source",
                "bounded_retrieval_action",
                "stop_condition",
                "uncertainty",
                "recommended_state_transition",
            ),
            checkpoint_required=False,
        ),
        "compare_evidence": CognitiveOperationSchema(
            operation_type="compare_evidence",
            schema_id="operation-schema-compare-evidence-v1",
            required_fields=(
                "operation_result_type",
                "interpretation",
                "evidence_refs",
                "contrary_evidence_considered",
                "uncertainty",
                "assumptions",
                "recommended_state_transition",
                "recommended_action",
                "next_evidence_need",
                "next_focus_proposal",
            ),
            optional_fields=(),
            allowed_transitions=("add_supporting_evidence", "add_conflicting_evidence", "weaken_hypothesis", "revise_hypothesis"),
            evidence_fields=("evidence_refs", "contrary_evidence_considered"),
            string_array_fields=("evidence_refs", "contrary_evidence_considered", "assumptions"),
            nonempty_string_fields=("operation_result_type", "interpretation", "uncertainty", "recommended_state_transition", "recommended_action"),
        ),
        "challenge_hypothesis": CognitiveOperationSchema(
            operation_type="challenge_hypothesis",
            schema_id="operation-schema-challenge-hypothesis-v1",
            required_fields=("challenged_hypothesis_id", "vulnerability", "contrary_evidence_refs", "disconfirming_observation", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("weaken_hypothesis", "revise_hypothesis", "reject_hypothesis", "falsify_hypothesis"),
            evidence_fields=("contrary_evidence_refs",),
            string_array_fields=("contrary_evidence_refs",),
            nonempty_string_fields=("challenged_hypothesis_id", "vulnerability", "disconfirming_observation", "uncertainty", "recommended_state_transition"),
        ),
        "revise_hypothesis": CognitiveOperationSchema(
            operation_type="revise_hypothesis",
            schema_id="operation-schema-revise-hypothesis-v1",
            required_fields=("prior_hypothesis_id", "revised_statement", "evidence_refs", "contrary_evidence_considered", "revision_reason", "new_confidence_state", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("revise_hypothesis", "reject_hypothesis", "falsify_hypothesis"),
            evidence_fields=("evidence_refs", "contrary_evidence_considered"),
            string_array_fields=("evidence_refs", "contrary_evidence_considered"),
            nonempty_string_fields=("prior_hypothesis_id", "revised_statement", "revision_reason", "new_confidence_state", "uncertainty", "recommended_state_transition"),
        ),
        "propose_plan": CognitiveOperationSchema(
            operation_type="propose_plan",
            schema_id="operation-schema-propose-plan-v1",
            required_fields=("plan_summary", "supporting_evidence_refs", "planned_steps", "risks", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("propose_plan", "request_operator_resolution", "declare_insufficient_evidence"),
            evidence_fields=("supporting_evidence_refs",),
            string_array_fields=("supporting_evidence_refs", "planned_steps", "risks"),
            nonempty_string_fields=("plan_summary", "uncertainty", "recommended_state_transition"),
        ),
        "revise_plan": CognitiveOperationSchema(
            operation_type="revise_plan",
            schema_id="operation-schema-revise-plan-v1",
            required_fields=("prior_plan_id", "revised_plan_summary", "evidence_refs", "revision_reason", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("revise_plan", "request_operator_resolution", "declare_insufficient_evidence"),
            evidence_fields=("evidence_refs",),
            string_array_fields=("evidence_refs",),
            nonempty_string_fields=("prior_plan_id", "revised_plan_summary", "revision_reason", "uncertainty", "recommended_state_transition"),
        ),
        "reflect_on_outcome": CognitiveOperationSchema(
            operation_type="reflect_on_outcome",
            schema_id="operation-schema-reflect-on-outcome-v1",
            required_fields=("expected_outcome", "observed_outcome", "discrepancy", "evidence_refs", "lesson", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("reflect_on_outcome", "weaken_hypothesis", "revise_hypothesis", "summarize_learning"),
            evidence_fields=("evidence_refs",),
            string_array_fields=("evidence_refs",),
            nonempty_string_fields=("expected_outcome", "observed_outcome", "discrepancy", "lesson", "uncertainty", "recommended_state_transition"),
        ),
        "summarize_learning": CognitiveOperationSchema(
            operation_type="summarize_learning",
            schema_id="operation-schema-summarize-learning-v1",
            required_fields=("lesson", "evidence_refs", "unresolved_questions", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("summarize_learning", "select_next_focus"),
            evidence_fields=("evidence_refs",),
            string_array_fields=("evidence_refs", "unresolved_questions"),
            nonempty_string_fields=("lesson", "uncertainty", "recommended_state_transition"),
        ),
        "select_next_focus": CognitiveOperationSchema(
            operation_type="select_next_focus",
            schema_id="operation-schema-select-next-focus-v1",
            required_fields=("selected_focus_id", "salience_reason", "related_goal_ids", "evidence_refs", "deferred_focus_ids", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("select_next_focus", "request_operator_resolution"),
            evidence_fields=("evidence_refs",),
            string_array_fields=("related_goal_ids", "evidence_refs", "deferred_focus_ids"),
            nonempty_string_fields=("selected_focus_id", "salience_reason", "uncertainty", "recommended_state_transition"),
        ),
        "request_operator_resolution": CognitiveOperationSchema(
            operation_type="request_operator_resolution",
            schema_id="operation-schema-request-operator-resolution-v1",
            required_fields=("question", "blocking_reason", "evidence_refs", "options", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("request_operator_resolution",),
            evidence_fields=("evidence_refs",),
            string_array_fields=("evidence_refs", "options"),
            nonempty_string_fields=("question", "blocking_reason", "uncertainty", "recommended_state_transition"),
        ),
        "declare_blocked_capability": CognitiveOperationSchema(
            operation_type="declare_blocked_capability",
            schema_id="operation-schema-declare-blocked-capability-v1",
            required_fields=("capability_gap", "attempted_evidence_refs", "blocking_reason", "bounded_next_action", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("declare_blocked_capability",),
            evidence_fields=("attempted_evidence_refs",),
            string_array_fields=("attempted_evidence_refs",),
            nonempty_string_fields=("capability_gap", "blocking_reason", "bounded_next_action", "uncertainty", "recommended_state_transition"),
        ),
        "declare_insufficient_evidence": CognitiveOperationSchema(
            operation_type="declare_insufficient_evidence",
            schema_id="operation-schema-declare-insufficient-evidence-v1",
            required_fields=("missing_evidence", "attempted_evidence_refs", "why_existing_evidence_is_insufficient", "bounded_next_evidence_request", "uncertainty", "recommended_state_transition"),
            optional_fields=(),
            allowed_transitions=("declare_insufficient_evidence",),
            evidence_fields=("attempted_evidence_refs",),
            string_array_fields=("missing_evidence", "attempted_evidence_refs"),
            nonempty_string_fields=("why_existing_evidence_is_insufficient", "bounded_next_evidence_request", "uncertainty", "recommended_state_transition"),
        ),
    }
    for operation_type in OPERATION_TYPES:
        if operation_type not in registry:
            raise ActiveCognitiveLoopError("operation_schema_registry_incomplete:" + operation_type)
    return registry


def _schema_prompt_record(schema: CognitiveOperationSchema, operation_type: str) -> dict[str, Any]:
    descriptions = {
        "operation_result_type": operation_type + "_result",
        "interpretation": "nonempty operation-specific interpretation",
        "state_summary": "nonempty summary of current state",
        "salient_observations": ["nonempty observation strings grounded in evidence_refs"],
        "evidence_refs": ["IDs only from supplied evidence"],
        "contrary_evidence_considered": ["IDs only from supplied contrary evidence"],
        "unresolved_questions": ["questions that remain unresolved"],
        "uncertainty": "nonempty uncertainty phrase",
        "assumptions": ["explicit assumptions"],
        "recommended_state_transition": "one allowed transition",
        "recommended_next_operation": "one allowed next operation",
        "recommended_action": "bounded next action",
        "next_evidence_need": "missing evidence need or empty string",
        "next_focus_proposal": "next focus proposal or empty string",
        "selected_focus_id": "focus ID selected from candidates",
        "selection_reason": "nonempty reason for focus selection",
        "supporting_evidence_refs": ["IDs only from supplied evidence"],
        "rejected_focus_ids": ["focus IDs not selected"],
        "hypothesis_statement": "falsifiable hypothesis statement",
        "scope": "scope of hypothesis",
        "expected_observations": ["observable expectations"],
        "challenged_hypothesis_id": "hypothesis ID being challenged",
        "vulnerability": "specific vulnerability in the hypothesis",
        "contrary_evidence_refs": ["IDs only from supplied contrary evidence"],
        "disconfirming_observation": "observation that would disconfirm the hypothesis",
        "prior_hypothesis_id": "prior hypothesis ID",
        "revised_statement": "new changed hypothesis statement",
        "revision_reason": "why the revision is needed",
        "new_confidence_state": "qualitative confidence state",
        "expected_outcome": "expected outcome",
        "observed_outcome": "observed outcome",
        "discrepancy": "difference between expected and observed",
        "lesson": "learning from outcome",
        "salience_reason": "why selected focus is salient",
        "related_goal_ids": ["related goal IDs"],
        "deferred_focus_ids": ["focus IDs deferred"],
        "missing_evidence": ["missing evidence descriptions"],
        "attempted_evidence_refs": ["IDs only from supplied evidence already attempted"],
        "why_existing_evidence_is_insufficient": "nonempty insufficiency reason",
        "bounded_next_evidence_request": "bounded request for evidence",
        "evidence_gap": "specific evidence gap",
        "existing_evidence_refs": ["IDs only from supplied evidence already available"],
        "plan_summary": "bounded plan summary",
        "planned_steps": ["bounded step descriptions"],
        "risks": ["risks or constraints"],
        "prior_plan_id": "prior plan ID",
        "revised_plan_summary": "changed plan summary",
        "question": "operator question",
        "blocking_reason": "why operator resolution is needed",
        "options": ["operator options"],
        "capability_gap": "capability gap description",
        "bounded_next_action": "bounded next action",
        "target_claim_or_decision": "specific claim, hypothesis, or decision",
        "known_evidence_refs": ["IDs only from supplied evidence already known"],
        "missing_fact": "one concrete missing factual question",
        "why_missing_fact_matters": "specific effect on hypothesis, confidence, or action",
        "acceptable_evidence_source": "local source category or artifact type",
        "bounded_retrieval_action": "one executable bounded lookup",
        "stop_condition": "what result would satisfy the evidence need",
    }
    return {field: descriptions.get(field, "operation-specific value") for field in schema.required_fields}


def _schema_contract_text(schema: CognitiveOperationSchema) -> str:
    parts = []
    for field in schema.required_fields:
        field_type = "array[string]" if field in schema.string_array_fields else "nonempty string"
        parts.append(f"- {field}: {field_type}")
    return "\n".join(parts)


def _contrary_prompt_clause(schema: CognitiveOperationSchema, contrary: Sequence[Mapping[str, str]]) -> str:
    if "contrary_evidence_considered" not in schema.required_fields:
        return ". Contrary evidence may inform the summary, but do not add a contrary_evidence_considered field"
    return (
        ". Use contrary_evidence_considered only from contrary_evidence IDs: "
        + (", ".join(item["evidence_id"] for item in contrary) or "none")
        + ". If contrary_evidence is not empty, the interpretation must state how it changes or weakens the hypothesis"
    )


def _id_array_rules_text(
    schema: CognitiveOperationSchema,
    supporting: Sequence[Mapping[str, str]],
    contrary: Sequence[Mapping[str, str]],
) -> str:
    evidence_ids = ", ".join(item["evidence_id"] for item in supporting) or "none"
    contrary_ids = ", ".join(item["evidence_id"] for item in contrary) or "none"
    combined_ids = ", ".join(
        dict.fromkeys([item["evidence_id"] for item in supporting] + [item["evidence_id"] for item in contrary])
    ) or "none"
    schema_has_contrary_field = any("contrary" in field for field in schema.evidence_fields)
    lines = [
        "ID ARRAY RULES:",
        "- array values for evidence/ref fields must be exact IDs, never evidence summaries or prose",
    ]
    for field in schema.evidence_fields:
        if field in {"contrary_evidence_considered", "contrary_evidence_refs"}:
            allowed = contrary_ids
        elif field == "evidence_refs" and contrary and not schema_has_contrary_field:
            allowed = combined_ids
        else:
            allowed = evidence_ids
        lines.append(f"- {field} values must be chosen from: {allowed}")
        if allowed == "none":
            lines.append(f"- {field} must be [] because no valid IDs are supplied; do not write none")
    if "contrary_evidence_considered" in schema.required_fields and contrary:
        lines.append("- contrary_evidence_considered must include at least one contrary_evidence ID")
    return "\n".join(lines)


def _operation_specific_prompt_rules(schema: CognitiveOperationSchema) -> str:
    rules = {
        "challenge_hypothesis": (
            "OPERATION RULE: vulnerability must name a concrete weakness in current_hypotheses and connect it to a contrary evidence ID; "
            "do not answer with generic phrases such as local evidence is incomplete; "
            "do not copy the assumption local evidence is complete for this bounded episode as a vulnerability"
        ),
        "revise_hypothesis": (
            "OPERATION RULE: revised_statement must differ semantically from the prior hypothesis and revision_reason must explain the change"
        ),
        "revise_plan": (
            "OPERATION RULE: revised_plan_summary must describe changed plan steps or constraints; "
            "do not restate a plausible working hypothesis and do not use local evidence supports progress as the revision_reason"
        ),
        "formulate_hypothesis": (
            "OPERATION RULE: hypothesis_statement must be testable against future observations"
        ),
        "reformulate_node_specific_hypothesis": (
            "RETRY OPERATION: formulate one new hypothesis_statement for active_frontier_node only. "
            "It must correct the stated rejection reasons, add a materially distinct proposition, and must not restate any prohibited duplicate target."
            " If the retry explicitly says only an observable/application field was missing, retain the proposition only while adding that concrete missing evidence."
        ),
        "repair_node_specific_hypothesis_format": (
            "FORMAT REPAIR OPERATION: return a complete replacement hypothesis record for active_frontier_node. "
            "Do not answer only with uncertainty and do not use generic cognitive-operation fields such as interpretation or next_focus_proposal."
        ),
        "identify_evidence_need": (
            "OPERATION RULE: this optional operation creates one evidence-acquisition work item; "
            "missing_fact must be one concrete question, bounded_retrieval_action must be executable, "
            "and no text field may be none, an operation name, or an evidence ID"
        ),
        "prioritize_focus": (
            "OPERATION RULE: selected_focus_id must be the active_focus focus_id or one supplied candidate focus ID"
        ),
        "select_next_focus": (
            "OPERATION RULE: selected_focus_id must be the active_focus focus_id or one supplied candidate focus ID"
        ),
        "declare_insufficient_evidence": (
            "OPERATION RULE: use this only when supplied evidence is genuinely insufficient and name the bounded missing evidence"
        ),
    }
    return rules.get(schema.operation_type, "")


def _primary_text(response: Mapping[str, Any], schema: CognitiveOperationSchema) -> str:
    for key in (
        "interpretation",
        "state_summary",
        "selection_reason",
        "hypothesis_statement",
        "vulnerability",
        "revised_statement",
        "revision_reason",
        "lesson",
        "salience_reason",
        "why_existing_evidence_is_insufficient",
        "evidence_gap",
        "target_claim_or_decision",
        "missing_fact",
        "why_missing_fact_matters",
        "acceptable_evidence_source",
        "bounded_retrieval_action",
        "stop_condition",
        "plan_summary",
        "revised_plan_summary",
        "question",
        "blocking_reason",
        "capability_gap",
        "bounded_next_action",
    ):
        value = str(response.get(key) or "").strip()
        if value:
            return value
    return ""


def _schema_evidence_refs(response: Mapping[str, Any], schema: CognitiveOperationSchema) -> tuple[str, ...]:
    refs: list[str] = []
    for key in schema.evidence_fields:
        value = response.get(key)
        if isinstance(value, list):
            refs.extend(str(item) for item in value if str(item))
    return tuple(refs)


def _schema_contrary_refs(response: Mapping[str, Any], schema: CognitiveOperationSchema) -> tuple[str, ...]:
    refs: list[str] = []
    for key in schema.evidence_fields:
        if "contrary" not in key:
            continue
        value = response.get(key)
        if isinstance(value, list):
            refs.extend(str(item) for item in value if str(item))
    return tuple(refs)


def _canonicalize_active_frontier_scope(
    packet: WorkingMemoryPacket,
    response: Mapping[str, Any],
) -> dict[str, Any]:
    """Replace only an exact active-node ID echoed into descriptive scope.

    The immutable focus ID and supporting evidence reference own frontier
    identity.  Small local models occasionally echo that evidence ID into the
    human-readable ``scope`` field.  Keeping the raw response intact in the
    ledger snapshot while replacing this one derived presentation field avoids
    rejecting an otherwise source-bound proposition for formatting alone.
    """

    normalized = dict(response)
    if str(packet.active_focus.get("source") or "") != "knowledge_frontier":
        return normalized
    node = dict(packet.active_focus.get("active_frontier_node") or {})
    node_id = str(node.get("node_id") or "")
    label = str(node.get("label") or "").strip()
    if node_id and label and str(normalized.get("scope") or "").strip() == node_id:
        normalized["scope"] = label
    return normalized


def _runtime_payload_from_operation_response(operation_type: str, response: dict[str, Any]) -> dict[str, Any]:
    if operation_type == "interpret_state":
        return {
            **response,
            "operation_result_type": "interpret_state_result",
            "interpretation": str(response.get("state_summary") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": (),
            "recommended_state_transition": "continue_focus",
            "recommended_action": str(response.get("recommended_next_operation") or ""),
            "next_evidence_need": "; ".join(str(item) for item in response.get("unresolved_questions", ()) if str(item)),
            "next_focus_proposal": str(response.get("recommended_next_operation") or ""),
        }
    if operation_type == "prioritize_focus":
        return {
            **response,
            "operation_result_type": "prioritize_focus_result",
            "interpretation": str(response.get("selection_reason") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("supporting_evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": (),
            "recommended_action": str(response.get("selected_focus_id") or ""),
            "next_evidence_need": "",
            "next_focus_proposal": str(response.get("selected_focus_id") or ""),
        }
    if operation_type in HYPOTHESIS_OPERATIONS:
        return {
            **response,
            "operation_result_type": operation_type + "_result",
            "interpretation": str(response.get("hypothesis_statement") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("supporting_evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": tuple(str(item) for item in response.get("assumptions", ()) if str(item)),
            "recommended_action": str(response.get("scope") or ""),
            "next_evidence_need": "",
            "next_focus_proposal": "",
        }
    if operation_type == "challenge_hypothesis":
        return {
            **response,
            "operation_result_type": "challenge_hypothesis_result",
            "interpretation": str(response.get("vulnerability") or ""),
            "evidence_refs": (),
            "contrary_evidence_considered": tuple(str(item) for item in response.get("contrary_evidence_refs", ()) if str(item)),
            "assumptions": (),
            "recommended_action": str(response.get("disconfirming_observation") or ""),
            "next_evidence_need": str(response.get("disconfirming_observation") or ""),
            "next_focus_proposal": str(response.get("challenged_hypothesis_id") or ""),
        }
    if operation_type == "identify_evidence_need":
        return {
            **response,
            "operation_result_type": "identify_evidence_need_result",
            "interpretation": str(response.get("missing_fact") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("known_evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": (),
            "recommended_action": str(response.get("bounded_retrieval_action") or ""),
            "next_evidence_need": str(response.get("missing_fact") or ""),
            "next_focus_proposal": str(response.get("target_claim_or_decision") or ""),
        }
    if operation_type == "revise_hypothesis":
        return {
            **response,
            "operation_result_type": "revise_hypothesis_result",
            "interpretation": str(response.get("revised_statement") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": tuple(str(item) for item in response.get("contrary_evidence_considered", ()) if str(item)),
            "assumptions": (),
            "recommended_action": str(response.get("revision_reason") or ""),
            "next_evidence_need": "",
            "next_focus_proposal": str(response.get("new_confidence_state") or ""),
        }
    if operation_type == "reflect_on_outcome":
        return {
            **response,
            "operation_result_type": "reflect_on_outcome_result",
            "interpretation": str(response.get("lesson") or response.get("discrepancy") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": (),
            "recommended_action": str(response.get("discrepancy") or ""),
            "next_evidence_need": "",
            "next_focus_proposal": "",
        }
    if operation_type == "propose_plan":
        return {
            **response,
            "operation_result_type": "propose_plan_result",
            "interpretation": str(response.get("plan_summary") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("supporting_evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": tuple(str(item) for item in response.get("risks", ()) if str(item)),
            "recommended_action": "; ".join(str(item) for item in response.get("planned_steps", ()) if str(item)),
            "next_evidence_need": "",
            "next_focus_proposal": "",
        }
    if operation_type == "revise_plan":
        return {
            **response,
            "operation_result_type": "revise_plan_result",
            "interpretation": str(response.get("revised_plan_summary") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": (),
            "recommended_action": str(response.get("revision_reason") or ""),
            "next_evidence_need": "",
            "next_focus_proposal": str(response.get("prior_plan_id") or ""),
        }
    if operation_type == "summarize_learning":
        return {
            **response,
            "operation_result_type": "summarize_learning_result",
            "interpretation": str(response.get("lesson") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": (),
            "recommended_action": "",
            "next_evidence_need": "; ".join(str(item) for item in response.get("unresolved_questions", ()) if str(item)),
            "next_focus_proposal": "",
        }
    if operation_type == "select_next_focus":
        return {
            **response,
            "operation_result_type": "select_next_focus_result",
            "interpretation": str(response.get("salience_reason") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": (),
            "recommended_action": str(response.get("selected_focus_id") or ""),
            "next_evidence_need": "",
            "next_focus_proposal": str(response.get("selected_focus_id") or ""),
        }
    if operation_type == "declare_insufficient_evidence":
        return {
            **response,
            "operation_result_type": "declare_insufficient_evidence_result",
            "interpretation": str(response.get("why_existing_evidence_is_insufficient") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("attempted_evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": tuple(str(item) for item in response.get("missing_evidence", ()) if str(item)),
            "recommended_action": str(response.get("bounded_next_evidence_request") or ""),
            "next_evidence_need": str(response.get("bounded_next_evidence_request") or ""),
            "next_focus_proposal": "",
        }
    if operation_type == "request_operator_resolution":
        return {
            **response,
            "operation_result_type": "request_operator_resolution_result",
            "interpretation": str(response.get("blocking_reason") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": tuple(str(item) for item in response.get("options", ()) if str(item)),
            "recommended_action": str(response.get("question") or ""),
            "next_evidence_need": "",
            "next_focus_proposal": "",
        }
    if operation_type == "declare_blocked_capability":
        return {
            **response,
            "operation_result_type": "declare_blocked_capability_result",
            "interpretation": str(response.get("capability_gap") or ""),
            "evidence_refs": tuple(str(item) for item in response.get("attempted_evidence_refs", ()) if str(item)),
            "contrary_evidence_considered": (),
            "assumptions": (),
            "recommended_action": str(response.get("bounded_next_action") or ""),
            "next_evidence_need": "",
            "next_focus_proposal": "",
        }
    return response


def compile_operation_prompt_snapshot(
    request: CognitiveOperationRequest,
    packet: WorkingMemoryPacket,
    *,
    retry_sequence: int = 0,
    request_identity_suffix: str = "",
) -> PromptSnapshot:
    schema = operation_schema_for(request.operation_type)
    supporting = tuple(_evidence_prompt_record(item) for item in packet.relevant_evidence)
    contrary = tuple(_evidence_prompt_record(item) for item in packet.conflicting_evidence)
    response_schema = _schema_prompt_record(schema, request.operation_type)
    prompt_payload = {
        "current_goal": packet.active_goal,
        "active_focus": packet.active_focus,
        "current_hypotheses": packet.current_hypotheses[-1:],
        "evidence_for": supporting,
        "contrary_evidence": contrary,
        "recent_outcomes": packet.observed_outcomes[-1:],
    }
    frontier_node = packet.active_focus.get("active_frontier_node") if isinstance(packet.active_focus, Mapping) else None
    frontier_rule = ""
    retry_response_reminder = ""
    if frontier_node:
        prompt_payload = {
            "current_goal": packet.active_goal,
            "active_frontier_node": frontier_node,
            "explicit_dependencies": tuple(packet.active_focus.get("explicit_dependencies") or ()),
            "evidence_for": supporting,
            "contrary_evidence": contrary,
            "retry_attempt": int(packet.active_focus.get("retry_attempt") or 0),
        }
        retry_rule = ""
        completion_contract = dict(frontier_node.get("minimum_contribution_contract") or {})
        completion_hint = _knowledge_contract_prompt_hint(completion_contract) if completion_contract else ""
        completion_rule = (
            " NODE COMPLETION RULE: a relevant statement is not enough. Provide a concrete explanatory relation and at least "
            + str(int(completion_contract.get("minimum_specific_terms") or 0))
            + " specific content terms beyond the node label; do not use an importance-only assertion. "
            + completion_hint
            if completion_contract else ""
        )
        if int(packet.active_focus.get("retry_attempt") or 0) > 0:
            retry_requires_new_proposition = bool(packet.active_focus.get("retry_requires_new_proposition", True))
            retry_requirement = (
                "Required new proposition: "
                if retry_requires_new_proposition
                else "Required supplemental observable/application evidence for the existing proposition: "
            )
            retry_rule = (
                " RETRY TARGET: The prior answer was rejected for "
                + ", ".join(str(item) for item in packet.active_focus.get("prior_rejection_reasons", ()) if str(item))
                + ". "
                + retry_requirement
                + str(frontier_node.get("completion_criterion_reference") or frontier_node.get("label") or "the active frontier node")
                + ". "
                + completion_hint
            )
            prompt_payload = {
                "active_frontier_node": frontier_node,
                "prior_rejection_reasons": tuple(packet.active_focus.get("prior_rejection_reasons") or ()),
                "rejected_hypotheses_for_this_node": tuple(packet.active_focus.get("retry_rejected_hypotheses") or ()),
                "explicit_dependencies": tuple(packet.active_focus.get("explicit_dependencies") or ()),
                "allowed_supporting_evidence_refs": tuple(item["evidence_id"] for item in supporting),
            }
            retry_response_reminder = (
                "\nFINAL RETRY RESPONSE: return every required key. hypothesis_statement must "
                + ("be a new proposition for " if retry_requires_new_proposition else "remain tied to the existing proposition for ")
                + str(frontier_node.get("label") or "the active frontier node")
                + "; scope must exactly name that node; supporting_evidence_refs must include its node ID. "
                + ("" if retry_requires_new_proposition else "Add the missing concrete observable/application in expected_observations. ")
                + "Do not return only uncertainty, interpretation, or a generic cognitive-operation record."
            )
        frontier_rule = (
            " KNOWLEDGE FRONTIER RULES: Work only on active_frontier_node. "
            "The response scope must match active_frontier_node.label and its completion_criterion_reference. "
            "Only hypothesis_statement is evaluated as the candidate knowledge proposition; scope, assumptions, expected observations, and uncertainty cannot satisfy the node. "
            "Do not restate conclusions from other nodes unless they are necessary dependencies. "
            "Name the specific new relationship, constraint, failure mode, tradeoff, fact, or uncertainty reduction added for this node. "
            "Prior-node claims are checked separately by deterministic duplicate validation; do not use them as generation context unless listed in explicit_dependencies. "
            "If retry_attempt is nonzero, correct prior_rejection_reasons with a node-specific response. When a prior response only missed an observable/application field, preserve its proposition only while supplying that missing field; otherwise state a required new proposition and do not repeat the prior hypothesis or explain another node's mechanism. "
            + completion_rule
            + retry_rule
        )
    prompt_text = (
        "OUTPUT CONTRACT: return only one minified JSON object. The first character must be { and the last character must be }. "
        "Do not use markdown. Do not add explanation outside JSON. Produce exactly these keys and no others. "
        "The following is a type contract, not answer text:\n"
        + _schema_contract_text(schema)
        + "\n"
        + _id_array_rules_text(schema, supporting, contrary)
        + ("\n" + _operation_specific_prompt_rules(schema) if _operation_specific_prompt_rules(schema) else "")
        + "\nTASK: perform only operation "
        + request.operation_type
        + ". Allowed transition/next-operation values: "
        + ", ".join(schema.allowed_transitions)
        + ". For recommended_state_transition or recommended_next_operation, copy exactly one allowed value with no new label"
        + ". Use evidence_refs only from evidence_for IDs: "
        + ", ".join(item["evidence_id"] for item in supporting)
        + _contrary_prompt_clause(schema, contrary)
        + " Empty strings are invalid for required text fields. "
        + "The uncertainty value must be a nonempty phrase naming what remains unresolved. "
        + "Do not copy field descriptions as answers. "
        + "Do not claim the loop, task, system, or episode is successful or complete. "
        + frontier_rule
        + "Do not choose declare_insufficient_evidence when both evidence_for and contrary_evidence are supplied.\n"
        + "CONTEXT_JSON:\n"
        + json.dumps(prompt_payload, sort_keys=True, default=list, separators=(",", ":"))
        + retry_response_reminder
    )
    prompt_digest = _digest({"prompt_text": prompt_text})
    request_identity = stable_id(
        "active-cognitive-ledger-request",
        request.operation_id,
        prompt_digest,
        request_identity_suffix,
        retry_sequence,
    )
    return PromptSnapshot(
        prompt_snapshot_id=stable_id("active-cognitive-prompt", request.operation_id, prompt_digest, retry_sequence),
        prompt_schema_version=PROMPT_SCHEMA_VERSION,
        operation_request=request.as_record(),
        operation_type=request.operation_type,
        cycle_id=request.cycle_id,
        goal_id=request.goal_id,
        focus_id=request.focus_id,
        working_memory_packet_id=packet.packet_id,
        working_memory_packet_digest=packet.packet_digest,
        prompt_text=prompt_text,
        prompt_byte_digest=prompt_digest,
        prompt_length=len(prompt_text.encode("utf-8")),
        evidence_ids_supplied=tuple(str(item.get("evidence_id") or "") for item in packet.relevant_evidence if item.get("evidence_id")),
        contrary_evidence_ids_supplied=tuple(str(item.get("evidence_id") or "") for item in packet.conflicting_evidence if item.get("evidence_id")),
        expected_response_schema=response_schema,
        authority_constraints=request.authority_constraints,
        model_identity=request.model_identity,
        request_identity=request_identity,
        retry_sequence=retry_sequence,
    )


def adapt_operation_response(raw_text: str) -> AdaptedOperationResponse:
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    transformations: list[str] = []
    rejection: list[str] = []
    if normalized != raw_text:
        transformations.append("trim_and_normalize_line_endings")
    text = normalized
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[0].strip().lower() in {"```", "```json"} and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
            transformations.append("removed_single_outer_markdown_fence")
        else:
            rejection.append("ambiguous_markdown_fence")
    parsed: dict[str, Any] = {}
    try:
        value = json.loads(text)
        if isinstance(value, Mapping):
            parsed = dict(value)
        else:
            rejection.append("json_root_not_object")
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start and text[:start].strip() == "" and text[end + 1 :].strip() == "":
            try:
                value = json.loads(text[start : end + 1])
                if isinstance(value, Mapping):
                    parsed = dict(value)
                    transformations.append("extracted_single_complete_json_object")
                else:
                    rejection.append("json_root_not_object")
            except json.JSONDecodeError:
                rejection.append("malformed_output")
        else:
            rejection.append("malformed_output")
    return AdaptedOperationResponse(
        raw_response=raw_text,
        raw_response_digest=_digest({"raw_response": raw_text}),
        adapted_response=parsed,
        adapter_transformations=tuple(transformations),
        adapter_rejection_reasons=tuple(dict.fromkeys(rejection)),
    )


def evaluate_operation_response(
    request: CognitiveOperationRequest,
    packet: WorkingMemoryPacket,
    adapted: AdaptedOperationResponse | Mapping[str, Any],
) -> OperationResponseEvaluation:
    if isinstance(adapted, AdaptedOperationResponse):
        response = dict(adapted.adapted_response)
        failures = list(adapted.adapter_rejection_reasons)
        raw_text = adapted.raw_response
    else:
        response = dict(adapted)
        failures = []
        raw_text = str(response.get("raw_model_output") or "")
    positives: list[str] = []
    schema = operation_schema_for(request.operation_type)
    required = set(schema.required_fields)
    missing = tuple(sorted(key for key in required if key not in response))
    if missing:
        failures.extend("missing_required_field:" + key for key in missing)
    else:
        positives.append("schema_valid")
    interpretation = _primary_text(response, schema)
    for key in schema.nonempty_string_fields:
        if not str(response.get(key) or "").strip():
            failures.append("empty_required_field:" + key)
    if "operation_result_type" in interpretation and "recommended_state_transition" in interpretation:
        failures.append("schema_echo")
    if "single_operation" in raw_text or "allowed_state_transitions" in raw_text:
        failures.append("prompt_echo")
    evidence_ids = {str(item.get("evidence_id") or "") for item in packet.relevant_evidence + packet.conflicting_evidence}
    refs = _schema_evidence_refs(response, schema)
    contrary_refs = _schema_contrary_refs(response, schema)
    invented = tuple(ref for ref in refs if ref not in evidence_ids)
    if invented:
        failures.append("invented_evidence_reference")
    elif refs:
        positives.append("evidence_grounded")
    for key in schema.evidence_fields:
        for ref in response.get(key, ()) if isinstance(response.get(key), list) else ():
            if str(ref) and str(ref) not in evidence_ids:
                failures.append("evidence_array_contains_non_id:" + key)
    has_contrary = bool(packet.conflicting_evidence)
    if has_contrary and request.operation_type in {"compare_evidence", "challenge_hypothesis", "revise_hypothesis", "reflect_on_outcome", "summarize_learning"}:
        if not contrary_refs and "contrary_evidence_considered" in schema.required_fields:
            contrary_refs = tuple(str(item) for item in response.get("contrary_evidence_considered", ()) if str(item))
        if schema.evidence_fields and any("contrary" in field for field in schema.evidence_fields):
            addressed = bool(contrary_refs) and any(ref in {str(item.get("evidence_id") or "") for item in packet.conflicting_evidence} for ref in contrary_refs)
        else:
            addressed = bool(_primary_text(response, schema).strip())
        if not addressed:
            failures.append("ignored_contrary_evidence")
        else:
            positives.append("contrary_evidence_addressed")
    if not str(response.get("uncertainty") or "").strip():
        failures.append("unsupported_confidence")
    else:
        positives.append("uncertainty_explicit")
    if "assumptions" in schema.required_fields:
        assumptions = response.get("assumptions")
        if not isinstance(assumptions, list):
            failures.append("missing_required_field:assumptions")
        else:
            positives.append("assumptions_explicit")
    if "operation_result_type" in schema.required_fields:
        op_type = str(response.get("operation_result_type") or "")
        if request.operation_type not in op_type:
            failures.append("operation_mismatch")
        else:
            positives.append("operation_matched")
    transition = str(response.get("recommended_state_transition") or "")
    allowed = set(schema.allowed_transitions)
    if "recommended_state_transition" in schema.required_fields:
        if transition not in allowed:
            failures.append("invalid_state_transition")
        else:
            positives.append("state_transition_valid")
    if transition == "declare_insufficient_evidence" and packet.relevant_evidence and packet.conflicting_evidence:
        failures.append("insufficient_evidence_escape")
    if request.operation_type in {"revise_hypothesis", "challenge_hypothesis"}:
        if transition not in {"weaken_hypothesis", "revise_hypothesis", "reject_hypothesis", "falsify_hypothesis"}:
            failures.append("no_hypothesis_change")
        elif interpretation.strip():
            positives.append("meaningful_revision")
    if request.operation_type == "challenge_hypothesis":
        vulnerability = str(response.get("vulnerability") or "").strip().lower()
        if "local evidence is complete for this bounded episode" in vulnerability:
            failures.append("vulnerability_copies_assumption")
    if request.operation_type == "interpret_state":
        next_operation = str(response.get("recommended_next_operation") or "")
        if next_operation not in schema.allowed_transitions:
            failures.append("invalid_recommended_next_operation")
        elif next_operation:
            positives.append("state_transition_valid")
    if any(text in interpretation.lower() for text in ("system is functioning", "loop is functioning", "task is complete", "successfully completed")):
        failures.append("unsupported_success_claim")
        failures.append("self_certification")
    min_words = 4 if request.operation_type == "interpret_state" else 8
    if len(interpretation.split()) < min_words or any(text in interpretation.lower() for text in ("as an ai", "i cannot", "not enough information")) and packet.relevant_evidence:
        failures.append("generic_filler")
    if interpretation.strip() and not any(item.startswith("missing_required_field") for item in failures):
        positives.append("useful_next_action")
    unique_failures = tuple(dict.fromkeys(failures))
    return OperationResponseEvaluation(
        passed=not unique_failures,
        failure_classifications=unique_failures,
        positive_observations=tuple(dict.fromkeys(positives)),
    )


def _preferred_model(preferences: Sequence[str], models: Mapping[str, Any]) -> str:
    for pref in preferences:
        for key, spec in models.items():
            if pref in key or pref in spec.name:
                if Path(spec.path).exists():
                    return spec.name
    for spec in models.values():
        if Path(spec.path).exists():
            return spec.name
    return ""


def _operation_prompt(request: CognitiveOperationRequest, packet: WorkingMemoryPacket) -> str:
    return compile_operation_prompt_snapshot(request, packet).prompt_text


def _parse_operation_json(raw_text: str) -> dict[str, Any]:
    adapted = adapt_operation_response(raw_text)
    payload = dict(adapted.adapted_response)
    if adapted.adapter_rejection_reasons:
        payload["adapter_rejection_reasons"] = adapted.adapter_rejection_reasons
    return payload


def _evidence_prompt_record(item: Mapping[str, Any]) -> dict[str, str]:
    return {
        "evidence_id": str(item.get("evidence_id") or ""),
        "source": str(item.get("source") or ""),
        "summary": str(item.get("summary") or "")[:300],
        "content": str(item.get("content") or "")[:700],
    }


def _allowed_transitions_for_operation(operation_type: str) -> tuple[str, ...]:
    transitions = {
        "interpret_state": ("continue_focus", "identify_evidence_need", "declare_insufficient_evidence"),
        "prioritize_focus": ("select_next_focus", "continue_focus", "request_operator_resolution"),
        "formulate_hypothesis": ("propose_hypothesis", "declare_insufficient_evidence"),
        "reformulate_node_specific_hypothesis": ("propose_hypothesis", "declare_insufficient_evidence"),
        "repair_node_specific_hypothesis_format": ("propose_hypothesis", "declare_insufficient_evidence"),
        "identify_evidence_need": ("request_evidence",),
        "compare_evidence": ("add_supporting_evidence", "add_conflicting_evidence", "weaken_hypothesis", "revise_hypothesis"),
        "challenge_hypothesis": ("weaken_hypothesis", "revise_hypothesis", "reject_hypothesis", "falsify_hypothesis"),
        "revise_hypothesis": ("revise_hypothesis", "reject_hypothesis", "falsify_hypothesis"),
        "propose_plan": ("propose_plan", "request_operator_resolution", "declare_insufficient_evidence"),
        "revise_plan": ("revise_plan", "request_operator_resolution", "declare_insufficient_evidence"),
        "reflect_on_outcome": ("reflect_on_outcome", "weaken_hypothesis", "revise_hypothesis", "summarize_learning"),
        "summarize_learning": ("summarize_learning", "select_next_focus"),
        "select_next_focus": ("select_next_focus", "request_operator_resolution"),
        "request_operator_resolution": ("request_operator_resolution",),
        "declare_blocked_capability": ("declare_blocked_capability",),
        "declare_insufficient_evidence": ("declare_insufficient_evidence",),
    }
    return transitions.get(operation_type, ("declare_insufficient_evidence",))


def _write_prompt_snapshot(root: Path, snapshot: PromptSnapshot) -> None:
    prompts = root / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    _atomic_write(prompts / f"{snapshot.prompt_snapshot_id}.json", snapshot.as_record())


def _write_response_snapshot(
    root: Path,
    snapshot: PromptSnapshot,
    terminal: Mapping[str, Any],
    ledger_result: Mapping[str, Any],
    adapted: AdaptedOperationResponse,
) -> None:
    raw_root = root / "raw-responses"
    adapted_root = root / "adapted-responses"
    eval_root = root / "evaluations"
    raw_root.mkdir(parents=True, exist_ok=True)
    adapted_root.mkdir(parents=True, exist_ok=True)
    eval_root.mkdir(parents=True, exist_ok=True)
    raw_record = {
        "prompt_snapshot_id": snapshot.prompt_snapshot_id,
        "ledger_request_id": terminal.get("request_id"),
        "ledger_result_id": terminal.get("result_id"),
        "model_identity": ledger_result.get("model_identity") or terminal.get("model_identity"),
        "raw_response": adapted.raw_response,
        "raw_response_digest": adapted.raw_response_digest,
        "terminal_status": terminal,
    }
    _atomic_write(raw_root / f"{snapshot.prompt_snapshot_id}.json", raw_record)
    _atomic_write(adapted_root / f"{snapshot.prompt_snapshot_id}.json", adapted.as_record())


def _evidence(item: EvidenceRef | Mapping[str, Any]) -> EvidenceRef:
    if isinstance(item, EvidenceRef):
        return item
    return EvidenceRef(
        evidence_id=str(item.get("evidence_id") or stable_id("evidence", item.get("source"), item.get("summary"))),
        source=str(item.get("source") or "local"),
        summary=str(item.get("summary") or ""),
        content=str(item.get("content") or ""),
        kind=str(item.get("kind") or "local_evidence"),
        exists=bool(item.get("exists", True)),
    )


def _dedupe_focuses(focuses: Sequence[CandidateFocus]) -> tuple[CandidateFocus, ...]:
    seen: set[str] = set()
    deduped: list[CandidateFocus] = []
    for focus in focuses:
        key = focus.description.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(focus)
    return tuple(deduped)


def _rank_focuses(candidates: Sequence[CandidateFocus]) -> tuple[CandidateFocus, ...]:
    priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return tuple(sorted(candidates, key=lambda item: (priority.get(item.urgency, 9), item.creation_sequence, item.focus_id)))


def _select_evidence_for_focus(
    state: ActiveCognitiveEpisodeState,
    focus: CandidateFocus,
    *,
    budget: int,
) -> tuple[tuple[EvidenceRef, ...], tuple[EvidenceRef, ...]]:
    wanted = set(focus.evidence_refs)
    relevant: list[EvidenceRef] = []
    conflicting: list[EvidenceRef] = []
    by_id = {item.evidence_id: item for item in state.evidence}
    if focus.source == "knowledge_frontier":
        for evidence_id in focus.evidence_refs:
            item = by_id.get(evidence_id)
            if item is not None:
                relevant.append(item)
    for item in state.evidence:
        if focus.source == "knowledge_frontier" and item.evidence_id in wanted:
            continue
        text = f"{item.summary} {item.content}".lower()
        target = conflicting if any(word in text for word in ("contrary", "conflict", "fails", "not ", "unsupported", "weaken")) else relevant
        if item.evidence_id in wanted or len(relevant) + len(conflicting) < budget:
            target.append(item)
    if focus.source == "knowledge_frontier":
        pinned = [item for item in relevant if item.evidence_id in wanted]
        remainder = [item for item in relevant if item.evidence_id not in wanted]
        return tuple((pinned + remainder)[:budget]), tuple(conflicting[: max(1, budget // 3)])
    return tuple(relevant[:budget]), tuple(conflicting[: max(1, budget // 3)])


def _validate_state(state: ActiveCognitiveEpisodeState) -> None:
    if state.loop_state not in LOOP_STATES:
        raise ActiveCognitiveLoopError("unsupported_loop_state")
    if state.attention and state.attention.schema_version != SCHEMA_VERSION:
        raise ActiveCognitiveLoopError("unsupported_attention_schema")
    for hyp in state.hypotheses:
        if hyp.confidence_state not in CONFIDENCE_STATES:
            raise ActiveCognitiveLoopError("unsupported_confidence_state")
        if hyp.lifecycle_state not in HYPOTHESIS_LIFECYCLE_STATES:
            raise ActiveCognitiveLoopError("unsupported_hypothesis_lifecycle")
    evidence_ids = {item.evidence_id for item in state.evidence}
    for packet in state.working_memory_packets:
        refs = set(packet.provenance_refs)
        if refs - evidence_ids:
            raise ActiveCognitiveLoopError("working_memory_references_missing_evidence")


def _state_from_mapping(data: Mapping[str, Any]) -> ActiveCognitiveEpisodeState:
    attention_data = data.get("attention")
    attention = _attention_from_mapping(attention_data) if isinstance(attention_data, Mapping) else None
    return ActiveCognitiveEpisodeState(
        episode_id=str(data.get("episode_id") or ""),
        title=str(data.get("title") or ""),
        loop_state=str(data.get("loop_state") or "failed_integrity"),
        goals=tuple(CognitiveGoal(**dict(item)) for item in data.get("goals", ())),
        evidence=tuple(EvidenceRef(**dict(item)) for item in data.get("evidence", ())),
        attention=attention,
        hypotheses=tuple(_hypothesis_from_mapping(item) for item in data.get("hypotheses", ())),
        working_memory_packets=tuple(_packet_from_mapping(item) for item in data.get("working_memory_packets", ())),
        operation_requests=tuple(_request_from_mapping(item) for item in data.get("operation_requests", ())),
        operation_results=tuple(_result_from_mapping(item) for item in data.get("operation_results", ())),
        cycles=tuple(LoopCycle(**dict(item)) for item in data.get("cycles", ())),
        actions=tuple(_mapping_from_json(item) for item in data.get("actions", ())),
        outcomes=tuple(_mapping_from_json(item) for item in data.get("outcomes", ())),
        learning_updates=tuple(_mapping_from_json(item) for item in data.get("learning_updates", ())),
        budgets=dict(data.get("budgets") or {}),
        model_call_count=int(data.get("model_call_count") or 0),
        useful_artifacts=tuple(_mapping_from_json(item) for item in data.get("useful_artifacts", ())),
        pending_operator_requests=tuple(_mapping_from_json(item) for item in data.get("pending_operator_requests", ())),
        next_focus_candidates=tuple(_focus_from_mapping(item) for item in data.get("next_focus_candidates", ())),
        completed=bool(data.get("completed", False)),
        schema_version=str(data.get("schema_version") or ""),
    )


def _attention_from_mapping(data: Mapping[str, Any]) -> AttentionState:
    payload = dict(data)
    payload["candidate_focuses"] = tuple(_focus_from_mapping(item) for item in payload.get("candidate_focuses", ()))
    for key in ("active_goal_ids", "salience_reasons", "evidence_refs", "unresolved_questions", "previous_focus_ids", "transition_journal"):
        payload[key] = tuple(payload.get(key) or ())
    return AttentionState(**payload)


def _focus_from_mapping(data: Mapping[str, Any]) -> CandidateFocus:
    payload = dict(data)
    for key in ("related_goal_ids", "salience_categories", "evidence_refs"):
        payload[key] = tuple(payload.get(key) or ())
    return CandidateFocus(**payload)


def _hypothesis_from_mapping(data: Mapping[str, Any]) -> HypothesisRecord:
    payload = dict(data)
    for key in ("evidence_for", "evidence_against", "assumptions", "expected_observations", "provenance"):
        payload[key] = tuple(payload.get(key) or ())
    return HypothesisRecord(**payload)


def _packet_from_mapping(data: Mapping[str, Any]) -> WorkingMemoryPacket:
    payload = dict(data)
    payload["active_goal"] = _mapping_from_json(payload.get("active_goal") or {})
    payload["active_focus"] = _mapping_from_json(payload.get("active_focus") or {})
    for key in ("current_hypotheses", "relevant_evidence", "conflicting_evidence", "recent_actions", "observed_outcomes"):
        payload[key] = tuple(_mapping_from_json(item) for item in payload.get(key) or ())
    for key in ("unresolved_questions", "operator_constraints", "capability_limits", "provenance_refs"):
        payload[key] = tuple(payload.get(key) or ())
    return WorkingMemoryPacket(**payload)


def _request_from_mapping(data: Mapping[str, Any]) -> CognitiveOperationRequest:
    payload = dict(data)
    for key in ("evidence_constraints", "authority_constraints", "provenance"):
        payload[key] = tuple(payload.get(key) or ())
    payload["expected_output_schema"] = dict(payload.get("expected_output_schema") or {})
    payload["budget"] = dict(payload.get("budget") or {})
    return CognitiveOperationRequest(**payload)


def _result_from_mapping(data: Mapping[str, Any]) -> CognitiveOperationResult:
    payload = dict(data)
    for key in ("evidence_refs", "contrary_evidence_considered", "assumptions", "expected_observations", "rejection_reasons", "evaluation_reasons"):
        payload[key] = tuple(payload.get(key) or ())
    return CognitiveOperationResult(**payload)


def _mapping_from_json(data: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_value(value) for key, value in dict(data).items()}


def _json_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_json_value(item) for item in value)
    if isinstance(value, dict):
        return _mapping_from_json(value)
    return value


def _next_step(state: ActiveCognitiveEpisodeState) -> str:
    if state.completed:
        return "inspect useful artifact and select next focus"
    if not state.hypotheses:
        return "formulate a first hypothesis"
    if state.hypotheses[-1].confidence_state in {"tentative", "plausible"}:
        return "challenge the active hypothesis with contrary evidence"
    if state.hypotheses[-1].confidence_state == "weakened":
        return "revise the hypothesis and plan a smaller step"
    return "summarize learning and choose next focus"


__all__ = [
    "ActiveCognitiveEpisodeState",
    "ActiveCognitiveLoopError",
    "AttentionState",
    "CandidateFocus",
    "CognitiveGoal",
    "CognitiveOperationRequest",
    "CognitiveOperationResult",
    "DEFAULT_STATE_PATH",
    "EvidenceRef",
    "HypothesisRecord",
    "LedgerBackedCognitiveModelRunner",
    "OperationResponseEvaluation",
    "PROMPT_SCHEMA_VERSION",
    "PromptSnapshot",
    "ScriptedSemanticModel",
    "WorkingMemoryPacket",
    "abandon_focus",
    "adapt_operation_response",
    "active_loop_snapshot",
    "build_operation_request",
    "build_working_memory_packet",
    "compile_operation_prompt_snapshot",
    "complete_focus",
    "discover_model_inventory",
    "evaluate_operation_response",
    "evaluate_cognitive_episode",
    "generate_candidate_focuses",
    "initialize_episode",
    "read_episode_state",
    "resume_focus",
    "run_cognitive_cycle",
    "run_episode",
    "select_attention",
    "interrupt_focus",
    "write_episode_state",
]
