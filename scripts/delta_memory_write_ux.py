from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v24_memory_write_ux_trial import run_memory_write_ux_trial
from orchestration.runtime.v24_memory_write_ux_trial_report import write_memory_write_ux_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA memory write UX trial.")
    parser.add_argument("--candidate-id", default="memory-candidate-demo")
    parser.add_argument("--approval-file")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    approval = Path(args.approval_file).read_text(encoding="utf-8") if args.approval_file else ""
    candidate = {"candidate_id": args.candidate_id, "proposed_memory_text": "Model B remains default.", "provenance_reference_ids": ["v24b-script"]}
    data = write_memory_write_ux_report() if args.output_report else run_memory_write_ux_trial(candidate, approval, write=args.write)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

