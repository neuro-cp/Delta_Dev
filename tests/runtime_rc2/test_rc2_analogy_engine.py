from orchestration.runtime.rc2_analogy_engine import (
    build_analogy_analysis,
    build_analogy_engine_report,
    is_analogy_prompt,
)
from orchestration.runtime.rc2_conversational_mode_router import route_message


def _classification(prompt: str) -> str:
    payload = build_analogy_analysis(prompt)
    assert payload["matched"] is True
    assert payload["route"] == "analogy_analysis"
    assert payload["provider_calls_performed"] is False
    assert payload["training_performed"] is False
    assert payload["canonical_write_performed"] is False
    return payload["analogy_analysis"]["analogy_classification"]


def test_detects_analogy_intent_without_hijacking_contradictions():
    assert is_analogy_prompt("How is photosynthesis like charging a battery?")
    assert is_analogy_prompt("What works and what breaks in that analogy?")
    assert is_analogy_prompt("Test this analogy: photosynthesis/respiration is like charging/discharging.")
    assert not is_analogy_prompt("Can these both be true: photosynthesis stores energy, and photosynthesis never stores energy?")


def test_strong_and_structural_analogies():
    expected = {
        "How is photosynthesis like charging a battery?": "process_analogy",
        "How is cellular respiration like discharging a battery?": "process_analogy",
        "How is working memory like a computer workspace?": "functional_analogy",
        "How are feedback loops like thermostatic control?": "strong_structural_analogy",
        "How is graph traversal like following roads through a map?": "relational_analogy",
        "How is access control like physical locks and permissions?": "functional_analogy",
    }
    for prompt, classification in expected.items():
        assert _classification(prompt) == classification


def test_cross_domain_analogies_have_limits():
    payload = build_analogy_analysis("How is immune defense like cybersecurity?")
    analysis = payload["analogy_analysis"]
    assert analysis["analogy_classification"] == "functional_analogy"
    assert analysis["mapped_roles"]
    assert analysis["limits_of_analogy"]
    assert "threat detection" in analysis["shared_structure"]


def test_misleading_analogies_are_qualified():
    prompts = [
        "Is blood pressure and allergies a good analogy merely because both are medical?",
        "Is photosynthesis and inflation a good analogy merely because both involve growth?",
        "Is memory and storage a perfect equivalent analogy?",
        "Is the brain and a computer physically identical?",
        "Is DNA a complete software program?",
    ]
    for prompt in prompts:
        classification = _classification(prompt)
        assert classification in {"misleading_analogy", "superficial_similarity"}


def test_router_uses_analogy_before_wrs_and_avoids_side_effects():
    payload = route_message("Conversation", "How is photosynthesis like charging a battery?")
    assert payload["route"] == "analogy_analysis"
    assert payload["memory_candidate"] is None
    assert payload["provider_calls_performed"] is False
    assert payload["web_search_performed"] is False
    assert payload["training_performed"] is False
    assert "Where it breaks" in payload["answer"]


def test_regression_contradiction_and_wrs_routes_remain_distinct():
    contradiction = route_message(
        "Conversation",
        "Can these both be true: blood pressure is always constant, and blood pressure varies with activity and stress?",
    )
    wrs = route_message("Conversation", "How does photosynthesis relate to cellular respiration?")
    assert contradiction["route"] == "contradiction_analysis"
    assert wrs["route"] != "analogy_analysis"


def test_analogy_report_generation():
    report = build_analogy_engine_report(write_reports=False)
    assert report["cases_tested"] >= 18
    assert report["structural_mapping_accuracy"] >= 0.8
    assert report["misleading_analogy_rejection"] >= 0.8
    assert report["local_model_avoidance"] == 1.0
