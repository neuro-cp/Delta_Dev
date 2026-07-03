from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v21_localhost_review_ui import create_localhost_review_server, render_static_localhost_review_ui
from orchestration.runtime.v21_localhost_review_ui_report import write_localhost_review_ui_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or render DELTA localhost review UI prototype.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--render-static", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if args.output_report:
        print(json.dumps(write_localhost_review_ui_report(), indent=2))
        return 0
    if args.render_static:
        print(json.dumps(render_static_localhost_review_ui(), indent=2))
        return 0
    if args.serve:
        server = create_localhost_review_server()
        print(f"Serving DELTA review UI at http://127.0.0.1:{args.port}")
        server.serve_forever()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
