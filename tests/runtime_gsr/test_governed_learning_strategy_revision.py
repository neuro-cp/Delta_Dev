from __future__ import annotations

from orchestration.runtime.continuous_runtime_controller import (
    compile_governed_learning_strategy_resource_revision,
    consume_continuous_operator_interaction_response,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.governed_learning_strategy_revision import (
    compile_governed_learning_strategy_resource_revision as compile_revision_record,
    validate_governed_learning_strategy_resource_revision,
)
from tests.runtime_gsr.test_governed_learning_strategy_acquisition import _approved_controller, _source
from orchestration.runtime.continuous_runtime_controller import execute_governed_learning_strategy_exact_source_acquisition


def _partially_sufficient_controller():
    return execute_governed_learning_strategy_exact_source_acquisition(
        _approved_controller(),
        retrieval_adapter=lambda locator: {
            **_source(locator),
            "content_text": "Apply a bounded property within its defined scope.",
        },
    )


def test_partial_source_evidence_compiles_immutable_revision_and_narrow_discovery_request():
    partial = _partially_sufficient_controller()
    original = dict(partial.continuous_learning_state["governed_learning_strategy"])
    acquisition = dict(partial.continuous_learning_state["governed_learning_strategy_acquisition"]["result"])
    revised = compile_governed_learning_strategy_resource_revision(partial)
    revision = revised.continuous_learning_state["governed_learning_strategy_resource_revision"]
    request = revision["authority_request"]
    assert revision["validation"]["accepted"]
    assert revision["strategy_id"] == original["strategy_id"]
    assert revision["acquisition_result_digest"] == acquisition["result_digest"]
    assert tuple(revision["answered_question_ids"]) == tuple(
        item["question_id"] for item in acquisition["question_sufficiency"] if item["status"] == "answered"
    )
    assert tuple(revision["unresolved_question_ids"]) == tuple(
        item["question_id"] for item in acquisition["question_sufficiency"] if item["status"] != "answered"
    )
    assert revised.continuous_learning_state["governed_learning_strategy"] == original
    assert request["action_type"] == "narrow_source_discovery"
    assert "source_locator" not in request
    assert request["discovery_constraints"]["automatic_retrieval_prohibited"]
    assert revised.continuous_mission_state == "learning_strategy_resource_revision_awaiting_authority"
    assert not revised.continuous_active_subgoal
    assert compile_governed_learning_strategy_resource_revision(revised).continuous_learning_state["governed_learning_strategy_resource_revision"] == revision


def test_revision_rejects_fabricated_source_and_evaluator_material():
    partial = _partially_sufficient_controller()
    strategy = partial.continuous_learning_state["governed_learning_strategy"]
    result = partial.continuous_learning_state["governed_learning_strategy_acquisition"]["result"]
    revision = compile_revision_record(
        strategy=strategy,
        acquisition_result=result,
        available_resource_classes=("retained_local_evidence",),
        retained_source_inventory=(),
    )
    revision["authority_request"]["source_locator"] = "https://fabricated.invalid/lesson"
    revision["authority_request"]["evaluator_view"] = {"answer_key": "hidden"}
    validation = validate_governed_learning_strategy_resource_revision(revision, strategy=strategy, acquisition_result=result)
    assert not validation["accepted"]
    assert "fabricated_or_non_narrow_source_authority" in validation["errors"]
    assert "evaluator_only_material_present" in validation["errors"]


def test_resource_revision_restart_restores_one_pending_authority_request():
    revised = compile_governed_learning_strategy_resource_revision(_partially_sufficient_controller())
    restart = export_continuous_mission_restart_state(revised)
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id=revised.session_id), restart,
    )
    request = restored.continuous_learning_state["governed_learning_strategy_resource_revision"]["authority_request"]
    pending = [item for item in restored.continuous_developmental_insight_requests if item.get("request_id") == request["request_id"]]
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


def test_revision_authority_approval_is_exact_once_and_does_not_discover_sources():
    revised = compile_governed_learning_strategy_resource_revision(_partially_sufficient_controller())
    request = revised.continuous_learning_state["governed_learning_strategy_resource_revision"]["authority_request"]
    response_count = len(revised.continuous_operator_interaction_responses)
    approved = consume_continuous_operator_interaction_response(
        revised,
        request_id=request["request_id"],
        response_kind=request["request_kind"],
        selected_option="approve_learning_strategy_resource_revision_authority",
        approved_scope=request["authority_scope"],
        operator_text="",
    )
    stored = approved.continuous_learning_state["governed_learning_strategy_resource_revision"]["authority_request"]
    assert stored["status"] == "consumed"
    assert stored["authority_granted"]
    assert approved.continuous_mission_state == "learning_strategy_resource_discovery_ready"
    assert "source_discovery_result" not in approved.continuous_learning_state
    replay = consume_continuous_operator_interaction_response(
        approved,
        request_id=request["request_id"],
        response_kind=request["request_kind"],
        selected_option="approve_learning_strategy_resource_revision_authority",
        approved_scope=request["authority_scope"],
        operator_text="",
    )
    assert len(replay.continuous_operator_interaction_responses) == response_count + 1
