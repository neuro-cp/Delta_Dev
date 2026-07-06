from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.ov6_ov10_operational_readiness import write_ov6_ov10_reports


def main() -> int:
    payload = write_ov6_ov10_reports()
    print(payload["final_recommendation"])
    print(f"operational_readiness_score={payload['operational_readiness_score']}")
    print(f"training_readiness_assessment={payload['training_readiness_assessment']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
