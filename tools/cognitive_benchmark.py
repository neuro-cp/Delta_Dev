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

from orchestration.benchmarks import CognitiveBenchmarkComparator


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _read_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Delta runtime and task-performance benchmark summaries."
    )
    parser.add_argument("--baseline-runtime", required=True)
    parser.add_argument("--candidate-runtime", required=True)
    parser.add_argument("--baseline-task")
    parser.add_argument("--candidate-task")
    parser.add_argument("--provider-summary")
    parser.add_argument("--output-path")
    args = parser.parse_args()

    report = CognitiveBenchmarkComparator().compare(
        baseline_summary=_read_json(args.baseline_runtime) or {},
        candidate_summary=_read_json(args.candidate_runtime) or {},
        baseline_task_summary=_read_json(args.baseline_task),
        candidate_task_summary=_read_json(args.candidate_task),
        provider_summary=_read_json(args.provider_summary),
    )
    payload = json.dumps(_jsonable(report), indent=2, sort_keys=True)
    if args.output_path:
        path = Path(args.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
