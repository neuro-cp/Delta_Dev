from orchestration.runtime.v26_training_dataset_review_ui import (
    build_training_dataset_review_ui,
    validate_training_dataset_review_ui_safe,
)


def test_training_dataset_review_ui_is_static_only():
    data = build_training_dataset_review_ui()

    assert validate_training_dataset_review_ui_safe(data)
    assert data["mode"] == "static_review_ui_design_only"
    assert data["safety_invariants"]["training_performed"] is False
    assert data["safety_invariants"]["dataset_exported"] is False
