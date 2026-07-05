from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_wave_2_readonly_retrieval import answer_fixture_question


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask the RC1 fixture corpus read-only.")
    parser.add_argument("question", nargs="*", default=["Why did the fixture system fail?"])
    args = parser.parse_args()
    report = answer_fixture_question(" ".join(args.question))
    print(report["answer"])
    print("evidence_ids=" + ",".join(report["evidence_ids"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
