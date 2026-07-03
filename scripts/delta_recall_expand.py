from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v22_controlled_general_recall_expansion import run_controlled_general_recall_expansion
from orchestration.runtime.v22_controlled_general_recall_expansion_report import write_recall_expansion_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA controlled general recall expansion.")
    parser.add_argument("query", nargs="*", default=[])
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--show-provenance", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--explain-ranking", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    query = " ".join(args.query)
    data = write_recall_expansion_report() if args.output_report else run_controlled_general_recall_expansion(query, max_candidates=args.max_candidates, explain_ranking=args.explain_ranking)
    if args.json or args.show_provenance or args.explain_ranking or args.output_report:
        print(json.dumps(data, indent=2))
    else:
        print(f"candidates={data['candidate_count']} final={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
