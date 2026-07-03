from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v17_provider_assisted_unknown_answer import answer_unknown_with_controlled_provider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask DELTA through the controlled unknown-answer provider path.")
    parser.add_argument("question")
    parser.add_argument("--live-provider", action="store_true")
    parser.add_argument("--show-request", action="store_true")
    args = parser.parse_args()
    payload = answer_unknown_with_controlled_provider(args.question, live_provider=args.live_provider)
    print(json.dumps(payload["route_or_provider_request"] if args.show_request else payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
