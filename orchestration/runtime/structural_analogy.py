"""Conservative, read-only structural patterns and analogy candidates.

The canonical provisional graph remains the semantic owner.  This module only
projects functional structure from graph-owned relations and never admits an
analogy as a fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Mapping

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.provisional_semantic_consolidation import SemanticRelation


@dataclass(frozen=True)
class StructuralAnalogyCandidate:
    candidate_id: str
    source_relation_ids: tuple[str, ...]
    target_relation_ids: tuple[str, ...]
    matched_relation_types: tuple[str, ...]
    unmatched_source_types: tuple[str, ...]
    unmatched_target_types: tuple[str, ...]
    implication: str
    limitation: str
    uncertainty: str
    state: str = "generated"
    source_cluster_id: str = ""
    target_cluster_id: str = ""
    source_pattern_id: str = ""
    target_pattern_id: str = ""
    source_unit_ids: tuple[str, ...] = ()
    target_unit_ids: tuple[str, ...] = ()
    expected_information_gain: int = 0
    operator_relevance: int = 0
    possible_next_question: str = ""
    provenance_refs: tuple[str, ...] = ()

    @property
    def lifecycle_state(self) -> str:
        """Compatibility label for callers that read the earlier scaffold."""
        return self.state


@dataclass(frozen=True)
class StructuralPattern:
    """A derived view over graph-owned functional relations, never a truth store."""

    pattern_id: str
    cluster_id: str
    semantic_unit_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    relation_types: tuple[str, ...]
    ordered_relation_types: tuple[str, ...]
    required_roles: tuple[str, ...]
    optional_roles: tuple[str, ...]
    threshold_or_capacity_roles: tuple[str, ...]
    causal_direction: str
    state_transitions: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    epistemic_state: str = "pending_consolidation"
    confidence: float = 0.0
    revision_lineage: tuple[str, ...] = ()


def project_structural_patterns(relations: Iterable[SemanticRelation]) -> tuple[StructuralPattern, ...]:
    """Project relation-connected components into bounded functional patterns."""

    usable = tuple(
        item for item in relations
        if item.metadata.get("epistemic_state") in {"pending_consolidation", "provisional", "uncertain"}
        and item.metadata.get("invalidation_state", "active") == "active"
        and item.provenance_refs
    )
    remaining = {item.relation_id: item for item in usable}
    patterns: list[StructuralPattern] = []
    while remaining:
        seed_id = sorted(remaining)[0]
        component = [remaining.pop(seed_id)]
        seen_refs = {component[0].source_ref, component[0].target_ref}
        changed = True
        while changed:
            changed = False
            for relation_id, relation in list(remaining.items()):
                if relation.source_ref in seen_refs or relation.target_ref in seen_refs:
                    component.append(remaining.pop(relation_id))
                    seen_refs.update((relation.source_ref, relation.target_ref))
                    changed = True
        ordered = tuple(sorted(component, key=lambda item: item.relation_id))
        relation_types = tuple(item.relation_type for item in ordered)
        relation_ids = tuple(item.relation_id for item in ordered)
        cluster_id = stable_id("functional-pattern-cluster", *sorted(seen_refs))
        patterns.append(StructuralPattern(
            pattern_id=stable_id("structural-pattern", cluster_id, *relation_ids),
            cluster_id=cluster_id,
            semantic_unit_ids=tuple(sorted(seen_refs)),
            relation_ids=relation_ids,
            relation_types=tuple(sorted(set(relation_types))),
            ordered_relation_types=relation_types,
            required_roles=tuple(sorted(set(relation_types))),
            optional_roles=(),
            threshold_or_capacity_roles=tuple(sorted(set(relation_types) & {"limited_by_capacity", "activates_at_threshold"})),
            causal_direction="source_to_target",
            state_transitions=tuple(item.relation_type for item in ordered if item.relation_type in {"activates_at_threshold", "discharges_through", "recovers_after_release", "degrades_under_load"}),
            provenance_refs=tuple(sorted({ref for item in ordered for ref in item.provenance_refs})),
            confidence=min(float(item.metadata.get("confidence") or 0.0) for item in ordered),
            revision_lineage=tuple(sorted({str(item.metadata.get("revision_of_relation_id") or "") for item in ordered if item.metadata.get("revision_of_relation_id")})),
        ))
    return tuple(sorted(patterns, key=lambda item: item.pattern_id))


def derive_structural_analogies(clusters: tuple[tuple[SemanticRelation, ...], ...]) -> tuple[StructuralAnalogyCandidate, ...]:
    """Return candidates only where two relation clusters share real structure."""

    candidates: list[StructuralAnalogyCandidate] = []
    for source, target in combinations(clusters, 2):
        source_types = {item.relation_type for item in source}
        target_types = {item.relation_type for item in target}
        matched = tuple(sorted(source_types & target_types))
        if len(matched) < 2:
            continue
        source_ids = tuple(sorted(item.relation_id for item in source))
        target_ids = tuple(sorted(item.relation_id for item in target))
        source_pattern = project_structural_patterns(source)
        target_pattern = project_structural_patterns(target)
        if len(source_pattern) != 1 or len(target_pattern) != 1:
            continue
        # At least two matching relations plus a sequence/dependency prevents
        # lexical or one-edge coincidence from appearing as an analogy.
        has_structure = any(item.relation_type in {"collects_from", "transfers_through", "accumulates_in", "limited_by_capacity", "activates_at_threshold", "discharges_through", "regulates"} for item in source + target)
        if not has_structure:
            continue
        source_view, target_view = source_pattern[0], target_pattern[0]
        candidates.append(StructuralAnalogyCandidate(
            candidate_id=stable_id("structural-analogy", *source_ids, *target_ids),
            source_relation_ids=source_ids,
            target_relation_ids=target_ids,
            matched_relation_types=matched,
            unmatched_source_types=tuple(sorted(source_types - target_types)),
            unmatched_target_types=tuple(sorted(target_types - source_types)),
            implication="The clusters share a functional pattern worth a bounded comparison.",
            limitation="Matching relations do not establish equivalent causes, scale, mechanism, or factual truth.",
            uncertainty="Both relation clusters remain provisional unless independently reviewed.",
            source_cluster_id=source_view.cluster_id,
            target_cluster_id=target_view.cluster_id,
            source_pattern_id=source_view.pattern_id,
            target_pattern_id=target_view.pattern_id,
            source_unit_ids=source_view.semantic_unit_ids,
            target_unit_ids=target_view.semantic_unit_ids,
            expected_information_gain=2,
            operator_relevance=1,
            possible_next_question="Should DELTA compare this shared functional pattern while retaining its limits?",
            provenance_refs=tuple(sorted(set(source_view.provenance_refs + target_view.provenance_refs))),
        ))
    return tuple(sorted(candidates, key=lambda item: item.candidate_id))


def derive_structural_analogies_from_graph(relations: Iterable[SemanticRelation]) -> tuple[StructuralAnalogyCandidate, ...]:
    """Convenience read adapter for the canonical graph relation collection."""

    return derive_structural_analogies(_relation_components(relations))


def describe_structural_analogy_candidate(
    candidate: StructuralAnalogyCandidate,
    *,
    record_labels: Mapping[str, str],
) -> str:
    """Render an operator-readable view without changing candidate authority."""

    def labels(record_ids: tuple[str, ...]) -> str:
        return "; ".join(record_labels.get(item, item) for item in record_ids) or "No source records available"

    return (
        "Cross-domain pattern:\n"
        f"Source domain: {labels(candidate.source_unit_ids)}\n"
        f"Target domain: {labels(candidate.target_unit_ids)}\n"
        f"Matched functional relations: {', '.join(candidate.matched_relation_types)}\n"
        f"Why DELTA surfaced it: {candidate.implication}\n"
        f"Where it may fail: {candidate.limitation}\n"
        f"Uncertainty: {candidate.uncertainty}\n"
        f"Bounded exploration question: {candidate.possible_next_question}"
    )


def _relation_components(relations: Iterable[SemanticRelation]) -> tuple[tuple[SemanticRelation, ...], ...]:
    materialized = tuple(relations)
    patterns = project_structural_patterns(materialized)
    by_id = {item.relation_id: item for item in materialized}
    return tuple(tuple(by_id[relation_id] for relation_id in pattern.relation_ids) for pattern in patterns)


__all__ = ["StructuralAnalogyCandidate", "StructuralPattern", "derive_structural_analogies", "derive_structural_analogies_from_graph", "describe_structural_analogy_candidate", "project_structural_patterns"]
