from orchestration.runtime.cognitive_backend import (
    classify_backend_availability,
    normalize_openai_chat_response,
    response_format_mode,
)


def test_normalize_openai_chat_response_preserves_reasoning_and_tool_fields():
    raw = {
        "choices": [{
            "finish_reason": "stop",
            "message": {
                "content": '{"ok":true}',
                "reasoning_content": "scratch",
                "tool_calls": [{"name": "x"}],
            },
        }],
        "usage": {"prompt_tokens": 3, "completion_tokens": 4},
    }

    result = normalize_openai_chat_response(raw, backend={"name": "llama_cpp"}, model={"id": "qwen"})

    assert result["content"] == '{"ok":true}'
    assert result["reasoning_content"] == "scratch"
    assert result["tool_calls"] == ({"name": "x"},)
    assert result["finish_reason"] == "stop"
    assert result["usage"]["completion_tokens"] == 4


def test_backend_availability_records_missing_local_servers():
    result = classify_backend_availability(llama_server_path=None, lmstudio_port_open=False)

    assert result["llama_cpp_python"] == "available"
    assert result["llama_server"] == "not_available_locally"
    assert result["lm_studio"] == "not_running"


def test_response_format_mode_distinguishes_json_object_and_schema_request():
    assert response_format_mode(None)["mode"] == "prompt_only"
    assert response_format_mode({"type": "json_object"}) == {"mode": "json_object", "schema_enforced": False}
    assert response_format_mode({"type": "json_object", "schema": {"type": "object"}})["mode"] == "json_schema_requested"
