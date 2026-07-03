from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v18_manual_provider_live_trial import run_provider_live_trial
from orchestration.runtime.v18_manual_provider_live_trial_report import write_provider_live_trial_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DELTA's manual provider one-shot trial path.")
    parser.add_argument("question")
    parser.add_argument("--show-request", action="store_true")
    parser.add_argument("--live-provider", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    data = write_provider_live_trial_report(args.question, live_provider=args.live_provider) if args.output_report else run_provider_live_trial(args.question, live_provider=args.live_provider)
    if args.show_request:
        print(json.dumps(data["trace"]["redacted_request"], indent=2))
    else:
        print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
