from __future__ import annotations

from orchestration.runtime.rc2_synthesis_trial_report import (
    build_synthesis_trial_report,
    score_concept_substance,
    score_synthesis_trial,
)
from orchestration.runtime.rc2_typed_graph_link_readiness import build_typed_graph_link_readiness_report


def test_concept_substance_penalizes_generic_definition():
    generic = {
        "concept_name": "Photosynthesis",
        "short_definition": "Photosynthesis is a reusable biology concept that helps explain causes, constraints, tradeoffs, and practical decisions in the biology domain.",
        "propositions": ["Photosynthesis converts light into stored chemical energy."],
        "examples": [],
        "misconceptions": [],
        "related_concepts": ["biology reasoning", "biology evidence"],
    }
    rich = {
        "concept_name": "Photosynthesis",
        "short_definition": "Photosynthesis converts light, carbon dioxide, and water into sugars that store chemical energy.",
        "propositions": [
            "Photosynthesis stores energy in chemical bonds.",
            "Photosynthesis uses carbon dioxide and water.",
            "Photosynthesis releases oxygen as a byproduct.",
        ],
        "examples": ["Leaves making sugars in sunlight."],
        "misconceptions": ["Photosynthesis is not the same as cellular respiration."],
        "related_concepts": ["chloroplasts", "carbon cycle", "glucose", "cellular respiration"],
    }

    generic_score = score_concept_substance(generic)
    rich_score = score_concept_substance(rich)

    assert generic_score["generic_definition"] is True
    assert "generic_definition" in generic_score["penalties"]
    assert rich_score["generic_definition"] is False
    assert rich_score["score"] > generic_score["score"]


def test_synthesis_quality_uses_concept_substance():
    result = {
        "retrieval_set_quality": 1.0,
        "tentative_inference": "These stored concepts may connect through energy transformation between stored sugars and usable cellular energy.",
        "uncertainty": "moderate: the retrieval set is strong, but the bridge is inferred and has not been approved as knowledge.",
    }
    weak = [{"score": 0.2}]
    strong = [{"score": 0.9}]

    weak_score = score_synthesis_trial(result, weak)
    strong_score = score_synthesis_trial(result, strong)

    assert strong_score["overall_score"] > weak_score["overall_score"]
    assert weak_score["activation_recommendation"] == "not_ready_concept_substance_audit_required"


def test_synthesis_quality_report_is_safe_and_trial_only():
    report = build_synthesis_trial_report()

    assert report["phase"] == "RC2.6 Manual Read-Only Synthesis Quality Trials"
    assert report["trial_count"] >= 20
    assert report["synthesis_activation"] is False
    assert report["trial_only"] is True
    assert report["safety"]["training_performed"] is False
    assert report["safety"]["provider_calls_performed"] is False
    assert report["safety"]["canonical_write_performed"] is False
    assert "median_synthesis_quality" in report
    assert "hallucination_risk_average" in report
    assert "stored_concept_substance_average" in report
    assert "generic_concept_count" in report
    for trial in report["trials"]:
        assert trial["memory_write_performed"] is False
        assert trial["synthesis_enabled"] is False
        assert trial["concept_substance_scores"]
        assert "stored_concept_substance" in trial["synthesis_quality"]
        assert "concept_diversity" in trial["synthesis_quality"]
        assert "overreach_risk" in trial["synthesis_quality"]


def test_typed_graph_link_readiness_is_report_only():
    report = build_typed_graph_link_readiness_report()

    assert report["phase"] == "RC2.6 Typed Graph Link Readiness"
    assert report["read_only"] is True
    assert report["graph_links_written"] is False
    assert report["safety"]["graph_links_written"] is False
    assert report["safety"]["memory_write_performed"] is False
    assert report["candidate_link_count"] > 0
    assert report["relation_types_detected"]
