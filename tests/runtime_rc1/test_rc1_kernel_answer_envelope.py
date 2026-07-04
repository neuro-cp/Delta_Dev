from orchestration.runtime.rc1_kernel_answer_envelope import wrap_local_answer_with_kernel_envelope
from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer


def test_kernel_answer_envelope_preserves_local_answer_text():
    data = run_v29_local_answer("What is DELTA?")
    wrapped = wrap_local_answer_with_kernel_envelope("What is DELTA?", data)
    assert wrapped["draft"]["answer_text"] == data["draft"]["answer_text"]
    assert wrapped["kernel_envelope"]["answer_text_preserved"] is True


def test_kernel_answer_envelope_is_non_mutating():
    wrapped = wrap_local_answer_with_kernel_envelope("What is DELTA?", run_v29_local_answer("What is DELTA?"))
    envelope = wrapped["kernel_envelope"]
    assert envelope["mutating"] is False
    assert envelope["provider_required"] is False
    assert envelope["memory_mutation_performed"] is False
    assert envelope["knowledge_mutation_performed"] is False
    assert envelope["transaction"]["mutation_performed"] is False


def test_kernel_answer_envelope_contains_dynamic_pipeline():
    wrapped = wrap_local_answer_with_kernel_envelope(
        "Why did Project Atlas fail after semantic consolidation?",
        run_v29_local_answer("Why did Project Atlas fail after semantic consolidation?"),
    )
    capabilities = [step["capability"] for step in wrapped["kernel_envelope"]["pipeline"]["steps"]]
    assert "semantic_consolidation_cycle" in capabilities
    assert "vertical_runtime_trace" in capabilities
