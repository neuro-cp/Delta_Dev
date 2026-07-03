from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v18_review_ui_evidence_quality_iteration_report import write_quality_review_ui_report


def main() -> int:
    data = write_quality_review_ui_report()
    print(f"quality_review_ui={data['report_entry']['output_path']}")
    print(f"final_recommendation={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
