from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v23_localhost_write_execution_bridge import run_localhost_write_execution_bridge
from orchestration.runtime.v23_localhost_write_execution_bridge_report import write_localhost_write_execution_bridge_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA localhost UI write execution bridge.")
    parser.add_argument("--approval-file")
    parser.add_argument("--candidate-id", default="memory-candidate-demo")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--show-result", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    approval = Path(args.approval_file).read_text(encoding="utf-8") if args.approval_file else ""
    candidate = {"candidate_id": args.candidate_id, "proposed_memory_text": "Model B remains default.", "provenance_reference_ids": ["ui-write-bridge"]}
    data = write_localhost_write_execution_bridge_report() if args.output_report else run_localhost_write_execution_bridge(candidate, approval, write=args.write and not args.dry_run)
    print(json.dumps(data, indent=2) if args.show_result or args.output_report else f"outcome={data['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

