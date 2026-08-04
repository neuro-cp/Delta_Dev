from dataclasses import replace
from types import SimpleNamespace

from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    compile_chat_clarification_request,
    handle_conversational_message,
    save_runtime_state,
    start_or_restore_runtime,
)
from orchestration.runtime.interactive_cognition import (
    CoordinationMetadata,
    CoordinationState,
    arbitrate_attention,
    build_workspace_snapshot,
    load_coordination_state,
    clear_preemption,
    record_shadow_decision,
    request_preemption,
    save_coordination_state,
    set_candidate_disposition,
    stage_attention_decision,
    surface_candidate_once,
)
from orchestration.runtime.provisional_semantic_consolidation import (
    ClaimVersion,
    ProvisionalSemanticGraphState,
    SemanticEdge,
    create_consolidation_cohort,
    load_graph,
    save_graph,
    seal_cohort_packet_once,
)


GOAL = "Your new goal is to study how a rain barrel collects water. Use local cognition and existing local evidence first."


def _goal_state(tmp_path):
    initial = start_or_restore_runtime(tmp_path)
    return handle_conversational_message(initial, GOAL, runtime_root=tmp_path, run_background_cycle=False).state


def test_workspace_snapshot_is_deterministic_and_does_not_mutate_canonical_state(tmp_path):
    state = _goal_state(tmp_path)
    before = state.as_record()

    first = build_workspace_snapshot(state, foreground_message="What is the current focus?")
    second = build_workspace_snapshot(state, foreground_message="What is the current focus?")

    assert state.as_record() == before
    assert first.snapshot_digest == second.snapshot_digest
    assert first.as_record() == second.as_record()
    assert any(item.thread_kind == "foreground_conversation" for item in first.threads)
    assert any(item.thread_kind == "active_goal" for item in first.threads)


def test_thread_identity_is_derived_and_coordination_persists_only_metadata(tmp_path):
    state = _goal_state(tmp_path)
    original = build_workspace_snapshot(state)
    goal_thread = next(item for item in original.threads if item.thread_kind == "active_goal")
    coordination = CoordinationState(
        runtime_id=state.runtime_id,
        entries=(CoordinationMetadata(thread_id=goal_thread.thread_id, starvation_count=4, preemption_requested=True),),
    )
    save_coordination_state(tmp_path, coordination)
    restored = load_coordination_state(tmp_path, runtime_id=state.runtime_id)
    rebuilt = build_workspace_snapshot(state, coordination=restored)
    rebuilt_goal = next(item for item in rebuilt.threads if item.thread_kind == "active_goal")

    assert rebuilt_goal.thread_id == goal_thread.thread_id
    assert rebuilt_goal.attention.starvation == 4
    assert restored.entries[0].preemption_requested is True
    assert "operator_wording" not in restored.as_record()["entries"][0]


def test_shadow_arbiter_always_prefers_foreground_over_active_goal(tmp_path):
    state = _goal_state(tmp_path)
    snapshot = build_workspace_snapshot(state, foreground_message="What color is the sky?", foreground_turn_id="operator-turn-1")

    decision = arbitrate_attention(snapshot)

    assert decision.shadow_mode is True
    assert decision.selected_posture == "answer_operator"
    assert decision.target_owner == "conversational_runtime"
    assert "unanswered_foreground_operator_message" in decision.reason_codes


def test_terminal_gap_pressure_selects_one_bounded_recovery_posture(tmp_path):
    state = replace(_goal_state(tmp_path), lifecycle_state="paused_budget")
    objective = state.active_objective
    assert objective is not None
    controller = {
        "controller_id": "teaching-controller-gap",
        "objective_id": objective.objective_id,
        "plan": objective.provenance["teaching_plan"],
        "teaching_cursor": 3,
        "developmental_pressures": (
            {
                "pressure_id": "terminal-gap-pressure",
                "pressure_type": "unresolved_curriculum_gap",
                "source_followup_id": "terminal-gap-followup",
                "source_terminal_report_key": "terminal-report-key",
                "source_gap": "address Connections",
                "reason": "A real terminal gap has one safe bounded recovery action.",
                "recommended_action": "perform_one_gap_recovery_study",
                "requires_operator": False,
                "priority": 4,
            },
        ),
    }

    snapshot = build_workspace_snapshot(state, developmental_controller=controller)
    decision = arbitrate_attention(snapshot)
    pressure = next(item for item in snapshot.threads if item.thread_kind == "developmental_pressure")

    assert pressure.authority_requirement == "standing_authority_for_one_bounded_gap_recovery"
    assert pressure.source_record_ids[-1] == "terminal-report-key"
    assert decision.selected_posture == "perform_one_gap_recovery_study"
    assert decision.target_owner == "continuous_runtime_controller"


def test_shadow_decision_journal_is_bounded_and_deduplicated(tmp_path):
    state = _goal_state(tmp_path)
    coordination = CoordinationState(runtime_id=state.runtime_id)
    initial = build_workspace_snapshot(state, coordination=coordination, foreground_message="What is the current focus?")
    decision = arbitrate_attention(initial)

    recorded = record_shadow_decision(coordination, decision, limit=2)
    duplicate = record_shadow_decision(recorded, decision, limit=2)
    rebuilt = build_workspace_snapshot(state, coordination=duplicate, foreground_message="What is the current focus?")
    active = stage_attention_decision(decision, stage="active_gate")

    assert len(recorded.decision_history) == 1
    assert duplicate.decision_history == recorded.decision_history
    assert duplicate.decision_history[0]["selected_posture"] == "answer_operator"
    assert rebuilt.snapshot_digest == initial.snapshot_digest
    assert active.decision_stage == "active_gate"
    assert active.shadow_mode is False


def test_preemption_metadata_is_explicit_and_does_not_change_thread_ownership(tmp_path):
    state = _goal_state(tmp_path)
    snapshot = build_workspace_snapshot(state)
    goal = next(item for item in snapshot.threads if item.thread_kind == "active_goal")
    coordination = request_preemption(CoordinationState(runtime_id=state.runtime_id), thread_id=goal.thread_id)

    assert coordination.entries[0].thread_id == goal.thread_id
    assert coordination.entries[0].preemption_requested is True
    assert state.active_objective.objective_id in goal.source_record_ids

    cleared = clear_preemption(coordination, thread_id=goal.thread_id)
    assert cleared.entries[0].preemption_requested is False


def test_restart_restores_preemption_metadata_without_creating_a_second_thread(tmp_path):
    state = _goal_state(tmp_path)
    goal = next(item for item in build_workspace_snapshot(state).threads if item.thread_kind == "active_goal")
    coordination = request_preemption(CoordinationState(runtime_id=state.runtime_id), thread_id=goal.thread_id)
    save_coordination_state(tmp_path, coordination)

    restored = load_coordination_state(tmp_path, runtime_id=state.runtime_id)
    rebuilt = build_workspace_snapshot(state, coordination=restored)
    restored_goal = next(item for item in rebuilt.threads if item.thread_kind == "active_goal")

    assert restored_goal.thread_id == goal.thread_id
    assert len([item for item in rebuilt.threads if item.thread_kind == "active_goal"]) == 1
    assert restored.entries[0].preemption_requested is True


def test_rendered_authority_request_owns_idle_attention_without_replacing_goal(tmp_path):
    state = _goal_state(tmp_path)
    request = ChatAddressableRequest(
        request_id="budget-request-1",
        request_type="knowledge_model_budget_increase",
        objective_id=state.active_objective.objective_id,
        goal_label="rain barrel",
        prompt_text="Increase the local-model budget for this goal?",
        authority_impact="goal_scoped_budget_change",
        rendered_turn_id="assistant-turn-7",
        render_sequence=7,
    )
    state = replace(state, pending_chat_requests=(request,))

    decision = arbitrate_attention(build_workspace_snapshot(state))

    assert decision.selected_posture == "ask_operator"
    assert decision.target_owner == "chat_addressable_request"
    assert any(item.thread_kind == "active_goal" for item in build_workspace_snapshot(state).threads)


def test_question_candidate_is_a_stable_view_of_the_existing_request_owner(tmp_path):
    state = _goal_state(tmp_path)
    request = ChatAddressableRequest(
        request_id="local-consent-1",
        request_type="local_model_execution",
        objective_id=state.active_objective.objective_id,
        goal_label="rain barrel",
        prompt_text="May I ask the local model about the collection mechanism?",
        rendered_turn_id="assistant-turn-9",
        render_sequence=9,
        accepted_response_types=("approved", "denied"),
    )
    state = replace(state, pending_chat_requests=(request,))

    first = build_workspace_snapshot(state)
    second = build_workspace_snapshot(state)
    candidate = first.question_candidates[0]

    assert first.question_candidates == second.question_candidates
    assert candidate.question_class == "progress-choice"
    assert candidate.canonical_owner == "chat_addressable_request"
    assert candidate.source_record_ids == (request.request_id,)
    assert candidate.operator_visible_wording == request.prompt_text
    assert candidate.surface_in_chat is True
    assert candidate.safe_independent_work_may_continue is True


def test_graph_claims_are_references_not_authoritative_thread_payloads(tmp_path):
    state = _goal_state(tmp_path)
    graph = ProvisionalSemanticGraphState(
        graph_id="graph-1",
        claim_versions=(
            ClaimVersion(
                claim_version_id="claim-version-1",
                claim_id="claim-1",
                version_index=1,
                exact_text="Rain barrels collect roof runoff.",
                epistemic_state="pending_consolidation",
                rationale_refs=("rationale-1",),
                assumption_refs=(),
                uncertainty_refs=(),
                source_experience_refs=("experience-1",),
                semantic_fingerprint="sha256:test",
                created_at="2026-08-01T00:00:00+00:00",
            ),
        ),
    )

    snapshot = build_workspace_snapshot(state, graph=graph)
    claim_thread = next(item for item in snapshot.threads if item.source_record_ids == ("claim-version-1",))

    assert claim_thread.canonical_owner == "provisional_semantic_graph"
    assert claim_thread.epistemic_status == "pending_consolidation"
    assert claim_thread.semantic_refs == ("experience-1",)
    assert claim_thread.focus == "Rain barrels collect roof runoff."


def test_near_association_requires_an_explicit_graph_dependency_not_word_overlap(tmp_path):
    state = _goal_state(tmp_path)
    graph = ProvisionalSemanticGraphState(
        graph_id="association-graph",
        claim_versions=(
            ClaimVersion("claim-version-a", "claim-a", 1, "Capture rooftop runoff.", "provisional", (), (), (), (), "sha256:a", "2026-08-01T00:00:00+00:00"),
            ClaimVersion("claim-version-b", "claim-b", 1, "Route the overflow safely.", "provisional", (), (), (), (), "sha256:b", "2026-08-01T00:00:00+00:00"),
        ),
        edges=(SemanticEdge("dependency-edge", "depends_on", "claim-version-b", "claim-version-a", "2026-08-01T00:00:00+00:00"),),
    )

    snapshot = build_workspace_snapshot(state, graph=graph)

    assert len(snapshot.association_candidates) == 1
    association = snapshot.association_candidates[0]
    assert association.association_type == "explicit_dependency"
    assert association.relation_path == ("dependency-edge",)
    assert association.surface_worthy is False
    assert association.uncertainty.startswith("The dependency establishes")
    assert any(item.thread_kind == "near_association" for item in snapshot.threads)


def test_curiosity_revisit_is_generated_only_for_actual_epistemic_instability(tmp_path):
    state = _goal_state(tmp_path)
    graph = ProvisionalSemanticGraphState(
        graph_id="curiosity-graph",
        claim_versions=(
            ClaimVersion("stable-version", "stable-claim", 1, "A settled provisional claim.", "pending_consolidation", (), (), (), (), "sha256:stable", "2026-08-01T00:00:00+00:00"),
            ClaimVersion("unstable-version", "unstable-claim", 1, "A claim with unresolved support.", "unstable", (), (), (), (), "sha256:unstable", "2026-08-01T00:00:00+00:00"),
        ),
    )

    snapshot = build_workspace_snapshot(state, graph=graph)

    assert len(snapshot.curiosity_candidates) == 1
    candidate = snapshot.curiosity_candidates[0]
    assert candidate.trigger == "epistemic_instability"
    assert candidate.source_record_ids == ("unstable-version",)
    assert candidate.surface_worthy is False
    assert any(item.thread_kind == "curiosity_candidate" for item in snapshot.threads)


def test_candidate_disposition_persists_without_promoting_a_derived_candidate(tmp_path):
    state = _goal_state(tmp_path)
    graph = ProvisionalSemanticGraphState(
        graph_id="candidate-disposition-graph",
        claim_versions=(
            ClaimVersion("unstable-version", "unstable-claim", 1, "A claim with unresolved support.", "unstable", (), (), (), (), "sha256:unstable", "2026-08-01T00:00:00+00:00"),
        ),
    )
    initial = build_workspace_snapshot(state, graph=graph)
    candidate = initial.curiosity_candidates[0]
    coordination = set_candidate_disposition(
        CoordinationState(runtime_id=state.runtime_id),
        candidate_id=candidate.candidate_id,
        candidate_kind="curiosity_candidate",
        disposition="deferred",
        source_record_ids=candidate.source_record_ids,
    )
    save_coordination_state(tmp_path, coordination)

    restored = load_coordination_state(tmp_path, runtime_id=state.runtime_id)
    rebuilt = build_workspace_snapshot(state, graph=graph, coordination=restored)
    rebuilt_candidate = rebuilt.curiosity_candidates[0]
    rebuilt_thread = next(item for item in rebuilt.threads if item.originating_reference == candidate.candidate_id)

    assert rebuilt_candidate.state == "deferred"
    assert rebuilt_thread.status == "deferred"
    assert restored.candidate_dispositions[0].source_record_ids == candidate.source_record_ids
    assert rebuilt_candidate.canonical_owner == "provisional_semantic_graph"


def test_association_disposition_changes_only_its_derived_thread(tmp_path):
    state = _goal_state(tmp_path)
    graph = ProvisionalSemanticGraphState(
        graph_id="association-disposition-graph",
        claim_versions=(
            ClaimVersion("claim-version-a", "claim-a", 1, "Capture rooftop runoff.", "provisional", (), (), (), (), "sha256:a", "2026-08-01T00:00:00+00:00"),
            ClaimVersion("claim-version-b", "claim-b", 1, "Route overflow safely.", "provisional", (), (), (), (), "sha256:b", "2026-08-01T00:00:00+00:00"),
        ),
        edges=(SemanticEdge("dependency-edge", "depends_on", "claim-version-b", "claim-version-a", "2026-08-01T00:00:00+00:00"),),
    )
    first = build_workspace_snapshot(state, graph=graph)
    candidate = first.association_candidates[0]
    coordination = set_candidate_disposition(
        CoordinationState(runtime_id=state.runtime_id),
        candidate_id=candidate.candidate_id,
        candidate_kind="near_association",
        disposition="deferred",
        source_record_ids=candidate.provenance_refs,
    )

    restored = build_workspace_snapshot(state, graph=graph, coordination=coordination)
    thread = next(item for item in restored.threads if item.originating_reference == candidate.candidate_id)

    assert restored.association_candidates[0].state == "deferred"
    assert thread.status == "deferred"
    assert graph.edges[0].edge_id == "dependency-edge"


def test_candidate_disposition_enforces_a_non_resurrectable_lifecycle():
    initial = CoordinationState(runtime_id="candidate-lifecycle-runtime")
    surfaced = set_candidate_disposition(
        initial,
        candidate_id="association-candidate-1",
        candidate_kind="near_association",
        disposition="surfaced",
        source_record_ids=("edge-1",),
    )
    resolved = set_candidate_disposition(
        surfaced,
        candidate_id="association-candidate-1",
        candidate_kind="near_association",
        disposition="resolved",
        source_record_ids=("edge-1",),
    )

    try:
        set_candidate_disposition(
            resolved,
            candidate_id="association-candidate-1",
            candidate_kind="near_association",
            disposition="queued",
            source_record_ids=("edge-1",),
        )
    except ValueError as exc:
        assert "cannot transition" in str(exc)
    else:
        raise AssertionError("a resolved candidate must not re-enter the attention queue")


def test_explicit_dependency_association_can_surface_once_without_graph_mutation(tmp_path):
    state = _goal_state(tmp_path)
    state = replace(state, active_objective=None, lifecycle_state="ready")
    graph = ProvisionalSemanticGraphState(
        graph_id="surface-association-graph",
        claim_versions=(
            ClaimVersion("claim-version-a", "claim-a", 1, "Capture rooftop runoff.", "validated", (), (), (), (), "sha256:a", "2026-08-01T00:00:00+00:00"),
            ClaimVersion("claim-version-b", "claim-b", 1, "Route overflow safely.", "validated", (), (), (), (), "sha256:b", "2026-08-01T00:00:00+00:00"),
        ),
        edges=(SemanticEdge("dependency-edge", "depends_on", "claim-version-b", "claim-version-a", "2026-08-01T00:00:00+00:00"),),
    )
    first = build_workspace_snapshot(state, graph=graph)
    candidate = first.association_candidates[0]
    decision = arbitrate_attention(first)

    surfaced = surface_candidate_once(
        CoordinationState(runtime_id=state.runtime_id),
        candidate_id=candidate.candidate_id,
        candidate_kind="near_association",
        source_record_ids=candidate.provenance_refs,
    )
    repeated = surface_candidate_once(
        surfaced,
        candidate_id=candidate.candidate_id,
        candidate_kind="near_association",
        source_record_ids=candidate.provenance_refs,
    )
    rebuilt = build_workspace_snapshot(state, graph=graph, coordination=surfaced)

    assert decision.selected_posture == "explore_near_association"
    assert len(surfaced.candidate_dispositions) == 1
    assert repeated == surfaced
    assert rebuilt.association_candidates[0].state == "surfaced"
    assert graph.claim_versions[0].epistemic_state == "validated"


def test_curiosity_can_receive_one_idle_inspection_after_the_review_thread_is_suppressed(tmp_path):
    state = _goal_state(tmp_path)
    state = replace(state, active_objective=None, lifecycle_state="ready")
    graph = ProvisionalSemanticGraphState(
        graph_id="curiosity-idle-graph",
        claim_versions=(
            ClaimVersion("unstable-version", "unstable-claim", 1, "A claim with unresolved support.", "unstable", (), (), (), (), "sha256:unstable", "2026-08-01T00:00:00+00:00"),
        ),
    )
    first = build_workspace_snapshot(state, graph=graph)
    review_thread = next(item for item in first.threads if item.thread_kind == "contradiction_review")
    coordination = CoordinationState(
        runtime_id=state.runtime_id,
        entries=(CoordinationMetadata(thread_id=review_thread.thread_id, suppressed=True),),
    )
    ready = build_workspace_snapshot(state, graph=graph, coordination=coordination)
    candidate = ready.curiosity_candidates[0]
    decision = arbitrate_attention(ready)
    surfaced = surface_candidate_once(
        coordination,
        candidate_id=candidate.candidate_id,
        candidate_kind="curiosity_candidate",
        source_record_ids=candidate.source_record_ids,
    )
    rebuilt = build_workspace_snapshot(state, graph=graph, coordination=surfaced)

    assert decision.selected_posture == "inspect_curiosity_candidate"
    assert rebuilt.curiosity_candidates[0].state == "surfaced"
    assert graph.claim_versions[0].epistemic_state == "unstable"


def test_mixed_cognitive_state_restores_twice_without_duplicate_requests_or_candidates(tmp_path):
    state = _goal_state(tmp_path)
    question = ChatAddressableRequest(
        request_id="mixed-state-question",
        request_type="reference_clarification",
        objective_id=state.active_objective.objective_id,
        goal_label="Reference clarification",
        prompt_text="Which prior subject should that refer to?",
        created_turn_id="mixed-state-user-turn",
        rendered_turn_id="mixed-state-assistant-turn",
        created_sequence=3,
        render_sequence=4,
        accepted_response_types=("clarification",),
    )
    state = replace(state, lifecycle_state="paused", pending_chat_requests=(question,))
    save_runtime_state(tmp_path, state)
    graph = ProvisionalSemanticGraphState(
        graph_id="mixed-state-graph",
        claim_versions=(
            ClaimVersion("dependency-source", "claim-a", 1, "Capture rooftop runoff.", "validated", (), (), (), (), "sha256:a", "2026-08-01T00:00:00+00:00"),
            ClaimVersion("dependency-target", "claim-b", 1, "Route overflow safely.", "validated", (), (), (), (), "sha256:b", "2026-08-01T00:00:00+00:00"),
            ClaimVersion("unstable-version", "unstable-claim", 1, "A claim with unresolved support.", "unstable", (), (), (), (), "sha256:unstable", "2026-08-01T00:00:00+00:00"),
        ),
        edges=(SemanticEdge("dependency-edge", "depends_on", "dependency-target", "dependency-source", "2026-08-01T00:00:00+00:00"),),
    )
    save_graph(tmp_path, graph)
    first = build_workspace_snapshot(state, graph=graph)
    association = first.association_candidates[0]
    curiosity = first.curiosity_candidates[0]
    coordination = surface_candidate_once(
        CoordinationState(runtime_id=state.runtime_id),
        candidate_id=association.candidate_id,
        candidate_kind="near_association",
        source_record_ids=association.provenance_refs,
    )
    coordination = set_candidate_disposition(
        coordination,
        candidate_id=curiosity.candidate_id,
        candidate_kind="curiosity_candidate",
        disposition="deferred",
        source_record_ids=curiosity.source_record_ids,
    )
    save_coordination_state(tmp_path, coordination)

    restored_runtime_one = start_or_restore_runtime(tmp_path)
    restored_graph_one = load_graph(tmp_path)
    restored_coordination_one = load_coordination_state(tmp_path, runtime_id=restored_runtime_one.runtime_id)
    restored_runtime_two = start_or_restore_runtime(tmp_path)
    restored_graph_two = load_graph(tmp_path)
    restored_coordination_two = load_coordination_state(tmp_path, runtime_id=restored_runtime_two.runtime_id)
    rebuilt = build_workspace_snapshot(restored_runtime_two, graph=restored_graph_two, coordination=restored_coordination_two)

    assert restored_runtime_one.lifecycle_state == restored_runtime_two.lifecycle_state == "paused"
    assert [item.request_id for item in restored_runtime_two.pending_chat_requests] == ["mixed-state-question"]
    assert restored_graph_one.as_record() == restored_graph_two.as_record()
    assert len(restored_coordination_one.candidate_dispositions) == len(restored_coordination_two.candidate_dispositions) == 2
    assert rebuilt.association_candidates[0].state == "surfaced"
    assert rebuilt.curiosity_candidates[0].state == "deferred"
    assert len(rebuilt.question_candidates) == 1


def test_background_arbitration_records_competing_thread_reasons_without_mutation(tmp_path):
    state = _goal_state(tmp_path)
    graph = ProvisionalSemanticGraphState(
        graph_id="arbitration-graph",
        claim_versions=(
            ClaimVersion("source-version", "source-claim", 1, "Capture rooftop runoff.", "validated", (), (), (), (), "sha256:source", "2026-08-01T00:00:00+00:00"),
            ClaimVersion("target-version", "target-claim", 1, "Route overflow safely.", "validated", (), (), (), (), "sha256:target", "2026-08-01T00:00:00+00:00"),
            ClaimVersion("unstable-version", "unstable-claim", 1, "A claim with unresolved support.", "unstable", (), (), (), (), "sha256:unstable", "2026-08-01T00:00:00+00:00"),
        ),
        edges=(SemanticEdge("dependency-edge", "depends_on", "target-version", "source-version", "2026-08-01T00:00:00+00:00"),),
    )
    before = graph.as_record()
    snapshot = build_workspace_snapshot(
        state,
        graph=graph,
        runtime_health=({"health_id": "health-1", "severity": "critical", "summary": "A bounded health observation."},),
    )

    decision = arbitrate_attention(snapshot)
    persisted = record_shadow_decision(CoordinationState(runtime_id=state.runtime_id), decision)

    assert decision.target_owner == "runtime_health"
    assert decision.selected_posture == "report_current_focus"
    assert {item["posture"] for item in decision.rejected_competitors} >= {"continue_active_goal", "surface_contradiction"}
    assert persisted.decision_history[0]["reason_codes"] == list(decision.reason_codes)
    assert graph.as_record() == before


def test_selected_consolidation_cluster_seals_one_packet_and_uses_graph_as_its_cursor(tmp_path):
    state = _goal_state(tmp_path)
    state = replace(state, active_objective=None, lifecycle_state="ready")
    graph = ProvisionalSemanticGraphState(
        graph_id="consolidation-step-graph",
        claim_versions=(
            ClaimVersion("claim-version-1", "claim-1", 1, "Rain barrels collect rooftop runoff.", "pending_consolidation", (), (), (), (), "sha256:claim-1", "2026-08-01T00:00:00+00:00"),
        ),
    )
    graph, cohort = create_consolidation_cohort(graph, trigger="idle_attention")
    decision = arbitrate_attention(build_workspace_snapshot(state, graph=graph))
    sealed_graph, packet, outcome = seal_cohort_packet_once(graph, cohort)
    repeated_graph, repeated_packet, repeated_outcome = seal_cohort_packet_once(sealed_graph, cohort)
    post_seal = build_workspace_snapshot(state, graph=sealed_graph)

    assert decision.selected_posture == "perform_one_consolidation_step"
    assert outcome == "sealed"
    assert packet is not None
    assert len(sealed_graph.packets) == 1
    assert repeated_outcome == "already_sealed"
    assert repeated_packet == packet
    assert repeated_graph == sealed_graph
    cohort_thread = next(item for item in post_seal.threads if item.originating_reference == cohort.cohort_id)
    assert cohort_thread.status == "awaiting_administrative_review"


def test_clarification_compiler_creates_one_typed_request_without_a_second_question_owner(tmp_path):
    state = _goal_state(tmp_path)

    request = compile_chat_clarification_request(
        state,
        pressure="missing_evidence",
        prompt_text="Which household load should this estimate prioritize?",
        source_record_ids=(state.active_objective.objective_id,),
        created_turn_id="operator-turn-7",
        created_sequence=7,
    )

    assert request.request_type == "interactive_clarification"
    assert request.accepted_response_types == ("clarification",)
    assert request.baseline_metrics["clarification_pressure"] == "missing_evidence"
    assert request.baseline_metrics["source_record_ids"] == (state.active_objective.objective_id,)
    assert request.request_id not in {item.request_id for item in state.pending_chat_requests}


def test_missing_evidence_and_contradiction_producers_require_existing_canonical_evidence(tmp_path):
    import orchestration.runtime.interactive_cognition as interactive

    episode = SimpleNamespace(
        episode_id="episode-missing-evidence",
        operation_results=(
            SimpleNamespace(
                operation_id="operation-evidence-gap",
                operation_result_type="declare_insufficient_evidence_result",
                interpretation="The current local record does not contain the installation history.",
                recommended_action="the installation history for this system",
                next_evidence_need="",
            ),
        ),
    )
    pressure = interactive._derive_cognitive_pressure_candidates(episode)
    state = _goal_state(tmp_path)
    graph = ProvisionalSemanticGraphState(
        graph_id="contradiction-producer-graph",
        claim_versions=(
            ClaimVersion("contradicted-version", "claim-a", 1, "The installation has no drainage path.", "locally_contradicted", (), (), (), (), "sha256:contradicted", "2026-08-01T00:00:00+00:00"),
        ),
    )
    snapshot = build_workspace_snapshot(state, graph=graph)

    assert len(pressure) == 1
    assert pressure[0].trigger == "missing_evidence"
    assert pressure[0].safe_next_step == "the installation history for this system"
    contradiction = next(item for item in snapshot.curiosity_candidates if item.trigger == "contradiction")
    assert contradiction.source_record_ids == ("contradicted-version",)
