"""Bounded continuity transfer tooling for the episodic learning marathon.

This module is deliberately narrow: it qualifies evidence-linked continuity
records, retrieves them for a related later objective, records explicit
behavioral influence, and evaluates transfer against a baseline. It does not
execute actions, grant authority, or infer semantic truth on behalf of the
model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import re


SCHEMA_VERSION = "continuity_and_episodic_learning_marathon_1_v1"
AUTHORITY_EFFECT_NONE = "none"
VALID_RECORD_STATUSES = {"provisional", "supported", "weakened", "superseded", "retired"}
VALID_THREAD_STATUSES = {"open", "dormant", "reopened", "resolved", "retired"}
VALID_CONCERN_STATES = {"watch_only", "revalidated", "decayed", "retired"}
VALID_PRESSURE_TYPES = {
    "unresolved_thread",
    "operational_lesson",
    "latent_concern",
    "strategy_preference",
    "incubation_reopen",
}
GENERIC_MATCH_TOKENS = {
    "add",
    "all",
    "and",
    "build",
    "create",
    "current",
    "future",
    "generic",
    "later",
    "new",
    "objective",
    "only",
    "plan",
    "prior",
    "related",
    "run",
    "state",
    "step",
    "work",
}


def _normalize_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", value.lower())
        if len(token) >= 3 and token not in GENERIC_MATCH_TOKENS
    }


def digest_payload(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class EpisodicRecord:
    episode_id: str
    objective: str
    outcome_summary: str
    evidence_refs: tuple[str, ...]
    artifact_refs: tuple[str, ...] = ()
    model_operation_refs: tuple[str, ...] = ()
    restart_refs: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContinuityRecord:
    record_id: str
    record_type: str
    summary: str
    source_episode_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    status: str = "provisional"
    confidence: float = 0.5
    context_tags: tuple[str, ...] = ()
    revisable: bool = True
    authority_effect: str = AUTHORITY_EFFECT_NONE
    invalidation_condition: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UnresolvedThread(ContinuityRecord):
    thread_status: str = "open"
    reopening_conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DurableOperationalLesson(ContinuityRecord):
    strategy_preference: str = ""
    expected_failure_avoided: str = ""


@dataclass(frozen=True)
class LatentConcern(ContinuityRecord):
    concern_state: str = "watch_only"
    belief_claim: str = ""


@dataclass(frozen=True)
class LearnedStrategyPreference(ContinuityRecord):
    preferred_strategy: str = ""
    applicable_scope: str = ""
    counterexample_condition: str = ""


@dataclass(frozen=True)
class SaliencePressure(ContinuityRecord):
    pressure_type: str = "operational_lesson"
    attention_effect: str = ""


@dataclass(frozen=True)
class IncubationState(ContinuityRecord):
    incubation_prompt: str = ""
    reopen_after: str = ""


@dataclass(frozen=True)
class ContinuityStateBundle:
    bundle_id: str
    gate_id: str
    episodic_records: tuple[EpisodicRecord, ...]
    continuity_records: tuple[ContinuityRecord, ...]
    created_from: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContinuityPacket:
    objective: str
    context_tags: tuple[str, ...]
    selected_record_ids: tuple[str, ...]
    selected_records: tuple[Mapping[str, Any], ...]
    rejected_record_ids: tuple[str, ...]
    selection_reasons: tuple[str, ...]
    authority_effect: str = AUTHORITY_EFFECT_NONE
    packet_digest: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        if not record["packet_digest"]:
            record["packet_digest"] = digest_payload({key: value for key, value in record.items() if key != "packet_digest"})
        return record


@dataclass(frozen=True)
class InfluenceEvent:
    event_id: str
    objective: str
    continuity_packet_digest: str
    before_plan: tuple[str, ...]
    after_plan: tuple[str, ...]
    changed_dimensions: tuple[str, ...]
    attribution_record_ids: tuple[str, ...]
    authority_effect: str = AUTHORITY_EFFECT_NONE
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


def _record_type(record: ContinuityRecord | Mapping[str, Any]) -> str:
    if isinstance(record, Mapping):
        return str(record.get("record_type") or "")
    return record.record_type


def _record_context_tokens(record: Mapping[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for field_name in ("summary", "strategy_preference", "preferred_strategy", "applicable_scope", "attention_effect"):
        tokens |= _normalize_tokens(str(record.get(field_name) or ""))
    for tag in record.get("context_tags") or ():
        tokens |= _normalize_tokens(str(tag))
    for condition in record.get("reopening_conditions") or ():
        tokens |= _normalize_tokens(str(condition))
    return tokens


def write_json(path: str | Path, payload: Mapping[str, Any] | Sequence[Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_bundle(path: str | Path, bundle: ContinuityStateBundle) -> None:
    write_json(path, bundle.as_record())


def read_bundle(path: str | Path) -> ContinuityStateBundle:
    payload = read_json(path)
    episodes = tuple(EpisodicRecord(**episode) for episode in payload.get("episodic_records", ()))
    records = tuple(_coerce_record(record) for record in payload.get("continuity_records", ()))
    return ContinuityStateBundle(
        bundle_id=str(payload["bundle_id"]),
        gate_id=str(payload["gate_id"]),
        episodic_records=episodes,
        continuity_records=records,
        created_from=tuple(payload.get("created_from", ())),
        schema_version=str(payload.get("schema_version") or SCHEMA_VERSION),
    )


def _coerce_record(payload: Mapping[str, Any]) -> ContinuityRecord:
    record_type = str(payload.get("record_type") or "")
    base_keys = set(ContinuityRecord.__dataclass_fields__)
    extras = {key: value for key, value in payload.items() if key not in base_keys}
    kwargs = {key: payload[key] for key in base_keys if key in payload}
    tuple_fields = {"source_episode_ids", "evidence_refs", "context_tags"}
    for field_name in tuple_fields:
        if field_name in kwargs:
            kwargs[field_name] = tuple(kwargs[field_name])
    if record_type == "unresolved_thread":
        kwargs["reopening_conditions"] = tuple(extras.get("reopening_conditions", ()))
        kwargs["thread_status"] = str(extras.get("thread_status") or "open")
        return UnresolvedThread(**kwargs)
    if record_type == "durable_operational_lesson":
        kwargs["strategy_preference"] = str(extras.get("strategy_preference") or "")
        kwargs["expected_failure_avoided"] = str(extras.get("expected_failure_avoided") or "")
        return DurableOperationalLesson(**kwargs)
    if record_type == "latent_concern":
        kwargs["concern_state"] = str(extras.get("concern_state") or "watch_only")
        kwargs["belief_claim"] = str(extras.get("belief_claim") or "")
        return LatentConcern(**kwargs)
    if record_type == "learned_strategy_preference":
        kwargs["preferred_strategy"] = str(extras.get("preferred_strategy") or "")
        kwargs["applicable_scope"] = str(extras.get("applicable_scope") or "")
        kwargs["counterexample_condition"] = str(extras.get("counterexample_condition") or "")
        return LearnedStrategyPreference(**kwargs)
    if record_type == "salience_pressure":
        kwargs["pressure_type"] = str(extras.get("pressure_type") or "operational_lesson")
        kwargs["attention_effect"] = str(extras.get("attention_effect") or "")
        return SaliencePressure(**kwargs)
    if record_type == "incubation_state":
        kwargs["incubation_prompt"] = str(extras.get("incubation_prompt") or "")
        kwargs["reopen_after"] = str(extras.get("reopen_after") or "")
        return IncubationState(**kwargs)
    return ContinuityRecord(**kwargs)


def validate_bundle(bundle: ContinuityStateBundle) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    episode_ids = {episode.episode_id for episode in bundle.episodic_records}
    evidence_ids = {ref for episode in bundle.episodic_records for ref in episode.evidence_refs}
    seen_record_ids: set[str] = set()
    for record in bundle.continuity_records:
        payload = record.as_record()
        if record.record_id in seen_record_ids:
            reasons.append(f"duplicate_record_id:{record.record_id}")
        seen_record_ids.add(record.record_id)
        if record.status not in VALID_RECORD_STATUSES:
            reasons.append(f"invalid_record_status:{record.record_id}")
        if not record.summary.strip():
            reasons.append(f"empty_summary:{record.record_id}")
        if not record.source_episode_ids or not set(record.source_episode_ids).issubset(episode_ids):
            reasons.append(f"missing_source_episode:{record.record_id}")
        if not record.evidence_refs or not set(record.evidence_refs).issubset(evidence_ids):
            reasons.append(f"missing_evidence_ref:{record.record_id}")
        if record.authority_effect != AUTHORITY_EFFECT_NONE:
            reasons.append(f"authority_effect_not_none:{record.record_id}")
        if not record.revisable and record.status in {"provisional", "supported"}:
            reasons.append(f"nonrevisable_active_record:{record.record_id}")
        if not (0.0 <= float(record.confidence) <= 1.0):
            reasons.append(f"invalid_confidence:{record.record_id}")
        if record.record_type == "latent_concern":
            if payload.get("concern_state") not in VALID_CONCERN_STATES:
                reasons.append(f"invalid_concern_state:{record.record_id}")
            if str(payload.get("belief_claim") or "").strip():
                reasons.append(f"latent_concern_hardened_into_belief:{record.record_id}")
        if record.record_type == "unresolved_thread" and payload.get("thread_status") not in VALID_THREAD_STATUSES:
            reasons.append(f"invalid_thread_status:{record.record_id}")
        if record.record_type == "salience_pressure":
            if payload.get("pressure_type") not in VALID_PRESSURE_TYPES:
                reasons.append(f"invalid_pressure_type:{record.record_id}")
            if not str(payload.get("attention_effect") or "").strip():
                reasons.append(f"missing_attention_effect:{record.record_id}")
        if record.record_type == "learned_strategy_preference":
            if not str(payload.get("applicable_scope") or "").strip():
                reasons.append(f"missing_applicable_scope:{record.record_id}")
            if not str(payload.get("counterexample_condition") or "").strip():
                reasons.append(f"missing_counterexample_condition:{record.record_id}")
            if str(payload.get("applicable_scope") or "").lower().strip() in {"global", "always", "all operator preferences"}:
                reasons.append(f"overbroad_single_episode_preference:{record.record_id}")
    return not reasons, tuple(reasons)


def retrieve_continuity(
    bundle: ContinuityStateBundle,
    *,
    objective: str,
    context_tags: Sequence[str],
    max_records: int = 4,
) -> ContinuityPacket:
    valid, reasons = validate_bundle(bundle)
    if not valid:
        return ContinuityPacket(
            objective=objective,
            context_tags=tuple(context_tags),
            selected_record_ids=(),
            selected_records=(),
            rejected_record_ids=tuple(record.record_id for record in bundle.continuity_records),
            selection_reasons=tuple(f"bundle_invalid:{reason}" for reason in reasons),
        )
    objective_tokens = _normalize_tokens(objective)
    context_tokens = set().union(*(_normalize_tokens(tag) for tag in context_tags)) if context_tags else set()
    target_tokens = objective_tokens | context_tokens
    scored: list[tuple[float, ContinuityRecord, str]] = []
    rejected: list[str] = []
    for record in bundle.continuity_records:
        payload = record.as_record()
        if record.status in {"retired", "superseded"}:
            rejected.append(record.record_id)
            continue
        overlap = target_tokens & _record_context_tokens(payload)
        if len(overlap) < 2:
            rejected.append(record.record_id)
            continue
        score = float(record.confidence) + (0.2 * len(overlap)) + (0.1 if record.status == "supported" else 0.0)
        scored.append((score, record, "matched:" + ",".join(sorted(overlap))))
    scored.sort(key=lambda item: (-item[0], item[1].record_id))
    selected = scored[:max_records]
    packet = ContinuityPacket(
        objective=objective,
        context_tags=tuple(context_tags),
        selected_record_ids=tuple(record.record_id for _, record, _ in selected),
        selected_records=tuple(record.as_record() for _, record, _ in selected),
        rejected_record_ids=tuple(rejected + [record.record_id for _, record, _ in scored[max_records:]]),
        selection_reasons=tuple(reason for _, _, reason in selected),
    )
    return ContinuityPacket(**{**packet.as_record(), "packet_digest": packet.as_record()["packet_digest"]})


def apply_continuity_influence(
    *,
    objective: str,
    before_plan: Sequence[str],
    packet: ContinuityPacket,
    event_id: str,
) -> tuple[tuple[str, ...], InfluenceEvent]:
    after: list[str] = []
    changed: list[str] = []
    records = list(packet.selected_records)
    avoid_architecture = any("architecture" in str(record).lower() or "scaffolding" in str(record).lower() for record in records)
    evidence_first = any("evidence" in str(record).lower() for record in records)
    if evidence_first:
        after.append("inspect prior evidence links before selecting implementation work")
        changed.append("evidence_prioritization")
    if avoid_architecture:
        after.append("reject new UI/schema/runtime architecture unless a live missing transition requires it")
        changed.append("scope_control")
    for step in before_plan:
        if avoid_architecture and any(term in step.lower() for term in ("new ui", "generic framework", "schema layer")):
            continue
        if step not in after:
            after.append(step)
    if records and not changed:
        changed.append("focus_selection")
        after.insert(0, "qualify retrieved continuity before acting")
    event = InfluenceEvent(
        event_id=event_id,
        objective=objective,
        continuity_packet_digest=packet.as_record()["packet_digest"],
        before_plan=tuple(before_plan),
        after_plan=tuple(after),
        changed_dimensions=tuple(dict.fromkeys(changed)),
        attribution_record_ids=packet.selected_record_ids,
    )
    return tuple(after), event


def evaluate_transfer(
    *,
    baseline_metrics: Mapping[str, Any],
    transfer_metrics: Mapping[str, Any],
    packet: ContinuityPacket,
    influence_events: Sequence[InfluenceEvent],
) -> dict[str, Any]:
    failures: list[str] = []
    if not packet.selected_record_ids:
        failures.append("no_continuity_retrieved")
    if not influence_events:
        failures.append("no_explicit_influence_event")
    if influence_events and not any(event.changed_dimensions for event in influence_events):
        failures.append("retrieval_without_behavior_change")
    if bool(baseline_metrics.get("continuity_enabled")):
        failures.append("baseline_contaminated_by_continuity")
    improved_dimensions: list[str] = []
    comparisons = (
        ("time_to_useful_first_action", "lower_is_better"),
        ("unproductive_cycles", "lower_is_better"),
        ("repeated_mistakes", "lower_is_better"),
        ("operator_interventions", "lower_is_better"),
        ("scope_drift_events", "lower_is_better"),
        ("evidence_quality", "higher_is_better"),
        ("final_artifact_quality", "higher_is_better"),
    )
    for metric, direction in comparisons:
        if metric not in baseline_metrics or metric not in transfer_metrics:
            continue
        baseline = float(baseline_metrics[metric])
        transfer = float(transfer_metrics[metric])
        if direction == "lower_is_better" and transfer < baseline:
            improved_dimensions.append(metric)
        if direction == "higher_is_better" and transfer > baseline:
            improved_dimensions.append(metric)
    if bool(transfer_metrics.get("avoided_known_failure")):
        improved_dimensions.append("avoided_known_failure")
    if not improved_dimensions:
        failures.append("no_useful_transfer_improvement")
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": not failures,
        "failure_reasons": failures,
        "improved_dimensions": tuple(dict.fromkeys(improved_dimensions)),
        "selected_record_ids": packet.selected_record_ids,
        "influence_event_ids": tuple(event.event_id for event in influence_events),
        "authority_effect": AUTHORITY_EFFECT_NONE,
    }
