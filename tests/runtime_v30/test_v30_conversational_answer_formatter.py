from orchestration.runtime.v30_conversational_answer_formatter import (
    SUPPORTED_MODES,
    build_conversational_answer,
    format_conversational_answer,
)


def test_v30_formatter_supports_all_modes_without_side_effects():
    payload = build_conversational_answer("What is DELTA?")
    for mode in SUPPORTED_MODES:
        rendered = format_conversational_answer(payload["answer_data"], mode=mode)
        assert rendered
    assert payload["answer_data"]["decision"]["provider_call_performed"] is False
    assert payload["answer_data"]["decision"]["memory_write_performed"] is False
    assert payload["answer_data"]["decision"]["training_triggered"] is False


def test_v30_formatter_unknown_question_stays_unknown():
    payload = build_conversational_answer("What did I eat for breakfast yesterday?")
    assert "do not have sufficient governed local evidence" in payload["formatted_answer"]
    assert payload["answer_data"]["local_answer"]["matched"] is False
