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


def test_v29_answer_engine_answers_rc1_activation_questions():
    readiness = run_v29_local_answer("What does RC1 readiness mean?")
    activation = run_v29_local_answer("What is the next safe activation?")
    waves = run_v29_local_answer("What is the activation wave plan?")
    learning = run_v29_local_answer("Can DELTA learn yet?")

    assert readiness["local_answer"]["topic_id"] == "rc1_readiness"
    assert "does not authorize live providers" in readiness["draft"]["answer_text"]
    assert activation["local_answer"]["topic_id"] == "next_safe_activation"
    assert "Wave 0 manual RC1 validation" in activation["draft"]["answer_text"]
    assert waves["local_answer"]["topic_id"] == "activation_wave_plan"
    assert "Wave 7 limited learning/consolidation pilot" in waves["draft"]["answer_text"]
    assert learning["local_answer"]["topic_id"] == "can_learn_yet"
    assert "remain disabled" in learning["draft"]["answer_text"]


def test_v29_answer_engine_answers_rc1_wave_chain_questions():
    wave = run_v29_local_answer("What wave is DELTA on?")
    fixture = run_v29_local_answer("Can DELTA retrieve from fixture records?")
    provider = run_v29_local_answer("Can DELTA call providers yet?")
    knowledge = run_v29_local_answer("Can DELTA write knowledge yet?")

    assert wave["local_answer"]["topic_id"] == "wave_state"
    assert "Wave 7" in wave["draft"]["answer_text"]
    assert fixture["local_answer"]["topic_id"] == "fixture_retrieval_status"
    assert "read-only mode" in fixture["draft"]["answer_text"]
    assert provider["local_answer"]["topic_id"] == "provider_call_status"
    assert "remain disabled" in provider["draft"]["answer_text"]
    assert knowledge["local_answer"]["topic_id"] == "knowledge_write_status"
    assert "canonical knowledge writes" in knowledge["draft"]["answer_text"]


def test_v29_answer_engine_answers_integrated_runtime_questions():
    know = run_v29_local_answer("What do you know?")
    records = run_v29_local_answer("Which semantic records support this?")
    audit = run_v29_local_answer("Show the audit path.")
    rollback = run_v29_local_answer("Show the rollback path.")

    assert know["local_answer"]["topic_id"] == "integrated_what_know"
    assert "noncanonical semantic records" in know["draft"]["answer_text"]
    assert records["local_answer"]["topic_id"] == "integrated_supporting_records"
    assert "source checksums" in records["draft"]["answer_text"]
    assert audit["local_answer"]["topic_id"] == "integrated_audit_path"
    assert "no live mutation" in audit["draft"]["answer_text"]
    assert rollback["local_answer"]["topic_id"] == "integrated_rollback_path"
    assert "no canonical write occurred" in rollback["draft"]["answer_text"]
