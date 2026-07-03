"""Report DELTA feature activation gate console state."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v26_feature_activation_gate_console import write_feature_activation_gate_console_report


if __name__ == "__main__":
    print(write_feature_activation_gate_console_report()["final_recommendation"])
