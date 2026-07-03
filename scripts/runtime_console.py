from __future__ import annotations

import argparse
import json

from orchestration.runtime.v14_runtime_console import build_runtime_console_preview


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual DELTA runtime console preview. Review-only; no mutation.")
    parser.add_argument("message", nargs="*", help="Manual user message to preview.")
    parser.add_argument("--source-reference", default="manual-cli-console", help="Review-only source reference.")
    args = parser.parse_args()
    message = " ".join(args.message).strip()
    if not message:
        message = input("Message: ").strip()
    preview = build_runtime_console_preview(message, source_reference=args.source_reference)
    print(json.dumps(preview.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
