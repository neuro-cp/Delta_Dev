"""Generate the RC1 runtime artifact registry report."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_runtime_artifact_registry import write_artifact_registry_report


def main() -> None:
    payload = write_artifact_registry_report()
    print(f"final_recommendation={payload['final_recommendation']}")
    print(f"estimated_runtime_maturity={payload['estimated_runtime_maturity']}")
    print(f"artifact_count={payload['artifact_count']}")
    print(f"missing_artifacts={len(payload['missing_artifacts'])}")
    print(f"consumerless_artifacts={len(payload['consumerless_artifacts'])}")


if __name__ == "__main__":
    main()
