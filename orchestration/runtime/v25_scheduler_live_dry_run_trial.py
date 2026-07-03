from __future__ import annotations

import hashlib
import json
from pathlib import Path


APPROVAL_TEXT = "APPROVE_SCHEDULER_LIVE_DRY_RUN_TRIAL\napproved_by=user\nschedule_scope=daily_evaluator_dry_run_only"
DEFAULT_AUDIT_PATH = Path("data/runtime_v25e/scheduler_live_dry_run_audit.jsonl")
REPORT_MD = Path("reports/runtime_v25e_scheduler_live_dry_run_trial_user_approved.md")
REPORT_JSON = Path("reports/runtime_v25e_scheduler_live_dry_run_trial_user_approved.json")


def run_scheduler_live_dry_run_trial(approval_text: str = "", *, env: dict[str, str] | None = None, write_audit: bool = False, audit_path: str | Path = DEFAULT_AUDIT_PATH) -> dict[str, object]:
    env = env or {}
    approved = _normalize(approval_text) == _normalize(APPROVAL_TEXT)
    permitted = approved and env.get("DELTA_SCHEDULER_LIVE_DRY_RUN_ENABLED", "").lower() == "true"
    audit = {"audit_id": _stable_id("v25e-audit", permitted), "simulated": True, "os_task_registered": False, "background_worker_started": False}
    if permitted and write_audit:
        path = Path(audit_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(audit, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "phase": "Runtime V2.5E",
        "approval": {"matches_required_shape": approved},
        "gate": {"permitted": permitted},
        "audit": audit,
        "decision": {"os_task_registered": False, "cron_entry_created": False, "windows_task_created": False, "background_worker_started": False, "api_call_performed": False, "memory_write_performed": False, "training_performed": False},
        "final_recommendation": "PROCEED_V25_SAFETY_CHECKPOINT",
    }


def validate_scheduler_live_dry_run_safe(data: dict[str, object]) -> bool:
    return all(value is False for value in data["decision"].values())


def write_scheduler_live_dry_run_trial_report() -> dict[str, object]:
    cases = [run_scheduler_live_dry_run_trial(), run_scheduler_live_dry_run_trial(APPROVAL_TEXT, env={"DELTA_SCHEDULER_LIVE_DRY_RUN_ENABLED": "true"})]
    data = {"phase": "Runtime V2.5E", "cases": cases, "all_safe": all(validate_scheduler_live_dry_run_safe(case) for case in cases), "final_recommendation": "PROCEED_V25_SAFETY_CHECKPOINT"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text("# Runtime V2.5E - Scheduler Live Dry-Run Trial, User-Approved\n\nScheduler trial creates dry-run audit only; no OS scheduler, cron, Windows task, or worker is started.\n", encoding="utf-8")
    return data


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


if __name__ == "__main__":
    result = write_scheduler_live_dry_run_trial_report()
    print(f"Runtime V2.5E scheduler live dry-run: safe={result['all_safe']} final={result['final_recommendation']}")

