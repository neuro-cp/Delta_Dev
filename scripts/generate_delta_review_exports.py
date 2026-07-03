from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v16_review_ui_export_flow_report import write_review_ui_export_flow_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate text-only DELTA review exports.")
    parser.add_argument("--candidate-id", default="memory-candidate-60ee56fb323e53de")
    args = parser.parse_args()
    print(json.dumps(write_review_ui_export_flow_report(args.candidate_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
