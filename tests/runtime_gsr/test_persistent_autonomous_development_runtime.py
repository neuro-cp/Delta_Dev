from __future__ import annotations

import json

import pytest

from orchestration.runtime.persistent_autonomous_development_runtime import (
    DEFAULT_PROVIDER_POLICY,
    MAPPING_ARTIFACT_DIRECTORY,
    SOURCE_ARTIFACT_DIRECTORY,
    compile_persistent_generic_evaluator_authority,
    recover_historical_retrieval_with_persistence,
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
    assert rerun["goals"][0]["state"] == "blocked_evidence_environment"


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
