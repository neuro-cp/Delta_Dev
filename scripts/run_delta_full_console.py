from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v24_localhost_full_review_console import build_full_console_snapshot, write_static_full_console_snapshot
from orchestration.runtime.v24_localhost_full_review_console_report import write_full_console_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA full localhost review console.")
    parser.add_argument("--render-static", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    data = write_full_console_report() if args.output_report else (write_static_full_console_snapshot() if args.render_static else build_full_console_snapshot())
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

