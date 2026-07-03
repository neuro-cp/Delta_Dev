from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v21_hyb1_reevaluation_report_only_report import write_hyb1_reevaluation_report


def main() -> int:
    print(json.dumps(write_hyb1_reevaluation_report(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
