from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp9_controlled_canonical_pilot_design import write_tp9_reports  # noqa: E402


def main() -> int:
    payload = write_tp9_reports()
    print(json.dumps({
        "phase": payload["phase"],
        "passed": payload["passed"],
        "final_recommendation": payload["final_recommendation"],
        "canonical_write_performed": payload["safety"]["canonical_write_performed"],
        "canonical_pilot_enabled": payload["safety"]["canonical_pilot_enabled"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
