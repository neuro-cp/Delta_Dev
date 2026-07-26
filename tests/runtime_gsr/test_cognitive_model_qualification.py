from pathlib import Path

from orchestration.runtime.cognitive_model_qualification import (
    InferenceProfileRecord,
    LocalModelInventoryRecord,
    build_routing_policy,
    candidate_stop,
    classify_candidate,
    file_sha256,
    select_candidates,
    validate_inference_profile,
)


def test_local_model_inventory_record_persists_exact_path_and_digest(tmp_path: Path):
    model = tmp_path / "Qwen3.5-9B-Q4_K_M.gguf"
    model.write_bytes(b"model")
    record = LocalModelInventoryRecord(
        model_id="qwen35",
        model_family="qwen",
        display_name="Qwen3.5 9B",
        absolute_path=str(model),
        file_digest=file_sha256(model),
        file_size=model.stat().st_size,
        gguf_architecture="qwen3",
        quantization="Q4_K_M",
        tokenizer_type="qwen",
        native_chat_template_present=True,
        context_length=4096,
        multimodal_capability=False,
        projector_requirement="none",
        llama_cpp_compatible=True,
        role_candidates=("general_cognitive_model",),
        source_of_metadata="test",
        inventory_timestamp="2026-07-25T00:00:00",
    ).to_record()

    assert record["absolute_path"] == str(model)
    assert record["file_digest"] == file_sha256(model)


def test_inference_profile_validation_accepts_bounded_llama_cpp_profile():
    profile = InferenceProfileRecord(
        inference_profile_id="qwen35-q4-ctx4096",
        model_id="qwen35",
        model_digest="abc",
        backend="llama_cpp",
        backend_version="0.3.32",
        context_length=4096,
        prompt_token_count=100,
        maximum_output_tokens=1200,
        temperature=0.1,
        top_p=0.9,
        top_k=20,
        repeat_penalty=1.1,
        seed=7,
        gpu_layer_count=-1,
        cpu_thread_count=8,
        batch_size=None,
        micro_batch_size=None,
        flash_attention="disabled",
        kv_cache_type="backend_default",
        kv_cache_placement="backend_default",
        mmap=True,
        mlock=False,
        split_mode="none",
        structured_output_mode="response_format_json_object",
        reasoning_mode="native_default",
        stop_token_policy=(),
        timeout_seconds=300,
        peak_vram_mb=None,
        peak_ram_mb=None,
        load_time_seconds=1.0,
        time_to_first_token_seconds=None,
        generation_tokens_per_second=None,
        prompt_tokens_per_second=None,
        final_load_disposition="unloaded",
    ).to_record()

    assert validate_inference_profile(profile)["accepted"] is True


def test_role_classification_requires_final_grounding_and_negative_rejection():
    result = {
        "json_identity_passed": True,
        "typed_abstention_passed": True,
        "stage_1_passed": True,
        "stage_2_passed": True,
        "stage_3_passed": True,
        "stage_4_passed": True,
        "final_grounding_passed": True,
        "negative_control_rejected": True,
    }

    assert classify_candidate(result, code_specialist=True) == (
        "qualified_general_cognitive_model",
        "qualified_code_specialist",
    )


def test_role_classification_does_not_promote_json_only_model():
    assert classify_candidate({"json_identity_passed": True, "typed_abstention_passed": True}) == ("qualified_for_typed_abstention_only",)


def test_candidate_stop_rules_include_backend_hardware_and_repeated_stage_failures():
    assert candidate_stop({"backend_incompatible": True}) is True
    assert candidate_stop({"hardware_blocked": True}) is True
    assert candidate_stop({"consecutive_stage_failures": 2}) is True
    assert candidate_stop({"consecutive_stage_failures": 1}) is False


def test_candidate_priority_prefers_new_qwen_models_then_control():
    records = [
        {"model_id": "meta-llama-3-1-8b"},
        {"model_id": "qwen2-5-coder-7b-instruct"},
        {"model_id": "qwen3-5-9b"},
    ]

    selected = select_candidates(records)

    assert [item["model_id"] for item in selected] == ["qwen3-5-9b", "qwen2-5-coder-7b-instruct", "meta-llama-3-1-8b"]


def test_routing_policy_is_model_neutral_and_not_production_active():
    policy = build_routing_policy(
        general={"model_id": "qwen35", "inference_profile_id": "p1", "qualified_stages": [1, 2, 3, 4], "qualification_status": "qualified_general_cognitive_model"},
        code={"model_id": "coder", "inference_profile_id": "p2", "qualified_stages": [3, 4], "qualification_status": "qualified_code_specialist"},
        senior=None,
    )

    assert policy["production_activation"] is False
    assert policy["general_cognitive_model"]["model_id"] == "qwen35"
    assert policy["code_specialist"]["qualified_stages"] == (3, 4)


def test_invalid_inference_profile_rejected():
    result = validate_inference_profile({"backend": "external_provider", "context_length": 0})

    assert result["accepted"] is False
    assert "unsupported_backend" in result["reasons"]
