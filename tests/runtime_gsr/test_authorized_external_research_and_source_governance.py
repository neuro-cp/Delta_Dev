from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    claim_developmental_external_research_execution,
    consume_developmental_resource_authority_response,
    execute_claimed_developmental_external_research,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.developmental_interest import compile_persistent_developmental_agenda
from orchestration.runtime.developmental_resource_policy import compile_developmental_resource_authority_requirement
from orchestration.runtime.governed_external_research import (
    compile_execution_claim,
    compile_external_research_plan,
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
    completed = execute_claimed_developmental_external_research(restored, adapter=lambda plan: calls.append(plan) or (_source("https://math.mit.edu/spectral", "applies to self-adjoint operators"),), adapter_identity="fixture-adapter")
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
    partial = execute_claimed_developmental_external_research(claimed, adapter=lambda plan: (_source("https://not-allowed.example/spectral", "applies to self-adjoint operators"),), adapter_identity="fixture-adapter")
    assert partial.continuous_mission_state == "developmental_external_research_incomplete"
    restart = export_continuous_mission_restart_state(claimed)
    restart["continuous_learning_state"] = {**restart["continuous_learning_state"], "external_research": {"plan": {"research_plan_id": "tampered"}, "claim": {}}}
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="external-research"), restart)
    assert restored.continuous_mission_state == "developmental_external_research_blocked"


def test_retrieval_budget_stops_extra_sources_and_preserves_partial_result():
    pending = _external_pending()
    approved = consume_developmental_resource_authority_response(pending, request_id="authority-external", selected_option="approve_scoped_authority", approved_scope="bounded external research only")
    claimed = claim_developmental_external_research_execution(approved, adapter_identity="fixture-adapter")
    exhausted = execute_claimed_developmental_external_research(
        claimed,
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
