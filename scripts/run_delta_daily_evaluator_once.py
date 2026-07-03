from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v16_daily_evaluator_manual_run_hardening import (  # noqa: E402
    build_manual_evaluator_run_request,
    run_hardened_manual_evaluator,
)
from orchestration.runtime.v16_daily_evaluator_manual_run_hardening_report import write_manual_run_hardening_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one hardened DELTA evaluator pass.")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--show-request", action="store_true")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    if args.output_report:
        payload = write_manual_run_hardening_report(run_id=args.run_id, live=args.live, show_request=args.show_request)
    else:
        request = build_manual_evaluator_run_request(args.run_id, live=args.live, show_request=args.show_request)
        payload = run_hardened_manual_evaluator(request)
    output = payload["trial"]["request"] if args.show_request else payload
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
