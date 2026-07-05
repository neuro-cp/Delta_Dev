from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_wave_7_learning_consolidation_pilot_plan import write_wave_7_report


if __name__ == "__main__":
    print(write_wave_7_report()["final_recommendation"])
