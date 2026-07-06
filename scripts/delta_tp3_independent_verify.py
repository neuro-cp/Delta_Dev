from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp3_independent_verification_freeze import (  # noqa: E402
    verify_freeze_package,
    write_tp3_reports,
)


def main() -> int:
    write_tp3_reports()
    result = verify_freeze_package()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
