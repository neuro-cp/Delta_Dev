from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp0_controlled_training_pilot import write_tp0_reports


def main() -> int:
    payload = write_tp0_reports()
    print(payload["final_recommendation"])
    print(f"tp0_status={payload['training_readiness_review']['tp0_status']}")
    print(f"before_cognitive_integrity={payload['before_after_evaluation']['before']['cognitive_integrity']}")
    print(f"after_cognitive_integrity={payload['before_after_evaluation']['after']['cognitive_integrity']}")
    print(f"rollback_passed={payload['rollback_result']['passed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
