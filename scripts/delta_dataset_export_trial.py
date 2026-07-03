"""Run the DELTA V2.5C controlled dataset export trial."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v25_training_dataset_export_trial import (
    APPROVAL_TEXT,
    run_training_dataset_export_trial,
    write_training_dataset_export_trial_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", action="store_true", help="Use the exact trial approval text.")
    parser.add_argument("--export", action="store_true", help="Write the small review dataset artifact.")
    parser.add_argument("--export-path", default=None)
    parser.add_argument("--audit-path", default=None)
    args = parser.parse_args()

    if args.export:
        data = run_training_dataset_export_trial(
            approval_text=APPROVAL_TEXT if args.approve else "",
            export=True,
            export_path=Path(args.export_path) if args.export_path else None,
            audit_path=Path(args.audit_path) if args.audit_path else None,
        )
    else:
        data = write_training_dataset_export_trial_report()

    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
