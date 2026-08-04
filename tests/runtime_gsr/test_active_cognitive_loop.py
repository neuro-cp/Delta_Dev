from dataclasses import replace
import json

import pytest

from integration.model_runtime.model_registry import ModelSpec
import orchestration.runtime.active_cognitive_loop as acl
from orchestration.runtime.conversational_runtime_operation import _knowledge_stagnation
import orchestration.runtime.local_model_execution_adapter as lmea
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
    generate_candidate_focuses,
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


def _knowledge_node(node_id, label, criterion, dependencies=(), contribution_contract=None):
    return EvidenceRef(
        node_id,
        "knowledge_contract",
        f"Knowledge frontier node: {label}",
        json.dumps({
            "label": label,
            "parent_id": "goal-battery",
            "completion_criterion_reference": criterion,
            "evidence_need": f"node-specific evidence for {label}",
            "unresolved_questions": [],
            "extracted_claim_ids": [],
            "extracted_concept_ids": [],
            "dependency_node_ids": list(dependencies),
            "minimum_contribution_contract": contribution_contract or {
                "minimum_specific_terms": 3,
                "requires_explanatory_relation": True,
                "reject_importance_only": True,
            },
        }),
        kind="knowledge_frontier_node",
    )


def _knowledge_episode():
    return initialize_episode(
        title="Knowledge acquisition objective",
        goal_summary="Residential battery backup systems",
        expected_state="Knowledge-specific criteria are advanced.",
        evidence=(
            EvidenceRef("operator-natural-goal", "ordinary_chat", "Study residential battery backup systems", ""),
            _knowledge_node("node-capacity", "capacity and outage-duration tradeoffs", "explain capacity versus outage duration"),
            _knowledge_node("node-inverter", "inverter size", "explain inverter sizing constraints"),
        ),
    )


def _many_node_knowledge_episode(count=10):
    nodes = tuple(
        _knowledge_node(f"node-{index}", f"topic {index}", f"address topic {index}")
        for index in range(1, count + 1)
    )
    return initialize_episode(
        title="Knowledge acquisition objective",
        goal_summary="Many node knowledge map",
        expected_state="Knowledge-specific criteria are advanced.",
        evidence=(EvidenceRef("operator-natural-goal", "ordinary_chat", "Study many nodes", ""),) + nodes,
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


def test_knowledge_frontier_packet_is_node_specific_and_excludes_unrelated_hypotheses():
    class CapacityModel:
        model_identity = "scripted-capacity"

        def __call__(self, request, packet):
            return {
                "operation_result_type": "formulate_hypothesis_result",
                "hypothesis_statement": "Capacity and outage-duration tradeoffs determine how long battery backup can support loads.",
                "scope": "capacity and outage-duration tradeoffs",
                "interpretation": "Capacity and outage-duration tradeoffs determine how long battery backup can support loads.",
                "evidence_refs": ["node-capacity"],
                "contrary_evidence_considered": [],
                "assumptions": ["battery capacity is finite"],
                "expected_observations": ["larger loads reduce runtime"],
                "uncertainty": "actual load profile remains unresolved",
                "recommended_state_transition": "propose_hypothesis",
                "raw_model_output": "capacity output",
                "model_identity": self.model_identity,
            }

    state = run_cognitive_cycle(_knowledge_episode(), model_runner=CapacityModel())
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=2)

    assert packet.active_focus["active_frontier_node"]["label"] == "inverter size"
    assert packet.current_hypotheses == ()
    duplicate_targets = packet.active_focus["prohibited_duplicate_targets"]
    assert duplicate_targets
    assert "Capacity and outage-duration" in duplicate_targets[0]["statement_excerpt"]
    assert "inverter sizing constraints" in packet.active_focus["active_frontier_node"]["completion_criterion_reference"]
    snapshot = compile_operation_prompt_snapshot(
        build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test"),
        packet,
    )
    assert "Capacity and outage-duration tradeoffs determine how long battery backup can support loads." not in snapshot.prompt_text
    assert "prohibited_duplicate_targets" not in snapshot.prompt_text


def test_frontier_packet_pins_active_node_beyond_packet_budget():
    state = _many_node_knowledge_episode(count=10)
    candidates = generate_candidate_focuses(state)
    state = replace(state, attention=select_attention(state, (candidates[8],)))
    packet = build_working_memory_packet(state, sequence=1)
    node = packet.active_focus["active_frontier_node"]
    relevant_ids = {item["evidence_id"] for item in packet.relevant_evidence}

    assert node["label"] == "topic 9"
    assert node["node_id"] in relevant_ids
    assert node["completion_criterion_reference"] == "address topic 9"


def test_capacity_hypothesis_is_rejected_for_inverter_size_node():
    state = run_cognitive_cycle(_knowledge_episode())
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=2)
    request = build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test")

    result = validate_model_result(request, packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Capacity and outage-duration tradeoffs determine how long battery backup can support loads.",
        "scope": "capacity and outage-duration tradeoffs",
        "interpretation": "Capacity and outage-duration tradeoffs determine how long battery backup can support loads.",
        "evidence_refs": ["node-capacity"],
        "contrary_evidence_considered": [],
        "assumptions": ["battery capacity is finite"],
        "expected_observations": ["larger loads reduce runtime"],
        "uncertainty": "actual load profile remains unresolved",
        "recommended_state_transition": "propose_hypothesis",
    })

    assert result.accepted is False
    assert "active_node_evidence_not_cited" in result.rejection_reasons
    assert "scope_not_aligned_with_active_node" in result.rejection_reasons
    assert "interpretation_not_node_specific" in result.rejection_reasons


def test_frontier_prompt_includes_prior_claim_only_for_explicit_dependency():
    class CapacityModel:
        model_identity = "scripted-capacity"

        def __call__(self, request, packet):
            return {
                "operation_result_type": "formulate_hypothesis_result",
                "hypothesis_statement": "Capacity and outage-duration tradeoffs determine how long battery backup can support loads.",
                "scope": "capacity and outage-duration tradeoffs",
                "interpretation": "Capacity and outage-duration tradeoffs determine how long battery backup can support loads.",
                "supporting_evidence_refs": ["node-capacity"],
                "assumptions": ["battery capacity is finite"],
                "expected_observations": ["larger loads reduce runtime"],
                "uncertainty": "actual load profile remains unresolved",
                "recommended_state_transition": "propose_hypothesis",
            }

    state = initialize_episode(
        title="Knowledge acquisition objective",
        goal_summary="Residential battery backup systems",
        expected_state="Knowledge-specific criteria are advanced.",
        evidence=(
            EvidenceRef("operator-natural-goal", "ordinary_chat", "Study residential battery backup systems", ""),
            _knowledge_node("node-capacity", "capacity and outage-duration tradeoffs", "explain capacity versus outage duration"),
            _knowledge_node("node-inverter", "inverter size", "explain inverter sizing constraints", dependencies=("node-capacity",)),
        ),
    )
    state = run_cognitive_cycle(state, model_runner=CapacityModel())
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=2)
    snapshot = compile_operation_prompt_snapshot(
        build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test"),
        packet,
    )

    assert packet.active_focus["explicit_dependencies"][0]["node_id"] == "node-capacity"
    assert "Capacity and outage-duration tradeoffs determine how long battery backup can support loads." in snapshot.prompt_text


def test_repeated_nonproductive_outputs_across_nodes_trigger_stagnation_guard():
    class RepetitiveModel:
        model_identity = "repetitive-local"

        def __call__(self, request, packet):
            return {
                "operation_result_type": request.operation_type + "_result",
                "hypothesis_statement": "The same generic proposition repeats without addressing the active node.",
                "scope": "generic proposition",
                "interpretation": "The same generic proposition repeats without addressing the active node.",
                "supporting_evidence_refs": ["operator-natural-goal"],
                "assumptions": [],
                "expected_observations": [],
                "uncertainty": "repetitive",
                "recommended_state_transition": "propose_hypothesis",
            }

    state = replace(_many_node_knowledge_episode(count=5), budgets={"max_cycles": None, "max_model_calls": None, "max_packet_items": 8})
    for _ in range(8):
        state = run_cognitive_cycle(state, model_runner=RepetitiveModel())

    stagnation = _knowledge_stagnation(state)
    assert stagnation["reason"] == "repeated_nonproductive_hypothesis"
    assert len(stagnation["affected_focus_ids"]) >= 3


def test_aligned_frontier_output_gets_runtime_attached_active_node_ref():
    state = run_cognitive_cycle(_knowledge_episode())
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=2)
    request = build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test")

    result = validate_model_result(request, packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Inverter size constrains which critical loads can start and run during an outage.",
        "scope": "inverter size",
        "interpretation": "Inverter size constrains backup design because motor-starting surge demand can exceed steady running load.",
        "supporting_evidence_refs": ["operator-natural-goal"],
        "assumptions": ["critical loads may include motor loads"],
        "expected_observations": ["higher surge loads require larger inverter ratings"],
        "uncertainty": "actual appliance surge loads remain unknown",
        "recommended_state_transition": "propose_hypothesis",
    })

    assert result.accepted is True
    assert "node-inverter" in result.evidence_refs
    assert request.expected_output_schema["hypothesis_statement"] == "string"
    assert request.expected_output_schema["supporting_evidence_refs"] == "list"


def test_frontier_rejects_prior_node_context_that_dominates_new_contribution():
    state = run_cognitive_cycle(_knowledge_episode())
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=2)
    request = build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test")

    result = validate_model_result(request, packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": (
            "Inverter size depends on site conditions, component constraints, operating demand, and the prior practical design "
            "decision because those earlier capacity tradeoffs determine the output-power requirement."
        ),
        "scope": "inverter size",
        "interpretation": (
            "Inverter size depends on site conditions, component constraints, operating demand, and the prior practical design "
            "decision because those earlier capacity tradeoffs determine the output-power requirement."
        ),
        "supporting_evidence_refs": ["operator-natural-goal"],
        "assumptions": [],
        "expected_observations": [],
        "uncertainty": "site loads remain unknown",
        "recommended_state_transition": "propose_hypothesis",
    })

    assert result.accepted is False
    assert "cross_node_context_dominates_active_contribution" in result.rejection_reasons


def test_frontier_rejects_sibling_node_contribution_as_active_node_completion():
    state = run_cognitive_cycle(_knowledge_episode())
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=2)
    request = build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test")

    assert packet.active_focus["active_frontier_node"]["label"] == "inverter size"
    assert any(item["label"] == "capacity and outage-duration tradeoffs" for item in packet.active_focus["sibling_frontier_nodes"])
    result = validate_model_result(request, packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Battery capacity determines outage duration because stored energy is depleted by the connected load demand.",
        "scope": "inverter size",
        "interpretation": "Battery capacity determines outage duration because stored energy is depleted by the connected load demand.",
        "supporting_evidence_refs": ["operator-natural-goal"],
        "assumptions": [],
        "expected_observations": [],
        "uncertainty": "load demand varies",
        "recommended_state_transition": "propose_hypothesis",
    })

    assert result.accepted is False
    assert "sibling_frontier_node_dominates_active_contribution" in result.rejection_reasons


def test_calibrated_frontier_contracts_reject_tangential_or_shallow_claims_and_accept_maintenance_actions():
    def packet_for(label, kind):
        state = initialize_episode(
            title="Knowledge acquisition objective",
            goal_summary="Generic local map",
            expected_state="Knowledge-specific criteria are advanced.",
            evidence=(
                EvidenceRef("operator-natural-goal", "ordinary_chat", "Study a local system", ""),
                _knowledge_node(
                    "node-1",
                    label,
                    "address " + label,
                    contribution_contract={
                        "minimum_specific_terms": 3,
                        "requires_explanatory_relation": True,
                        "reject_importance_only": True,
                        "contribution_kind": kind,
                        "minimum_action_count": 2,
                    },
                ),
            ),
        )
        state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
        packet = build_working_memory_packet(state, sequence=1)
        request = build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test")
        return request, packet

    collection_request, collection_packet = packet_for("rainwater collection", "mechanism_path")
    tangential = validate_model_result(collection_request, collection_packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Rainwater collection systems can be integrated with irrigation networks to optimize water usage.",
        "scope": "rainwater collection",
        "supporting_evidence_refs": ["node-1"],
        "assumptions": [], "expected_observations": [], "uncertainty": "site layout varies", "recommended_state_transition": "propose_hypothesis",
    })
    verb_collection_request, verb_collection_packet = packet_for("how rain barrels collect water", "mechanism_path")
    overflow_only = validate_model_result(verb_collection_request, verb_collection_packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Rain barrels have a spout or outlet for overflow, which directs excess water away from the structure.",
        "scope": "how rain barrels collect water", "supporting_evidence_refs": ["node-1"],
        "assumptions": [], "expected_observations": [], "uncertainty": "site layout varies", "recommended_state_transition": "propose_hypothesis",
    })
    internal_scope = validate_model_result(verb_collection_request, verb_collection_packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Rain barrels collect roof runoff when gutters route water through a downspout into the barrel inlet.",
        "scope": "knowledge-frontier-node-2c6a2ec7a23eddc0", "supporting_evidence_refs": ["node-1"],
        "assumptions": [], "expected_observations": [], "uncertainty": "gutter layout varies", "recommended_state_transition": "propose_hypothesis",
    })
    overflow_request, overflow_packet = packet_for("overflow", "threshold_and_safe_mitigation")
    shallow = validate_model_result(overflow_request, overflow_packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Overflow occurs when storage capacity is exceeded by incoming water.",
        "scope": "overflow", "supporting_evidence_refs": ["node-1"],
        "assumptions": [], "expected_observations": [], "uncertainty": "rainfall varies", "recommended_state_transition": "propose_hypothesis",
    })
    vague_overflow = validate_model_result(overflow_request, overflow_packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Rain barrels overflow when the water level reaches a threshold, and the overflow is directed to a safe outlet.",
        "scope": "overflow", "supporting_evidence_refs": ["node-1"],
        "assumptions": [], "expected_observations": [], "uncertainty": "outlet details vary", "recommended_state_transition": "propose_hypothesis",
    })
    safe_overflow = validate_model_result(overflow_request, overflow_packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Rain barrel overflow occurs when capacity is exceeded, so an overflow hose diverts excess water away from the foundation.",
        "scope": "overflow", "supporting_evidence_refs": ["node-1"],
        "interpretation": "Rain barrel overflow occurs when capacity is exceeded, so an overflow hose diverts excess water away from the foundation.",
        "assumptions": [], "expected_observations": [], "uncertainty": "site drainage varies", "recommended_state_transition": "propose_hypothesis",
    })
    prevention_request, prevention_packet = packet_for("prevent mosquitoes", "prevention_intervention")
    vague_prevention = validate_model_result(prevention_request, prevention_packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Rain barrels can prevent mosquitoes by creating an environment unsuitable for their breeding.",
        "scope": "prevent mosquitoes", "supporting_evidence_refs": ["node-1"],
        "assumptions": [], "expected_observations": [], "uncertainty": "climate varies", "recommended_state_transition": "propose_hypothesis",
    })
    concrete_prevention = validate_model_result(prevention_request, prevention_packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "A screened inlet and sealed lid prevent mosquitoes because they block adult access to standing water for egg laying.",
        "scope": "prevent mosquitoes", "supporting_evidence_refs": ["node-1"],
        "interpretation": "A screened inlet and sealed lid prevent mosquitoes because they block adult access to standing water for egg laying.",
        "assumptions": [], "expected_observations": [], "uncertainty": "screen condition varies", "recommended_state_transition": "propose_hypothesis",
    })
    maintenance_request, maintenance_packet = packet_for("basic maintenance", "recurring_actions_with_consequence")
    maintenance = validate_model_result(maintenance_request, maintenance_packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Regularly checking clogs, addressing leaks, and securing the container prevents damage and keeps the system working.",
        "scope": "rain barrel maintenance", "supporting_evidence_refs": ["node-1"],
        "interpretation": "Checking, addressing, and securing recurring maintenance conditions prevents damage and preserves operation.",
        "assumptions": [], "expected_observations": [], "uncertainty": "maintenance interval varies", "recommended_state_transition": "propose_hypothesis",
    })

    assert "node_completion_contract_missing:mechanism_path" in tangential.rejection_reasons
    assert "node_completion_contract_missing:mechanism_path" in overflow_only.rejection_reasons
    assert "scope_uses_internal_frontier_node_id" in internal_scope.rejection_reasons
    assert "node_completion_contract_missing:threshold_and_safe_mitigation" in shallow.rejection_reasons
    assert "node_completion_contract_missing:threshold_and_safe_mitigation" in vague_overflow.rejection_reasons
    assert safe_overflow.accepted is True
    assert "node_completion_contract_missing:prevention_intervention" in vague_prevention.rejection_reasons
    assert concrete_prevention.accepted is True
    assert maintenance.accepted is True
    assert maintenance.evaluation_state == "supported"


def test_frontier_adapter_preserves_source_binding_when_model_echoes_active_node_id_as_scope():
    state = initialize_episode(
        title="Knowledge acquisition objective",
        goal_summary="Teach introductory calculus for mechanics",
        expected_state="A prerequisite must demonstrate one mechanics application.",
        evidence=(
            EvidenceRef("operator-natural-goal", "ordinary_chat", "Teach me physics.", ""),
            _knowledge_node(
                "node-calculus",
                "introductory calculus: derivatives and integrals for mechanics",
                "explain how a derivative represents rate of change in one mechanics application",
                contribution_contract={
                    "minimum_specific_terms": 3,
                    "requires_explanatory_relation": True,
                    "requires_expected_observation": True,
                    "reject_importance_only": True,
                    "required_topic_terms": ("derivative", "derivatives", "integral", "integrals", "rate"),
                },
            ),
        ),
    )
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=1)
    request = build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test")
    model_payload = _runtime_payload_from_operation_response("formulate_hypothesis", {
        "hypothesis_statement": (
            "A derivative represents the rate of change of position with time, corresponding to velocity in a mechanics example."
        ),
        "scope": "node-calculus",
        "supporting_evidence_refs": ["node-calculus"],
        "assumptions": [],
        "expected_observations": ["Velocity changes when the position-versus-time slope changes."],
        "uncertainty": "The motion model may not have constant acceleration.",
        "recommended_state_transition": "propose_hypothesis",
    })

    canonical_payload = acl._canonicalize_active_frontier_scope(packet, model_payload)
    result = validate_model_result(request, packet, canonical_payload)

    assert canonical_payload["scope"] == "introductory calculus: derivatives and integrals for mechanics"
    assert result.accepted is True
    assert result.expected_observations == ("Velocity changes when the position-versus-time slope changes.",)


def test_retry_prompt_names_required_frontier_contribution_shape():
    state = initialize_episode(
        title="Knowledge acquisition objective",
        goal_summary="Study rain barrels",
        expected_state="Knowledge-specific criteria are advanced.",
        evidence=(
            EvidenceRef("operator-natural-goal", "ordinary_chat", "Study rain barrels", ""),
            _knowledge_node("node-1", "how rain barrels collect water", "address how rain barrels collect water", contribution_contract={
                "minimum_specific_terms": 3,
                "requires_explanatory_relation": True,
                "reject_importance_only": True,
                "contribution_kind": "mechanism_path",
            }),
        ),
    )
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=1)
    packet = replace(
        packet,
        active_focus={
            **packet.active_focus,
            "retry_attempt": 1,
            "prior_rejection_reasons": ("node_completion_contract_missing:mechanism_path",),
            "retry_rejected_hypotheses": ("Rain barrels collect water through a funnel and storage container.",),
        },
    )
    request = build_operation_request(state, packet, operation_type="reformulate_node_specific_hypothesis", model_identity="qwen-test")

    prompt = compile_operation_prompt_snapshot(request, packet).prompt_text

    assert "mechanism-path node" in prompt
    assert "route or transfer path from source" in prompt
    assert "connector such as because, through, leads to, controls, depends on, represents, corresponds to, or prevents" in prompt
    assert "node_completion_contract_missing:mechanism_path" in prompt
    assert "Rain barrels collect water through a funnel and storage container." in prompt


def test_independent_evaluator_rejects_arithmetic_capacity_contradiction():
    state = initialize_episode(
        title="Knowledge acquisition objective",
        goal_summary="Generic local map",
        expected_state="Knowledge-specific criteria are advanced.",
        evidence=(
            EvidenceRef("operator-natural-goal", "ordinary_chat", "Study a local system", ""),
            _knowledge_node("node-1", "storage capacity", "address storage capacity", contribution_contract={
                "minimum_specific_terms": 3, "requires_explanatory_relation": True, "reject_importance_only": True, "contribution_kind": "sizing_relation",
            }),
        ),
    )
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=1)
    request = build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test")
    result = validate_model_result(request, packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "A 50-gallon capacity can provide water for a family of four during a 10-day period.",
        "scope": "storage capacity", "supporting_evidence_refs": ["node-1"],
        "assumptions": ["average daily water usage is 50 gallons per person per day"],
        "expected_observations": [], "uncertainty": "demand varies", "recommended_state_transition": "propose_hypothesis",
    })

    assert result.accepted is False
    assert result.evaluation_state == "contradicted"
    assert any(reason.startswith("independent_evaluation_arithmetic_capacity_shortfall") for reason in result.rejection_reasons)


def test_frontier_rejects_global_duplicate_then_retries_same_node_with_distinct_operation():
    class DuplicateThenSpecific:
        model_identity = "qwen-test"

        def __call__(self, request, packet):
            node = packet.active_focus["active_frontier_node"]
            generic = "Capacity and outage-duration tradeoffs determine how long battery backup can support loads."
            if node["node_id"] == "node-capacity":
                statement = generic
            elif not packet.active_focus.get("retry_attempt"):
                statement = generic
            else:
                statement = "Inverter size limits which critical loads can start because motor surge demand can exceed steady running power."
            return {
                "operation_result_type": request.operation_type + "_result",
                "hypothesis_statement": statement,
                "scope": node["label"],
                "interpretation": statement,
                "supporting_evidence_refs": ["operator-natural-goal"],
                "assumptions": [],
                "expected_observations": [],
                "uncertainty": "site-specific loads remain unknown",
                "recommended_state_transition": "propose_hypothesis",
            }

    state = run_cognitive_cycle(_knowledge_episode(), model_runner=DuplicateThenSpecific())
    state = run_cognitive_cycle(state, model_runner=DuplicateThenSpecific())
    state = run_cognitive_cycle(state, model_runner=DuplicateThenSpecific())

    first, duplicate, retry = state.operation_results
    first_packet, duplicate_packet, retry_packet = state.working_memory_packets
    assert first.accepted is True
    assert duplicate.accepted is False
    assert "duplicate_prior_node_contribution" in duplicate.rejection_reasons
    assert retry.accepted is True
    assert state.operation_requests[1].operation_type == "formulate_hypothesis"
    assert state.operation_requests[2].operation_type == "reformulate_node_specific_hypothesis"
    assert duplicate_packet.active_focus["active_frontier_node"]["node_id"] == "node-inverter"
    assert retry_packet.active_focus["active_frontier_node"]["node_id"] == "node-inverter"
    assert retry_packet.active_focus["focus_id"] == duplicate_packet.active_focus["focus_id"]
    assert "duplicate_prior_node_contribution" in retry_packet.active_focus["prior_rejection_reasons"]
    assert first_packet.active_focus["active_frontier_node"]["node_id"] == "node-capacity"
    retry_prompt = compile_operation_prompt_snapshot(state.operation_requests[2], retry_packet)
    assert "RETRY TARGET:" in retry_prompt.prompt_text
    assert "Required new proposition: explain inverter sizing constraints." in retry_prompt.prompt_text


def test_accepted_frontier_node_is_removed_from_persisted_attention_candidates():
    state = run_cognitive_cycle(_knowledge_episode())

    assert state.attention.active_focus_id == ""
    assert "capacity and outage-duration" not in " ".join(item.description for item in state.attention.candidate_focuses)
    assert any("inverter size" in item.description for item in state.attention.candidate_focuses)
    assert all("capacity and outage-duration" not in item.description for item in state.next_focus_candidates)


def test_malformed_retry_gets_one_same_node_format_repair_before_completion():
    class DuplicateMalformedThenRepaired:
        model_identity = "qwen-test"

        def __call__(self, request, packet):
            node = packet.active_focus["active_frontier_node"]
            generic = "Capacity and outage-duration tradeoffs determine how long battery backup can support loads."
            if node["node_id"] == "node-capacity":
                statement = generic
            elif request.operation_type == "formulate_hypothesis":
                statement = generic
            elif request.operation_type == "reformulate_node_specific_hypothesis":
                return {
                    "operation_result_type": "cognitive_operation",
                    "interpretation": "The replacement should be more specific to inverter size.",
                    "evidence_refs": ["operator-natural-goal", node["node_id"]],
                    "uncertainty": "exact surge loads remain unknown",
                    "recommended_state_transition": "propose_hypothesis",
                }
            else:
                statement = "Inverter size must cover both continuous demand and short motor-starting surge demand for the selected critical loads."
            return {
                "operation_result_type": request.operation_type + "_result",
                "hypothesis_statement": statement,
                "scope": node["label"],
                "interpretation": statement,
                "supporting_evidence_refs": ["operator-natural-goal"],
                "assumptions": [],
                "expected_observations": [],
                "uncertainty": "site-specific loads remain unknown",
                "recommended_state_transition": "propose_hypothesis",
            }

    state = _knowledge_episode()
    for _ in range(4):
        state = run_cognitive_cycle(state, model_runner=DuplicateMalformedThenRepaired())

    operations = [request.operation_type for request in state.operation_requests]
    packets = state.working_memory_packets
    assert operations == [
        "formulate_hypothesis",
        "formulate_hypothesis",
        "reformulate_node_specific_hypothesis",
        "repair_node_specific_hypothesis_format",
    ]
    assert "retry_output_schema_invalid" in state.operation_results[2].rejection_reasons
    assert state.operation_results[3].accepted is True
    assert packets[1].active_focus["active_frontier_node"]["node_id"] == "node-inverter"
    assert packets[2].active_focus["active_frontier_node"]["node_id"] == "node-inverter"
    assert packets[3].active_focus["active_frontier_node"]["node_id"] == "node-inverter"


def test_frontier_completion_rejects_generic_importance_and_accepts_concrete_relation():
    state = _knowledge_episode()
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=1)
    node = packet.active_focus["active_frontier_node"]
    packet = replace(packet, active_focus={
        **packet.active_focus,
        "active_frontier_node": {
            **node,
            "minimum_contribution_contract": {
                "minimum_specific_terms": 3,
                "requires_explanatory_relation": True,
                "reject_importance_only": True,
            },
        },
    })
    request = build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test")

    weak = validate_model_result(request, packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Capacity and outage-duration tradeoffs are critical for battery backup systems.",
        "scope": "capacity and outage-duration tradeoffs",
        "interpretation": "Capacity and outage-duration tradeoffs are critical for battery backup systems.",
        "supporting_evidence_refs": ["operator-natural-goal"],
        "assumptions": [],
        "expected_observations": [],
        "uncertainty": "load details remain unknown",
        "recommended_state_transition": "propose_hypothesis",
    })
    strong = validate_model_result(request, packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Capacity and outage-duration tradeoffs depend on critical-load power, usable battery energy, and outage length because higher demand shortens runtime.",
        "scope": "capacity and outage-duration tradeoffs",
        "interpretation": "Capacity and outage-duration tradeoffs depend on critical-load power, usable battery energy, and outage length because higher demand shortens runtime.",
        "supporting_evidence_refs": ["operator-natural-goal"],
        "assumptions": [],
        "expected_observations": [],
        "uncertainty": "actual household loads remain unknown",
        "recommended_state_transition": "propose_hypothesis",
    })

    assert weak.accepted is False
    assert "node_completion_generic_importance_assertion" in weak.rejection_reasons
    assert strong.accepted is True


def test_aligned_novel_frontier_output_completes_only_active_node():
    state = run_cognitive_cycle(_knowledge_episode())
    state = replace(state, attention=select_attention(state, generate_candidate_focuses(state)))
    packet = build_working_memory_packet(state, sequence=2)
    request = build_operation_request(state, packet, operation_type="formulate_hypothesis", model_identity="qwen-test")

    result = validate_model_result(request, packet, {
        "operation_result_type": "formulate_hypothesis_result",
        "hypothesis_statement": "Inverter size must cover the continuous and surge wattage of selected critical loads.",
        "scope": "inverter size",
        "interpretation": "Inverter size must cover continuous load and short surge demand, so motor-starting appliances can constrain backup design even when energy capacity is sufficient.",
        "evidence_refs": ["node-inverter"],
        "contrary_evidence_considered": [],
        "assumptions": ["critical loads include some devices with startup surge"],
        "expected_observations": ["surge-heavy loads require higher inverter ratings"],
        "uncertainty": "actual appliance surge loads remain unknown",
        "recommended_state_transition": "propose_hypothesis",
    })
    updated = apply_operation_result(state, packet, request, result, sequence=2)

    assert result.accepted is True
    assert updated.cycles[-1].focus_id == request.focus_id
    assert updated.hypotheses[-1].originating_focus_id == request.focus_id
    assert "Inverter size" in updated.hypotheses[-1].statement or "inverter size" in updated.hypotheses[-1].statement


def test_rejected_frontier_node_retries_once_with_prior_rejection_context():
    class FirstBadThenGood:
        model_identity = "qwen-test"

        def __call__(self, request, packet):
            node = packet.active_focus["active_frontier_node"]
            if not packet.active_focus.get("prior_rejection_reasons"):
                return {
                    "operation_result_type": "formulate_hypothesis_result",
                    "hypothesis_statement": "A generic unrelated answer about roof color.",
                    "scope": "roof color",
                    "interpretation": "Roof color is unrelated to this battery backup node.",
                    "supporting_evidence_refs": ["operator-natural-goal"],
                    "assumptions": ["unrelated"],
                    "expected_observations": ["unrelated"],
                    "uncertainty": "misaligned",
                    "recommended_state_transition": "propose_hypothesis",
                }
            return {
                "operation_result_type": "formulate_hypothesis_result",
                "hypothesis_statement": "Capacity and outage duration determine how long selected backup loads can run.",
                "scope": node["label"],
                "interpretation": "Capacity and outage duration determine how long selected backup loads can run.",
                "supporting_evidence_refs": ["operator-natural-goal"],
                "assumptions": ["critical loads are known"],
                "expected_observations": ["larger loads shorten runtime"],
                "uncertainty": "actual loads unknown",
                "recommended_state_transition": "propose_hypothesis",
            }

    state = run_cognitive_cycle(_knowledge_episode(), model_runner=FirstBadThenGood())
    assert state.loop_state == "selecting_focus"
    state = run_cognitive_cycle(state, model_runner=FirstBadThenGood())

    assert len(state.operation_results) == 2
    assert state.operation_results[0].accepted is False
    assert state.operation_results[1].accepted is True
    assert state.cycles[0].focus_id == state.cycles[1].focus_id
    assert state.working_memory_packets[-1].active_focus["prior_rejection_reasons"]
    assert state.working_memory_packets[-1].active_focus["prohibited_duplicate_targets"]
    assert state.loop_state != "blocked_insufficient_evidence"


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


def test_ledger_runner_attempts_one_registered_local_fallback(monkeypatch, tmp_path):
    class FakeProviderManager:
        def __init__(self):
            self.calls = []

        def infer(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs["model_name"] == "qwen":
                raise RuntimeError("qwen runtime unavailable")

            class Result:
                answer = '{"hypothesis_statement":"fallback worked","scope":"test","supporting_evidence_refs":["operator-natural-goal"],"assumptions":["bounded"],"expected_observations":["typed output"],"uncertainty":"low","recommended_state_transition":"propose_hypothesis"}'
                confidence = 0.7
                model_id = "llama-test"
                latency_seconds = 0.2
                response_tokens = 12

            return Result()

    qwen = tmp_path / "qwen.gguf"
    llama = tmp_path / "llama.gguf"
    qwen.write_text("q", encoding="utf-8")
    llama.write_text("l", encoding="utf-8")
    monkeypatch.setattr(acl, "list_available_models", lambda: {
        "qwen": ModelSpec("qwen-test", str(qwen), 3, "qwen", 4096, family="qwen"),
        "llama": ModelSpec("llama-test", str(llama), 4, "llama", 4096, family="llama"),
    })
    manager = FakeProviderManager()
    runner = LedgerBackedCognitiveModelRunner(ledger=object(), provider_manager=manager)

    result = runner._execute_exact_prompt(
        "JSON prompt",
        {"selected_model": "qwen", "model_family": "qwen", "lane": "reasoning_analysis"},
        operation_type="formulate_hypothesis",
    )

    assert result["executed"] is True
    assert result["model_id"] == "llama-test"
    assert [call["model_name"] for call in manager.calls] == ["qwen", "llama"]
    assert result["model_attempts"][0]["succeeded"] is False
    assert result["model_attempts"][1]["succeeded"] is True


def test_ledger_runner_uses_venv_subprocess_when_ui_python_lacks_llama_cpp(monkeypatch):
    class MissingLlamaCppProvider:
        def infer(self, **_kwargs):
            raise ModuleNotFoundError("No module named 'llama_cpp'")

    monkeypatch.setattr(lmea, "execute_local_model_via_venv_subprocess", lambda **kwargs: {
        "executed": True,
        "answer": '{"hypothesis_statement":"venv path worked","scope":"test","supporting_evidence_refs":["operator-natural-goal"],"assumptions":["bounded"],"expected_observations":["typed output"],"uncertainty":"low","recommended_state_transition":"propose_hypothesis"}',
        "model_id": "qwen-test",
        "confidence_score": 0.7,
        "response_tokens": 10,
        "execution_adapter": kwargs["execution_adapter"],
    })
    runner = LedgerBackedCognitiveModelRunner(ledger=object(), provider_manager=MissingLlamaCppProvider())

    result = runner._execute_exact_prompt(
        "JSON prompt",
        {"selected_model": "qwen", "model_family": "qwen", "lane": "reasoning_analysis"},
        operation_type="formulate_hypothesis",
    )

    assert result["executed"] is True
    assert result["model_id"] == "qwen-test"
    assert result["execution_adapter"] == "active_cognitive_loop.exact_prompt.venv_subprocess"


def test_unavailable_operation_result_is_not_accepted_as_concept_progress():
    request, packet = _request_and_packet("formulate_hypothesis")
    raw = {
        "operation_result_type": "formulate_hypothesis_unavailable",
        "interpretation": "Local model execution did not complete: ModuleNotFoundError: No module named 'llama_cpp'",
        "supporting_evidence_refs": ["repo_runtime"],
        "evidence_refs": ["repo_runtime"],
        "assumptions": ["No concept progress should be accepted without model output or evidence."],
        "expected_observations": ["A later successful local execution should produce a typed result."],
        "uncertainty": "local_model_execution_exception",
        "recommended_state_transition": "declare_insufficient_evidence",
    }

    result = validate_model_result(request, packet, raw)

    assert result.accepted is False
    assert "local_model_execution_blocked" in result.rejection_reasons


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
