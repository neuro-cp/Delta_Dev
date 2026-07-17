from __future__ import annotations

from pathlib import Path

from orchestration.runtime.capability_evaluation_strategy import compile_capability_evaluation_strategy
from orchestration.runtime.continuous_runtime_controller import (
    attach_developmental_learning_mission,
    compile_operator_developmental_learning_mission,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.developmental_learning import load_retained_learning_bundle


def _compile(*, target: str, behavior: str, domain: str = "mathematics", topic: str = "algebra", authorities=(), context=None):
    return compile_capability_evaluation_strategy(
        mission_id="mission", capability_id=target, subgoal_id="subgoal", domain=domain, topic=topic,
        capability_target=target, target_behavior=behavior, teaching_evidence_ids=("teaching-result",),
        capability_context=context, evaluator_authorities=authorities,
    )


def _selected(compiled):
    return compiled["selected_plan"]["selected_strategy"]


def test_requirement_classifies_observable_behavior_without_topic_to_strategy_shortcut():
    compiled = _compile(
        target="matrix_property_reasoning", behavior="verify a predeclared matrix predicate on unseen cases",
        authorities=({"strategy": "deterministic_predicate", "identity": "matrix-authority", "provenance": ("sealed-matrix-cases",)},),
    )
    requirement = compiled["requirement"]
    assert requirement["capability_type"] == "mathematical_reasoning"
    assert requirement["observable_outputs"]
    assert requirement["teaching_evidence_ids"] == ("teaching-result",)
    assert _selected(compiled) == "deterministic_predicate"


def test_independence_rejects_teaching_conflict_answer_leakage_and_mutable_authority():
    compiled = _compile(
        target="equation_solving", behavior="solve an equation on held-out inputs",
        authorities=({"strategy": "deterministic_predicate", "identity": "teaching-result", "provenance": ("teaching-result",)},),
    )
    predicate = next(item for item in compiled["strategy_candidates"] if item["strategy"] == "deterministic_predicate")
    assert predicate["independence_valid"] is False
    assert "teaching_source_conflict" in predicate["rejection_reasons"]
    assert _selected(compiled) == "evaluation_unavailable"
    assert compiled["selected_plan"]["capability_update_policy"] == "promotion_prohibited"
    assert compiled["evaluator_authority_request"]["request_type"] == "operator_supplied_sealed_cases"
    mutable = _compile(
        target="equation_solving", behavior="solve an equation on held-out inputs",
        authorities=({"strategy": "deterministic_predicate", "identity": "sealed-but-mutable", "provenance": ("independent-cases",), "candidate_mutable": True},),
    )
    mutable_predicate = next(item for item in mutable["strategy_candidates"] if item["strategy"] == "deterministic_predicate")
    assert "candidate_mutable_evaluator" in mutable_predicate["rejection_reasons"]
    assert _selected(mutable) == "evaluation_unavailable"


def test_software_behavior_selects_disposable_sandbox_and_forbids_tracked_mutation():
    compiled = _compile(
        target="repository_callable_behavior", behavior="execute a repository callable and preserve its control behavior",
        domain="software", topic="runtime", authorities=({
            "strategy": "sandbox_behavioral_execution", "identity": "existing-disposable-sandbox", "provenance": ("repository_behavior_contract",), "disposable": True,
        },),
    )
    assert compiled["requirement"]["capability_type"] == "software_behavior"
    assert _selected(compiled) == "sandbox_behavioral_execution"
    assert compiled["selected_plan"]["sandbox_scope"] == "disposable_only"
    assert compiled["selected_plan"]["tracked_source_mutation_allowed"] is False


def test_answer_key_and_source_comparison_select_only_for_their_evidence_shapes():
    answer_key = _compile(
        target="historical_concept_distinction", behavior="distinguish two predeclared historical claims",
        domain="history", topic="claims", authorities=({
            "strategy": "authoritative_answer_key", "identity": "operator-authored-sealed-key", "provenance": ("operator-retained-fixture-v1",), "sealed": True,
        },),
    )
    assert _selected(answer_key) == "authoritative_answer_key"
    synthesis = _compile(
        target="claim_source_comparison", behavior="produce a sourced synthesis that preserves disagreement",
        domain="research", topic="claims", authorities=({
            "strategy": "independent_source_comparison", "identity": "retained-independent-sources", "provenance": ("source-a", "source-b"), "contradiction_handling": True,
        },),
    )
    assert synthesis["requirement"]["capability_type"] == "evidence_synthesis"
    assert _selected(synthesis) == "independent_source_comparison"
    non_synthesis = _compile(
        target="equation_solving", behavior="solve equations", authorities=({
            "strategy": "independent_source_comparison", "identity": "sources", "provenance": ("source-a", "source-b"), "contradiction_handling": True,
        },),
    )
    assert _selected(non_synthesis) == "evaluation_unavailable"


def test_simulation_stays_unavailable_without_existing_independent_trusted_authority():
    compiled = _compile(target="causal_mechanism", behavior="predict a causal outcome", domain="biology", topic="selection")
    simulation = next(item for item in compiled["strategy_candidates"] if item["strategy"] == "simulation_or_model")
    assert simulation["available"] is False
    assert _selected(compiled) == "evaluation_unavailable"


def test_equivalent_compilation_is_stable_and_material_scope_change_versions_requirement():
    authority = ({"strategy": "deterministic_predicate", "identity": "sealed", "provenance": ("cases",)},)
    first = _compile(target="matrix_reasoning", behavior="verify matrix properties", authorities=authority, context={"required_scope": "finite real matrices"})
    same = _compile(target="matrix_reasoning", behavior="verify matrix properties", authorities=authority, context={"required_scope": "finite real matrices"})
    changed = _compile(target="matrix_reasoning", behavior="verify matrix properties", authorities=authority, context={"required_scope": "complex inner-product spaces"})
    assert first["requirement"]["requirement_id"] == same["requirement"]["requirement_id"]
    assert first["selected_plan"]["plan_id"] == same["selected_plan"]["plan_id"]
    assert changed["requirement"]["requirement_id"] != first["requirement"]["requirement_id"]


def test_existing_learning_controller_persists_strategy_and_restores_without_duplication(tmp_path: Path):
    controller = compile_operator_developmental_learning_mission(
        start_continuous_runtime_controller(session_id="strategy-restart"), "Today your goal is to learn mathematical induction."
    )
    state = controller.continuous_learning_state
    assert state["requirement"]["status"] == "requirement_compiled"
    assert state["selected_plan"]["status"] == "evaluation_plan_ready"
    restart = export_continuous_mission_restart_state(controller)
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="strategy-restart"), restart)
    assert restored.continuous_learning_state["requirement"]["requirement_id"] == state["requirement"]["requirement_id"]
    assert restored.continuous_learning_state["selected_plan"]["plan_id"] == state["selected_plan"]["plan_id"]
    assert len(restored.continuous_learning_state["strategy_candidates"]) == len(state["strategy_candidates"])


def test_complex_spectral_scope_without_complex_authority_stops_with_exact_blocker():
    compiled = _compile(
        target="complex_inner_product_space_scope", behavior="apply spectral reasoning in complex inner-product spaces",
        topic="spectral_theorem", context={"required_scope": "complex inner-product spaces"}, authorities=({
            "strategy": "deterministic_predicate", "identity": "finite-real-spectral-evaluator", "provenance": ("finite-real-sealed-cases",), "scope": "finite real matrices",
        },),
    )
    assert _selected(compiled) == "evaluation_unavailable"
    assert "missing_or_scope_mismatched_deterministic_authority" in next(item for item in compiled["strategy_candidates"] if item["strategy"] == "deterministic_predicate")["rejection_reasons"]
    assert compiled["evaluator_authority_request"]["coverage"] == ("baseline", "control", "held_out", "adversarial", "transfer")


def test_controller_blocks_learning_without_evaluator_authority_before_activation():
    bundle = dict(load_retained_learning_bundle("mathematics", "mathematical_induction") or {})
    bundle.pop("sealed_evaluation_cases", None)
    controller = attach_developmental_learning_mission(
        start_continuous_runtime_controller(session_id="strategy-blocked"),
        "Today your goal is to learn mathematical induction.",
        bundle,
    )
    assert controller.continuous_mission_state == "learning_evaluator_authority_needed"
    assert not controller.continuous_active_subgoal
    assert controller.continuous_learning_state["selected_plan"]["selected_strategy"] == "evaluation_unavailable"
    assert controller.continuous_learning_state["evaluator_authority_request"]["request_type"] == "operator_supplied_sealed_cases"
