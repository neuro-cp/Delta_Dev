from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v15_explicit_canonical_memory_write_trial import (  # noqa: E402
    DEFAULT_TRIAL_STORE,
    execute_explicit_canonical_memory_write_trial,
)
from orchestration.runtime.v15_feedback_memory_candidate import build_feedback_memory_candidate_case  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one explicit-approval local canonical memory write trial.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--answer", required=True)
    parser.add_argument("--feedback", required=True)
    parser.add_argument("--approval", required=True)
    parser.add_argument("--store-path", default=str(DEFAULT_TRIAL_STORE))
    args = parser.parse_args()
    feedback_case = build_feedback_memory_candidate_case(args.question, args.answer, args.feedback)
    payload = execute_explicit_canonical_memory_write_trial(feedback_case["memory_candidate"], args.approval, args.store_path)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
