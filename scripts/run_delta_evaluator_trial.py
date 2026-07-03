from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import (  # noqa: E402
    run_external_evaluator_api_trial,
)
from orchestration.runtime.v16_external_consolidation_evaluator_api_trial_report import (  # noqa: E402
    write_external_evaluator_api_trial_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the DELTA V1.6C external evaluator trial.")
    parser.add_argument("--live", action="store_true", help="Attempt one live evaluator call if env gates permit it.")
    parser.add_argument("--show-request", action="store_true", help="Print the redacted evaluator request.")
    parser.add_argument("--output-report", action="store_true", help="Write/update the V1.6C report.")
    args = parser.parse_args()

    payload = write_external_evaluator_api_trial_report(live=args.live) if args.output_report else run_external_evaluator_api_trial(live=args.live)
    output = payload["request"] if args.show_request else payload
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
