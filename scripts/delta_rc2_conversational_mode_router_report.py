from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc2_conversational_mode_router import write_rc2_report  # noqa: E402


def main() -> int:
    payload = write_rc2_report()
    print(json.dumps({
        "safe": payload["safe"],
        "modes": len(payload["modes"]),
        "final_recommendation": payload["final_recommendation"],
    }, indent=2, sort_keys=True))
    return 0 if payload["safe"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

