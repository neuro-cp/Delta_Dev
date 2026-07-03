from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v15_demo_showcase import build_runtime_demo_showcase, format_runtime_demo_showcase  # noqa: E402
from orchestration.runtime.v15_explicit_canonical_memory_write_trial import DEFAULT_TRIAL_STORE  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the DELTA Runtime V1.5K local demo showcase.")
    parser.add_argument("--store-path", default=str(DEFAULT_TRIAL_STORE))
    args = parser.parse_args()
    payload = build_runtime_demo_showcase(args.store_path)
    print(format_runtime_demo_showcase(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
