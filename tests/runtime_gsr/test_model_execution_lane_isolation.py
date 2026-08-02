import pytest

from integration.model_runtime.execution_lanes import ModelExecutionLane
from integration.model_runtime.inference_types import CanonicalInferenceResult
from integration.model_runtime.model_registry import ModelSpec
from integration.model_runtime.model_session import GRAMMAR_SUPPORTED, LlamaGrammar, cognitive_operation_grammar
from integration.model_runtime.prompt_builder import build_prompt
from integration.model_runtime.provider_manager import ProviderManager
from integration.model_runtime import gguf_model_runner
from orchestration.runtime.active_cognitive_loop import (
    LedgerBackedCognitiveModelRunner,
    OPERATION_TYPES,
    adapt_operation_response,
)
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


def _spec(name="qwen"):
    return ModelSpec(
        name=name,
        path=f"/models/{name}.gguf",
        tier=1,
        description=name,
        context_length=4096,
        family="qwen",
    )


def test_chat_lane_keeps_conversational_prompt_and_answer_confidence_contract():
    prompt = build_prompt({
        "question": "What is fire?",
        "task_type": "rc2_conversation",
        "execution_lane": ModelExecutionLane.CHAT.value,
    })

    assert "Answer like a friendly" not in prompt
    assert "You are part of an automated AI reasoning pipeline." in prompt
    assert '{"answer":"<your answer here>","confidence":0.0}' in prompt
    assert "Question:\nWhat is fire?" in prompt


def test_cognitive_lane_bypasses_chat_prompt_wrapping():
    exact = '{"operation_result_type":"compare_evidence_result"}'

    prompt = build_prompt({
        "question": exact,
        "task_type": "active_cognitive_json_operation",
        "execution_lane": ModelExecutionLane.COGNITIVE_OPERATION.value,
    })

    assert prompt == exact
    assert "Required format" not in prompt
    assert "<your answer here>" not in prompt


def test_provider_manager_records_lane_and_fails_closed_on_unknown_lane():
    seen = {}

    class FakeRunner:
        def produce_output(self, input_payload):
            seen.update(input_payload)
            return CanonicalInferenceResult(
                provider="local",
                model_id="qwen",
                answer="ok",
                raw_output="ok",
                confidence=0.5,
                latency_seconds=0.0,
                prompt_tokens=1,
                response_tokens=1,
            )

    manager = ProviderManager(
        available_models={"qwen": _spec()},
        runner_factory=lambda _spec: FakeRunner(),
    )
    manager.infer(model_name="qwen", prompt="hello", task_type="rc2_conversation")
    assert seen["execution_lane"] == ModelExecutionLane.CHAT.value

    with pytest.raises(ValueError, match="unsupported_model_execution_lane"):
        manager.infer(
            model_name="qwen",
            prompt="hello",
            task_type="rc2_conversation",
            metadata={"execution_lane": "unknown"},
        )


def test_chat_lane_can_still_use_legacy_non_qwen_model():
    seen = {}

    class FakeRunner:
        def __init__(self, model_id):
            self.model_id = model_id

        def produce_output(self, input_payload):
            seen["model_id"] = self.model_id
            seen["input_payload"] = input_payload
            return CanonicalInferenceResult(
                provider="local",
                model_id=self.model_id,
                answer="legacy model answer",
                raw_output="legacy model answer",
                confidence=0.5,
                latency_seconds=0.0,
                prompt_tokens=3,
                response_tokens=3,
            )

    manager = ProviderManager(
        available_models={"phi4": _spec("phi4")},
        runner_factory=lambda spec: FakeRunner(spec.name),
    )
    result = manager.infer(
        model_name="phi4",
        prompt="legacy chat prompt",
        task_type="rc2_conversation",
        metadata={"execution_lane": ModelExecutionLane.CHAT.value},
    )

    assert result.model_id == "phi4"
    assert seen["model_id"] == "phi4"
    assert seen["input_payload"]["execution_lane"] == ModelExecutionLane.CHAT.value


def test_cognitive_exact_prompt_executor_declares_lane_and_skips_chat_naturalization():
    seen = {}

    class FakeProviderManager:
        def infer(self, **kwargs):
            seen.update(kwargs)
            return CanonicalInferenceResult(
                provider="local",
                model_id="qwen",
                answer='{"operation_result_type":"compare_evidence_result"}',
                raw_output='{"operation_result_type":"compare_evidence_result"}',
                confidence=0.7,
                latency_seconds=0.0,
                prompt_tokens=1,
                response_tokens=1,
            )

    runner = LedgerBackedCognitiveModelRunner(ledger=object(), provider_manager=FakeProviderManager())
    result = runner._execute_exact_prompt(
        '{"operation_result_type":"compare_evidence_result"}',
        {"selected_model": "qwen", "lane": "analysis"},
    )

    assert seen["prompt"] == '{"operation_result_type":"compare_evidence_result"}'
    assert seen["task_type"] == "active_cognitive_json_operation"
    assert seen["metadata"]["execution_lane"] == ModelExecutionLane.COGNITIVE_OPERATION.value
    assert result["answer"].startswith("{")


def test_cognitive_parse_failure_does_not_fallback_to_chat_prose():
    adapted = adapt_operation_response("A friendly concise answer.")

    assert adapted.adapted_response == {}
    assert "malformed_output" in adapted.adapter_rejection_reasons


def test_chat_and_cognition_identical_text_have_distinct_ledger_identity(tmp_path):
    ledger = LocalModelRequestResultLedger(tmp_path)
    text = "same local model text"
    chat = ledger.create_or_reuse_request(
        semantic_identity="lane:chat:" + text,
        question=text,
        requester_type="chat",
        question_objective="conversation",
    )
    cognition = ledger.create_or_reuse_request(
        semantic_identity="lane:cognition:" + text,
        question=text,
        requester_type="active_cognitive_loop",
        question_objective="compare_evidence",
    )

    assert chat["request_id"] != cognition["request_id"]
    assert chat["semantic_identity"].startswith("lane:chat")
    assert cognition["semantic_identity"].startswith("lane:cognition")


def test_gguf_runner_selects_chat_or_cognitive_grammar(monkeypatch):
    calls = []

    class FakeSession:
        def __init__(self, **_kwargs):
            pass

        def load(self, _model_spec):
            pass

        def generate(self, prompt, *, structured_json=True, cognitive_json=False, cognitive_operation_type=""):
            calls.append({
                "prompt": prompt,
                "structured_json": structured_json,
                "cognitive_json": cognitive_json,
                "cognitive_operation_type": cognitive_operation_type,
            })
            return '{"answer":"ok","confidence":0.8}' if structured_json else '{"operation_result_type":"compare_evidence_result","interpretation":"ok","evidence_refs":[],"contrary_evidence_considered":[],"uncertainty":"bounded","assumptions":[],"recommended_state_transition":"add_supporting_evidence","recommended_action":"","next_evidence_need":"","next_focus_proposal":""}'

        def unload(self):
            pass

    monkeypatch.setattr(gguf_model_runner, "ModelSession", FakeSession)
    monkeypatch.setattr(gguf_model_runner, "get_model_spec", lambda _name: _spec())

    runner = gguf_model_runner.GGUFModelRunner("qwen")
    runner.produce_output({
        "question": "chat",
        "prompt": "chat",
        "task_type": "rc2_conversation",
        "execution_lane": ModelExecutionLane.CHAT.value,
        "metadata": {},
    })
    runner.produce_output({
        "question": '{"operation_result_type":"compare_evidence_result"}',
        "prompt": '{"operation_result_type":"compare_evidence_result"}',
        "task_type": "active_cognitive_json_operation",
        "execution_lane": ModelExecutionLane.COGNITIVE_OPERATION.value,
        "metadata": {"operation_type": "interpret_state"},
    })

    assert calls[0]["structured_json"] is True
    assert calls[0]["cognitive_json"] is False
    assert "Required format" in calls[0]["prompt"]
    assert calls[1]["structured_json"] is False
    assert calls[1]["cognitive_json"] is True
    assert calls[1]["cognitive_operation_type"] == "interpret_state"
    assert calls[1]["prompt"] == '{"operation_result_type":"compare_evidence_result"}'


def test_cognitive_operation_grammar_constructs_when_supported():
    if not GRAMMAR_SUPPORTED:
        pytest.skip("llama-cpp grammar support unavailable")

    operations = ["", *OPERATION_TYPES]
    grammars = [LlamaGrammar.from_string(cognitive_operation_grammar(operation)) for operation in operations]

    assert all(grammar is not None for grammar in grammars)


def test_compare_evidence_grammar_enumerates_allowed_transition_values():
    grammar = cognitive_operation_grammar("compare_evidence")

    assert 'enum-recommended-state-transition ::= "\\"add_supporting_evidence\\""' in grammar
    assert '"\\"continue_with_hypothesis\\""' not in grammar
    assert 'enum-operation-result-type ::= "\\"compare_evidence_result\\""' in grammar


def test_retry_hypothesis_operations_use_the_hypothesis_grammar_contract():
    for operation in ("reformulate_node_specific_hypothesis", "repair_node_specific_hypothesis_format"):
        grammar = cognitive_operation_grammar(operation)

        assert '"\\"hypothesis_statement\\""' in grammar
        assert '"\\"scope\\""' in grammar
        assert '"\\"supporting_evidence_refs\\""' in grammar
        assert '"\\"next_focus_proposal\\""' not in grammar
        assert 'enum-recommended-state-transition ::= "\\"propose_hypothesis\\""' in grammar
