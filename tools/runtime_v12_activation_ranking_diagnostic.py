from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.candidate_knowledge_retrieval import (
    KnowledgeActivationEngine,
    _jaccard,
    _tokens,
)
from orchestration.runtime.knowledge_attention import KnowledgeAttentionFilter, _expanded_tokens
from tools.runtime_v12_real_knowledge import (
    _build_cases,
    _chunk_report_dirs,
    _governance_decisions,
    _load_jsonl,
)


BASELINE_LIMIT = 10
DIAGNOSTIC_LIMIT = 50
NEAR_DUPLICATE_THRESHOLD = 0.48
GENERIC_ATTRACTORS = {
    "evidence",
    "plan",
    "planning",
    "failure",
    "resource",
    "prediction",
    "uncertainty",
    "risk",
    "response",
    "emergency",
    "change",
    "support",
    "conflict",
    "contradiction",
    "capacity",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Runtime V1.2 activation ranking diagnostic."
    )
    parser.add_argument(
        "--campaign-root",
        type=Path,
        default=Path(".tmp/experiments/phaseA_architecture_graduation"),
    )
    parser.add_argument("--campaign", default="overnight_3000")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    campaign_dir = args.campaign_root / args.campaign
    store_root = campaign_dir / "store"
    store_path = store_root / "knowledge.jsonl"
    if not store_path.exists():
        raise SystemExit(f"missing Phase A knowledge store: {store_path}")

    before_hash = _file_hash(store_path)
    reports_dirs = _chunk_report_dirs(campaign_dir)
    records = _load_jsonl(store_path)
    decisions = _governance_decisions(reports_dirs)
    cases, _ = _build_cases(records=records, decisions=decisions)
    record_by_id = {str(record.get("concept_id")): record for record in records}

    activation_engine = KnowledgeActivationEngine(store_root=store_root, reports_dirs=reports_dirs)
    attention_filter = KnowledgeAttentionFilter()
    case_reports = []
    for case in cases:
        activation = activation_engine.activate(case.question, limit=DIAGNOSTIC_LIMIT)
        baseline_activation = type(activation)(
            query=activation.query,
            items=activation.items[:BASELINE_LIMIT],
        )
        attention = attention_filter.filter(baseline_activation)
        case_reports.append(
            _diagnose_case(
                case=case,
                activation=activation,
                attention=attention,
                records=record_by_id,
            )
        )

    after_hash = _file_hash(store_path)
    payload = _payload(
        campaign=str(campaign_dir),
        store_hash_before=before_hash,
        store_hash_after=after_hash,
        cases=case_reports,
    )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    _write_reports(args.reports_dir, payload)
    return 0


def _diagnose_case(*, case: Any, activation: Any, attention: Any, records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    selected = {item.concept_id for item in attention.selected_items}
    expected = set(case.expected_concepts)
    top_items = list(activation.items)
    rank_by_id = {item.concept_id: index + 1 for index, item in enumerate(top_items)}
    item_by_id = {item.concept_id: item for item in top_items}
    expected_details = []
    noise_above_counter: Counter[str] = Counter()
    lexical_attractors: Counter[str] = Counter()

    for concept_id in case.expected_concepts:
        item = item_by_id.get(concept_id)
        rank = rank_by_id.get(concept_id)
        noise_above = [
            _item_diagnostic(noise, case.question, records, role=_role(noise.concept_id, expected, set(case.useful_neighbor_concepts), case.sparse_expected))
            for noise in top_items[: max(0, (rank or DIAGNOSTIC_LIMIT + 1) - 1)]
            if noise.concept_id not in expected and noise.concept_id not in set(case.useful_neighbor_concepts)
        ]
        for noise in noise_above:
            noise_above_counter[noise["concept_id"]] += 1
            lexical_attractors.update(noise["generic_query_terms_matched"])
        detail = {
            "concept_id": concept_id,
            "rank": rank,
            "inside_top_10": bool(rank is not None and rank <= BASELINE_LIMIT),
            "inside_top_20": bool(rank is not None and rank <= 20),
            "selected_by_attention": concept_id in selected,
            "pruned_by_attention": bool(rank is not None and rank <= BASELINE_LIMIT and concept_id not in selected),
            "noise_above_count": len(noise_above),
            "nearest_noise_above": noise_above[-1] if noise_above else None,
            "score_gap_to_nearest_noise_above": _score_gap(item, noise_above[-1] if noise_above else None),
            "diagnostic": _item_diagnostic(item, case.question, records, role="expected") if item else None,
            "store_record": _record_summary(records.get(concept_id, {})),
        }
        expected_details.append(detail)

    top_50 = [
        _item_diagnostic(item, case.question, records, role=_role(item.concept_id, expected, set(case.useful_neighbor_concepts), case.sparse_expected))
        for item in top_items
    ]
    clusters = _near_duplicate_clusters(top_50)
    return {
        "case": case.name,
        "category": case.category,
        "question": case.question,
        "sparse_expected": case.sparse_expected,
        "expected_concepts": expected_details,
        "top_50": top_50,
        "near_duplicate_clusters": clusters,
        "noise_above_expected": dict(noise_above_counter.most_common()),
        "lexical_attractors": dict(lexical_attractors.most_common()),
        "expected_outside_top_10": sum(1 for item in expected_details if item["rank"] is None or item["rank"] > BASELINE_LIMIT),
        "expected_outside_top_20": sum(1 for item in expected_details if item["rank"] is None or item["rank"] > 20),
        "expected_pruned_by_attention": sum(1 for item in expected_details if item["pruned_by_attention"]),
        "sparse_noise_activated": sum(1 for item in top_50 if item["role"] == "noise_sparse_case"),
        "diagnosis": _case_diagnosis(expected_details, case.sparse_expected, top_50),
    }


def _item_diagnostic(item: Any | None, question: str, records: dict[str, dict[str, Any]], *, role: str) -> dict[str, Any]:
    if item is None:
        return {}
    record = records.get(item.concept_id, {})
    concept = str(record.get("concept", item.concept))
    definition = str(record.get("definition", item.definition))
    query_tokens = _tokens(question)
    concept_tokens = _tokens(concept)
    definition_tokens = _tokens(definition)
    combined_tokens = _tokens(f"{concept} {definition}")
    expanded_query = _expanded_tokens(question)
    expanded_combined = _expanded_tokens(f"{concept} {definition}")
    overlap = sorted(query_tokens & combined_tokens)
    generic = sorted((query_tokens | expanded_query) & expanded_combined & GENERIC_ATTRACTORS)
    components = _score_components(item, query_tokens, combined_tokens)
    return {
        "concept_id": item.concept_id,
        "role": role,
        "concept": concept,
        "definition": definition,
        "activation_score": item.score,
        "score_components": components,
        "query_concept_overlap": sorted(query_tokens & concept_tokens),
        "query_definition_overlap": sorted(query_tokens & definition_tokens),
        "query_combined_overlap": overlap,
        "generic_query_terms_matched": generic,
        "expanded_jaccard_to_question": round(_jaccard(expanded_query, expanded_combined), 4),
        "promotion_score": item.promotion_score,
        "confidence": item.confidence,
        "recommendation": item.recommendation,
        "projected_centrality": item.metadata.get("projected_centrality", 0.0),
        "evidence_support": item.metadata.get("evidence_support", 0.0),
    }


def _score_components(item: Any, query_tokens: set[str], combined_tokens: set[str]) -> dict[str, float]:
    relevance = _jaccard(query_tokens, combined_tokens)
    confidence = float(item.confidence)
    promotion = float(item.promotion_score)
    centrality = float(item.metadata.get("projected_centrality", 0.0) or 0.0)
    support = float(item.metadata.get("evidence_support", 0.0) or 0.0)
    return {
        "lexical_relevance": round(relevance, 4),
        "weighted_lexical": round(0.55 * relevance, 4),
        "weighted_confidence": round(0.18 * confidence, 4),
        "weighted_promotion": round(0.14 * promotion, 4),
        "weighted_centrality": round(0.08 * centrality, 4),
        "weighted_evidence_support": round(0.05 * support, 4),
    }


def _score_gap(item: Any | None, noise: dict[str, Any] | None) -> float | None:
    if item is None or not noise:
        return None
    return round(float(noise["activation_score"]) - float(item.score), 4)


def _near_duplicate_clusters(top_50: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    used: set[str] = set()
    token_sets = {
        item["concept_id"]: _expanded_tokens(f"{item['concept']} {item['definition']}")
        for item in top_50
    }
    for item in top_50:
        concept_id = item["concept_id"]
        if concept_id in used:
            continue
        members = [concept_id]
        used.add(concept_id)
        for other in top_50:
            other_id = other["concept_id"]
            if other_id in used:
                continue
            similarity = _jaccard(token_sets[concept_id], token_sets[other_id])
            if similarity >= NEAR_DUPLICATE_THRESHOLD:
                members.append(other_id)
                used.add(other_id)
        if len(members) >= 2:
            clusters.append(
                {
                    "size": len(members),
                    "members": members,
                    "roles": Counter(
                        item2["role"]
                        for item2 in top_50
                        if item2["concept_id"] in set(members)
                    ),
                }
            )
    return clusters


def _case_diagnosis(expected_details: list[dict[str, Any]], sparse_expected: bool, top_50: list[dict[str, Any]]) -> str:
    if sparse_expected and any(item["role"] == "noise_sparse_case" for item in top_50):
        return "sparse_activation_abstention_needed"
    if not expected_details:
        return "no_expected_concepts"
    outside = sum(1 for item in expected_details if item["rank"] is None or item["rank"] > BASELINE_LIMIT)
    pruned = sum(1 for item in expected_details if item["pruned_by_attention"])
    if outside > pruned:
        return "activation_ranking_primary"
    if pruned > outside:
        return "attention_primary"
    if outside and pruned:
        return "mixed_activation_attention"
    return "activation_adequate"


def _role(concept_id: str, expected: set[str], useful_neighbors: set[str], sparse: bool) -> str:
    if concept_id in expected:
        return "expected"
    if concept_id in useful_neighbors:
        return "useful_neighbor"
    if sparse:
        return "noise_sparse_case"
    return "noise"


def _payload(*, campaign: str, store_hash_before: str, store_hash_after: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    expected_ranks = [
        item["rank"]
        for case in cases
        for item in case["expected_concepts"]
        if item["rank"] is not None
    ]
    noise_counts = [
        item["noise_above_count"]
        for case in cases
        for item in case["expected_concepts"]
    ]
    diagnoses = Counter(case["diagnosis"] for case in cases)
    recurring_noise = Counter()
    recurring_attractors = Counter()
    for case in cases:
        recurring_noise.update(case["noise_above_expected"])
        recurring_attractors.update(case["lexical_attractors"])
    aggregate = {
        "mean_expected_rank": round(statistics.mean(expected_ranks), 4) if expected_ranks else None,
        "median_expected_rank": round(statistics.median(expected_ranks), 4) if expected_ranks else None,
        "expected_outside_top_10": sum(case["expected_outside_top_10"] for case in cases),
        "expected_outside_top_20": sum(case["expected_outside_top_20"] for case in cases),
        "mean_noise_above_expected": round(statistics.mean(noise_counts), 4) if noise_counts else 0.0,
        "attention_secondary_to_activation_cases": diagnoses.get("activation_ranking_primary", 0),
        "attention_primary_cases": diagnoses.get("attention_primary", 0),
        "mixed_activation_attention_cases": diagnoses.get("mixed_activation_attention", 0),
        "sparse_activation_abstention_cases": diagnoses.get("sparse_activation_abstention_needed", 0),
        "top_recurring_noisy_concepts": recurring_noise.most_common(10),
        "top_recurring_lexical_attractors": recurring_attractors.most_common(12),
    }
    return {
        "campaign": campaign,
        "read_only_verified": store_hash_before == store_hash_after,
        "store_hash_before": store_hash_before,
        "store_hash_after": store_hash_after,
        "baseline_limit": BASELINE_LIMIT,
        "diagnostic_limit": DIAGNOSTIC_LIMIT,
        "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
        "aggregate": aggregate,
        "cases": cases,
        "recommendations": _recommendations(aggregate),
    }


def _recommendations(aggregate: dict[str, Any]) -> dict[str, list[str]]:
    intervention = []
    rejected = [
        "Do not modify learning, validation, normalization, governance, promotion scoring, or provider prompts.",
        "Do not loosen attention or promotion thresholds based only on aggregate V1.2 metrics.",
        "Do not begin conversation support until real-store single-turn activation is more reliable.",
    ]
    evidence = []
    if aggregate["expected_outside_top_10"]:
        intervention.append("Activation ranking diagnostic/prototype: relevant concepts frequently rank outside the top-10 working window.")
    if aggregate["attention_primary_cases"]:
        intervention.append("Attention scoring diagnostic/prototype: some cases retrieve expected concepts in the top-10 but prune them before working memory.")
    if aggregate["sparse_activation_abstention_cases"]:
        intervention.append("Sparse-query abstention gate: unsupported questions activate unrelated concepts before attention suppresses them.")
    evidence.append("Any future change must improve Runtime V1.2 real-store metrics while preserving grounding=1.0, hallucinations=0, read-only store hashes, and sparse refusal behavior.")
    evidence.append("Compare against reports/runtime_v12_real_knowledge.json and reports/runtime_v12_activation_ranking_diagnostic.json before accepting changes.")
    return {
        "Recommended Runtime V1.3 intervention candidates": intervention,
        "Rejected intervention candidates": rejected,
        "Evidence required before implementation": evidence,
        "Benchmark command to run before and after any future change": [
            ".\\.venv311\\Scripts\\python.exe tools\\runtime_v12_real_knowledge.py --campaign-root .tmp\\experiments\\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports",
            ".\\.venv311\\Scripts\\python.exe tools\\runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\\experiments\\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports",
        ],
    }


def _write_reports(reports_dir: Path, payload: dict[str, Any]) -> None:
    (reports_dir / "runtime_v12_activation_ranking_diagnostic.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "runtime_v12_activation_ranking_diagnostic.md").write_text(
        _markdown(payload),
        encoding="utf-8",
    )


def _markdown(payload: dict[str, Any]) -> str:
    aggregate = payload["aggregate"]
    lines = [
        "# Runtime V1.2 Activation Ranking Diagnostic",
        "",
        f"- campaign: `{payload['campaign']}`",
        f"- read-only verified: `{payload['read_only_verified']}`",
        f"- baseline limit: `{payload['baseline_limit']}`",
        f"- diagnostic limit: `{payload['diagnostic_limit']}`",
        "",
        "## Aggregate",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in aggregate.items():
        if key.startswith("top_"):
            continue
        lines.append(f"| {key} | `{value}` |")
    lines.extend(["", "## Top Recurring Noisy Concepts", "", "| Concept ID | Count |", "| --- | ---: |"])
    for concept_id, count in aggregate["top_recurring_noisy_concepts"]:
        lines.append(f"| `{concept_id}` | `{count}` |")
    lines.extend(["", "## Top Recurring Lexical Attractors", "", "| Token | Count |", "| --- | ---: |"])
    for token, count in aggregate["top_recurring_lexical_attractors"]:
        lines.append(f"| `{token}` | `{count}` |")
    lines.extend(["", "## Case Summary", "", "| Case | Diagnosis | Expected Outside Top 10 | Pruned By Attention | Sparse Noise |", "| --- | --- | ---: | ---: | ---: |"])
    for case in payload["cases"]:
        lines.append(
            f"| {case['case']} | `{case['diagnosis']}` | `{case['expected_outside_top_10']}` | "
            f"`{case['expected_pruned_by_attention']}` | `{case['sparse_noise_activated']}` |"
        )
    for section, items in payload["recommendations"].items():
        lines.extend(["", f"## {section}", ""])
        for item in items:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept": record.get("concept", ""),
        "definition": record.get("definition", ""),
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
