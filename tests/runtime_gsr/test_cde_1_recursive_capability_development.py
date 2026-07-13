from __future__ import annotations

from dataclasses import replace

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


MISSION_TEXT = "Develop the minimum demonstrated capabilities required to conduct a rigorous, evidence-linked investigation of a bounded mathematical question."


def _mission_result(**request_overrides):
    request = gsr.make_capability_development_mission_request(
        original_operator_wording=MISSION_TEXT,
        intended_outcome="rigorous evidence-linked bounded mathematical investigation capability",
        domain="bounded_mathematical_question",
        constraints=("fixture_only", "no_external_models", "no_network", "operator_review_required"),
        prohibited_outcomes=("claim_scholar_status", "tracked_source_application", "capability_self_activation"),
        success_concept="first missing prerequisite identified and developed through a bounded fixture campaign",
        requested_sequence=2000,
        **request_overrides,
    )
    authorization = gsr.make_capability_development_mission_authorization(request, issued_sequence=2001, expiration_sequence=2100)
    result = gsr.interpret_capability_development_mission(request, authorization, sequence=2002)
    assert result.accepted is True
    return request, authorization, result


def _cde_chain(*, operator_disposition: str = "approve_fixture_validated_capability", overclaim: bool = False):
    _request, _authorization, mission_result = _mission_result()
    graph_result = gsr.build_required_capability_graph(mission_result.mission)
    assert graph_result.accepted is True
    self_model = gsr.build_demonstrated_capability_self_model(overclaim=overclaim)
    analysis = gsr.analyze_capability_gaps(graph_result.graph, self_model, mission_result.mission)
    selection = gsr.select_capability_prerequisite(analysis, graph_result.graph)
    synthesis = gsr.synthesize_capability_development_objective(mission_result.mission, selection)
    cycle = gsr.run_capability_development_cycle(mission_result.mission, selection, synthesis, operator_disposition=operator_disposition, sequence=2010)
    reevaluation = gsr.reevaluate_parent_mission(mission_result.mission, graph_result.graph, analysis, cycle)
    question = gsr.make_capability_operator_question(
        category="capability_activation_required",
        mission=mission_result.mission,
        blocking_capability_id=selection.selected_capability_id,
        current_evidence=("fixture_validated_claim_representation",),
        alternatives=("keep_inactive", "request_activation_later"),
        tradeoffs=("safest default avoids unearned activation",),
        safest_default="keep capability inactive",
        no_response_consequence="mission pauses at operator review boundary",
        exact_authorization_required="operator capability activation review",
    )
    return mission_result, graph_result, self_model, analysis, selection, synthesis, cycle, reevaluation, question


def test_cde_1a_mission_interpretation_preserves_operator_wording_and_boundaries():
    request, authorization, result = _mission_result()
    assert result.reason == "mission_interpreted"
    assert result.authorization_consumed is True
    assert result.consumed_authorization.consumed is True
    assert result.mission.original_operator_wording == MISSION_TEXT
    assert result.interpretation.capability_distinction
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.network_used is False
    assert result.tracked_source_mutated is False

    substituted = replace(authorization, original_operator_wording="Do something easier")
    denied = gsr.interpret_capability_development_mission(request, substituted, sequence=2002)
    assert denied.accepted is False
    assert denied.reason == "mission_wording_substitution"

    permission = gsr.make_capability_development_mission_request(
        original_operator_wording=MISSION_TEXT,
        intended_outcome="rigorous evidence-linked bounded mathematical investigation capability",
        domain="bounded_mathematical_question",
        constraints=("fixture_only",),
        prohibited_outcomes=("tracked_source_application",),
        success_concept="first missing prerequisite",
        requested_sequence=2000,
        permission_expansion_requested=True,
    )
    permission_auth = gsr.make_capability_development_mission_authorization(permission, issued_sequence=2001, expiration_sequence=2100)
    denied_permission = gsr.interpret_capability_development_mission(permission, permission_auth, sequence=2002)
    assert denied_permission.reason == "permission_boundary_requires_operator"


def test_cde_1b_capability_graph_limits_cycles_and_permission_disguise():
    _request, _authorization, mission_result = _mission_result()
    graph = gsr.build_required_capability_graph(mission_result.mission)
    assert graph.accepted is True
    assert len(graph.graph.nodes) == 3
    first = gsr.deserialize(gsr.RequiredCapabilityNode, graph.graph.nodes[0])
    assert first.capability_id == "governed_claim_representation"
    assert first.authority_class != "permission"

    too_many = gsr.build_required_capability_graph(mission_result.mission, node_count=13)
    assert too_many.accepted is False
    assert too_many.reason == "capability_node_limit_exceeded"

    cyclic = gsr.build_required_capability_graph(mission_result.mission, include_cycle=True)
    assert cyclic.accepted is False
    assert cyclic.reason == "capability_graph_cycle_detected"


def test_cde_1c_1d_self_model_and_gap_analysis_prevent_overclaim_and_downstream_selection():
    _request, _authorization, mission_result = _mission_result()
    graph = gsr.build_required_capability_graph(mission_result.mission).graph
    self_model = gsr.build_demonstrated_capability_self_model()
    assert self_model.overclaim_detected is False
    assert all("scholar" not in payload["capability_id"] for payload in self_model.capabilities)

    analysis = gsr.analyze_capability_gaps(graph, self_model, mission_result.mission)
    gaps = [gsr.deserialize(gsr.CapabilityGap, payload) for payload in analysis.gaps]
    assert gaps[0].capability_id == "governed_claim_representation"
    assert gaps[0].classification == "missing"
    assert analysis.first_actionable_gap_id == gaps[0].gap_id

    selection = gsr.select_capability_prerequisite(analysis, graph)
    assert selection.disposition == "select_capability_for_development"
    assert selection.selected_capability_id == "governed_claim_representation"

    overclaim = gsr.build_demonstrated_capability_self_model(overclaim=True)
    assert overclaim.overclaim_detected is True


def test_cde_1e_1f_selection_and_objective_synthesis_are_measurable_and_bounded():
    mission_result, graph_result, self_model, analysis, selection, synthesis, _cycle, _reevaluation, _question = _cde_chain()
    assert selection.selected_capability_id == "governed_claim_representation"
    assert selection.disposition == "select_capability_for_development"
    objective_request = gsr.deserialize(gsr.DevelopmentObjectiveRequest, synthesis.objective_request)
    assert objective_request.target_metric == "capability_fixture_contracts"
    assert objective_request.success_thresholds["capability_fixture_contracts"] == 1.0
    assert objective_request.allowed_source_paths == ("claim_representation_fixture.py",)
    assert objective_request.tracked_source_application_requested is False
    assert "improve yourself" not in objective_request.statement.lower()
    assert synthesis.parent_mission_id == mission_result.mission.mission_id


def test_cde_1g_1h_operator_approval_updates_fixture_evidence_only_and_reevaluates():
    _mission_result, _graph_result, _self_model, _analysis, selection, _synthesis, cycle, reevaluation, question = _cde_chain()
    assert cycle.accepted is True
    assert cycle.self_model_update_allowed is True
    assert cycle.capability_evidence_tier == "fixture_validated"
    assert cycle.capability_activated is False
    assert reevaluation.capability_now_demonstrated is True
    assert reevaluation.evidence_tier == "fixture_validated"
    assert reevaluation.parent_mission_unchanged is True
    assert reevaluation.disposition in {"select_next_capability_gap", "mission_feasible"}
    assert question.generic_question is False
    assert question.category == "capability_activation_required"

    rejected = _cde_chain(operator_disposition="reject_fixture_capability")
    rejected_cycle = rejected[6]
    rejected_reevaluation = rejected[7]
    assert rejected_cycle.self_model_update_allowed is False
    assert rejected_cycle.capability_evidence_tier == "not_promoted"
    assert rejected_reevaluation.capability_now_demonstrated is False
    assert rejected_reevaluation.disposition == "pause_for_operator"


def test_cde_1i_generic_questions_are_flagged_and_authorized_continuation_asks_none():
    _request, _authorization, mission_result = _mission_result()
    generic = gsr.make_capability_operator_question(
        category="mission_clarification_required",
        mission=mission_result.mission,
        blocking_capability_id="",
        current_evidence=(),
        alternatives=("continue",),
        tradeoffs=("none",),
        safest_default="pause",
        no_response_consequence="pause",
        exact_authorization_required="What should I do next?",
    )
    assert generic.generic_question is True


def test_cde_1_closure_accepts_scholar_fixture_pilot_and_rejects_adversarial_cases():
    mission_result, graph_result, self_model, analysis, selection, synthesis, cycle, reevaluation, question = _cde_chain()
    authorization = gsr.make_capability_development_closure_authorization(mission_result.mission, reevaluation, issued_sequence=2020, expiration_sequence=2030)
    closure = gsr.evaluate_capability_development_closure(
        mission_result.mission,
        graph_result.graph,
        self_model,
        analysis,
        selection,
        synthesis,
        cycle,
        reevaluation,
        question,
        authorization,
        sequence=2021,
    )
    assert closure.accepted is True
    assert closure.reason == "accepted_for_cde_1_closure"
    assert closure.authorization_consumed is True
    assert closure.consumed_authorization.consumed is True
    assert closure.capability_activated is False
    assert closure.tracked_source_mutated is False
    assert closure.provider_called is False
    assert closure.model_invoked is False
    assert closure.network_used is False

    overclaim_chain = _cde_chain(overclaim=True)
    overclaim = gsr.evaluate_capability_development_closure(
        overclaim_chain[0].mission,
        overclaim_chain[1].graph,
        overclaim_chain[2],
        overclaim_chain[3],
        overclaim_chain[4],
        overclaim_chain[5],
        overclaim_chain[6],
        overclaim_chain[7],
        overclaim_chain[8],
        gsr.make_capability_development_closure_authorization(overclaim_chain[0].mission, overclaim_chain[7], issued_sequence=2020, expiration_sequence=2030),
        sequence=2021,
    )
    assert overclaim.accepted is False
    assert overclaim.reason == "rejected_self_model_overclaim"

    drift = gsr.evaluate_capability_development_closure(
        mission_result.mission,
        graph_result.graph,
        self_model,
        analysis,
        selection,
        replace(synthesis, parent_mission_id="other"),
        cycle,
        reevaluation,
        question,
        authorization,
        sequence=2021,
    )
    assert drift.accepted is False
    assert drift.reason == "rejected_parent_mission_drift"

    recursion = gsr.evaluate_capability_development_closure(
        mission_result.mission,
        graph_result.graph,
        self_model,
        analysis,
        selection,
        synthesis,
        replace(cycle, recursive_depth_used=99),
        reevaluation,
        question,
        authorization,
        sequence=2021,
    )
    assert recursion.accepted is False
    assert recursion.reason == "rejected_unbounded_recursion"
