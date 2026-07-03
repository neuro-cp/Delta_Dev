from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v17_provider_evidence_review_ui_report import write_provider_evidence_review_ui_report


def main() -> int:
    data = write_provider_evidence_review_ui_report()
    print(f"evidence_review_ui={data['report_entry']['output_path']}")
    print(f"items={data['report_entry']['item_count']}")
    print(f"final_recommendation={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
