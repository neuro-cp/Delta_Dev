"""Conservative, read-only structural analogy candidates over functional relations."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

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
    lifecycle_state: str = "provisional_question_candidate"


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
        ))
    return tuple(sorted(candidates, key=lambda item: item.candidate_id))


__all__ = ["StructuralAnalogyCandidate", "derive_structural_analogies"]
