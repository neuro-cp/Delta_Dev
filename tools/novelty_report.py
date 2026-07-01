from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.persistent import MemoryStore
from knowledge import SemanticKnowledgeStore
from orchestration.curriculum import CurriculumEngine
from orchestration.novelty import NoveltyAnalyzer


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def build_report(
    *,
    store_root: Path,
    ticks: int,
    output_path: Path | None = None,
) -> dict[str, Any]:
    memory = MemoryStore(store_root / "memory.jsonl")
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    cases = CurriculumEngine().generate_sequence(count=ticks)
    analyzer = NoveltyAnalyzer()
    reports = [
        analyzer.analyze(
            text=case.prompt,
            memories=memory.all(),
            knowledge=knowledge.latest(),
            required_capabilities=case.required_capabilities,
            known_capabilities=("reasoning", "planning", "mathematics"),
        )
        for case in cases
    ]
    summary = {
        "store_root": str(store_root),
        "ticks": ticks,
        "summary": analyzer.summarize(reports),
        "lowest_utility": sorted(
            [_jsonable(report) for report in reports],
            key=lambda item: item["experience_utility_score"],
        )[:5],
        "highest_utility": sorted(
            [_jsonable(report) for report in reports],
            key=lambda item: item["experience_utility_score"],
            reverse=True,
        )[:5],
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure curriculum novelty and utility.")
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--ticks", type=int, required=True)
    parser.add_argument("--output-path")
    args = parser.parse_args()
    report = build_report(
        store_root=Path(args.store_root),
        ticks=max(0, int(args.ticks)),
        output_path=Path(args.output_path) if args.output_path else None,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
