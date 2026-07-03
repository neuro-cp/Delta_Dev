"""Generate the DELTA V2.7E full local demo report."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v27_full_local_demo import write_full_local_demo_report


if __name__ == "__main__":
    print(write_full_local_demo_report()["final_recommendation"])
