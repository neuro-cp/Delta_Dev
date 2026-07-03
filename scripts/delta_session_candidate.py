from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v19_session_to_memory_candidate import propose_session_memory_candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a review-only DELTA memory candidate proposal from a session summary.")
    parser.add_argument("summary")
    parser.add_argument("--session-id", default="default")
    args = parser.parse_args()
    print(json.dumps(propose_session_memory_candidate(args.summary, session_id=args.session_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
