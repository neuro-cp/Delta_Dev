from __future__ import annotations

import json
from pathlib import Path
import threading

import pytest

from orchestration.runtime.persistent_autonomous_development_runtime import (
    DEFAULT_PROVIDER_POLICY,
    EVIDENCE_REVISION_OWNERSHIP_DIRECTORY,
    MAPPING_ARTIFACT_DIRECTORY,
    SOURCE_ARTIFACT_DIRECTORY,
    compile_persistent_generic_evaluator_authority,
    compile_persistent_evidence_revision_plan,
    execute_persistent_evidence_revision_consumer,
    preflight_persistent_evidence_revision_execution,
    recover_persistent_evidence_revision_execution,
    recover_historical_retrieval_with_persistence,
    run_persistent_evidence_revision_cycle,
    _target_is_satisfied,
    _exclusive_transition,
    _write_immutable_artifact,
    export_runtime_report,
    initialize_runtime,
    pause_runtime,
    resume_runtime,
    run_until_idle,
    schedule_runtime_wake,
    stop_runtime,
)


def _local_miss(_goal):
    return {"status": "public_evidence_required", "fingerprint": "local-miss", "evidence": {"reason": "no_local_evidence"}}


def _public_unresolved(goal, advisory):
    return {
        "status": "public_evidence_unresolved",
        "fingerprint": f"public-{goal['goal_id']}-{bool(advisory)}",
        "evidence": {"route": "fixture_public", "advisory_influenced": bool(advisory)},
    }


def _public_candidate(goal, _advisory):
    candidate = {
        "candidate_id": f"candidate-{goal['goal_id']}", "title": "Grammar fixture",
        "evidence_target": "Grammar",
        "canonical_locator": "https://example.edu/grammar", "source_class": "university_educational_material",
        "supports_labels": (goal["topic"].replace(" ", "_"),), "provenance": "fixture",
    }
    return {"status": "public_evidence_unresolved", "fingerprint": f"public-{goal['goal_id']}", "evidence": {"route": "fixture_public", "candidates": (candidate,)}}


def _retrieval(_candidate):
    return {
        "canonical_locator": "https://example.edu/grammar", "content_digest": "source-digest",
        "extraction_digest": "extract-digest",
        "content_text": "Grammar is a system of language rules. Grammar may vary by context and usage.",
    }


def _advisory(request):
    return {
        "status": "completed",
        "usage": {"total_tokens": 120},
        "raw_response": {
            "packet_type": "persistent_learning_advisory_v1",
            "advisory_only": True,
            "capability_claim": False,
            "goal_id": request["goal_id"],
            "frontier_id": request["frontier_id"],
            "unresolved_question": request["unresolved_question"],
            "explanation": "fixture advisory only",
            "prerequisite_topics": ["fixture prerequisite"],
            "search_queries": ["fixture public query"],
            "source_suggestions": [], "counterexamples": [], "uncertainty": "requires verification",
        },
    }


def _seed_goal_setting_failure(tmp_path, *, topic="Goal setting", target_behavior="explain and apply goal setting using retained excerpts", capability="explain_and_apply_goal_setting", generic_predicates=()):
    state = initialize_runtime(runtime_root=tmp_path, goals=(f"learn {topic}",))
    goal = dict(state["goals"][0])
    candidate = {
        "candidate_id": "persistent-development-candidate-9fa516d6a2d2e29e",
        "candidate_version": 1,
        "topic": topic,
        "parent_goal_topic": goal["topic"],
        "scoped_claim": f"source-grounded scoped claim about {topic}",
        "target_behavior": target_behavior,
        "direct_provenance": {
            "source_artifact_id": "persistent-development-source-artifact-257ccd8d514f07e8",
            "source_artifact_digest": "source-digest",
            "excerpt_mapping_id": "persistent-development-excerpt-mapping-bc8bf28e6877c5f3",
            "excerpt_mapping_digest": "mapping-digest",
        },
        "trusted_admission": False,
        "capability_promotion": False,
    }
    candidate["candidate_digest"] = "c9fa7f19c7994aad9636324992ce5c60290737812b00ee82a3eb4b673464f913"
    claim = _write_immutable_artifact(runtime_root=tmp_path, directory="learning_attempt_claims", artifact_id="persistent-learning-attempt-claim-6ae38b13992d2ef0", payload={
        "schema": "persistent_learning_attempt_claim_v1",
        "claim_id": "persistent-learning-attempt-claim-6ae38b13992d2ef0",
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "work_node_id": goal["work_nodes"][0]["node_id"],
        "sealed_package_digest": "sealed-digest",
        "learner_visible_bundle_digest": "old-bundle",
        "claim_state": "completed",
    })
    cases = tuple({**case, "failed_predicates": tuple(generic_predicates) or case["failed_predicates"]} for case in (
        {"case_id": "goalsetting-baseline-001", "kind": "baseline", "task_type": "explanation_and_application", "score": 0.0, "failure_reason": "insufficient_retained_teaching_evidence", "failed_predicates": ("purpose", "specific", "measurable", "achievable", "relevant", "time-bound", "example")},
        {"case_id": "goalsetting-control-001", "kind": "control", "task_type": "application_task", "score": 0.0, "failure_reason": "insufficient_retained_teaching_evidence", "failed_predicates": ("effective", "monthly", "within", "measurable")},
        {"case_id": "goalsetting-held_out-001", "kind": "held_out", "task_type": "explanation_task", "score": 0.0, "failure_reason": "insufficient_retained_teaching_evidence", "failed_predicates": ("motivation", "performance", "feedback", "outcome")},
        {"case_id": "goalsetting-adversarial-001", "kind": "adversarial", "task_type": "application_task", "score": 0.0, "failure_reason": "insufficient_retained_teaching_evidence", "failed_predicates": ("vague", "specific", "measurable", "revised", "successful")},
        {"case_id": "goalsetting-transfer-001", "kind": "transfer", "task_type": "application_task", "score": 0.0, "failure_reason": "insufficient_retained_teaching_evidence", "failed_predicates": ("specific", "measurable", "achievable", "relevant", "time-bound", "monitoring", "adjust", "progress")},
    ))
    evaluation = {
        "evaluation_id": "learning-content-evaluation-5b68bd42e4bdc52d",
        "attempt_id": "learning-attempt-02a6c554fa90156d",
        "disposition": "insufficient_retained_teaching_evidence",
        "promotion_eligible": False,
        "evaluation_digest": "81f50313055c18e6dc3188c810f24b5193fe661c23750e4852b3de43046a6086",
        "content_case_results": cases,
        "capability_dimension": capability,
    }
    eval_artifact = _write_immutable_artifact(runtime_root=tmp_path, directory="learning_evaluations", artifact_id=evaluation["evaluation_id"], payload={
        "schema": "persistent_learning_evaluation_v1",
        "claim_id": claim["claim_id"],
        "sealed_package_digest": "751091204dde7718297a320ce845c2dad8f38c27e81652cfb7af56112ad00af5",
        "learner_response_digest": "learner-digest",
        "evaluation": evaluation,
    })
    sealed_cases = tuple({
        "case_id": item["case_id"],
        "case_kind": item["kind"],
        "target_capability": capability,
        "assessment_dimension": capability,
        "learner_view": {"prompt": "fixture"},
        "evaluator_view": {"rubric": ("secret",), "scoring_rule": {"pass_condition": "secret"}},
    } for item in cases)
    result = _write_immutable_artifact(runtime_root=tmp_path, directory="evaluator_authority_requests/execution_results", artifact_id="persistent-isolated-evaluator-execution-result-8230a067c232cd2e", payload={
        "schema": "persistent_isolated_evaluator_execution_result_v1",
        "request_id": "isolated-evaluator-authoring-request-a0aaecef5425615c",
        "claim_state": "completed",
        "sealed_package": {
            "sealed_package_id": "provider-authored-sealed-evaluator-3d1e4cab56e2fa0b",
            "execution_contract_version": "sealed_evaluator_execution_v3",
            "target_capability": capability,
            "sealed_evaluation_cases": sealed_cases,
        },
    })
    view = _write_immutable_artifact(runtime_root=tmp_path, directory="sealed_case_execution_views", artifact_id="sealed-case-execution-view-81606e801addb731", payload={
        "schema": "sealed_case_execution_view_v1",
        "sealed_package_id": "provider-authored-sealed-evaluator-3d1e4cab56e2fa0b",
        "sealed_package_digest": result["artifact_digest"],
        "sealed_evaluation_cases": sealed_cases,
    })
    authority = _write_immutable_artifact(runtime_root=tmp_path, directory="evaluator_authority_requests", artifact_id="isolated-evaluator-authoring-request-a0aaecef5425615c", payload={
        "schema": "persistent_generic_isolated_evaluator_authoring",
        "request_id": "isolated-evaluator-authoring-request-a0aaecef5425615c",
        "status": "sealed_package_ready",
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "learner_visible_bundle": {"bundle_digest": "old-bundle", "study_resources": ()},
    })
    goal["candidate_versions"] = (candidate,)
    goal["learning_attempts"] = ({"claim_id": claim["claim_id"], "attempt_id": evaluation["attempt_id"], "status": "completed"},)
    goal["behavioral_evaluations"] = ({"evaluation_id": evaluation["evaluation_id"], "artifact_id": eval_artifact["artifact_id"], "disposition": evaluation["disposition"]},)
    goal["post_evaluation_disposition"] = {"tier": "candidate_revision_required", "evaluation_id": evaluation["evaluation_id"]}
    goal["pending_evaluator_authority"] = {
        "request_id": authority["request_id"],
        "status": "behavioral_evaluation_complete",
        "result_artifact_id": result["artifact_id"],
        "execution_view_digest": view["artifact_digest"],
        "learning_attempt_claim_id": claim["claim_id"],
        "learning_attempt_id": evaluation["attempt_id"],
        "evaluation_id": evaluation["evaluation_id"],
    }
    from orchestration.runtime.persistent_autonomous_development_runtime import _checkpoint
    _checkpoint(state={**state, "goals": (goal,), "lifecycle_state": "ready"}, runtime_root=tmp_path, reason="fixture_goal_setting_failure")
    return initialize_runtime(runtime_root=tmp_path)


def _revision_retrieval(candidate):
    target = candidate["revision_plan_id"] + candidate["evidence_target"]
    if "SMART" in candidate["evidence_target"]:
        text = "SMART goals are specific, measurable, achievable, relevant, and time-bound. For example, a goal can state what will be done, how success will be measured, and when it will be finished."
    elif "monitoring" in candidate["evidence_target"]:
        text = "Progress monitoring means tracking progress and using feedback about performance. Feedback helps show whether the goal is being reached."
    else:
        text = "A person should adjust or revise a goal based on observed progress and feedback. If progress shows the goal is unrealistic, the goal can be modified."
    return {
        "canonical_locator": candidate["canonical_locator"],
        "content_digest": f"source-{json.dumps(target, sort_keys=True)}",
        "extraction_digest": f"extract-{json.dumps(target, sort_keys=True)}",
        "content_text": text,
    }


def test_multiple_goals_rerank_after_one_honest_block_and_persist(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha", "learn beta"))
    calls = []
    def resolver(goal):
        calls.append(goal["topic"])
        return {"status": "blocked_evidence_environment", "fingerprint": f"fp-{goal['topic']}", "evidence": {"reason": "fixture_exhausted"}}
    result = run_until_idle(state=state, runtime_root=tmp_path, maximum_cycles=2, evidence_resolver=resolver)
    assert {call.rsplit(" ", 1)[0] for call in calls} == {"alpha", "beta"}
    assert result["lifecycle_state"] == "ready"
    assert [goal["state"] for goal in result["goals"]] == ["queued", "queued"]
    assert initialize_runtime(runtime_root=tmp_path)["state_digest"] == result["state_digest"]


def test_duplicate_evidence_fingerprint_is_suppressed_after_restart(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha",))
    result = run_until_idle(state=state, runtime_root=tmp_path, evidence_resolver=lambda _goal: {"status": "blocked_evidence_environment", "fingerprint": "same", "evidence": {"reason": "fixture"}})
    resumed = resume_runtime(state=result, runtime_root=tmp_path)
    rerun = run_until_idle(state=resumed, runtime_root=tmp_path, evidence_resolver=lambda _goal: (_ for _ in ()).throw(AssertionError("duplicate resolver call")))
    assert rerun["goals"][0]["state"] == "development_route_exhausted"
    assert rerun["goals"][0]["blocker"] == "all_unique_development_routes_exhausted"


def test_goal_cycle_budget_exhaustion_wins_over_replenishment(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha",))
    state = dict(state)
    goal = dict(state["goals"][0])
    goal["budget"] = {**dict(goal["budget"]), "cycles_used": 0, "maximum_cycles": 1}
    state["goals"] = (goal,)
    result = run_until_idle(
        state=state,
        runtime_root=tmp_path,
        maximum_cycles=3,
        evidence_resolver=lambda _goal: {"status": "blocked_evidence_environment", "fingerprint": "route-one", "evidence": {"reason": "fixture_exhausted"}},
    )
    goal = result["goals"][0]
    assert goal["budget"]["cycles_used"] == 1
    assert goal["state"] == "paused_budget"
    assert goal["blocker"] == "cycle_budget_exhausted_with_remaining_distinct_work"
    assert result["lifecycle_state"] == "waiting"


def test_duplicate_public_evidence_route_without_distinct_strategy_stops_cleanly(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha",))
    first = run_until_idle(
        state=state,
        runtime_root=tmp_path,
        maximum_cycles=1,
        evidence_resolver=_local_miss,
        public_evidence_resolver=lambda _goal, _advice: {"status": "public_evidence_unresolved", "fingerprint": "same-public", "evidence": {"candidates": ()}},
        provider_executor=_advisory,
    )
    rerun = run_until_idle(
        state=first,
        runtime_root=tmp_path,
        maximum_cycles=2,
        evidence_resolver=_local_miss,
        public_evidence_resolver=lambda _goal, _advice: {"status": "public_evidence_unresolved", "fingerprint": "same-public", "evidence": {"candidates": ()}},
        provider_executor=lambda _request: (_ for _ in ()).throw(AssertionError("provider replay")),
    )
    goal = rerun["goals"][0]
    assert goal["state"] == "blocked_evidence_environment"
    assert goal["blocker"] == "duplicate_public_evidence_route_without_distinct_retrieval_strategy"
    assert len(goal["work_history"]) == 3


def test_pause_resume_stop_and_report_are_durable(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha",))
    paused = pause_runtime(state=state, runtime_root=tmp_path)
    assert run_until_idle(state=paused, runtime_root=tmp_path)["lifecycle_state"] == "paused_runtime"
    resumed = resume_runtime(state=paused, runtime_root=tmp_path)
    stopped = stop_runtime(state=resumed, runtime_root=tmp_path)
    report = export_runtime_report(state=stopped, runtime_root=tmp_path)
    assert stopped["lifecycle_state"] == "stopped"
    assert report["terminal_reason"] == "operator_requested_clean_stop"


def test_retained_evidence_enters_verification_path_without_promoting_capability(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha",))
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1,
        evidence_resolver=lambda _goal: {"status": "retained_evidence_available", "fingerprint": "retained", "evidence": {"summary": "fixture"}},
        public_evidence_resolver=_public_unresolved,
        provider_executor=_advisory,
    )
    assert result["goals"][0]["state"] == "queued"
    candidate = result["goals"][0]["candidate_versions"][0]
    evaluation = result["goals"][0]["sealed_evaluations"][0]
    assert candidate["evidence_level"] == "developmental_candidate_provisional"
    assert candidate["unresolved_limits"]
    assert evaluation["result"]["status"] == "provisional_competence_supported"
    assert result["capability_promotions"] == result["trusted_admissions"] == 0


def test_broad_goal_starts_with_renewable_developmental_graph(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    nodes = state["goals"][0]["work_nodes"]
    assert len(nodes) >= 8
    assert {node["operation"] for node in nodes} >= {"definition", "example", "counterexample", "transfer"}


def test_exhausted_node_replenishes_with_bounded_material_revision(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha",))
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1,
        evidence_resolver=lambda _goal: {"status": "blocked_evidence_environment", "fingerprint": "first-route", "evidence": {"reason": "fixture_exhausted"}},
    )
    nodes = result["goals"][0]["work_nodes"]
    assert any(node.get("origin") == "branch_replenishment" and node.get("state") == "queued" for node in nodes)


def test_scheduled_wake_persists_a_finite_next_action(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha",))
    scheduled = schedule_runtime_wake(state=state, runtime_root=tmp_path, delay_seconds=30)
    assert scheduled["next_wake_at"]
    assert scheduled["next_action"]["transition"] == "run_one_bounded_developmental_cycle"
    assert initialize_runtime(runtime_root=tmp_path)["next_action"] == scheduled["next_action"]


def test_public_route_precedes_one_untrusted_provider_advisory_and_downstream_public_work(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    calls = []
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=4,
        evidence_resolver=_local_miss, public_evidence_resolver=_public_unresolved,
        provider_executor=lambda request: (calls.append(request["claim_id"]) or _advisory(request)),
    )
    goal = result["goals"][0]
    assert len(calls) == result["provider_calls"] == 1
    assert goal["provider_claims"][0]["claim_state"] == "completed"
    assert goal["provider_claims"][0]["raw_response"]["advisory_only"] is True
    assert goal["provider_claims"][0]["raw_response"]["capability_claim"] is False
    assert any(item.get("advisory_influenced") for item in goal["evidence"])
    assert result["trusted_admissions"] == result["capability_promotions"] == 0


def test_restart_never_replays_completed_provider_claim(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    first = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=2,
        evidence_resolver=_local_miss, public_evidence_resolver=_public_unresolved, provider_executor=_advisory,
    )
    restored = initialize_runtime(runtime_root=tmp_path)
    assert restored["provider_calls"] == first["provider_calls"] == 1
    rerun = run_until_idle(
        state=restored, runtime_root=tmp_path, maximum_cycles=2,
        evidence_resolver=_local_miss, public_evidence_resolver=_public_unresolved,
        provider_executor=lambda _request: (_ for _ in ()).throw(AssertionError("provider replay")),
    )
    assert rerun["provider_calls"] == 1


def test_goal_provider_budget_pauses_one_goal_and_other_goal_runs(tmp_path):
    policy = {**DEFAULT_PROVIDER_POLICY, "maximum_calls_per_goal": 0}
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha", "learn beta"), provider_policy=policy)
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=4,
        evidence_resolver=_local_miss, public_evidence_resolver=_public_unresolved, provider_executor=_advisory,
    )
    assert [goal["state"] for goal in result["goals"]] == ["paused_budget", "paused_budget"]
    assert result["provider_calls"] == 0


def test_elapsed_cooldown_resets_consecutive_provider_limit(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn alpha",))
    state = dict(state)
    goal = dict(state["goals"][0])
    goal["provider_claims"] = ({"claim_state": "completed", "completed_at": "2020-01-01T00:00:00+00:00"},)
    state["goals"] = (goal,)
    state["consecutive_provider_calls"] = 2
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1,
        evidence_resolver=_local_miss, public_evidence_resolver=_public_unresolved, provider_executor=_advisory,
    )
    assert result["goals"][0]["state"] == "queued"
    assert result["provider_calls"] == 1


def test_malformed_or_self_authorizing_provider_response_is_terminal_and_untrusted(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=2,
        evidence_resolver=_local_miss, public_evidence_resolver=_public_unresolved,
        provider_executor=lambda request: {**_advisory(request), "raw_response": {**_advisory(request)["raw_response"], "capability_claim": True}},
    )
    claim = result["goals"][0]["provider_claims"][0]
    assert claim["claim_state"] == "failed"
    assert claim["failure_reason"] == "provider_response_advisory_boundary_invalid"
    assert result["trusted_admissions"] == result["capability_promotions"] == 0


def test_source_body_candidate_has_exact_excerpts_and_sealed_evaluation_before_progress(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=2,
        evidence_resolver=_local_miss, public_evidence_resolver=_public_candidate,
        retrieval_executor=_retrieval,
        evaluator_executor=lambda candidate, specs: {"status": "passed", "candidate_digest": candidate["candidate_digest"], "criteria_digest": specs["criteria_digest"], "unseen_use": "passed", "transfer": "passed"},
    )
    goal = result["goals"][0]
    claim = goal["retrieval_claims"][0]
    assert claim["claim_state"] == "completed"
    source = json.loads((tmp_path / SOURCE_ARTIFACT_DIRECTORY / f"{claim['source_artifact_id']}.json").read_text(encoding="utf-8"))
    mapping = json.loads((tmp_path / MAPPING_ARTIFACT_DIRECTORY / f"{claim['excerpt_mapping_id']}.json").read_text(encoding="utf-8"))
    assert source["retained_text"] == _retrieval({})["content_text"]
    assert {item["facet"] for item in mapping["accepted_excerpts"]} == {"definition", "scope_limit"}
    assert claim["source_artifact_digest"] == source["artifact_digest"]
    assert goal["candidate_versions"][0]["direct_provenance"]["source_digest"] == "source-digest"
    assert goal["sealed_evaluations"][0]["specifications"]["criteria_digest"]
    assert result["competence_map"]["grammar"]["status"] == "developmentally_validated"
    assert result["trusted_admissions"] == result["capability_promotions"] == 0


def test_grounded_candidate_with_unavailable_evaluator_creates_operator_authority(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1,
        evidence_resolver=_local_miss, public_evidence_resolver=_public_candidate,
        retrieval_executor=_retrieval,
    )
    goal = result["goals"][0]
    pending = goal["pending_evaluator_authority"]
    assert goal["state"] == "blocked_operator_authority"
    assert goal["blocker"] == "pending_isolated_evaluator_authority"
    assert pending["status"] == "pending_operator_approval"
    assert pending["request_id"]
    assert len(goal["candidate_versions"]) == 1
    assert len(list((tmp_path / "evaluator_authority_requests").glob("*.json"))) == 1
    assert not (tmp_path / "evidence_revision_plans").exists()
    assert result["provider_calls"] == 0
    assert result["trusted_admissions"] == result["capability_promotions"] == 0


def test_mapping_insufficient_candidate_does_not_create_evaluator_authority_or_revision(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",), provider_policy={"maximum_runtime_calls": 0, "maximum_calls_per_goal": 0})
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1,
        evidence_resolver=_local_miss, public_evidence_resolver=_public_candidate,
        retrieval_executor=lambda selected: {
            "canonical_locator": selected["canonical_locator"],
            "content_digest": "definition-only",
            "extraction_digest": "definition-only-extract",
            "content_text": "Grammar is a language system.",
        },
    )
    goal = result["goals"][0]
    assert "pending_evaluator_authority" not in goal
    assert len(goal.get("candidate_versions") or ()) == 0
    assert not (tmp_path / "evaluator_authority_requests").exists()
    assert not (tmp_path / "evidence_revision_plans").exists()
    assert result["provider_calls"] == 0
    assert result["trusted_admissions"] == result["capability_promotions"] == 0


def test_source_facet_mapping_uses_selected_evidence_target_not_parent_goal_label(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn foundational grammar for conversational clarity",))
    candidate = {
        "candidate_id": "grammar", "title": "Grammar", "evidence_target": "Grammar",
        "canonical_locator": "https://example.edu/grammar", "source_class": "university_educational_material",
        "supports_labels": ("grammar",), "provenance": "fixture",
    }
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1, evidence_resolver=_local_miss,
        public_evidence_resolver=lambda goal, _advice: {"status": "public_evidence_unresolved", "fingerprint": "grammar-target", "evidence": {"candidates": (candidate,)}},
        retrieval_executor=lambda _selected: {"canonical_locator": "https://example.edu/grammar", "content_digest": "grammar-digest", "extraction_digest": "grammar-extract", "content_text": "Grammar is a language system. Grammar may vary by context."},
    )
    grounded = result["goals"][0]["candidate_versions"][0]
    assert grounded["topic"] == "Grammar"
    assert grounded["parent_goal_topic"] == "foundational grammar for conversational clarity"
    mapping = json.loads((tmp_path / MAPPING_ARTIFACT_DIRECTORY / f"{grounded['direct_provenance']['excerpt_mapping_id']}.json").read_text(encoding="utf-8"))
    assert {item["facet"] for item in mapping["accepted_excerpts"]} == {"definition", "scope_limit"}


def test_source_artifacts_are_immutable_and_restart_reuses_them_without_retrieval(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    first = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1, evidence_resolver=_local_miss,
        public_evidence_resolver=_public_candidate, retrieval_executor=_retrieval,
    )
    claim = first["goals"][0]["retrieval_claims"][0]
    source_path = tmp_path / SOURCE_ARTIFACT_DIRECTORY / f"{claim['source_artifact_id']}.json"
    original = source_path.read_text(encoding="utf-8")
    restored = initialize_runtime(runtime_root=tmp_path)
    rerun = run_until_idle(
        state=restored, runtime_root=tmp_path, maximum_cycles=1, evidence_resolver=_local_miss,
        public_evidence_resolver=_public_candidate,
        retrieval_executor=lambda _candidate: (_ for _ in ()).throw(AssertionError("retrieval replay")),
    )
    assert source_path.read_text(encoding="utf-8") == original
    assert rerun["goals"][0]["retrieval_claims"][0]["source_artifact_id"] == claim["source_artifact_id"]


def test_immutable_artifact_rejects_content_drift(tmp_path):
    _write_immutable_artifact(runtime_root=tmp_path, directory="artifacts", artifact_id="same", payload={"value": "first"})
    with pytest.raises(ValueError, match="artifact_digest_drift"):
        _write_immutable_artifact(runtime_root=tmp_path, directory="artifacts", artifact_id="same", payload={"value": "second"})


def test_historical_digest_only_claims_are_nonreviewable_after_restart(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    state = dict(state); goal = dict(state["goals"][0])
    goal["retrieval_claims"] = ({"claim_id": "historical", "claim_state": "completed", "source_digest": "only-digest"},)
    state["goals"] = (goal,)
    from orchestration.runtime.persistent_autonomous_development_runtime import _checkpoint
    _checkpoint(state=state, runtime_root=tmp_path, reason="fixture_historical_digest_only")
    restored = initialize_runtime(runtime_root=tmp_path)
    claim = restored["goals"][0]["retrieval_claims"][0]
    assert claim["historical_disposition"] == "historical_retrieval_completed_content_not_persisted_nonreviewable"
    assert claim["reviewable_for_grounding"] is False


def test_grounded_candidate_compiles_pending_generic_evaluator_authority(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1, evidence_resolver=_local_miss,
        public_evidence_resolver=_public_candidate, retrieval_executor=_retrieval,
    )
    goal = result["goals"][0]
    authority = compile_persistent_generic_evaluator_authority(
        runtime_root=tmp_path, runtime_id=result["runtime_id"], goal=goal, candidate=goal["candidate_versions"][0],
    )
    assert authority["status"] == "pending_operator_approval"
    assert authority["recommended_approval_token"] == "approve_persistent_generic_evaluator_authoring"
    assert authority["source_artifact_digest"] == goal["retrieval_claims"][0]["source_artifact_digest"]
    assert "no_capability_promotion" in authority["authority_limits"]


def test_explicit_persistence_recovery_preserves_digest_only_history_and_creates_new_authority(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn goal setting",))
    state = dict(state); goal = dict(state["goals"][0])
    historical = {
        "claim_id": "historical-goal-setting", "claim_state": "completed",
        "canonical_locator": "https://en.wikipedia.org/wiki/Goal_setting", "source_digest": "old-digest",
        "historical_disposition": "historical_retrieval_completed_content_not_persisted_nonreviewable",
    }
    goal["retrieval_claims"] = (historical,); state["goals"] = (goal,)
    from orchestration.runtime.persistent_autonomous_development_runtime import _checkpoint
    _checkpoint(state=state, runtime_root=tmp_path, reason="fixture_historical_recovery")
    final, result = recover_historical_retrieval_with_persistence(
        state=initialize_runtime(runtime_root=tmp_path), runtime_root=tmp_path,
        historical_claim_id="historical-goal-setting", evidence_target="Goal setting",
        retrieval_executor=lambda candidate: {
            "canonical_locator": candidate["canonical_locator"], "content_digest": "fresh-source", "extraction_digest": "fresh-extract",
            "content_text": "Goal setting is an action plan. Goal setting may guide a person toward a goal.",
        },
    )
    claims = final["goals"][0]["retrieval_claims"]
    assert claims[0]["historical_disposition"] == "historical_retrieval_completed_content_not_persisted_nonreviewable"
    assert claims[1]["parent_historical_claim_id"] == "historical-goal-setting"
    assert claims[1]["source_artifact_id"]
    assert result["candidate"]["candidate_id"]
    assert result["authority"]["status"] == "pending_operator_approval"


def test_budget_failed_full_page_can_compile_one_distinct_same_page_summary_claim(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    state = dict(state)
    goal = dict(state["goals"][0])
    original_claim = {
        "claim_id": "old-full-page", "canonical_locator": "https://en.wikipedia.org/wiki/Grammar",
        "claim_state": "failed", "failure_reason": "ValueError:rc8_retrieval_failed:content_budget_exhausted",
        "extraction_strategy": "full_page_rc8",
    }
    goal["retrieval_claims"] = (original_claim,)
    state["goals"] = (goal,)
    candidate = {
        "candidate_id": "grammar-page", "title": "Grammar", "canonical_locator": "https://en.wikipedia.org/wiki/Grammar",
        "source_class": "recognized_reference", "supports_labels": ("grammar",), "provenance": "fixture",
        "bounded_extract_permitted": True,
    }
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1, evidence_resolver=_local_miss,
        public_evidence_resolver=lambda goal, _advice: {"status": "public_evidence_unresolved", "fingerprint": "grammar-retry", "evidence": {"candidates": (candidate,)}},
        retrieval_executor=lambda selected: {
            "canonical_locator": selected["canonical_locator"], "content_digest": "summary-digest", "extraction_digest": "summary-extract",
            "content_text": "Grammar is a language system. Grammar may vary by context.",
        },
    )
    claim = result["goals"][0]["retrieval_claims"][-1]
    assert claim["claim_state"] == "completed"
    assert claim["extraction_strategy"] == "wikipedia_bounded_summary"
    assert claim["parent_terminal_claim_id"] == "old-full-page"
    assert len(result["goals"][0]["retrieval_claims"]) == 2


def test_exhausted_metadata_fingerprint_still_allows_distinct_strategy_reeligibility(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    state = dict(state); goal = dict(state["goals"][0])
    goal["retrieval_claims"] = ({"claim_id": "old-full-page", "canonical_locator": "https://en.wikipedia.org/wiki/Grammar", "claim_state": "failed", "failure_reason": "content_budget_exhausted", "extraction_strategy": "full_page_rc8"},)
    state["goals"] = (goal,); state["exhausted_fingerprints"] = ("same-metadata",)
    candidate = {"candidate_id": "grammar-page", "canonical_locator": "https://en.wikipedia.org/wiki/Grammar", "bounded_extract_permitted": True}
    result = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=1, evidence_resolver=_local_miss,
        public_evidence_resolver=lambda goal, _advice: {"status": "public_evidence_unresolved", "fingerprint": "same-metadata", "evidence": {"candidates": (candidate,)}},
        retrieval_executor=lambda selected: {"canonical_locator": selected["canonical_locator"], "content_digest": "summary", "extraction_digest": "summary-extract", "content_text": "Grammar is a system. Grammar may vary by context."},
    )
    assert result["goals"][0]["retrieval_claims"][-1]["extraction_strategy"] == "wikipedia_bounded_summary"


def test_terminal_source_invalid_state_still_suppresses_all_strategies(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    state = dict(state); goal = dict(state["goals"][0])
    goal["retrieval_claims"] = ({"claim_id": "invalid", "canonical_locator": "https://en.wikipedia.org/wiki/Grammar", "claim_state": "failed", "failure_reason": "source_identity_mismatch"},)
    state["goals"] = (goal,)
    candidate = {"candidate_id": "grammar-page", "canonical_locator": "https://en.wikipedia.org/wiki/Grammar", "bounded_extract_permitted": True}
    result = run_until_idle(state=state, runtime_root=tmp_path, maximum_cycles=1, evidence_resolver=_local_miss, public_evidence_resolver=lambda goal, _advice: {"status": "public_evidence_unresolved", "fingerprint": "invalid-source", "evidence": {"candidates": (candidate,)}})
    assert len(result["goals"][0]["retrieval_claims"]) == 1


def test_restart_preserves_completed_retrieval_and_evaluation_without_duplication(tmp_path):
    state = initialize_runtime(runtime_root=tmp_path, goals=("learn grammar",))
    first = run_until_idle(
        state=state, runtime_root=tmp_path, maximum_cycles=2, evidence_resolver=_local_miss,
        public_evidence_resolver=_public_candidate, retrieval_executor=_retrieval,
        evaluator_executor=lambda _candidate, _specs: {"status": "passed"},
    )
    restored = initialize_runtime(runtime_root=tmp_path)
    assert restored["goals"][0]["retrieval_claims"][0]["claim_state"] == "completed"
    assert len(restored["goals"][0]["sealed_evaluations"]) == len(first["goals"][0]["sealed_evaluations"]) == 1


def test_evidence_revision_plan_derives_from_failed_dimensions_and_is_idempotent(tmp_path):
    _seed_goal_setting_failure(tmp_path)
    first = compile_persistent_evidence_revision_plan(runtime_root=tmp_path, failed_evaluation_id="learning-content-evaluation-5b68bd42e4bdc52d")
    second = compile_persistent_evidence_revision_plan(runtime_root=tmp_path, failed_evaluation_id="learning-content-evaluation-5b68bd42e4bdc52d")
    assert first["revision_plan_id"] == second["revision_plan_id"]
    assert first["plan_digest"] == second["plan_digest"]
    assert tuple(first["failed_case_ids"]) == (
        "goalsetting-baseline-001",
        "goalsetting-control-001",
        "goalsetting-held_out-001",
        "goalsetting-adversarial-001",
        "goalsetting-transfer-001",
    )
    assert [target["target_id"] for target in first["missing_evidence_targets"]][:3] == [
        "smart_components",
        "progress_monitoring_feedback",
        "progress_based_adjustment",
    ]
    assert first["maximum_retrieval_count"] == 3
    assert first["provider_budget"] == 0


def test_evidence_revision_cycle_creates_revised_candidate_bundle_and_pending_authority(tmp_path):
    seeded = _seed_goal_setting_failure(tmp_path)
    parent = seeded["goals"][0]["candidate_versions"][0]
    result = run_persistent_evidence_revision_cycle(
        runtime_root=tmp_path,
        failed_evaluation_id="learning-content-evaluation-5b68bd42e4bdc52d",
        retrieval_executor=_revision_retrieval,
    )
    assert result["status"] == "reevaluation_pending"
    assert len(result["retrieval_claims"]) == 3
    assert {claim["evidence_revision_target_id"] for claim in result["retrieval_claims"]} == {
        "smart_components",
        "progress_monitoring_feedback",
        "progress_based_adjustment",
    }
    assert result["sufficiency_decision"]["evidence_sufficient"] is True
    revised = result["revised_candidate"]
    assert revised["candidate_id"] != parent["candidate_id"]
    assert revised["candidate_digest"] != parent["candidate_digest"]
    assert revised["parent_candidate_digest"] == parent["candidate_digest"]
    bundle = result["learner_visible_bundle"]
    bundle_text = json.dumps(bundle)
    assert "specific, measurable, achievable, relevant, and time-bound" in bundle_text
    assert "tracking progress and using feedback" in bundle_text
    assert "adjust or revise a goal based on observed progress" in bundle_text
    assert "answer_key" not in bundle_text
    assert "scoring_rule" not in bundle_text
    assert result["evaluator_reuse_decision"]["reuse_valid"] is True
    authority = result["pending_authority"]
    assert authority["recommended_approval_token"].startswith("approve_persistent_evidence_revision_retry_")
    assert authority["maximum_learner_attempts"] == 1
    assert "evaluator_authoring_provider_call" in authority["prohibited_actions"]
    final = initialize_runtime(runtime_root=tmp_path)
    assert len(final["goals"][0]["learning_attempts"]) == 1
    assert final["trusted_admissions"] == final["capability_promotions"] == 0


def test_evidence_revision_preflight_binds_revised_candidate_without_execution_and_is_exact_once(tmp_path):
    _seed_goal_setting_failure(tmp_path, topic="Evidence-based study planning", target_behavior="explain and apply study planning using retained excerpts")
    result = run_persistent_evidence_revision_cycle(
        runtime_root=tmp_path,
        failed_evaluation_id="learning-content-evaluation-5b68bd42e4bdc52d",
        retrieval_executor=_revision_retrieval,
    )
    assert result["status"] == "reevaluation_pending"
    assert "Goal_setting" not in " ".join(claim["canonical_locator"] for claim in result["retrieval_claims"])
    authority = result["pending_authority"]
    preflight = preflight_persistent_evidence_revision_execution(
        runtime_root=tmp_path,
        authority_id=authority["request_id"],
        approval_token=authority["recommended_approval_token"],
    )
    assert preflight["status"] == "preflight_accepted_no_execution"
    assert preflight["binding"]["candidate_digest"] == result["revised_candidate"]["candidate_digest"]
    assert preflight["binding"]["sealed_package_digest"] == authority["sealed_package_digest"]
    executed = execute_persistent_evidence_revision_consumer(
        runtime_root=tmp_path,
        authority_id=authority["request_id"],
    )
    assert executed["status"] == "execution_completed"
    assert executed["execution_claim"]["claim_state"] == "dispatching"
    assert executed["execution_result"]["execution_claim_id"] == executed["execution_claim"]["artifact_id"]
    replay = preflight_persistent_evidence_revision_execution(
        runtime_root=tmp_path,
        authority_id=authority["request_id"],
        approval_token=authority["recommended_approval_token"],
    )
    assert replay["status"] == "preflight_replay_suppressed"
    execution_replay = execute_persistent_evidence_revision_consumer(runtime_root=tmp_path, authority_id=authority["request_id"])
    assert execution_replay["status"] == "execution_replay_suppressed"
    final = initialize_runtime(runtime_root=tmp_path)
    assert len(final["goals"][0]["learning_attempts"]) == 2
    assert len(final["goals"][0]["behavioral_evaluations"]) == 2
    assert final["provider_calls"] == final["trusted_admissions"] == final["capability_promotions"] == 0


def test_monitoring_sufficiency_requires_explicit_relation():
    assert not _target_is_satisfied("progress_monitoring_feedback", ({"text": "Progress was mentioned."},))
    assert _target_is_satisfied("progress_monitoring_feedback", ({"text": "Progress toward the target should be measured regularly."},))
    assert _target_is_satisfied("progress_monitoring_feedback", ({"text": "Feedback is used to compare current performance with the intended goal."},))


def test_evidence_revision_executes_a_genuine_generic_article_agreement_episode_once(tmp_path):
    _seed_goal_setting_failure(
        tmp_path,
        topic="Basic grammar article agreement",
        target_behavior="choose articles from retained grammar evidence",
        capability="apply_article_agreement",
        generic_predicates=("article", "vowel"),
    )

    def grammar_retrieval(candidate):
        return {
            "canonical_locator": candidate["canonical_locator"],
            "content_digest": "grammar-article-source",
            "extraction_digest": "grammar-article-extract",
            "content_text": "Article choice is determined by the initial vowel sound of the following word.",
        }

    revised = run_persistent_evidence_revision_cycle(
        runtime_root=tmp_path,
        failed_evaluation_id="learning-content-evaluation-5b68bd42e4bdc52d",
        retrieval_executor=grammar_retrieval,
    )
    assert revised["status"] == "reevaluation_pending"
    assert [target["target_id"] for target in revised["revision_plan"]["missing_evidence_targets"]][0].startswith("generic_failed_dimension_")
    assert "smart" not in json.dumps(revised["revision_plan"]).lower()
    authority = revised["pending_authority"]
    preflight_persistent_evidence_revision_execution(runtime_root=tmp_path, authority_id=authority["request_id"], approval_token=authority["recommended_approval_token"])
    executed = execute_persistent_evidence_revision_consumer(runtime_root=tmp_path, authority_id=authority["request_id"])
    assert executed["status"] == "execution_completed"
    assert execute_persistent_evidence_revision_consumer(runtime_root=tmp_path, authority_id=authority["request_id"])["status"] == "execution_replay_suppressed"


def _prepare_revision_execution(tmp_path):
    _seed_goal_setting_failure(tmp_path, topic="Evidence-based study planning", target_behavior="explain and apply study planning using retained excerpts")
    revised = run_persistent_evidence_revision_cycle(
        runtime_root=tmp_path,
        failed_evaluation_id="learning-content-evaluation-5b68bd42e4bdc52d",
        retrieval_executor=_revision_retrieval,
    )
    authority = revised["pending_authority"]
    preflight_persistent_evidence_revision_execution(
        runtime_root=tmp_path,
        authority_id=authority["request_id"],
        approval_token=authority["recommended_approval_token"],
    )
    return authority


def test_evidence_revision_execution_concurrent_callers_acquire_one_owner(tmp_path, monkeypatch):
    authority = _prepare_revision_execution(tmp_path)
    import orchestration.runtime.developmental_learning as developmental_learning

    original_execute = developmental_learning.execute_learning_attempt
    original_evaluate = developmental_learning.evaluate_learning_attempt
    counts = {"learner": 0, "evaluator": 0}
    lock = threading.Lock()

    def counted_execute(*args, **kwargs):
        with lock:
            counts["learner"] += 1
        return original_execute(*args, **kwargs)

    def counted_evaluate(*args, **kwargs):
        with lock:
            counts["evaluator"] += 1
        return original_evaluate(*args, **kwargs)

    monkeypatch.setattr(developmental_learning, "execute_learning_attempt", counted_execute)
    monkeypatch.setattr(developmental_learning, "evaluate_learning_attempt", counted_evaluate)
    barrier = threading.Barrier(2)
    results: list[dict[str, object]] = []
    errors: list[BaseException] = []

    def worker():
        try:
            barrier.wait(timeout=5)
            results.append(execute_persistent_evidence_revision_consumer(runtime_root=tmp_path, authority_id=authority["request_id"]))
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert errors == []
    assert sorted(result["status"] for result in results) == ["execution_completed", "execution_owned_elsewhere"]
    assert counts == {"learner": 1, "evaluator": 1}
    assert execute_persistent_evidence_revision_consumer(runtime_root=tmp_path, authority_id=authority["request_id"])["status"] == "execution_replay_suppressed"


def test_exclusive_transition_ignores_abandoned_tempdir_and_publishes_complete_metadata(tmp_path):
    execution_id = "execution-under-publication"
    sequence = "000-acquired"
    root = tmp_path / EVIDENCE_REVISION_OWNERSHIP_DIRECTORY / execution_id
    (root / f".{sequence}.abandoned.tmpdir").mkdir(parents=True)
    status, ownership = _exclusive_transition(
        runtime_root=tmp_path,
        execution_id=execution_id,
        sequence=sequence,
        payload={"schema": "persistent_evidence_revision_execution_ownership_v1", "state": "acquired_not_started"},
    )
    assert status == "acquired"
    assert ownership["state"] == "acquired_not_started"
    assert (root / f"{sequence}.transition" / "metadata.json").exists()


def test_exclusive_transition_paused_publisher_cannot_be_overwritten_by_competitor(tmp_path, monkeypatch):
    execution_id = "execution-active-publisher"
    sequence = "050-terminal"
    original_rename = Path.rename
    paused = threading.Event()
    release = threading.Event()
    delayed = {"used": False}

    def delayed_rename(self, target):
        if not delayed["used"] and str(self).endswith(".td") and Path(target).name == f"{sequence}.transition":
            delayed["used"] = True
            paused.set()
            release.wait(timeout=5)
        return original_rename(self, target)

    monkeypatch.setattr(Path, "rename", delayed_rename)
    first: list[tuple[str, dict[str, object]]] = []

    def publisher():
        first.append(_exclusive_transition(
            runtime_root=tmp_path,
            execution_id=execution_id,
            sequence=sequence,
            payload={"schema": "persistent_evidence_revision_execution_ownership_v1", "execution_claim_id": execution_id, "state": "terminal-original"},
        ))

    thread = threading.Thread(target=publisher)
    thread.start()
    assert paused.wait(timeout=5)
    second = _exclusive_transition(
        runtime_root=tmp_path,
        execution_id=execution_id,
        sequence=sequence,
        payload={"schema": "persistent_evidence_revision_execution_ownership_v1", "execution_claim_id": execution_id, "state": "terminal-competitor"},
        repair_orphaned_lock=True,
    )
    root = tmp_path / EVIDENCE_REVISION_OWNERSHIP_DIRECTORY / execution_id
    published_before_release = json.loads((root / f"{sequence}.transition" / "metadata.json").read_text(encoding="utf-8"))
    release.set()
    thread.join(timeout=5)
    published_after_release = json.loads((root / f"{sequence}.transition" / "metadata.json").read_text(encoding="utf-8"))
    assert second[0] == "acquired"
    assert first[0][0] == "already_exists"
    assert published_before_release == published_after_release
    assert published_after_release["state"] == "terminal-competitor"


class _InjectedCrash(RuntimeError):
    pass


@pytest.mark.parametrize(
    ("boundary", "expected_status", "expected_counts"),
    (
        ("after_ownership_acquired", "recovery_resumed_before_learner", {"learner": 1, "evaluator": 1}),
        ("after_execution_claim_persisted", "recovery_resumed_before_learner", {"learner": 1, "evaluator": 1}),
        ("after_learner_dispatching", "execution_outcome_unknown_integrity_stop", {"learner": 0, "evaluator": 0}),
        ("after_attempt_persisted", "recovery_resumed_evaluation_from_persisted_attempt", {"learner": 1, "evaluator": 1}),
        ("after_evaluator_dispatching", "evaluation_outcome_unknown_integrity_stop", {"learner": 1, "evaluator": 0}),
        ("after_evaluation_persisted", "recovery_finalized_from_persisted_evaluation", {"learner": 1, "evaluator": 1}),
        ("after_terminal_result_persisted", "terminal_result_reconciled", {"learner": 1, "evaluator": 1}),
    ),
)
def test_evidence_revision_execution_recovery_classifies_crash_windows(tmp_path, monkeypatch, boundary, expected_status, expected_counts):
    authority = _prepare_revision_execution(tmp_path)
    import orchestration.runtime.developmental_learning as developmental_learning

    original_execute = developmental_learning.execute_learning_attempt
    original_evaluate = developmental_learning.evaluate_learning_attempt
    counts = {"learner": 0, "evaluator": 0}

    def counted_execute(*args, **kwargs):
        counts["learner"] += 1
        return original_execute(*args, **kwargs)

    def counted_evaluate(*args, **kwargs):
        counts["evaluator"] += 1
        return original_evaluate(*args, **kwargs)

    monkeypatch.setattr(developmental_learning, "execute_learning_attempt", counted_execute)
    monkeypatch.setattr(developmental_learning, "evaluate_learning_attempt", counted_evaluate)

    def crash_hook(name):
        if name == boundary:
            raise _InjectedCrash(name)

    with pytest.raises(_InjectedCrash):
        execute_persistent_evidence_revision_consumer(runtime_root=tmp_path, authority_id=authority["request_id"], boundary_hook=crash_hook)
    before_recovery_counts = dict(counts)
    recovered = recover_persistent_evidence_revision_execution(runtime_root=tmp_path, authority_id=authority["request_id"])
    assert recovered["status"] == expected_status
    assert counts == expected_counts
    if boundary == "after_evaluation_persisted":
        assert counts == before_recovery_counts
        assert recovered["execution_result"]["evaluation_artifact_id"]
    if boundary == "after_terminal_result_persisted":
        assert counts == before_recovery_counts
        final = initialize_runtime(runtime_root=tmp_path)
        pending = final["goals"][0]["pending_evidence_revision_authority"]
        assert pending["status"] == "consumed_completed"
        assert pending["execution_result_id"] == recovered["execution_result"]["artifact_id"]
        assert len(final["goals"][0]["learning_attempts"]) == 2
        assert len(final["goals"][0]["behavioral_evaluations"]) == 2
    if expected_status.endswith("integrity_stop") or expected_status.endswith("manual_recovery_required"):
        assert execute_persistent_evidence_revision_consumer(runtime_root=tmp_path, authority_id=authority["request_id"])["status"] == "execution_recovery_classified_replay_suppressed"


def test_terminal_reconciliation_repairs_orphaned_terminal_lock_without_rerun(tmp_path, monkeypatch):
    authority = _prepare_revision_execution(tmp_path)
    import orchestration.runtime.developmental_learning as developmental_learning

    original_execute = developmental_learning.execute_learning_attempt
    original_evaluate = developmental_learning.evaluate_learning_attempt
    counts = {"learner": 0, "evaluator": 0}

    def counted_execute(*args, **kwargs):
        counts["learner"] += 1
        return original_execute(*args, **kwargs)

    def counted_evaluate(*args, **kwargs):
        counts["evaluator"] += 1
        return original_evaluate(*args, **kwargs)

    monkeypatch.setattr(developmental_learning, "execute_learning_attempt", counted_execute)
    monkeypatch.setattr(developmental_learning, "evaluate_learning_attempt", counted_evaluate)

    def crash_hook(name):
        if name == "after_terminal_result_persisted":
            raise _InjectedCrash(name)

    with pytest.raises(_InjectedCrash):
        execute_persistent_evidence_revision_consumer(runtime_root=tmp_path, authority_id=authority["request_id"], boundary_hook=crash_hook)
    before_recovery_counts = dict(counts)
    result = next((tmp_path / "evidence_revision_execution_results").glob("*.json"))
    execution_id = Path(result).stem
    root = tmp_path / EVIDENCE_REVISION_OWNERSHIP_DIRECTORY / execution_id

    recovered = recover_persistent_evidence_revision_execution(runtime_root=tmp_path, authority_id=authority["request_id"])
    assert recovered["status"] == "terminal_result_reconciled"
    assert counts == before_recovery_counts
    assert (root / "050-terminal.transition" / "metadata.json").exists()


def test_evidence_revision_replay_reuses_pending_authority_without_new_retrieval(tmp_path):
    _seed_goal_setting_failure(tmp_path)
    first = run_persistent_evidence_revision_cycle(
        runtime_root=tmp_path,
        failed_evaluation_id="learning-content-evaluation-5b68bd42e4bdc52d",
        retrieval_executor=_revision_retrieval,
    )
    second = run_persistent_evidence_revision_cycle(
        runtime_root=tmp_path,
        failed_evaluation_id="learning-content-evaluation-5b68bd42e4bdc52d",
        retrieval_executor=lambda _candidate: (_ for _ in ()).throw(AssertionError("revision retrieval replay")),
    )
    assert second["status"] == "reevaluation_pending"
    assert second["revision_plan"]["revision_plan_id"] == first["revision_plan"]["revision_plan_id"]
    assert second["revision_plan"]["pending_authority_id"] == first["pending_authority"]["request_id"]


def test_evidence_revision_keyword_only_or_missing_adjustment_stops_insufficient(tmp_path):
    _seed_goal_setting_failure(tmp_path)

    def weak_retrieval(candidate):
        if "SMART" in candidate["evidence_target"]:
            text = "SMART goals are popular in planning."
        elif "monitoring" in candidate["evidence_target"]:
            text = "Tracking is sometimes mentioned."
        else:
            text = "Adjustment is a word in goal-setting discussions."
        return {
            "canonical_locator": candidate["canonical_locator"],
            "content_digest": f"weak-{candidate['evidence_target']}",
            "extraction_digest": f"weak-extract-{candidate['evidence_target']}",
            "content_text": text,
        }

    result = run_persistent_evidence_revision_cycle(
        runtime_root=tmp_path,
        failed_evaluation_id="learning-content-evaluation-5b68bd42e4bdc52d",
        retrieval_executor=weak_retrieval,
    )
    assert result["status"] == "evidence_insufficient"
    assert result["sufficiency_decision"]["unresolved_targets"]
    final = initialize_runtime(runtime_root=tmp_path)
    assert len(final["goals"][0]["candidate_versions"]) == 1
    assert not final["goals"][0].get("pending_evidence_revision_authority")
