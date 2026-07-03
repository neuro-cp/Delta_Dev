from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v22_localhost_ui_mutation_bridge import LocalhostUIEventKind, run_ui_mutation_bridge
from orchestration.runtime.v22_localhost_ui_mutation_bridge_report import write_ui_mutation_bridge_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA localhost UI mutation bridge export tool.")
    parser.add_argument("candidate_id", nargs="?", default="memory-candidate-demo")
    parser.add_argument("--event", choices=[item.value for item in LocalhostUIEventKind], default="approve")
    parser.add_argument("--write-export", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    if args.output_report:
        print(json.dumps(write_ui_mutation_bridge_report(), indent=2))
        return 0
    payload = run_ui_mutation_bridge(args.candidate_id, LocalhostUIEventKind(args.event), dry_run=not args.write_export)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
