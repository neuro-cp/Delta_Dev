from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc2_conversation_pathology_harness import write_conversation_pathology_reports  # noqa: E402


def main() -> int:
    report = write_conversation_pathology_reports(count=100)
    summary = {
        "question_count": report["question_count"],
        "recommendation": report["readiness_gate"]["recommendation"],
        "persistent_cognitive_store_enabled": report["persistent_cognitive_store_enabled"],
        "pathology_counts": report["pathology_counts"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
