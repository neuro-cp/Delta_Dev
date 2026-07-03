"""Run DELTA deterministic redaction trial."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v26_dataset_redaction_trial import write_dataset_redaction_trial_report


if __name__ == "__main__":
    print(write_dataset_redaction_trial_report()["final_recommendation"])
