from pathlib import Path

import pytest

from orchestration.runtime.rc3_e_to_k_foundations import (
    ProjectStateStore,
    build_plugin_manifest,
    build_project_frame,
    run_all_stages,
    run_stage,
    validate_plugin_manifest,
)


def test_rc3_e_through_k_stage_reports_pass(tmp_path: Path):
    reports = [run_stage(stage, write_reports=False, persistence_root=tmp_path / "project_state") for stage in "EFGHIJK"]
    assert [report["stage"] for report in reports] == [f"RC3-{stage}" for stage in "EFGHIJK"]
    assert all(report["overall"] == 1.0 for report in reports)
    assert all(report["safety_metadata_completeness"] == 1.0 for report in reports)
    assert all(report["delta_75_interaction_performed"] is False for report in reports)


def test_plugin_manifest_rejects_unrestricted_permissions():
    manifest = build_plugin_manifest()
    unsafe = type(manifest)(
        **{**manifest.__dict__, "permissions": ("unrestricted",)}
    )
    validation = validate_plugin_manifest(unsafe)
    assert validation.result == "rejected"
    assert "unrestricted_permission_claim" in validation.rejection_reasons


def test_project_state_store_requires_explicit_actor_and_blocks_secret_like_values(tmp_path: Path):
    frame, _health = build_project_frame("Example project")
    frame = type(frame)(**{**frame.__dict__, "persistence_status": "explicit_project_state"})
    store = ProjectStateStore(tmp_path)
    with pytest.raises(ValueError):
        store.write(frame, actor="", reason="missing actor", source_episode="test")
    secret_frame = type(frame)(**{**frame.__dict__, "context_segments": ("api_key=x",)})
    with pytest.raises(ValueError):
        store.write(secret_frame, actor="operator", reason="secret test", source_episode="test")


def test_project_state_round_trip_archive_and_export(tmp_path: Path):
    frame, _health = build_project_frame("Round trip project")
    frame = type(frame)(**{**frame.__dict__, "persistence_status": "explicit_project_state"})
    store = ProjectStateStore(tmp_path)
    preview = store.preview_write(frame, actor="operator", reason="round trip", source_episode="test")
    record = store.write(frame, actor="operator", reason="round trip", source_episode="test")
    exported = store.export(frame.project_id)
    archived = store.archive(frame.project_id, actor="operator", reason="archive test")
    assert preview["write_authorized"] is True
    assert record.project_frame.project_id == frame.project_id
    assert exported["project_frame"]["project_id"] == frame.project_id
    assert archived.archived is True


def test_all_stage_summary_boundary(tmp_path: Path):
    summary = run_all_stages(write_reports=False, persistence_root=tmp_path / "project_state")
    assert summary["overall"] == 1.0
    assert summary["delta_75_interaction_performed"] is False
    assert summary["next_boundary"] == "pause_feature_development_for_post_rc3_k_calibration_campaign"
