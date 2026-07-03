from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v23_provider_live_to_candidate_trial import run_provider_live_to_candidate_trial
from orchestration.runtime.v23_provider_live_to_candidate_trial_report import write_provider_live_to_candidate_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA provider evidence to candidate trial.")
    parser.add_argument("question", nargs="*", default=["unknown topic"])
    parser.add_argument("--live-provider", action="store_true")
    parser.add_argument("--live-approval-file")
    parser.add_argument("--conversion-approval-file")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    live_approval = Path(args.live_approval_file).read_text(encoding="utf-8") if args.live_approval_file else ""
    conversion_approval = Path(args.conversion_approval_file).read_text(encoding="utf-8") if args.conversion_approval_file else ""
    data = write_provider_live_to_candidate_report() if args.output_report else run_provider_live_to_candidate_trial(" ".join(args.question), live_approval_text=live_approval, conversion_approval_text=conversion_approval, live_provider=args.live_provider)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

