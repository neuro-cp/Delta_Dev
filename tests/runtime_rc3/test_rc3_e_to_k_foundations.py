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
    assert all(report["overall"] == 1.0 for report in reports[:5])
    assert reports[5]["scores"]["real_operator_evidence"] == 0.0
    assert reports[6]["scores"]["real_operator_evidence"] == 0.0
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


def test_governance_and_plugin_stage_outputs_are_substantive(tmp_path: Path):
    governance = run_stage("E", write_reports=False, persistence_root=tmp_path / "project_state")
    plugin = run_stage("F", write_reports=False, persistence_root=tmp_path / "project_state")
    assert governance["result"]["review_request"]["intake_status"] == "reviewable"
    assert governance["result"]["approval_chain"]
    assert governance["result"]["rollback_requirement"]["absent_or_dishonest"] is False
    assert governance["result"]["governance_decision"]["execution_permission_granted"] is False
    assert plugin["result"]["interface_contract"]["live_execution_connected"] is False
    assert plugin["result"]["permission_contract"]["default_policy"] == "deny"
    assert plugin["result"]["comparison"]["automatically_selected"] is False


def test_operator_pilot_and_freeze_do_not_claim_real_evidence(tmp_path: Path):
    pilot = run_stage("J", write_reports=False, persistence_root=tmp_path / "project_state")
    freeze = run_stage("K", write_reports=False, persistence_root=tmp_path / "project_state")
    assert pilot["result"]["pilot_protocol"]["real_operator_evidence_collected"] is False
    assert all(item["evidence_type"] == "simulated_fixture" for item in pilot["result"]["pilot_scenarios"])
    assert freeze["result"]["operator_freeze_review"]["real_operator_review_completed"] is False
    assert freeze["result"]["freeze_manifest"]["freeze_status"] == "RC3_FREEZE_PENDING_REAL_OPERATOR_PILOT_EVIDENCE"


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
    assert summary["overall"] < 1.0
    assert summary["final_recommendation"] == "READY_FOR_COMPREHENSIVE_TESTING_AND_CALIBRATION"
    assert summary["freeze_status"] == "RC3_FREEZE_PENDING_REAL_OPERATOR_PILOT_EVIDENCE"
    assert summary["real_operator_evidence_collected"] is False
    assert summary["delta_75_interaction_performed"] is False
    assert summary["next_boundary"] == "pause_feature_development_for_post_rc3_k_calibration_campaign"
