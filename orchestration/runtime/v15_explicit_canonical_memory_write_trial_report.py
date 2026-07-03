from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_explicit_canonical_memory_write_trial import (
    APPROVAL_APPROVED_BY,
    APPROVAL_HEADER,
    APPROVAL_SCOPE,
    DEFAULT_TRIAL_STORE,
    execute_explicit_canonical_memory_write_trial,
    validate_explicit_write_trial_safe,
)
from orchestration.runtime.v15_feedback_memory_candidate import build_feedback_memory_candidate_case


REPORT_MD = Path("reports/runtime_v15i_explicit_user_approved_canonical_memory_write_trial.md")
REPORT_JSON = Path("reports/runtime_v15i_explicit_user_approved_canonical_memory_write_trial.json")


def build_v15i_sample_memory_candidate() -> dict[str, object]:
    case = build_feedback_memory_candidate_case(
        "What is HYB1?",
        "HYB1 is active.",
        "No, HYB1 is not active. It is dormant and env-gated. Model B remains default.",
    )
    return dict(case["memory_candidate"])


def build_v15i_approval_text(memory_candidate_id: str) -> str:
    return "\n".join(
        [
            APPROVAL_HEADER,
            f"candidate_id={memory_candidate_id}",
            APPROVAL_APPROVED_BY,
            APPROVAL_SCOPE,
        ]
    )


def build_explicit_canonical_memory_write_trial_report_data(store_path: str | Path = DEFAULT_TRIAL_STORE) -> dict[str, object]:
    candidate = build_v15i_sample_memory_candidate()
    approval_text = build_v15i_approval_text(str(candidate["memory_candidate_id"]))
    success_payload = execute_explicit_canonical_memory_write_trial(candidate, approval_text, store_path)
    casual_payload = execute_explicit_canonical_memory_write_trial(candidate, "yeah, save it", Path(store_path).with_suffix(".blocked.jsonl"))
    return {
        "phase": "Runtime V1.5I",
        "title": "Explicit User-Approved Canonical Memory Write Trial",
        "status": "single_local_trial_record_written_with_explicit_approval_recall_inactive",
        "approval_format": "\n".join(
            [
                APPROVAL_HEADER,
                "candidate_id=<memory_candidate_id>",
                APPROVAL_APPROVED_BY,
                APPROVAL_SCOPE,
            ]
        ),
        "trial_store_path": str(store_path),
        "success_payload": success_payload,
        "casual_approval_payload": casual_payload,
        "success_safe": validate_explicit_write_trial_safe(success_payload),
        "casual_rejected": casual_payload["result"]["record_written"] is False,
        "final_recommendation": "PROCEED_RECALL_BRIDGE_LIMITED_TRIAL_DESIGN",
    }


def write_explicit_canonical_memory_write_trial_report(store_path: str | Path = DEFAULT_TRIAL_STORE) -> dict[str, object]:
    data = build_explicit_canonical_memory_write_trial_report_data(store_path)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    success = data["success_payload"]
    record = success["canonical_record"]
    result = success["result"]
    lines = [
        "# Runtime V1.5I - Explicit User-Approved Canonical Memory Write Trial",
        "",
        f"- Status: `{data['status']}`",
        f"- Trial store path: `{data['trial_store_path']}`",
        f"- Record written: `{result['record_written']}`",
        f"- Canonical record ID: `{result['canonical_record_id']}`",
        f"- Success safe: `{data['success_safe']}`",
        f"- Casual approval rejected: `{data['casual_rejected']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Required Approval Format",
        "",
        "```text",
        str(data["approval_format"]),
        "```",
        "",
        "## Written Trial Record",
        "",
        f"- Text: {record['record_text'] if record else ''}",
        f"- Active for recall: `{record['active_for_recall'] if record else ''}`",
        f"- General memory enabled: `{record['general_memory_enabled'] if record else ''}`",
        "",
        "## Safety",
        "",
        "- Provider/tool/action/training paths did not run.",
        "- Recall remains inactive.",
        "- HYB1 remains dormant/env-gated and Model B remains default.",
        "- Rollback reference was created but rollback was not executed.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_explicit_canonical_memory_write_trial_report()
    print(
        "Runtime V1.5I explicit write trial: "
        f"written={report['success_payload']['result']['record_written']} "
        f"safe={report['success_safe']} "
        f"casual_rejected={report['casual_rejected']} "
        f"final={report['final_recommendation']}"
    )
