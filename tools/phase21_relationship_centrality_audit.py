from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge import PredictionEngine, SemanticKnowledgeStore
from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from tools.promotion_governance import run_promotion_governance


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", str(text).lower()))


def _overlap_score(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))


def _relationships_touching(relationships: list[Any], ids: set[str]) -> list[Any]:
    return [
        relationship
        for relationship in relationships
        if relationship.source_id in ids or relationship.target_id in ids
    ]


def _learning_sources(record: Any, learning_records: list[Any]) -> list[dict[str, Any]]:
    supporting = set(record.supporting_evidence)
    matches = []
    for learning in learning_records:
        cycle_match = record.metadata.get("cycle_id") and learning.cycle_id == record.metadata.get("cycle_id")
        best_candidate = None
        best_score = 0.0
        for candidate in learning.semantic_candidates:
            candidate_text = str(getattr(candidate, "text", ""))
            evidence_ids = set(getattr(candidate, "evidence_memory_ids", []))
            evidence_match = bool(supporting & evidence_ids)
            score = max(
                _overlap_score(record.concept, candidate_text),
                _overlap_score(record.definition, candidate_text),
            )
            if evidence_match:
                score += 0.25
            if score > best_score:
                best_score = score
                best_candidate = candidate_text
        if cycle_match or best_score >= 0.32:
            matches.append(
                {
                    "learning_id": learning.learning_id,
                    "cycle_id": learning.cycle_id,
                    "match_score": round(best_score, 4),
                    "candidate_text": best_candidate,
                }
            )
    return sorted(matches, key=lambda item: -item["match_score"])[:5]


def _shared_evidence_neighbors(record: Any, concepts: list[Any]) -> list[dict[str, Any]]:
    supporting = set(record.supporting_evidence)
    neighbors = []
    if not supporting:
        return neighbors
    for other in concepts:
        if other.concept_id == record.concept_id:
            continue
        shared = sorted(supporting & set(other.supporting_evidence))
        if shared:
            neighbors.append(
                {
                    "concept_id": other.concept_id,
                    "concept": other.concept,
                    "shared_evidence_count": len(shared),
                    "shared_evidence_ids": shared[:5],
                }
            )
    return sorted(neighbors, key=lambda item: -item["shared_evidence_count"])[:10]


def audit_relationship_centrality(
    *,
    store_root: Path,
    reports_dir: Path,
    sample_size: int = 50,
) -> dict[str, Any]:
    memory = MemoryStore(store_root / "memory.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    learning = LearningStore(store_root / "learning.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")

    concepts = knowledge.latest()
    all_relationships = relationships.latest()
    memory_ids = {item.memory_id for item in memory.all()}
    concept_ids = {record.concept_id for record in concepts}
    relationship_endpoint_counts = {
        "total_relationships": len(all_relationships),
        "memory_to_memory": 0,
        "concept_to_concept": 0,
        "concept_to_memory": 0,
        "other": 0,
    }
    for relationship in all_relationships:
        source_is_memory = relationship.source_id in memory_ids
        target_is_memory = relationship.target_id in memory_ids
        source_is_concept = relationship.source_id in concept_ids
        target_is_concept = relationship.target_id in concept_ids
        if source_is_memory and target_is_memory:
            relationship_endpoint_counts["memory_to_memory"] += 1
        elif source_is_concept and target_is_concept:
            relationship_endpoint_counts["concept_to_concept"] += 1
        elif (source_is_concept and target_is_memory) or (source_is_memory and target_is_concept):
            relationship_endpoint_counts["concept_to_memory"] += 1
        else:
            relationship_endpoint_counts["other"] += 1

    governance = run_promotion_governance(store_root=store_root, reports_dir=reports_dir)
    governance_by_id = {item["concept_id"]: item for item in governance["decisions"]}
    predictions_by_concept: Counter[str] = Counter()
    for prediction in predictions.latest():
        predictions_by_concept[prediction.source_concept_id] += 1

    selected = sorted(
        concepts,
        key=lambda record: governance_by_id.get(record.concept_id, {}).get("promotion_score", 0.0),
        reverse=True,
    )[: max(1, int(sample_size))]
    concept_reports = []
    projected_counts = []
    direct_counts = []
    for record in selected:
        supporting_ids = set(record.supporting_evidence)
        direct_edges = _relationships_touching(all_relationships, {record.concept_id})
        evidence_edges = _relationships_touching(all_relationships, supporting_ids)
        relationship_types = Counter(edge.relationship_type for edge in evidence_edges)
        projected_neighbors = sorted(
            {
                edge.target_id if edge.source_id in supporting_ids else edge.source_id
                for edge in evidence_edges
            }
        )
        shared_neighbors = _shared_evidence_neighbors(record, concepts)
        governance_record = governance_by_id.get(record.concept_id, {})
        direct_count = len(direct_edges)
        projected_count = len(evidence_edges)
        direct_counts.append(direct_count)
        projected_counts.append(projected_count)
        concept_reports.append(
            {
                "concept_id": record.concept_id,
                "concept": record.concept,
                "promotion_score": governance_record.get("promotion_score", 0.0),
                "recommendation": governance_record.get("recommendation", "unknown"),
                "governance_relationship_centrality": governance_record.get("evidence", {}).get("relationship_centrality", 0),
                "direct_semantic_relationship_edges": direct_count,
                "supporting_memory_ids": sorted(supporting_ids),
                "supporting_memory_relationship_edges": projected_count,
                "projected_unique_neighbor_memory_count": len(projected_neighbors),
                "projected_relationship_types": dict(relationship_types.most_common()),
                "prediction_count": predictions_by_concept.get(record.concept_id, 0),
                "learning_sources": _learning_sources(record, learning.all()),
                "shared_evidence_concept_neighbors": shared_neighbors,
                "diagnosis": (
                    "memory_graph_not_projected"
                    if direct_count == 0 and projected_count > 0
                    else "direct_semantic_edges_exist"
                    if direct_count > 0
                    else "no_relationship_evidence"
                ),
            }
        )

    diagnosis_counts = Counter(item["diagnosis"] for item in concept_reports)
    concepts_with_direct = sum(1 for count in direct_counts if count > 0)
    concepts_with_projected = sum(1 for count in projected_counts if count > 0)
    summary = {
        "store_root": str(store_root),
        "concepts_total": len(concepts),
        "concepts_sampled": len(concept_reports),
        "relationship_endpoint_counts": relationship_endpoint_counts,
        "concepts_with_direct_semantic_edges": concepts_with_direct,
        "concepts_with_projected_memory_edges": concepts_with_projected,
        "average_direct_semantic_edges": round(sum(direct_counts) / max(1, len(direct_counts)), 4),
        "average_projected_memory_edges": round(sum(projected_counts) / max(1, len(projected_counts)), 4),
        "diagnosis_counts": dict(diagnosis_counts),
        "hypothesis": (
            "relationships_exist_at_memory_layer_but_are_not_projected_to_semantic_layer"
            if concepts_with_projected > concepts_with_direct
            else "semantic_relationships_absent_or_measurement_inconclusive"
        ),
        "concepts": concept_reports,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase21_relationship_centrality_audit.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_report(summary, reports_dir)
    return summary


def _write_report(summary: dict[str, Any], reports_dir: Path) -> None:
    examples = summary["concepts"][:20]
    lines = [
        "# Phase 21 Relationship Centrality Audit",
        "",
        "Read-only diagnostic pass. No learning, validation, promotion, or store mutation was performed.",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Concepts total | {summary['concepts_total']} |",
        f"| Concepts sampled | {summary['concepts_sampled']} |",
        f"| Total relationships | {summary['relationship_endpoint_counts']['total_relationships']} |",
        f"| Memory-to-memory relationships | {summary['relationship_endpoint_counts']['memory_to_memory']} |",
        f"| Concept-to-concept relationships | {summary['relationship_endpoint_counts']['concept_to_concept']} |",
        f"| Concept-to-memory relationships | {summary['relationship_endpoint_counts']['concept_to_memory']} |",
        f"| Concepts with direct semantic edges | {summary['concepts_with_direct_semantic_edges']} |",
        f"| Concepts with projected memory edges | {summary['concepts_with_projected_memory_edges']} |",
        f"| Avg direct semantic edges | {summary['average_direct_semantic_edges']} |",
        f"| Avg projected memory edges | {summary['average_projected_memory_edges']} |",
        "",
        "## Diagnosis",
        "",
        f"`{summary['hypothesis']}`",
        "",
        "## Diagnosis Counts",
        "",
        *[f"- `{key}`: `{value}`" for key, value in summary["diagnosis_counts"].items()],
        "",
        "## Sampled Concepts",
        "",
    ]
    for item in examples:
        lines.extend(
            [
                f"### {item['concept']}",
                "",
                f"- concept_id: `{item['concept_id']}`",
                f"- recommendation: `{item['recommendation']}`",
                f"- promotion_score: `{item['promotion_score']}`",
                f"- governance_relationship_centrality: `{item['governance_relationship_centrality']}`",
                f"- direct_semantic_relationship_edges: `{item['direct_semantic_relationship_edges']}`",
                f"- supporting_memory_relationship_edges: `{item['supporting_memory_relationship_edges']}`",
                f"- projected_relationship_types: `{item['projected_relationship_types']}`",
                f"- prediction_count: `{item['prediction_count']}`",
                f"- diagnosis: `{item['diagnosis']}`",
                "",
            ]
        )
    (reports_dir / "phase21_relationship_centrality_audit.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit semantic centrality against memory-layer relationships.")
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--sample-size", type=int, default=50)
    args = parser.parse_args()
    summary = audit_relationship_centrality(
        store_root=Path(args.store_root),
        reports_dir=Path(args.reports_dir),
        sample_size=args.sample_size,
    )
    print(
        json.dumps(
            {
                "concepts_sampled": summary["concepts_sampled"],
                "hypothesis": summary["hypothesis"],
                "concepts_with_direct_semantic_edges": summary["concepts_with_direct_semantic_edges"],
                "concepts_with_projected_memory_edges": summary["concepts_with_projected_memory_edges"],
                "diagnosis_counts": summary["diagnosis_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
