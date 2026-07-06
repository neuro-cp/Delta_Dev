from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp1_generalization_pilot import write_tp1_reports


def main() -> int:
    payload = write_tp1_reports()
    print(payload["final_recommendation"])
    print(f"tp1_status={payload['readiness_review']['tp1_status']}")
    print(f"generalization_delta={payload['heldout_benchmark']['generalization_delta']}")
    print(f"reasoning_delta={payload['cognitive_evolution']['reasoning_improvement']}")
    print(f"rollback_passed={payload['rollback']['passed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
