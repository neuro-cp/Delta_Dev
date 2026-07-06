from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp5_noncanonical_persistent_pilot import write_tp5_reports  # noqa: E402


def main() -> int:
    payload = write_tp5_reports()
    print(json.dumps({
        "phase": payload["phase"],
        "final_recommendation": payload["final_recommendation"],
        "passed": payload["passed"],
        "record_id": payload["persistence"]["record"]["record_id"],
        "canonical": payload["persistence"]["record"]["canonical"],
        "provider_call_performed": payload["safety"]["provider_call_performed"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
