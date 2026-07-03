from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v24_provider_unknown_answer_ux_trial import run_provider_unknown_answer_ux_trial
from orchestration.runtime.v24_provider_unknown_answer_ux_trial_report import write_provider_unknown_answer_ux_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA provider unknown answer UX trial.")
    parser.add_argument("question", nargs="*")
    parser.add_argument("--approval-file")
    parser.add_argument("--live-provider", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    approval = Path(args.approval_file).read_text(encoding="utf-8") if args.approval_file else ""
    data = write_provider_unknown_answer_ux_report() if args.output_report else run_provider_unknown_answer_ux_trial(" ".join(args.question), approval_text=approval, live_provider=args.live_provider)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

