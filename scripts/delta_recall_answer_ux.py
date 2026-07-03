from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v24_recall_answer_ux_trial import run_recall_answer_ux_trial
from orchestration.runtime.v24_recall_answer_ux_trial_report import write_recall_answer_ux_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA recall answer UX trial.")
    parser.add_argument("query", nargs="*")
    parser.add_argument("--no-recall", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    data = write_recall_answer_ux_report() if args.output_report else run_recall_answer_ux_trial(" ".join(args.query), use_recall=not args.no_recall)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

