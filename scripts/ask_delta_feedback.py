from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v15_feedback_memory_candidate import build_feedback_memory_candidate_case  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a review-only DELTA feedback -> memory candidate proposal.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--answer", required=True)
    parser.add_argument("--feedback", required=True)
    args = parser.parse_args()
    case = build_feedback_memory_candidate_case(args.question, args.answer, args.feedback)
    print(json.dumps(case, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
