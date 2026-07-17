from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    claim_developmental_external_research_execution,
    claim_developmental_external_research_retrieval,
    compile_failed_research_adapter_repair_authority,
    compile_failed_research_fallback_authority,
    compile_relevance_failed_direct_topic_authority,
    record_external_transport_diagnostic_interpretation,
    consume_developmental_resource_authority_response,
    execute_claimed_developmental_external_research,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.developmental_interest import compile_persistent_developmental_agenda
from orchestration.runtime.developmental_resource_policy import compile_developmental_resource_authority_requirement
from orchestration.runtime.governed_external_research import (
    ExternalResearchRetrievalError,
    compile_execution_claim,
    compile_external_research_plan,
    compile_historical_transport_interpretation,
    compile_direct_topic_source_candidates,
    execute_rc8_mock_research_adapter,
    normalize_external_research_source,
    research_state_is_valid,
    synthesize_external_research_result,
)


INSTRUCTION = "Continue your governed developmental agenda. Propose one goal at a time and wait for approval before each mission."


def _requirement() -> dict[str, object]:
    agenda = compile_persistent_developmental_agenda(operator_scope=INSTRUCTION, material_digest="external-research").as_dict()
    proposal = {"proposal_id": "proposal-external", "selected_interest_id": "interest-external", "domain": "mathematics", "topic": "spectral_theorem", "target_capability": "complex_inner_product_space_scope", "measurable_outcome": "identify the complex inner-product-space scope of the spectral theorem", "source_evidence": ("retained-gap",)}
    candidate = {"interest_id": "interest-external", "domain": "mathematics", "topic": "spectral_theorem", "target_capability": "complex_inner_product_space_scope", "target_behavior": "identify the complex inner-product-space scope of the spectral theorem", "resource_state": "unavailable", "authority_state": "operator_approval_required", "evaluator_state": "evaluation_plan_ready"}
    return compile_developmental_resource_authority_requirement(agenda=agenda, proposal=proposal, candidate=candidate, mission={"mission_id": "mission-external", "domain": "mathematics", "topic": "spectral_theorem"}, learning_state={"evaluation_strategy": {"selected_plan": {"plan_id": "sealed-evaluator", "status": "evaluation_plan_ready", "selected_strategy": "deterministic_predicate"}}}).as_dict()


def _decision(requirement: dict[str, object]) -> dict[str, object]:
    return {"decision_id": "decision-external", "requirement_id": requirement["requirement_id"], "action_type": "request_external_research_authority", "selected_policy_candidate_id": "candidate-external", "target_authority_request_id": "authority-external", "status": "decision_compiled"}


def _source(url: str, claim: str, *, source_class: str = "peer_reviewed_or_academic", content: str | None = None) -> dict[str, object]:
    return {"url": url, "title": "Spectral theorem reference", "author_or_organization": "Example University", "publisher": "Example University", "source_class": source_class, "content": content or f"The spectral theorem {claim}. This spectral theorem material identifies complex inner product scope.", "claims": (claim,), "topic_scope": "spectral_theorem"}


def _external_pending() -> object:
    requirement = _requirement()
    decision = _decision(requirement)
    request = {"request_id": "authority-external", "request_kind": "developmental_resource_authority", "policy_decision_id": "decision-external", "requirement_id": requirement["requirement_id"], "action_type": "request_external_research_authority", "status": "pending", "authority_scope": "bounded external research only", "permitted_responses": ("approve_scoped_authority", "reject_scoped_authority", "defer_resource_policy", "ask_for_clarification")}
    policy = {"requirement": requirement, "decision": decision, "policy_candidates": ({"policy_candidate_id": "candidate-external"},), "status": "authority_pending", "policy_state_digest": "policy-digest"}
    state = {"developmental_agenda": compile_persistent_developmental_agenda(operator_scope=INSTRUCTION, material_digest="external-research").as_dict(), "developmental_interest": {"proposal": {"proposal_id": "proposal-external", "selected_interest_id": "interest-external"}, "candidate_interests": ({"interest_id": "interest-external", "domain": "mathematics", "topic": "spectral_theorem"},)}, "developmental_resource_policy": policy}
    return replace(start_continuous_runtime_controller(session_id="external-research"), continuous_learning_state=state, continuous_developmental_insight_requests=(request,))


def test_plan_identity_is_deterministic_and_requires_approval_binding():
    requirement, decision = _requirement(), _decision(_requirement())
    first = compile_external_research_plan(requirement=requirement, decision=decision, authority_request_id="authority-external", operator_approval_id="authority-external")
    second = compile_external_research_plan(requirement=requirement, decision=decision, authority_request_id="authority-external", operator_approval_id="authority-external")
    assert first.research_plan_id == second.research_plan_id
    assert first.query_budget == 2 and first.retrieval_budget == 3
    assert first.evaluator_separation_policy == "research_sources_are_teaching_evidence_only"


def test_source_validation_rejects_duplicate_low_quality_and_provenance_missing():
    plan = compile_external_research_plan(requirement=_requirement(), decision=_decision(_requirement()), authority_request_id="authority-external", operator_approval_id="authority-external")
    accepted = normalize_external_research_source(plan, _source("https://math.mit.edu/spectral", "applies to self-adjoint operators"))
    duplicate = normalize_external_research_source(plan, _source("https://math.mit.edu/spectral#section", "applies to self-adjoint operators"), existing=(accepted.as_dict(),))
    low = normalize_external_research_source(plan, _source("https://math.mit.edu/forum", "informal claim", source_class="community_or_forum"))
    missing = normalize_external_research_source(plan, {"content": "spectral theorem", "claims": ("spectral theorem",)})
    assert accepted.status == "accepted"
    assert duplicate.status == "rejected" and "duplicate_or_mirrored_source" in duplicate.rejection_reasons
    assert low.status == "rejected" and "source_class_not_permitted" in low.rejection_reasons
    assert missing.status == "rejected" and "provenance_missing" in missing.rejection_reasons


def test_contradictions_remain_explicit_and_never_become_evaluator_material():
    plan = compile_external_research_plan(requirement=_requirement(), decision=_decision(_requirement()), authority_request_id="authority-external", operator_approval_id="authority-external")
    first = normalize_external_research_source(plan, _source("https://math.mit.edu/spectral-a", "applies to self-adjoint operators"))
    second = normalize_external_research_source(plan, _source("https://ocw.mit.edu/spectral-b", "does not apply to arbitrary non-normal operators"))
    result = synthesize_external_research_result(plan, (first, second))
    assert result["contradictions"]
    assert result["provisional_resource"]["sealed_evaluation_cases"] == ()
    assert "independently_authored" in result["provisional_resource"]["evaluation_requirements"]


def test_no_approval_or_claim_means_zero_adapter_calls():
    calls: list[dict[str, object]] = []
    adapter = lambda plan: calls.append(plan) or ()
    pending = _external_pending()
    blocked = execute_claimed_developmental_external_research(pending, adapter=adapter, adapter_identity="fixture-adapter")
    assert not calls and blocked.continuous_mission_state == "developmental_external_research_blocked"
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="wrong")
    assert not calls and approved.continuous_mission_state != "developmental_external_research_plan_ready"


def test_claim_is_durable_before_adapter_execution_and_restart_does_not_duplicate():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    claim = claimed.continuous_learning_state["external_research"]["claim"]
    assert claim["claim_state"] == "research_execution_claimed"
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="external-research"), export_continuous_mission_restart_state(claimed))
    calls: list[dict[str, object]] = []
    retrieval_claimed = claim_developmental_external_research_retrieval(restored, adapter_identity="fixture-adapter")
    restored_retrieval = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="external-research"), export_continuous_mission_restart_state(retrieval_claimed))
    completed = execute_claimed_developmental_external_research(restored_retrieval, adapter=lambda plan: calls.append(plan) or (_source("https://math.mit.edu/spectral", "applies to self-adjoint operators"),), adapter_identity="fixture-adapter")
    assert len(calls) == 1
    assert completed.continuous_learning_state["external_research"]["result"]["status"] == "research_completed"
    fulfillment = completed.continuous_learning_state["developmental_resource_fulfillments"][-1]
    assert fulfillment["fulfillment_type"] == "external_research_fulfillment"
    assert fulfillment["status"] == "validated"
    assert fulfillment["evaluator_independence_state"] == "not_applicable"
    replay = execute_claimed_developmental_external_research(completed, adapter=lambda plan: calls.append(plan) or (), adapter_identity="fixture-adapter")
    assert len(calls) == 1 and replay.continuous_learning_state["external_research"]["result"]["status"] == "research_completed"


def test_invalid_research_restart_state_fails_closed_and_partial_results_do_not_resume():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    partial = execute_claimed_developmental_external_research(retrieval_claimed, adapter=lambda plan: (_source("https://not-allowed.example/spectral", "applies to self-adjoint operators"),), adapter_identity="fixture-adapter")
    assert partial.continuous_mission_state == "developmental_external_research_incomplete"
    restart = export_continuous_mission_restart_state(claimed)
    restart["continuous_learning_state"] = {**restart["continuous_learning_state"], "external_research": {"plan": {"research_plan_id": "tampered"}, "claim": {}}}
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="external-research"), restart)
    assert restored.continuous_mission_state == "developmental_external_research_blocked"


def test_source_validation_failure_retires_dependent_fulfillment_request():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    failed = execute_claimed_developmental_external_research(
        retrieval_claimed,
        adapter=lambda _plan: (_source("https://math.mit.edu/spectral", "unrelated material", content="unrelated material"),),
        adapter_identity="fixture-adapter",
    )
    assert failed.continuous_mission_state == "developmental_external_research_incomplete"
    request = next(item for item in failed.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_resource_fulfillment")
    assert request["status"] == "blocked"
    assert request["resolution"] == "research_plan_terminal_validation_failure"


def test_direct_topic_candidate_requires_relevance_failure_and_is_exactly_bound():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    failed = execute_claimed_developmental_external_research(
        retrieval_claimed,
        adapter=lambda _plan: (_source("https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/", "unrelated material", content="generic linear algebra course landing page"),),
        adapter_identity="fixture-adapter",
    )
    research = failed.continuous_learning_state["external_research"]
    candidates = compile_direct_topic_source_candidates(research)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["target_kind"] == "direct_topic_specific"
    assert candidate["canonical_target"].endswith("mit18_701f10_spthm")
    assert candidate["required_topic_terms"] == ("spectral theorem", "hermitian")
    requested = compile_relevance_failed_direct_topic_authority(failed)
    request = next(item for item in requested.continuous_developmental_insight_requests if item.get("status") == "pending")
    plan = requested.continuous_learning_state["external_research"]["fallback"]["plan"]
    assert request["fallback_plan_id"] == plan["research_plan_id"]
    assert plan["source_target_kind"] == "direct_topic_specific"
    assert plan["required_topic_terms"] == ("spectral theorem", "hermitian")
    assert requested.continuous_mission_state == "awaiting_operator_insight"


def test_direct_topic_plan_rejects_landing_page_or_missing_declared_terms():
    plan = compile_external_research_plan(
        requirement=_requirement(), decision=_decision(_requirement()), authority_request_id="direct-topic", operator_approval_id="direct-topic",
        source_target="https://ocw.mit.edu/courses/18-701-algebra-i-fall-2010/resources/mit18_701f10_spthm/",
        source_class="recognized_reference", source_organization="MIT OpenCourseWare",
        required_topic_terms=("spectral theorem", "hermitian"), source_target_kind="direct_topic_specific",
    )
    landing = normalize_external_research_source(plan, _source("https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/", "spectral theorem", content="The spectral theorem appears in this generic course."))
    missing = normalize_external_research_source(plan, _source(plan.source_target, "spectral theorem", content="The spectral theorem is introduced here."))
    accepted = normalize_external_research_source(plan, _source(plan.source_target, "applies to hermitian matrices", content="The spectral theorem for hermitian matrices identifies the complex inner product scope."))
    assert "direct_target_mismatch" in landing.rejection_reasons
    assert "topic_relevance_unproven" in missing.rejection_reasons
    assert accepted.status == "accepted"


def test_bounded_transport_failure_is_persisted_without_a_retry_or_fabricated_source():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    completed = execute_claimed_developmental_external_research(
        retrieval_claimed,
        adapter=lambda _plan: (_ for _ in ()).throw(ExternalResearchRetrievalError("content_type_rejected")),
        adapter_identity="fixture-adapter",
    )
    research = completed.continuous_learning_state["external_research"]
    assert research["result"] == {"status": "research_failed", "failure_state": "content_type_rejected"}
    assert research["retrieval_attempts"][0]["status"] == "retrieval_failed"
    assert research["retrieval_attempts"][0]["failure_state"] == "content_type_rejected"
    replay = execute_claimed_developmental_external_research(
        completed,
        adapter=lambda _plan: (_ for _ in ()).throw(AssertionError("must not retry")),
        adapter_identity="fixture-adapter",
    )
    assert replay is completed


def test_legacy_unknown_transport_failure_cannot_create_a_fallback_request():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    failed = execute_claimed_developmental_external_research(
        retrieval_claimed,
        adapter=lambda _plan: (_ for _ in ()).throw(RuntimeError("legacy")),
        adapter_identity="fixture-adapter",
    )
    fallback = compile_failed_research_fallback_authority(failed)
    research = fallback.continuous_learning_state["external_research"]
    assert fallback.continuous_mission_state == "developmental_external_research_fallback_blocked"
    assert research["fallback"]["failure"]["normalized_failure_type"] == "unknown_transport_failure"
    assert not research["fallback"]["candidates"]


def test_source_specific_failure_creates_one_distinct_fallback_plan_and_preserves_history():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    failed = execute_claimed_developmental_external_research(
        retrieval_claimed,
        adapter=lambda _plan: (_ for _ in ()).throw(ExternalResearchRetrievalError("HTTPError")),
        adapter_identity="fixture-adapter",
    )
    original = failed.continuous_learning_state["external_research"]
    fallback_pending = compile_failed_research_fallback_authority(failed)
    request = next(item for item in fallback_pending.continuous_developmental_insight_requests if item.get("status") == "pending")
    candidate = fallback_pending.continuous_learning_state["external_research"]["fallback"]["selected_candidate"]
    plan = fallback_pending.continuous_learning_state["external_research"]["fallback"]["plan"]
    assert candidate["canonical_target"] != original["retrieval_attempts"][0]["target_reference"]
    assert plan["prior_plan_id"] == original["plan"]["research_plan_id"]
    assert plan["prior_failure_id"] == fallback_pending.continuous_learning_state["external_research"]["fallback"]["failure"]["failure_id"]
    assert plan["plan_version"] == 2 and plan["query_budget"] == plan["retrieval_budget"] == 1
    assert plan["source_target"].endswith("/")
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="external-research"), export_continuous_mission_restart_state(fallback_pending))
    assert len([item for item in restored.continuous_developmental_insight_requests if item.get("status") == "pending"]) == 1
    fallback_approved = consume_developmental_resource_authority_response(
        restored, request_id=request["request_id"], selected_option="approve_scoped_authority", approved_scope=request["authority_scope"],
    )
    active = fallback_approved.continuous_learning_state["external_research"]
    assert active["plan"]["research_plan_id"] == plan["research_plan_id"]
    assert active["history"][0]["plan"] == original["plan"]
    claimed_fallback = claim_developmental_external_research_execution(fallback_approved, adapter_identity="fixture-adapter")
    retrieval_fallback = claim_developmental_external_research_retrieval(claimed_fallback, adapter_identity="fixture-adapter")
    completed = execute_claimed_developmental_external_research(
        retrieval_fallback,
        adapter=lambda _plan: (_source(candidate["retrieval_target"], "applies to self-adjoint operators in complex inner product spaces"),),
        adapter_identity="fixture-adapter",
    )
    assert completed.continuous_learning_state["external_research"]["result"]["status"] == "research_completed"
    assert completed.continuous_learning_state["external_research"]["history"][0]["claim"]["claim_state"] == "research_failed"


def test_historical_transport_interpretation_needs_a_distinct_working_target_before_fallback():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    failed = execute_claimed_developmental_external_research(
        retrieval_claimed,
        adapter=lambda _plan: (_ for _ in ()).throw(ExternalResearchRetrievalError("HTTPError")),
        adapter_identity="fixture-adapter",
    )
    research = failed.continuous_learning_state["external_research"]
    original_result = dict(research["result"])
    insufficient = compile_historical_transport_interpretation(research, ())
    source_specific = compile_historical_transport_interpretation(research, (
        {"diagnostic_id": "failed-target", "canonical_target": research["retrieval_attempts"][0]["target_reference"], "terminal_state": "diagnostic_failed", "systemic_indicator": False},
        {"diagnostic_id": "working-control", "canonical_target": "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/", "terminal_state": "diagnostic_completed", "systemic_indicator": False},
    ))
    assert insufficient["fallback_eligible"] is False
    assert source_specific["classification"] == "source_specific"
    assert source_specific["fallback_eligible"] is True
    assert research["result"] == original_result


def test_derived_source_specific_interpretation_can_create_one_fallback_without_rewriting_history():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    failed = execute_claimed_developmental_external_research(
        retrieval_claimed,
        adapter=lambda _plan: (_ for _ in ()).throw(RuntimeError("legacy")),
        adapter_identity="fixture-adapter",
    )
    research = failed.continuous_learning_state["external_research"]
    original_result = dict(research["result"])
    interpreted = record_external_transport_diagnostic_interpretation(failed, (
        {"diagnostic_id": "failed-target", "canonical_target": research["retrieval_attempts"][0]["target_reference"], "terminal_state": "diagnostic_failed", "normalized_exception_class": "http_client_error", "systemic_indicator": False},
        {"diagnostic_id": "working-control", "canonical_target": "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/", "terminal_state": "diagnostic_completed", "normalized_exception_class": "", "systemic_indicator": False},
    ))
    fallback = compile_failed_research_fallback_authority(interpreted)
    pending_requests = [item for item in fallback.continuous_developmental_insight_requests if item.get("status") == "pending"]
    assert len(pending_requests) == 1
    assert fallback.continuous_learning_state["external_research"]["result"] == original_result
    assert fallback.continuous_learning_state["external_research"]["fallback"]["failure"]["derived_interpretation_id"]


def test_proven_locator_repair_requires_a_new_authority_request():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    failed = execute_claimed_developmental_external_research(
        retrieval_claimed,
        adapter=lambda _plan: (_ for _ in ()).throw(ExternalResearchRetrievalError("HTTPError")),
        adapter_identity="fixture-adapter",
    )
    state = dict(failed.continuous_learning_state)
    research = dict(state["external_research"])
    target = "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010"
    research["plan"] = {**research["plan"], "source_target": target, "allowed_domains": ("ocw.mit.edu",)}
    research["retrieval_attempts"] = ({**research["retrieval_attempts"][0], "target_reference": target},)
    repaired_input = replace(failed, continuous_learning_state={**state, "external_research": research})
    interpreted = record_external_transport_diagnostic_interpretation(repaired_input, (
        {"diagnostic_id": "ocw-working-locator", "canonical_target": target + "/", "terminal_state": "diagnostic_completed", "normalized_exception_class": "", "systemic_indicator": False},
    ))
    retry = compile_failed_research_adapter_repair_authority(interpreted)
    request = next(item for item in retry.continuous_developmental_insight_requests if item.get("status") == "pending")
    assert request["request_id"] != "authority-external"
    assert request["fallback_plan_id"] != research["plan"]["research_plan_id"]
    assert retry.continuous_learning_state["external_research"]["fallback"]["plan"]["source_target"].endswith("/")


def test_retrieval_budget_stops_extra_sources_and_preserves_partial_result():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    retrieval_claimed = claim_developmental_external_research_retrieval(claimed, adapter_identity="fixture-adapter")
    exhausted = execute_claimed_developmental_external_research(
        retrieval_claimed,
        adapter=lambda plan: tuple(_source(f"https://math.mit.edu/spectral-{index}", f"applies to condition {index}") for index in range(4)),
        adapter_identity="fixture-adapter",
    )
    research = exhausted.continuous_learning_state["external_research"]
    assert len(research["source_records"]) == research["plan"]["retrieval_budget"]
    assert research["result"]["status"] == "research_partially_completed"
    assert exhausted.continuous_mission_state == "developmental_external_research_incomplete"


def test_claim_contract_is_exactly_bound_to_plan_and_approval():
    plan = compile_external_research_plan(requirement=_requirement(), decision=_decision(_requirement()), authority_request_id="authority-external", operator_approval_id="authority-external")
    claim = compile_execution_claim(plan, adapter_identity="fixture-adapter")
    assert claim.research_plan_id == plan.research_plan_id
    assert claim.authority_request_id == plan.authority_request_id
    assert research_state_is_valid({"plan": plan.as_dict(), "claim": claim.as_dict(), "source_records": ()})


def test_rc8_adapter_is_bounded_and_never_marks_a_live_network_call():
    plan = compile_external_research_plan(requirement=_requirement(), decision=_decision(_requirement()), authority_request_id="authority-external", operator_approval_id="authority-external")
    sources = execute_rc8_mock_research_adapter(plan.as_dict())
    assert len(sources) == 1
    assert sources[0]["url"].startswith("https://")
