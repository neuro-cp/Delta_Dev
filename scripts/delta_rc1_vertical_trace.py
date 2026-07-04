"""Generate the DELTA RC1 vertical integration trace reports."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_vertical_integration import write_rc1_reports


def main() -> None:
    payload = write_rc1_reports()
    print(f"final_recommendation={payload['final_recommendation']}")
    print(f"estimated_runtime_maturity={payload['scorecard']['estimated_runtime_maturity']}")
    print(f"trace_steps={len(payload['trace_steps'])}")
    print(f"lifecycle_owners={len(payload['lifecycle_owners'])}")
    print(f"kernel_routed={payload['scorecard']['kernel_routed']}")
    print(f"transaction_wrapped={payload['scorecard']['transaction_wrapped']}")
    print(f"audit_graph_linked={payload['scorecard']['audit_graph_linked']}")


if __name__ == "__main__":
    main()
