"""Generate the RC1 adversarial validation reports."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_adversarial_validation import write_adversarial_validation_reports


def main() -> None:
    report = write_adversarial_validation_reports()
    print(f"final_recommendation={report['final_recommendation']}")
    print(f"runtime_maturity_estimate={report['runtime_maturity_estimate']}")
    print(f"scenario_count={report['scenario_count']}")
    print(f"passed_count={report['passed_count']}")
    print(f"failed_count={report['failed_count']}")


if __name__ == "__main__":
    main()
