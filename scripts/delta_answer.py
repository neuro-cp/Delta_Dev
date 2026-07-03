from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v23_recall_to_synthesis_integration import run_recall_to_synthesis
from orchestration.runtime.v23_recall_to_synthesis_integration_report import write_recall_to_synthesis_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA local answer synthesis.")
    parser.add_argument("query", nargs="*")
    parser.add_argument("--use-recall", action="store_true")
    parser.add_argument("--show-provenance", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    data = write_recall_to_synthesis_report() if args.output_report else run_recall_to_synthesis(" ".join(args.query), use_recall=args.use_recall)
    if args.json or args.show_provenance or args.output_report:
        print(json.dumps(data, indent=2))
    else:
        print(data["draft"]["answer_text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

