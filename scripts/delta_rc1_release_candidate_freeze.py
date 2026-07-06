from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_release_candidate_freeze import write_rc1_reports  # noqa: E402


def main() -> int:
    payload = write_rc1_reports()
    print(json.dumps({
        "passed": payload["passed"],
        "final_recommendation": payload["final_recommendation"],
        "version": payload["manifest"]["version"],
        "operational_baseline": payload["manifest"]["operational_baseline"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

