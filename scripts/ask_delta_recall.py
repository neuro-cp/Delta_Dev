from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v15_explicit_canonical_memory_write_trial import DEFAULT_TRIAL_STORE  # noqa: E402
from orchestration.runtime.v15_recall_bridge_limited_trial import run_limited_recall_bridge_trial  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask DELTA's limited V1.5J recall bridge for candidate context.")
    parser.add_argument("query")
    parser.add_argument("--store-path", default=str(DEFAULT_TRIAL_STORE))
    args = parser.parse_args()
    payload = run_limited_recall_bridge_trial(args.query, args.store_path)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
