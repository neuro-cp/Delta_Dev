from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.model_runtime.provider_manager import ProviderManager  # noqa: E402


def main() -> int:
    try:
        request = json.loads(sys.stdin.read() or "{}")
        model_name = str(request["model_name"])
        prompt = str(request["prompt"])
        task_type = str(request.get("task_type") or "rc2_conversation")
        metadata = dict(request.get("metadata") or {})
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = ProviderManager().infer(
                model_name=model_name,
                prompt=prompt,
                task_type=task_type,
                metadata=metadata,
            )
        print(
            json.dumps(
                {
                    "executed": True,
                    "provider": result.provider,
                    "model_id": result.model_id,
                    "answer": result.answer,
                    "confidence_score": result.confidence,
                    "provider_calls_performed": False,
                    "training_performed": False,
                    "canonical_write_performed": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - helper returns an inert diagnostic.
        print(
            json.dumps(
                {
                    "executed": False,
                    "error": f"{type(exc).__name__}:{str(exc)[:200]}",
                    "provider_calls_performed": False,
                    "training_performed": False,
                    "canonical_write_performed": False,
                },
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
