from __future__ import annotations

from orchestration.runtime.rc2_conversational_mode_router import route_message
from orchestration.runtime.rc2_working_reasoning_set import (
    build_working_reasoning_set,
    build_wrs_report,
    extract_reasoning_seeds,
    should_use_wrs,
)


def test_wrs_seed_extraction_captures_medical_pair() -> None:
    seeds = extract_reasoning_seeds(
        "How could knowledge about a patient's allergies influence the interpretation or management of their blood pressure?"
    )
    assert "allergies" in seeds
    assert "blood pressure" in seeds
    assert should_use_wrs("What common reasoning principles connect allergies and blood pressure?")


def test_wrs_builds_ephemeral_multi_concept_workspace() -> None:
    result = build_working_reasoning_set(
        "What common reasoning principles connect allergies and blood pressure?"
    )
    assert result["matched"] is True
    assert result["retrieved_concept_count"] >= 2
    assert result["retrieved_proposition_count"] >= 2
    assert result["safety"]["provider_calls_performed"] is False
    assert result["safety"]["training_performed"] is False
    assert result["safety"]["noncanonical_memory_write_performed"] is False
    assert result["safety"]["graph_write_performed"] is False
    assert result["ephemeral"] is True
    assert "Stored knowledge" in result["answer"]
    assert "Reasoned connection" in result["answer"]
    assert "Uncertainty" in result["answer"]
    assert "evidence, context, uncertainty, constraints" not in result["answer"]


def test_conversation_routes_relational_substrate_question_to_wrs() -> None:
    payload = route_message(
        "Conversation",
        "Suppose a patient has elevated blood pressure and a history of severe allergies. "
        "What additional evidence would you want before making a medical decision?",
    )
    assert payload["route"] == "working_reasoning_set"
    assert payload["local_model_result"]["executed"] is False if "local_model_result" in payload else True
    assert payload["provider_calls_performed"] is False
    assert payload["training_performed"] is False
    assert payload["canonical_write_performed"] is False
    assert payload["working_reasoning_set"]["retrieved_concept_count"] >= 2
    assert payload["working_reasoning_set"]["memory_write_performed"] is False
    assert payload["working_reasoning_set"]["graph_write_performed"] is False


def test_wrs_covers_all_explicit_topic_families_in_cross_pair_prompt() -> None:
    result = build_working_reasoning_set(
        "Compare the reasoning used for blood pressure and allergies with the reasoning used for photosynthesis and cellular respiration. "
        "What common cognitive process connects these pairs?"
    )
    assert result["matched"] is True
    assert set(result["required_families"]) >= {"blood pressure", "allergies", "photosynthesis", "respiration"}
    assert set(result["covered_families"]) >= {"blood pressure", "allergies", "photosynthesis", "respiration"}
    assert result["entity_coverage_score"] == 1.0
    answer = result["answer"].lower()
    assert "photosynthesis" in answer
    assert "respiration" in answer
    assert "complementary system" in answer or "energy transformation" in answer


def test_wrs_report_keeps_synthesis_disabled() -> None:
    report = build_wrs_report(write_reports=False)
    assert report["wrs_implemented"] is True
    assert report["questions_tested"] >= 5
    assert report["synthesis_activation"] is False
    assert report["local_model_avoidance"] == 1.0
    assert report["safety"]["provider_calls_performed"] is False
    assert report["safety"]["training_performed"] is False
