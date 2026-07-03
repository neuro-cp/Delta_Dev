from orchestration.runtime.v26_dataset_redaction_trial import (
    build_dataset_redaction_trial,
    redact_text,
    validate_dataset_redaction_trial_safe,
)


def test_dataset_redaction_trial_redacts_without_exporting():
    data = build_dataset_redaction_trial()

    assert validate_dataset_redaction_trial_safe(data)
    assert "[REDACTED_EMAIL]" in redact_text("x@y.com")
    assert "[REDACTED_NUMBER]" in redact_text("4111111111111111")
    assert data["safety_invariants"]["training_performed"] is False
