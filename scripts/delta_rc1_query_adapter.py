"""Generate the RC1 read-only substrate query adapter report."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_substrate_query_adapter import write_query_adapter_report


def main() -> None:
    payload = write_query_adapter_report()
    print(f"final_recommendation={payload['final_recommendation']}")
    print(f"estimated_runtime_maturity={payload['estimated_runtime_maturity']}")
    print(f"packet_count={len(payload['packets'])}")
    print(f"result_count={sum(len(packet['results']) for packet in payload['packets'])}")


if __name__ == "__main__":
    main()
