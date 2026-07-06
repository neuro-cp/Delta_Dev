from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp15_governed_substrate_integration_design import write_tp15_reports  # noqa: E402


def main() -> int:
    payload = write_tp15_reports()
    print(json.dumps({
        "phase": payload["phase"],
        "passed": payload["passed"],
        "final_recommendation": payload["final_recommendation"],
        "mapped_improvements": len(payload["mapping"]["mapped_improvements"]),
        "substrate_integration_performed": payload["safety"]["substrate_integration_performed"],
        "model_b_modified": payload["safety"]["model_b_modified"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
