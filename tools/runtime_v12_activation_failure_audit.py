from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.candidate_knowledge_retrieval import KnowledgeActivationEngine
from orchestration.runtime.knowledge_attention import KnowledgeAttentionFilter, _expanded_tokens
from tools.runtime_v12_real_knowledge import (
    _build_cases,
    _chunk_report_dirs,
    _concept_summary,
    _governance_decisions,
    _load_jsonl,
)


BASELINE_LIMIT = 10
AUDIT_LIMIT = 50


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only diagnostic audit for Runtime V1.2 activation and attention failures."
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
    cases, case_metadata = _build_cases(records=records, decisions=decisions)

    activation = KnowledgeActivationEngine(store_root=store_root, reports_dirs=reports_dirs)
    attention = KnowledgeAttentionFilter()
    record_by_id = {str(record.get("concept_id")): record for record in records}

    case_audits: list[dict[str, Any]] = []
    for case in cases:
        wide_activation = activation.activate(case.question, limit=AUDIT_LIMIT)
        baseline_items = wide_activation.items[:BASELINE_LIMIT]
        baseline_activation = type(wide_activation)(query=wide_activation.query, items=baseline_items)
        baseline_attention = attention.filter(baseline_activation)
        wide_attention = attention.filter(wide_activation)
        case_audits.append(
            _audit_case(
                case=case,
                case_metadata=case_metadata.get(case.name, {}),
                records=record_by_id,
                wide_activation=wide_activation,
                baseline_attention=baseline_attention,
                wide_attention=wide_attention,
            )
        )

    after_hash = _file_hash(store_path)
    payload = _payload(
        campaign=str(campaign_dir),
        store_hash_before=before_hash,
        store_hash_after=after_hash,
        case_audits=case_audits,
    )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    _write_reports(args.reports_dir, payload)
    return 0


def _audit_case(
    *,
    case: Any,
    case_metadata: dict[str, Any],
    records: dict[str, dict[str, Any]],
    wide_activation: Any,
    baseline_attention: Any,
    wide_attention: Any,
) -> dict[str, Any]:
    activated = [item.concept_id for item in wide_activation.items]
    activation_rank = {concept_id: index + 1 for index, concept_id in enumerate(activated)}
    baseline_ids = set(activated[:BASELINE_LIMIT])
    baseline_selected = {item.concept_id for item in baseline_attention.selected_items}
    wide_selected = {item.concept_id for item in wide_attention.selected_items}
    expected = list(case.expected_concepts)
    useful_neighbors = set(case.useful_neighbor_concepts)

    expected_audits = [
        _audit_expected_concept(
            concept_id=concept_id,
            case=case,
            records=records,
            activation_rank=activation_rank,
            baseline_ids=baseline_ids,
            baseline_selected=baseline_selected,
            wide_selected=wide_selected,
            wide_activation=wide_activation,
        )
        for concept_id in expected
    ]
    activated_audits = [
        _audit_activated_item(
            item=item,
            rank=index + 1,
            case=case,
            records=records,
            expected=set(expected),
            useful_neighbors=useful_neighbors,
            baseline_selected=baseline_selected,
            wide_selected=wide_selected,
        )
        for index, item in enumerate(wide_activation.items[:20])
    ]
    miss_categories: dict[str, int] = {}
    for item in expected_audits:
        miss_categories[item["category"]] = miss_categories.get(item["category"], 0) + 1
    return {
        "case": case.name,
        "category": case.category,
        "question": case.question,
        "sparse_expected": case.sparse_expected,
        "expected_count": len(expected),
        "baseline_activation_count": min(BASELINE_LIMIT, len(activated)),
        "wide_activation_count": len(activated),
        "baseline_attention_count": len(baseline_selected),
        "wide_attention_count": len(wide_selected),
        "miss_categories": miss_categories,
        "expected_concepts": expected_audits,
        "top_20_activation": activated_audits,
        "expected_concept_text": case_metadata.get("expected_concept_text", []),
        "useful_neighbor_text": case_metadata.get("useful_neighbor_text", []),
    }


def _audit_expected_concept(
    *,
    concept_id: str,
    case: Any,
    records: dict[str, dict[str, Any]],
    activation_rank: dict[str, int],
    baseline_ids: set[str],
    baseline_selected: set[str],
    wide_selected: set[str],
    wide_activation: Any,
) -> dict[str, Any]:
    rank = activation_rank.get(concept_id)
    similar = _similar_activated(concept_id, records, wide_activation.items[:20])
    if rank is None:
        category = "not_retrieved"
        if similar and similar[0]["similarity"] >= 0.5:
            category = "possible_evaluator_mismatch"
    elif rank > BASELINE_LIMIT:
        category = "retrieved_but_ranked_too_low"
    elif concept_id not in baseline_selected:
        category = "retrieved_but_pruned_by_attention"
    elif concept_id in baseline_selected:
        category = "reached_working_memory"
    else:
        category = "unknown"
    return {
        "concept_id": concept_id,
        "category": category,
        "activation_rank": rank,
        "in_baseline_activation": concept_id in baseline_ids,
        "in_baseline_attention": concept_id in baseline_selected,
        "in_wide_attention": concept_id in wide_selected,
        "concept": _concept_summary(list(records.values()), concept_id),
        "similar_top_20_activated": similar[:3],
    }


def _audit_activated_item(
    *,
    item: Any,
    rank: int,
    case: Any,
    records: dict[str, dict[str, Any]],
    expected: set[str],
    useful_neighbors: set[str],
    baseline_selected: set[str],
    wide_selected: set[str],
) -> dict[str, Any]:
    if item.concept_id in expected:
        role = "expected"
    elif item.concept_id in useful_neighbors:
        role = "useful_neighbor"
    elif case.sparse_expected:
        role = "noise_sparse_case"
    else:
        role = "candidate_noise"
    record = records.get(item.concept_id, {})
    return {
        "rank": rank,
        "concept_id": item.concept_id,
        "role": role,
        "activation_score": item.score,
        "promotion_score": item.promotion_score,
        "confidence": item.confidence,
        "selected_by_baseline_attention": item.concept_id in baseline_selected,
        "selected_by_wide_attention": item.concept_id in wide_selected,
        "concept": record.get("concept", item.concept),
        "definition": record.get("definition", item.definition),
    }


def _similar_activated(
    concept_id: str,
    records: dict[str, dict[str, Any]],
    items: list[Any],
) -> list[dict[str, Any]]:
    expected = records.get(concept_id, {})
    expected_tokens = _expanded_tokens(f"{expected.get('concept', '')} {expected.get('definition', '')}")
    if not expected_tokens:
        return []
    matches: list[dict[str, Any]] = []
    for item in items:
        if item.concept_id == concept_id:
            continue
        candidate_tokens = _expanded_tokens(f"{item.concept} {item.definition}")
        similarity = _jaccard(expected_tokens, candidate_tokens)
        if similarity <= 0.0:
            continue
        matches.append(
            {
                "concept_id": item.concept_id,
                "rank": items.index(item) + 1,
                "similarity": round(similarity, 4),
                "concept": item.concept,
            }
        )
    matches.sort(key=lambda row: (row["similarity"], -row["rank"]), reverse=True)
    return matches


def _payload(
    *,
    campaign: str,
    store_hash_before: str,
    store_hash_after: str,
    case_audits: list[dict[str, Any]],
) -> dict[str, Any]:
    taxonomy: dict[str, int] = {}
    for case in case_audits:
        for category, count in case["miss_categories"].items():
            taxonomy[category] = taxonomy.get(category, 0) + count
    sparse_noise = sum(
        1
        for case in case_audits
        if case["sparse_expected"]
        for item in case["top_20_activation"]
        if item["role"] == "noise_sparse_case"
    )
    return {
        "campaign": campaign,
        "read_only_verified": store_hash_before == store_hash_after,
        "store_hash_before": store_hash_before,
        "store_hash_after": store_hash_after,
        "baseline_limit": BASELINE_LIMIT,
        "audit_limit": AUDIT_LIMIT,
        "case_count": len(case_audits),
        "expected_concepts_audited": sum(case["expected_count"] for case in case_audits),
        "miss_taxonomy": dict(sorted(taxonomy.items())),
        "sparse_noise_top20_count": sparse_noise,
        "cases": case_audits,
        "recommendation": _recommendation(taxonomy, sparse_noise),
    }


def _recommendation(taxonomy: dict[str, int], sparse_noise: int) -> str:
    if taxonomy.get("not_retrieved", 0) or taxonomy.get("retrieved_but_ranked_too_low", 0):
        return "Diagnose activation ranking before changing attention; expected concepts are missing or too low in the real-store candidate list."
    if taxonomy.get("retrieved_but_pruned_by_attention", 0):
        return "Diagnose attention scoring; expected concepts are retrieved in the baseline window but suppressed before working memory."
    if sparse_noise:
        return "Diagnose sparse-query activation; unsupported questions still retrieve unrelated learned concepts before attention suppresses them."
    return "No dominant activation failure mode was found; expand held-out real-store questions before changing runtime behavior."


def _write_reports(reports_dir: Path, payload: dict[str, Any]) -> None:
    (reports_dir / "runtime_v12_activation_failure_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "runtime_v12_activation_failure_audit.md").write_text(
        _summary_markdown(payload),
        encoding="utf-8",
    )
    (reports_dir / "runtime_v12_activation_trace.md").write_text(
        _trace_markdown(payload),
        encoding="utf-8",
    )


def _summary_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.2 Activation Failure Audit",
        "",
        f"- campaign: `{payload['campaign']}`",
        f"- read-only verified: `{payload['read_only_verified']}`",
        f"- baseline activation limit: `{payload['baseline_limit']}`",
        f"- audit activation limit: `{payload['audit_limit']}`",
        f"- cases audited: `{payload['case_count']}`",
        f"- expected concepts audited: `{payload['expected_concepts_audited']}`",
        f"- sparse top-20 noise activations: `{payload['sparse_noise_top20_count']}`",
        "",
        "## Miss Taxonomy",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    if not payload["miss_taxonomy"]:
        lines.append("| none | `0` |")
    for category, count in payload["miss_taxonomy"].items():
        lines.append(f"| {category} | `{count}` |")
    lines.extend(["", "## Recommendation", "", payload["recommendation"], ""])
    return "\n".join(lines)


def _trace_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Runtime V1.2 Activation Trace", ""]
    for case in payload["cases"]:
        lines.extend(
            [
                f"## {case['case']}",
                "",
                f"- category: `{case['category']}`",
                f"- baseline attention count: `{case['baseline_attention_count']}`",
                f"- wide attention count: `{case['wide_attention_count']}`",
                "",
                "### Expected Concepts",
                "",
                "| Concept | Category | Rank | Baseline Attention | Wide Attention |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        if not case["expected_concepts"]:
            lines.append("| none | none |  |  |  |")
        for item in case["expected_concepts"]:
            lines.append(
                f"| `{item['concept_id']}` | `{item['category']}` | "
                f"`{item['activation_rank']}` | `{item['in_baseline_attention']}` | "
                f"`{item['in_wide_attention']}` |"
            )
        lines.extend(
            [
                "",
                "### Top 20 Activated",
                "",
                "| Rank | Concept | Role | Score | Baseline Attention |",
                "| ---: | --- | --- | ---: | --- |",
            ]
        )
        for item in case["top_20_activation"]:
            lines.append(
                f"| `{item['rank']}` | `{item['concept_id']}` | `{item['role']}` | "
                f"`{item['activation_score']}` | `{item['selected_by_baseline_attention']}` |"
            )
        lines.append("")
    return "\n".join(lines)


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
