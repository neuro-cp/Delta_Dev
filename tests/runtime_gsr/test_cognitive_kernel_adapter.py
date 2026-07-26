from orchestration.runtime.cognitive_kernel_adapter import (
    ModelAdapter,
    NativeTemplateDeltaAdapter,
    compare_prompts,
    extract_exactly_one_json_object,
    render_delta_prompt,
    select_native_model_adapter,
    typed_abstention_probe,
    typed_proposal_probe,
    validate_typed_abstention,
    validate_typed_proposal,
)


def test_model_adapter_record_preserves_native_template_policy():
    record = ModelAdapter(
        adapter_id="llama-native-chat-v1",
        model_family="llama",
        native_chat_template_source="gguf_metadata:tokenizer.chat_template",
        system_role_support=True,
        assistant_prefix_policy="backend_native",
        reasoning_mode_controls="none",
        stop_token_policy=("<|eot_id|>",),
        tool_call_policy="disabled",
        json_generation_capability="response_format_json_object",
        response_wrapper_policy="choices.message.content",
        tokenizer_identity="gguf_tokenizer",
        backend_compatibility="llama_cpp.create_chat_completion",
    ).to_record()

    assert record["adapter_id"] == "llama-native-chat-v1"
    assert record["native_chat_template_source"] == "gguf_metadata:tokenizer.chat_template"
    assert record["json_generation_capability"] == "response_format_json_object"


def test_prompt_profiles_select_typed_abstention_and_proposal():
    abstention = typed_abstention_probe()
    proposal = typed_proposal_probe()

    assert abstention.profile_id == "typed_abstention_probe"
    assert abstention.schema["result_type"] == "insufficient_evidence"
    assert proposal.profile_id == "typed_proposal_probe"
    assert "diagnosis" in proposal.schema


def test_typed_abstention_validation_accepts_schema_object():
    result = validate_typed_abstention({
        "result_type": "insufficient_evidence",
        "problem_id": "p1",
        "supported_findings": [],
        "missing_evidence": [{"required_clause": "trace", "reason": "not supplied"}],
        "requested_evidence": ["focused failing output"],
        "limitations": ["No grounded proposal can be produced."],
        "uncertainty": {"score": 0.9, "reason": "direct trace absent"},
    })

    assert result["accepted"] is True


def test_typed_proposal_validation_uses_existing_grounding():
    result = validate_typed_proposal(
        {
            "problem_id": "p1",
            "diagnosis": "Duplicate replay lacks accepted-report check.",
            "first_incorrect_transition": "stale output -> passed replay",
            "implementation_path": "orchestration/runtime/autonomy_advisory_assistance.py",
            "focused_test_path": "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
            "independent_evaluator_path": "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
            "bounded_strategy": ["add replay guard"],
            "limitations": ["single replay branch only"],
            "uncertainty": {"score": 0.2, "reason": "focused fixture"},
            "evidence_references": [{
                "source_id": "ck1r-a18-replay",
                "path": "orchestration/runtime/autonomy_advisory_assistance.py",
                "excerpt_id": "duplicate-replay",
                "claim": "the duplicate branch reads stale artifacts",
            }],
        },
        evidence_references=("ck1r-a18-replay:duplicate-replay",),
        inspected_paths=("orchestration/runtime/autonomy_advisory_assistance.py",),
        evaluator_path="tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        allowed_authority={"provider_calls": 0, "network": False, "deployment": False, "credentials": False, "source_mutation": False},
    )

    assert result["accepted"] is True


def test_exact_one_object_extraction_rejects_prose_and_multiple_objects():
    payload, audit = extract_exactly_one_json_object('{"status":"ok"} extra')
    assert payload is None
    assert audit["reason"] == "trailing_or_multiple_content_rejected"

    payload, audit = extract_exactly_one_json_object('{"a":1}{"b":2}')
    assert payload is None
    assert audit["reason"] == "trailing_or_multiple_content_rejected"


def test_fenced_output_policy_rejects_markdown():
    payload, audit = extract_exactly_one_json_object('```json\n{"status":"ok"}\n```')

    assert payload is None
    assert audit["reason"] == "markdown_fence_rejected"


def test_no_semantic_auto_repair_for_bare_insufficient_evidence():
    payload, audit = extract_exactly_one_json_object("insufficient_evidence")

    assert payload is None
    assert audit["reason"] == "json_decode_error"


def test_native_versus_delta_prompt_comparison_records_mismatch():
    messages = [{"role": "system", "content": "Return JSON."}, {"role": "user", "content": "Ping."}]
    delta = render_delta_prompt(messages)
    native = "<|begin_of_text|><|start_header_id|>system<|end_header_id|>Return JSON.<|eot_id|>"

    comparison = compare_prompts(native, delta)

    assert comparison["same"] is False
    assert comparison["delta_hard_coded_roles"] is True
    assert comparison["native_has_template_markers"] is True


def test_grounding_still_rejects_prohibited_paths_and_authority():
    result = validate_typed_proposal(
        {
            "problem_id": "p1",
            "diagnosis": "bad",
            "first_incorrect_transition": "bad",
            "implementation_path": "DELTA-75/secret.py",
            "focused_test_path": "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
            "independent_evaluator_path": "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
            "bounded_strategy": ["bad"],
            "limitations": ["bad"],
            "uncertainty": {"score": 0.2, "reason": "bad"},
            "required_authority": ["primary_source_mutation"],
            "evidence_references": [{
                "source_id": "bad",
                "path": "DELTA-75/secret.py",
                "excerpt_id": "x",
                "claim": "bad",
            }],
        },
        evidence_references=("ck1r-a18-replay:duplicate-replay",),
        inspected_paths=("orchestration/runtime/autonomy_advisory_assistance.py",),
        evaluator_path="tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        allowed_authority={"provider_calls": 0, "network": False, "deployment": False, "credentials": False, "source_mutation": False},
    )

    assert result["accepted"] is False
    assert "prohibited_path_rejected" in result["reasons"]
    assert "authority_expansion_primary_source_mutation" in result["reasons"]


def test_adapter_selection_by_model_family_uses_native_template_source():
    adapter = select_native_model_adapter(model_family="llama", tokenizer_identity="gpt2", chat_template_available=True)

    assert adapter.model_family == "llama"
    assert adapter.native_chat_template_source == "gguf_metadata:tokenizer.chat_template"
    assert adapter.backend_compatibility == "llama_cpp.create_chat_completion"


def test_native_template_adapter_delegates_without_hard_coded_prompt_fallback():
    class FakeBackend:
        def __init__(self):
            self.calls = []

        def create_chat_completion(self, **kwargs):
            self.calls.append(kwargs)
            return {"choices": [{"message": {"role": "assistant", "content": '{"status":"ok","model_family":"llama"}'}}]}

    backend = FakeBackend()
    profile = select_native_model_adapter(model_family="llama", tokenizer_identity="gpt2", chat_template_available=True)
    adapter = NativeTemplateDeltaAdapter(backend, profile)
    result = adapter.complete_json(
        [{"role": "system", "content": "Return JSON."}, {"role": "user", "content": "Ping."}],
        max_tokens=64,
    )

    assert backend.calls
    assert backend.calls[0]["messages"][0]["role"] == "system"
    assert backend.calls[0]["messages"][1]["role"] == "user"
    assert backend.calls[0]["response_format"] == {"type": "json_object"}
    assert "SYSTEM:" not in str(backend.calls[0]["messages"])
    assert result["raw_content"] == '{"status":"ok","model_family":"llama"}'


def test_repaired_adapter_output_passes_exact_json_identity_extraction():
    class FakeBackend:
        def create_chat_completion(self, **kwargs):
            return {"choices": [{"message": {"role": "assistant", "content": '{"status":"ok","model_family":"llama"}'}}]}

    profile = select_native_model_adapter(model_family="llama", tokenizer_identity="gpt2", chat_template_available=True)
    result = NativeTemplateDeltaAdapter(FakeBackend(), profile).complete_json([{"role": "user", "content": "Ping"}], max_tokens=64)
    payload, audit = extract_exactly_one_json_object(result["raw_content"])

    assert audit["status"] == "parsed"
    assert payload == {"status": "ok", "model_family": "llama"}


def test_native_template_adapter_preserves_assistant_prefix_policy_and_stop_tokens():
    profile = select_native_model_adapter(model_family="llama", tokenizer_identity="gpt2", chat_template_available=True)
    record = profile.to_record()

    assert record["assistant_prefix_policy"] == "backend_native_create_chat_completion"
    assert record["stop_token_policy"] == ()
