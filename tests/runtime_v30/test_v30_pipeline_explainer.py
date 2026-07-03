from orchestration.runtime.v30_pipeline_explainer import build_pipeline_explanation, explain_answer_pipeline
from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer


def test_v30_pipeline_explainer_reports_required_stages():
    answer = run_v29_local_answer("What is DELTA?")
    explanation = explain_answer_pipeline(answer)
    assert explanation["input"] == "What is DELTA?"
    assert explanation["route_matched"] is True
    assert explanation["matched_topic"] == "identity"
    assert explanation["recall_authoritative"] is False
    assert explanation["mutation_status"] == "none"
    assert explanation["safety_gates_checked"]["provider_call_performed"] is False


def test_v30_pipeline_explanation_render_is_human_readable():
    payload = build_pipeline_explanation("What is DELTA?")
    assert "Pipeline explanation" in payload["rendered_explanation"]
    assert "Final synthesis" in payload["rendered_explanation"]
