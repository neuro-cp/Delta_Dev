from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v20_provider_live_review_bridge_report import write_provider_live_review_bridge_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate DELTA provider evidence review bridge.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = write_provider_live_review_bridge_report()
    print(json.dumps(data, indent=2) if args.json else f"provider_report_present={data['provider_report_present']} final={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
