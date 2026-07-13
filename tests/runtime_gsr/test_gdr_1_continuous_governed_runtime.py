from __future__ import annotations

import json
from dataclasses import replace

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


def _doe_bundle():
    request = gsr.make_development_objective_request(
        title="Improve disposable fixture symbol coverage",
        statement="Raise fixture_symbol_coverage from 0.0 to 1.0 without reducing protected_safety.",
        target_metric="fixture_symbol_coverage",
        baseline_metrics={"fixture_symbol_coverage": 0.0, "protected_safety": 1.0},
        success_thresholds={"fixture_symbol_coverage": 1.0},
        protected_metric_floors={"protected_safety": 1.0},
        allowed_source_paths=("sample.py",),
        maximum_attempts=3,
        stagnation_limit=2,
        regression_limit=1,
        requested_sequence=1500,
    )
    authorization = gsr.make_development_objective_authorization(request, issued_sequence=1501, expiration_sequence=1600)
    objective_result = gsr.authorize_development_objective(request, authorization, sequence=1502)
    assert objective_result.accepted is True
    contract = gsr.make_development_objective_acceptance_contract(objective_result.objective, objective_result.state)
    decomposition = gsr.decompose_development_objective(objective_result.objective, objective_result.state, contract, requested_subgoal_count=1, sequence=1503)
    queue = gsr.create_development_attempt_queue(objective_result.state, decomposition, artifact_chain_starting_digest="DOE-GENESIS", authorization_identity=authorization.objective_authorization_id)
    state = gsr.make_governed_runtime_state(
        objective_result.objective,
        contract,
        attempt_budget=3,
        cycle_budget=3,
        sandbox_execution_budget=3,
        sequence=1504,
    )
    budget = gsr.make_governed_runtime_budget(max_runtime_cycles=3, max_doe_attempts=3, max_pcm_sandbox_executions=3)
    return objective_result.objective, contract, queue, state, budget


def test_gdr_1a_checkpoint_persistence_and_integrity(tmp_path):
    objective, contract, _queue, state, budget = _doe_bundle()
    checkpoint_path = tmp_path / "gdr_1_runtime_state.json"
    write = gsr.write_governed_runtime_checkpoint(state, checkpoint_path=checkpoint_path, max_state_bytes=budget.max_persisted_state_bytes, sequence=1510)
    assert write.accepted is True
    assert write.checkpoint.atomic_write_completed is True
    assert write.checkpoint.integrity_verified is True
    loaded = gsr.load_governed_runtime_checkpoint(checkpoint_path=checkpoint_path, objective=objective, contract=contract, max_state_bytes=budget.max_persisted_state_bytes)
    assert loaded.accepted is True
    assert loaded.state.state_digest == state.state_digest

    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    payload["schema_version"] = "bad"
    checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")
    bad_schema = gsr.load_governed_runtime_checkpoint(checkpoint_path=checkpoint_path, objective=objective, contract=contract, max_state_bytes=budget.max_persisted_state_bytes)
    assert bad_schema.accepted is False
    assert bad_schema.reason == "invalid_schema"

    wrong_path = gsr.write_governed_runtime_checkpoint(state, checkpoint_path=tmp_path / "other.json", max_state_bytes=budget.max_persisted_state_bytes, sequence=1511)
    assert wrong_path.accepted is False
    assert wrong_path.reason == "state_path_not_allowlisted"


def test_gdr_1b_scheduler_denies_parallel_reordered_and_budget_exhausted():
    _objective, _contract, queue, state, budget = _doe_bundle()
    decision = gsr.select_governed_runtime_attempt(state, queue, budget=budget, sequence=1520)
    assert decision.disposition == "run_next_authorized_attempt"
    assert decision.selected_attempt_id

    parallel = gsr.select_governed_runtime_attempt(replace(state, active_attempt_count=2), queue, budget=budget, sequence=1521)
    assert parallel.disposition == "suspend_invalid_state"
    assert parallel.reason == "parallel_attempt_denied"

    exhausted = gsr.select_governed_runtime_attempt(replace(state, remaining_cycle_budget=0), queue, budget=budget, sequence=1522)
    assert exhausted.disposition == "pause_budget"
    assert exhausted.reason == "cycle_budget_exhausted"

    second_attempt = queue.attempts[1]
    reordered_state = replace(state, completed_attempt_summaries=({"attempt_id": gsr.deserialize(gsr.DevelopmentAttemptPlan, second_attempt).attempt_id},))
    reordered = gsr.select_governed_runtime_attempt(reordered_state, queue, budget=budget, sequence=1523)
    assert reordered.disposition == "suspend_invalid_state"


def test_gdr_1c_runtime_cycle_updates_checkpoint_and_review_queue(tmp_path):
    objective, contract, queue, state, budget = _doe_bundle()
    checkpoint_path = tmp_path / "gdr_1_runtime_state.json"
    result = gsr.run_governed_runtime_cycle(
        state,
        objective,
        contract,
        queue,
        budget=budget,
        metric_after={"fixture_symbol_coverage": 1.0, "protected_safety": 1.0},
        pcm_chain_digest="CHAIN1",
        candidate_patch_id="candidate-a",
        checkpoint_path=checkpoint_path,
        sequence=1530,
    )
    assert result.accepted is True
    assert result.attempt_executed is True
    assert result.attempts_executed == 1
    assert result.sandbox_executions == 1
    assert result.next_state.campaign_disposition == "complete_success"
    assert result.next_state.best_candidate_id == "candidate-a"
    assert checkpoint_path.exists()
    queue_result = gsr.create_governed_runtime_review_queue(result.next_state, contract)
    assert len(queue_result.items) == 1
    item = gsr.deserialize(gsr.GovernedRuntimeReviewItem, queue_result.items[0])
    assert item.recommended_disposition == "eligible_for_operator_application_review"
    assert queue_result.application_authorization_created is False
    assert queue_result.git_operation_performed is False


def test_gdr_1d_1e_budget_and_drift_controls():
    objective, contract, _queue, state, budget = _doe_bundle()
    ok, reason = gsr.check_governed_runtime_budgets(state, budget)
    assert ok is True
    exhausted, exhausted_reason = gsr.check_governed_runtime_budgets(replace(state, remaining_sandbox_execution_budget=0), budget)
    assert exhausted is False
    assert exhausted_reason == "sandbox_execution_budget_exhausted"

    repeated = replace(state, repeated_patch_count=2)
    drift = gsr.assess_governed_runtime_drift(
        repeated,
        objective_digest=repeated.objective_digest,
        expected_objective_digest=repeated.objective_digest,
        source_scope=("sample.py",),
        allowed_source_scope=("sample.py",),
        latest_chain_digest="CHAIN",
        expected_previous_digest="CHAIN",
    )
    assert drift.disposition == "suspend_cycle_detected"

    scope = gsr.assess_governed_runtime_drift(
        state,
        objective_digest=state.objective_digest,
        expected_objective_digest=state.objective_digest,
        source_scope=("other.py",),
        allowed_source_scope=("sample.py",),
        latest_chain_digest="CHAIN",
        expected_previous_digest="CHAIN",
    )
    assert scope.disposition == "suspend_scope_drift"

    integrity = gsr.assess_governed_runtime_drift(
        state,
        objective_digest=state.objective_digest,
        expected_objective_digest=state.objective_digest,
        source_scope=("sample.py",),
        allowed_source_scope=("sample.py",),
        latest_chain_digest="CHAIN2",
        expected_previous_digest="CHAIN1",
    )
    assert integrity.disposition == "suspend_integrity_failure"


def test_gdr_1f_resume_requires_clean_boundary_and_operator_authorization():
    _objective, _contract, _queue, state, _budget = _doe_bundle()
    paused = replace(state, recovery_review_required=True, clean_resume_boundary="paused_for_operator")
    paused = replace(paused, state_digest=gsr.governed_runtime_state_digest(paused))
    request = gsr.make_governed_runtime_resume_request(paused, requested_sequence=1540)
    authorization = gsr.make_governed_runtime_resume_authorization(request, issued_sequence=1541, expiration_sequence=1550)
    result = gsr.authorize_governed_runtime_resume(paused, request, authorization, sequence=1542)
    assert result.accepted is True
    assert result.authorization_consumed is True
    assert result.state.recovery_review_required is False

    replay = gsr.authorize_governed_runtime_resume(paused, request, result.consumed_authorization, sequence=1543)
    assert replay.accepted is False
    assert replay.reason == "resume_authorization_unavailable"

    mid_execution = replace(paused, clean_resume_boundary="mid_execution")
    mid_execution = replace(mid_execution, state_digest=gsr.governed_runtime_state_digest(mid_execution))
    mid_request = gsr.make_governed_runtime_resume_request(mid_execution, requested_sequence=1544)
    mid_auth = gsr.make_governed_runtime_resume_authorization(mid_request, issued_sequence=1545, expiration_sequence=1550)
    denied = gsr.authorize_governed_runtime_resume(mid_execution, mid_request, mid_auth, sequence=1546)
    assert denied.accepted is False
    assert denied.reason == "resume_boundary_denied"


def test_gdr_1h_progressive_pilots_and_closure(tmp_path):
    objective, contract, queue, state, budget = _doe_bundle()
    checkpoint_path = tmp_path / "gdr_1_runtime_state.json"
    final_state, review_queue, evidence = gsr.run_progressive_governed_runtime_pilot(
        objective,
        contract,
        queue,
        initial_state=state,
        budget=budget,
        checkpoint_path=checkpoint_path,
        metric_sequence=(
            {"fixture_symbol_coverage": 0.4, "protected_safety": 1.0},
            {"fixture_symbol_coverage": 1.0, "protected_safety": 1.0},
        ),
        chain_digests=("CHAIN1", "CHAIN2"),
        candidate_ids=("candidate-a", "candidate-b"),
        sequence=1550,
        interrupt_after_cycle=2,
    )
    assert final_state.campaign_disposition == "complete_success"
    assert evidence.cycle_count == 2
    assert evidence.resume_event_count == 1
    assert evidence.sandbox_created_count == evidence.sandbox_cleanup_count
    assert len(review_queue.items) == 1
    assert gsr.evaluate_tracked_source_branch_readiness(final_state) == "tracked_source_branch_pilot_deferred"

    closure_authorization = gsr.make_governed_runtime_closure_authorization(final_state, review_queue, issued_sequence=1560, expiration_sequence=1570)
    closure = gsr.evaluate_governed_runtime_closure(final_state, review_queue, evidence, closure_authorization, sequence=1561)
    assert closure.accepted is True
    assert closure.reason == "accepted_for_gdr_1_closure"
    assert closure.authorization_consumed is True
    assert closure.runtime_active is False
    assert closure.background_thread_started is False
    assert closure.active_worktree_mutated is False
    assert closure.provider_called is False
    assert closure.model_invoked is False
    assert closure.git_operation_performed is False


def test_gdr_1h_stagnation_budget_and_closure_denials(tmp_path):
    objective, contract, queue, state, budget = _doe_bundle()
    stagnation_state, _queue_result, stagnation_evidence = gsr.run_progressive_governed_runtime_pilot(
        objective,
        contract,
        queue,
        initial_state=state,
        budget=budget,
        checkpoint_path=tmp_path / "gdr_1_runtime_state.json",
        metric_sequence=(
            {"fixture_symbol_coverage": 0.0, "protected_safety": 1.0},
            {"fixture_symbol_coverage": 0.0, "protected_safety": 1.0},
        ),
        chain_digests=("CHAIN1", "CHAIN2"),
        candidate_ids=("candidate-a", "candidate-a"),
        sequence=1570,
    )
    assert stagnation_state.campaign_disposition in {"suspend_stagnation", "suspend_cycle_detected"}
    assert stagnation_evidence.cycle_count >= 1

    budget_state = replace(state, remaining_cycle_budget=0)
    decision = gsr.select_governed_runtime_attempt(budget_state, queue, budget=budget, sequence=1580)
    assert decision.disposition == "pause_budget"

    bad_queue = gsr.GovernedRuntimeReviewQueue(state.runtime_id)
    evidence = gsr.GovernedRuntimePilotEvidence(
        pilot_id="pilot",
        actual_duration_units=1,
        cycle_count=1,
        attempt_count=1,
        process_count_observed=1,
        thread_count_observed=1,
        memory_observation="not_measured_external_counter",
        disk_bytes_observed=0,
        sandbox_created_count=1,
        sandbox_cleanup_count=0,
        checkpoint_write_count=1,
        resume_event_count=0,
        candidate_changes=("candidate-a",),
        final_disposition="complete_success",
    )
    auth = gsr.make_governed_runtime_closure_authorization(state, bad_queue, issued_sequence=1581, expiration_sequence=1590)
    denied = gsr.evaluate_governed_runtime_closure(state, bad_queue, evidence, auth, sequence=1582)
    assert denied.accepted is False
    assert denied.reason == "rejected_cleanup_failure"
