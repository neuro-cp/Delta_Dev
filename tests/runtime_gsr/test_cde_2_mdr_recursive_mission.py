from __future__ import annotations

from dataclasses import replace

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


MISSION_TEXT = "Develop the minimum demonstrated capabilities required to conduct a rigorous, evidence-linked investigation of a bounded mathematical question, then begin that investigation."


def _mission_chain():
    request = gsr.make_capability_development_mission_request(
        original_operator_wording=MISSION_TEXT,
        intended_outcome="mission-driven bounded mathematical investigation after prerequisite capability development",
        domain="bounded_mathematical_question",
        constraints=("fixture_only", "no_network", "operator_review_required"),
        prohibited_outcomes=("autonomous_git", "tracked_source_application", "capability_self_activation"),
        success_concept="first blocker developed and parent mission resumed",
        requested_sequence=3000,
    )
    authorization = gsr.make_capability_development_mission_authorization(request, issued_sequence=3001, expiration_sequence=3100)
    mission_result = gsr.interpret_capability_development_mission(request, authorization, sequence=3002)
    assert mission_result.accepted is True
    graph_result = gsr.build_required_capability_graph(mission_result.mission)
    assert graph_result.accepted is True
    self_model = gsr.build_demonstrated_capability_self_model()
    analysis = gsr.analyze_capability_gaps(graph_result.graph, self_model, mission_result.mission)
    selection = gsr.select_capability_prerequisite(analysis, graph_result.graph)
    return mission_result, graph_result, self_model, analysis, selection


def _cde2_chain(*, operator_approved: bool = True):
    mission_result, graph_result, self_model, analysis, selection = _mission_chain()
    request = gsr.make_capability_specification_request(mission_result.mission, selection, requested_sequence=3010)
    authorization = gsr.make_capability_specification_authorization(request, issued_sequence=3011, expiration_sequence=3100)
    spec_result = gsr.synthesize_capability_specification(mission_result.mission, graph_result.graph, self_model, selection, request, authorization, sequence=3012)
    assert spec_result.accepted is True
    options = gsr.generate_capability_architecture_options(spec_result.specification)
    selected = gsr.select_minimum_viable_architecture(spec_result.specification, options)
    validation_plan = gsr.synthesize_capability_validation_plan(spec_result.specification, selected)
    implementation_plan = gsr.synthesize_capability_implementation_plan(spec_result.specification, selected, validation_plan)
    campaign = gsr.run_capability_implementation_campaign(spec_result.specification, selected, validation_plan, implementation_plan, sequence=3020)
    promotion = gsr.analyze_capability_integration_and_promotion(spec_result.specification, campaign, operator_approved=operator_approved)
    resumption = gsr.resume_parent_mission_after_capability(mission_result.mission, promotion, analysis)
    state = gsr.make_recursive_mission_state(mission_result.mission, self_model, selection.selected_capability_id)
    invocation = gsr.invoke_capability_development_from_mission(state, selection, sequence=3030)
    resumed_state = gsr.resume_recursive_mission_after_approval(invocation.state, promotion)
    review = gsr.create_recursive_mission_review_package(resumed_state, mission_result.mission, graph_result.graph, self_model, spec_result.specification, options, selected, campaign, promotion, resumption)
    return mission_result, graph_result, self_model, analysis, selection, spec_result, options, selected, validation_plan, implementation_plan, campaign, promotion, resumption, state, invocation, resumed_state, review


def test_cde_2a_specification_is_bound_to_exact_gap_and_authority():
    mission_result, graph_result, self_model, analysis, selection = _mission_chain()
    request = gsr.make_capability_specification_request(mission_result.mission, selection, requested_sequence=3010)
    authorization = gsr.make_capability_specification_authorization(request, issued_sequence=3011, expiration_sequence=3100)
    result = gsr.synthesize_capability_specification(mission_result.mission, graph_result.graph, self_model, selection, request, authorization, sequence=3012)
    assert result.accepted is True
    assert result.authorization_consumed is True
    assert result.specification.capability_id == selection.selected_capability_id
    assert result.specification.parent_mission_id == mission_result.mission.mission_id
    assert "self_activation" in result.specification.prohibited_behavior

    bad = gsr.synthesize_capability_specification(
        mission_result.mission,
        graph_result.graph,
        self_model,
        selection,
        replace(request, selected_capability_id="unrelated_capability"),
        authorization,
        sequence=3012,
    )
    assert bad.accepted is False
    assert bad.reason == "selected_gap_substitution"


def test_cde_2b_2c_architecture_options_are_bounded_and_reuse_biased():
    *_, spec_result, options, selected, _validation, _impl, _campaign, _promotion, _resumption, _state, _invocation, _resumed, _review = _cde2_chain()
    assert options.accepted is True
    assert len(options.options) <= 3
    assert options.implementation_started is False
    assert selected.outcome == "select_minimum_viable_architecture"
    selected_option = next(payload for payload in options.options if payload["option_id"] == selected.selected_option_id)
    assert selected_option["reuse_score"] >= selected_option["novelty_score"]
    assert selected.rejected_option_reasons

    too_many = gsr.generate_capability_architecture_options(spec_result.specification, requested_option_count=4)
    assert too_many.accepted is False
    assert too_many.reason == "architecture_option_limit_exceeded"
    recursive = gsr.generate_capability_architecture_options(spec_result.specification, recursive=True)
    assert recursive.reason == "recursive_option_generation_denied"


def test_cde_2d_2e_validation_and_implementation_plans_precede_campaign():
    *_, spec_result, _options, selected, validation_plan, implementation_plan, campaign, _promotion, _resumption, _state, _invocation, _resumed, _review = _cde2_chain()
    assert validation_plan.frozen_before_implementation is True
    assert validation_plan.achievable_evidence_tier == "fixture_validated"
    assert "scientific competence" in validation_plan.claims_not_proven
    assert implementation_plan.direct_source_mutation is False
    assert len(implementation_plan.files_for_modification) <= implementation_plan.maximum_changed_file_count
    assert campaign.accepted is True
    assert campaign.tracked_source_mutated is False
    assert campaign.capability_activated is False

    unfrozen = replace(validation_plan, frozen_before_implementation=False)
    denied = gsr.run_capability_implementation_campaign(spec_result.specification, selected, unfrozen, implementation_plan, sequence=3021)
    assert denied.accepted is False
    assert denied.reason == "validation_plan_not_frozen"


def test_cde_2g_2h_promotion_and_parent_resumption_require_operator_approval():
    chain = _cde2_chain(operator_approved=True)
    promotion = chain[11]
    resumption = chain[12]
    assert promotion.promotion_allowed is True
    assert promotion.evidence_tier_reached == "operator_approved"
    assert promotion.activation_required is True
    assert resumption.capability_approved is True
    assert resumption.outcome in {"select_next_blocking_capability", "mission_feasible"}

    rejected = _cde2_chain(operator_approved=False)
    rejected_promotion = rejected[11]
    rejected_resumption = rejected[12]
    assert rejected_promotion.promotion_allowed is False
    assert rejected_promotion.evidence_tier_reached == "fixture_validated"
    assert rejected_resumption.outcome == "pause_capability_rejected"


def test_mdr_1a_to_1f_recursive_state_blockers_invocation_and_limits():
    mission_result, _graph, self_model, analysis, selection = _mission_chain()
    state = gsr.make_recursive_mission_state(mission_result.mission, self_model, selection.selected_capability_id)
    assert state.original_parent_mission == MISSION_TEXT
    assert gsr.detect_recursive_mission_blocker(state, analysis) == "capability_gap_blocking"

    invocation = gsr.invoke_capability_development_from_mission(state, selection, sequence=3030)
    assert invocation.accepted is True
    assert invocation.active_campaigns == 1
    nested = gsr.invoke_capability_development_from_mission(invocation.state, selection, sequence=3031)
    assert nested.accepted is False
    assert nested.reason == "nested_active_campaign_denied"

    limited = replace(state, recursion_depth=3)
    assert gsr.enforce_recursive_mission_limits(limited) == "recursion_limit"
    drift = gsr.enforce_recursive_mission_limits(state, parent_mission="changed")
    assert drift == "scope_drift"
    repeated = gsr.enforce_recursive_mission_limits(state, repeated_blocker_count=2)
    assert repeated == "repeated_blocker"


def test_mdr_1g_review_package_and_closure_accept_successful_recursive_pilot():
    chain = _cde2_chain()
    review = chain[-1]
    assert review.original_mission == MISSION_TEXT
    assert review.capability_specifications
    assert review.architecture_options_considered
    assert review.selected_architectures
    assert review.development_campaigns
    assert review.validation_evidence
    assert review.final_disposition in {"select_next_blocking_capability", "mission_feasible"}

    authorization = gsr.make_cde2_mdr_closure_authorization(review, issued_sequence=3040, expiration_sequence=3050)
    closure = gsr.evaluate_cde2_mdr_closure(review, authorization, sequence=3041)
    assert closure.accepted is True
    assert closure.reason == "accepted_for_cde_2_mdr_1_closure"
    assert closure.authorization_consumed is True
    assert closure.consumed_authorization.consumed is True
    assert closure.capability_activated is False
    assert closure.tracked_source_mutated is False
    assert closure.autonomous_git_performed is False
    assert closure.provider_called is False
    assert closure.model_invoked is False
    assert closure.network_used is False

    replay = gsr.evaluate_cde2_mdr_closure(review, closure.consumed_authorization, sequence=3042)
    assert replay.accepted is False
    assert replay.reason == "rejected_operator_boundary_bypass"


def test_cde_2_mdr_adversarial_authority_and_unrelated_growth_denials():
    chain = _cde2_chain()
    review = chain[-1]
    authorization = gsr.make_cde2_mdr_closure_authorization(review, issued_sequence=3040, expiration_sequence=3050)

    activation = gsr.evaluate_cde2_mdr_closure(review, replace(authorization, capability_activation_prohibited=False), sequence=3041)
    assert activation.accepted is False
    assert activation.reason == "rejected_capability_self_approval"

    git = gsr.evaluate_cde2_mdr_closure(review, replace(authorization, autonomous_git_prohibited=False), sequence=3041)
    assert git.reason == "rejected_permission_expansion"

    incomplete = replace(review, capability_specifications=())
    denied = gsr.evaluate_cde2_mdr_closure(incomplete, gsr.make_cde2_mdr_closure_authorization(incomplete, issued_sequence=3040, expiration_sequence=3050), sequence=3041)
    assert denied.accepted is False
    assert denied.reason == "rejected_incomplete_evidence"
