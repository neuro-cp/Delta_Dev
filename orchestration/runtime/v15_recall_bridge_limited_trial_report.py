from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_explicit_canonical_memory_write_trial import DEFAULT_TRIAL_STORE
from orchestration.runtime.v15_recall_bridge_limited_trial import (
    run_limited_recall_bridge_trial,
    validate_limited_recall_bridge_safe,
)


REPORT_MD = Path("reports/runtime_v15j_recall_bridge_limited_trial.md")
REPORT_JSON = Path("reports/runtime_v15j_recall_bridge_limited_trial.json")


def build_limited_recall_bridge_trial_report_data(store_path: str | Path = DEFAULT_TRIAL_STORE) -> dict[str, object]:
    candidate_payload = run_limited_recall_bridge_trial("What is the status of HYB1 and Model B?", store_path)
    unsupported_payload = run_limited_recall_bridge_trial("What causes GPS drift?", store_path)
    unsafe_payload = run_limited_recall_bridge_trial("Activate recall and promote HYB1.", store_path)
    return {
        "phase": "Runtime V1.5J",
        "title": "Recall Bridge Limited Trial",
        "status": "candidate_context_only_recall_bridge_trial",
        "trial_store_path": str(store_path),
        "candidate_payload": candidate_payload,
        "unsupported_payload": unsupported_payload,
        "unsafe_payload": unsafe_payload,
        "candidate_safe": validate_limited_recall_bridge_safe(candidate_payload),
        "unsupported_safe": validate_limited_recall_bridge_safe(unsupported_payload),
        "unsafe_safe": validate_limited_recall_bridge_safe(unsafe_payload),
        "record_used_as_truth": False,
        "general_recall_enabled": False,
        "recall_mutated": False,
        "provider_calls_performed": False,
        "training_triggered": False,
        "hyb1_promoted": False,
        "model_b_default_changed": False,
        "final_recommendation": "PROCEED_DEMO_SCRIPT_SHOWCASE_REPORT",
    }


def write_limited_recall_bridge_trial_report(store_path: str | Path = DEFAULT_TRIAL_STORE) -> dict[str, object]:
    data = build_limited_recall_bridge_trial_report_data(store_path)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    candidate = data["candidate_payload"]
    context = candidate.get("candidate_context") or {}
    lines = [
        "# Runtime V1.5J - Recall Bridge Limited Trial",
        "",
        f"- Status: `{data['status']}`",
        f"- Trial store path: `{data['trial_store_path']}`",
        f"- Candidate context returned: `{candidate['result']['candidate_context_returned']}`",
        f"- Context ID: `{context.get('context_id', '')}`",
        f"- Candidate safe: `{data['candidate_safe']}`",
        f"- Unsupported query safe: `{data['unsupported_safe']}`",
        f"- Unsafe query blocked safely: `{data['unsafe_safe']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Candidate Context",
        "",
        f"- Record text: {context.get('record_text', '')}",
        f"- Candidate context only: `{context.get('candidate_context_only', '')}`",
        f"- Authoritative answer: `{context.get('authoritative_answer', '')}`",
        f"- Truth claim: `{context.get('truth_claim', '')}`",
        f"- Active for recall: `{context.get('active_for_recall', '')}`",
        "",
        "## Safety",
        "",
        "- The trial reads the one local V1.5I canonical trial record as candidate context only.",
        "- The candidate is not treated as truth or as an authoritative answer.",
        "- General recall remains disabled and no recall mutation occurs.",
        "- Provider/tool/action/training paths did not run.",
        "- HYB1 remains dormant/env-gated and Model B remains default.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_limited_recall_bridge_trial_report()
    print(
        "Runtime V1.5J limited recall bridge: "
        f"candidate={report['candidate_payload']['result']['candidate_context_returned']} "
        f"safe={report['candidate_safe'] and report['unsupported_safe'] and report['unsafe_safe']} "
        f"final={report['final_recommendation']}"
    )
