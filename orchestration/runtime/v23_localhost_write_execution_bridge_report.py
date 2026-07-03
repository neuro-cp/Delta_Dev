from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v23_localhost_write_execution_bridge import run_localhost_write_execution_bridge, validate_localhost_write_execution_bridge_safe


REPORT_MD = Path("reports/runtime_v23b_localhost_ui_candidate_write_execution_bridge.md")
REPORT_JSON = Path("reports/runtime_v23b_localhost_ui_candidate_write_execution_bridge.json")
APPROVAL = "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE\ncandidate_id=memory-candidate-demo\napproved_by=user\napproval_scope=single_memory_candidate_only\napproval_source=localhost_review_ui"


def write_localhost_write_execution_bridge_report() -> dict[str, object]:
    candidate = {"candidate_id": "memory-candidate-demo", "proposed_memory_text": "Model B remains default.", "provenance_reference_ids": ["v23b-demo"]}
    cases = [run_localhost_write_execution_bridge(candidate, "", write=False), run_localhost_write_execution_bridge(candidate, APPROVAL, write=False)]
    data = {"phase": "Runtime V2.3B", "cases": cases, "all_safe": all(validate_localhost_write_execution_bridge_safe(case) for case in cases), "final_recommendation": "PROCEED_CONTROLLED_RECALL_TO_SYNTHESIS_INTEGRATION"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.3B - Localhost UI Candidate Write Execution Bridge", "", "The bridge invokes controlled memory trial logic only after an exact localhost approval event. It is dry-run by default.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_localhost_write_execution_bridge_report()
    print(f"Runtime V2.3B localhost write bridge: safe={result['all_safe']} final={result['final_recommendation']}")

