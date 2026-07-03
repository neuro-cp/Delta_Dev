from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v17_limited_general_recall_trial import run_limited_general_recall_trial


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask DELTA through the limited general recall trial.")
    parser.add_argument("query")
    args = parser.parse_args()
    print(json.dumps(run_limited_general_recall_trial(args.query), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
