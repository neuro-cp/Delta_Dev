from __future__ import annotations

from orchestration.runtime.tp5_noncanonical_persistent_pilot import (
    APPROVAL_PREFIX,
    APPROVAL_SCOPE,
    TARGET_STORE_NAME,
    answer_tp5_question,
    build_pilot_candidate,
    build_tp5_approval,
    create_operator_session,
    is_tp5_question,
    parse_tp5_approval,
    persist_candidate,
    replay_pilot_store,
    run_tp5_demo_pilot,
    validate_governance,
    validate_rollback,
    write_tp5_reports,
)


def test_tp5_candidate_preserves_required_provenance_fields():
    session = create_operator_session(
        "Operator notes checksum recovery; however execution remains unresolved.",
        operator_id="operator-a",
        source_references=("operator-session://a", "report://demo"),
    )
    candidate = build_pilot_candidate(session)

    assert candidate.canonical is False
    assert candidate.source_references == ("operator-session://a", "report://demo")
    assert candidate.source_checksum == session.checksum
    assert candidate.supporting_evidence == candidate.source_references
    assert candidate.uncertainty == "explicit_uncertainty"
    assert candidate.contradictions


def test_tp5_exact_operator_approval_required():
    session = create_operator_session("Operator reviewed a stable claim.")
    candidate = build_pilot_candidate(session)
    approval_text = build_tp5_approval(candidate.candidate_id, approved_by="operator-demo")
    approval = parse_tp5_approval(approval_text, candidate.candidate_id)

    assert approval.valid is True
    assert approval.approval_scope == APPROVAL_SCOPE
    assert approval.target_store == TARGET_STORE_NAME
    assert parse_tp5_approval("yes, save it", candidate.candidate_id).valid is False
    assert parse_tp5_approval(
        f"{APPROVAL_PREFIX}\ncandidate_id=wrong\napproved_by=user\napproval_scope={APPROVAL_SCOPE}\ntarget_store={TARGET_STORE_NAME}",
        candidate.candidate_id,
    ).valid is False


def test_tp5_rejects_persistence_without_exact_approval(tmp_path):
    session = create_operator_session("Operator reviewed a stable claim.")
    candidate = build_pilot_candidate(session)
    result = persist_candidate(candidate, "save it", store_dir=tmp_path, write=True)

    assert result["persisted"] is False
    assert "exact_operator_approval_required" in result["blocks"]
    assert not (tmp_path / "records.jsonl").exists()


def test_tp5_persists_one_noncanonical_record_with_audit_and_rollback(tmp_path):
    session = create_operator_session("Operator reviewed a stable claim.", source_references=("operator://source",))
    candidate = build_pilot_candidate(session)
    approval = build_tp5_approval(candidate.candidate_id)
    result = persist_candidate(candidate, approval, store_dir=tmp_path, write=True)

    assert result["persisted"] is True
    assert result["record"]["canonical"] is False
    assert result["record"]["authoritative"] is False
    assert result["record"]["source_references"] == ["operator://source"] or result["record"]["source_references"] == ("operator://source",)
    assert result["audit"]["event_type"] == "noncanonical_pilot_persisted"
    assert result["rollback"]["rollback_token"]
    assert (tmp_path / "records.jsonl").exists()
    assert (tmp_path / "audit.jsonl").exists()
    assert (tmp_path / "rollback.jsonl").exists()


def test_tp5_replay_is_read_only_and_preserves_uncertainty(tmp_path):
    payload = run_tp5_demo_pilot(store_dir=tmp_path, write=True)
    replay = replay_pilot_store(store_dir=tmp_path)

    assert payload["persistence"]["persisted"] is True
    assert replay["read_only"] is True
    assert replay["mutation_performed"] is False
    assert replay["record_count"] == 1
    assert replay["provenance_preserved"] is True
    assert replay["uncertainty_preserved"] is True


def test_tp5_rollback_validation_is_deterministic(tmp_path):
    run_tp5_demo_pilot(store_dir=tmp_path, write=True)
    rollback = validate_rollback(store_dir=tmp_path)

    assert rollback["passed"] is True
    assert rollback["all_records_have_rollback"] is True
    assert rollback["deterministic"] is True
    assert rollback["deletion_requires_governance"] is True
    assert rollback["historical_reconstruction_available"] is True


def test_tp5_governance_and_safety_flags(tmp_path):
    payload = run_tp5_demo_pilot(store_dir=tmp_path, write=True)
    governance = validate_governance(payload["persistence"], payload["replay"], payload["rollback"])
    safety = payload["safety"]

    assert governance["passed"] is True
    assert governance["casual_approval_rejected"] is True
    assert safety["model_training_performed"] is False
    assert safety["fine_tuning_performed"] is False
    assert safety["weight_update_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["canonical_memory_enabled"] is False
    assert safety["live_knowledge_mutation_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["hyb1_promoted"] is False
    assert safety["model_b_default_changed"] is False


def test_tp5_reports_and_local_answer_route(tmp_path):
    payload = write_tp5_reports(store_dir=tmp_path)
    answer = answer_tp5_question("How does rollback work in TP5?")

    assert payload["passed"] is True
    assert payload["final_recommendation"] == "PROCEED_PHASE_10_CONTROLLED_OPERATIONAL_VALIDATION"
    assert is_tp5_question("What is noncanonical persistence?")
    assert answer["phase"] == "TP5 Controlled Noncanonical Persistent Pilot"
    assert "rollback token" in answer["answer_text"]
