from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.promotion_governance import run_promotion_governance


def _avg(values: list[float]) -> float:
    return round(mean(values), 4) if values else 0.0


def _store_runs(campaign_root: Path | None, store_root: Path | None) -> list[tuple[str, Path]]:
    if store_root is not None:
        return [(store_root.name or "store", store_root)]
    if campaign_root is None:
        raise ValueError("campaign_root or store_root is required")
    runs = []
    for run_dir in sorted(path for path in campaign_root.iterdir() if path.is_dir()):
        candidate = run_dir / "store"
        if (candidate / "knowledge.jsonl").exists():
            runs.append((run_dir.name, candidate))
    return runs


def compare_projection(
    *,
    reports_dir: Path,
    campaign_root: Path | None = None,
    store_root: Path | None = None,
) -> dict[str, Any]:
    run_summaries = []
    all_changes = []
    all_centrality_increases = []
    all_isolated = []
    all_evidence_boosted = []
    raw_scores = []
    projected_scores = []
    raw_centralities = []
    projected_centralities = []

    for run_name, store in _store_runs(campaign_root, store_root):
        raw_dir = reports_dir / "_phase22_raw" / run_name
        projected_dir = reports_dir / "_phase22_projected" / run_name
        raw = run_promotion_governance(
            store_root=store,
            reports_dir=raw_dir,
            use_projection=False,
        )
        projected = run_promotion_governance(
            store_root=store,
            reports_dir=projected_dir,
            use_projection=True,
        )
        raw_by_id = {item["concept_id"]: item for item in raw["decisions"]}
        projected_by_id = {item["concept_id"]: item for item in projected["decisions"]}
        run_changes = []
        run_increases = []
        run_isolated = []
        run_evidence_boosted = []
        for concept_id, raw_item in raw_by_id.items():
            projected_item = projected_by_id.get(concept_id)
            if projected_item is None:
                continue
            raw_centrality = float(raw_item["dimensions"].get("raw_relationship_centrality", 0.0))
            projected_centrality = float(projected_item["dimensions"].get("projected_centrality", 0.0))
            score_delta = round(
                float(projected_item["promotion_score"]) - float(raw_item["promotion_score"]),
                4,
            )
            raw_scores.append(float(raw_item["promotion_score"]))
            projected_scores.append(float(projected_item["promotion_score"]))
            raw_centralities.append(raw_centrality)
            projected_centralities.append(projected_centrality)
            item = {
                "run": run_name,
                "concept_id": concept_id,
                "concept": raw_item["concept"],
                "raw_recommendation": raw_item["recommendation"],
                "projected_recommendation": projected_item["recommendation"],
                "raw_promotion_score": raw_item["promotion_score"],
                "projected_promotion_score": projected_item["promotion_score"],
                "promotion_score_delta": score_delta,
                "raw_centrality": raw_centrality,
                "projected_centrality": projected_centrality,
                "centrality_delta": round(projected_centrality - raw_centrality, 4),
                "projection_sources": projected_item["evidence"].get("projection_sources", []),
                "projected_neighbor_count": projected_item["evidence"].get("projected_neighbor_count", 0),
                "why_projected_centrality_changed": projected_item["evidence"].get(
                    "why_projected_centrality_changed",
                    "",
                ),
                "incomplete_proposition": projected_item["evidence"].get("incomplete_proposition", False),
                "failed_predictions": projected_item["evidence"].get("failed_predictions", 0),
                "unresolved_predictions": projected_item["evidence"].get("unresolved_predictions", 0),
            }
            if item["raw_recommendation"] != item["projected_recommendation"]:
                run_changes.append(item)
                all_changes.append(item)
            if item["centrality_delta"] > 0:
                run_increases.append(item)
                all_centrality_increases.append(item)
            if projected_centrality == 0.0:
                run_isolated.append(item)
                all_isolated.append(item)
            if (
                raw_centrality == 0.0
                and projected_centrality > 0.0
                and "supporting_evidence_memory_relationships" in item["projection_sources"]
            ):
                run_evidence_boosted.append(item)
                all_evidence_boosted.append(item)
        run_summaries.append(
            {
                "run": run_name,
                "concepts_evaluated": raw["concepts_evaluated"],
                "raw_average_promotion_score": raw["average_promotion_score"],
                "projected_average_promotion_score": projected["average_promotion_score"],
                "promotion_score_delta": round(
                    projected["average_promotion_score"] - raw["average_promotion_score"],
                    4,
                ),
                "raw_recommendation_counts": raw["recommendation_counts"],
                "projected_recommendation_counts": projected["recommendation_counts"],
                "recommendation_changes": len(run_changes),
                "centrality_increases": len(run_increases),
                "remained_isolated": len(run_isolated),
                "evidence_boosted": len(run_evidence_boosted),
            }
        )

    all_changes = sorted(all_changes, key=lambda item: (-abs(item["promotion_score_delta"]), item["concept"]))
    all_centrality_increases = sorted(
        all_centrality_increases,
        key=lambda item: (-item["centrality_delta"], -item["promotion_score_delta"]),
    )
    summary = {
        "runs": run_summaries,
        "concepts_evaluated": sum(run["concepts_evaluated"] for run in run_summaries),
        "average_raw_centrality": _avg(raw_centralities),
        "average_projected_centrality": _avg(projected_centralities),
        "average_raw_promotion_score": _avg(raw_scores),
        "average_projected_promotion_score": _avg(projected_scores),
        "average_promotion_score_delta": round(
            _avg(projected_scores) - _avg(raw_scores),
            4,
        ),
        "recommendation_changes": all_changes,
        "recommendation_change_count": len(all_changes),
        "centrality_increased_most": all_centrality_increases[:50],
        "concepts_remained_isolated": all_isolated[:50],
        "evidence_projection_boosted": all_evidence_boosted[:50],
        "evidence_projection_boosted_count": len(all_evidence_boosted),
        "success_assessment": _assessment(all_changes, all_evidence_boosted, all_isolated),
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase22_projection_comparison.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_report(summary, reports_dir)
    return summary


def _assessment(changes: list[dict[str, Any]], boosted: list[dict[str, Any]], isolated: list[dict[str, Any]]) -> str:
    bad_changes = [
        item
        for item in changes
        if item["projected_recommendation"] == "Promotion Eligible"
        and (item["incomplete_proposition"] or item["failed_predictions"] or item["unresolved_predictions"])
    ]
    if bad_changes:
        return "projection_overwhelmed_quality_gates"
    if boosted and not changes:
        return "projection_revealed_hidden_structure_without_destabilizing_recommendations"
    if boosted and changes:
        return "projection_changed_governance_recommendations_review_required"
    if isolated and not boosted:
        return "projection_found_little_hidden_structure"
    return "projection_effect_inconclusive"


def _write_report(summary: dict[str, Any], reports_dir: Path) -> None:
    lines = [
        "# Phase 22 Projection Comparison",
        "",
        "Diagnostic-only comparison. Raw governance and projected governance were run against the same stores.",
        "No semantic relationships were generated or persisted. No canonical promotion was performed.",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Concepts evaluated | {summary['concepts_evaluated']} |",
        f"| Average raw centrality | {summary['average_raw_centrality']} |",
        f"| Average projected centrality | {summary['average_projected_centrality']} |",
        f"| Average raw promotion score | {summary['average_raw_promotion_score']} |",
        f"| Average projected promotion score | {summary['average_projected_promotion_score']} |",
        f"| Average promotion score delta | {summary['average_promotion_score_delta']} |",
        f"| Recommendation changes | {summary['recommendation_change_count']} |",
        f"| Evidence-projection boosted concepts | {summary['evidence_projection_boosted_count']} |",
        "",
        f"Assessment: `{summary['success_assessment']}`",
        "",
        "## Runs",
        "",
        "| Run | Concepts | Raw Score | Projected Score | Delta | Changes | Boosted | Isolated |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *[
            f"| {run['run']} | {run['concepts_evaluated']} | {run['raw_average_promotion_score']} | {run['projected_average_promotion_score']} | {run['promotion_score_delta']} | {run['recommendation_changes']} | {run['evidence_boosted']} | {run['remained_isolated']} |"
            for run in summary["runs"]
        ],
        "",
        "## Recommendation Changes",
        "",
        *[
            f"- `{item['concept']}` ({item['run']}): `{item['raw_recommendation']}` -> `{item['projected_recommendation']}`, score delta `{item['promotion_score_delta']}`, centrality `{item['raw_centrality']}` -> `{item['projected_centrality']}`"
            for item in summary["recommendation_changes"][:50]
        ],
        "",
        "## Centrality Increased Most",
        "",
        *[
            f"- `{item['concept']}` ({item['run']}): centrality `{item['raw_centrality']}` -> `{item['projected_centrality']}`, sources `{item['projection_sources']}`"
            for item in summary["centrality_increased_most"][:25]
        ],
        "",
        "## Remained Isolated",
        "",
        *[
            f"- `{item['concept']}` ({item['run']})"
            for item in summary["concepts_remained_isolated"][:25]
        ],
        "",
        "## Boosted Through Evidence Projection",
        "",
        *[
            f"- `{item['concept']}` ({item['run']}): projected neighbors `{item['projected_neighbor_count']}`, reason `{item['why_projected_centrality_changed']}`"
            for item in summary["evidence_projection_boosted"][:25]
        ],
        "",
    ]
    (reports_dir / "phase22_projection_comparison.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare raw governance against virtual semantic projection.")
    parser.add_argument("--campaign-root")
    parser.add_argument("--store-root")
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()
    summary = compare_projection(
        campaign_root=Path(args.campaign_root) if args.campaign_root else None,
        store_root=Path(args.store_root) if args.store_root else None,
        reports_dir=Path(args.reports_dir),
    )
    print(
        json.dumps(
            {
                "concepts_evaluated": summary["concepts_evaluated"],
                "average_raw_centrality": summary["average_raw_centrality"],
                "average_projected_centrality": summary["average_projected_centrality"],
                "average_promotion_score_delta": summary["average_promotion_score_delta"],
                "recommendation_change_count": summary["recommendation_change_count"],
                "success_assessment": summary["success_assessment"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
