from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import phaseA_architecture_graduation as phaseA


def _write_fake_operator_reports(
    *,
    reports_dir: Path,
    cycles: int,
    profiles: tuple[str, ...],
    eligible: int = 1,
    coverage: float = 0.92,
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    decisions = []
    for index in range(4):
        recommendation = "Promotion Eligible" if index < eligible else "Validated"
        decisions.append(
            {
                "concept_id": f"{profiles[0] if profiles else 'mixed'}-{cycles}-{index}",
                "concept": f"Reusable proposition {index} for {profiles[0] if profiles else 'mixed'}",
                "recommendation": recommendation,
                "promotion_score": 0.7 - (index * 0.02),
                "confidence_trajectory": [0.42, 0.58, 0.71],
                "evidence": {
                    "supporting_evidence_count": 3,
                    "supported_predictions": 2,
                    "failed_predictions": 0,
                    "unresolved_predictions": 0,
                    "open_contradictions": 0,
                    "projection_sources": ["neighbor-a", "neighbor-b"],
                },
                "dimensions": {
                    "redundancy_penalty": 0.1,
                    "relationship_centrality": 0.25,
                    "projected_centrality": 0.45,
                    "prompt_artifact_penalty": 0.0,
                    "incomplete_proposition": 0.0,
                },
                "provenance": {
                    "source_profile": profiles[0] if profiles else "mixed",
                    "source_provider": "qwen",
                },
            }
        )
    (reports_dir / "continuous_learning_training_summary.json").write_text(
        json.dumps(
            {
                "cycles_completed": cycles,
                "stopped_early": False,
                "stop_reason": None,
                "baseline_counts": {
                    "semantic_knowledge": 10,
                    "memories": 20,
                    "relationships": 5,
                    "predictions": 3,
                    "contradictions": 0,
                },
                "final_counts": {
                    "semantic_knowledge": 10 + cycles // 2,
                    "memories": 20 + cycles,
                    "relationships": 5 + cycles // 3,
                    "predictions": 3 + cycles // 4,
                    "contradictions": 0,
                },
                "provider_metrics": {"qwen": {"cycles": cycles}},
            }
        ),
        encoding="utf-8",
    )
    (reports_dir / "phase16_validation_report.json").write_text(
        json.dumps({"after_prediction_quality": {"coverage": coverage, "supported": 4, "failed": 0, "inconclusive": 0, "open": 1}}),
        encoding="utf-8",
    )
    (reports_dir / "phase17_validation_report.json").write_text(
        json.dumps({"after_prediction_quality": {"coverage": coverage, "supported": 5, "failed": 0, "inconclusive": 0, "open": 0}}),
        encoding="utf-8",
    )
    (reports_dir / "phase18_normalization_report.json").write_text(
        json.dumps({"recovered_concepts": 0, "normalization_precision": 1.0}),
        encoding="utf-8",
    )
    (reports_dir / "promotion_governance_report.json").write_text(
        json.dumps(
            {
                "average_promotion_score": 0.64,
                "recommendation_counts": {
                    "Promotion Eligible": eligible,
                    "Validated": 4 - eligible,
                },
                "decisions": decisions,
                "virtual_projection_enabled": True,
            }
        ),
        encoding="utf-8",
    )


def test_phaseA_runs_chunked_campaign_and_writes_reports(tmp_path, monkeypatch):
    calls = []

    def fake_operator(**kwargs):
        calls.append(kwargs)
        _write_fake_operator_reports(
            reports_dir=kwargs["reports_dir"],
            cycles=kwargs["cycles"],
            profiles=kwargs["curriculum_profiles"],
        )
        return {"ok": True}

    monkeypatch.setattr(phaseA, "run_continuous_learning", fake_operator)

    result = phaseA.run_phaseA(
        campaign_root=tmp_path / ".tmp" / "experiments" / "phaseA",
        reports_dir=tmp_path / "reports",
        selected_campaigns={"dry_run_40"},
        reset=True,
    )

    assert len(calls) == 2
    assert all(call["cycles"] == 20 for call in calls)
    assert result["aggregate"]["completed_campaign_count"] == 1
    assert result["aggregate"]["total_cycles_completed"] == 40
    assert (tmp_path / "reports" / "phaseA_temp_store_validation_report.md").exists()
    assert (tmp_path / "reports" / "PhaseA_Architecture_Graduation.md").exists()
    assert (tmp_path / "reports" / "phaseA_complete.json").exists()
    sentinel = json.loads((tmp_path / "reports" / "phaseA_complete.json").read_text())
    assert sentinel["canonical_merge_performed"] is False
    assert sentinel["report_paths"]["graduation"].endswith("PhaseA_Architecture_Graduation.md")
    checkpoint = json.loads(
        (tmp_path / ".tmp" / "experiments" / "phaseA" / "dry_run_40" / "phaseA_checkpoint.json").read_text()
    )
    assert checkpoint["status"] == "completed"
    assert checkpoint["canonical_merge_performed"] is False


def test_phaseA_resume_skips_completed_chunks(tmp_path, monkeypatch):
    calls = []

    def fake_operator(**kwargs):
        calls.append(kwargs)
        _write_fake_operator_reports(
            reports_dir=kwargs["reports_dir"],
            cycles=kwargs["cycles"],
            profiles=kwargs["curriculum_profiles"],
        )
        return {"ok": True}

    monkeypatch.setattr(phaseA, "run_continuous_learning", fake_operator)
    root = tmp_path / ".tmp" / "experiments" / "phaseA"
    reports = tmp_path / "reports"

    phaseA.run_phaseA(
        campaign_root=root,
        reports_dir=reports,
        selected_campaigns={"dry_run_40"},
        reset=True,
    )
    phaseA.run_phaseA(
        campaign_root=root,
        reports_dir=reports,
        selected_campaigns={"dry_run_40"},
        reset=False,
    )

    assert len(calls) == 2


def test_phaseA_stops_after_two_low_coverage_chunks(tmp_path, monkeypatch):
    def fake_operator(**kwargs):
        _write_fake_operator_reports(
            reports_dir=kwargs["reports_dir"],
            cycles=kwargs["cycles"],
            profiles=kwargs["curriculum_profiles"],
            eligible=0,
            coverage=0.5,
        )
        return {"ok": True}

    monkeypatch.setattr(phaseA, "run_continuous_learning", fake_operator)

    result = phaseA.run_phaseA(
        campaign_root=tmp_path / ".tmp" / "experiments" / "phaseA",
        reports_dir=tmp_path / "reports",
        selected_campaigns={"dry_run_40"},
        reset=True,
    )

    campaign = result["aggregate"]["campaigns"][0]
    assert campaign["status"] == "stopped"
    assert "validation coverage below 0.80" in campaign["stop_reason"]


def test_phaseA_rejects_non_isolated_root(tmp_path):
    with pytest.raises(ValueError, match="isolated"):
        phaseA.run_phaseA(
            campaign_root=tmp_path / "not_isolated",
            reports_dir=tmp_path / "reports",
            selected_campaigns={"dry_run_40"},
            reset=False,
        )


def test_phaseA_dry_run_report_shape_contains_no_canonical_writes(tmp_path, monkeypatch):
    def fake_operator(**kwargs):
        _write_fake_operator_reports(
            reports_dir=kwargs["reports_dir"],
            cycles=kwargs["cycles"],
            profiles=kwargs["curriculum_profiles"],
            eligible=2,
        )
        return {"ok": True}

    monkeypatch.setattr(phaseA, "run_continuous_learning", fake_operator)

    result = phaseA.run_phaseA(
        campaign_root=tmp_path / ".tmp" / "experiments" / "phaseA",
        reports_dir=tmp_path / "reports",
        selected_campaigns={"dry_run_40"},
        reset=True,
    )

    assert result["canonical_dry_run"]
    assert all(item["canonical_write_performed"] is False for item in result["canonical_dry_run"])
    dry_run_report = (tmp_path / "reports" / "phaseA_canonical_promotion_dry_run.md").read_text()
    assert "No canonical writes were performed." in dry_run_report


def test_phaseA_can_run_selected_overnight_3000_with_prerequisites_ignored(tmp_path, monkeypatch):
    calls = []

    def fake_operator(**kwargs):
        calls.append(kwargs)
        _write_fake_operator_reports(
            reports_dir=kwargs["reports_dir"],
            cycles=kwargs["cycles"],
            profiles=kwargs["curriculum_profiles"],
            eligible=1,
        )
        return {"ok": True}

    monkeypatch.setattr(phaseA, "run_continuous_learning", fake_operator)

    result = phaseA.run_phaseA(
        campaign_root=tmp_path / ".tmp" / "experiments" / "phaseA",
        reports_dir=tmp_path / "reports",
        selected_campaigns={"overnight_3000"},
        reset=True,
        ignore_prerequisites=True,
    )

    assert len(calls) == 15
    assert all(call["cycles"] == 200 for call in calls)
    campaign = result["aggregate"]["campaigns"][0]
    assert campaign["campaign"] == "overnight_3000"
    assert campaign["cycles_requested"] == 3000
    assert result["aggregate"]["total_cycles_completed"] == 3000
