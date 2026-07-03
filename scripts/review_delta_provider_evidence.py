from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v18_provider_evidence_post_review_report import write_provider_evidence_post_review_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Review DELTA provider evidence as advisory-only.")
    parser.add_argument("question")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = write_provider_evidence_post_review_report(args.question)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"outcome={data['decision']['outcome']}")
        print(f"risk_count={data['report_entry']['risk_count']}")
        print(f"final_recommendation={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
