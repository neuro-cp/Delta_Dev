from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp7_longitudinal_stability import write_tp7_reports  # noqa: E402


def main() -> int:
    payload = write_tp7_reports()
    print(json.dumps({
        "phase": payload["phase"],
        "passed": payload["passed"],
        "final_recommendation": payload["final_recommendation"],
        "overall_score": payload["scorecard"]["overall_score"],
        "operator_agreement": payload["human_evaluation"]["evaluator_agreement"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
