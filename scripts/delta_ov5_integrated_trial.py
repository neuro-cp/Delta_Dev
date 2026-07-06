from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.ov5_integrated_readonly_cognitive_trial import write_ov5_reports


def main() -> int:
    payload = write_ov5_reports()
    print(payload["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
