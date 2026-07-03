from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v23_hyb1_shadow_trial_simulation import run_hyb1_shadow_simulation
from orchestration.runtime.v23_hyb1_shadow_trial_simulation_report import write_hyb1_shadow_simulation_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA HYB1 shadow simulation.")
    parser.add_argument("prompt", nargs="*", default=["What does DELTA know about HYB1?"])
    parser.add_argument("--approval-file")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    approval = Path(args.approval_file).read_text(encoding="utf-8") if args.approval_file else ""
    data = write_hyb1_shadow_simulation_report() if args.output_report else run_hyb1_shadow_simulation(" ".join(args.prompt), approval_text=approval)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

