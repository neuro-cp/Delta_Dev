"""Generate the RC1 read-only document-to-audit vertical slice report."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_document_audit_slice import write_document_audit_reports


def main() -> None:
    payload = write_document_audit_reports()
    print(f"final_recommendation={payload['final_recommendation']}")
    print(f"estimated_runtime_maturity={payload['estimated_runtime_maturity']}")
    print(f"fixture_paper_count={payload['fixture_paper_count']}")
    print(f"claim_count={len(payload['claims'])}")
    print(f"finding_count={len(payload['findings'])}")
    print(f"evidence_gap_count={len(payload['answer']['evidence_gaps'])}")


if __name__ == "__main__":
    main()
