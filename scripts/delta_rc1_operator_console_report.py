from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_operator_console_report import write_operator_console_report  # noqa: E402


def main() -> int:
    payload = write_operator_console_report()
    print(json.dumps({
        "safe": payload["safe"],
        "ui_route": payload["ui_route"],
        "features": len(payload["features"]),
        "final_recommendation": payload["final_recommendation"],
    }, indent=2, sort_keys=True))
    return 0 if payload["safe"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

