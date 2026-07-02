from __future__ import annotations

import json

from tools.phase20_campaign_aggregate import aggregate_campaigns


def test_phase20_aggregate_classifies_failure_reasons(tmp_path):
    campaign_root = tmp_path / "campaign"
    reports_dir = tmp_path / "reports"
    run_reports = campaign_root / "run_a" / "reports"
    run_reports.mkdir(parents=True)
    (run_reports / "continuous_learning_operator_report.json").write_text(
        json.dumps({"cycles_requested": 20}),
        encoding="utf-8",
    )
    (run_reports / "continuous_learning_training_summary.json").write_text(
        json.dumps(
            {
                "cycles_completed": 20,
                "curriculum_profiles": ["planning"],
                "baseline_counts": {"semantic_knowledge": 1, "relationships": 0, "memories": 1},
                "final_counts": {
                    "semantic_knowledge": 3,
                    "relationships": 0,
                    "memories": 8,
                    "contradictions": 0,
                },
                "provider_metrics": {"qwen": {"cycles": 20}},
                "elapsed_seconds": 1.0,
            }
        ),
        encoding="utf-8",
    )
    (run_reports / "phase16_validation_report.json").write_text(
        json.dumps({"after_prediction_quality": {"coverage": 0.5, "supported": 1, "failed": 0}}),
        encoding="utf-8",
    )
    (run_reports / "phase17_validation_report.json").write_text(
        json.dumps({"after_prediction_quality": {"coverage": 0.75, "supported": 2, "failed": 1}}),
        encoding="utf-8",
    )
    (run_reports / "phase18_normalization_report.json").write_text(
        json.dumps({"recovered_concepts": 0, "normalization_precision": 0.0}),
        encoding="utf-8",
    )
    (run_reports / "promotion_governance_report.json").write_text(
        json.dumps(
            {
                "average_promotion_score": 0.3,
                "recommendation_counts": {"Reject": 1},
                "decisions": [
                    {
                        "recommendation": "Reject",
                        "promotion_score": 0.3,
                        "dimensions": {
                            "relationship_centrality": 0.0,
                            "evidence_support": 0.2,
                            "redundancy_penalty": 0.5,
                        },
                        "evidence": {
                            "failed_predictions": 1,
                            "effective_failed_predictions": 1,
                            "unresolved_predictions": 1,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = aggregate_campaigns(campaign_root=campaign_root, reports_dir=reports_dir)

    assert summary["run_count"] == 1
    assert summary["aggregate_failure_distribution"]["low_centrality"] == 1
    assert summary["aggregate_failure_distribution"]["failed_validation"] == 1
    assert summary["provider_usage"]["qwen"] == 20
    assert (reports_dir / "phase20_cross_run_report.md").exists()
