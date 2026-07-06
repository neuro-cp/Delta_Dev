from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp11_governed_base_corpus import write_tp11_reports  # noqa: E402


def main() -> int:
    payload = write_tp11_reports()
    print(json.dumps({
        "phase": payload["phase"],
        "passed": payload["passed"],
        "final_recommendation": payload["final_recommendation"],
        "included_count": payload["base"]["included_count"],
        "training_started": payload["safety"]["training_started"],
        "model_artifact_created": payload["safety"]["model_artifact_created"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
