"""Generate DELTA Runtime V2.8 validation and hardening reports."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v28_validation_hardening import write_all_reports


def main() -> int:
    reports = write_all_reports(ROOT)
    print(f"wrote {len(reports)} V2.8 reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
