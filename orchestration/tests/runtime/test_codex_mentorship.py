from __future__ import annotations

from knowledge import KnowledgeQualityReport
from orchestration.mentorship import CodexMentorshipEngine


def test_codex_mentorship_reports_engineering_tasks_without_editing_cognition():
    report = CodexMentorshipEngine().generate(
        runtime_summary={
            "ticks_requested": 10,
            "ticks_completed": 9,
            "prediction_quality": {"coverage": 0.5},
        },
        knowledge_quality=[
            KnowledgeQualityReport(
                concept_id="weak",
                concept="weak",
                evidence_count=0,
                counter_evidence_count=0,
                relationship_count=0,
                prediction_success_count=0,
                prediction_failure_count=0,
                validation_count=0,
                revision_count=0,
                contradiction_count=1,
                derived_confidence=0.3,
                uncertainty=0.7,
            )
        ],
        provider_profiles=[],
    )

    assert "runtime_incomplete" in report.weaknesses
    assert "prediction_coverage_low" in report.weaknesses
    assert "knowledge_quality_pressure" in report.weaknesses
    assert "provider_evidence_missing" in report.weaknesses
    assert report.metadata["does_not_edit_delta_cognition"] is True
    assert report.recommended_engineering_tasks


def test_codex_mentorship_is_quiet_when_evidence_is_healthy():
    report = CodexMentorshipEngine().generate(
        runtime_summary={
            "ticks_requested": 2,
            "ticks_completed": 2,
            "prediction_quality": {"coverage": 1.0},
        },
        knowledge_quality=[],
        provider_profiles=[],
    )

    assert "runtime_incomplete" not in report.weaknesses
    assert "prediction_coverage_low" not in report.weaknesses
