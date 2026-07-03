from orchestration.runtime.v29_local_answer_engine import format_v29_cli_output, run_v29_local_answer


def test_v29_answer_engine_answers_natural_self_description():
    data = run_v29_local_answer("What is DELTA?")

    assert data["phase"] == "Runtime V2.9"
    assert data["local_answer"]["matched"] is True
    assert data["local_answer"]["topic_id"] == "identity"
    assert "governed cognitive-runtime substrate" in data["draft"]["answer_text"]
    assert data["decision"]["provider_call_performed"] is False
    assert data["decision"]["memory_write_performed"] is False


def test_v29_answer_engine_keeps_unknowns_safe():
    data = run_v29_local_answer("What did I eat for breakfast yesterday?")

    assert data["phase"] == "Runtime V2.9"
    assert data["local_answer"]["matched"] is False
    assert data["local_answer"]["topic_id"] == "unsupported"
    assert data["draft"]["grounded"] is True
    assert data["decision"]["provider_call_performed"] is False
    assert data["decision"]["training_triggered"] is False


def test_v29_answer_engine_preserves_candidate_context_recall_flag():
    data = run_v29_local_answer("What can you do?", use_recall=True)

    assert data["local_answer"]["matched"] is True
    assert data["draft"]["uses_candidate_context"] is True
    assert data["recall_context"]["invariant_flags"]["authoritative_recall_enabled"] is False
    assert data["decision"]["recall_mutated"] is False


def test_v29_cli_formatter_reports_safety_status():
    data = run_v29_local_answer("What phase are you in?")
    text = format_v29_cli_output(data)

    assert "Runtime V2.9" in text
    assert "provider_call_performed: False" in text
    assert "model_b_default_changed: False" in text
