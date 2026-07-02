from __future__ import annotations

import json

from tools.phase26_autonomous_campaign import _aggregate, _write_reports


def test_phase26_aggregate_tracks_survival_and_failure_trends(tmp_path):
    run = {
        "run": "planning_100",
        "cycles_completed": 20,
        "cycles_requested": 100,
        "profiles": ["planning"],
        "semantic_growth": 12,
        "prediction_coverage": 0.8,
        "failed_predictions": 2,
        "average_promotion_score": 0.51,
        "promotion_score_max": 0.62,
        "promotion_counts": {"Candidate": 4, "Validated": 3, "Reject": 1},
        "promotion_eligible": 0,
        "validated_concepts": 3,
        "centrality_average": 0.2,
        "projected_centrality_average": 0.4,
        "artifact_rate": 0.0,
        "incomplete_rate": 0.0,
        "redundancy_average": 0.1,
        "dominant_failure": "unresolved_prediction",
        "failure_distribution": {"unresolved_prediction": 2, "failed_validation": 1},
        "provider_usage": {"qwen": 20},
        "survival_curve": {
            "extracted_candidates": 12,
            "semantic_records_evaluated": 16,
            "predictions_validated": 8,
            "survived_normalization": 15,
            "survived_governance": 7,
            "promotion_candidates": 7,
            "promotion_eligible": 0,
            "canonical_ready": 0,
        },
    }

    summary = _aggregate([run], tmp_path / "campaign")
    _write_reports(summary, tmp_path / "reports")

    assert summary["run_count"] == 1
    assert summary["aggregate_survival_curve"]["extracted_candidates"] == 12
    assert summary["aggregate_failure_distribution"]["unresolved_prediction"] == 2
    assert summary["aggregate_provider_usage"]["qwen"] == 20
    report = json.loads((tmp_path / "reports" / "phase26_autonomous_campaign_report.json").read_text())
    assert report["canonical_merge_performed"] is False
    assert (tmp_path / "reports" / "phase26_survival_curves.md").exists()
