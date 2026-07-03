from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v23_recall_to_synthesis_integration import run_recall_to_synthesis, validate_recall_to_synthesis_safe


REPORT_MD = Path("reports/runtime_v23c_controlled_recall_to_synthesis_integration.md")
REPORT_JSON = Path("reports/runtime_v23c_controlled_recall_to_synthesis_integration.json")


def write_recall_to_synthesis_report() -> dict[str, object]:
    cases = [run_recall_to_synthesis("What does DELTA know about HYB1?", use_recall=True), run_recall_to_synthesis("unknown topic", use_recall=True)]
    data = {"phase": "Runtime V2.3C", "cases": cases, "all_safe": all(validate_recall_to_synthesis_safe(case) for case in cases), "final_recommendation": "PROCEED_PROVIDER_EVIDENCE_LIVE_TO_CANDIDATE_TRIAL"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.3C - Controlled Recall-to-Synthesis Integration", "", "Recall candidate context may support local synthesis, but remains non-authoritative and non-mutating.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_recall_to_synthesis_report()
    print(f"Runtime V2.3C recall synthesis: safe={result['all_safe']} final={result['final_recommendation']}")

