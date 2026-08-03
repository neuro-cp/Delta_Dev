"""Governed provisional-semantic graph and offline consolidation contracts.

This module is intentionally provider-free.  It records waking cognition as
provisional, versioned semantic material, seals dependency-complete review
packets, and applies only administrative, deterministic admission decisions.
It does not schedule work, call an Oracle, or mutate legacy durable memory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


SCHEMA_VERSION = "provisional_semantic_consolidation_v1"
POLICY_VERSION = "oracle_admission_v1"
SOURCE_CLASSES = frozenset({
    "operator_statement",
    "local_model_output",
    "deterministic_calculation",
    "document_excerpt",
    "runtime_observation",
    "oracle_review",
    "administrative_operator_revision",
})
ONLINE_STATES = frozenset({
    "provisional",
    "pending_consolidation",
    "locally_contradicted",
    "uncertain",
    "insufficient_local_evidence",
})
REVIEW_STATES = frozenset({
    "validated",
    "partially_valid",
    "requires_revision",
    "unsupported",
    "contradicted",
    "quarantined",
    "invalidated",
    "pending_operator_consolidation_review",
    "escalated_operator",
})
ORACLE_VERDICTS = frozenset({"validated", "partially_valid", "requires_revision", "unsupported", "contradicted", "invalid"})
ADMINISTRATIVE_ACTIONS = frozenset({
    "approve",
    "reject",
    "approve_partial",
    "replace_fragment",
    "revise_claim",
    "split_claim",
    "merge_claims",
    "recompose_cluster",
    "retain_provisional",
    "quarantine",
    "invalidate",
    "request_re_review",
    "escalate_for_more_evidence",
})
ADMISSION_ACTIONS = frozenset({"promote", "promote_partial", "revise", "retain_provisional", "quarantine", "invalidate", "escalate_operator"})
FUNCTIONAL_RELATION_TYPES = frozenset({
    "collects_from", "transfers_through", "accumulates_in", "limited_by_capacity",
    "activates_at_threshold", "discharges_through", "regulates", "inhibits",
    "reinforces", "depends_on", "transforms", "detects", "corrects",
    "competes_for", "resumes_after", "triggers", "buffers",
    "degrades_under_load", "recovers_after_release",
})


class ConsolidationIntegrityError(ValueError):
    """Raised when an immutable graph or review invariant is violated."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _semantic_fingerprint(text: str) -> str:
    tokens = sorted(set(re.findall(r"[a-z0-9][a-z0-9-]{2,}", str(text).lower())))
    return _digest({"tokens": tokens})


def _record(instance: Any) -> dict[str, Any]:
    return asdict(instance)


@dataclass(frozen=True)
class SemanticExperience:
    experience_id: str
    source_class: str
    authority_class: str
    content: str
    origin_refs: tuple[str, ...]
    created_at: str
    content_digest: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class SemanticRationale:
    rationale_id: str
    summary: str
    experience_refs: tuple[str, ...]
    source_claim_refs: tuple[str, ...]
    created_at: str
    fingerprint: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class SemanticClaim:
    claim_id: str
    originating_goal_id: str
    originating_node_id: str
    created_at: str
    protected_memory: bool = False
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class ClaimFragment:
    fragment_id: str
    claim_version_id: str
    exact_text: str
    ordinal: int
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class ClaimVersion:
    claim_version_id: str
    claim_id: str
    version_index: int
    exact_text: str
    epistemic_state: str
    rationale_refs: tuple[str, ...]
    assumption_refs: tuple[str, ...]
    uncertainty_refs: tuple[str, ...]
    source_experience_refs: tuple[str, ...]
    semantic_fingerprint: str
    created_at: str
    supersedes_version_id: str = ""
    validated_under_review_id: str = ""
    validated_against_packet_digest: str = ""
    validation_scope: str = ""
    validation_policy_version: str = ""
    validation_timestamp: str = ""
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class SemanticRelation:
    relation_id: str
    relation_type: str
    source_ref: str
    target_ref: str
    created_at: str
    provenance_refs: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SemanticConcept:
    concept_id: str
    label: str
    created_at: str
    provenance_refs: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class SemanticEdge:
    edge_id: str
    edge_type: str
    source_ref: str
    target_ref: str
    created_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class ReviewRecord:
    review_id: str
    packet_id: str
    packet_digest: str
    oracle_metadata: Mapping[str, Any]
    claim_reviews: tuple[Mapping[str, Any], ...]
    reviewed_at: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class AdministrativeReviewOverlay:
    overlay_id: str
    review_id: str
    claim_version_id: str
    action: str
    role: str
    operator_id: str
    replacement_text: str = ""
    selected_fragment_ids: tuple[str, ...] = ()
    created_at: str = ""
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class AdmissionRecord:
    admission_id: str
    review_id: str
    overlay_id: str
    claim_version_id: str
    action: str
    resulting_claim_version_id: str
    created_at: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class AdaptationTraceReference:
    trace_id: str
    goal_id: str
    node_id: str
    operation_id: str
    model_identity: str
    source_experience_ref: str
    claim_version_id: str
    local_disposition: str
    review_id: str = ""
    administrative_disposition: str = ""
    corrected_formulation: str = ""
    propagation_refs: tuple[str, ...] = ()
    created_at: str = ""
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class EpisodicTrace:
    trace_id: str
    episode_id: str
    objective_id: str
    operation_ids: tuple[str, ...]
    semantic_unit_refs: tuple[str, ...]
    terminal_status: str
    sealed_at: str
    digest: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class ConsolidationCohort:
    cohort_id: str
    trigger: str
    episode_refs: tuple[str, ...]
    claim_version_refs: tuple[str, ...]
    dependency_clusters: tuple[Mapping[str, Any], ...]
    contradiction_refs: tuple[str, ...]
    duplicate_clusters: tuple[Mapping[str, Any], ...]
    unresolved_claim_refs: tuple[str, ...]
    adaptation_trace_refs: tuple[str, ...]
    creation_policy: Mapping[str, Any]
    created_at: str
    cohort_digest: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class SealedConsolidationPacket:
    packet_id: str
    packet_version: int
    cohort_id: str
    packet_digest: str
    schema_version: str
    policy_version: str
    payload: Mapping[str, Any]
    created_at: str
    privacy_metadata: Mapping[str, Any]


@dataclass(frozen=True)
class ProvisionalSemanticGraphState:
    graph_id: str
    experiences: tuple[SemanticExperience, ...] = ()
    rationales: tuple[SemanticRationale, ...] = ()
    claims: tuple[SemanticClaim, ...] = ()
    claim_versions: tuple[ClaimVersion, ...] = ()
    claim_fragments: tuple[ClaimFragment, ...] = ()
    relations: tuple[SemanticRelation, ...] = ()
    concepts: tuple[SemanticConcept, ...] = ()
    edges: tuple[SemanticEdge, ...] = ()
    reviews: tuple[ReviewRecord, ...] = ()
    overlays: tuple[AdministrativeReviewOverlay, ...] = ()
    admissions: tuple[AdmissionRecord, ...] = ()
    adaptation_traces: tuple[AdaptationTraceReference, ...] = ()
    episodic_traces: tuple[EpisodicTrace, ...] = ()
    cohorts: tuple[ConsolidationCohort, ...] = ()
    packets: tuple[SealedConsolidationPacket, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return _record(self)


def empty_graph(*, root_hint: str = "") -> ProvisionalSemanticGraphState:
    return ProvisionalSemanticGraphState(graph_id=stable_id("provisional-semantic-graph", root_hint or "default"))


def record_provisional_functional_relation(
    graph: ProvisionalSemanticGraphState,
    *,
    relation_type: str,
    source_ref: str,
    target_ref: str,
    provenance_refs: Sequence[str],
    confidence: float = 0.0,
    source_class: str = "runtime_observation",
    originating_episode_id: str = "",
    originating_operation_id: str = "",
    revision_of_relation_id: str = "",
    invalidation_state: str = "active",
) -> tuple[ProvisionalSemanticGraphState, SemanticRelation]:
    """Append a graph-owned functional hypothesis without granting factual authority."""

    if relation_type not in FUNCTIONAL_RELATION_TYPES:
        raise ConsolidationIntegrityError("unsupported_functional_relation:" + relation_type)
    if not source_ref or not target_ref or not tuple(provenance_refs):
        raise ConsolidationIntegrityError("functional_relation_requires_bound_provenance")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ConsolidationIntegrityError("functional_relation_confidence_out_of_range")
    if source_class not in SOURCE_CLASSES:
        raise ConsolidationIntegrityError("functional_relation_unknown_source_class:" + source_class)
    if invalidation_state not in {"active", "superseded", "invalidated", "quarantined"}:
        raise ConsolidationIntegrityError("functional_relation_invalid_invalidation_state:" + invalidation_state)
    relation = SemanticRelation(
        relation_id=stable_id("provisional-functional-relation", relation_type, source_ref, target_ref, *tuple(provenance_refs)),
        relation_type=relation_type,
        source_ref=source_ref,
        target_ref=target_ref,
        created_at=utc_now(),
        provenance_refs=tuple(provenance_refs),
        metadata={
            "epistemic_state": "pending_consolidation",
            "confidence": float(confidence),
            "review_state": "unreviewed",
            "source_class": source_class,
            "originating_episode_id": originating_episode_id,
            "originating_operation_id": originating_operation_id,
            "revision_of_relation_id": revision_of_relation_id,
            "invalidation_state": invalidation_state,
            "relation_version": 1,
        },
    )
    return _append(graph, "relations", relation), relation


def graph_path(runtime_root: str | Path) -> Path:
    return Path(runtime_root) / "consolidation" / "provisional_semantic_graph.json"


def trace_path(runtime_root: str | Path, episode_id: str) -> Path:
    return Path(runtime_root) / "consolidation" / "episodic_traces" / f"{episode_id}.json"


def load_graph(runtime_root: str | Path) -> ProvisionalSemanticGraphState:
    path = graph_path(runtime_root)
    if not path.exists():
        return empty_graph(root_hint=str(Path(runtime_root)))
    return graph_from_record(json.loads(path.read_text(encoding="utf-8")))


def save_graph(runtime_root: str | Path, graph: ProvisionalSemanticGraphState) -> None:
    _atomic_write_json(graph_path(runtime_root), graph.as_record())


def record_associative_insight(
    graph: ProvisionalSemanticGraphState,
    *,
    exploration: Any,
    insight: Mapping[str, str],
    ledger_result: Mapping[str, Any],
) -> tuple[ProvisionalSemanticGraphState, str]:
    """Record one model-assisted association as evidence, never as a relation admission."""

    experience_id = stable_id("semantic-experience", "association-insight", str(exploration.exploration_id))
    if any(item.experience_id == experience_id for item in graph.experiences):
        return graph, experience_id
    content = json.dumps(dict(insight), sort_keys=True)
    experience = _experience(
        experience_id,
        "local_model_output",
        "model_generated_provisional_associative_insight",
        content,
        tuple(exploration.source_record_ids) + tuple(exploration.relation_edge_ids) + (str(exploration.candidate_id),),
        {
            "record_kind": "provisional_associative_insight",
            "association_candidate_id": str(exploration.candidate_id),
            "approval_request_id": str(exploration.approval_request_id),
            "ledger_request_id": str(exploration.ledger_request_id),
            "ledger_result_id": str(ledger_result.get("result_id") or ""),
            "model_identity": str(ledger_result.get("model_identity") or ""),
            "epistemic_state": "pending_consolidation",
        },
    )
    rationale = SemanticRationale(
        stable_id("semantic-rationale", "association-insight", str(exploration.exploration_id)),
        str(insight["shared_structure"]),
        (experience_id,),
        tuple(exploration.source_record_ids),
        utc_now(),
        _semantic_fingerprint(str(insight["shared_structure"])),
    )
    graph = replace(graph, experiences=graph.experiences + (experience,), rationales=graph.rationales + (rationale,))
    graph, _ = _record_insight_claim(
        graph,
        experience_id=experience_id,
        exact_text=str(insight["possible_implication"]),
        rationale=rationale,
        record_kind="provisional_associative_insight",
        source_claim_refs=tuple(exploration.source_record_ids),
    )
    return graph, experience_id


def record_revised_associative_insight(
    graph: ProvisionalSemanticGraphState,
    *,
    experience: SemanticExperience,
    original_insight_id: str,
) -> tuple[ProvisionalSemanticGraphState, str]:
    """Project a revised insight into the canonical provisional-claim path.

    The original insight stays immutable.  This creates a separate provisional
    claim whose provenance carries the review and revisit lineage, so an
    existing cohort can seal it without reopening an earlier packet.
    """

    if any(item.experience_id == experience.experience_id for item in graph.experiences):
        return graph, _insight_claim_version_id(experience.experience_id)
    try:
        details = json.loads(experience.content)
    except (TypeError, json.JSONDecodeError):
        details = {}
    revised = str(details.get("revised_proposition") or "").strip()
    if not revised:
        raise ConsolidationIntegrityError("revised_insight_requires_proposition")
    original_claim = next(
        (item for item in graph.claim_versions if original_insight_id in item.source_experience_refs),
        None,
    )
    rationale = SemanticRationale(
        stable_id("semantic-rationale", "revised-association-insight", experience.experience_id),
        revised,
        (experience.experience_id,),
        (original_claim.claim_version_id,) if original_claim is not None else (),
        utc_now(),
        _semantic_fingerprint(revised),
    )
    graph = replace(graph, experiences=graph.experiences + (experience,), rationales=graph.rationales + (rationale,))
    graph, claim_version_id = _record_insight_claim(
        graph,
        experience_id=experience.experience_id,
        exact_text=revised,
        rationale=rationale,
        record_kind="revised_provisional_associative_insight",
        source_claim_refs=(original_claim.claim_version_id,) if original_claim is not None else (),
    )
    if original_claim is not None:
        relation = SemanticRelation(
            stable_id("provisional-functional-relation", "corrects", claim_version_id, original_claim.claim_version_id, experience.experience_id),
            "corrects",
            claim_version_id,
            original_claim.claim_version_id,
            utc_now(),
            (experience.experience_id,),
            {"epistemic_state": "pending_consolidation", "review_state": "unreviewed"},
        )
        graph = _append(graph, "relations", relation)
    return graph, claim_version_id


def _insight_claim_version_id(experience_id: str) -> str:
    claim_id = stable_id("semantic-claim", "interactive-insight", experience_id)
    return stable_id("semantic-claim-version", claim_id, "1")


def _record_insight_claim(
    graph: ProvisionalSemanticGraphState,
    *,
    experience_id: str,
    exact_text: str,
    rationale: SemanticRationale,
    record_kind: str,
    source_claim_refs: Sequence[str],
) -> tuple[ProvisionalSemanticGraphState, str]:
    """Append one source-bound provisional claim for an insight experience."""

    claim_version_id = _insight_claim_version_id(experience_id)
    if any(item.claim_version_id == claim_version_id for item in graph.claim_versions):
        return graph, claim_version_id
    claim_id = stable_id("semantic-claim", "interactive-insight", experience_id)
    claim = SemanticClaim(claim_id, "interactive_cognition", record_kind, utc_now())
    version = ClaimVersion(
        claim_version_id,
        claim_id,
        1,
        exact_text,
        "pending_consolidation",
        (rationale.rationale_id,),
        (),
        (),
        (experience_id,),
        _semantic_fingerprint(exact_text),
        utc_now(),
    )
    fragment = ClaimFragment(stable_id("semantic-fragment", claim_version_id, "1"), claim_version_id, exact_text, 1)
    graph = replace(
        graph,
        claims=graph.claims + (claim,),
        claim_versions=graph.claim_versions + (version,),
        claim_fragments=graph.claim_fragments + (fragment,),
        edges=graph.edges + (
            _edge("derived_from", claim_version_id, rationale.rationale_id),
            _edge("grounded_in", rationale.rationale_id, experience_id),
        ),
    )
    return graph, claim_version_id


def graph_from_record(record: Mapping[str, Any]) -> ProvisionalSemanticGraphState:
    def items(key: str, factory: Any) -> tuple[Any, ...]:
        return tuple(factory(item) for item in record.get(key, ()) if isinstance(item, Mapping))

    return ProvisionalSemanticGraphState(
        graph_id=str(record.get("graph_id") or stable_id("provisional-semantic-graph", "restored")),
        experiences=items("experiences", _experience_from_record),
        rationales=items("rationales", _rationale_from_record),
        claims=items("claims", _claim_from_record),
        claim_versions=items("claim_versions", _claim_version_from_record),
        claim_fragments=items("claim_fragments", _fragment_from_record),
        relations=items("relations", _relation_from_record),
        concepts=items("concepts", _concept_from_record),
        edges=items("edges", _edge_from_record),
        reviews=items("reviews", _review_from_record),
        overlays=items("overlays", _overlay_from_record),
        admissions=items("admissions", _admission_from_record),
        adaptation_traces=items("adaptation_traces", _adaptation_from_record),
        episodic_traces=items("episodic_traces", _trace_from_record),
        cohorts=items("cohorts", _cohort_from_record),
        packets=items("packets", _packet_from_record),
        schema_version=str(record.get("schema_version") or SCHEMA_VERSION),
    )


def ingest_knowledge_episode(
    graph: ProvisionalSemanticGraphState,
    *,
    objective: Any,
    episode: Any,
    terminal_status: str = "",
) -> ProvisionalSemanticGraphState:
    """Project an existing episode into provisional units without controlling it."""
    objective_id = str(getattr(objective, "objective_id", ""))
    operator_wording = str(getattr(objective, "operator_wording", ""))
    episode_id = str(getattr(episode, "episode_id", ""))
    graph = _append(graph, "experiences", _experience(
        stable_id("semantic-experience", "operator", objective_id),
        "operator_statement",
        "operator_provided",
        operator_wording,
        (objective_id, episode_id),
        {"objective_id": objective_id},
    ))
    requests = {str(item.operation_id): item for item in getattr(episode, "operation_requests", ())}
    packets = {str(item.packet_id): item for item in getattr(episode, "working_memory_packets", ())}
    cycles = {str(item.operation_id): item for item in getattr(episode, "cycles", ())}
    semantic_refs: list[str] = []
    for result in getattr(episode, "operation_results", ()):
        operation_id = str(result.operation_id)
        request = requests.get(operation_id)
        cycle = cycles.get(operation_id)
        node_metadata = _node_metadata_for_request(cycle, packets, request)
        node_id = str(node_metadata.get("node_id") or getattr(request, "focus_id", ""))
        node_label = str(node_metadata.get("label") or node_id or "unscoped knowledge topic")
        output_experience = _experience(
            stable_id("semantic-experience", "local-model-output", operation_id),
            "local_model_output",
            "model_generated_provisional",
            str(result.raw_model_output or result.interpretation),
            tuple(item for item in (objective_id, episode_id, operation_id, node_id) if item),
            {
                "model_identity": str(result.model_identity),
                "accepted_locally": bool(result.accepted),
                "evaluation_state": str(getattr(result, "evaluation_state", "not_evaluated")),
                "rejection_reasons": list(getattr(result, "rejection_reasons", ())),
            },
        )
        graph = _append(graph, "experiences", output_experience)
        assumptions = tuple(str(item) for item in getattr(result, "assumptions", ()) if str(item))
        uncertainties = tuple(item for item in (str(getattr(result, "uncertainty", "")),) if item)
        assumption_refs = tuple(
            stable_id("semantic-experience", "assumption", operation_id, item)
            for item in assumptions
        )
        uncertainty_refs = tuple(
            stable_id("semantic-experience", "uncertainty", operation_id, item)
            for item in uncertainties
        )
        for item, item_id in zip(assumptions, assumption_refs):
            graph = _append(graph, "experiences", _experience(item_id, "runtime_observation", "nonclaim_assumption", item, (operation_id,), {"kind": "assumption"}))
        for item, item_id in zip(uncertainties, uncertainty_refs):
            graph = _append(graph, "experiences", _experience(item_id, "runtime_observation", "nonclaim_uncertainty", item, (operation_id,), {"kind": "uncertainty"}))
        local_disposition = _local_disposition(result)
        if bool(result.accepted):
            claim_id = stable_id("semantic-claim", objective_id, node_id, operation_id)
            version_id = stable_id("semantic-claim-version", claim_id, "1")
            rationale_id = stable_id("semantic-rationale", operation_id)
            graph = _append(graph, "claims", SemanticClaim(claim_id, objective_id, node_id, utc_now()))
            graph = _append(graph, "rationales", SemanticRationale(
                rationale_id=rationale_id,
                summary=str(result.interpretation),
                experience_refs=(output_experience.experience_id,),
                source_claim_refs=(),
                created_at=utc_now(),
                fingerprint=_semantic_fingerprint(str(result.interpretation)),
            ))
            version = ClaimVersion(
                claim_version_id=version_id,
                claim_id=claim_id,
                version_index=1,
                exact_text=str(result.interpretation),
                epistemic_state="pending_consolidation" if local_disposition == "locally_accepted" else local_disposition,
                rationale_refs=(rationale_id,),
                assumption_refs=assumption_refs,
                uncertainty_refs=uncertainty_refs,
                source_experience_refs=(output_experience.experience_id,),
                semantic_fingerprint=_semantic_fingerprint(str(result.interpretation)),
                created_at=utc_now(),
            )
            graph = _append(graph, "claim_versions", version)
            graph = _append(graph, "claim_fragments", ClaimFragment(
                fragment_id=stable_id("semantic-fragment", version_id, "1"),
                claim_version_id=version_id,
                exact_text=version.exact_text,
                ordinal=1,
            ))
            graph = _append(graph, "edges", _edge("derived_from", version_id, rationale_id))
            graph = _append(graph, "edges", _edge("grounded_in", rationale_id, output_experience.experience_id))
            concept_id = stable_id("semantic-concept", objective_id, node_id, node_label)
            graph = _append(graph, "concepts", SemanticConcept(
                concept_id=concept_id,
                label=node_label,
                created_at=utc_now(),
                provenance_refs=(output_experience.experience_id,),
            ))
            relation = SemanticRelation(
                relation_id=stable_id("semantic-relation", "claim_describes_concept", version_id, concept_id),
                relation_type="claim_describes_concept",
                source_ref=version_id,
                target_ref=concept_id,
                created_at=utc_now(),
                provenance_refs=(rationale_id, output_experience.experience_id),
            )
            graph = _append(graph, "relations", relation)
            graph = _append(graph, "edges", _edge("asserts_about", version_id, concept_id))
            duplicate = _first_duplicate_version(graph, version)
            if duplicate and duplicate.claim_version_id != version_id:
                graph = _append(graph, "edges", _edge("semantic_duplicate_of", version_id, duplicate.claim_version_id))
            semantic_refs.append(version_id)
        else:
            graph = _append(graph, "adaptation_traces", AdaptationTraceReference(
                trace_id=stable_id("adaptation-trace", operation_id, local_disposition),
                goal_id=objective_id,
                node_id=node_id,
                operation_id=operation_id,
                model_identity=str(result.model_identity),
                source_experience_ref=output_experience.experience_id,
                claim_version_id="",
                local_disposition=local_disposition,
                corrected_formulation="",
                created_at=utc_now(),
            ))
    trace = _episodic_trace(episode_id, objective_id, getattr(episode, "operation_results", ()), semantic_refs, terminal_status or str(getattr(episode, "loop_state", "")))
    graph = _append(graph, "episodic_traces", trace)
    return graph


def ingest_episode_at_runtime_root(runtime_root: str | Path, *, objective: Any, episode: Any, terminal_status: str = "") -> ProvisionalSemanticGraphState:
    graph = ingest_knowledge_episode(load_graph(runtime_root), objective=objective, episode=episode, terminal_status=terminal_status)
    save_graph(runtime_root, graph)
    trace = next(item for item in graph.episodic_traces if item.episode_id == str(getattr(episode, "episode_id", "")))
    _atomic_write_json(trace_path(runtime_root, trace.episode_id), _record(trace))
    return graph


def create_consolidation_cohort(
    graph: ProvisionalSemanticGraphState,
    *,
    trigger: str = "explicit_goal_closure",
    policy: Mapping[str, Any] | None = None,
) -> tuple[ProvisionalSemanticGraphState, ConsolidationCohort]:
    sealed_refs = _sealed_claim_version_refs(graph)
    eligible = tuple(
        item for item in graph.claim_versions
        if item.epistemic_state in {"provisional", "pending_consolidation", "uncertain", "insufficient_local_evidence", "locally_contradicted"}
        and item.claim_version_id not in sealed_refs
    )
    refs = tuple(sorted(item.claim_version_id for item in eligible))
    clusters = _dependency_clusters(graph, refs)
    duplicates = _duplicate_clusters(eligible)
    contradictions = tuple(
        trace.trace_id for trace in graph.adaptation_traces
        if trace.local_disposition == "locally_contradicted"
    )
    unresolved = tuple(item.claim_version_id for item in eligible if item.epistemic_state in {"uncertain", "insufficient_local_evidence"})
    base = {
        "trigger": trigger,
        "claim_version_refs": refs,
        "dependency_clusters": clusters,
        "contradiction_refs": contradictions,
        "duplicate_clusters": duplicates,
        "unresolved_claim_refs": unresolved,
        "policy": dict(policy or {"cadence": "cohort", "policy_version": POLICY_VERSION}),
    }
    cohort = ConsolidationCohort(
        cohort_id=stable_id("consolidation-cohort", _digest(base)),
        trigger=trigger,
        episode_refs=tuple(sorted({trace.episode_id for trace in graph.episodic_traces if set(trace.semantic_unit_refs) & set(refs)})),
        claim_version_refs=refs,
        dependency_clusters=clusters,
        contradiction_refs=contradictions,
        duplicate_clusters=duplicates,
        unresolved_claim_refs=unresolved,
        adaptation_trace_refs=tuple(sorted(trace.trace_id for trace in graph.adaptation_traces)),
        creation_policy=dict(base["policy"]),
        created_at=utc_now(),
        cohort_digest=_digest(base),
    )
    return _append(graph, "cohorts", cohort), cohort


def ensure_consolidation_cohort(
    graph: ProvisionalSemanticGraphState,
    *,
    trigger: str,
    policy: Mapping[str, Any] | None = None,
) -> tuple[ProvisionalSemanticGraphState, ConsolidationCohort | None]:
    """Register one cohort for unsealed material without creating a second owner.

    A cohort is only a durable cursor over already-canonical provisional claim
    versions.  Reusing an equivalent cursor makes idle ticks and restart safe.
    """

    candidate_graph, cohort = create_consolidation_cohort(graph, trigger=trigger, policy=policy)
    if not cohort.claim_version_refs:
        return graph, None
    existing = next(
        (
            item
            for item in graph.cohorts
            if item.claim_version_refs == cohort.claim_version_refs
            and item.trigger == cohort.trigger
        ),
        None,
    )
    if existing is not None:
        return graph, existing
    return candidate_graph, cohort


def compile_sealed_packet(
    graph: ProvisionalSemanticGraphState,
    cohort: ConsolidationCohort,
    *,
    privacy_metadata: Mapping[str, Any] | None = None,
    dependency_clusters: Sequence[Mapping[str, Any]] | None = None,
    chunk_ordinal: int = 1,
    chunk_count: int = 1,
) -> tuple[ProvisionalSemanticGraphState, SealedConsolidationPacket]:
    if chunk_ordinal < 1 or chunk_count < chunk_ordinal:
        raise ConsolidationIntegrityError("invalid_packet_chunk_position")
    versions = {item.claim_version_id: item for item in graph.claim_versions}
    rationales = {item.rationale_id: item for item in graph.rationales}
    experiences = {item.experience_id: item for item in graph.experiences}
    fragments = {item.claim_version_id: tuple(sorted((fragment for fragment in graph.claim_fragments if fragment.claim_version_id == item.claim_version_id), key=lambda item: item.ordinal)) for item in graph.claim_versions}
    clusters = []
    selected_clusters = tuple(dependency_clusters or cohort.dependency_clusters)
    allowed_refs = set(cohort.claim_version_refs)
    for cluster in selected_clusters:
        claim_refs = tuple(cluster.get("claim_version_refs") or ())
        if any(ref not in allowed_refs for ref in claim_refs):
            raise ConsolidationIntegrityError("packet_chunk_claim_outside_cohort")
        claims = []
        rationale_context: dict[str, Any] = {}
        evidence_context: dict[str, Any] = {}
        for ref in claim_refs:
            version = versions.get(ref)
            if not version:
                raise ConsolidationIntegrityError("cohort_references_unknown_claim_version:" + ref)
            claims.append({
                "claim_id": version.claim_id,
                "claim_version_id": version.claim_version_id,
                "claim_version": version.version_index,
                "exact_text": version.exact_text,
                "epistemic_status": version.epistemic_state,
                "rationale_refs": list(version.rationale_refs),
                "dependency_refs": list(_dependency_targets(graph, version.claim_version_id)),
                "fragment_ids": [fragment.fragment_id for fragment in fragments.get(ref, ())],
            })
            for rationale_id in version.rationale_refs:
                rationale = rationales.get(rationale_id)
                if rationale:
                    rationale_context[rationale_id] = {
                        "rationale_id": rationale.rationale_id,
                        "summary": rationale.summary[:600],
                        "experience_refs": list(rationale.experience_refs),
                    }
                    for experience_id in rationale.experience_refs:
                        experience = experiences.get(experience_id)
                        if experience:
                            evidence_context[experience_id] = {
                                "experience_id": experience.experience_id,
                                "source_class": experience.source_class,
                                "authority_class": experience.authority_class,
                "content_excerpt": experience.content[:800],
                "content_digest": experience.content_digest,
                "origin_refs": list(experience.origin_refs),
                "record_kind": str(experience.metadata.get("record_kind") or ""),
                "lineage": {
                    key: experience.metadata[key]
                    for key in (
                        "association_candidate_id", "approval_request_id", "ledger_request_id", "ledger_result_id",
                        "revises_insight_id", "review_id", "packet_id", "overlay_id",
                    )
                    if experience.metadata.get(key)
                },
            }
        clusters.append({
            "cluster_id": str(cluster["cluster_id"]),
            "requested_action": "validate_semantic_cluster",
            "claims": claims,
            "rationale_context": list(rationale_context.values()),
            "evidence_context": list(evidence_context.values()),
            "prior_review_summaries": [],
            "contradiction_refs": list(cohort.contradiction_refs),
        })
    packet_id = stable_id("consolidation-packet", cohort.cohort_id, str(chunk_ordinal), str(chunk_count))
    payload = {
        "packet_id": packet_id,
        "packet_version": 1,
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "cohort_id": cohort.cohort_id,
        "chunk": {"ordinal": chunk_ordinal, "count": chunk_count},
        "clusters": clusters,
        "privacy_admission": dict(privacy_metadata or {"external_review_admitted": False, "contains_credentials": False}),
    }
    digest = _digest(payload)
    sealed = SealedConsolidationPacket(packet_id, 1, cohort.cohort_id, digest, SCHEMA_VERSION, POLICY_VERSION, payload, utc_now(), dict(payload["privacy_admission"]))
    return _append(graph, "packets", sealed), sealed


def compile_sealed_packets(
    graph: ProvisionalSemanticGraphState,
    cohort: ConsolidationCohort,
    *,
    max_clusters_per_packet: int = 8,
    privacy_metadata: Mapping[str, Any] | None = None,
) -> tuple[ProvisionalSemanticGraphState, tuple[SealedConsolidationPacket, ...]]:
    """Create deterministic packet chunks without splitting dependency components."""
    if max_clusters_per_packet < 1:
        raise ConsolidationIntegrityError("max_clusters_per_packet_must_be_positive")
    clusters = tuple(sorted(cohort.dependency_clusters, key=lambda item: str(item.get("cluster_id") or "")))
    if not clusters:
        return graph, ()
    groups = tuple(
        clusters[index:index + max_clusters_per_packet]
        for index in range(0, len(clusters), max_clusters_per_packet)
    )
    packets: list[SealedConsolidationPacket] = []
    for ordinal, group in enumerate(groups, start=1):
        graph, packet = compile_sealed_packet(
            graph,
            cohort,
            privacy_metadata=privacy_metadata,
            dependency_clusters=group,
            chunk_ordinal=ordinal,
            chunk_count=len(groups),
        )
        packets.append(packet)
    return graph, tuple(packets)


def seal_cohort_packet_once(
    graph: ProvisionalSemanticGraphState,
    cohort: ConsolidationCohort,
) -> tuple[ProvisionalSemanticGraphState, SealedConsolidationPacket | None, str]:
    """Seal the first local packet for a cohort once; admission remains unavailable."""

    existing = next((item for item in graph.packets if item.cohort_id == cohort.cohort_id), None)
    if existing is not None:
        return graph, existing, "already_sealed"
    if not cohort.claim_version_refs or not cohort.dependency_clusters:
        return graph, None, "no_eligible_clusters"
    updated, packet = compile_sealed_packet(graph, cohort)
    return updated, packet, "sealed"


def verify_sealed_packet(packet: SealedConsolidationPacket) -> None:
    """Reject a packet whose content no longer matches its recorded seal."""
    payload = dict(packet.payload)
    if str(payload.get("packet_id") or "") != packet.packet_id:
        raise ConsolidationIntegrityError("sealed_packet_id_mismatch")
    if str(payload.get("schema_version") or "") != packet.schema_version:
        raise ConsolidationIntegrityError("sealed_packet_schema_version_mismatch")
    if str(payload.get("policy_version") or "") != packet.policy_version:
        raise ConsolidationIntegrityError("sealed_packet_policy_version_mismatch")
    if str(payload.get("cohort_id") or "") != packet.cohort_id:
        raise ConsolidationIntegrityError("sealed_packet_cohort_mismatch")
    if _digest(payload) != packet.packet_digest:
        raise ConsolidationIntegrityError("sealed_packet_digest_mismatch")


def validate_oracle_response(graph: ProvisionalSemanticGraphState, packet: SealedConsolidationPacket, response: Mapping[str, Any]) -> ReviewRecord:
    verify_sealed_packet(packet)
    if str(response.get("packet_id") or "") != packet.packet_id:
        raise ConsolidationIntegrityError("oracle_response_packet_id_mismatch")
    if str(response.get("reviewed_packet_digest") or "") != packet.packet_digest:
        raise ConsolidationIntegrityError("oracle_response_packet_digest_mismatch")
    if str(response.get("schema_version") or "") != packet.schema_version:
        raise ConsolidationIntegrityError("oracle_response_schema_version_mismatch")
    versions = {item.claim_version_id: item for item in graph.claim_versions}
    fragment_ids = {item.fragment_id: item for item in graph.claim_fragments}
    claim_reviews = tuple(response.get("claim_reviews") or ())
    seen: set[str] = set()
    normalized: list[Mapping[str, Any]] = []
    for item in claim_reviews:
        if not isinstance(item, Mapping):
            raise ConsolidationIntegrityError("oracle_response_claim_review_not_mapping")
        version_id = str(item.get("claim_version_id") or "")
        verdict = str(item.get("verdict") or "")
        if version_id not in versions:
            raise ConsolidationIntegrityError("oracle_response_unknown_claim_version:" + version_id)
        if version_id in seen:
            raise ConsolidationIntegrityError("oracle_response_duplicate_claim_review:" + version_id)
        seen.add(version_id)
        if verdict not in ORACLE_VERDICTS:
            raise ConsolidationIntegrityError("oracle_response_invalid_verdict:" + verdict)
        fragment_refs = tuple(str(value) for value in item.get("reviewed_fragment_ids", ()) if str(value))
        if any(ref not in fragment_ids or fragment_ids[ref].claim_version_id != version_id for ref in fragment_refs):
            raise ConsolidationIntegrityError("oracle_response_invalid_fragment_reference")
        correction = str(item.get("proposed_correction") or "")
        if verdict == "requires_revision" and not correction:
            raise ConsolidationIntegrityError("oracle_response_revision_missing_correction")
        confidence = float(item.get("confidence") or 0.0)
        if not 0.0 <= confidence <= 1.0:
            raise ConsolidationIntegrityError("oracle_response_confidence_out_of_range")
        if verdict == "validated" and confidence < 0.5:
            raise ConsolidationIntegrityError("oracle_response_impossible_validated_confidence")
        normalized.append({
            "claim_version_id": version_id,
            "verdict": verdict,
            "reviewed_fragment_ids": fragment_refs,
            "proposed_correction": correction,
            "confidence": confidence,
            "rationale_code": str(item.get("rationale_code") or ""),
            "evidence_refs": tuple(str(value) for value in item.get("evidence_refs", ()) if str(value)),
            "dependency_impact": tuple(str(value) for value in item.get("dependency_impact", ()) if str(value)),
        })
    return ReviewRecord(
        review_id=str(response.get("review_id") or stable_id("oracle-review", packet.packet_id, packet.packet_digest, _digest(normalized))),
        packet_id=packet.packet_id,
        packet_digest=packet.packet_digest,
        oracle_metadata=dict(response.get("oracle_metadata") or {}),
        claim_reviews=tuple(normalized),
        reviewed_at=str(response.get("reviewed_at") or utc_now()),
    )


def record_validated_oracle_response(graph: ProvisionalSemanticGraphState, packet: SealedConsolidationPacket, response: Mapping[str, Any]) -> tuple[ProvisionalSemanticGraphState, ReviewRecord]:
    review = validate_oracle_response(graph, packet, response)
    return _append(graph, "reviews", review), review


def create_administrative_overlay(
    graph: ProvisionalSemanticGraphState,
    *,
    review_id: str,
    claim_version_id: str,
    action: str,
    role: str,
    operator_id: str,
    replacement_text: str = "",
    selected_fragment_ids: Sequence[str] = (),
) -> tuple[ProvisionalSemanticGraphState, AdministrativeReviewOverlay]:
    if role != "administrative_operator":
        raise ConsolidationIntegrityError("administrative_role_required")
    if action not in ADMINISTRATIVE_ACTIONS:
        raise ConsolidationIntegrityError("unsupported_administrative_action:" + action)
    if review_id not in {item.review_id for item in graph.reviews}:
        raise ConsolidationIntegrityError("unknown_review_id")
    if claim_version_id not in {item.claim_version_id for item in graph.claim_versions}:
        raise ConsolidationIntegrityError("unknown_claim_version_id")
    overlay = AdministrativeReviewOverlay(
        overlay_id=stable_id("administrative-overlay", review_id, claim_version_id, action, operator_id, replacement_text, tuple(selected_fragment_ids)),
        review_id=review_id,
        claim_version_id=claim_version_id,
        action=action,
        role=role,
        operator_id=operator_id,
        replacement_text=replacement_text,
        selected_fragment_ids=tuple(selected_fragment_ids),
        created_at=utc_now(),
    )
    return _append(graph, "overlays", overlay), overlay


def apply_admission(graph: ProvisionalSemanticGraphState, *, review_id: str, overlay_id: str) -> tuple[ProvisionalSemanticGraphState, AdmissionRecord]:
    review = _by_id(graph.reviews, review_id, "review_id")
    overlay = _by_id(graph.overlays, overlay_id, "overlay_id")
    if overlay.review_id != review.review_id:
        raise ConsolidationIntegrityError("overlay_review_binding_mismatch")
    existing_admission = next(
        (
            item
            for item in graph.admissions
            if item.review_id == review.review_id and item.overlay_id == overlay.overlay_id
        ),
        None,
    )
    if existing_admission is not None:
        return graph, existing_admission
    review_item = next((item for item in review.claim_reviews if str(item.get("claim_version_id")) == overlay.claim_version_id), None)
    if review_item is None:
        raise ConsolidationIntegrityError("overlay_claim_not_reviewed")
    action = _admission_action(str(review_item["verdict"]), overlay.action)
    if action not in ADMISSION_ACTIONS:
        raise ConsolidationIntegrityError("unsupported_admission_action")
    version = _by_id(graph.claim_versions, overlay.claim_version_id, "claim_version_id")
    result_version_id = version.claim_version_id
    if action in {"promote", "retain_provisional", "quarantine", "invalidate", "escalate_operator"}:
        state = {
            "promote": "validated",
            "retain_provisional": "pending_consolidation",
            "quarantine": "quarantined",
            "invalidate": "invalidated",
            "escalate_operator": "escalated_operator",
        }[action]
        graph, result_version_id = _version_with_state(graph, version, state, review)
    elif action == "promote_partial":
        selected = tuple(overlay.selected_fragment_ids or tuple(review_item.get("reviewed_fragment_ids") or ()))
        graph, result_version_id = _promote_partial(graph, version, selected, review)
    elif action == "revise":
        correction = overlay.replacement_text or str(review_item.get("proposed_correction") or "")
        if not correction:
            raise ConsolidationIntegrityError("revision_requires_bound_correction")
        graph, result_version_id = _revise_claim(graph, version, correction, review)
    admission = AdmissionRecord(
        admission_id=stable_id("admission", review.review_id, overlay.overlay_id, action, result_version_id),
        review_id=review.review_id,
        overlay_id=overlay.overlay_id,
        claim_version_id=version.claim_version_id,
        action=action,
        resulting_claim_version_id=result_version_id,
        created_at=utc_now(),
    )
    graph = _append(graph, "admissions", admission)
    if action in {"quarantine", "invalidate", "revise"}:
        graph = _append(graph, "adaptation_traces", AdaptationTraceReference(
            trace_id=stable_id("adaptation-trace", version.claim_version_id, review.review_id, action),
            goal_id=_by_id(graph.claims, version.claim_id, "claim_id").originating_goal_id,
            node_id=_by_id(graph.claims, version.claim_id, "claim_id").originating_node_id,
            operation_id="",
            model_identity="",
            source_experience_ref=version.source_experience_refs[0] if version.source_experience_refs else "",
            claim_version_id=version.claim_version_id,
            local_disposition=version.epistemic_state,
            review_id=review.review_id,
            administrative_disposition=action,
            corrected_formulation=str(review_item.get("proposed_correction") or overlay.replacement_text),
            propagation_refs=tuple(_affected_dependents(graph, version.claim_version_id)),
            created_at=utc_now(),
        ))
    return graph, admission


def render_administrative_review(graph: ProvisionalSemanticGraphState, review_id: str) -> dict[str, Any]:
    review = _by_id(graph.reviews, review_id, "review_id")
    versions = {item.claim_version_id: item for item in graph.claim_versions}
    claims = []
    for item in review.claim_reviews:
        version = versions[str(item["claim_version_id"])]
        claims.append({
            "claim_version_id": version.claim_version_id,
            "exact_text": version.exact_text,
            "epistemic_state": version.epistemic_state,
            "verdict": item["verdict"],
            "proposed_correction": item["proposed_correction"],
            "reviewed_fragment_ids": list(item["reviewed_fragment_ids"]),
            "rationale_refs": list(version.rationale_refs),
            "source_experience_refs": list(version.source_experience_refs),
            "available_actions": sorted(ADMINISTRATIVE_ACTIONS),
        })
    return {
        "review_id": review.review_id,
        "packet_id": review.packet_id,
        "packet_digest": review.packet_digest,
        "oracle_metadata": dict(review.oracle_metadata),
        "claims": claims,
        "role_required": "administrative_operator",
    }


def _experience(experience_id: str, source_class: str, authority_class: str, content: str, origin_refs: Sequence[str], metadata: Mapping[str, Any]) -> SemanticExperience:
    if source_class not in SOURCE_CLASSES:
        raise ConsolidationIntegrityError("unknown_source_class:" + source_class)
    return SemanticExperience(experience_id, source_class, authority_class, content, tuple(origin_refs), utc_now(), _digest({"content": content}), dict(metadata))


def _local_disposition(result: Any) -> str:
    evaluation = str(getattr(result, "evaluation_state", "not_evaluated"))
    if evaluation == "contradicted":
        return "locally_contradicted"
    if evaluation == "insufficient_evidence":
        return "insufficient_local_evidence"
    if bool(getattr(result, "accepted", False)):
        return "locally_accepted"
    return "uncertain"


def _node_metadata_for_request(cycle: Any, packets: Mapping[str, Any], request: Any) -> Mapping[str, Any]:
    if cycle is None:
        return {"node_id": str(getattr(request, "focus_id", "")), "label": str(getattr(request, "focus_id", ""))}
    packet = next((item for item in packets.values() if str(getattr(item, "packet_digest", "")) == str(getattr(cycle, "packet_digest", ""))), None)
    node = dict(getattr(packet, "active_focus", {}).get("active_frontier_node") or {}) if packet else {}
    if not node:
        node = {"node_id": str(getattr(request, "focus_id", "")), "label": str(getattr(request, "focus_id", ""))}
    return node


def _node_id_for_request(cycle: Any, packets: Mapping[str, Any], request: Any) -> str:
    return str(_node_metadata_for_request(cycle, packets, request).get("node_id") or "")


def _episodic_trace(episode_id: str, objective_id: str, results: Iterable[Any], refs: Sequence[str], terminal_status: str) -> EpisodicTrace:
    operation_ids = tuple(str(item.operation_id) for item in results)
    base = {"episode_id": episode_id, "objective_id": objective_id, "operation_ids": operation_ids, "semantic_unit_refs": tuple(refs), "terminal_status": terminal_status}
    return EpisodicTrace(stable_id("episodic-trace", _digest(base)), episode_id, objective_id, operation_ids, tuple(refs), terminal_status, utc_now(), _digest(base))


def _append(graph: ProvisionalSemanticGraphState, field_name: str, item: Any) -> ProvisionalSemanticGraphState:
    values = tuple(getattr(graph, field_name))
    identity = _identity(item)
    existing = next((candidate for candidate in values if _identity(candidate) == identity), None)
    if existing is not None:
        if not _same_immutable_record(existing, item):
            raise ConsolidationIntegrityError("immutable_record_conflict:" + identity)
        return graph
    return replace(graph, **{field_name: values + (item,)})


def _same_immutable_record(left: Any, right: Any) -> bool:
    """Ignore creation bookkeeping when replaying the exact source artifact."""
    ignored = {"created_at", "sealed_at", "reviewed_at", "validation_timestamp"}
    left_record = {key: value for key, value in _record(left).items() if key not in ignored}
    right_record = {key: value for key, value in _record(right).items() if key not in ignored}
    return left_record == right_record


def _identity(item: Any) -> str:
    # Wrapper records carry claim/review references too. Their own durable ID must
    # win so replay never confuses an admission or overlay with its subject.
    for key in ("admission_id", "overlay_id", "trace_id", "review_id", "packet_id", "cohort_id", "experience_id", "rationale_id", "fragment_id", "relation_id", "concept_id", "edge_id", "claim_version_id", "claim_id"):
        value = getattr(item, key, "")
        if value:
            return str(value)
    raise ConsolidationIntegrityError("record_identity_missing")


def _edge(edge_type: str, source_ref: str, target_ref: str) -> SemanticEdge:
    return SemanticEdge(stable_id("semantic-edge", edge_type, source_ref, target_ref), edge_type, source_ref, target_ref, utc_now())


def _first_duplicate_version(graph: ProvisionalSemanticGraphState, version: ClaimVersion) -> ClaimVersion | None:
    return next((item for item in graph.claim_versions if item.semantic_fingerprint == version.semantic_fingerprint), None)


def _dependency_targets(graph: ProvisionalSemanticGraphState, version_id: str) -> tuple[str, ...]:
    return tuple(sorted(edge.target_ref for edge in graph.edges if edge.edge_type == "depends_on" and edge.source_ref == version_id))


def _sealed_claim_version_refs(graph: ProvisionalSemanticGraphState) -> set[str]:
    """Return exact claim versions already represented by an immutable packet."""

    refs: set[str] = set()
    for packet in graph.packets:
        for cluster in packet.payload.get("clusters", ()):
            if not isinstance(cluster, Mapping):
                continue
            for claim in cluster.get("claims", ()):
                if isinstance(claim, Mapping) and claim.get("claim_version_id"):
                    refs.add(str(claim["claim_version_id"]))
    return refs


def _dependency_clusters(graph: ProvisionalSemanticGraphState, refs: Sequence[str]) -> tuple[Mapping[str, Any], ...]:
    remaining = set(refs)
    adjacency: dict[str, set[str]] = {ref: set() for ref in refs}
    for edge in graph.edges:
        if edge.edge_type != "depends_on":
            continue
        if edge.source_ref in adjacency and edge.target_ref in adjacency:
            adjacency[edge.source_ref].add(edge.target_ref)
            adjacency[edge.target_ref].add(edge.source_ref)
    clusters = []
    while remaining:
        seed = min(remaining)
        component = {seed}
        frontier = [seed]
        while frontier:
            current = frontier.pop()
            for candidate in adjacency[current]:
                if candidate not in component:
                    component.add(candidate)
                    frontier.append(candidate)
        remaining -= component
        members = tuple(sorted(component))
        clusters.append({"cluster_id": stable_id("dependency-cluster", members), "claim_version_refs": members})
    return tuple(clusters)


def _duplicate_clusters(versions: Sequence[ClaimVersion]) -> tuple[Mapping[str, Any], ...]:
    grouped: dict[str, list[str]] = {}
    for version in versions:
        grouped.setdefault(version.semantic_fingerprint, []).append(version.claim_version_id)
    return tuple(
        {"cluster_id": stable_id("duplicate-cluster", fingerprint), "claim_version_refs": tuple(sorted(refs))}
        for fingerprint, refs in sorted(grouped.items()) if len(refs) > 1
    )


def _by_id(items: Sequence[Any], identifier: str, attribute: str) -> Any:
    found = next((item for item in items if str(getattr(item, attribute)) == identifier), None)
    if found is None:
        raise ConsolidationIntegrityError("unknown_" + attribute + ":" + identifier)
    return found


def _admission_action(verdict: str, overlay_action: str) -> str:
    if overlay_action == "approve" and verdict == "validated":
        return "promote"
    if overlay_action == "reject" and verdict == "contradicted":
        return "quarantine"
    if overlay_action == "reject" and verdict == "invalid":
        return "invalidate"
    if overlay_action == "approve_partial" and verdict == "partially_valid":
        return "promote_partial"
    if overlay_action in {"revise_claim", "replace_fragment"} and verdict in {"requires_revision", "partially_valid"}:
        return "revise"
    if overlay_action in {"split_claim", "merge_claims", "recompose_cluster"} and verdict in {"validated", "partially_valid", "requires_revision"}:
        return "revise"
    if overlay_action == "retain_provisional" and verdict == "unsupported":
        return "retain_provisional"
    if overlay_action == "quarantine" and verdict == "contradicted":
        return "quarantine"
    if overlay_action == "invalidate" and verdict == "invalid":
        return "invalidate"
    if overlay_action == "escalate_for_more_evidence":
        return "escalate_operator"
    if overlay_action == "request_re_review":
        return "escalate_operator"
    raise ConsolidationIntegrityError("administrative_action_not_compatible_with_oracle_verdict")


def _version_with_state(graph: ProvisionalSemanticGraphState, version: ClaimVersion, state: str, review: ReviewRecord) -> tuple[ProvisionalSemanticGraphState, str]:
    return _new_version(graph, version, version.exact_text, state, review)


def _promote_partial(graph: ProvisionalSemanticGraphState, version: ClaimVersion, fragment_ids: Sequence[str], review: ReviewRecord) -> tuple[ProvisionalSemanticGraphState, str]:
    fragments = {item.fragment_id: item for item in graph.claim_fragments}
    selected = tuple(fragments[item] for item in fragment_ids if item in fragments and fragments[item].claim_version_id == version.claim_version_id)
    if not selected or len(selected) != len(tuple(fragment_ids)):
        raise ConsolidationIntegrityError("partial_promotion_requires_bound_fragments")
    text = " ".join(item.exact_text for item in sorted(selected, key=lambda item: item.ordinal))
    return _new_version(graph, version, text, "partially_valid", review)


def _revise_claim(graph: ProvisionalSemanticGraphState, version: ClaimVersion, correction: str, review: ReviewRecord) -> tuple[ProvisionalSemanticGraphState, str]:
    graph, version_id = _new_version(graph, version, correction, "requires_revision", review)
    for dependent in _affected_dependents(graph, version.claim_version_id):
        dependent_version = _by_id(graph.claim_versions, dependent, "claim_version_id")
        if dependent_version.epistemic_state == "validated":
            graph, _ = _new_version(graph, dependent_version, dependent_version.exact_text, "pending_operator_consolidation_review", review)
    return graph, version_id


def _new_version(graph: ProvisionalSemanticGraphState, previous: ClaimVersion, text: str, state: str, review: ReviewRecord) -> tuple[ProvisionalSemanticGraphState, str]:
    prior_versions = [item for item in graph.claim_versions if item.claim_id == previous.claim_id]
    version_index = max(item.version_index for item in prior_versions) + 1
    version_id = stable_id("semantic-claim-version", previous.claim_id, str(version_index), text, state, review.review_id)
    new_version = replace(
        previous,
        claim_version_id=version_id,
        version_index=version_index,
        exact_text=text,
        epistemic_state=state,
        semantic_fingerprint=_semantic_fingerprint(text),
        created_at=utc_now(),
        supersedes_version_id=previous.claim_version_id,
        validated_under_review_id=review.review_id if state in {"validated", "partially_valid"} else "",
        validated_against_packet_digest=review.packet_digest if state in {"validated", "partially_valid"} else "",
        validation_scope="oracle_review_plus_administrative_overlay" if state in {"validated", "partially_valid"} else "",
        validation_policy_version=POLICY_VERSION if state in {"validated", "partially_valid"} else "",
        validation_timestamp=utc_now() if state in {"validated", "partially_valid"} else "",
    )
    graph = _append(graph, "claim_versions", new_version)
    graph = _append(graph, "claim_fragments", ClaimFragment(stable_id("semantic-fragment", version_id, "1"), version_id, text, 1))
    graph = _append(graph, "edges", _edge("supersedes", version_id, previous.claim_version_id))
    for dependency_ref in _dependency_targets(graph, previous.claim_version_id):
        graph = _append(graph, "edges", _edge("depends_on", version_id, dependency_ref))
    return graph, version_id


def _affected_dependents(graph: ProvisionalSemanticGraphState, version_id: str) -> tuple[str, ...]:
    affected: set[str] = set()
    frontier = [version_id]
    while frontier:
        target = frontier.pop()
        for edge in graph.edges:
            if edge.edge_type == "depends_on" and edge.target_ref == target and edge.source_ref not in affected:
                affected.add(edge.source_ref)
                frontier.append(edge.source_ref)
    return tuple(sorted(affected))


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _experience_from_record(value: Mapping[str, Any]) -> SemanticExperience:
    return SemanticExperience(str(value["experience_id"]), str(value["source_class"]), str(value["authority_class"]), str(value["content"]), tuple(value.get("origin_refs") or ()), str(value["created_at"]), str(value["content_digest"]), dict(value.get("metadata") or {}), str(value.get("schema_version") or SCHEMA_VERSION))


def _rationale_from_record(value: Mapping[str, Any]) -> SemanticRationale:
    return SemanticRationale(str(value["rationale_id"]), str(value["summary"]), tuple(value.get("experience_refs") or ()), tuple(value.get("source_claim_refs") or ()), str(value["created_at"]), str(value["fingerprint"]), str(value.get("schema_version") or SCHEMA_VERSION))


def _claim_from_record(value: Mapping[str, Any]) -> SemanticClaim:
    return SemanticClaim(str(value["claim_id"]), str(value["originating_goal_id"]), str(value.get("originating_node_id") or ""), str(value["created_at"]), bool(value.get("protected_memory", False)), str(value.get("schema_version") or SCHEMA_VERSION))


def _fragment_from_record(value: Mapping[str, Any]) -> ClaimFragment:
    return ClaimFragment(str(value["fragment_id"]), str(value["claim_version_id"]), str(value["exact_text"]), int(value["ordinal"]), str(value.get("schema_version") or SCHEMA_VERSION))


def _claim_version_from_record(value: Mapping[str, Any]) -> ClaimVersion:
    return ClaimVersion(str(value["claim_version_id"]), str(value["claim_id"]), int(value["version_index"]), str(value["exact_text"]), str(value["epistemic_state"]), tuple(value.get("rationale_refs") or ()), tuple(value.get("assumption_refs") or ()), tuple(value.get("uncertainty_refs") or ()), tuple(value.get("source_experience_refs") or ()), str(value["semantic_fingerprint"]), str(value["created_at"]), str(value.get("supersedes_version_id") or ""), str(value.get("validated_under_review_id") or ""), str(value.get("validated_against_packet_digest") or ""), str(value.get("validation_scope") or ""), str(value.get("validation_policy_version") or ""), str(value.get("validation_timestamp") or ""), str(value.get("schema_version") or SCHEMA_VERSION))


def _relation_from_record(value: Mapping[str, Any]) -> SemanticRelation:
    return SemanticRelation(str(value["relation_id"]), str(value["relation_type"]), str(value["source_ref"]), str(value["target_ref"]), str(value["created_at"]), tuple(value.get("provenance_refs") or ()), str(value.get("schema_version") or SCHEMA_VERSION), dict(value.get("metadata") or {}))


def _concept_from_record(value: Mapping[str, Any]) -> SemanticConcept:
    return SemanticConcept(str(value["concept_id"]), str(value["label"]), str(value["created_at"]), tuple(value.get("provenance_refs") or ()), str(value.get("schema_version") or SCHEMA_VERSION))


def _edge_from_record(value: Mapping[str, Any]) -> SemanticEdge:
    return SemanticEdge(str(value["edge_id"]), str(value["edge_type"]), str(value["source_ref"]), str(value["target_ref"]), str(value["created_at"]), dict(value.get("metadata") or {}), str(value.get("schema_version") or SCHEMA_VERSION))


def _review_from_record(value: Mapping[str, Any]) -> ReviewRecord:
    return ReviewRecord(str(value["review_id"]), str(value["packet_id"]), str(value["packet_digest"]), dict(value.get("oracle_metadata") or {}), tuple(dict(item) for item in value.get("claim_reviews", ()) if isinstance(item, Mapping)), str(value["reviewed_at"]), str(value.get("schema_version") or SCHEMA_VERSION))


def _overlay_from_record(value: Mapping[str, Any]) -> AdministrativeReviewOverlay:
    return AdministrativeReviewOverlay(str(value["overlay_id"]), str(value["review_id"]), str(value["claim_version_id"]), str(value["action"]), str(value["role"]), str(value["operator_id"]), str(value.get("replacement_text") or ""), tuple(value.get("selected_fragment_ids") or ()), str(value.get("created_at") or ""), str(value.get("schema_version") or SCHEMA_VERSION))


def _admission_from_record(value: Mapping[str, Any]) -> AdmissionRecord:
    return AdmissionRecord(str(value["admission_id"]), str(value["review_id"]), str(value["overlay_id"]), str(value["claim_version_id"]), str(value["action"]), str(value["resulting_claim_version_id"]), str(value["created_at"]), str(value.get("schema_version") or SCHEMA_VERSION))


def _adaptation_from_record(value: Mapping[str, Any]) -> AdaptationTraceReference:
    return AdaptationTraceReference(str(value["trace_id"]), str(value["goal_id"]), str(value.get("node_id") or ""), str(value.get("operation_id") or ""), str(value.get("model_identity") or ""), str(value.get("source_experience_ref") or ""), str(value.get("claim_version_id") or ""), str(value["local_disposition"]), str(value.get("review_id") or ""), str(value.get("administrative_disposition") or ""), str(value.get("corrected_formulation") or ""), tuple(value.get("propagation_refs") or ()), str(value.get("created_at") or ""), str(value.get("schema_version") or SCHEMA_VERSION))


def _trace_from_record(value: Mapping[str, Any]) -> EpisodicTrace:
    return EpisodicTrace(str(value["trace_id"]), str(value["episode_id"]), str(value["objective_id"]), tuple(value.get("operation_ids") or ()), tuple(value.get("semantic_unit_refs") or ()), str(value["terminal_status"]), str(value["sealed_at"]), str(value["digest"]), str(value.get("schema_version") or SCHEMA_VERSION))


def _cohort_from_record(value: Mapping[str, Any]) -> ConsolidationCohort:
    return ConsolidationCohort(str(value["cohort_id"]), str(value["trigger"]), tuple(value.get("episode_refs") or ()), tuple(value.get("claim_version_refs") or ()), tuple(dict(item) for item in value.get("dependency_clusters", ()) if isinstance(item, Mapping)), tuple(value.get("contradiction_refs") or ()), tuple(dict(item) for item in value.get("duplicate_clusters", ()) if isinstance(item, Mapping)), tuple(value.get("unresolved_claim_refs") or ()), tuple(value.get("adaptation_trace_refs") or ()), dict(value.get("creation_policy") or {}), str(value["created_at"]), str(value["cohort_digest"]), str(value.get("schema_version") or SCHEMA_VERSION))


def _packet_from_record(value: Mapping[str, Any]) -> SealedConsolidationPacket:
    return SealedConsolidationPacket(str(value["packet_id"]), int(value["packet_version"]), str(value["cohort_id"]), str(value["packet_digest"]), str(value["schema_version"]), str(value["policy_version"]), dict(value.get("payload") or {}), str(value["created_at"]), dict(value.get("privacy_metadata") or {}))


__all__ = [
    "ADMINISTRATIVE_ACTIONS", "ADMISSION_ACTIONS", "FUNCTIONAL_RELATION_TYPES", "ClaimFragment", "ClaimVersion", "ConsolidationCohort", "ConsolidationIntegrityError", "EpisodicTrace", "ProvisionalSemanticGraphState", "ReviewRecord", "SemanticClaim", "SemanticConcept", "SemanticEdge", "SemanticExperience", "SemanticRationale", "SemanticRelation", "SealedConsolidationPacket", "AdaptationTraceReference", "AdministrativeReviewOverlay", "AdmissionRecord", "apply_admission", "compile_sealed_packet", "compile_sealed_packets", "create_administrative_overlay", "create_consolidation_cohort", "empty_graph", "ensure_consolidation_cohort", "graph_from_record", "ingest_episode_at_runtime_root", "ingest_knowledge_episode", "load_graph", "record_associative_insight", "record_provisional_functional_relation", "record_revised_associative_insight", "record_validated_oracle_response", "render_administrative_review", "save_graph", "seal_cohort_packet_once", "validate_oracle_response", "verify_sealed_packet",
]
