from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge import ContradictionEngine, PredictionEngine, SemanticKnowledgeStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from tools.phase16_validation import (
    _concept_reuse,
    _cross_profile_recurrence,
    _prompt_specificity,
    _redundancy_scores,
    _relationship_centrality,
)
from tools.phase18_semantic_normalization import _cycle_provenance


DEFAULT_WEIGHTS = {
    "evidence_support": 0.16,
    "prediction_validation": 0.22,
    "confidence": 0.14,
    "confidence_gain": 0.08,
    "semantic_reuse": 0.12,
    "cross_profile_recurrence": 0.10,
    "relationship_centrality": 0.10,
    "normalization_success": 0.08,
    "failed_validation_penalty": 0.24,
    "contradiction_penalty": 0.22,
    "redundancy_penalty": 0.14,
    "prompt_artifact_penalty": 0.16,
    "unresolved_prediction_penalty": 0.14,
}


@dataclass(frozen=True)
class GovernanceDecision:
    concept_id: str
    concept: str
    lifecycle_state: str
    promotion_score: float
    recommendation: str
    confidence: float
    confidence_trajectory: list[float]
    dimensions: dict[str, float]
    evidence: dict[str, Any]
    provenance: dict[str, Any]
    rationale: list[str]


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _load_weights(path: Path | None) -> dict[str, float]:
    weights = dict(DEFAULT_WEIGHTS)
    if path is None:
        return weights
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key, value in payload.items():
        if key in weights:
            weights[key] = float(value)
    return weights


def _lineages(knowledge: SemanticKnowledgeStore) -> dict[str, set[str]]:
    return {
        record.concept_id: set([record.concept_id, *record.revision_history])
        for record in knowledge.latest()
    }


def _status_counts_by_concept(
    predictions: PredictionEngine,
    lineages: dict[str, set[str]],
) -> dict[str, Counter[str]]:
    lineage_owner = {
        prior_id: concept_id
        for concept_id, ids in lineages.items()
        for prior_id in ids
    }
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for prediction in predictions.latest():
        owner = lineage_owner.get(prediction.source_concept_id)
        if owner is None:
            continue
        counts[owner][prediction.status] += 1
    return counts


def _contradictions_by_concept(
    contradictions: ContradictionEngine,
    lineages: dict[str, set[str]],
) -> tuple[dict[str, Counter[str]], dict[str, int]]:
    lineage_owner = {
        prior_id: concept_id
        for concept_id, ids in lineages.items()
        for prior_id in ids
    }
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    open_counts: Counter[str] = Counter()
    for contradiction in contradictions.latest():
        owners = {
            lineage_owner.get(contradiction.claim_a_id),
            lineage_owner.get(contradiction.claim_b_id),
        }
        for owner in owners:
            if owner is None:
                continue
            counts[owner][contradiction.status] += 1
            if contradiction.status == "open":
                open_counts[owner] += 1
    return counts, dict(open_counts)


def _confidence_trajectory(record: Any, all_by_id: dict[str, Any]) -> list[float]:
    history = [
        float(all_by_id[prior_id].confidence)
        for prior_id in record.revision_history
        if prior_id in all_by_id
    ]
    history.append(float(record.confidence))
    return [round(value, 4) for value in history]


def _provenance_for(record: Any, cycle_provenance: dict[str, dict[str, Any]]) -> dict[str, Any]:
    normalization = {}
    if isinstance(record.metadata.get("phase18_normalization"), dict):
        normalization = dict(record.metadata["phase18_normalization"])
    cycle_id = str(record.metadata.get("cycle_id") or normalization.get("cycle_id") or "").strip()
    cycle = cycle_provenance.get(cycle_id, {})
    return {
        "creation_source": record.creation_source,
        "cycle_id": cycle_id or "unknown",
        "source_provider": normalization.get("source_provider")
        or record.metadata.get("source_provider")
        or cycle.get("source_provider")
        or "unknown",
        "source_experiment": normalization.get("source_experiment")
        or record.metadata.get("source_experiment")
        or cycle.get("source_experiment")
        or "unknown",
        "source_profile": normalization.get("source_profile")
        or record.metadata.get("source_profile")
        or cycle.get("source_profile")
        or "unknown",
        "objective_tag": normalization.get("objective_tag")
        or record.metadata.get("objective_tag")
        or cycle.get("objective_tag")
        or "unknown",
        "normalization": normalization,
    }


def _recommendation(score: float, *, supported: int, failed: int, unresolved: int, open_contradictions: int) -> str:
    if failed > 0 or open_contradictions > 0 or score < 0.2:
        return "Reject"
    if unresolved > 0:
        return "Hold for More Validation"
    if score >= 0.74 and supported > 0:
        return "Promotion Eligible"
    if score >= 0.56 and supported > 0:
        return "Validated"
    if score >= 0.38:
        return "Candidate"
    return "Experimental"


def _governance_recommendation(
    *,
    score: float,
    supported: int,
    failed: int,
    unresolved: int,
    open_contradictions: int,
    evidence_support: float,
    redundancy: float,
    prompt_specificity: float,
    incomplete_proposition: bool,
) -> str:
    if failed > 0 or open_contradictions > 0 or score < 0.2:
        return "Reject"
    if unresolved > 0:
        return "Hold for More Validation"
    if incomplete_proposition or prompt_specificity >= 0.16:
        return "Candidate" if score >= 0.38 else "Experimental"
    if (
        supported > 0
        and score >= 0.62
        and evidence_support >= 0.75
        and redundancy <= 0.22
        and prompt_specificity < 0.16
        and not incomplete_proposition
    ):
        return "Promotion Eligible"
    if score >= 0.56 and supported > 0:
        return "Validated"
    if score >= 0.38:
        return "Candidate"
    return "Experimental"


def _incomplete_proposition(concept: str, definition: str) -> bool:
    text = " ".join(str(concept or definition).strip().lower().split())
    words = text.split()
    if len(words) < 4:
        return True
    if text.startswith(("for instance if ", "for example if ")):
        return True
    if text.startswith(("if ", "when ")) and "," not in text and " then " not in text:
        return True
    process_fragments = (
        "the cycle can be completed by predicting that",
        "by doing so we can predict",
        "the failure mode could be a situation where",
    )
    if any(fragment in text for fragment in process_fragments):
        return True
    fragment_endings = (
        "could include",
        "would include",
        "may include",
        "could require",
        "would require",
        "may require",
        "can require",
        "is that",
        "is the",
        "are the",
        "includes",
        "include",
        "requires",
        "require",
        "would",
        "could",
        "may",
        "should",
        "must",
        "will",
        "can",
        "was",
        "were",
        "be",
        "been",
        "being",
        "based",
        "forecasted",
        "significant",
        "the",
        "a",
        "an",
        "to",
        "of",
        "for",
    )
    return text.endswith(fragment_endings)


def _relationships_touching(relationships: list[Any], ids: set[str]) -> list[Any]:
    return [
        relationship
        for relationship in relationships
        if relationship.source_id in ids or relationship.target_id in ids
    ]


def _shared_evidence_neighbor_count(record: Any, records: list[Any]) -> int:
    supporting = set(record.supporting_evidence)
    if not supporting:
        return 0
    return sum(
        1
        for other in records
        if other.concept_id != record.concept_id
        and bool(supporting & set(other.supporting_evidence))
    )


def _projected_centrality(
    *,
    record: Any,
    records: list[Any],
    relationships: list[Any],
    direct_relationship_count: int,
    total_predictions: int,
) -> dict[str, Any]:
    supporting_ids = set(record.supporting_evidence)
    evidence_edges = _relationships_touching(relationships, supporting_ids)
    relationship_types = {edge.relationship_type for edge in evidence_edges}
    projected_neighbors = {
        edge.target_id if edge.source_id in supporting_ids else edge.source_id
        for edge in evidence_edges
    }
    shared_neighbors = _shared_evidence_neighbor_count(record, records)
    direct_score = min(1.0, direct_relationship_count / 8)
    evidence_edge_score = min(1.0, len(evidence_edges) / 4)
    shared_evidence_score = min(1.0, shared_neighbors / 4)
    diversity_score = min(1.0, len(relationship_types) / 3)
    prediction_link_score = min(1.0, total_predictions / 3)
    evidence_count_score = min(1.0, len(supporting_ids) / 3)
    projected = max(
        direct_score,
        (direct_score * 0.10)
        + (evidence_edge_score * 0.32)
        + (shared_evidence_score * 0.22)
        + (diversity_score * 0.14)
        + (prediction_link_score * 0.12)
        + (evidence_count_score * 0.10),
    )
    sources = []
    if direct_relationship_count:
        sources.append("direct_semantic_edges")
    if evidence_edges:
        sources.append("supporting_evidence_memory_relationships")
    if shared_neighbors:
        sources.append("shared_supporting_evidence")
    if total_predictions:
        sources.append("prediction_links")
    if supporting_ids:
        sources.append("supporting_evidence_count")
    if relationship_types:
        sources.append("relationship_type_diversity")
    return {
        "projected_centrality": round(min(1.0, projected), 4),
        "projected_neighbor_count": len(projected_neighbors) + shared_neighbors,
        "projected_relationship_diversity": len(relationship_types),
        "projection_sources": sources,
        "supporting_memory_relationship_edges": len(evidence_edges),
        "shared_evidence_neighbor_concepts": shared_neighbors,
        "direct_semantic_relationship_edges": direct_relationship_count,
        "raw_centrality": round(direct_score, 4),
        "why_projected_centrality_changed": (
            "supporting evidence memories participate in relationships"
            if evidence_edges and direct_relationship_count == 0
            else "shared supporting evidence links concepts"
            if shared_neighbors and direct_relationship_count == 0
            else "direct semantic centrality already visible"
            if direct_relationship_count
            else "no projection evidence found"
        ),
    }


def _lifecycle_state(recommendation: str) -> str:
    if recommendation == "Reject":
        return "Reject"
    if recommendation == "Promotion Eligible":
        return "Promotion Eligible"
    if recommendation == "Validated":
        return "Validated"
    if recommendation == "Hold for More Validation":
        return "Hold for More Validation"
    if recommendation == "Candidate":
        return "Candidate"
    return "Experimental"


def run_promotion_governance(
    *,
    store_root: Path,
    reports_dir: Path,
    weights_path: Path | None = None,
    use_projection: bool = False,
) -> dict[str, Any]:
    memory = MemoryStore(store_root / "memory.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    contradictions = ContradictionEngine(store_root / "contradictions.jsonl")

    weights = _load_weights(weights_path)
    latest_records = knowledge.latest()
    all_by_id = {record.concept_id: record for record in knowledge.all()}
    lineages = _lineages(knowledge)
    prediction_counts = _status_counts_by_concept(predictions, lineages)
    contradiction_counts, open_contradictions = _contradictions_by_concept(
        contradictions,
        lineages,
    )
    redundancy = _redundancy_scores(latest_records)
    centrality = _relationship_centrality(relationships)
    all_relationships = relationships.latest()
    phrase_profiles = _cross_profile_recurrence(memory)
    cycle_provenance = _cycle_provenance(memory)

    decisions = []
    for record in latest_records:
        statuses = prediction_counts.get(record.concept_id, Counter())
        supported = statuses.get("supported", 0) + statuses.get("succeeded", 0)
        failed = statuses.get("failed", 0)
        unresolved = statuses.get("open", 0) + statuses.get("inconclusive", 0)
        total_predictions = supported + failed + unresolved
        open_contradiction_count = open_contradictions.get(record.concept_id, 0)
        contradiction_total = sum(contradiction_counts.get(record.concept_id, Counter()).values())
        specificity = _prompt_specificity(record.concept, record.definition)
        incomplete = _incomplete_proposition(record.concept, record.definition)
        redundant = redundancy.get(record.concept_id, 0.0)
        reuse = _concept_reuse(record, phrase_profiles)
        direct_relationship_count = centrality.get(record.concept_id, 0)
        projection = _projected_centrality(
            record=record,
            records=latest_records,
            relationships=all_relationships,
            direct_relationship_count=direct_relationship_count,
            total_predictions=total_predictions,
        )
        raw_relation_score = projection["raw_centrality"]
        relation_score = (
            projection["projected_centrality"] if use_projection else raw_relation_score
        )
        trajectory = _confidence_trajectory(record, all_by_id)
        confidence_gain = max(0.0, trajectory[-1] - trajectory[0]) if trajectory else 0.0
        evidence_support = min(
            1.0,
            (len(record.supporting_evidence) / 4)
            + (supported / max(1, total_predictions)) * 0.5,
        )
        prediction_validation = (
            supported / max(1, supported + failed + unresolved)
            if total_predictions
            else 0.0
        )
        cross_profile = reuse
        normalization = record.metadata.get("phase18_normalization")
        normalization_success = 0.5
        if isinstance(normalization, dict):
            normalization_success = 1.0 if supported else 0.25
        recovered_after_normalization = bool(isinstance(normalization, dict) and supported > 0)
        effective_failed = max(0, failed - 1) if recovered_after_normalization else failed
        dimensions = {
            "evidence_support": round(evidence_support, 4),
            "prediction_validation": round(prediction_validation, 4),
            "confidence": round(float(record.confidence), 4),
            "confidence_gain": round(confidence_gain, 4),
            "semantic_reuse": reuse,
            "cross_profile_recurrence": cross_profile,
            "relationship_centrality": round(relation_score, 4),
            "raw_relationship_centrality": round(raw_relation_score, 4),
            "projected_centrality": projection["projected_centrality"],
            "projected_neighbor_count": float(projection["projected_neighbor_count"]),
            "projected_relationship_diversity": float(projection["projected_relationship_diversity"]),
            "normalization_success": round(normalization_success, 4),
            "failed_validation_penalty": round(
                min(
                    1.0,
                    (effective_failed / max(1, total_predictions))
                    + ((failed - effective_failed) * 0.08),
                ),
                4,
            ),
            "contradiction_penalty": round(min(1.0, open_contradiction_count * 0.25), 4),
            "redundancy_penalty": redundant,
            "prompt_artifact_penalty": specificity,
            "incomplete_proposition": 1.0 if incomplete else 0.0,
            "unresolved_prediction_penalty": round(min(1.0, unresolved * 0.1), 4),
        }
        score = (
            dimensions["evidence_support"] * weights["evidence_support"]
            + dimensions["prediction_validation"] * weights["prediction_validation"]
            + dimensions["confidence"] * weights["confidence"]
            + dimensions["confidence_gain"] * weights["confidence_gain"]
            + dimensions["semantic_reuse"] * weights["semantic_reuse"]
            + dimensions["cross_profile_recurrence"] * weights["cross_profile_recurrence"]
            + dimensions["relationship_centrality"] * weights["relationship_centrality"]
            + dimensions["normalization_success"] * weights["normalization_success"]
            - dimensions["failed_validation_penalty"] * weights["failed_validation_penalty"]
            - dimensions["contradiction_penalty"] * weights["contradiction_penalty"]
            - dimensions["redundancy_penalty"] * weights["redundancy_penalty"]
            - dimensions["prompt_artifact_penalty"] * weights["prompt_artifact_penalty"]
            - dimensions["unresolved_prediction_penalty"] * weights["unresolved_prediction_penalty"]
        )
        score = round(max(0.0, min(1.0, score)), 4)
        recommendation = _governance_recommendation(
            score=score,
            supported=supported,
            failed=effective_failed,
            unresolved=unresolved,
            open_contradictions=open_contradiction_count,
            evidence_support=dimensions["evidence_support"],
            redundancy=dimensions["redundancy_penalty"],
            prompt_specificity=dimensions["prompt_artifact_penalty"],
            incomplete_proposition=incomplete,
        )
        rationale = [
            f"supported_predictions={supported}",
            f"failed_predictions={failed}",
            f"effective_failed_predictions={effective_failed}",
            f"unresolved_predictions={unresolved}",
            f"open_contradictions={open_contradiction_count}",
            f"redundancy={redundant}",
            f"prompt_specificity={specificity}",
            f"incomplete_proposition={incomplete}",
        ]
        if isinstance(normalization, dict):
            rationale.append("phase18_normalized=true")
        decisions.append(
            GovernanceDecision(
                concept_id=record.concept_id,
                concept=record.concept,
                lifecycle_state=_lifecycle_state(recommendation),
                promotion_score=score,
                recommendation=recommendation,
                confidence=round(float(record.confidence), 4),
                confidence_trajectory=trajectory,
                dimensions=dimensions,
                evidence={
                    "supported_predictions": supported,
                    "failed_predictions": failed,
                    "effective_failed_predictions": effective_failed,
                    "unresolved_predictions": unresolved,
                    "prediction_statuses": dict(statuses),
                    "contradictions": dict(contradiction_counts.get(record.concept_id, Counter())),
                    "open_contradictions": open_contradiction_count,
                    "relationship_centrality": direct_relationship_count,
                    "raw_centrality": projection["raw_centrality"],
                    "projected_centrality": projection["projected_centrality"],
                    "projected_neighbor_count": projection["projected_neighbor_count"],
                    "projected_relationship_diversity": projection["projected_relationship_diversity"],
                    "projection_sources": projection["projection_sources"],
                    "supporting_memory_relationship_edges": projection["supporting_memory_relationship_edges"],
                    "shared_evidence_neighbor_concepts": projection["shared_evidence_neighbor_concepts"],
                    "why_projected_centrality_changed": projection["why_projected_centrality_changed"],
                    "supporting_evidence_count": len(record.supporting_evidence),
                    "contradicting_evidence_count": len(record.contradicting_evidence),
                    "revision_count": len(record.revision_history),
                    "contradiction_total": contradiction_total,
                    "incomplete_proposition": incomplete,
                },
                provenance=_provenance_for(record, cycle_provenance),
                rationale=rationale,
            )
        )

    decisions = sorted(decisions, key=lambda item: (-item.promotion_score, item.concept))
    state_counts = Counter(item.recommendation for item in decisions)
    summary = {
        "run_id": f"promotion_governance_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "store_root": str(store_root),
        "canonical_merge_performed": False,
        "virtual_projection_enabled": bool(use_projection),
        "concepts_evaluated": len(decisions),
        "weights": weights,
        "recommendation_counts": dict(state_counts),
        "promotion_eligible_count": state_counts.get("Promotion Eligible", 0),
        "validated_count": state_counts.get("Validated", 0),
        "rejected_count": state_counts.get("Reject", 0),
        "hold_count": state_counts.get("Hold for More Validation", 0),
        "average_promotion_score": round(
            sum(item.promotion_score for item in decisions) / max(1, len(decisions)),
            4,
        ),
        "decisions": [_jsonable(item) for item in decisions],
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "promotion_governance_report.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_reports(summary, reports_dir)
    return summary


def _write_reports(summary: dict[str, Any], reports_dir: Path) -> None:
    decisions = summary["decisions"]
    candidates = [
        item
        for item in decisions
        if item["recommendation"] in {"Promotion Eligible", "Validated"}
    ]
    rejections = [item for item in decisions if item["recommendation"] == "Reject"]
    holds = [item for item in decisions if item["recommendation"] == "Hold for More Validation"]
    (reports_dir / "promotion_governance_report.md").write_text(
        "\n".join(
            [
                "# Promotion Governance Report",
                "",
                "Promotion governance evaluated isolated experiment knowledge only.",
                "No canonical merge was performed.",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Concepts evaluated | {summary['concepts_evaluated']} |",
                f"| Promotion eligible | {summary['promotion_eligible_count']} |",
                f"| Validated | {summary['validated_count']} |",
                f"| Hold for more validation | {summary['hold_count']} |",
                f"| Rejected | {summary['rejected_count']} |",
                f"| Average promotion score | {summary['average_promotion_score']} |",
                f"| Virtual projection enabled | {str(summary['virtual_projection_enabled']).lower()} |",
                "",
                "## Recommendation Counts",
                "",
                *[
                    f"- `{key}`: `{value}`"
                    for key, value in sorted(summary["recommendation_counts"].items())
                ],
                "",
                "## Interpretation",
                "",
                "Promotion governance is a scoring and recommendation layer. It protects "
                "canonical knowledge by requiring evidence support, validation history, "
                "low contradiction pressure, low prompt specificity, and manageable "
                "redundancy before a concept is marked promotion eligible.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "promotion_candidates.md").write_text(
        "\n".join(
            [
                "# Promotion Candidates",
                "",
                *[
                    (
                        f"- `{item['concept']}` | `{item['recommendation']}` | "
                        f"score `{item['promotion_score']}` | provider "
                        f"`{item['provenance']['source_provider']}` | profile "
                        f"`{item['provenance']['source_profile']}`"
                    )
                    for item in candidates[:100]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "promotion_rejections.md").write_text(
        "\n".join(
            [
                "# Promotion Rejections",
                "",
                *[
                    (
                        f"- `{item['concept']}` | score `{item['promotion_score']}` | "
                        f"failed `{item['evidence']['failed_predictions']}` | "
                        f"open contradictions `{item['evidence']['open_contradictions']}` | "
                        f"redundancy `{item['dimensions']['redundancy_penalty']}`"
                    )
                    for item in rejections[:150]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "concept_lifecycle_report.md").write_text(
        "\n".join(
            [
                "# Concept Lifecycle Report",
                "",
                "| State | Count |",
                "| --- | ---: |",
                *[
                    f"| {key} | {value} |"
                    for key, value in sorted(summary["recommendation_counts"].items())
                ],
                "",
                "## Hold For More Validation",
                "",
                *[
                    f"- `{item['concept']}` | score `{item['promotion_score']}` | unresolved `{item['evidence']['unresolved_predictions']}`"
                    for item in holds[:100]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Score isolated knowledge for promotion governance.")
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--weights")
    parser.add_argument("--use-projection", action="store_true")
    args = parser.parse_args()
    summary = run_promotion_governance(
        store_root=Path(args.store_root),
        reports_dir=Path(args.reports_dir),
        weights_path=Path(args.weights) if args.weights else None,
        use_projection=args.use_projection,
    )
    print(
        json.dumps(
            {
                "run_id": summary["run_id"],
                "concepts_evaluated": summary["concepts_evaluated"],
                "recommendation_counts": summary["recommendation_counts"],
                "average_promotion_score": summary["average_promotion_score"],
                "canonical_merge_performed": summary["canonical_merge_performed"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
