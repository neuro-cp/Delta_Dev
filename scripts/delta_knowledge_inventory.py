from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v15_knowledge_inventory_report import format_inventory_summary, write_knowledge_inventory_report  # noqa: E402


def main() -> int:
    data = write_knowledge_inventory_report(ROOT)
    print(format_inventory_summary(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
