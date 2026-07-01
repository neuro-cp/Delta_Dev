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

from integration.model_runtime.model_registry import ModelSpec
from integration.model_runtime.provider_qualification import LlamaCppProbeExecutor


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one provider qualification probe.")
    parser.add_argument("--spec-json", required=True)
    parser.add_argument("--n-gpu-layers", type=int, required=True)
    parser.add_argument("--requested-context", type=int, required=True)
    parser.add_argument("--max-context", type=int, required=True)
    parser.add_argument("--max-tokens", type=int, required=True)
    args = parser.parse_args()

    spec = ModelSpec(**json.loads(args.spec_json))
    result = LlamaCppProbeExecutor(
        max_context=args.max_context,
        max_tokens=args.max_tokens,
    ).probe(
        spec,
        n_gpu_layers=args.n_gpu_layers,
        requested_context=args.requested_context,
    )
    print(json.dumps(_jsonable(result), sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
