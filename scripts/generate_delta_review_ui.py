from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v16_local_review_ui_report import write_local_review_ui_report  # noqa: E402


def main() -> int:
    data = write_local_review_ui_report()
    print(json.dumps({"dashboard_path": data["dashboard_path"], "ui_safe": data["ui_safe"], "items": len(data["items"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
