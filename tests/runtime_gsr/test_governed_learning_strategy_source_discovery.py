from __future__ import annotations

from orchestration.runtime.continuous_runtime_controller import (
    claim_governed_learning_strategy_narrow_source_discovery,
    compile_governed_learning_strategy_resource_revision,
    consume_continuous_operator_interaction_response,
    export_continuous_mission_restart_state,
    record_governed_learning_strategy_metadata_source_discovery,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from tests.runtime_gsr.test_governed_learning_strategy_revision import _partially_sufficient_controller


def _discovery_ready_controller():
    revised = compile_governed_learning_strategy_resource_revision(_partially_sufficient_controller())
    request = revised.continuous_learning_state["governed_learning_strategy_resource_revision"]["authority_request"]
    return consume_continuous_operator_interaction_response(
        revised,
        request_id=request["request_id"], response_kind=request["request_kind"],
        selected_option="approve_learning_strategy_resource_revision_authority",
        approved_scope=request["authority_scope"], operator_text="",
    )


def _candidate(locator: str, question_ids: tuple[str, ...], *, title: str = "Course notes", source_type: str = "authoritative_course_material", provenance: object | None = None):
    return {
        "candidate_id": f"metadata-{title}", "title": title, "canonical_locator": locator,
        "organization": "Example University", "source_type": source_type, "access_type": "open_access",
        "publication_or_course_identity": "Example course", "question_ids": question_ids,
        "relevance_rationale": "Public title and description identify coverage of the mapped learner question.",
        "metadata_confidence": 0.8, "retrieval_cost": 0.2,
        "provenance": provenance if provenance is not None else {"discovery_method": "fixture_metadata_search", "observed_at": "2026-07-21T00:00:00+00:00"},
    }


def test_metadata_discovery_retains_at_most_three_candidates_without_source_bodies():
    ready = _discovery_ready_controller()
    claimed = claim_governed_learning_strategy_narrow_source_discovery(ready)
    unresolved = tuple(claimed.continuous_learning_state["governed_learning_strategy_resource_revision"]["unresolved_question_ids"])
    exhausted = claimed.continuous_learning_state["governed_learning_strategy_resource_revision"]["retained_source_inventory"][0]["source_locator"]
    completed = record_governed_learning_strategy_metadata_source_discovery(claimed, metadata_candidates=(
        _candidate("https://university.example/course-a", unresolved[:1], title="A"),
        _candidate("https://university.example/course-b", unresolved[:1], title="B"),
        _candidate("https://university.example/course-c", unresolved[:1], title="C"),
        _candidate("https://university.example/course-d", unresolved, title="D"),
        _candidate(exhausted, unresolved[:1], title="Exhausted"),
        _candidate("https://forum.example/post", unresolved[:1], title="Forum", source_type="community_or_forum"),
    ))
    discovery = completed.continuous_learning_state["governed_learning_strategy_source_discovery"]
    result = discovery["result"]
    assert discovery["status"] == "completed"
    assert len(result["candidates"]) == 3
    assert result["metadata_only"] and result["source_body_retention_prohibited"] and result["retrieval_not_performed"]
    assert all(not {"body", "content", "content_text", "sanitized_text", "excerpt"}.intersection(candidate) for candidate in result["candidates"])
    assert all(set(candidate["question_ids"]).intersection(unresolved) for candidate in result["candidates"])
    assert {item["rejection_reason"] for item in result["rejected_candidates"]} >= {"duplicate_or_exhausted_retained_source", "source_type_not_authoritative_or_open"}
    assert not completed.continuous_active_subgoal
    assert "governed_learning_strategy_retrieval_authority_request" not in completed.continuous_learning_state


def test_metadata_discovery_rejects_unverifiable_or_body_bearing_candidates_and_restores_once():
    ready = _discovery_ready_controller()
    claimed = claim_governed_learning_strategy_narrow_source_discovery(ready)
    unresolved = tuple(claimed.continuous_learning_state["governed_learning_strategy_resource_revision"]["unresolved_question_ids"])
    completed = record_governed_learning_strategy_metadata_source_discovery(claimed, metadata_candidates=(
        {**_candidate("https://university.example/no-provenance", unresolved[:1]), "provenance": {}},
        {**_candidate("https://university.example/body", unresolved[:1]), "content_text": "not allowed"},
    ))
    result = completed.continuous_learning_state["governed_learning_strategy_source_discovery"]["result"]
    assert result["status"] == "learning_strategy_source_discovery_insufficient"
    assert {item["rejection_reason"] for item in result["rejected_candidates"]} == {"metadata_provenance_incomplete", "source_body_or_prohibited_material_present"}
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id=completed.session_id), export_continuous_mission_restart_state(completed),
    )
    assert restored.continuous_learning_state["governed_learning_strategy_source_discovery"]["result"] == result
    duplicate = claim_governed_learning_strategy_narrow_source_discovery(restored)
    assert duplicate.continuous_learning_state["governed_learning_strategy_source_discovery"]["result"] == result
