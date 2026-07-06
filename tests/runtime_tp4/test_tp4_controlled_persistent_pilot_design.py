from __future__ import annotations

from orchestration.runtime.tp4_controlled_persistent_pilot_design import (
    answer_tp4_question,
    audit_governance_layers,
    build_activation_matrix,
    design_controlled_persistent_pilot,
    is_tp4_question,
    review_tp3_outcome,
    run_tp4_design_review,
    select_minimum_safe_feature,
    write_tp4_reports,
)


def test_tp4_accepts_tp3_for_design_but_not_activation():
    review = review_tp3_outcome()

    assert review["accepted_for_tp4"] is True
    assert review["rollback_validation"] == 1.0
    assert review["scorecard_integrity"] >= 0.9
    assert "not enable" in review["conclusion"]


def test_tp4_activation_matrix_classifies_subsystems_without_activating():
    matrix = build_activation_matrix()
    classes = matrix["classification_counts"]

    assert matrix["no_capability_activated"] is True
    assert classes["Pilot Ready"] >= 3
    assert classes["Blocked"] >= 3
    assert any(entry["subsystem"] == "canonical_memory_writes" and entry["classification"] == "Blocked" for entry in matrix["entries"])
    assert any(entry["subsystem"] == "operator_reviewed_noncanonical_semantic_consolidation" and entry["classification"] == "Pilot Ready" for entry in matrix["entries"])


def test_tp4_selects_smallest_noncanonical_operator_reviewed_feature():
    matrix = build_activation_matrix()
    feature = select_minimum_safe_feature(matrix)

    assert feature["selected_capability"] == "operator_reviewed_noncanonical_semantic_consolidation_from_real_operator_sessions"
    assert feature["recommended_activation_state"] == "design_ready_not_enabled"
    assert feature["explicitly_not_activated"] is True
    assert "canonical_memory_writes" in {item["capability"] for item in feature["rejected_candidates"]}


def test_tp4_pilot_design_is_noncanonical_reversible_and_disabled():
    feature = select_minimum_safe_feature(build_activation_matrix())
    design = design_controlled_persistent_pilot(feature)

    assert design["enabled_now"] is False
    assert design["storage_model"]["canonical"] is False
    assert design["storage_model"]["target_store"] == "data/tp5_noncanonical_pilot_store/"
    assert "any canonical write" in design["abort_criteria"]
    assert "PilotRollbackToken" in design["storage_model"]["records"]


def test_tp4_governance_audit_covers_required_layers():
    feature = select_minimum_safe_feature(build_activation_matrix())
    design = design_controlled_persistent_pilot(feature)
    audit = audit_governance_layers(design)

    assert audit["all_required_layers_present"] is True
    assert audit["checks"]["provenance"] == "strong"
    assert audit["checks"]["operator_approval"] == "strong"
    assert audit["checks"]["rollback"] == "strong_for_isolated_store"
    assert audit["no_instrumentation_patch_required_now"] is True


def test_tp4_final_recommendation_preserves_all_safety_boundaries():
    payload = run_tp4_design_review()
    safety = payload["safety"]

    assert payload["final_recommendation"] == "READY_FOR_CONTROLLED_NONCANONICAL_PERSISTENT_PILOT_IMPLEMENTATION"
    assert safety["model_training_performed"] is False
    assert safety["fine_tuning_performed"] is False
    assert safety["weight_update_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["live_memory_mutation_performed"] is False
    assert safety["live_knowledge_mutation_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["autonomous_action_execution_performed"] is False
    assert safety["hyb1_promoted"] is False
    assert safety["model_b_default_changed"] is False
    assert safety["pilot_enabled"] is False


def test_tp4_reports_and_local_answer_route():
    payload = write_tp4_reports()
    answer = answer_tp4_question("What is the minimum safe feature for TP4?")

    assert payload["persistent_pilot_design"]["enabled_now"] is False
    assert is_tp4_question("controlled persistent pilot")
    assert answer["phase"] == "TP4 Controlled Persistent Pilot Design Review"
    assert answer["safety"]["pilot_enabled"] is False
