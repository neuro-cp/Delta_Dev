from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v16_canonical_memory_rollback_trial import execute_canonical_memory_rollback_trial  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a DELTA canonical trial rollback dry-run or exact approval marker.")
    parser.add_argument("--canonical-record-id", default="v15i-canonical-trial-record-f97e30a731f4638c")
    parser.add_argument("--approval", default="")
    parser.add_argument("--apply-marker", action="store_true")
    args = parser.parse_args()
    print(json.dumps(execute_canonical_memory_rollback_trial(args.canonical_record_id, args.approval, dry_run=not args.apply_marker), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
