from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v17_provider_evidence_review_ui import write_evidence_review_ui


REPORT_MD = Path("reports/runtime_v17e_provider_specialist_evidence_review_ui.md")
REPORT_JSON = Path("reports/runtime_v17e_provider_specialist_evidence_review_ui.json")


def write_provider_evidence_review_ui_report() -> dict[str, object]:
    data = write_evidence_review_ui()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    entry = data["report_entry"]
    flags = data["safety_flags"]
    return "\n".join(
        [
            "# Runtime V1.7E - Provider / Specialist Evidence Review UI",
            "",
            f"- UI path: `{entry['output_path']}`",
            f"- Items: `{entry['item_count']}`",
            f"- All items non-authoritative: `{entry['all_items_non_authoritative']}`",
            f"- No live calls: `{entry['no_live_calls']}`",
            f"- Provider calls performed: `{flags['provider_call_performed']}`",
            f"- Specialist calls performed: `{flags['specialist_call_performed']}`",
            f"- Memory writes: `{flags['memory_write_performed']}`",
            f"- Recall mutation: `{flags['recall_mutated']}`",
            f"- Training: `{flags['training_triggered']}`",
            f"- Scheduler enabled: `{flags['scheduler_enabled']}`",
            f"- HYB1 promoted: `{flags['hyb1_promoted']}`",
            f"- Model B changed: `{flags['model_b_default_changed']}`",
            "",
            "Static review UI only. Provider, specialist, evaluator, and recall entries are evidence-only or advisory-only and not authority.",
            "",
            f"Final recommendation: `{data['final_recommendation']}`",
            "",
        ]
    )


if __name__ == "__main__":
    result = write_provider_evidence_review_ui_report()
    print(f"Runtime V1.7E evidence review UI: items={result['report_entry']['item_count']} final={result['final_recommendation']}")
