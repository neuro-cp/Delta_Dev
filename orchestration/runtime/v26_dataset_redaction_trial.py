"""Runtime V2.6B deterministic dataset redaction trial."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPORT_MD = Path("reports/runtime_v26b_dataset_redaction_pii_scrub_trial.md")
REPORT_JSON = Path("reports/runtime_v26b_dataset_redaction_pii_scrub_trial.json")


def redact_text(text: str) -> str:
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b(?:\d[ -]?){13,16}\b", "[REDACTED_NUMBER]", text)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)
    return text


def build_dataset_redaction_trial() -> dict[str, object]:
    fixtures = [
        "Contact person@example.com about DELTA.",
        "Card 4111 1111 1111 1111 must not enter training.",
        "SSN 123-45-6789 is forbidden.",
    ]
    redacted = [redact_text(item) for item in fixtures]
    return {
        "phase": "Runtime V2.6B",
        "mode": "redaction_trial_only",
        "fixtures": redacted,
        "redactions_applied": sum("[REDACTED_" in item for item in redacted),
        "safety_invariants": _safe_flags(),
        "final_recommendation": "PROCEED_TRAINING_JOB_PLAN_DESIGN_NO_EXECUTION",
    }


def validate_dataset_redaction_trial_safe(data: dict[str, object]) -> bool:
    return data["redactions_applied"] == 3 and all(value is False for value in data["safety_invariants"].values())


def write_dataset_redaction_trial_report() -> dict[str, object]:
    data = build_dataset_redaction_trial()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _safe_flags() -> dict[str, bool]:
    return {
        "training_performed": False,
        "dataset_exported": False,
        "provider_call_performed": False,
        "memory_write_performed": False,
        "model_artifact_created": False,
    }


def _render(data: dict[str, object]) -> str:
    return f"# {data['phase']} Dataset Redaction Trial\n\nMode: {data['mode']}\n\nRedactions applied: {data['redactions_applied']}\n\nFinal recommendation: {data['final_recommendation']}\n"


if __name__ == "__main__":
    print(write_dataset_redaction_trial_report()["final_recommendation"])
