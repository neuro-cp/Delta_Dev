from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v18_promotion_readiness_scorecard_report import write_promotion_readiness_scorecard_report


def main() -> int:
    data = write_promotion_readiness_scorecard_report()
    print(f"ready_for_human_review={data['report_entry']['ready_for_human_review_count']}")
    print(f"blocked={data['report_entry']['blocked_count']}")
    print(f"design_only={data['report_entry']['design_only_count']}")
    print(f"final_recommendation={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
