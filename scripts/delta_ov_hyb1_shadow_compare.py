from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.ov_hyb1_shadow_comparison import write_ov_hyb1_shadow_comparison_reports


def main() -> int:
    payload = write_ov_hyb1_shadow_comparison_reports()
    summary = payload["summary"]
    print(f"recommendation={payload['final_recommendation']}")
    print(f"exact_payload_match={summary['exact_payload_match']}")
    print(f"hyb1_effective_output_change={summary['hyb1_effective_output_change']}")
    print(f"model_b_default_changed={summary['model_b_default_changed']}")
    print(f"hyb1_promoted={summary['hyb1_promoted']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
