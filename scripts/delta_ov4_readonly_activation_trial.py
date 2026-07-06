from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.ov4_readonly_activation_trial import write_ov4_reports


if __name__ == "__main__":
    print(write_ov4_reports()["final_recommendation"])
