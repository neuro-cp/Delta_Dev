from pathlib import Path

from orchestration.runtime.v25_training_dataset_export_trial import (
    APPROVAL_TEXT,
    parse_dataset_export_approval,
    redact_dataset_text,
    run_training_dataset_export_trial,
    validate_dataset_export_trial_safe,
)


def test_dataset_export_dry_run_writes_nothing(tmp_path: Path):
    export_path = tmp_path / "dataset.jsonl"
    audit_path = tmp_path / "audit.jsonl"

    data = run_training_dataset_export_trial(export_path=export_path, audit_path=audit_path)

    assert validate_dataset_export_trial_safe(data)
    assert data["approval"]["matches_required_shape"] is False
    assert data["decision"]["dataset_exported"] is False
    assert not export_path.exists()
    assert not audit_path.exists()


def test_dataset_export_requires_exact_approval_and_redacts(tmp_path: Path):
    export_path = tmp_path / "dataset.jsonl"
    audit_path = tmp_path / "audit.jsonl"

    casual = parse_dataset_export_approval("yes, export it")
    assert casual["matches_required_shape"] is False

    data = run_training_dataset_export_trial(
        approval_text=APPROVAL_TEXT,
        export=True,
        export_path=export_path,
        audit_path=audit_path,
    )

    assert validate_dataset_export_trial_safe(data)
    assert data["approval"]["matches_required_shape"] is True
    assert data["decision"]["dataset_exported"] is True
    assert export_path.exists()
    assert audit_path.exists()
    text = export_path.read_text(encoding="utf-8")
    assert "[REDACTED_EMAIL]" in text
    assert "person@example.com" not in text
    assert redact_dataset_text("a@b.com 4111111111111111") == "[REDACTED_EMAIL] [REDACTED_NUMBER]"
