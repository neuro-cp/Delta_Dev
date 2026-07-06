from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp14_substrate_first_improvement import write_tp14_reports  # noqa: E402


def main() -> int:
    payload = write_tp14_reports()
    print(json.dumps({
        "phase": payload["phase"],
        "passed": payload["passed"],
        "final_recommendation": payload["final_recommendation"],
        "substrate_matches_or_exceeds_shadow": payload["vs_training"]["substrate_matches_or_exceeds_shadow"],
        "training_started": payload["safety"]["training_started"],
        "new_shadow_artifact_created": payload["safety"]["new_shadow_artifact_created"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
