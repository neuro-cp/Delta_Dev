from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v17_local_session_state import add_local_session_turn, clear_local_session, validate_local_session_safe


REPORT_MD = Path("reports/runtime_v17b_local_multi_turn_session_state.md")
REPORT_JSON = Path("reports/runtime_v17b_local_multi_turn_session_state.json")


def write_local_session_state_report() -> dict[str, object]:
    session_id = "v17b-report-session"
    clear_local_session(session_id)
    first = add_local_session_turn(session_id, "What is Model B?")
    second = add_local_session_turn(session_id, "Is HYB1 active?")
    data = {"phase": "Runtime V1.7B", "first": first, "second": second, "all_safe": validate_local_session_safe(first) and validate_local_session_safe(second), "final_recommendation": "PROCEED_CONTROLLED_PROVIDER_ASSISTED_UNKNOWN_ANSWER_PATH"}
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V1.7B - Local Multi-Turn Session State\n\n"
        f"- All safe: `{data['all_safe']}`\n"
        f"- Turns: `{len(second['session']['turns'])}`\n"
        f"- Final recommendation: `{data['final_recommendation']}`\n\n"
        "Session state is local, ephemeral, and non-canonical. No provider calls, memory writes, recall mutation, training, or actions.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    report = write_local_session_state_report()
    print(f"Runtime V1.7B local session state: safe={report['all_safe']} final={report['final_recommendation']}")
