from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v22_evaluator_assisted_memory_candidate_review import EvaluatorCandidateReviewInput, review_memory_candidate_with_evaluator
from orchestration.runtime.v22_evaluator_assisted_memory_candidate_review_report import write_evaluator_candidate_review_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local advisory evaluator review for a memory candidate.")
    parser.add_argument("--candidate-id", default="candidate-demo")
    parser.add_argument("--text", default="Reviewed candidate.")
    parser.add_argument("--provenance", default="manual_cli")
    parser.add_argument("--ambiguity", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    if args.output_report:
        print(json.dumps(write_evaluator_candidate_review_report(), indent=2))
        return 0
    candidate = EvaluatorCandidateReviewInput(args.candidate_id, args.text, (args.provenance,), ambiguity_flag=args.ambiguity)
    print(json.dumps(review_memory_candidate_with_evaluator(candidate), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
