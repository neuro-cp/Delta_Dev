from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v17_local_session_state import add_local_session_turn, clear_local_session  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask DELTA with local ephemeral session state.")
    parser.add_argument("message", nargs="*", default=[])
    parser.add_argument("--session-id", default="default")
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()
    if args.clear:
        print(json.dumps({"cleared": clear_local_session(args.session_id)}, indent=2))
        return 0
    print(json.dumps(add_local_session_turn(args.session_id, " ".join(args.message)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
