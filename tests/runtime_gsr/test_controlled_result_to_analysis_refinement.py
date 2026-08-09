from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import compile_controlled_fixture_analysis_refinement
from orchestration.runtime.provisional_semantic_consolidation import load_graph


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."


def _send(state, text, tmp_path):
    return handle_conversational_message(state, text, runtime_root=tmp_path, run_background_cycle=False)


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _closed_loop_state(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    started = _send(state, GOAL, tmp_path)
    framed = _send(started.state, FINANCE, tmp_path)
    refined = _send(framed.state, "Assume losing more than 10% over six months is unacceptable.", tmp_path)
    granted = _send(refined.state, "Yes, but only a local fixture.", tmp_path)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", tmp_path)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", tmp_path)
    return _send(authority.state, "Yes, record this bounded plan.", tmp_path)


def test_fixture_result_reuses_append_only_analysis_refinement_with_explicit_lineage(tmp_path):
    graph_before = load_graph(tmp_path)
    result = _closed_loop_state(tmp_path)
    analyses = _records(result.state, "evidence_bound_analyses")
    refinements = _records(result.state, "analysis_refinements")
    fixture = _records(result.state, "evidence_minimal_fixture_results")[0]

    assert len(analyses) == 1
    assert len(refinements) == 2
    original_refinement, controlled = refinements
    assert original_refinement["status"] == "provisional_refinement"
    assert controlled["status"] == "controlled_fixture_refinement"
    assert controlled["source_analysis_id"] == analyses[0]["analysis_id"]
    assert controlled["source_evidence_minimal_fixture_result_id"] == fixture["evidence_minimal_fixture_result_id"]
    assert controlled["source_evidence_analysis_revision_candidate_id"] == fixture["source_evidence_analysis_revision_candidate_id"]
    assert "-11.3%" in controlled["after_summary"]
    assert "live-data and correlation gap remains unresolved" in controlled["after_summary"].lower()
    assert "controlled fixture result" in result.reply.lower()
    assert "append-only refinement" in result.reply.lower()

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_fixture_result_cannot_append_refinement_when_it_claims_update_authority(tmp_path):
    result = _closed_loop_state(tmp_path)
    analysis = _records(result.state, "evidence_bound_analyses")[0]
    fixture = _records(result.state, "evidence_minimal_fixture_results")[0]
    request = _records(result.state, "evidence_requests")[0]

    assert compile_controlled_fixture_analysis_refinement(
        analysis,
        {**dict(fixture), "may_update_analysis": True},
        source_evidence_request=request,
    ) is None
    assert compile_controlled_fixture_analysis_refinement(
        analysis,
        {**dict(fixture), "requires_analysis_refinement_gate": False},
        source_evidence_request=request,
    ) is None


def test_controlled_refinement_survives_restart_without_analysis_or_answer_rewrite(tmp_path):
    result = _closed_loop_state(tmp_path)
    analyses = _records(result.state, "evidence_bound_analyses")
    refinements = _records(result.state, "analysis_refinements")
    restored = start_or_restore_runtime(tmp_path)

    restored_analyses = _records(restored, "evidence_bound_analyses")
    assert len(restored_analyses) == len(analyses) == 1
    assert restored_analyses[0]["analysis_id"] == analyses[0]["analysis_id"]
    assert restored_analyses[0]["result_summary"] == analyses[0]["result_summary"]
    restored_refinements = _records(restored, "analysis_refinements")
    assert len(restored_refinements) == len(refinements) == 2
    assert [item["refinement_id"] for item in restored_refinements] == [item["refinement_id"] for item in refinements]
    assert restored_refinements[-1]["source_evidence_minimal_fixture_result_id"] == refinements[-1]["source_evidence_minimal_fixture_result_id"]
    assert all(item["status"] != "final_answer" for item in restored_refinements)
