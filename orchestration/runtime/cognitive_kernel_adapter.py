"""Small typed adapter surface for cognitive-kernel local model probes."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Protocol, Sequence

from orchestration.runtime.autonomy_governed_primitives import grounding_result


@dataclass(frozen=True)
class ModelAdapter:
    adapter_id: str
    model_family: str
    native_chat_template_source: str
    system_role_support: bool
    assistant_prefix_policy: str
    reasoning_mode_controls: str
    stop_token_policy: tuple[str, ...]
    tool_call_policy: str
    json_generation_capability: str
    response_wrapper_policy: str
    tokenizer_identity: str
    backend_compatibility: str

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InferenceProfile:
    context_length: int
    output_token_limit: int
    gpu_layer_count: int | None
    batch_size: int | None
    flash_attention: str
    kv_cache: str
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float
    stop_tokens: tuple[str, ...]
    constrained_output: str

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptProfile:
    profile_id: str
    result_type: str
    schema: Mapping[str, Any]
    instructions: tuple[str, ...]

    def render(self, *, problem_id: str, evidence_packet: Mapping[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": "\n".join((
                    *self.instructions,
                    "Your assistant message must be the result object itself, not an envelope containing the request.",
                    "Do not echo the schema, evidence packet, prompt, or instructions.",
                )),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "problem_id": problem_id,
                        "required_result_type": self.result_type,
                        "schema": self.schema,
                        "evidence_packet": evidence_packet,
                    },
                    indent=2,
                    sort_keys=True,
                ),
            },
        ]

    def to_record(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = dict(self.schema)
        return payload


ABSTENTION_SCHEMA = {
    "result_type": "insufficient_evidence",
    "problem_id": "string",
    "supported_findings": [],
    "missing_evidence": [{"required_clause": "string", "reason": "string"}],
    "requested_evidence": ["string"],
    "limitations": ["string"],
    "uncertainty": {"score": 0.0, "reason": "string"},
}

COGNITIVE_PROPOSAL_SCHEMA = {
    "proposal_type": "cognitive_proposal",
    "problem_id": "string",
    "diagnosis": "string",
    "first_incorrect_transition": "string",
    "implementation_path": "string",
    "focused_test_path": "string",
    "independent_evaluator_path": "string",
    "bounded_strategy": ["string"],
    "limitations": ["string"],
    "uncertainty": {"score": 0.0, "reason": "string"},
    "evidence_references": [{"source_id": "string", "path": "string", "excerpt_id": "string", "claim": "string"}],
}

STRICT_JSON_INSTRUCTIONS = (
    "Return exactly one top-level JSON object.",
    "Do not use Markdown fences.",
    "Do not add prose before or after the JSON object.",
    "Use result_type=insufficient_evidence when evidence is inadequate.",
    "Never emit bare text as the abstention.",
    "Never invent paths or evidence references.",
)


def typed_abstention_probe() -> PromptProfile:
    return PromptProfile(
        profile_id="typed_abstention_probe",
        result_type="insufficient_evidence",
        schema=ABSTENTION_SCHEMA,
        instructions=STRICT_JSON_INSTRUCTIONS,
    )


def typed_proposal_probe() -> PromptProfile:
    return PromptProfile(
        profile_id="typed_proposal_probe",
        result_type="cognitive_proposal",
        schema=COGNITIVE_PROPOSAL_SCHEMA,
        instructions=STRICT_JSON_INSTRUCTIONS,
    )


def render_delta_prompt(messages: Sequence[Mapping[str, str]]) -> str:
    return "\n\n".join(f"{message.get('role', 'user').upper()}:\n{message.get('content', '')}" for message in messages)


class NativeChatBackend(Protocol):
    def create_chat_completion(self, **kwargs: Any) -> Mapping[str, Any]:
        ...


def select_native_model_adapter(*, model_family: str, tokenizer_identity: str, chat_template_available: bool) -> ModelAdapter:
    template_source = "gguf_metadata:tokenizer.chat_template" if chat_template_available else "backend_native_default"
    return ModelAdapter(
        adapter_id=f"{model_family}-native-chat-json-object-v1",
        model_family=model_family,
        native_chat_template_source=template_source,
        system_role_support=True,
        assistant_prefix_policy="backend_native_create_chat_completion",
        reasoning_mode_controls="none_detected",
        stop_token_policy=(),
        tool_call_policy="disabled",
        json_generation_capability="response_format_json_object",
        response_wrapper_policy="choices[0].message.content",
        tokenizer_identity=tokenizer_identity,
        backend_compatibility="llama_cpp.create_chat_completion",
    )


def _chat_content(response: Mapping[str, Any]) -> str:
    choices = response.get("choices") or ()
    if not choices:
        return ""
    first = choices[0] or {}
    if not isinstance(first, Mapping):
        return ""
    message = first.get("message") or {}
    if isinstance(message, Mapping):
        return str(message.get("content") or "")
    return str(first.get("text") or "")


class NativeTemplateDeltaAdapter:
    """DELTA-side cognitive adapter that delegates rendering to the model backend."""

    def __init__(self, backend: NativeChatBackend, profile: ModelAdapter) -> None:
        self.backend = backend
        self.profile = profile

    def complete_json(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
        top_p: float = 1.0,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
    ) -> dict[str, Any]:
        normalized_messages = [
            {"role": str(message.get("role") or "user"), "content": str(message.get("content") or "")}
            for message in messages
        ]
        response = self.backend.create_chat_completion(
            messages=normalized_messages,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return {
            "adapter": self.profile.to_record(),
            "raw_backend_response": dict(response),
            "raw_content": _chat_content(response),
            "response_wrapper_policy": self.profile.response_wrapper_policy,
            "structured_output": self.profile.json_generation_capability,
        }


def extract_exactly_one_json_object(text: str, *, allow_native_wrapper: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    raw = str(text or "").strip()
    if allow_native_wrapper:
        pattern = rf"^{re.escape(allow_native_wrapper)}\s*(\{{.*\}})\s*$"
        match = re.fullmatch(pattern, raw, re.S)
        if match:
            raw = match.group(1).strip()
    if raw.startswith("```"):
        return None, {"status": "rejected", "reason": "markdown_fence_rejected"}
    decoder = json.JSONDecoder()
    try:
        value, end = decoder.raw_decode(raw)
    except json.JSONDecodeError as exc:
        return None, {"status": "rejected", "reason": "json_decode_error", "detail": str(exc)}
    if raw[end:].strip():
        return None, {"status": "rejected", "reason": "trailing_or_multiple_content_rejected"}
    if not isinstance(value, dict):
        return None, {"status": "rejected", "reason": "top_level_json_not_object"}
    return value, {"status": "parsed"}


def validate_typed_abstention(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(payload, Mapping):
        reasons.append("missing_object")
        payload = {}
    if payload.get("result_type") != "insufficient_evidence":
        reasons.append("wrong_result_type")
    if not payload.get("problem_id"):
        reasons.append("missing_problem_id")
    if not isinstance(payload.get("supported_findings"), list):
        reasons.append("supported_findings_not_list")
    missing = payload.get("missing_evidence")
    if not isinstance(missing, list) or not missing:
        reasons.append("missing_evidence_required")
    elif not all(isinstance(item, Mapping) and item.get("required_clause") and item.get("reason") for item in missing):
        reasons.append("missing_evidence_item_invalid")
    if not isinstance(payload.get("requested_evidence"), list) or not payload.get("requested_evidence"):
        reasons.append("requested_evidence_required")
    if not isinstance(payload.get("limitations"), list) or not payload.get("limitations"):
        reasons.append("limitations_required")
    uncertainty = payload.get("uncertainty")
    if not isinstance(uncertainty, Mapping) or "score" not in uncertainty or not uncertainty.get("reason"):
        reasons.append("uncertainty_invalid")
    else:
        try:
            score = float(uncertainty["score"])
        except (TypeError, ValueError):
            reasons.append("uncertainty_score_invalid")
        else:
            if score < 0.0 or score > 1.0:
                reasons.append("uncertainty_score_invalid")
    return {"accepted": not reasons, "reasons": tuple(reasons), "schema": "typed_abstention_v1"}


def validate_typed_proposal(
    payload: Mapping[str, Any] | None,
    *,
    evidence_references: Sequence[str],
    inspected_paths: Sequence[str],
    evaluator_path: str,
    allowed_authority: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        payload = {}
    candidate = {
        **dict(payload),
        "proposal_origin": payload.get("proposal_origin") or "local_model",
        "model_output_authoritative": False,
        "provider_calls": 0,
        "network": False,
        "deployment": False,
        "credentials": False,
        "source_mutation": False,
    }
    return grounding_result(
        candidate,
        evidence_references=evidence_references,
        inspected_paths=inspected_paths,
        evaluator_path=evaluator_path,
        allowed_authority=allowed_authority,
    )


def compare_prompts(native_rendered: str, delta_rendered: str) -> dict[str, Any]:
    return {
        "same": native_rendered == delta_rendered,
        "native_length": len(native_rendered),
        "delta_length": len(delta_rendered),
        "delta_hard_coded_roles": "SYSTEM:" in delta_rendered or "USER:" in delta_rendered,
        "native_has_template_markers": any(marker in native_rendered for marker in ("<|", "[INST]", "<s>", "<start_of_turn>")),
    }
