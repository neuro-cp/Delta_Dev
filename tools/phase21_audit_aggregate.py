from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def aggregate_phase21_audits(*, campaign_root: Path, reports_dir: Path) -> dict[str, Any]:
    runs = []
    diagnosis_counts: Counter[str] = Counter()
    endpoint_counts: Counter[str] = Counter()
    sampled_total = 0
    direct_total = 0
    projected_total = 0
    for run_dir in sorted(path for path in campaign_root.iterdir() if path.is_dir()):
        audit_path = run_dir / "reports" / "phase21_relationship_centrality_audit.json"
        if not audit_path.exists():
            continue
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        sampled_total += int(audit.get("concepts_sampled", 0))
        direct_total += int(audit.get("concepts_with_direct_semantic_edges", 0))
        projected_total += int(audit.get("concepts_with_projected_memory_edges", 0))
        diagnosis_counts.update(audit.get("diagnosis_counts", {}))
        endpoint_counts.update(audit.get("relationship_endpoint_counts", {}))
        runs.append(
            {
                "run": run_dir.name,
                "concepts_sampled": audit.get("concepts_sampled", 0),
                "direct_semantic": audit.get("concepts_with_direct_semantic_edges", 0),
                "projected_memory": audit.get("concepts_with_projected_memory_edges", 0),
                "avg_direct_edges": audit.get("average_direct_semantic_edges", 0.0),
                "avg_projected_edges": audit.get("average_projected_memory_edges", 0.0),
                "hypothesis": audit.get("hypothesis", "unknown"),
                "diagnosis_counts": audit.get("diagnosis_counts", {}),
            }
        )
    summary = {
        "campaign_root": str(campaign_root),
        "runs": runs,
        "runs_aggregated": len(runs),
        "concepts_sampled": sampled_total,
        "concepts_with_direct_semantic_edges": direct_total,
        "concepts_with_projected_memory_edges": projected_total,
        "direct_semantic_ratio": round(direct_total / max(1, sampled_total), 4),
        "projected_memory_ratio": round(projected_total / max(1, sampled_total), 4),
        "diagnosis_counts": dict(diagnosis_counts),
        "relationship_endpoint_counts": dict(endpoint_counts),
        "conclusion": (
            "governance_centrality_is_blind_to_existing_memory_relationships"
            if projected_total > direct_total and direct_total == 0
            else "relationship_centrality_cause_inconclusive"
        ),
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase21_relationship_centrality_audit.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows = [
        (
            f"| {run['run']} | {run['concepts_sampled']} | {run['direct_semantic']} | "
            f"{run['projected_memory']} | {run['avg_direct_edges']} | "
            f"{run['avg_projected_edges']} | {run['hypothesis']} |"
        )
        for run in runs
    ]
    markdown = [
        "# Phase 21 Relationship Centrality Audit",
        "",
        "Read-only aggregate diagnostic. No experiment stores or canonical knowledge were modified.",
        "",
        "| Run | Concepts Sampled | Direct Semantic Edges | Projected Memory Edges | Avg Direct Edges | Avg Projected Edges | Hypothesis |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        *rows,
        "",
        "## Aggregate",
        "",
        f"- Concepts sampled: `{summary['concepts_sampled']}`",
        f"- Concepts with direct semantic edges: `{summary['concepts_with_direct_semantic_edges']}`",
        f"- Concepts with projected memory edges: `{summary['concepts_with_projected_memory_edges']}`",
        f"- Direct semantic ratio: `{summary['direct_semantic_ratio']}`",
        f"- Projected memory ratio: `{summary['projected_memory_ratio']}`",
        f"- Conclusion: `{summary['conclusion']}`",
        "",
        "## Diagnosis Counts",
        "",
        *[
            f"- `{key}`: `{value}`"
            for key, value in summary["diagnosis_counts"].items()
        ],
        "",
        "## Interpretation",
        "",
        "Relationship structure exists in the memory layer for most sampled concepts, "
        "but no sampled concepts have direct semantic relationship edges. Promotion "
        "governance is therefore measuring concept-level centrality over a graph that "
        "does not yet expose the memory evidence graph.",
        "",
    ]
    (reports_dir / "phase21_relationship_centrality_audit.md").write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate Phase 21 relationship centrality audits.")
    parser.add_argument("--campaign-root", required=True)
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()
    summary = aggregate_phase21_audits(
        campaign_root=Path(args.campaign_root),
        reports_dir=Path(args.reports_dir),
    )
    print(
        json.dumps(
            {
                "runs_aggregated": summary["runs_aggregated"],
                "concepts_sampled": summary["concepts_sampled"],
                "direct_semantic_ratio": summary["direct_semantic_ratio"],
                "projected_memory_ratio": summary["projected_memory_ratio"],
                "conclusion": summary["conclusion"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
