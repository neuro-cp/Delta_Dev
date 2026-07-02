from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge import PredictionEngine, SemanticKnowledgeStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from tools.phase16_validation import _content_tokens
from tools.promotion_governance import _incomplete_proposition


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _governance_metrics(reports_dir: Path) -> dict[str, Any]:
    governance = _load_json(reports_dir / "promotion_governance_report.json")
    decisions = list(governance.get("decisions", []))
    learned_decisions = [
        item
        for item in decisions
        if not str(item.get("provenance", {}).get("creation_source", "")).startswith("bootstrap:")
    ]

    def _rate_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
        prompt_artifacts = [
            item
            for item in items
            if float(item.get("dimensions", {}).get("prompt_artifact_penalty", 0.0)) >= 0.16
        ]
        incomplete = [
            item
            for item in items
            if bool(item.get("evidence", {}).get("incomplete_proposition"))
            or bool(item.get("dimensions", {}).get("incomplete_proposition"))
        ]
        redundancies = [
            float(item.get("dimensions", {}).get("redundancy_penalty", 0.0))
            for item in items
        ]
        scores = [float(item.get("promotion_score", 0.0)) for item in items]
        return {
            "concepts": len(items),
            "recommendation_counts": dict(Counter(item.get("recommendation", "unknown") for item in items)),
            "average_promotion_score": round(sum(scores) / max(1, len(scores)), 4),
            "score_min": round(min(scores), 4) if scores else 0.0,
            "score_max": round(max(scores), 4) if scores else 0.0,
            "score_ge_056": sum(1 for score in scores if score >= 0.56),
            "score_ge_062": sum(1 for score in scores if score >= 0.62),
            "prompt_artifact_count": len(prompt_artifacts),
            "prompt_artifact_rate": round(len(prompt_artifacts) / max(1, len(items)), 4),
            "incomplete_count": len(incomplete),
            "incomplete_rate": round(len(incomplete) / max(1, len(items)), 4),
            "average_redundancy": round(sum(redundancies) / max(1, len(redundancies)), 4),
        }

    all_metrics = _rate_metrics(decisions)
    learned_metrics = _rate_metrics(learned_decisions)
    prompt_artifacts = [
        item
        for item in decisions
        if float(item.get("dimensions", {}).get("prompt_artifact_penalty", 0.0)) >= 0.16
    ]
    incomplete = [
        item
        for item in decisions
        if bool(item.get("evidence", {}).get("incomplete_proposition"))
        or bool(item.get("dimensions", {}).get("incomplete_proposition"))
    ]
    redundancies = [
        float(item.get("dimensions", {}).get("redundancy_penalty", 0.0))
        for item in decisions
    ]
    scores = [float(item.get("promotion_score", 0.0)) for item in decisions]
    prediction_report = _load_json(reports_dir / "phase17_validation_report.json") or _load_json(
        reports_dir / "phase16_validation_report.json"
    )
    quality = prediction_report.get("after_prediction_quality", {})
    return {
        "concepts": len(decisions),
        "learned_concepts": len(learned_decisions),
        "recommendation_counts": governance.get("recommendation_counts", {}),
        "learned_recommendation_counts": learned_metrics["recommendation_counts"],
        "average_promotion_score": governance.get("average_promotion_score", 0.0),
        "score_min": round(min(scores), 4) if scores else 0.0,
        "score_max": round(max(scores), 4) if scores else 0.0,
        "score_ge_056": sum(1 for score in scores if score >= 0.56),
        "score_ge_062": sum(1 for score in scores if score >= 0.62),
        "prompt_artifact_count": len(prompt_artifacts),
        "prompt_artifact_rate": round(len(prompt_artifacts) / max(1, len(decisions)), 4),
        "incomplete_count": len(incomplete),
        "incomplete_rate": round(len(incomplete) / max(1, len(decisions)), 4),
        "average_redundancy": round(sum(redundancies) / max(1, len(redundancies)), 4),
        "learned_average_promotion_score": learned_metrics["average_promotion_score"],
        "learned_score_ge_056": learned_metrics["score_ge_056"],
        "learned_score_ge_062": learned_metrics["score_ge_062"],
        "learned_prompt_artifact_count": learned_metrics["prompt_artifact_count"],
        "learned_prompt_artifact_rate": learned_metrics["prompt_artifact_rate"],
        "learned_incomplete_count": learned_metrics["incomplete_count"],
        "learned_incomplete_rate": learned_metrics["incomplete_rate"],
        "learned_average_redundancy": learned_metrics["average_redundancy"],
        "prediction_coverage": quality.get("coverage"),
        "prediction_accuracy": quality.get("accuracy"),
        "prediction_failed": quality.get("failed"),
        "prediction_supported": quality.get("supported"),
    }


class _UnionFind:
    def __init__(self, ids: list[str]) -> None:
        self.parent = {item: item for item in ids}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root

    def groups(self) -> list[list[str]]:
        buckets: dict[str, list[str]] = defaultdict(list)
        for item in self.parent:
            buckets[self.find(item)].append(item)
        return list(buckets.values())


def _coherence_metrics(store_root: Path, reports_dir: Path) -> dict[str, Any]:
    memory = MemoryStore(store_root / "memory.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")

    concepts = knowledge.latest()
    concept_ids = [record.concept_id for record in concepts]
    concept_by_id = {record.concept_id: record for record in concepts}
    decisions = {
        item.get("concept_id"): item
        for item in _load_json(reports_dir / "promotion_governance_report.json").get("decisions", [])
    }
    evidence_to_concepts: dict[str, set[str]] = defaultdict(set)
    objective_to_concepts: dict[str, set[str]] = defaultdict(set)
    provider_to_concepts: dict[str, set[str]] = defaultdict(set)
    prediction_counts: Counter[str] = Counter()
    for record in concepts:
        for evidence_id in record.supporting_evidence:
            evidence_to_concepts[str(evidence_id)].add(record.concept_id)
        provenance = decisions.get(record.concept_id, {}).get("provenance", {})
        objective_to_concepts[str(provenance.get("objective_tag") or "unknown")].add(record.concept_id)
        provider_to_concepts[str(provenance.get("source_provider") or "unknown")].add(record.concept_id)
    for prediction in predictions.latest():
        if prediction.source_concept_id in concept_by_id:
            prediction_counts[prediction.source_concept_id] += 1

    relationship_list = relationships.latest()
    memory_relationship_ids: dict[str, list[Any]] = defaultdict(list)
    direct_semantic_edges: Counter[str] = Counter()
    relationship_types = Counter()
    for relationship in relationship_list:
        relationship_types[relationship.relationship_type] += 1
        if relationship.source_id in concept_by_id:
            direct_semantic_edges[relationship.source_id] += 1
        if relationship.target_id in concept_by_id:
            direct_semantic_edges[relationship.target_id] += 1
        memory_relationship_ids[relationship.source_id].append(relationship)
        memory_relationship_ids[relationship.target_id].append(relationship)

    uf = _UnionFind(concept_ids)
    for bucket in evidence_to_concepts.values():
        items = list(bucket)
        for item in items[1:]:
            uf.union(items[0], item)
    for objective, bucket in objective_to_concepts.items():
        if objective == "unknown":
            continue
        items = list(bucket)
        for item in items[1:]:
            uf.union(items[0], item)

    per_concept = []
    for record in concepts:
        shared_evidence_neighbors = set()
        evidence_relationship_types = set()
        evidence_relationship_count = 0
        for evidence_id in record.supporting_evidence:
            shared_evidence_neighbors.update(evidence_to_concepts.get(str(evidence_id), set()))
            touching = memory_relationship_ids.get(str(evidence_id), [])
            evidence_relationship_count += len(touching)
            evidence_relationship_types.update(item.relationship_type for item in touching)
        shared_evidence_neighbors.discard(record.concept_id)
        provenance = decisions.get(record.concept_id, {}).get("provenance", {})
        objective = str(provenance.get("objective_tag") or "unknown")
        objective_neighbors = set(objective_to_concepts.get(objective, set()))
        objective_neighbors.discard(record.concept_id)
        incomplete = _incomplete_proposition(record.concept, record.definition)
        isolated = (
            not shared_evidence_neighbors
            and not objective_neighbors
            and prediction_counts[record.concept_id] == 0
            and evidence_relationship_count == 0
            and direct_semantic_edges[record.concept_id] == 0
        )
        per_concept.append(
            {
                "concept_id": record.concept_id,
                "concept": record.concept,
                "recommendation": decisions.get(record.concept_id, {}).get("recommendation", "unknown"),
                "promotion_score": decisions.get(record.concept_id, {}).get("promotion_score", 0.0),
                "objective": objective,
                "provider": str(provenance.get("source_provider") or "unknown"),
                "shared_evidence_neighbors": len(shared_evidence_neighbors),
                "objective_neighbors": len(objective_neighbors),
                "prediction_count": prediction_counts[record.concept_id],
                "evidence_relationship_count": evidence_relationship_count,
                "evidence_relationship_diversity": len(evidence_relationship_types),
                "direct_semantic_edges": direct_semantic_edges[record.concept_id],
                "isolated": isolated,
                "incomplete": incomplete,
            }
        )

    clusters = []
    for group in uf.groups():
        token_counter = Counter()
        for concept_id in group:
            record = concept_by_id[concept_id]
            token_counter.update(_content_tokens(f"{record.concept} {record.definition}"))
        clusters.append(
            {
                "size": len(group),
                "concept_ids": group,
                "top_terms": [term for term, _count in token_counter.most_common(8)],
                "sample_concepts": [concept_by_id[concept_id].concept for concept_id in group[:8]],
            }
        )
    clusters.sort(key=lambda item: (-item["size"], item["top_terms"]))

    concept_text_counts = Counter(record.concept for record in concepts)
    evidence_reuse = [len(items) for items in evidence_to_concepts.values()]
    shared_evidence_values = [item["shared_evidence_neighbors"] for item in per_concept]
    objective_values = [item["objective_neighbors"] for item in per_concept]
    prediction_values = [item["prediction_count"] for item in per_concept]
    relationship_diversity_values = [item["evidence_relationship_diversity"] for item in per_concept]
    isolated = [item for item in per_concept if item["isolated"]]

    cooccurrence = Counter()
    for cluster in clusters:
        terms = cluster["top_terms"][:6]
        for left_index, left in enumerate(terms):
            for right in terms[left_index + 1 :]:
                cooccurrence[tuple(sorted((left, right)))] += cluster["size"]

    return {
        "store_root": str(store_root),
        "concept_count": len(concepts),
        "average_shared_evidence_neighbors": round(sum(shared_evidence_values) / max(1, len(shared_evidence_values)), 4),
        "average_objective_neighbors": round(sum(objective_values) / max(1, len(objective_values)), 4),
        "average_prediction_links": round(sum(prediction_values) / max(1, len(prediction_values)), 4),
        "average_relationship_diversity": round(sum(relationship_diversity_values) / max(1, len(relationship_diversity_values)), 4),
        "isolated_concepts": len(isolated),
        "isolated_rate": round(len(isolated) / max(1, len(concepts)), 4),
        "reused_evidence_count": sum(1 for value in evidence_reuse if value > 1),
        "average_concepts_per_evidence": round(sum(evidence_reuse) / max(1, len(evidence_reuse)), 4),
        "duplicate_concept_texts": sum(1 for _text, count in concept_text_counts.items() if count > 1),
        "relationship_type_counts": dict(relationship_types.most_common()),
        "cluster_count": len(clusters),
        "largest_cluster_size": clusters[0]["size"] if clusters else 0,
        "clusters": clusters[:25],
        "isolated_samples": sorted(isolated, key=lambda item: item["promotion_score"])[:50],
        "top_cooccurring_terms": [
            {"terms": list(pair), "weighted_count": count}
            for pair, count in cooccurrence.most_common(25)
        ],
        "per_concept": per_concept,
    }


def _table_row(label: str, baseline: Any, experiment: Any) -> str:
    return f"| {label} | {baseline} | {experiment} |"


def write_reports(
    *,
    baseline_store: Path,
    baseline_reports: Path,
    experiment_store: Path,
    experiment_reports: Path,
    output_dir: Path,
) -> dict[str, Any]:
    baseline_governance = _governance_metrics(baseline_reports)
    experiment_governance = _governance_metrics(experiment_reports)
    baseline_coherence = _coherence_metrics(baseline_store, baseline_reports)
    experiment_coherence = _coherence_metrics(experiment_store, experiment_reports)
    summary = {
        "baseline": {
            "store": str(baseline_store),
            "reports": str(baseline_reports),
            "governance": baseline_governance,
            "coherence": baseline_coherence,
        },
        "experiment": {
            "store": str(experiment_store),
            "reports": str(experiment_reports),
            "governance": experiment_governance,
            "coherence": experiment_coherence,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase23_concept_coherence.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "phase23_concept_coherence.md").write_text(
        "\n".join(
            [
                "# Phase 23 Concept Coherence Audit",
                "",
                "Diagnostic-only audit. No semantic edges were generated, no stores were modified, and no canonical promotion was performed.",
                "",
                "## Comparison",
                "",
                "| Metric | Phase 20 planning-20 baseline | Formatting-contract run |",
                "| --- | ---: | ---: |",
                _table_row("Concepts evaluated", baseline_governance["concepts"], experiment_governance["concepts"]),
                _table_row("Learned concepts evaluated", baseline_governance["learned_concepts"], experiment_governance["learned_concepts"]),
                _table_row("Prompt artifact rate, all concepts", baseline_governance["prompt_artifact_rate"], experiment_governance["prompt_artifact_rate"]),
                _table_row("Prompt artifact rate, learned concepts", baseline_governance["learned_prompt_artifact_rate"], experiment_governance["learned_prompt_artifact_rate"]),
                _table_row("Incomplete proposition rate, all concepts", baseline_governance["incomplete_rate"], experiment_governance["incomplete_rate"]),
                _table_row("Incomplete proposition rate, learned concepts", baseline_governance["learned_incomplete_rate"], experiment_governance["learned_incomplete_rate"]),
                _table_row("Average redundancy, learned concepts", baseline_governance["learned_average_redundancy"], experiment_governance["learned_average_redundancy"]),
                _table_row("Average promotion score", baseline_governance["average_promotion_score"], experiment_governance["average_promotion_score"]),
                _table_row("Learned average promotion score", baseline_governance["learned_average_promotion_score"], experiment_governance["learned_average_promotion_score"]),
                _table_row("Learned scores >= 0.56", baseline_governance["learned_score_ge_056"], experiment_governance["learned_score_ge_056"]),
                _table_row("Learned scores >= 0.62", baseline_governance["learned_score_ge_062"], experiment_governance["learned_score_ge_062"]),
                _table_row("Prediction coverage", baseline_governance["prediction_coverage"], experiment_governance["prediction_coverage"]),
                _table_row("Prediction accuracy", baseline_governance["prediction_accuracy"], experiment_governance["prediction_accuracy"]),
                _table_row("Average shared-evidence neighbors", baseline_coherence["average_shared_evidence_neighbors"], experiment_coherence["average_shared_evidence_neighbors"]),
                _table_row("Average objective neighbors", baseline_coherence["average_objective_neighbors"], experiment_coherence["average_objective_neighbors"]),
                _table_row("Average prediction links", baseline_coherence["average_prediction_links"], experiment_coherence["average_prediction_links"]),
                _table_row("Average relationship diversity", baseline_coherence["average_relationship_diversity"], experiment_coherence["average_relationship_diversity"]),
                _table_row("Isolated concept rate", baseline_coherence["isolated_rate"], experiment_coherence["isolated_rate"]),
                _table_row("Reused evidence count", baseline_coherence["reused_evidence_count"], experiment_coherence["reused_evidence_count"]),
                _table_row("Largest cluster size", baseline_coherence["largest_cluster_size"], experiment_coherence["largest_cluster_size"]),
                "",
                "## Recommendation Counts",
                "",
                f"- Baseline: `{baseline_governance['recommendation_counts']}`",
                f"- Formatting run: `{experiment_governance['recommendation_counts']}`",
                f"- Baseline learned-only: `{baseline_governance['learned_recommendation_counts']}`",
                f"- Formatting learned-only: `{experiment_governance['learned_recommendation_counts']}`",
                "",
                "## Interpretation",
                "",
                "The formatting contract did not prove a coherent semantic graph improvement. The run saturated after 8 cycles, produced fewer learned concepts, and still emitted incomplete fragments that required an additional governance quality-gate fix.",
                "",
                "The apparent all-concept prompt-artifact improvement is denominator-sensitive because bootstrap concepts dominated the shorter formatting run. On learned concepts only, prompt artifacts and incomplete propositions did not improve.",
                "",
                "Conclusion: the current formatting contract should not become the default yet. Phase 23 shows no reliable evidence that it produces a more coherent semantic substrate.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "phase23_cluster_report.md").write_text(
        "\n".join(
            [
                "# Phase 23 Cluster Report",
                "",
                "Clusters are report-only connected components formed through shared supporting evidence and shared objective provenance. No semantic edges were created.",
                "",
                "## Baseline Clusters",
                "",
                *[
                    f"- size `{cluster['size']}` terms `{', '.join(cluster['top_terms'])}` samples `{cluster['sample_concepts'][:3]}`"
                    for cluster in baseline_coherence["clusters"][:15]
                ],
                "",
                "## Formatting-Run Clusters",
                "",
                *[
                    f"- size `{cluster['size']}` terms `{', '.join(cluster['top_terms'])}` samples `{cluster['sample_concepts'][:3]}`"
                    for cluster in experiment_coherence["clusters"][:15]
                ],
                "",
                "## Repeated Term Groups",
                "",
                *[
                    f"- `{', '.join(item['terms'])}`: `{item['weighted_count']}`"
                    for item in experiment_coherence["top_cooccurring_terms"][:20]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "phase23_isolated_concepts.md").write_text(
        "\n".join(
            [
                "# Phase 23 Isolated Concepts",
                "",
                f"Baseline isolated concepts: `{baseline_coherence['isolated_concepts']}` of `{baseline_coherence['concept_count']}`.",
                f"Formatting-run isolated concepts: `{experiment_coherence['isolated_concepts']}` of `{experiment_coherence['concept_count']}`.",
                "",
                "## Formatting-Run Isolated Samples",
                "",
                *[
                    f"- `{item['concept']}` | recommendation `{item['recommendation']}` | score `{item['promotion_score']}`"
                    for item in experiment_coherence["isolated_samples"][:30]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "phase23_relationship_diversity.md").write_text(
        "\n".join(
            [
                "# Phase 23 Relationship Diversity",
                "",
                "Relationship diversity is computed from existing memory/evidence relationships touching supporting evidence. It is not persisted as semantic edges.",
                "",
                "## Baseline",
                "",
                f"- Average relationship diversity: `{baseline_coherence['average_relationship_diversity']}`",
                f"- Relationship types: `{baseline_coherence['relationship_type_counts']}`",
                "",
                "## Formatting Run",
                "",
                f"- Average relationship diversity: `{experiment_coherence['average_relationship_diversity']}`",
                f"- Relationship types: `{experiment_coherence['relationship_type_counts']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 23 diagnostic concept coherence audit.")
    parser.add_argument("--baseline-store", required=True)
    parser.add_argument("--baseline-reports", required=True)
    parser.add_argument("--experiment-store", required=True)
    parser.add_argument("--experiment-reports", required=True)
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args()
    summary = write_reports(
        baseline_store=Path(args.baseline_store),
        baseline_reports=Path(args.baseline_reports),
        experiment_store=Path(args.experiment_store),
        experiment_reports=Path(args.experiment_reports),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "baseline_concepts": summary["baseline"]["governance"]["concepts"],
                "experiment_concepts": summary["experiment"]["governance"]["concepts"],
                "baseline_artifact_rate": summary["baseline"]["governance"]["prompt_artifact_rate"],
                "experiment_artifact_rate": summary["experiment"]["governance"]["prompt_artifact_rate"],
                "baseline_incomplete_rate": summary["baseline"]["governance"]["incomplete_rate"],
                "experiment_incomplete_rate": summary["experiment"]["governance"]["incomplete_rate"],
                "baseline_largest_cluster": summary["baseline"]["coherence"]["largest_cluster_size"],
                "experiment_largest_cluster": summary["experiment"]["coherence"]["largest_cluster_size"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
