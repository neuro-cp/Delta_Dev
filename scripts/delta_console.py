from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v19_local_delta_console import run_delta_console_command


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA local command-mode console.")
    parser.add_argument("command")
    parser.add_argument("argument", nargs="*", default=[])
    args = parser.parse_args()
    payload = run_delta_console_command(args.command, " ".join(args.argument))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
