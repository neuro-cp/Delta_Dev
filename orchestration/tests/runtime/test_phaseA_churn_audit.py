from __future__ import annotations

import json

from tools.phaseA_churn_audit import audit_churn


def _decision(
    concept_id: str,
    *,
    recommendation: str,
    score: float,
    redundancy: float = 0.08,
    concept: str | None = None,
):
    return {
        "concept_id": concept_id,
        "concept": concept or f"Concept {concept_id} should remain stable across chunks",
        "recommendation": recommendation,
        "promotion_score": score,
        "evidence": {
            "supported_predictions": 1,
            "failed_predictions": 0,
            "unresolved_predictions": 0,
            "open_contradictions": 0,
            "incomplete_proposition": False,
        },
        "dimensions": {
            "redundancy_penalty": redundancy,
            "prompt_artifact_penalty": 0.0,
            "projected_centrality": 0.3,
            "evidence_support": 1.0,
        },
    }


def _write_chunk(root, index, decisions):
    reports = root / "chunks" / f"chunk_{index:03d}" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    reports.joinpath("promotion_governance_report.json").write_text(
        json.dumps({"decisions": decisions}),
        encoding="utf-8",
    )


def test_phaseA_churn_audit_classifies_expansion_and_threshold_edge_loss(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    campaign.joinpath("phaseA_checkpoint.json").write_text(
        json.dumps(
            {
                "status": "stopped",
                "stop_reason": "promotion eligibility churn exceeded 20%",
                "chunks": [
                    {"chunk_index": 1, "promotion_churn": {"churn_rate": 2.0}},
                    {"chunk_index": 2, "promotion_churn": {"churn_rate": 1.0}},
                    {"chunk_index": 3, "promotion_churn": {"churn_rate": 0.75}},
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_chunk(
        campaign,
        1,
        [
            _decision("a", recommendation="Promotion Eligible", score=0.6211),
            _decision("b", recommendation="Promotion Eligible", score=0.6202),
        ],
    )
    _write_chunk(
        campaign,
        2,
        [
            _decision("a", recommendation="Promotion Eligible", score=0.6211),
            _decision("b", recommendation="Promotion Eligible", score=0.6202),
            _decision("c", recommendation="Promotion Eligible", score=0.63),
            _decision("d", recommendation="Promotion Eligible", score=0.64),
        ],
    )
    _write_chunk(
        campaign,
        3,
        [
            _decision("a", recommendation="Promotion Eligible", score=0.6211),
            _decision("b", recommendation="Validated", score=0.619, redundancy=0.0952),
            _decision("c", recommendation="Validated", score=0.619, redundancy=0.0952),
            _decision("d", recommendation="Promotion Eligible", score=0.64),
            _decision("e", recommendation="Promotion Eligible", score=0.67),
        ],
    )

    summary = audit_churn(campaign_root=campaign, reports_dir=tmp_path / "reports")

    assert summary["healthy_expansion_transitions"] == 1
    assert summary["threshold_edge_losses"] == 2
    assert summary["harmful_losses"] == 0
    assert summary["loss_cause_counts"] == {"threshold_edge_redundancy_increase": 2}
    assert "operationally stable" in summary["conclusion"]
    assert (tmp_path / "reports" / "phaseA_churn_audit.md").exists()


def test_phaseA_churn_audit_flags_failed_validation_as_harmful(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    campaign.joinpath("phaseA_checkpoint.json").write_text(
        json.dumps(
            {
                "status": "stopped",
                "stop_reason": "promotion eligibility churn exceeded 20%",
                "chunks": [
                    {"chunk_index": 1, "promotion_churn": {"churn_rate": 1.0}},
                    {"chunk_index": 2, "promotion_churn": {"churn_rate": 1.0}},
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_chunk(campaign, 1, [_decision("a", recommendation="Promotion Eligible", score=0.7)])
    failed = _decision("a", recommendation="Reject", score=0.3)
    failed["evidence"]["failed_predictions"] = 1
    _write_chunk(campaign, 2, [failed])

    summary = audit_churn(campaign_root=campaign, reports_dir=tmp_path / "reports")

    assert summary["harmful_losses"] == 1
    assert summary["loss_cause_counts"] == {"failed_validation": 1}
