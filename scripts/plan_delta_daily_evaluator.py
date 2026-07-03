from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v16_scheduled_daily_evaluator_design_report import (  # noqa: E402
    write_scheduled_daily_evaluator_design_report,
)


def main() -> int:
    data = write_scheduled_daily_evaluator_design_report()
    print(json.dumps({"plan_safe": data["plan_safe"], "manual_run_command": data["plan"]["manual_run_command"]["command_text"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
