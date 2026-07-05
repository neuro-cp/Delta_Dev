from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_wave_1_fixture_corpus_ingestion import ingest_fixture_corpus


def main() -> int:
    parser = argparse.ArgumentParser(description="RC1 fixture-only corpus ingestion.")
    parser.add_argument("--input", default="data/rc1_fixture_corpus")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    report = ingest_fixture_corpus(args.input, args.output)
    print(f"record_count={report['record_count']}")
    print(f"final_recommendation={report['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
