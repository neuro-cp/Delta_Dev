from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v20_review_ui_write_approval_bridge_report import write_review_ui_write_approval_bridge_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate DELTA memory review approval bridge.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = write_review_ui_write_approval_bridge_report()
    print(json.dumps(data, indent=2) if args.json else f"ui={data['ui_path']} final={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
