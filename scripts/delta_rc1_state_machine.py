"""Generate the RC1 unified review state machine report."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_unified_review_state_machine import write_state_machine_report


def main() -> None:
    payload = write_state_machine_report()
    lifecycle = payload["lifecycle"]
    print(f"final_recommendation={payload['final_recommendation']}")
    print(f"estimated_runtime_maturity={payload['estimated_runtime_maturity']}")
    print(f"current_state={lifecycle['current_state']}")
    print(f"transition_count={len(lifecycle['transitions'])}")
    print(f"integrated={lifecycle['integrated']}")


if __name__ == "__main__":
    main()
