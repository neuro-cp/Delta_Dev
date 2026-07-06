from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp12_disabled_shadow_training_dry_run import write_tp12_reports  # noqa: E402


def main() -> int:
    payload = write_tp12_reports()
    print(json.dumps({
        "phase": payload["phase"],
        "passed": payload["passed"],
        "final_recommendation": payload["final_recommendation"],
        "training_started": payload["safety"]["training_started"],
        "optimization_started": payload["safety"]["optimization_started"],
        "model_artifact_created": payload["safety"]["model_artifact_created"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
