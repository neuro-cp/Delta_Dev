from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_wave_chain_summary import write_wave_chain_summary


if __name__ == "__main__":
    print(write_wave_chain_summary()["final_recommendation"])
