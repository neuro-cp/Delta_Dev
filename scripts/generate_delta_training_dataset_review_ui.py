"""Generate the static DELTA dataset review UI scaffold."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v26_training_dataset_review_ui import write_training_dataset_review_ui_report


if __name__ == "__main__":
    print(write_training_dataset_review_ui_report()["ui_path"])
