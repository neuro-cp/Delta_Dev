from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v15_first_interaction import build_first_interaction_result, format_first_interaction_cli_output  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask DELTA through the V1.5D local console-only preview path.")
    parser.add_argument("message", nargs="*", help="One manual message. No listener, provider call, memory write, or action execution.")
    args = parser.parse_args()
    message = " ".join(args.message).strip()
    if not message:
        message = input("Message: ").strip()
    data = build_first_interaction_result(message)
    print(format_first_interaction_cli_output(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
