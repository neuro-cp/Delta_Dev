from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v18_manual_provider_live_trial_gate_report import write_provider_live_trial_gate_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DELTA's manual provider live trial gate.")
    parser.add_argument("question")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = write_provider_live_trial_gate_report(args.question)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"decision={data['decision']['status']}")
        print(f"requirements={data['report_entry']['passed_requirements']}/{data['report_entry']['total_requirements']}")
        print(f"final_recommendation={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
