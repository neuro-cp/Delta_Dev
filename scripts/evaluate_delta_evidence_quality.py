from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v18_evidence_quality_evaluation_report import write_evidence_quality_evaluation_report


def main() -> int:
    data = write_evidence_quality_evaluation_report()
    print(f"average_score={data['report_entry']['average_score']}")
    print(f"all_safe={data['all_safe']}")
    print(f"final_recommendation={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
