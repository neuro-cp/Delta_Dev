from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v21_hyb1_reevaluation_report_only import reevaluate_hyb1_report_only, validate_hyb1_reevaluation_safe


REPORT_MD = Path("reports/runtime_v21e_hyb1_reevaluation_report_only.md")
REPORT_JSON = Path("reports/runtime_v21e_hyb1_reevaluation_report_only.json")


def write_hyb1_reevaluation_report() -> dict[str, object]:
    payload = reevaluate_hyb1_report_only()
    data = {**payload, "all_safe": validate_hyb1_reevaluation_safe(payload)}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.1E - HYB1 Re-evaluation, Report-Only",
        "",
        "HYB1 was re-evaluated as a dormant/env-gated candidate only. No activation, promotion, or routing default change occurred.",
        "",
        f"Recommendation: `{data['recommendation']}`",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_hyb1_reevaluation_report()
    print(f"Runtime V2.1E HYB1 re-evaluation: safe={result['all_safe']} recommendation={result['recommendation']}")
