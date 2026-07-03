from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v21_provider_live_trial_user_approved import run_user_approved_provider_live_trial
from orchestration.runtime.v21_provider_live_trial_user_approved_report import write_provider_live_trial_user_approved_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA user-approved provider live trial.")
    parser.add_argument("question", nargs="*", default=[])
    parser.add_argument("--live-provider", action="store_true")
    parser.add_argument("--approval-file", default="")
    parser.add_argument("--show-request", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    question = " ".join(args.question)
    if args.output_report and not args.live_provider:
        data = write_provider_live_trial_user_approved_report()
    else:
        approval = Path(args.approval_file).read_text(encoding="utf-8") if args.approval_file else ""
        data = run_user_approved_provider_live_trial(question, approval_text=approval, live_provider=args.live_provider)
    print(json.dumps(data["redacted_request"] if args.show_request else data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
