from orchestration.runtime.v26_model_artifact_registry_design import (
    build_model_artifact_registry_design,
    validate_model_artifact_registry_design_safe,
)


def test_model_artifact_registry_does_not_create_artifacts():
    data = build_model_artifact_registry_design()

    assert validate_model_artifact_registry_design_safe(data)
    assert data["registry_active"] is False
    assert data["artifact_created"] is False
