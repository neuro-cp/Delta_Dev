from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v21_controlled_general_memory_expansion import (
    check_expanded_memory_write_eligibility,
    list_expanded_memory_candidates,
    read_approval_file,
    run_expanded_memory_write_trial,
)
from orchestration.runtime.v21_controlled_general_memory_expansion_report import write_memory_expansion_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA controlled general memory expansion trial.")
    parser.add_argument("--list-candidates", action="store_true")
    parser.add_argument("--check-eligibility", default="")
    parser.add_argument("--approval-file", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    if args.output_report:
        print(json.dumps(write_memory_expansion_report(), indent=2))
        return 0
    if args.list_candidates:
        print(json.dumps({"candidates": list_expanded_memory_candidates()}, indent=2))
        return 0
    approval = read_approval_file(args.approval_file) if args.approval_file else ""
    if args.check_eligibility:
        print(json.dumps(check_expanded_memory_write_eligibility(args.check_eligibility, approval), indent=2))
        return 0
    print(json.dumps(run_expanded_memory_write_trial("memory-candidate-demo", approval, write=args.write and not args.dry_run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
