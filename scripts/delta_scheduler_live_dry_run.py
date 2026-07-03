"""Run the DELTA V2.5E scheduler live dry-run audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v25_scheduler_live_dry_run_trial import (
    APPROVAL_TEXT,
    run_scheduler_live_dry_run_trial,
    write_scheduler_live_dry_run_trial_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", action="store_true", help="Use the exact scheduler dry-run approval text.")
    parser.add_argument("--write-audit", action="store_true", help="Write the dry-run audit artifact.")
    parser.add_argument("--audit-path", default=None)
    args = parser.parse_args()
    data = (
        run_scheduler_live_dry_run_trial(
            approval_text=APPROVAL_TEXT,
            env={"DELTA_SCHEDULER_LIVE_DRY_RUN_ENABLED": "true"},
            write_audit=args.write_audit,
            audit_path=Path(args.audit_path) if args.audit_path else None,
        )
        if args.approve
        else write_scheduler_live_dry_run_trial_report()
    )
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
