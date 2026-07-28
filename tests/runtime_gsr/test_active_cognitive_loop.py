import pytest

from orchestration.runtime.active_cognitive_loop import (
    ActiveCognitiveLoopError,
    EvidenceRef,
    LedgerBackedCognitiveModelRunner,
    OPERATION_TYPES,
    _runtime_payload_from_operation_response,
    operation_schema_for,
    operation_schema_registry,
    adapt_operation_response,
    abandon_focus,
    apply_operation_result,
    build_operation_request,
    build_working_memory_packet,
    compile_operation_prompt_snapshot,
    complete_focus,
    evaluate_operation_response,
    evaluate_cognitive_episode,
    initialize_episode,
    interrupt_focus,
    read_episode_state,
    resume_focus,
    run_cognitive_cycle,
    run_episode,
    select_attention,
    validate_model_result,
    write_episode_state,
)


def _evidence():
    return (
        EvidenceRef("repo_runtime", "repo", "DELTA has persistent runtime pieces", "goals, ledgers, and local model routing exist"),
        EvidenceRef("repo_gap", "repo", "Contrary evidence: active loop is missing", "components do not yet continuously select focus and revise beliefs"),
        EvidenceRef("repo_useful", "repo", "Useful artifact target", "a bounded architecture diagnosis can be produced"),
    )


def _episode():
    return initialize_episode(
        title="active cognitive architecture test",
        goal_summary="turn available runtime pieces into one active cognitive loop",
        expected_state="useful artifact produced",
        evidence=_evidence(),
    )


def test_active_loop_runs_focus_memory_model_revision_and_useful_learning():
    state = run_episode(_episode(), cycles=5)
    evaluation = evaluate_cognitive_episode(state)

    assert evaluation["passed"] is True
    assert state.completed is True
    assert state.model_call_count >= 2
    assert state.attention is not None
    assert state.attention.active_focus_id
    assert state.working_memory_packets
    assert state.hypotheses[-1].revision_parent_id
    assert state.learning_updates
    assert state.useful_artifacts


def test_focus_lifecycle_supports_establish_continue_interrupt_resume_abandon_and_complete():
    state = _episode()
    first_attention = select_attention(state, state.next_focus_candidates or ())
    assert first_attention.active_focus_id == ""

    state = run_cognitive_cycle(state)
    focus_id = state.attention.active_focus_id
    assert state.attention.transition_journal[-1]["transition"] == "establish_focus"

    continued = select_attention(state, state.attention.candidate_focuses)
    assert continued.active_focus_id == focus_id
    assert continued.transition_journal[-1]["transition"] == "continue_focus"

    interrupted = interrupt_focus(state, reason="operator needs a decision", priority="high")
    assert interrupted.loop_state == "blocked_operator_decision"
    assert interrupted.attention.interruption_reason == "operator needs a decision"

    resumed = resume_focus(interrupted, reason="operator approved continuation")
    assert resumed.loop_state == "selecting_focus"
    assert resumed.attention.active_focus_id == focus_id
    assert resumed.attention.interruption_reason == ""

    abandoned = abandon_focus(resumed, reason="focus no longer has enough evidence")
    assert abandoned.loop_state == "selecting_focus"
    assert abandoned.attention.active_focus_id == ""
    assert focus_id in abandoned.attention.previous_focus_ids

    completed = complete_focus(resumed, summary="focus produced a useful bounded result")
    assert completed.completed is True
    assert completed.useful_artifacts[-1]["artifact_type"] == "focus_completion_summary"


def test_restart_round_trip_preserves_episode_state(tmp_path):
    state = run_episode(_episode(), cycles=5)
    path = tmp_path / "active_loop_state.json"
    write_episode_state(path, state)

    restored = read_episode_state(path)

    assert restored == state
    assert evaluate_cognitive_episode(restored)["passed"] is True


def test_working_memory_is_bounded_and_provenance_checked():
    state = _episode()
    state = run_cognitive_cycle(state)
    packet = state.working_memory_packets[0]

    assert packet.size_budget <= 8
    assert set(packet.provenance_refs).issubset({item.evidence_id for item in state.evidence})
    assert "no protected paths" in packet.operator_constraints


def test_model_result_rejects_self_certified_or_invented_evidence():
    state = run_cognitive_cycle(_episode())
    packet = build_working_memory_packet(state, sequence=len(state.cycles) + 1)
    request = build_operation_request(state, packet, operation_type="compare_evidence", model_identity="test")

    result = validate_model_result(request, packet, {
        "interpretation": "I declare final success.",
        "evidence_refs": ["missing_evidence"],
        "recommended_state_transition": "final_status_success",
    })

    assert result.accepted is False
    assert "self_certified_success" in result.rejection_reasons
    assert any(reason.startswith("unsupported_evidence_reference") for reason in result.rejection_reasons)


def test_resume_requires_real_interruption():
    state = run_cognitive_cycle(_episode())

    with pytest.raises(ActiveCognitiveLoopError, match="focus_not_interrupted"):
        resume_focus(state)


def test_ledger_backed_runner_uses_shared_request_lifecycle():
    class FakeLedger:
        def __init__(self):
            self.created = None
            self.approved = None
            self.executed = None

        def create_or_reuse_request(self, **kwargs):
            self.created = kwargs
            return {"request_id": "req-1", "lifecycle_state": "pending_operator_approval"}

        def approve_request(self, request_id, reason):
            self.approved = (request_id, reason)

        def execute_claimed_request(self, request_id, context):
            self.executed = (request_id, context)
            return {"request_id": request_id, "lifecycle_state": "completed", "result_id": "res-1"}

        def observe_result(self, result_id):
            assert result_id == "res-1"
            return {
                "model_identity": "fake-local-model",
                "response_reference": (
                    '{"interpretation":"ledger-backed hypothesis",'
                    '"evidence_refs":["repo_runtime"],'
                    '"contrary_evidence_considered":["repo_gap"],'
                    '"uncertainty":"bounded",'
                    '"recommended_state_transition":"propose_hypothesis"}'
                ),
            }

    state = _episode()
    state = run_cognitive_cycle(state)
    packet = build_working_memory_packet(state, sequence=len(state.cycles) + 1)
    request = build_operation_request(state, packet, operation_type="compare_evidence", model_identity="ledger")
    ledger = FakeLedger()
    runner = LedgerBackedCognitiveModelRunner(ledger=ledger, provider_manager=object(), authority_reason="test_authority")

    raw = runner(request, packet)

    assert ledger.created["requester_type"] == "active_cognitive_loop"
    assert ledger.created["question_objective"] == "compare_evidence"
    assert ledger.approved == ("req-1", "test_authority")
    assert ledger.executed[0] == "req-1"
    assert callable(ledger.executed[1]["executor"])
    assert raw["model_identity"] == "fake-local-model"
    assert raw["evidence_refs"] == ["repo_runtime"]


def test_ledger_backed_runner_reuses_completed_equivalent_request():
    class CompletedLedger:
        def __init__(self):
            self.created = None
            self.approved = False
            self.executed = False

        def create_or_reuse_request(self, **kwargs):
            self.created = kwargs
            return {"request_id": "req-completed", "lifecycle_state": "completed", "result_id": "res-completed"}

        def approve_request(self, request_id, reason):
            self.approved = True

        def execute_claimed_request(self, request_id, context):
            self.executed = True
            raise AssertionError("completed request must not be claimed again")

        def observe_result(self, result_id):
            assert result_id == "res-completed"
            return {
                "model_identity": "fake-local-model",
                "response_reference": (
                    '{"interpretation":"reused completed evidence",'
                    '"evidence_refs":["repo_runtime"],'
                    '"contrary_evidence_considered":[],'
                    '"uncertainty":"bounded",'
                    '"recommended_state_transition":"propose_hypothesis"}'
                ),
            }

    state = run_cognitive_cycle(_episode())
    packet = build_working_memory_packet(state, sequence=len(state.cycles) + 1)
    request = build_operation_request(state, packet, operation_type="compare_evidence", model_identity="ledger")
    ledger = CompletedLedger()
    runner = LedgerBackedCognitiveModelRunner(ledger=ledger, provider_manager=object(), authority_reason="test_authority")

    raw = runner(request, packet)

    assert ledger.created["requester_type"] == "active_cognitive_loop"
    assert ledger.approved is False
    assert ledger.executed is False
    assert raw["model_identity"] == "fake-local-model"
    assert raw["interpretation"] == "reused completed evidence"


def test_ledger_runner_exact_prompt_executor_uses_provider_manager_without_chat_compactor():
    class FakeProviderManager:
        def __init__(self):
            self.calls = []

        def infer(self, **kwargs):
            self.calls.append(kwargs)

            class Result:
                answer = '{"operation_result_type":"compare_evidence_result","interpretation":"ok"}'
                confidence = 0.8
                model_id = "fake-model"
                latency_seconds = 0.1
                response_tokens = 9

            return Result()

    manager = FakeProviderManager()
    runner = LedgerBackedCognitiveModelRunner(ledger=object(), provider_manager=manager)
    result = runner._execute_exact_prompt("EXACT PROMPT JSON", {"selected_model": "qwen", "lane": "analysis"})

    assert result["executed"] is True
    assert result["answer"].startswith("{")
    assert manager.calls[0]["prompt"] == "EXACT PROMPT JSON"
    assert manager.calls[0]["task_type"] == "active_cognitive_json_operation"


def _request_and_packet(operation_type="compare_evidence"):
    state = run_cognitive_cycle(_episode())
    packet = build_working_memory_packet(state, sequence=len(state.cycles) + 1)
    request = build_operation_request(state, packet, operation_type=operation_type, model_identity="test-model")
    return request, packet


def _valid_response(operation_type="compare_evidence", transition="add_conflicting_evidence"):
    return {
        "operation_result_type": operation_type + "_result",
        "interpretation": "The supporting evidence shows runtime pieces exist, while contrary evidence shows they were not yet connected into a reliable active loop.",
        "evidence_refs": ["repo_runtime", "repo_useful"],
        "contrary_evidence_considered": ["repo_gap"],
        "uncertainty": "bounded to supplied repository evidence",
        "assumptions": ["the packet evidence is sufficient for this bounded comparison"],
        "recommended_state_transition": transition,
        "recommended_action": "revise the active hypothesis before claiming a useful outcome",
        "next_evidence_need": "",
        "next_focus_proposal": "qualify the prompt boundary against contrary evidence",
    }


def test_production_prompt_snapshot_is_exact_digestable_and_separates_evidence():
    request, packet = _request_and_packet("compare_evidence")

    snapshot = compile_operation_prompt_snapshot(request, packet, request_identity_suffix="unit", retry_sequence=2)
    again = compile_operation_prompt_snapshot(request, packet, request_identity_suffix="unit", retry_sequence=2)

    assert snapshot == again
    assert snapshot.prompt_text.startswith("OUTPUT CONTRACT")
    assert snapshot.prompt_byte_digest == again.prompt_byte_digest
    assert snapshot.prompt_length < 9000
    assert "evidence_for" in snapshot.prompt_text
    assert "contrary_evidence" in snapshot.prompt_text
    assert snapshot.evidence_ids_supplied
    assert snapshot.contrary_evidence_ids_supplied == ("repo_gap",)
    assert snapshot.request_identity == again.request_identity


def test_compare_prompt_requires_exact_ids_in_evidence_arrays():
    request, packet = _request_and_packet("compare_evidence")

    snapshot = compile_operation_prompt_snapshot(request, packet)

    assert "ID ARRAY RULES:" in snapshot.prompt_text
    assert "array values for evidence/ref fields must be exact IDs" in snapshot.prompt_text
    assert "evidence_refs values must be chosen from: repo_runtime, repo_useful" in snapshot.prompt_text
    assert "contrary_evidence_considered values must be chosen from: repo_gap" in snapshot.prompt_text
    assert "contrary_evidence_considered must include at least one contrary_evidence ID" in snapshot.prompt_text


def test_insufficient_evidence_prompt_uses_empty_ref_array_when_no_ids():
    state = initialize_episode(
        title="missing evidence prompt test",
        goal_summary="identify missing local evidence",
        expected_state="bounded evidence request produced",
        evidence=(),
    )
    state = run_cognitive_cycle(state, requested_operation="interpret_state")
    packet = build_working_memory_packet(state, sequence=len(state.cycles) + 1)
    request = build_operation_request(state, packet, operation_type="declare_insufficient_evidence", model_identity="test")

    snapshot = compile_operation_prompt_snapshot(request, packet)

    assert "attempted_evidence_refs values must be chosen from: none" in snapshot.prompt_text
    assert "attempted_evidence_refs must be [] because no valid IDs are supplied; do not write none" in snapshot.prompt_text


def test_mechanical_adapter_removes_single_fence_and_rejects_ambiguous_text():
    raw = '```json\n{"operation_result_type":"compare_evidence_result","interpretation":"ok"}\n```'
    adapted = adapt_operation_response(raw)
    assert adapted.adapter_transformations == ("removed_single_outer_markdown_fence",)
    assert adapted.adapter_rejection_reasons == ()
    assert adapted.adapted_response["operation_result_type"] == "compare_evidence_result"

    ambiguous = adapt_operation_response('Here is JSON: {"interpretation":"hidden"} thanks')
    assert "malformed_output" in ambiguous.adapter_rejection_reasons
    assert ambiguous.adapted_response == {}


def test_response_evaluator_rejects_schema_prompt_echo_and_unsupported_success():
    request, packet = _request_and_packet("compare_evidence")
    bad = adapt_operation_response(
        '{"operation_result_type":"compare_evidence_result",'
        '"interpretation":"operation_result_type recommended_state_transition: the loop is functioning successfully completed.",'
        '"evidence_refs":["repo_runtime"],'
        '"contrary_evidence_considered":[],'
        '"uncertainty":"low",'
        '"assumptions":[],'
        '"recommended_state_transition":"add_supporting_evidence",'
        '"recommended_action":"declare success",'
        '"next_evidence_need":"",'
        '"next_focus_proposal":""}'
    )

    evaluation = evaluate_operation_response(request, packet, bad)

    assert evaluation.passed is False
    assert "schema_echo" in evaluation.failure_classifications
    assert "ignored_contrary_evidence" in evaluation.failure_classifications
    assert "unsupported_success_claim" in evaluation.failure_classifications
    assert "self_certification" in evaluation.failure_classifications


def test_response_evaluator_rejects_invented_evidence_and_insufficient_escape():
    request, packet = _request_and_packet("compare_evidence")
    escaped = dict(_valid_response())
    escaped["evidence_refs"] = ["invented"]
    escaped["recommended_state_transition"] = "declare_insufficient_evidence"

    evaluation = evaluate_operation_response(request, packet, escaped)

    assert "invented_evidence_reference" in evaluation.failure_classifications
    assert "invalid_state_transition" in evaluation.failure_classifications


def test_response_evaluator_accepts_grounded_compare_and_is_order_invariant():
    request, packet = _request_and_packet("compare_evidence")
    response = _valid_response()

    first = evaluate_operation_response(request, packet, response)
    reordered_packet = packet.__class__(**{
        **packet.as_record(),
        "relevant_evidence": tuple(reversed(packet.relevant_evidence)),
        "conflicting_evidence": tuple(reversed(packet.conflicting_evidence)),
    })
    second = evaluate_operation_response(request, reordered_packet, response)

    assert first.passed is True
    assert second.passed is True
    assert set(first.positive_observations) >= {
        "schema_valid",
        "evidence_grounded",
        "contrary_evidence_addressed",
        "state_transition_valid",
    }


def test_response_evaluator_requires_real_revision_for_revision_family():
    request, packet = _request_and_packet("revise_hypothesis")
    no_change = dict(_valid_response("revise_hypothesis", "declare_insufficient_evidence"))
    no_change["operation_result_type"] = "revise_hypothesis_result"

    rejected = evaluate_operation_response(request, packet, no_change)
    assert "invalid_state_transition" in rejected.failure_classifications
    assert "no_hypothesis_change" in rejected.failure_classifications

    revision = dict(_valid_response("revise_hypothesis", "revise_hypothesis"))
    revision["operation_result_type"] = "revise_hypothesis_result"
    revision["prior_hypothesis_id"] = "prior-hypothesis"
    revision["revised_statement"] = "The hypothesis should be narrowed because contrary evidence weakens the broad claim."
    revision["revision_reason"] = "Contrary evidence requires a narrower hypothesis."
    revision["new_confidence_state"] = "contested"
    accepted = evaluate_operation_response(request, packet, revision)
    assert accepted.passed is True
    assert "meaningful_revision" in accepted.positive_observations


def test_summarize_learning_consumes_contrary_evidence_through_evidence_refs():
    request, packet = _request_and_packet("summarize_learning")
    raw = {
        "operation_result_type": "summarize_learning_result",
        "lesson": "The runtime can progress, but the prior gap evidence narrows the claim.",
        "evidence_refs": ["repo_runtime", "repo_gap"],
        "unresolved_questions": ["Which live episode should run next?"],
        "uncertainty": "bounded to supplied repository evidence",
        "recommended_state_transition": "summarize_learning",
    }

    result = validate_model_result(request, packet, _runtime_payload_from_operation_response("summarize_learning", raw))

    assert result.accepted is True
    assert result.rejection_reasons == ()


def test_summarize_learning_prompt_allows_contrary_ids_in_evidence_refs():
    request, packet = _request_and_packet("summarize_learning")

    snapshot = compile_operation_prompt_snapshot(request, packet)

    assert "evidence_refs values must be chosen from: repo_runtime, repo_useful, repo_gap" in snapshot.prompt_text
    assert "contrary_evidence_considered" not in snapshot.expected_response_schema


def test_summarize_learning_select_next_focus_still_creates_artifact():
    state = run_cognitive_cycle(_episode())
    state = run_cognitive_cycle(state)
    packet = build_working_memory_packet(state, sequence=len(state.cycles) + 1)
    request = build_operation_request(state, packet, operation_type="summarize_learning", model_identity="test")
    raw = {
        "lesson": "The loop can progress, but prior gap evidence keeps the next focus bounded.",
        "evidence_refs": ["repo_runtime", "repo_useful", "repo_gap"],
        "unresolved_questions": ["Which next focus should begin?"],
        "uncertainty": "bounded to supplied repository evidence",
        "recommended_state_transition": "select_next_focus",
    }
    result = validate_model_result(request, packet, _runtime_payload_from_operation_response("summarize_learning", raw))

    updated = apply_operation_result(state, packet, request, result, sequence=len(state.cycles) + 1)

    assert result.accepted is True
    assert updated.completed is True
    assert updated.learning_updates
    assert updated.useful_artifacts


def test_evaluator_rejects_fixture_name_dependent_generic_filler():
    request, packet = _request_and_packet("compare_evidence")
    response = dict(_valid_response())
    response["interpretation"] = "Not enough information."

    evaluation = evaluate_operation_response(request, packet, response)

    assert "generic_filler" in evaluation.failure_classifications


def test_operation_schema_registry_is_complete_and_unknown_fails_closed():
    registry = operation_schema_registry()

    assert set(registry) == set(OPERATION_TYPES)
    assert "interpret_state" in registry
    assert "compare_evidence" in registry
    assert registry["interpret_state"].schema_id == "operation-schema-interpret-state-v1"
    assert registry["compare_evidence"].schema_id == "operation-schema-compare-evidence-v1"
    assert registry["identify_evidence_need"].checkpoint_required is False
    assert registry["identify_evidence_need"].allowed_transitions == ("request_evidence",)
    assert all("compare-compatible" not in schema.schema_id for schema in registry.values())
    with pytest.raises(ActiveCognitiveLoopError, match="unknown_operation_schema"):
        operation_schema_for("not_a_real_operation")


def test_interpret_state_schema_excludes_revision_only_fields():
    schema = operation_schema_for("interpret_state")

    assert "state_summary" in schema.required_fields
    assert "recommended_next_operation" in schema.required_fields
    assert "contrary_evidence_considered" not in schema.required_fields
    assert "recommended_state_transition" not in schema.required_fields


def test_interpret_state_prompt_uses_operation_specific_schema():
    request, packet = _request_and_packet("interpret_state")
    snapshot = compile_operation_prompt_snapshot(request, packet)

    assert "state_summary" in snapshot.prompt_text
    assert "recommended_next_operation" in snapshot.prompt_text
    assert "contrary_evidence_considered" not in snapshot.expected_response_schema
    assert "recommended_state_transition" not in snapshot.expected_response_schema


def test_interpret_state_evaluator_accepts_minimal_grounded_schema():
    request, packet = _request_and_packet("interpret_state")
    response = {
        "state_summary": "The episode has usable runtime evidence and one unresolved prompt-boundary question.",
        "salient_observations": ["Runtime evidence is present.", "A useful target remains unresolved."],
        "evidence_refs": ["repo_runtime", "repo_useful"],
        "unresolved_questions": ["Which operation should run next?"],
        "uncertainty": "bounded to supplied local evidence",
        "recommended_next_operation": "compare_evidence",
    }

    evaluation = evaluate_operation_response(request, packet, response)

    assert evaluation.passed is True
    assert "schema_valid" in evaluation.positive_observations
    assert "evidence_grounded" in evaluation.positive_observations


def test_challenge_hypothesis_uses_operation_specific_contrary_field():
    request, packet = _request_and_packet("challenge_hypothesis")
    response = {
        "challenged_hypothesis_id": "prior-hypothesis",
        "vulnerability": "The active hypothesis depends on prior attempts being reliable.",
        "contrary_evidence_refs": ["repo_gap"],
        "disconfirming_observation": "A repeated failure would disconfirm the broad hypothesis.",
        "uncertainty": "bounded to contrary evidence",
        "recommended_state_transition": "weaken_hypothesis",
    }

    evaluation = evaluate_operation_response(request, packet, response)

    assert evaluation.passed is True
    assert "contrary_evidence_addressed" in evaluation.positive_observations


def test_challenge_hypothesis_rejects_assumption_as_vulnerability():
    request, packet = _request_and_packet("challenge_hypothesis")
    response = {
        "challenged_hypothesis_id": "prior-hypothesis",
        "vulnerability": "local evidence is complete for this bounded episode",
        "contrary_evidence_refs": ["repo_gap"],
        "disconfirming_observation": "A repeated failure would disconfirm the broad hypothesis.",
        "uncertainty": "bounded to contrary evidence",
        "recommended_state_transition": "weaken_hypothesis",
    }

    evaluation = evaluate_operation_response(request, packet, response)

    assert "vulnerability_copies_assumption" in evaluation.failure_classifications


def test_operation_specific_runtime_payload_bridges_to_consumer_contract():
    payload = _runtime_payload_from_operation_response(
        "challenge_hypothesis",
        {
            "challenged_hypothesis_id": "prior-hypothesis",
            "vulnerability": "The broad claim is weakened by prior failures.",
            "contrary_evidence_refs": ["repo_gap"],
            "disconfirming_observation": "Another failed run would falsify the broad claim.",
            "uncertainty": "bounded",
            "recommended_state_transition": "weaken_hypothesis",
        },
    )

    assert payload["operation_result_type"] == "challenge_hypothesis_result"
    assert payload["interpretation"] == "The broad claim is weakened by prior failures."
    assert payload["contrary_evidence_considered"] == ("repo_gap",)


def test_interpret_state_rejects_evidence_prose_and_blank_required_fields():
    request, packet = _request_and_packet("interpret_state")
    response = {
        "state_summary": "",
        "salient_observations": ["Runtime evidence is present."],
        "evidence_refs": ["Runtime evidence is present."],
        "unresolved_questions": ["Which operation should run next?"],
        "uncertainty": "",
        "recommended_next_operation": "compare_evidence",
    }

    evaluation = evaluate_operation_response(request, packet, response)

    assert "empty_required_field:state_summary" in evaluation.failure_classifications
    assert "empty_required_field:uncertainty" in evaluation.failure_classifications
    assert "invented_evidence_reference" in evaluation.failure_classifications
