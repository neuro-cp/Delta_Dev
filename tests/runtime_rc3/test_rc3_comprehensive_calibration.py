from pathlib import Path

from orchestration.runtime.rc3_comprehensive_calibration import (
    FINAL_RECOMMENDATION,
    failure_taxonomy,
    run_comprehensive_calibration,
    run_determinism_probe,
)
from orchestration.runtime.rc3_e_to_k_foundations import FREEZE_STATUS


def test_comprehensive_calibration_recommends_real_operator_pilot(tmp_path: Path):
    report = run_comprehensive_calibration(write_reports=False, tmp_root=tmp_path)
    assert report["final_recommendation"] == FINAL_RECOMMENDATION
    assert report["freeze_status"] == FREEZE_STATUS
    assert report["actual_operator_pilot_evidence"] is False
    assert report["simulated_operator_pilot_evidence"] is True
    assert "real operator pilot evidence missing" in report["freeze_blockers"]
    assert report["safety"]["delta_75_interaction_performed"] is False
    assert report["rc4_status"] == "not_started"


def test_failure_taxonomy_contains_required_high_risk_boundaries():
    taxonomy = {item.identifier: item for item in failure_taxonomy()}
    for key in (
        "false_goal_activation",
        "governance_bypass",
        "hidden_persistence",
        "fixture_real_confusion",
        "false_freeze_claim",
        "rc2_regression",
    ):
        assert key in taxonomy
        assert taxonomy[key].severity in ("high", "critical")


def test_determinism_probe_stable_except_timestamps(tmp_path: Path):
    probe = run_determinism_probe(tmp_path)
    assert probe["passed"] is True
    assert probe["timestamp_sensitive_fields_excluded"] == ("created_at",)


def test_calibration_family_scores_do_not_hide_missing_real_pilot(tmp_path: Path):
    report = run_comprehensive_calibration(write_reports=False, tmp_root=tmp_path)
    assert report["family_scores"]["pilot_real_evidence"] == 0.0
    assert report["overall"] < 1.0
    assert report["family_scores"]["rc2_compatibility"] == 1.0
