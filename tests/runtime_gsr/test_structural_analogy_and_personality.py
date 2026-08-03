from dataclasses import replace

import pytest

from orchestration.runtime.approved_structural_analogy_exploration import _parse as parse_structural_analogy_output, execute_once, load_explorations, queue_exploration
from orchestration.runtime.approved_curiosity_inquiry import execute_once as execute_curiosity_once, queue_inquiry
from orchestration.runtime.curiosity_pressure import make_pressure, score_question_value, should_surface_question
from orchestration.runtime.governed_personality_profile import (
    approve_and_activate,
    load_state,
    propose_profile,
    record_relationship_convention,
    rollback_profile,
    save_state,
    shape_presentation,
    self_model_projection,
)
from orchestration.runtime.provisional_semantic_consolidation import (
    ClaimVersion,
    ProvisionalSemanticGraphState,
    record_provisional_functional_relation,
    load_graph,
    save_graph,
)
from orchestration.runtime.structural_analogy import describe_structural_analogy_candidate, derive_structural_analogies, project_structural_patterns
from orchestration.runtime.interactive_cognition import CoordinationState, build_workspace_snapshot, set_candidate_disposition, surface_candidate_once
from orchestration.runtime.conversational_runtime_operation import compile_chat_clarification_request, start_or_restore_runtime


def _relation_graph():
    graph = ProvisionalSemanticGraphState(
        graph_id="analogy-graph",
        claim_versions=(
            ClaimVersion("rain-a", "rain-a", 1, "A downspout transfers roof runoff to a rain barrel.", "pending_consolidation", (), (), (), (), "sha256:a", "2026-01-01T00:00:00+00:00"),
            ClaimVersion("rain-b", "rain-b", 1, "A rain barrel is limited by capacity and discharges overflow.", "pending_consolidation", (), (), (), (), "sha256:b", "2026-01-01T00:00:00+00:00"),
            ClaimVersion("memory-a", "memory-a", 1, "A queue transfers messages to a bounded memory buffer.", "pending_consolidation", (), (), (), (), "sha256:c", "2026-01-01T00:00:00+00:00"),
            ClaimVersion("memory-b", "memory-b", 1, "A bounded buffer activates backpressure and discharges work.", "pending_consolidation", (), (), (), (), "sha256:d", "2026-01-01T00:00:00+00:00"),
        ),
    )
    records = (
        ("transfers_through", "rain-a", "rain-b", "source-rain-a"),
        ("limited_by_capacity", "rain-b", "rain-a", "source-rain-b"),
        ("transfers_through", "memory-a", "memory-b", "source-memory-a"),
        ("limited_by_capacity", "memory-b", "memory-a", "source-memory-b"),
    )
    for relation_type, source, target, provenance in records:
        graph, _ = record_provisional_functional_relation(graph, relation_type=relation_type, source_ref=source, target_ref=target, provenance_refs=(provenance,), confidence=0.6)
    return graph


def test_functional_relations_project_patterns_and_reject_unknown_relation():
    graph = _relation_graph()
    patterns = project_structural_patterns(graph.relations)
    assert len(patterns) == 2
    assert all(len(item.relation_ids) == 2 for item in patterns)
    with pytest.raises(ValueError, match="unsupported_functional_relation"):
        record_provisional_functional_relation(graph, relation_type="free_text_relation", source_ref="rain-a", target_ref="rain-b", provenance_refs=("source",))


def test_structural_analogy_requires_multiple_matches_and_a_boundary():
    graph = _relation_graph()
    groups = (tuple(graph.relations[:2]), tuple(graph.relations[2:]))
    candidates = derive_structural_analogies(groups)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert set(candidate.matched_relation_types) == {"limited_by_capacity", "transfers_through"}
    assert candidate.limitation
    assert candidate.possible_next_question
    assert derive_structural_analogies(((graph.relations[0],), (graph.relations[2],))) == ()


def test_structural_analogy_summary_keeps_both_domains_and_boundary_visible():
    graph = _relation_graph()
    candidate = derive_structural_analogies((tuple(graph.relations[:2]), tuple(graph.relations[2:])))[0]
    summary = describe_structural_analogy_candidate(
        candidate,
        record_labels={item.claim_version_id: item.exact_text for item in graph.claim_versions},
    )
    assert "A downspout transfers roof runoff" in summary
    assert "bounded memory buffer" in summary
    assert "Matched functional relations" in summary
    assert "Where it may fail" in summary
    assert "Bounded exploration question" in summary


def test_structural_analogy_uses_the_canonical_clarification_request_contract(tmp_path):
    runtime = start_or_restore_runtime(tmp_path)
    request = compile_chat_clarification_request(
        runtime,
        pressure="structural_analogy_boundary",
        prompt_text="Compare two provisional functional patterns?",
        source_record_ids=("source-a", "source-b"),
    )
    assert request.baseline_metrics["clarification_pressure"] == "structural_analogy_boundary"


def test_structural_analogy_rejects_a_shared_risk_mislabeled_as_a_failure_boundary():
    raw = (
        '{"shared_structure":"Both systems buffer incoming load.",'
        '"source_domain_interpretation":"One system stores a load.",'
        '"target_domain_interpretation":"The other system stores a load.",'
        '"possible_implication":"Capacity can expose pressure.",'
        '"failure_boundary":"Both systems fail when capacity is exceeded.",'
        '"uncertainty":"The thresholds are not recorded.",'
        '"evidence_still_missing":"No measured threshold is available.",'
        '"next_question":"What threshold applies?"}'
    )
    assert parse_structural_analogy_output(raw) is None


def test_structural_analogy_is_a_disposition_backed_workspace_view(tmp_path):
    graph = _relation_graph()
    before = graph.as_record()
    runtime = start_or_restore_runtime(tmp_path)
    first = build_workspace_snapshot(runtime, graph=graph, coordination=CoordinationState(runtime_id=runtime.runtime_id))
    candidate = first.analogy_candidates[0]
    state = set_candidate_disposition(CoordinationState(runtime_id=runtime.runtime_id), candidate_id=candidate.candidate_id, candidate_kind="far_analogy", disposition="surfaced", source_record_ids=candidate.provenance_refs)
    rebuilt = build_workspace_snapshot(runtime, graph=graph, coordination=state)
    assert rebuilt.analogy_candidates[0].state == "surfaced"
    assert graph.as_record() == before


def test_approved_analogy_exploration_uses_one_shared_ledger_request_and_stays_provisional(tmp_path):
    graph = _relation_graph()
    queued = queue_exploration(
        tmp_path, graph, candidate_id="analogy-1", source_pattern_id="source-pattern", target_pattern_id="target-pattern",
        source_record_ids=("rain-a", "rain-b"), target_record_ids=("memory-a", "memory-b"),
        relation_ids=tuple(item.relation_id for item in graph.relations), approval_request_id="operator-approval",
    )
    answer = '{"shared_structure":"Both systems transfer incoming load into a bounded container before a capacity response.","source_domain_interpretation":"Rainwater enters a finite barrel.","target_domain_interpretation":"Messages enter a finite buffer.","possible_implication":"Capacity controls can make pressure visible before overflow.","failure_boundary":"Water flow and queue scheduling differ in physical mechanism.","uncertainty":"The source records do not establish an equivalent threshold policy.","evidence_still_missing":"The buffer release policy is not recorded.","next_question":"What threshold behavior does the buffer use?"}'
    completed, updated = execute_once(tmp_path, graph, queued, executor=lambda _q, _l: {"executed": True, "model_id": "fixture", "answer": answer})
    repeated, repeated_graph = execute_once(tmp_path, updated, completed, executor=lambda _q, _l: {"executed": True, "model_id": "fixture", "answer": answer})
    assert completed.lifecycle_state == "analogy_explored_pending_consolidation"
    assert repeated.lifecycle_state == completed.lifecycle_state
    assert repeated_graph.as_record() == updated.as_record()
    insight = next(item for item in updated.experiences if item.experience_id == completed.insight_experience_id)
    assert insight.metadata["epistemic_state"] == "pending_consolidation"


def test_analogy_restart_reuses_the_same_operation_request_and_insight(tmp_path):
    graph = _relation_graph()
    queued = queue_exploration(tmp_path, graph, candidate_id="analogy-restart", source_pattern_id="source", target_pattern_id="target", source_record_ids=("rain-a", "rain-b"), target_record_ids=("memory-a", "memory-b"), relation_ids=tuple(item.relation_id for item in graph.relations), approval_request_id="approval")
    answer = '{"shared_structure":"Both paths accumulate bounded load.","source_domain_interpretation":"Water accumulates in a barrel.","target_domain_interpretation":"Messages accumulate in a buffer.","possible_implication":"Capacity limits can require a release path.","failure_boundary":"The release mechanisms are not physically equivalent.","uncertainty":"The target threshold is not recorded.","evidence_still_missing":"No buffer policy is present.","next_question":"What release policy applies?"}'
    completed, graph = execute_once(tmp_path, graph, queued, executor=lambda _q, _l: {"executed": True, "model_id": "fixture", "answer": answer})
    save_graph(tmp_path, graph)
    restored = load_explorations(tmp_path)[0]
    repeated, restored_graph = execute_once(tmp_path, load_graph(tmp_path), restored, executor=lambda _q, _l: {"executed": True, "model_id": "fixture", "answer": answer})
    assert repeated.exploration_id == completed.exploration_id
    assert repeated.ledger_request_id == completed.ledger_request_id
    assert repeated.insight_experience_id == completed.insight_experience_id
    assert restored_graph.as_record() == graph.as_record()


def test_curiosity_value_suppresses_low_value_and_foreground_interruption():
    pressure = make_pressure(source_owner="graph", source_record_ids=("claim",), thread_id="thread", reason_code="missing_limiting_condition", uncertainty="A threshold is missing.", expected_information_gain=3, urgency=2, operator_relevance=3, safe_independent_work_may_continue=False)
    assert should_surface_question(pressure)
    assert score_question_value(pressure, foreground_active=True) < 0
    assert not should_surface_question(pressure, duplicate_risk=3, recent_question_frequency=2)


def test_source_backed_curiosity_pressure_keeps_one_disposition_kind_through_approval():
    state = CoordinationState(runtime_id="curiosity-runtime")
    surfaced = surface_candidate_once(
        state,
        candidate_id="missing-evidence-candidate",
        candidate_kind="cognitive_pressure",
        source_record_ids=("episode", "operation"),
    )
    accepted = set_candidate_disposition(
        surfaced,
        candidate_id="missing-evidence-candidate",
        candidate_kind="cognitive_pressure",
        disposition="accepted",
        source_record_ids=("episode", "operation"),
    )
    approved = set_candidate_disposition(
        accepted,
        candidate_id="missing-evidence-candidate",
        candidate_kind="cognitive_pressure",
        disposition="approved_for_bounded_exploration",
        source_record_ids=("episode", "operation"),
    )
    assert approved.candidate_dispositions[0].candidate_kind == "cognitive_pressure"


def test_approved_curiosity_inquiry_uses_one_ledger_call_and_stays_provisional(tmp_path):
    graph = _relation_graph()
    inquiry = queue_inquiry(
        tmp_path,
        graph,
        candidate_id="gap-1",
        source_record_ids=("rain-a",),
        approval_request_id="approval",
        proposed_action="inspect barrel inlet capacity",
        source_context="The active episode declared that barrel inlet capacity is missing.",
    )
    assert "barrel inlet capacity is missing" in inquiry.inquiry_question
    answer = '{"question_addressed":"Whether the recorded inlet can transfer runoff to the barrel.","evidence_considered":"The recorded inlet path and barrel claim.","bounded_answer":"The recorded inlet path transfers runoff to the barrel.","uncertainty":"The inlet diameter is not recorded.","evidence_still_missing":"No local flow measurement is available.","next_question":"What inlet diameter is installed?"}'
    completed, updated = execute_curiosity_once(tmp_path, graph, inquiry, executor=lambda _q, _l: {"executed": True, "model_id": "fixture", "answer": answer})
    repeated, repeated_graph = execute_curiosity_once(tmp_path, updated, completed, executor=lambda _q, _l: {"executed": True, "model_id": "fixture", "answer": answer})
    assert completed.lifecycle_state == "curiosity_inquiry_pending_consolidation"
    assert repeated_graph.as_record() == updated.as_record()


def test_personality_is_operator_governed_presentation_only_and_restart_safe(tmp_path):
    state = load_state(tmp_path)
    proposed = propose_profile(state, traits={"directness": 3, "formality": 0, "uncertainty_expression_style": "plain"}, proposer_role="general_user", rationale="A proposal only.")
    version = proposed.versions[-1]
    with pytest.raises(PermissionError):
        approve_and_activate(proposed, profile_version_id=version.profile_version_id, operator_id="", approval_ref="")
    active = approve_and_activate(proposed, profile_version_id=version.profile_version_id, operator_id="operator", approval_ref="approval-1")
    active = record_relationship_convention(active, key="technical_detail", value="concise", operator_id="operator", approval_ref="approval-2")
    text = "The claim remains provisional; local evidence is incomplete."
    assert shape_presentation(text, active).endswith(text)
    save_state(tmp_path, active)
    restored = load_state(tmp_path)
    assert restored.active_profile_version_id == version.profile_version_id
    assert self_model_projection(restored)["authority_boundary"] == "presentation_only_operator_approved"
    rolled = rollback_profile(restored, target_profile_version_id=version.profile_version_id, operator_id="operator", approval_ref="rollback-1")
    assert rolled.active_profile_version_id == version.profile_version_id
