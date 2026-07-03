from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


APPROVAL_TEXT = "APPROVE_TRAINING_DATASET_EXPORT_TRIAL\napproved_by=user\nexport_scope=small_review_dataset_only"
DEFAULT_EXPORT_PATH = Path("data/runtime_v25c/training_dataset_export_trial.jsonl")
DEFAULT_AUDIT_PATH = Path("data/runtime_v25c/training_dataset_export_audit.jsonl")
REPORT_MD = Path("reports/runtime_v25c_controlled_training_dataset_export_trial.md")
REPORT_JSON = Path("reports/runtime_v25c_controlled_training_dataset_export_trial.json")


def parse_dataset_export_approval(text: str) -> dict[str, object]:
    normalized = _normalize(text)
    return {"approval_present": bool(normalized), "matches_required_shape": normalized == _normalize(APPROVAL_TEXT)}


def redact_dataset_text(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w.-]+", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_NUMBER]", text)
    return text


def run_training_dataset_export_trial(
    approval_text: str = "",
    *,
    export: bool = False,
    export_path: str | Path = DEFAULT_EXPORT_PATH,
    audit_path: str | Path = DEFAULT_AUDIT_PATH,
) -> dict[str, object]:
    approval = parse_dataset_export_approval(approval_text)
    eligible = [
        {
            "example_id": "v25c-example-1",
            "input": "What does DELTA know about HYB1?",
            "output": "HYB1 remains dormant/env-gated and Model B remains default.",
            "provenance": ["runtime_v24_summary"],
            "reviewed": True,
            "approved": True,
        },
        {
            "example_id": "v25c-example-2",
            "input": "Contact test@example.com about DELTA.",
            "output": "Email should be redacted before export.",
            "provenance": ["redaction_fixture"],
            "reviewed": True,
            "approved": True,
        },
    ]
    redacted = [{**item, "input": redact_dataset_text(item["input"]), "output": redact_dataset_text(item["output"])} for item in eligible]
    written = False
    if export and approval["matches_required_shape"]:
        target = Path(export_path)
        audit = Path(audit_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        audit.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(json.dumps(item, sort_keys=True) for item in redacted) + "\n", encoding="utf-8")
        audit.write_text(json.dumps({"audit_id": _stable_id("v25c-audit", len(redacted)), "record_count": len(redacted), "training_performed": False}, sort_keys=True) + "\n", encoding="utf-8")
        written = True
    return {
        "phase": "Runtime V2.5C",
        "approval": approval,
        "eligible_count": len(eligible),
        "redacted_examples": redacted,
        "decision": {
            "dataset_exported": written,
            "training_performed": False,
            "model_artifact_created": False,
            "provider_call_performed": False,
            "scheduler_started": False,
        },
        "invariant_flags": {
            "dataset_export_trial_enabled": True,
            "dry_run_default": True,
            "exact_approval_required": True,
            "training_performed": False,
            "model_artifact_created": False,
            "model_b_default_changed": False,
            "hyb1_promoted": False,
        },
        "final_recommendation": "PROCEED_HYB1_SHADOW_TRIAL_LIVE_COMPARISON",
    }


def validate_dataset_export_trial_safe(data: dict[str, object]) -> bool:
    flags = data["invariant_flags"]
    return data["decision"]["training_performed"] is False and data["decision"]["model_artifact_created"] is False and flags["dataset_export_trial_enabled"] and flags["dry_run_default"] and flags["exact_approval_required"] and all(
        value is False for key, value in flags.items() if key not in {"dataset_export_trial_enabled", "dry_run_default", "exact_approval_required"}
    )


def write_training_dataset_export_trial_report() -> dict[str, object]:
    data = run_training_dataset_export_trial()
    data["approved_dry_run"] = run_training_dataset_export_trial(APPROVAL_TEXT, export=False)
    data["all_safe"] = validate_dataset_export_trial_safe(data) and validate_dataset_export_trial_safe(data["approved_dry_run"])
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.5C - Controlled Training Dataset Export Trial", "", "Dataset export is exact-approval gated and does not train or create model artifacts.", "", f"Eligible examples: `{data['eligible_count']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


if __name__ == "__main__":
    result = write_training_dataset_export_trial_report()
    print(f"Runtime V2.5C dataset export: safe={result['all_safe']} final={result['final_recommendation']}")

