from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.tp2_scientific_validation import write_tp2_reports


def main() -> int:
    payload = write_tp2_reports()
    print(payload["final_recommendation"])
    print(f"tp2_status={payload['readiness']['tp2_status']}")
    print(f"corpora={payload['multi_corpus_generalization']['corpus_count']}")
    print(f"average_delta={payload['multi_corpus_generalization']['average_delta']}")
    print(f"evaluator_agreement={payload['blinded_evaluation']['agreement_score']}")
    print(f"rollback={payload['longitudinal_replay']['rollback_stability']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
