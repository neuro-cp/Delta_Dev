from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp16_tp30_master_marathon import PHASES, run_phase  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one DELTA TP16-TP30 phase.")
    parser.add_argument("phase", type=int, choices=sorted(PHASES))
    args = parser.parse_args()
    payload = run_phase(args.phase)
    print(json.dumps({
        "phase": payload["phase"],
        "title": payload["title"],
        "passed": payload["passed"],
        "recommendation": payload["recommendation"],
        "next_phase": payload["next_phase"],
        "hard_stop_required": payload["hard_stop_required"],
    }, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

