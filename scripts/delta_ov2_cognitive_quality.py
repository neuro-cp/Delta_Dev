from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.ov2_cognitive_quality import write_ov2_reports


if __name__ == "__main__":
    print(write_ov2_reports()["final_recommendation"])
