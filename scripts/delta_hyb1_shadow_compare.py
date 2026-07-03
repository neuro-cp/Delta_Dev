"""Run the DELTA V2.5D HYB1 shadow comparison report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v25_hyb1_shadow_live_comparison import (
    APPROVAL_TEXT,
    run_hyb1_shadow_live_comparison,
    write_hyb1_shadow_live_comparison_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", action="store_true", help="Use the exact shadow comparison approval text.")
    args = parser.parse_args()
    data = (
        run_hyb1_shadow_live_comparison(approval_text=APPROVAL_TEXT)
        if args.approve
        else write_hyb1_shadow_live_comparison_report()
    )
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
