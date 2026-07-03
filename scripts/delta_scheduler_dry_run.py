from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v23_daily_evaluator_scheduled_dry_run_trial import run_scheduled_dry_run_trial
from orchestration.runtime.v23_daily_evaluator_scheduled_dry_run_trial_report import write_scheduled_dry_run_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA daily evaluator scheduler dry-run.")
    parser.add_argument("--approval-file")
    parser.add_argument("--write-artifact", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    approval = Path(args.approval_file).read_text(encoding="utf-8") if args.approval_file else ""
    data = write_scheduled_dry_run_report() if args.output_report else run_scheduled_dry_run_trial(approval_text=approval, write_artifact=args.write_artifact)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

