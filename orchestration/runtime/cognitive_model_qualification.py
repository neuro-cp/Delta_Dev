"""Model-neutral records for local cognitive model qualification."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


MODEL_QUALIFICATION_SCHEMA = "cognitive_model_qualification_v1"
ROLE_CLASSIFICATIONS = (
    "qualified_general_cognitive_model",
    "qualified_code_specialist",
    "qualified_local_senior_analyst",
    "qualified_for_typed_abstention_only",
    "qualified_for_evidence_selection_only",
    "qualified_for_grounded_diagnosis_only",
    "qualified_for_path_selection_only",
    "qualified_for_bounded_strategy_only",
    "schema_compliant_but_semantically_ungrounded",
    "model_not_suitable_for_cognitive_proposals",
    "backend_incompatible",
    "hardware_blocked",
    "hardware_operationally_impractical",
    "not_present",
)


@dataclass(frozen=True)
class LocalModelInventoryRecord:
    model_id: str
    model_family: str
    display_name: str
    absolute_path: str
    file_digest: str
    file_size: int
    gguf_architecture: str
    quantization: str
    tokenizer_type: str
    native_chat_template_present: bool
    context_length: int
    multimodal_capability: bool
    projector_requirement: str
    llama_cpp_compatible: bool
    role_candidates: tuple[str, ...]
    source_of_metadata: str
    inventory_timestamp: str

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InferenceProfileRecord:
    inference_profile_id: str
    model_id: str
    model_digest: str
    backend: str
    backend_version: str
    context_length: int
    prompt_token_count: int
    maximum_output_tokens: int
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float
    seed: int
    gpu_layer_count: int
    cpu_thread_count: int
    batch_size: int | None
    micro_batch_size: int | None
    flash_attention: str
    kv_cache_type: str
    kv_cache_placement: str
    mmap: bool
    mlock: bool
    split_mode: str
    structured_output_mode: str
    reasoning_mode: str
    stop_token_policy: tuple[str, ...]
    timeout_seconds: int
    peak_vram_mb: int | None
    peak_ram_mb: int | None
    load_time_seconds: float | None
    time_to_first_token_seconds: float | None
    generation_tokens_per_second: float | None
    prompt_tokens_per_second: float | None
    final_load_disposition: str

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def file_sha256(path: str | Path, *, chunk_size: int = 16 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_candidate(result: Mapping[str, Any], *, code_specialist: bool = False, senior: bool = False) -> tuple[str, ...]:
    if result.get("not_present"):
        return ("not_present",)
    if result.get("backend_incompatible"):
        return ("backend_incompatible",)
    if result.get("hardware_blocked"):
        return ("hardware_blocked",)
    if result.get("hardware_operationally_impractical"):
        return ("hardware_operationally_impractical",)
    if result.get("final_grounding_passed") and result.get("negative_control_rejected"):
        roles = ["qualified_general_cognitive_model"]
        if code_specialist:
            roles.append("qualified_code_specialist")
        if senior:
            roles.append("qualified_local_senior_analyst")
        return tuple(roles)
    if result.get("stage_4_passed"):
        return ("qualified_for_bounded_strategy_only",)
    if result.get("stage_3_passed"):
        return ("qualified_for_path_selection_only",)
    if result.get("stage_2_passed"):
        return ("qualified_for_grounded_diagnosis_only",)
    if result.get("stage_1_passed"):
        return ("qualified_for_evidence_selection_only",)
    if result.get("typed_abstention_passed") and result.get("json_identity_passed"):
        return ("qualified_for_typed_abstention_only",)
    if result.get("json_valid"):
        return ("schema_compliant_but_semantically_ungrounded",)
    return ("model_not_suitable_for_cognitive_proposals",)


def candidate_stop(result: Mapping[str, Any]) -> bool:
    return any(
        bool(result.get(key))
        for key in (
            "backend_incompatible",
            "hardware_blocked",
            "hardware_operationally_impractical",
            "json_identity_failed",
            "repeated_envelope_echo",
            "repeated_ungrounded_references",
            "process_instability",
        )
    ) or int(result.get("consecutive_stage_failures") or 0) >= 2


def build_routing_policy(
    *,
    general: Mapping[str, Any] | None,
    code: Mapping[str, Any] | None,
    senior: Mapping[str, Any] | None,
) -> dict[str, Any]:
    def entry(record: Mapping[str, Any] | None, *, optional: bool = False) -> dict[str, Any] | None:
        if not record:
            return None
        return {
            "model_id": record.get("model_id"),
            "inference_profile_id": record.get("inference_profile_id"),
            "qualified_stages": tuple(record.get("qualified_stages") or ()),
            "qualification_status": record.get("qualification_status"),
            "fallback": None,
            "optional": optional,
        }

    return {
        "schema": MODEL_QUALIFICATION_SCHEMA,
        "general_cognitive_model": entry(general),
        "code_specialist": entry(code),
        "local_senior_analyst": entry(senior, optional=True),
        "production_activation": False,
    }


def validate_inference_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    for field in ("inference_profile_id", "model_id", "model_digest", "backend", "context_length", "maximum_output_tokens", "structured_output_mode"):
        if not profile.get(field):
            reasons.append(f"missing_{field}")
    if int(profile.get("context_length") or 0) <= 0:
        reasons.append("invalid_context_length")
    if int(profile.get("maximum_output_tokens") or 0) <= 0:
        reasons.append("invalid_maximum_output_tokens")
    if profile.get("backend") not in {"llama_cpp"}:
        reasons.append("unsupported_backend")
    return {"accepted": not reasons, "reasons": tuple(reasons)}


def select_candidates(records: Sequence[Mapping[str, Any]], *, limit: int = 4) -> tuple[Mapping[str, Any], ...]:
    priority = (
        "qwen3.5-9b",
        "qwen3-5-9b",
        "qwen2.5-coder-7b",
        "qwen2-5-coder-7b",
        "qwen3.6-35b",
        "qwen3-6-35b",
        "llama-3.1-8b",
        "llama-3-1-8b",
    )

    def score(record: Mapping[str, Any]) -> tuple[int, str]:
        haystack = " ".join(
            str(record.get(key) or "")
            for key in ("model_id", "name", "display_name", "absolute_path", "path")
        ).lower()
        for index, marker in enumerate(priority):
            if marker in haystack:
                return (index, haystack)
        return (len(priority), haystack)

    return tuple(sorted(records, key=score)[:limit])
