from pathlib import Path

from orchestration.runtime.v25_scheduler_live_dry_run_trial import (
    APPROVAL_TEXT,
    run_scheduler_live_dry_run_trial,
    validate_scheduler_live_dry_run_safe,
)


def test_scheduler_live_dry_run_disabled_by_default(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    data = run_scheduler_live_dry_run_trial(audit_path=audit_path)

    assert validate_scheduler_live_dry_run_safe(data)
    assert data["gate"]["permitted"] is False
    assert data["decision"]["os_task_registered"] is False
    assert not audit_path.exists()
    assert all(value is False for value in data["decision"].values())


def test_scheduler_live_dry_run_writes_only_dry_run_audit_when_approved(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    data = run_scheduler_live_dry_run_trial(
        approval_text=APPROVAL_TEXT,
        env={"DELTA_SCHEDULER_LIVE_DRY_RUN_ENABLED": "true"},
        write_audit=True,
        audit_path=audit_path,
    )

    assert validate_scheduler_live_dry_run_safe(data)
    assert data["gate"]["permitted"] is True
    assert data["decision"]["os_task_registered"] is False
    assert audit_path.exists()
    assert data["audit"]["simulated"] is True
    assert all(value is False for value in data["decision"].values())
