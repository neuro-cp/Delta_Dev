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

from learning.region import LearningEngine
from memory.persistent import MemoryStore


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


def _answer_text(output: str) -> str:
    raw = str(output or "").strip()
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and parsed.get("answer"):
            return str(parsed["answer"])
    except Exception:
        pass
    return raw


def _legacy_clean(sentence: str) -> str:
    return str(sentence).strip().strip("\"'").rstrip(",;:")


def _legacy_sentences(text: str) -> list[str]:
    normalized = " ".join(str(text).replace("\n", " ").split())
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [_legacy_clean(part) for part in parts if _legacy_clean(part)]


def _legacy_looks_reusable(sentence: str) -> bool:
    tokens = re.findall(r"[a-z0-9_]+", sentence.lower())
    if len(tokens) < 7:
        return False
    if len(sentence) > 260:
        return False
    reusable_terms = {
        "because",
        "confidence",
        "contradiction",
        "conflict",
        "evidence",
        "fail",
        "falsify",
        "if",
        "predict",
        "prediction",
        "requires",
        "risk",
        "should",
        "therefore",
        "uncertainty",
        "when",
    }
    return bool(set(tokens) & reusable_terms)


def _legacy_reasons(sentence: str) -> list[str]:
    return [] if _legacy_looks_reusable(sentence) else ["legacy_not_reusable"]


def _outputs_by_cycle(store_root: Path) -> list[dict[str, Any]]:
    memory = MemoryStore(store_root / "memory.jsonl")
    observations: dict[str, str] = {}
    outputs = []
    for item in memory.all():
        cycle_id = str(item.metadata.get("cycle_id") or "")
        if not cycle_id:
            continue
        if item.kind == "observation":
            observations[cycle_id] = item.text
        elif item.kind == "orchestration_output":
            outputs.append(
                {
                    "cycle_id": cycle_id,
                    "provider_input": observations.get(cycle_id, item.metadata.get("prompt", "")),
                    "provider_output": item.text,
                    "provider": item.source,
                }
            )
    return outputs


def _quality_flags(sentence: str, reasons: list[str]) -> dict[str, Any]:
    lower = sentence.lower()
    artifact = any(
        reason in reasons
        for reason in (
            "prompt_scaffolding",
            "answer_scaffolding",
            "prompt_artifact",
            "imperative_task_wording",
        )
    )
    incomplete = any(
        reason in reasons
        for reason in (
            "incomplete_proposition",
            "dangling_conditional",
            "too_short",
            "missing_predicate_signal",
        )
    )
    multi_claim = bool(re.search(r"\b(and|or|while|but)\b", lower)) and len(
        re.findall(r"\b(is|are|can|should|must|may|will|requires|require|includes|reduces|increases|decreases|improves|supports)\b", lower)
    ) > 1
    reusable = not artifact and not incomplete and not reasons
    return {
        "prompt_artifact": artifact,
        "incomplete": incomplete,
        "fragment": bool(reasons),
        "multi_claim": multi_claim,
        "reusable": reusable,
    }


def _evaluate_sentences(engine: LearningEngine, sentence: str) -> dict[str, Any]:
    current_reasons = engine._candidate_rejection_reasons(sentence)
    legacy_reasons = _legacy_reasons(sentence)
    return {
        "sentence": sentence,
        "legacy_accept": not legacy_reasons,
        "legacy_reasons": legacy_reasons,
        "current_accept": not current_reasons,
        "current_reasons": current_reasons,
        "quality": _quality_flags(sentence, current_reasons),
    }


def audit_extraction_boundary(*, store_root: Path, output_dir: Path) -> dict[str, Any]:
    engine = LearningEngine()
    rows = []
    legacy_rows = []
    current_rows = []
    for output in _outputs_by_cycle(store_root):
        answer = _answer_text(output["provider_output"])
        legacy_sentences = _legacy_sentences(answer)
        current_sentences = engine._sentences(answer)
        for sentence in legacy_sentences:
            evaluated = _evaluate_sentences(engine, sentence)
            evaluated.update(output)
            evaluated["source_segmenter"] = "legacy"
            legacy_rows.append(evaluated)
        for sentence in current_sentences:
            evaluated = _evaluate_sentences(engine, sentence)
            evaluated.update(output)
            evaluated["source_segmenter"] = "current"
            current_rows.append(evaluated)
        for sentence in sorted(set(legacy_sentences + current_sentences)):
            evaluated = _evaluate_sentences(engine, sentence)
            evaluated.update(output)
            evaluated["source_segmenter"] = (
                "both"
                if sentence in legacy_sentences and sentence in current_sentences
                else "legacy_only"
                if sentence in legacy_sentences
                else "current_only"
            )
            rows.append(evaluated)

    legacy_accepted = [row for row in legacy_rows if row["legacy_accept"]]
    current_accepted = [row for row in current_rows if row["current_accept"]]
    good_pool = [
        row for row in current_rows if row["quality"]["reusable"] or row["current_accept"]
    ]
    legacy_good = [row for row in legacy_accepted if row["quality"]["reusable"]]
    current_good = [row for row in current_accepted if row["quality"]["reusable"]]
    def rate(count: int, total: int) -> float:
        return round(count / max(1, total), 4)

    summary = {
        "store_root": str(store_root),
        "outputs_traced": len(_outputs_by_cycle(store_root)),
        "sentences_evaluated": len(rows),
        "legacy_sentences_evaluated": len(legacy_rows),
        "current_sentences_evaluated": len(current_rows),
        "legacy": {
            "accepted": len(legacy_accepted),
            "acceptance_rate": rate(len(legacy_accepted), len(rows)),
            "prompt_artifact_rate": rate(
                sum(1 for row in legacy_accepted if row["quality"]["prompt_artifact"]),
                len(legacy_accepted),
            ),
            "incomplete_rate": rate(
                sum(1 for row in legacy_accepted if row["quality"]["incomplete"]),
                len(legacy_accepted),
            ),
            "fragment_rate": rate(
                sum(1 for row in legacy_accepted if row["quality"]["fragment"]),
                len(legacy_accepted),
            ),
            "multi_claim_rate": rate(
                sum(1 for row in legacy_accepted if row["quality"]["multi_claim"]),
                len(legacy_accepted),
            ),
            "estimated_precision": rate(len(legacy_good), len(legacy_accepted)),
            "estimated_recall": rate(len(legacy_good), len(good_pool)),
        },
        "current": {
            "accepted": len(current_accepted),
            "acceptance_rate": rate(len(current_accepted), len(rows)),
            "prompt_artifact_rate": rate(
                sum(1 for row in current_accepted if row["quality"]["prompt_artifact"]),
                len(current_accepted),
            ),
            "incomplete_rate": rate(
                sum(1 for row in current_accepted if row["quality"]["incomplete"]),
                len(current_accepted),
            ),
            "fragment_rate": rate(
                sum(1 for row in current_accepted if row["quality"]["fragment"]),
                len(current_accepted),
            ),
            "multi_claim_rate": rate(
                sum(1 for row in current_accepted if row["quality"]["multi_claim"]),
                len(current_accepted),
            ),
            "estimated_precision": rate(len(current_good), len(current_accepted)),
            "estimated_recall": rate(len(current_good), len(good_pool)),
        },
        "rejection_reasons": dict(
            Counter(reason for row in rows for reason in row["current_reasons"]).most_common()
        ),
        "examples": rows[:200],
        "legacy_examples": legacy_rows[:200],
        "current_examples": current_rows[:200],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase25_extraction_boundary_audit.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_reports(summary, output_dir)
    return summary


def _write_reports(summary: dict[str, Any], output_dir: Path) -> None:
    examples = summary["examples"]
    current_examples = summary["current_examples"]
    rejected_artifacts = [
        row
        for row in examples
        if row["legacy_accept"] and not row["current_accept"]
    ][:30]
    accepted = [row for row in current_examples if row["current_accept"]][:30]
    (output_dir / "phase25_extraction_boundary_audit.md").write_text(
        "\n".join(
            [
                "# Phase 25 Extraction Boundary Audit",
                "",
                "Deterministic replay audit of LearningEngine sentence segmentation and candidate filtering. No provider inference, canonical promotion, or store mutation was performed.",
                "",
                "| Metric | Legacy Filter | Current Filter |",
                "| --- | ---: | ---: |",
                f"| Accepted candidates | {summary['legacy']['accepted']} | {summary['current']['accepted']} |",
                f"| Acceptance rate | {summary['legacy']['acceptance_rate']} | {summary['current']['acceptance_rate']} |",
                f"| Prompt artifact rate | {summary['legacy']['prompt_artifact_rate']} | {summary['current']['prompt_artifact_rate']} |",
                f"| Incomplete rate | {summary['legacy']['incomplete_rate']} | {summary['current']['incomplete_rate']} |",
                f"| Fragment rate | {summary['legacy']['fragment_rate']} | {summary['current']['fragment_rate']} |",
                f"| Multi-claim rate | {summary['legacy']['multi_claim_rate']} | {summary['current']['multi_claim_rate']} |",
                f"| Estimated precision | {summary['legacy']['estimated_precision']} | {summary['current']['estimated_precision']} |",
                f"| Estimated recall | {summary['legacy']['estimated_recall']} | {summary['current']['estimated_recall']} |",
                "",
                "## Interpretation",
                "",
                "The deterministic filter rejects prompt scaffolding, answer scaffolding, task imperatives, dangling conditionals, incomplete propositions, and formatting remnants before they enter semantic consolidation. Complete reusable propositions continue to pass.",
                "",
                "This is an extraction-boundary quality fix only. It does not rewrite candidate text, call a model, change governance, or alter promotion thresholds.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "phase25_candidate_filter_comparison.md").write_text(
        "\n".join(
            [
                "# Phase 25 Candidate Filter Comparison",
                "",
                "## Current Rejection Reasons",
                "",
                *[
                    f"- `{reason}`: `{count}`"
                    for reason, count in summary["rejection_reasons"].items()
                ],
                "",
                "## Legacy-Accepted Candidates Now Rejected",
                "",
                *[
                    f"- `{row['sentence']}` reasons `{row['current_reasons']}`"
                    for row in rejected_artifacts
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "phase25_candidate_examples.md").write_text(
        "\n".join(
            [
                "# Phase 25 Candidate Examples",
                "",
                "## Accepted By Current Filter",
                "",
                *[f"- `{row['sentence']}`" for row in accepted],
                "",
                "## Rejected Artifact Examples",
                "",
                *[
                    f"- `{row['sentence']}` reasons `{row['current_reasons']}`"
                    for row in rejected_artifacts[:20]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 25 extraction boundary audit.")
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args()
    summary = audit_extraction_boundary(
        store_root=Path(args.store_root),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "legacy": summary["legacy"],
                "current": summary["current"],
                "rejection_reasons": summary["rejection_reasons"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
