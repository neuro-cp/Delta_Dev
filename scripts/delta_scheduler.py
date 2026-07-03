from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v21_daily_evaluator_scheduler_activation import (
    activate_scheduler_local_artifact,
    build_scheduler_activation_plan,
    build_scheduler_disable_plan,
    verify_scheduler_gates,
)
from orchestration.runtime.v21_daily_evaluator_scheduler_activation_report import write_scheduler_activation_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA daily evaluator scheduler gated local trial.")
    parser.add_argument("command", choices=["status", "plan", "activate-dry-run", "activate-local-artifact", "disable-plan", "verify-gates"])
    parser.add_argument("--approval-file", default="")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    approval = Path(args.approval_file).read_text(encoding="utf-8") if args.approval_file else ""
    if args.output_report:
        data = write_scheduler_activation_report()
    elif args.command == "status":
        data = {"scheduler": "disabled_by_default", "os_task_registered": False, "background_worker_started": False}
    elif args.command == "plan":
        data = build_scheduler_activation_plan()
    elif args.command == "activate-dry-run":
        data = activate_scheduler_local_artifact(approval, dry_run=True)
    elif args.command == "activate-local-artifact":
        data = activate_scheduler_local_artifact(approval, dry_run=True)
    elif args.command == "disable-plan":
        data = build_scheduler_disable_plan()
    else:
        data = verify_scheduler_gates(approval_text=approval)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
