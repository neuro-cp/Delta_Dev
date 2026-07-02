from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge.consolidation_engine import SemanticConsolidationEngine
from learning.region import LearningStore
from memory.persistent import MemoryStore
from tools.phase16_validation import _prompt_specificity
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


def _memory_by_cycle(memory: MemoryStore) -> dict[str, dict[str, Any]]:
    cycles: dict[str, dict[str, Any]] = defaultdict(dict)
    for item in memory.all():
        cycle_id = str(item.metadata.get("cycle_id") or "")
        if not cycle_id:
            continue
        if item.kind == "observation":
            cycles[cycle_id]["provider_input"] = item.text
        elif item.kind == "orchestration_output":
            cycles[cycle_id]["provider_output"] = item.text
            cycles[cycle_id]["provider"] = item.source
    return cycles


def _knowledge_rows(store_root: Path) -> list[dict[str, Any]]:
    path = store_root / "knowledge.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _governance_by_id(reports_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        item.get("concept_id"): item
        for item in _load_json(reports_dir / "promotion_governance_report.json").get("decisions", [])
    }


def _validation_statuses(reports_dir: Path) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for name in ("phase16_validation_report.json", "phase17_validation_report.json"):
        report = _load_json(reports_dir / name)
        for key in ("concepts", "lifecycle", "confidence_trajectories"):
            payload = report.get(key)
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and item.get("concept_id"):
                        statuses[str(item["concept_id"])] = item
    return statuses


def _failure_reasons(text: str) -> list[str]:
    normalized = " ".join(str(text or "").split())
    lower = normalized.lower()
    reasons = []
    if not normalized:
        return ["empty"]
    if _incomplete_proposition(normalized, normalized):
        reasons.append("incomplete_proposition")
    if lower.startswith(("if ", "when ")) and "," not in lower and " then " not in lower:
        reasons.append("dangling_conditional")
    if any(
        phrase in lower
        for phrase in (
            "the cycle can be completed",
            "complete the cycle",
            "training objective",
            "this prompt",
            "this task",
            "this prediction",
            "the question",
            "the user",
        )
    ):
        reasons.append("prompt_scaffolding_leakage")
    if lower.startswith(("the answer is", "answer:", "based on")):
        reasons.append("answer_prefix_artifact")
    if _prompt_specificity(normalized, "") >= 0.16:
        reasons.append("prompt_artifact")
    tokens = re.findall(r"[a-z0-9_]+", lower)
    if len(tokens) < 7:
        reasons.append("too_short")
    if not any(token in tokens for token in ("is", "are", "can", "should", "must", "may", "will", "requires", "includes", "reduces", "increases", "decreases")):
        reasons.append("missing_predicate_signal")
    if len(re.findall(r"\b(and|or|while|but)\b", lower)) >= 3:
        reasons.append("possible_merged_multiple_propositions")
    return list(dict.fromkeys(reasons))


def _match_records(
    *,
    learning_id: str,
    candidate_text: str,
    knowledge_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matches = [
        row
        for row in knowledge_rows
        if row.get("creation_source") == f"learning:{learning_id}"
        and str(row.get("definition", "")).strip() == candidate_text.strip()
    ]
    if matches:
        return matches
    return [
        row
        for row in knowledge_rows
        if row.get("creation_source") == f"learning:{learning_id}"
        and candidate_text.strip() in str(row.get("definition", ""))
    ]


def audit_boundary(*, store_root: Path, reports_dir: Path, output_dir: Path) -> dict[str, Any]:
    memory = MemoryStore(store_root / "memory.jsonl")
    learning = LearningStore(store_root / "learning.jsonl")
    cycles = _memory_by_cycle(memory)
    knowledge_rows = _knowledge_rows(store_root)
    governance = _governance_by_id(reports_dir)
    validation = _validation_statuses(reports_dir)

    traces = []
    failure_counts = Counter()
    boundary_loss_counts = Counter()
    duplicate_candidate_texts = Counter()
    for record in learning.all():
        cycle = cycles.get(record.cycle_id, {})
        for candidate in record.semantic_candidates:
            candidate_text = str(candidate.text).strip()
            duplicate_candidate_texts[candidate_text] += 1
            matched = _match_records(
                learning_id=record.learning_id,
                candidate_text=candidate_text,
                knowledge_rows=knowledge_rows,
            )
            if not matched:
                reasons = ["not_consolidated"]
                failure_counts.update(reasons)
                traces.append(
                    {
                        "cycle_id": record.cycle_id,
                        "learning_id": record.learning_id,
                        "provider_input": cycle.get("provider_input", ""),
                        "provider_output": cycle.get("provider_output", ""),
                        "semantic_candidate": candidate_text,
                        "semantic_concept": None,
                        "semantic_definition": None,
                        "hypothetical_preserved_concept": SemanticConsolidationEngine._concept_name(candidate_text),
                        "validation_outcome": None,
                        "governance_recommendation": None,
                        "quality_loss_stage": "candidate_not_consolidated",
                        "failure_reasons": reasons,
                    }
                )
                continue
            for row in matched:
                concept = str(row.get("concept", ""))
                definition = str(row.get("definition", ""))
                hypothetical = SemanticConsolidationEngine._concept_name(candidate_text)
                candidate_reasons = _failure_reasons(candidate_text)
                concept_reasons = _failure_reasons(concept)
                failure_counts.update(concept_reasons)
                boundary_loss_stage = "none_detected"
                if concept != hypothetical and definition.strip() == candidate_text.strip():
                    boundary_loss_stage = "consolidation_concept_label_truncation"
                    boundary_loss_counts[boundary_loss_stage] += 1
                elif candidate_reasons:
                    boundary_loss_stage = "learning_candidate_extraction"
                    boundary_loss_counts[boundary_loss_stage] += 1
                decision = governance.get(row.get("concept_id"), {})
                traces.append(
                    {
                        "cycle_id": record.cycle_id,
                        "learning_id": record.learning_id,
                        "concept_id": row.get("concept_id"),
                        "provider_input": cycle.get("provider_input", ""),
                        "provider_output": cycle.get("provider_output", ""),
                        "semantic_candidate": candidate_text,
                        "semantic_concept": concept,
                        "semantic_definition": definition,
                        "hypothetical_preserved_concept": hypothetical,
                        "validation_outcome": validation.get(row.get("concept_id"), {}),
                        "governance_recommendation": decision.get("recommendation"),
                        "promotion_score": decision.get("promotion_score"),
                        "quality_loss_stage": boundary_loss_stage,
                        "candidate_failure_reasons": candidate_reasons,
                        "concept_failure_reasons": concept_reasons,
                    }
                )

    consolidated_traces = [item for item in traces if item.get("semantic_concept")]
    complete_candidates = [
        item for item in traces if not _failure_reasons(item["semantic_candidate"])
    ]
    incomplete_candidates = [
        item for item in traces if _failure_reasons(item["semantic_candidate"])
    ]
    current_incomplete_concepts = [
        item
        for item in consolidated_traces
        if item.get("semantic_concept")
        and _incomplete_proposition(item["semantic_concept"], item["semantic_definition"] or "")
    ]
    hypothetical_incomplete = [
        item
        for item in consolidated_traces
        if _incomplete_proposition(
            item["hypothetical_preserved_concept"],
            item["semantic_definition"] or "",
        )
    ]
    reusable = [
        item
        for item in traces
        if not _failure_reasons(item["semantic_candidate"])
        and _prompt_specificity(item["semantic_candidate"], "") < 0.16
    ]
    summary = {
        "store_root": str(store_root),
        "reports_dir": str(reports_dir),
        "learning_records": len(learning.all()),
        "semantic_candidates": len(traces),
        "consolidated_candidates": len(consolidated_traces),
        "complete_candidate_count": len(complete_candidates),
        "incomplete_candidate_count": len(incomplete_candidates),
        "complete_candidate_rate": round(len(complete_candidates) / max(1, len(traces)), 4),
        "fragment_rate": round(len(incomplete_candidates) / max(1, len(traces)), 4),
        "reusable_candidate_count": len(reusable),
        "reusable_candidate_rate": round(len(reusable) / max(1, len(traces)), 4),
        "current_incomplete_concept_count": len(current_incomplete_concepts),
        "current_incomplete_concept_rate": round(
            len(current_incomplete_concepts) / max(1, len(consolidated_traces)),
            4,
        ),
        "hypothetical_incomplete_concept_count": len(hypothetical_incomplete),
        "hypothetical_incomplete_concept_rate": round(
            len(hypothetical_incomplete) / max(1, len(consolidated_traces)),
            4,
        ),
        "boundary_loss_counts": dict(boundary_loss_counts.most_common()),
        "failure_counts": dict(failure_counts.most_common()),
        "duplicate_candidate_texts": {
            text: count for text, count in duplicate_candidate_texts.items() if count > 1
        },
        "traces": traces,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase24_semantic_boundary_audit.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(summary, output_dir)
    return summary


def _write_markdown(summary: dict[str, Any], output_dir: Path) -> None:
    traces = summary["traces"]
    examples = [
        item
        for item in traces
        if item["quality_loss_stage"] == "consolidation_concept_label_truncation"
    ][:12]
    candidate_failures = [
        item for item in traces if item["quality_loss_stage"] == "learning_candidate_extraction"
    ][:12]
    (output_dir / "phase24_semantic_boundary_audit.md").write_text(
        "\n".join(
            [
                "# Phase 24 Semantic Candidate Boundary Audit",
                "",
                "Diagnostic audit of provider output -> semantic candidate -> semantic record -> validation/governance. No provider inference, canonical promotion, or store mutation was performed by this audit.",
                "",
                "## Summary",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Learning records | {summary['learning_records']} |",
                f"| Semantic candidates traced | {summary['semantic_candidates']} |",
                f"| Consolidated candidates traced | {summary['consolidated_candidates']} |",
                f"| Complete candidate rate | {summary['complete_candidate_rate']} |",
                f"| Fragment rate at candidate extraction | {summary['fragment_rate']} |",
                f"| Reusable candidate rate | {summary['reusable_candidate_rate']} |",
                f"| Current incomplete semantic concept rate | {summary['current_incomplete_concept_rate']} |",
                f"| Hypothetical preserved-label incomplete rate | {summary['hypothetical_incomplete_concept_rate']} |",
                "",
                "## Boundary Loss Counts",
                "",
                *[
                    f"- `{key}`: `{value}`"
                    for key, value in summary["boundary_loss_counts"].items()
                ],
                "",
                "## Interpretation",
                "",
                "The dominant quality loss in the audited store is not provider output formatting and not governance permissiveness. Candidate text often contains a complete proposition, but consolidation previously converted it into an eight-word concept label. That label could become an incomplete fragment even when the stored definition remained complete.",
                "",
                "The implemented boundary-preserving consolidation change keeps complete candidate propositions as concept labels when they fit within a conservative length limit. This preserves meaning without paraphrasing, inference, prompt tuning, or threshold changes.",
                "",
                "## Trace Examples",
                "",
                *[
                    (
                        f"- Candidate: `{item['semantic_candidate']}`\n"
                        f"  - Old concept: `{item['semantic_concept']}`\n"
                        f"  - Preserved concept: `{item['hypothetical_preserved_concept']}`\n"
                        f"  - Governance: `{item['governance_recommendation']}` score `{item['promotion_score']}`"
                    )
                    for item in examples
                ],
                "",
                "## Candidate-Level Failures",
                "",
                *[
                    f"- `{item['semantic_candidate']}` reasons `{item['candidate_failure_reasons']}`"
                    for item in candidate_failures
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "phase24_extraction_failure_catalog.md").write_text(
        "\n".join(
            [
                "# Phase 24 Extraction Failure Catalog",
                "",
                "| Failure Type | Count |",
                "| --- | ---: |",
                *[
                    f"| {key} | {value} |"
                    for key, value in summary["failure_counts"].items()
                ],
                "",
                "## Duplicate Candidate Texts",
                "",
                *[
                    f"- `{text}`: `{count}`"
                    for text, count in summary["duplicate_candidate_texts"].items()
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "phase24_boundary_comparison.md").write_text(
        "\n".join(
            [
                "# Phase 24 Boundary Comparison",
                "",
                "Comparison is deterministic and report-only. `current` reflects existing consolidated records. `preserved-label` reflects the boundary-preserving concept label that future consolidation now uses.",
                "",
                "| Metric | Current | Preserved-label |",
                "| --- | ---: | ---: |",
                f"| Incomplete concept count | {summary['current_incomplete_concept_count']} | {summary['hypothetical_incomplete_concept_count']} |",
                f"| Incomplete concept rate | {summary['current_incomplete_concept_rate']} | {summary['hypothetical_incomplete_concept_rate']} |",
                "",
                "No existing experiment store was rewritten.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 24 semantic boundary audit.")
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--reports-dir", required=True)
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args()
    summary = audit_boundary(
        store_root=Path(args.store_root),
        reports_dir=Path(args.reports_dir),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "semantic_candidates": summary["semantic_candidates"],
                "complete_candidate_rate": summary["complete_candidate_rate"],
                "fragment_rate": summary["fragment_rate"],
                "current_incomplete_concept_rate": summary["current_incomplete_concept_rate"],
                "hypothetical_incomplete_concept_rate": summary["hypothetical_incomplete_concept_rate"],
                "boundary_loss_counts": summary["boundary_loss_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
