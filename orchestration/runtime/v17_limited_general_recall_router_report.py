from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v17_limited_general_recall_router import route_limited_general_recall, validate_limited_general_recall_safe


REPORT_MD = Path("reports/runtime_v17a_limited_general_recall_router_design.md")
REPORT_JSON = Path("reports/runtime_v17a_limited_general_recall_router_design.json")


def write_limited_general_recall_router_report() -> dict[str, object]:
    data = route_limited_general_recall("What is the status of HYB1 and Model B?")
    data["router_safe"] = validate_limited_general_recall_safe(data)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V1.7A - Limited General Recall Router Design\n\n"
        f"- Router safe: `{data['router_safe']}`\n"
        f"- Candidates: `{len(data['candidates'])}`\n"
        f"- Final recommendation: `{data['final_recommendation']}`\n\n"
        "Candidate-context only. No general recall activation, recall mutation, provider call, memory write, training, HYB1 promotion, or Model B change.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    report = write_limited_general_recall_router_report()
    print(f"Runtime V1.7A limited recall router: safe={report['router_safe']} candidates={len(report['candidates'])} final={report['final_recommendation']}")
