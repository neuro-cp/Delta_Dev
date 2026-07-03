from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v24_evaluator_consolidation_ux_trial import run_evaluator_consolidation_ux_trial
from orchestration.runtime.v24_evaluator_consolidation_ux_trial_report import write_evaluator_consolidation_ux_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA evaluator consolidation UX trial.")
    parser.add_argument("--candidate-id", default="candidate-demo")
    parser.add_argument("--text", default="Model B remains default.")
    parser.add_argument("--ambiguity", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    candidate = {"candidate_id": args.candidate_id, "candidate_text": args.text, "provenance_reference_ids": ["v24e-script"], "ambiguity_flag": args.ambiguity}
    data = write_evaluator_consolidation_ux_report() if args.output_report else run_evaluator_consolidation_ux_trial(candidate)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

