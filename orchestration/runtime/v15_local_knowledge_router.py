from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


RUNTIME_V15E_LOCAL_ROUTER_FLAGS: dict[str, bool] = {
    "local_knowledge_router_enabled": True,
    "static_topic_registry_enabled": True,
    "provider_calls_enabled": False,
    "provider_calls_performed": False,
    "tool_calls_enabled": False,
    "action_execution_enabled": False,
    "memory_mutation_enabled": False,
    "memory_write_performed": False,
    "canonical_write_enabled": False,
    "canonical_write_performed": False,
    "runtime_recall_active": False,
    "runtime_recall_mutation_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "specialist_routing_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "dataset_export_enabled": False,
    "scheduler_enabled": False,
    "background_listener_enabled": False,
    "background_queue_enabled": False,
    "runtime_defaults_changed": False,
}


class LocalKnowledgeConfidenceLabel(str, Enum):
    LOCAL_STATIC = "local_static"
    LOCAL_REPORT_SUMMARY = "local_report_summary"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class LocalKnowledgeTopic:
    topic_id: str
    match_keywords: tuple[tuple[str, ...], ...]
    answer_text: str
    confidence_label: LocalKnowledgeConfidenceLabel
    source_summary: str
    provider_required: bool = False
    memory_required: bool = False
    training_required: bool = False
    action_required: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class LocalKnowledgeAnswer:
    answer_id: str
    topic_id: str
    answer_text: str
    confidence_label: LocalKnowledgeConfidenceLabel
    source_summary: str
    provider_required: bool = False
    memory_required: bool = False
    training_required: bool = False
    action_required: bool = False
    deterministic_local: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class LocalKnowledgeRoute:
    route_id: str
    user_message: str
    matched: bool
    topic_id: str
    answer: LocalKnowledgeAnswer | None
    matched_keywords: tuple[str, ...]
    safety_status_id: str
    unsupported_reason: str = ""

    def as_dict(self) -> dict[str, object]:
        values = _as_dict(self)
        values["answer"] = self.answer.as_dict() if self.answer else None
        return values


@dataclass(frozen=True)
class LocalKnowledgeUnsupportedResult:
    unsupported_id: str
    user_message: str
    fallback_text: str
    confidence_label: LocalKnowledgeConfidenceLabel = LocalKnowledgeConfidenceLabel.UNSUPPORTED
    provider_required: bool = False
    memory_required: bool = False
    training_required: bool = False
    action_required: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class LocalKnowledgeRouterSafetyStatus:
    safety_status_id: str
    provider_calls_enabled: bool = False
    provider_calls_performed: bool = False
    tool_calls_enabled: bool = False
    action_execution_enabled: bool = False
    memory_mutation_enabled: bool = False
    canonical_write_enabled: bool = False
    runtime_recall_active: bool = False
    runtime_recall_mutation_enabled: bool = False
    hyb1_default_activation_enabled: bool = False
    hyb1_promoted: bool = False
    model_b_default_changed: bool = False
    training_enabled: bool = False
    scheduler_enabled: bool = False
    runtime_defaults_changed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class LocalKnowledgeRouterReportEntry:
    report_entry_id: str
    topic_id: str
    topic_summary: str
    source_summary: str
    confidence_label: LocalKnowledgeConfidenceLabel
    local_only: bool = True
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def build_local_knowledge_topics() -> tuple[LocalKnowledgeTopic, ...]:
    return (
        _topic(
            "replay_consolidation_path",
            (("replay", "consolidation"), ("sleep", "replay"), ("current", "replay", "path")),
            "DELTA's current replay and consolidation path is: manual/raw message -> experience boundary/record -> episodic feedback capture -> replay markers/batches -> replay review -> consolidation candidate -> consolidation decision -> sleep-cycle plan -> canonical memory draft/record design. Canonical writes remain disabled.",
            "V1.4D/V1.4E/V1.4F scaffold reports and V1.5D first interaction template",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "memory_status",
            (("remember",), ("memory", "status"), ("memory", "yet"), ("memory", "write"), ("before", "memory")),
            "DELTA can create local runtime preview traces, but active memory writes, canonical memory, and runtime recall mutation remain disabled. It is not remembering this console question as durable memory.",
            "V1.5 safety flags and knowledge inventory",
        ),
        _topic(
            "canonical_write_status",
            (("canonical", "write"), ("canonical", "writes"), ("canonical", "memory"), ("write", "canonical")),
            "Canonical memory writes remain disabled. V1.4F created canonical store design scaffolding only: drafts, records, decisions, revisions, and rollback plans without active persistence.",
            "V1.4F canonical store design report",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "provider_call_status",
            (("provider", "call"), ("provider", "calls"), ("call", "providers"), ("external", "model"), ("local", "model")),
            "Provider calls are disabled in this console path. The answer is deterministic local scaffold text, not generated by Qwen, Llama, GPT, or any other provider.",
            "V1.5 safety flags",
        ),
        _topic(
            "action_execution_status",
            (("execute", "actions"), ("action", "execution"), ("tool", "calls"), ("perform", "action")),
            "Action execution and tool calls are disabled. V1.4O/V1.4P/V1.4Q only designed authorization, ledger, and dry-run action scaffolds; they do not execute actions.",
            "V1.4O/V1.4P/V1.4Q design reports",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "training_status",
            (("train",), ("training",), ("fine", "tune"), ("weights",), ("model", "weights")),
            "Training, fine-tuning, and model weight updates remain disabled. Codex did not train model weights; V1.4T was a tiny controlled training experiment design scaffold only.",
            "V1.4T and V1.5 inventory reports",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "hyb1_status",
            (("hyb1",), ("hybrid", "prototype"), ("upgraded", "variant")),
            "HYB1 is a dormant, environment-gated Runtime V1.3 prototype. It is not the default, was not promoted, and only becomes opt-in with DELTA_RUNTIME_V13_HYB1_ENABLED=true.",
            "Runtime V1.3 HYB1 dormant prototype validation and invariants",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "model_b_status",
            (("model", "b"), ("default", "runtime"), ("accepted", "default")),
            "Model B remains the accepted default runtime: contextualized corpus support plus the citation_context reasoning usage gate. HYB1 did not replace it.",
            "Runtime V1.3 Model B/HYB1 reports",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "integration_gate_status",
            (("integration", "gate"), ("gates",), ("gate", "status")),
            "The V1.5A integration gate exists as a design scaffold with gates closed by default. It did not activate training, recall, providers, specialist routing, or action execution.",
            "V1.5A integration gate report",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "runtime_console_purpose",
            (("runtime", "console"), ("console", "purpose"), ("ask_delta",), ("first", "interaction"), ("local", "knowledge", "router")),
            "The runtime console is a manual, local, console-only interaction path for deterministic scaffold answers and safety traces. The local knowledge router is a static repo-local answer map behind that console; it is not active recall, provider reasoning, or learned memory.",
            "V1.5D first live interaction path",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "experience_adapter",
            (("experience", "adapter"), ("raw", "input"), ("input", "experience")),
            "The raw input / experience adapter is scaffold-only. It shapes manual input into inert preview records without live ingestion, listeners, schedulers, or memory persistence.",
            "V1.4M raw input / experience adapter design",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "semantic_adapter",
            (("semantic", "adapter"), ("structural", "semantic"), ("semantic", "signal")),
            "The structural semantic adapter and signal tagging schemas are scaffold-only. They define how future candidates can carry evidence roles, lane permissions, and semantic signals without creating live learned memory.",
            "V1.4A/V1.4L scaffold reports",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "feedback_capture",
            (("feedback",), ("episode",), ("episodic",), ("answer", "trace")),
            "Feedback capture is scaffolded as AnswerTrace/observation -> EpisodeTrace -> FeedbackCaptureRecord -> ReplayReviewMarker -> PruningReviewProposal. It records the shape of future learning input but does not learn yet.",
            "V1.4C/V1.4D feedback capture reports",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "controlled_learning",
            (("controlled", "learning"), ("learning", "enabled"), ("learn", "from")),
            "Controlled learning is design-only. DELTA has proposed envelopes, replay review, consolidation decisions, and safety gates, but no active learning, promotion, or pruning is enabled.",
            "V1.4H controlled learning design",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "offline_evaluation",
            (("offline", "evaluation"), ("evaluation", "harness"), ("benchmark",), ("tests",)),
            "Offline evaluation is scaffolded for future comparison and safety review. Current verification is through deterministic repo tests and static reports, not provider-backed benchmark execution.",
            "V1.4S offline evaluation harness design",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "promotion_rollback",
            (("promotion", "rollback"), ("rollback",), ("promote",), ("promotion",)),
            "Promotion and rollback remain design-only. V1.4V created decision scaffolding; no artifacts, concepts, HYB1 variant, or canonical memory records were promoted.",
            "V1.4V promotion/rollback design",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "active_capabilities",
            (("currently", "active"), ("what", "active"), ("active", "capabilities"), ("can", "delta", "do")),
            "Currently active: manual local console questions, deterministic local self-knowledge routing, raw/semantic preview traces, safety status output, and repo-local report/test inspection. These are non-mutating capabilities.",
            "V1.5D/V1.5E active local console path",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "disabled_capabilities",
            (("still", "disabled"), ("disabled", "capabilities"), ("what", "disabled"), ("remains", "disabled")),
            "Still disabled: provider calls, tool calls, action execution, memory writes, canonical writes, runtime recall mutation, active recall bridge, specialist routing, HYB1 default activation, training, dataset export, schedulers, listeners, and queues.",
            "V1.5 safety flags and invariants",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "scaffold_only_capabilities",
            (("scaffold", "only"), ("design", "only"), ("not", "active"), ("inert",)),
            "Scaffold-only capabilities include canonical store design, replay/consolidation design, temporary pruning projection, controlled learning, specialist routing, action authorization, action ledger, dry-run execution, dataset export, and offline evaluation.",
            "V1.4/V1.5 scaffold reports",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "safest_next_activation_gate",
            (("safest", "next"), ("next", "activation"), ("activation", "gate"), ("next", "gate")),
            "The safest next activation gate is still a narrow, observable, reversible gate. Based on the current V1.5 path, the next work should prefer local-console review and limited dry-run validation before enabling any memory, provider, specialist, training, or action path.",
            "V1.5 integration/selective activation reports",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
        _topic(
            "what_delta_cannot_answer_yet",
            (("cannot", "answer"), ("can't", "answer"), ("not", "answer"), ("limitations",), ("world", "questions"), ("arbitrary", "questions"), ("before", "recall")),
            "DELTA cannot yet answer arbitrary world questions from this local path unless the answer is already represented in repo-local scaffold summaries. Provider reasoning, active recall, canonical memory, live external facts, and learned model updates remain unavailable.",
            "V1.5 knowledge inventory report",
            LocalKnowledgeConfidenceLabel.LOCAL_REPORT_SUMMARY,
        ),
    )


def route_local_knowledge_answer(user_message: str) -> LocalKnowledgeRoute:
    message = " ".join(str(user_message).split())
    normalized = _normalize_text(message)
    safety = build_local_knowledge_router_safety_status(message)
    for topic in build_local_knowledge_topics():
        matched_keywords = _matched_keywords(normalized, topic.match_keywords)
        if matched_keywords:
            answer = LocalKnowledgeAnswer(
                answer_id=_stable_id("local-knowledge-answer", topic.topic_id, topic.answer_text),
                topic_id=topic.topic_id,
                answer_text=topic.answer_text,
                confidence_label=topic.confidence_label,
                source_summary=topic.source_summary,
                provider_required=topic.provider_required,
                memory_required=topic.memory_required,
                training_required=topic.training_required,
                action_required=topic.action_required,
            )
            return LocalKnowledgeRoute(
                route_id=_stable_id("local-knowledge-route", message, topic.topic_id, matched_keywords),
                user_message=message,
                matched=True,
                topic_id=topic.topic_id,
                answer=answer,
                matched_keywords=matched_keywords,
                safety_status_id=safety.safety_status_id,
            )
    unsupported = build_local_knowledge_unsupported_result(message)
    return LocalKnowledgeRoute(
        route_id=_stable_id("local-knowledge-route", message, "unsupported"),
        user_message=message,
        matched=False,
        topic_id="unsupported",
        answer=None,
        matched_keywords=(),
        safety_status_id=safety.safety_status_id,
        unsupported_reason=unsupported.fallback_text,
    )


def build_local_knowledge_unsupported_result(user_message: str) -> LocalKnowledgeUnsupportedResult:
    message = " ".join(str(user_message).split())
    return LocalKnowledgeUnsupportedResult(
        unsupported_id=_stable_id("local-knowledge-unsupported", message),
        user_message=message,
        fallback_text=(
            "I cannot answer that from the local DELTA scaffold yet. I can answer repo-local questions about DELTA's "
            "runtime scaffold, phase history, safety boundaries, and local reports, but provider calls, active recall, "
            "memory writes, action execution, training, and HYB1 default activation remain disabled."
        ),
    )


def build_local_knowledge_router_safety_status(user_message: str = "") -> LocalKnowledgeRouterSafetyStatus:
    return LocalKnowledgeRouterSafetyStatus(safety_status_id=_stable_id("local-knowledge-router-safety", user_message))


def build_local_knowledge_router_report_entries() -> tuple[LocalKnowledgeRouterReportEntry, ...]:
    return tuple(
        LocalKnowledgeRouterReportEntry(
            report_entry_id=_stable_id("local-knowledge-router-entry", topic.topic_id),
            topic_id=topic.topic_id,
            topic_summary=topic.answer_text,
            source_summary=topic.source_summary,
            confidence_label=topic.confidence_label,
        )
        for topic in build_local_knowledge_topics()
    )


def validate_local_knowledge_router_safe(route: LocalKnowledgeRoute) -> bool:
    answer = route.answer
    answer_safe = answer is None or (
        answer.provider_required is False
        and answer.memory_required is False
        and answer.training_required is False
        and answer.action_required is False
        and answer.deterministic_local is True
    )
    return (
        answer_safe
        and RUNTIME_V15E_LOCAL_ROUTER_FLAGS["local_knowledge_router_enabled"] is True
        and RUNTIME_V15E_LOCAL_ROUTER_FLAGS["static_topic_registry_enabled"] is True
        and all(
            value is False
            for key, value in RUNTIME_V15E_LOCAL_ROUTER_FLAGS.items()
            if key not in {"local_knowledge_router_enabled", "static_topic_registry_enabled"}
        )
    )


def _topic(
    topic_id: str,
    match_keywords: tuple[tuple[str, ...], ...],
    answer_text: str,
    source_summary: str,
    confidence_label: LocalKnowledgeConfidenceLabel = LocalKnowledgeConfidenceLabel.LOCAL_STATIC,
) -> LocalKnowledgeTopic:
    return LocalKnowledgeTopic(
        topic_id=topic_id,
        match_keywords=match_keywords,
        answer_text=answer_text,
        confidence_label=confidence_label,
        source_summary=source_summary,
    )


def _matched_keywords(normalized: str, keyword_groups: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    for group in keyword_groups:
        if all(_normalize_text(keyword) in normalized for keyword in group):
            return group
    return ()


def _normalize_text(text: str) -> str:
    return " " + " ".join(str(text).lower().replace("?", " ").replace("'", " ").replace("-", " ").split()) + " "


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        elif isinstance(value, tuple):
            values[key] = [item.value if isinstance(item, Enum) else item for item in value]
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(_normalize_part(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, Enum):
        return part.value
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)
