from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp13_research_shadow_training_protocol import write_tp13_reports  # noqa: E402


def main() -> int:
    payload = write_tp13_reports()
    print(json.dumps({
        "phase": payload["phase"],
        "passed": payload["passed"],
        "final_recommendation": payload["final_recommendation"],
        "artifact_id": payload["artifact"]["artifact_id"],
        "model_b_modified": payload["safety"]["model_b_modified"],
        "baseline_replacement_performed": payload["safety"]["baseline_replacement_performed"],
        "routing_to_shadow_artifact_enabled": payload["safety"]["routing_to_shadow_artifact_enabled"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
