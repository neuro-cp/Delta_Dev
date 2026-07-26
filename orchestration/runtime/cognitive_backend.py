"""Backend-neutral response records for cognitive model probes."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CognitiveBackendResponse:
    content: str
    reasoning_content: str | None
    tool_calls: tuple[Any, ...]
    finish_reason: str
    usage: Mapping[str, Any]
    backend: Mapping[str, Any]
    model: Mapping[str, Any]
    raw_response: Mapping[str, Any]

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def normalize_openai_chat_response(response: Mapping[str, Any], *, backend: Mapping[str, Any], model: Mapping[str, Any]) -> dict[str, Any]:
    choices = response.get("choices") or ()
    first = choices[0] if choices else {}
    if not isinstance(first, Mapping):
        first = {}
    message = first.get("message") or {}
    if not isinstance(message, Mapping):
        message = {}
    normalized = CognitiveBackendResponse(
        content=str(message.get("content") or first.get("text") or ""),
        reasoning_content=(
            str(message.get("reasoning_content"))
            if message.get("reasoning_content") is not None
            else None
        ),
        tool_calls=tuple(message.get("tool_calls") or ()),
        finish_reason=str(first.get("finish_reason") or ""),
        usage=dict(response.get("usage") or {}),
        backend=dict(backend),
        model=dict(model),
        raw_response=dict(response),
    )
    return normalized.to_record()


def classify_backend_availability(*, llama_server_path: str | None, lmstudio_port_open: bool) -> dict[str, Any]:
    return {
        "llama_cpp_python": "available",
        "llama_server": "available" if llama_server_path else "not_available_locally",
        "lm_studio": "local_server_open" if lmstudio_port_open else "not_running",
    }


def response_format_mode(response_format: Mapping[str, Any] | None) -> dict[str, Any]:
    if not response_format:
        return {"mode": "prompt_only", "schema_enforced": False}
    if response_format.get("json_schema") or response_format.get("schema"):
        return {"mode": "json_schema_requested", "schema_enforced": "backend_dependent"}
    if response_format.get("type") == "json_object":
        return {"mode": "json_object", "schema_enforced": False}
    return {"mode": "unknown", "schema_enforced": False}
