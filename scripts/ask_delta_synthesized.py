from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v17_controlled_answer_synthesis import synthesize_controlled_answer


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask DELTA through controlled answer synthesis.")
    parser.add_argument("question")
    args = parser.parse_args()
    print(json.dumps(synthesize_controlled_answer(args.question), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
