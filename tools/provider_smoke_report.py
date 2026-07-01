from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _latest_run_id(queue_records: list[dict[str, Any]]) -> str | None:
    run_ids = [
        record.get("metadata", {}).get("run_id")
        for record in queue_records
        if record.get("metadata", {}).get("run_id")
    ]
    return run_ids[-1] if run_ids else None


def _avg(records: list[dict[str, Any]], key: str) -> float:
    values = [float(record.get(key, 0.0) or 0.0) for record in records]
    return round(mean(values), 4) if values else 0.0


def _metric(result: dict[str, Any], legacy_name: str, current_name: str) -> float:
    if current_name in result:
        return float(result.get(current_name) or 0.0)
    metrics = result.get("metrics", {})
    return float(metrics.get(legacy_name, 0.0) or 0.0)


def _summarize(records: list[dict[str, Any]], *keys: str) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        bucket_key = "::".join(str(record.get(key, "unknown")) for key in keys)
        buckets[bucket_key].append(record)
    summary: dict[str, Any] = {}
    for bucket_key, bucket_records in sorted(buckets.items()):
        entry: dict[str, Any] = {
            "count": len(bucket_records),
            "average_utility": _avg(bucket_records, "utility"),
            "average_information_gain": _avg(bucket_records, "information_gain"),
            "average_surprise": _avg(bucket_records, "surprise"),
        }
        if keys == ("provider", "capability"):
            provider, capability = bucket_key.split("::", 1)
            entry["provider"] = provider
            entry["capability"] = capability
        summary[bucket_key] = entry
    return summary


def build_report(queue_path: Path, results_path: Path, run_id: str | None = None) -> dict[str, Any]:
    queue_records = _read_jsonl(queue_path)
    results_records = _read_jsonl(results_path)
    selected_run_id = run_id or _latest_run_id(queue_records)
    if not selected_run_id:
        raise SystemExit("No provider smoke run_id found in queue metadata.")

    queue_by_id = {
        record.get("item_id"): record
        for record in queue_records
        if record.get("metadata", {}).get("run_id") == selected_run_id
    }
    joined: list[dict[str, Any]] = []
    generated_experience_count = 0
    for result in results_records:
        queue_record = queue_by_id.get(result.get("item_id"))
        if not queue_record:
            continue
        metadata = queue_record.get("metadata", {})
        generated_experience_count += int(
            result.get("generated_experience_count")
            or len(result.get("generated_experiences", []))
        )
        joined.append(
            {
                "provider": result.get("provider_model")
                or queue_record.get("provider_model")
                or metadata.get("provider_model", "unknown"),
                "capability": queue_record.get("capability", "unknown"),
                "objective": metadata.get("objective_id") or queue_record.get("task_type", "unknown"),
                "status": result.get("status", "unknown"),
                "utility": _metric(result, "experience_utility", "utility_score"),
                "information_gain": _metric(result, "information_gain", "information_gain_score"),
                "surprise": _metric(result, "surprise", "surprise_score"),
            }
        )

    completed = [record for record in joined if record["status"] == "completed"]
    failed = [record for record in joined if record["status"] != "completed"]
    return {
        "run_id": selected_run_id,
        "count": len(joined),
        "completed": len(completed),
        "failed": len(failed),
        "generated_experience_count": generated_experience_count,
        "average_utility": _avg(completed, "utility"),
        "average_information_gain": _avg(completed, "information_gain"),
        "average_surprise": _avg(completed, "surprise"),
        "by_provider": _summarize(completed, "provider"),
        "by_capability": _summarize(completed, "capability"),
        "by_objective": _summarize(completed, "objective"),
        "by_provider_capability": _summarize(completed, "provider", "capability"),
    }


def _table(summary: dict[str, Any], title: str, label: str) -> list[str]:
    lines = [f"## {title}", "", f"| {label} | Count | Utility | Info Gain | Surprise |", "| --- | ---: | ---: | ---: | ---: |"]
    for name, row in summary.items():
        lines.append(
            f"| {name} | {row['count']} | {row['average_utility']} | "
            f"{row['average_information_gain']} | {row['average_surprise']} |"
        )
    return lines


def _best_by_capability(report: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    best: dict[str, tuple[str, dict[str, Any]]] = {}
    for row in report.get("by_provider_capability", {}).values():
        capability = str(row.get("capability", "unknown"))
        provider = str(row.get("provider", "unknown"))
        current = best.get(capability)
        if current is None or row["average_utility"] > current[1]["average_utility"]:
            best[capability] = (provider, row)
    return [(capability, provider, row) for capability, (provider, row) in sorted(best.items())]


def write_reports(
    report: dict[str, Any],
    json_path: Path,
    markdown_path: Path,
    *,
    title: str = "Provider Smoke Report",
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        f"# {title}",
        "",
        f"Run ID: `{report['run_id']}`",
        "",
        f"Completed: {report['completed']}/{report['count']}",
        f"Generated experience candidates: {report['generated_experience_count']}",
        f"Average utility: {report['average_utility']}",
        f"Average information gain: {report['average_information_gain']}",
        f"Average surprise: {report['average_surprise']}",
        "",
        *_table(report["by_provider"], "By Provider", "Provider"),
        "",
        *_table(report["by_capability"], "By Capability", "Capability"),
        "",
        *_table(report["by_objective"], "By Objective", "Objective"),
        "",
        "## Best Provider By Capability",
        "",
        "| Capability | Provider | Utility | Info Gain | Surprise | Count |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
        *[
            (
                f"| {capability} | {provider} | {row['average_utility']} | "
                f"{row['average_information_gain']} | {row['average_surprise']} | {row['count']} |"
            )
            for capability, provider, row in _best_by_capability(report)
        ],
        "",
        "## Notes",
        "",
        "- This report is generated from experiment scheduler results joined to queue metadata.",
        "- Generated experiences are candidates only; no direct semantic knowledge promotion is performed.",
        "- Surprise is present but uneven; inspect the capability and objective tables before expanding the next run.",
    ]
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize provider smoke run utility metrics.")
    parser.add_argument("--queue", default="data/experiments/experiment_queue.jsonl")
    parser.add_argument("--results", default="data/experiments/experiment_results.jsonl")
    parser.add_argument("--run-id")
    parser.add_argument("--json-out", default="reports/provider_smoke_report.json")
    parser.add_argument("--md-out", default="reports/provider_smoke_report.md")
    parser.add_argument("--title", default="Provider Smoke Report")
    args = parser.parse_args()

    report = build_report(Path(args.queue), Path(args.results), args.run_id)
    write_reports(report, Path(args.json_out), Path(args.md_out), title=args.title)
    print(
        f"wrote {args.json_out} and {args.md_out}; "
        f"completed={report['completed']}/{report['count']} utility={report['average_utility']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
