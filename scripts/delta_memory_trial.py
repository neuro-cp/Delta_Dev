from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v20_controlled_general_memory_trial import (
    list_controlled_general_memory_records,
    run_controlled_general_memory_trial,
)
from orchestration.runtime.v20_controlled_general_memory_trial_report import write_controlled_general_memory_trial_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA controlled general memory trial.")
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--candidate-text", default="Controlled memory trial candidate.")
    parser.add_argument("--approval-file", default="")
    parser.add_argument("--approval-text", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--list-records", action="store_true")
    parser.add_argument("--show-audit", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    if args.output_report:
        print(json.dumps(write_controlled_general_memory_trial_report(), indent=2))
        return 0
    if args.list_records:
        print(json.dumps({"records": list_controlled_general_memory_records()}, indent=2))
        return 0
    approval = args.approval_text
    if args.approval_file:
        approval = Path(args.approval_file).read_text(encoding="utf-8")
    candidate = {
        "candidate_id": args.candidate_id,
        "proposed_memory_text": args.candidate_text,
        "provenance_reference_ids": ["manual_cli"],
    }
    payload = run_controlled_general_memory_trial(candidate, approval, write=args.write and not args.dry_run)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
