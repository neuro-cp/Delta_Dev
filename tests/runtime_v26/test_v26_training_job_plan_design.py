from orchestration.runtime.v26_training_job_plan_design import (
    build_training_job_plan_design,
    validate_training_job_plan_design_safe,
)


def test_training_job_plan_has_no_execution_path():
    data = build_training_job_plan_design()

    assert validate_training_job_plan_design_safe(data)
    assert data["execution_fields_present"] is False
    assert data["plan"]["explicit_training_approval_required"] is True
