from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v16_memory_candidate_review_loop_report import write_memory_candidate_review_loop_report  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(write_memory_candidate_review_loop_report(), indent=2))
