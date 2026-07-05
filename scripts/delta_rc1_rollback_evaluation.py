from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_wave_4_rollback_evaluation import write_wave_4_report


if __name__ == "__main__":
    print(write_wave_4_report()["final_recommendation"])
