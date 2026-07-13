from __future__ import annotations

from dataclasses import replace

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


def _request(**overrides) -> gsr.DevelopmentObjectiveRequest:
    data = {
        "title": "Improve disposable fixture symbol coverage",
        "statement": "Raise fixture_symbol_coverage from 0.0 to 1.0 without reducing protected_safety.",
        "target_metric": "fixture_symbol_coverage",
        "baseline_metrics": {"fixture_symbol_coverage": 0.0, "protected_safety": 1.0},
        "success_thresholds": {"fixture_symbol_coverage": 1.0},
        "protected_metric_floors": {"protected_safety": 1.0},
        "allowed_source_paths": ("sample.py",),
        "maximum_attempts": 3,
        "stagnation_limit": 2,
        "regression_limit": 1,
        "requested_sequence": 1200,
    }
    data.update(overrides)
    return gsr.make_development_objective_request(**data)


def _authorization(request: gsr.DevelopmentObjectiveRequest, **overrides) -> gsr.DevelopmentObjectiveAuthorization:
    data = {"issued_sequence": 1201, "expiration_sequence": 1300}
    data.update(overrides)
    return gsr.make_development_objective_authorization(request, **data)


def _authorized_objective():
    request = _request()
    authorization = _authorization(request)
    result = gsr.authorize_development_objective(request, authorization, sequence=1202)
    assert result.accepted is True
    return request, authorization, result


def test_doe_1a_measurable_objective_contract_accepts_exact_operator_scope():
    request, authorization, result = _authorized_objective()
    assert result.reason == "development_objective_authorized"
    assert result.authorization_consumed is True
    assert authorization.consumed is False
    assert result.consumed_authorization.consumed is True
    assert result.state.maximum_attempts == 3
    assert result.state.remaining_attempt_budget == 3
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.tracked_source_mutated is False
    assert result.provider_called is False
    assert result.model_invoked is False

    replay = gsr.authorize_development_objective(request, result.consumed_authorization, sequence=1203)
    assert replay.accepted is False
    assert replay.reason == "consumed"


def test_doe_1a_vague_missing_and_substituted_objectives_fail_closed():
    vague = _request(statement="improve yourself")
    assert gsr.authorize_development_objective(vague, _authorization(vague), sequence=1202).reason == "vague_objective_denied"

    missing_baseline = _request(baseline_metrics={"protected_safety": 1.0})
    assert gsr.authorize_development_objective(missing_baseline, _authorization(missing_baseline), sequence=1202).reason == "missing_baseline"

    missing_threshold = _request(success_thresholds={})
    assert gsr.authorize_development_objective(missing_threshold, _authorization(missing_threshold), sequence=1202).reason == "missing_threshold"

    unsafe_path = _request(allowed_source_paths=("../sample.py",))
    assert gsr.authorize_development_objective(unsafe_path, _authorization(unsafe_path), sequence=1202).reason == "path_traversal_or_forbidden_path"

    request = _request()
    authorization = replace(_authorization(request), success_thresholds={"fixture_symbol_coverage": 0.5})
    result = gsr.authorize_development_objective(request, authorization, sequence=1202)
    assert result.accepted is False
    assert result.reason == "threshold_substitution"


def test_doe_1b_acceptance_contract_states_are_exact_and_protected():
    _request_value, _authorization_value, result = _authorized_objective()
    contract = gsr.make_development_objective_acceptance_contract(result.objective, result.state)
    success = gsr.evaluate_development_objective_metrics(contract, {"fixture_symbol_coverage": 1.0, "protected_safety": 1.0}, sequence=1210, attempts_completed=1, maximum_attempts=3)
    assert success.state == "success_threshold_met"

    regression = gsr.evaluate_development_objective_metrics(contract, {"fixture_symbol_coverage": 1.0, "protected_safety": 0.5}, sequence=1211, attempts_completed=1, maximum_attempts=3)
    assert regression.state == "protected_regression"
    assert "protected_safety" in regression.protected_regressions

    budget = gsr.evaluate_development_objective_metrics(contract, {"fixture_symbol_coverage": 0.5, "protected_safety": 1.0}, sequence=1212, attempts_completed=3, maximum_attempts=3)
    assert budget.state == "budget_exhausted"

    paused = gsr.evaluate_development_objective_metrics(contract, {"fixture_symbol_coverage": 0.5, "protected_safety": 1.0}, sequence=1213, operator_paused=True)
    assert paused.state == "operator_paused"


def test_doe_1c_1d_decomposition_and_attempt_plan_are_bounded():
    _request_value, authorization, result = _authorized_objective()
    contract = gsr.make_development_objective_acceptance_contract(result.objective, result.state)
    decomposition = gsr.decompose_development_objective(result.objective, result.state, contract, requested_subgoal_count=2, sequence=1220)
    assert decomposition.accepted is True
    assert len(decomposition.subgoals) == 2
    assert decomposition.execution_started is False

    too_many = gsr.decompose_development_objective(result.objective, result.state, contract, requested_subgoal_count=6, sequence=1220)
    assert too_many.accepted is False
    assert too_many.reason == "decomposition_count_limit_exceeded"
    recursive = gsr.decompose_development_objective(result.objective, result.state, contract, requested_subgoal_count=1, recursive=True, sequence=1220)
    assert recursive.reason == "recursive_decomposition_denied"

    queue = gsr.create_development_attempt_queue(result.state, decomposition, artifact_chain_starting_digest="CHAIN0", authorization_identity=authorization.objective_authorization_id)
    assert len(queue.attempts) <= result.state.maximum_attempts
    first = gsr.deserialize(gsr.DevelopmentAttemptPlan, queue.attempts[0])
    assert first.pcm_cycle_kind == "pcm_2_disposable_sandbox_coding_loop"
    assert first.source_scope == ("sample.py",)
    assert first.active is False


def test_doe_1e_1f_1g_ledger_arbitration_and_best_candidate_rules():
    _request_value, authorization, result = _authorized_objective()
    contract = gsr.make_development_objective_acceptance_contract(result.objective, result.state)
    decomposition = gsr.decompose_development_objective(result.objective, result.state, contract, requested_subgoal_count=1, sequence=1220)
    queue = gsr.create_development_attempt_queue(result.state, decomposition, artifact_chain_starting_digest="CHAIN0", authorization_identity=authorization.objective_authorization_id)
    attempt1 = gsr.deserialize(gsr.DevelopmentAttemptPlan, queue.attempts[0])
    ledger = gsr.DevelopmentProgressLedger(result.state.objective_id)
    ledger = gsr.append_development_progress(
        ledger,
        attempt1,
        pcm_artifact_chain_digest="CHAIN1",
        diagnosis_category="expected_symbol_missing",
        candidate_patch_id="candidate-a",
        sandbox_result="proposal_passed",
        metric_before={"fixture_symbol_coverage": 0.0, "protected_safety": 1.0},
        metric_after={"fixture_symbol_coverage": 0.4, "protected_safety": 1.0},
        protected_metric_changes={"protected_safety": 0.0},
        resource_usage={"pcm_attempts": 1},
        disposition="candidate_recorded",
    )
    assert len(ledger.entries) == 1
    arbitration = gsr.arbitrate_development_campaign(result.state, contract, ledger)
    assert arbitration.disposition == "continue_next_attempt"

    entry = gsr.deserialize(gsr.DevelopmentProgressEntry, ledger.entries[-1])
    retention = gsr.update_development_candidate_retention(gsr.DevelopmentCandidateRetentionState(result.state.objective_id), entry, contract)
    assert retention.best_candidate_id == "candidate-a"

    regressed = replace(entry, candidate_patch_id="candidate-b", metric_after={"fixture_symbol_coverage": 1.0, "protected_safety": 0.5}, protected_metric_changes={"protected_safety": -0.5})
    retention = gsr.update_development_candidate_retention(retention, regressed, contract)
    assert retention.best_candidate_id == "candidate-a"
    assert retention.current_candidate_id == "candidate-b"
    assert retention.rejected_candidate_summaries


def test_doe_1h_bounded_campaign_success_stagnation_budget_scope_and_integrity():
    request = _request(maximum_attempts=3)
    authorization = _authorization(request)
    success = gsr.run_bounded_development_objective_campaign(
        request,
        authorization,
        metric_after_attempts=(
            {"fixture_symbol_coverage": 0.4, "protected_safety": 1.0},
            {"fixture_symbol_coverage": 1.0, "protected_safety": 1.0},
        ),
        pcm_chain_digests=("CHAIN1", "CHAIN2"),
        candidate_patch_ids=("candidate-a", "candidate-b"),
        sequence=1230,
    )
    assert success.accepted is True
    assert success.arbitration.disposition == "complete_success"
    assert success.retention.best_candidate_id == "candidate-b"
    assert success.active_worktree_mutated is False
    assert success.persistence_performed is False
    assert success.scheduler_started is False
    assert success.provider_called is False
    assert success.model_invoked is False

    stagnation = gsr.run_bounded_development_objective_campaign(
        request,
        _authorization(request),
        metric_after_attempts=(
            {"fixture_symbol_coverage": 0.0, "protected_safety": 1.0},
            {"fixture_symbol_coverage": 0.0, "protected_safety": 1.0},
        ),
        pcm_chain_digests=("CHAIN1", "CHAIN2"),
        candidate_patch_ids=("candidate-a", "candidate-b"),
        sequence=1240,
    )
    assert stagnation.arbitration.disposition == "suspend_stagnation"

    budget_request = _request(maximum_attempts=1)
    budget = gsr.run_bounded_development_objective_campaign(
        budget_request,
        _authorization(budget_request),
        metric_after_attempts=({"fixture_symbol_coverage": 0.2, "protected_safety": 1.0},),
        pcm_chain_digests=("CHAIN1",),
        candidate_patch_ids=("candidate-a",),
        sequence=1250,
    )
    assert budget.arbitration.disposition == "complete_budget_exhausted"

    scope = gsr.run_bounded_development_objective_campaign(
        request,
        _authorization(request),
        metric_after_attempts=({"fixture_symbol_coverage": 0.2, "protected_safety": 1.0},),
        pcm_chain_digests=("CHAIN1",),
        candidate_patch_ids=("candidate-a",),
        sequence=1260,
        scope_violation_attempt=1,
    )
    assert scope.arbitration.disposition == "suspend_scope_violation"

    integrity = gsr.run_bounded_development_objective_campaign(
        request,
        _authorization(request),
        metric_after_attempts=({"fixture_symbol_coverage": 0.2, "protected_safety": 1.0},),
        pcm_chain_digests=("STALE",),
        candidate_patch_ids=("candidate-a",),
        sequence=1270,
        integrity_failure_attempt=1,
    )
    assert integrity.arbitration.disposition == "suspend_integrity_failure"


def test_doe_1_closure_accepts_bounded_campaign_and_rejects_substitution():
    request = _request(maximum_attempts=2)
    pilot = gsr.run_bounded_development_objective_campaign(
        request,
        _authorization(request),
        metric_after_attempts=(
            {"fixture_symbol_coverage": 0.5, "protected_safety": 1.0},
            {"fixture_symbol_coverage": 1.0, "protected_safety": 1.0},
        ),
        pcm_chain_digests=("CHAIN1", "CHAIN2"),
        candidate_patch_ids=("candidate-a", "candidate-b"),
        sequence=1280,
    )
    authorization = gsr.make_development_objective_engine_closure_authorization(pilot, issued_sequence=1281, expiration_sequence=1290)
    closure = gsr.evaluate_development_objective_engine_closure(pilot, authorization, sequence=1282)
    assert closure.accepted is True
    assert closure.reason == "accepted_for_doe_1_closure"
    assert closure.authorization_consumed is True
    assert closure.consumed_authorization.consumed is True
    assert closure.continuous_runtime_started is False
    assert closure.tracked_source_mutated is False
    assert closure.persistence_performed is False
    assert closure.scheduler_started is False
    assert closure.provider_called is False
    assert closure.model_invoked is False

    replay = gsr.evaluate_development_objective_engine_closure(pilot, closure.consumed_authorization, sequence=1283)
    assert replay.accepted is False
    assert replay.reason == "rejected_capability_escalation"

    substituted = replace(authorization, objective_id="other")
    bad = gsr.evaluate_development_objective_engine_closure(pilot, substituted, sequence=1282)
    assert bad.accepted is False
    assert bad.reason == "rejected_objective_substitution"
