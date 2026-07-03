from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v17_specialist_evidence_acquisition_trial import run_specialist_evidence_trial  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DELTA specialist evidence acquisition trial.")
    parser.add_argument("question")
    parser.add_argument("--domain", default="general")
    parser.add_argument("--live-specialist", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_specialist_evidence_trial(args.question, specialist_domain=args.domain, live_specialist=args.live_specialist), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
