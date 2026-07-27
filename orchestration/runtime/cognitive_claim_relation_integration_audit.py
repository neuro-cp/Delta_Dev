"""Read-only integration feasibility audit for governed claim relations.

COGNITIVE-TRANSFER-CYCLE-1C inspects the exact production boundaries needed to
connect the inert 1B claim-relation contract. It does not integrate the
contract or mutate production memory, discourse, authority, persistence,
operator-request, work-item, or conversation paths.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.developmental_bootstrap import bootstrap_digest


STATUS_EXCLUDED_PATH_REQUIRED = "COGNITIVE_TRANSFER_CYCLE_1C_EXCLUDED_PATH_REQUIRED"
STATUS_INTEGRITY_STOP = "COGNITIVE_TRANSFER_CYCLE_1C_INTEGRITY_STOP"
SCHEMA_VERSION = "cognitive_claim_relation_integration_audit_v1"
OUTPUT_ROOT = Path(".tmp/cognitive-transfer-cycle-1c-integration-audit")
FROZEN_HEAD = "c8386d4935d82981cc3b34543b384e4837b12e14"
EXPECTED_EVALUATOR_DIGEST = "6c849e6a92ff0ac6ae6246e9a84651d9eae8f1fafdc6721731351149a598a847"
EXPECTED_AMENDMENT_ID = "cognitive-claim-relation-amendment-fcd6210a00b71ee1"
EXPECTED_AMENDMENT_DIGEST = "38a6dc1dee1d7689ff4a2bcf3daaff94cc10ea90eaabe5b116eb508908631e58"
EXPECTED_CONTRACT_DIGEST = "cde1599b2ffb91a2fdf5e17c5ab2d05d15b23ade2f9c52357ec7a9dbf2b40b8a"
EVALUATOR_PATH = Path("orchestration/runtime/cognitive_contradiction_evaluation.py")
CONTRACT_PATH = Path("orchestration/runtime/cognitive_claim_relations.py")
CONTRACT_TEST_PATH = Path("tests/runtime_gsr/test_cognitive_claim_relations.py")
EXCLUDED_PATHS = ("DELTA.py", "orchestration/runtime/live_competence_adapter.py")
PROTECTED_PATHS = ("DELTA-75", "reports/RC4_*")

REQUIRED_REPORT_FILES = (
    "baseline.json",
    "branch_head.json",
    "dirty_tree_before.json",
    "first_missing_transition.json",
    "transfer_gap_identity.json",
    "evaluator_identity.json",
    "evaluator_digest_audit.json",
    "contract_identity.json",
    "contract_digest.json",
    "amendment_identity.json",
    "amendment_digest_audit.json",
    "producer_inventory.json",
    "producer_feasibility.json",
    "relation_classifier_audit.json",
    "deterministic_relation_types.json",
    "semantic_relation_types.json",
    "consumer_inventory.json",
    "persistence_inventory.json",
    "persistence_feasibility.json",
    "authority_inventory.json",
    "operator_request_inventory.json",
    "dependent_work_inventory.json",
    "restart_inventory.json",
    "integration_path_graph.json",
    "required_information_matrix.json",
    "excluded_path_dependencies.json",
    "protected_path_dependencies.json",
    "missing_facts.json",
    "minimum_pilot_boundary.json",
    "feasibility_classification.json",
    "classification_evidence.json",
    "amendment_consequence.json",
    "next_gate_recommendation.json",
    "no_production_integration.json",
    "no_model_execution.json",
    "no_candidate_generation.json",
    "replay_checkpoint_regression.json",
    "test_results.json",
    "py_compile_result.json",
    "diff_check_result.json",
    "whitespace_result.json",
    "process_cleanup.json",
    "dirty_tree_after.json",
    "final_status.json",
)


def first_missing_transition() -> dict[str, Any]:
    return {
        "schema": "cognitive_transfer_cycle_1c_integration_audit_first_missing_transition_v1",
        "first_missing_transition": (
            "GovernedClaimRecord and GovernedClaimRelationRecord exist -> no production event currently creates "
            "them -> no production consumer currently evaluates their lifecycle, authority, or operator-resolution "
            "state -> the minimum legal integration boundary is unknown"
        ),
        "required_transition": (
            "actual cross-turn input event -> governed claim producer -> candidate relation classification boundary -> "
            "relation-state persistence -> claim-currentness consumer -> authority and dependent-work effects -> "
            "operator-resolution request -> restart reconstruction -> exact path and scope feasibility classification"
        ),
    }


def producer_inventory() -> tuple[dict[str, Any], ...]:
    return (
        {
            "path": "DELTA.py",
            "symbol": "desktop/live chat input dispatch and imported discourse/memory routes",
            "event_type": "operator_statement",
            "input_payload": "raw operator conversation text",
            "provenance_available": "conversation/session context likely available at boundary",
            "temporal_information_available": "turn order available at boundary",
            "applicability_scope_available": "implicit unless UI/session supplies it",
            "authority_source_available": "operator identity/session authority at boundary",
            "existing_persisted_identity": "not governed claim identity",
            "can_create_claim_without_inventing_facts": False,
            "currently_overwrites_or_appends": "conversation path not audited for claim ledger; excluded",
            "excluded_file": True,
        },
        {
            "path": "orchestration/runtime/v31_learning_opportunity.py",
            "symbol": "detect_learning_opportunities",
            "event_type": "review_only_operator_statement_scan",
            "input_payload": "text plus source",
            "provenance_available": "source string only",
            "temporal_information_available": "none beyond caller order",
            "applicability_scope_available": "not structured",
            "authority_source_available": "not structured",
            "existing_persisted_identity": "LearningOpportunity.id",
            "can_create_claim_without_inventing_facts": False,
            "currently_overwrites_or_appends": "returns in-memory review objects",
            "excluded_file": False,
        },
        {
            "path": "orchestration/runtime/v31_contradiction_aggregation.py",
            "symbol": "ContradictionObservation / aggregate_contradictions",
            "event_type": "runtime_observation_bundle",
            "input_payload": "topic, source, claim, confidence",
            "provenance_available": "source string",
            "temporal_information_available": "not explicit",
            "applicability_scope_available": "topic only",
            "authority_source_available": "not structured",
            "existing_persisted_identity": "ContradictionReviewBundle.bundle_id",
            "can_create_claim_without_inventing_facts": False,
            "currently_overwrites_or_appends": "groups observations only",
            "excluded_file": False,
        },
        {
            "path": "orchestration/runtime/v22_controlled_general_recall_expansion.py",
            "symbol": "run_controlled_general_recall_expansion",
            "event_type": "accepted_memory_or_recalled_concept_candidate",
            "input_payload": "jsonl memory candidate records",
            "provenance_available": "provenance_reference_ids when present",
            "temporal_information_available": "not consistently structured",
            "applicability_scope_available": "not consistently structured",
            "authority_source_available": "not consistently structured",
            "existing_persisted_identity": "candidate_id/canonical_record_id",
            "can_create_claim_without_inventing_facts": False,
            "currently_overwrites_or_appends": "read-only candidates",
            "excluded_file": False,
        },
        {
            "path": "orchestration/runtime/v31_gated_integration.py",
            "symbol": "parse_admin_approval / evaluate_gated_integration",
            "event_type": "operator_approval_or_authority_grant",
            "input_payload": "admin approval text, proposal, overwatch, override",
            "provenance_available": "approval_id, proposal_id, review ids",
            "temporal_information_available": "timestamp on integration event",
            "applicability_scope_available": "approval_scope",
            "authority_source_available": "approved_by/owner",
            "existing_persisted_identity": "approval_id/integration_event_id",
            "can_create_claim_without_inventing_facts": True,
            "currently_overwrites_or_appends": "returns event; no live write",
            "excluded_file": False,
        },
        {
            "path": "orchestration/runtime/live_competence_adapter.py",
            "symbol": "declare_adapter_capability / run_live_competence_json_validation_mission",
            "event_type": "runtime_observation/evidence_packet",
            "input_payload": "adapter capability and validation artifacts",
            "provenance_available": "artifact digests and source path",
            "temporal_information_available": "fixed timestamp",
            "applicability_scope_available": "task class",
            "authority_source_available": "adapter authority_requirements",
            "existing_persisted_identity": "artifact_digest",
            "can_create_claim_without_inventing_facts": True,
            "currently_overwrites_or_appends": "writes artifacts under .tmp",
            "excluded_file": True,
        },
        {
            "path": "orchestration/runtime/persistent_autonomous_development_runtime.py",
            "symbol": "recover_historical_retrieval_with_persistence",
            "event_type": "runtime_retrieval_claim",
            "input_payload": "historical claim id, locator, evidence target",
            "provenance_available": "parent_historical_claim_id and locator",
            "temporal_information_available": "created_at",
            "applicability_scope_available": "goal/frontier ids",
            "authority_source_available": "implicit runtime authority, not claim relation authority",
            "existing_persisted_identity": "claim_id",
            "can_create_claim_without_inventing_facts": True,
            "currently_overwrites_or_appends": "appends retrieval claims via checkpoint",
            "excluded_file": False,
        },
    )


def consumer_inventory() -> tuple[dict[str, Any], ...]:
    return (
        _consumer("DELTA.py", "conversation context assembly/rendering", "operator-visible conversation state", "does not consult claim lifecycle", True),
        _consumer("orchestration/runtime/v29_local_answer_engine.py", "run_v29_local_answer", "candidate local answer/evidence items", "candidate-context only, not authoritative", False),
        _consumer("orchestration/runtime/v29_natural_alias_router.py", "route_v29_alias", "current-state inventory text", "deterministic self-description only", False),
        _consumer("orchestration/runtime/v22_controlled_general_recall_expansion.py", "run_controlled_general_recall_expansion", "memory candidate records", "filters rejected/rolled_back but not claim-relation lifecycle", False),
        _consumer("orchestration/runtime/v34_cognitive_state.py", "build_runtime_state_snapshot", "MemoryState/LearningState", "snapshot flags only, no durable claim currentness", False),
        _consumer("orchestration/runtime/v31_gated_integration.py", "evaluate_gated_integration", "approval/proposal state", "does not consult revocation relation state", False),
        _consumer("orchestration/runtime/gsr_a_governed_self_regulation.py", "run_live_long_horizon_pilot", "LiveLongHorizonWorkItem state", "selective work blocking exists but unbound to claims", False),
        _consumer("orchestration/runtime/persistent_autonomous_development_runtime.py", "_checkpoint/restore_continuous state analogs", "runtime state bundle", "can persist dictionaries but no claim relation schema slot", False),
    )


def persistence_inventory() -> tuple[dict[str, Any], ...]:
    return (
        {
            "path": "orchestration/runtime/gsr_a_governed_self_regulation.py",
            "symbol": "write_governed_runtime_checkpoint/load_governed_runtime_checkpoint",
            "mechanism": "allowlisted gdr_1_runtime_state.json with digest validation",
            "atomic": True,
            "restart_reconstruction": True,
            "schema_impact": "GovernedRuntimeState dataclass has no claim_relation bundle slot",
            "safe_for_claim_relations_without_source_change": False,
        },
        {
            "path": "orchestration/runtime/persistent_autonomous_development_runtime.py",
            "symbol": "_checkpoint / _write_immutable_artifact / _exclusive_transition",
            "mechanism": "atomic state.json checkpoint plus immutable artifacts and transition directories",
            "atomic": True,
            "restart_reconstruction": True,
            "schema_impact": "dict state can carry new versioned bundle but production consumer wiring still needed",
            "safe_for_claim_relations_without_source_change": True,
        },
        {
            "path": "orchestration/runtime/live_general_2_dynamic_mission.py",
            "symbol": "_write / _state_record / _operator_request",
            "mechanism": "bootstrap artifacts under mission root",
            "atomic": True,
            "restart_reconstruction": True,
            "schema_impact": "mission-specific, not general conversation memory",
            "safe_for_claim_relations_without_source_change": False,
        },
        {
            "path": ".tmp/cognitive-transfer-cycle-1b/*",
            "symbol": "write_bundle/read_bundle",
            "mechanism": "inert report/test persistence",
            "atomic": True,
            "restart_reconstruction": True,
            "schema_impact": "not production; cannot couple integration to .tmp",
            "safe_for_claim_relations_without_source_change": False,
        },
    )


def authority_inventory() -> tuple[dict[str, Any], ...]:
    return (
        {"path": "orchestration/runtime/v31_gated_integration.py", "symbol": "AdminApprovalEvent/OwnerOverrideEvent/GatedIntegrationEvent", "supports_authorization": True, "supports_revocation": False, "consumed_once": False},
        {"path": "orchestration/runtime/operator_ux.py", "symbol": "compile_formal_operator_response/consume_formal_operator_response", "supports_authorization": True, "supports_revocation": False, "consumed_once": True},
        {"path": "orchestration/runtime/gsr_a_governed_self_regulation.py", "symbol": "create_live_operator_question/apply_live_operator_response", "supports_authorization": True, "supports_revocation": "partial via dispositions, not claim relation revocation", "consumed_once": True},
        {"path": "orchestration/runtime/continuous_runtime_controller.py", "symbol": "recover_accepted_boundary_operator_requests/restore_continuous_mission_restart_state", "supports_authorization": True, "supports_revocation": "not generic claim authority", "consumed_once": True},
    )


def operator_request_inventory() -> tuple[dict[str, Any], ...]:
    return (
        {"path": "orchestration/runtime/operator_ux.py", "symbol": "compile_operator_request_card", "duplicate_suppression": "caller-owned", "human_safe_text": True, "restart_recovery": "caller-owned"},
        {"path": "orchestration/runtime/gsr_a_governed_self_regulation.py", "symbol": "create_live_operator_question", "duplicate_suppression": "active/completed question ids", "human_safe_text": True, "restart_recovery": "OARRuntimeState"},
        {"path": "orchestration/runtime/live_general_2_dynamic_mission.py", "symbol": "_operator_request / consume_reconciliation_operator_rejection", "duplicate_suppression": "paused/terminal state replay suppression", "human_safe_text": True, "restart_recovery": "mission_state state.json"},
        {"path": "orchestration/runtime/autonomy_goal_discovery.py", "symbol": "operator_request directory", "duplicate_suppression": "request_id check", "human_safe_text": True, "restart_recovery": "artifact directory"},
    )


def dependent_work_inventory() -> tuple[dict[str, Any], ...]:
    return (
        {"path": "orchestration/runtime/gsr_a_governed_self_regulation.py", "symbol": "LiveLongHorizonWorkItem", "blocked_state": "blocked_operator_decision", "independent_work_continues": True, "claim_link": False},
        {"path": "orchestration/runtime/live_general_2_dynamic_mission.py", "symbol": "work_graph / mission_state work_items", "blocked_state": "blocked_learning_required", "independent_work_continues": True, "claim_link": False},
        {"path": "orchestration/runtime/persistent_autonomous_development_runtime.py", "symbol": "active_work_item/goals", "blocked_state": "blocked_operator_authority", "independent_work_continues": "goal graph dependent", "claim_link": "retrieval claims only"},
    )


def restart_inventory() -> tuple[dict[str, Any], ...]:
    return (
        {"path": "orchestration/runtime/gsr_a_governed_self_regulation.py", "symbol": "recover_oar_runtime_after_restart", "automatic_resume": False, "pending_request_preserved": "state ids"},
        {"path": "orchestration/runtime/continuous_runtime_controller.py", "symbol": "export_continuous_mission_restart_state/restore_continuous_mission_restart_state", "automatic_resume": False, "pending_request_preserved": True},
        {"path": "orchestration/runtime/persistent_autonomous_development_runtime.py", "symbol": "_checkpoint/resume_runtime", "automatic_resume": False, "pending_request_preserved": "state dependent"},
        {"path": "orchestration/runtime/live_general_2_dynamic_mission.py", "symbol": "_state/consume_reconciliation_operator_rejection", "automatic_resume": False, "pending_request_preserved": True},
    )


def deterministic_relation_types() -> tuple[str, ...]:
    return ("duplicate_restatement", "explicit_correction", "authority_revocation", "temporal_transition", "bounded_exception", "unrelated")


def semantic_relation_types() -> tuple[str, ...]:
    return ("direct_contradiction", "uncertain_conflict", "ambiguous_scope", "scoped_preference_update")


def classify_feasibility(
    producers: Sequence[Mapping[str, Any]] | None = None,
    consumers: Sequence[Mapping[str, Any]] | None = None,
    persistence: Sequence[Mapping[str, Any]] | None = None,
    *,
    semantic_classifier_needed: bool = True,
) -> dict[str, Any]:
    producers = tuple(producers or producer_inventory())
    consumers = tuple(consumers or consumer_inventory())
    persistence = tuple(persistence or persistence_inventory())
    excluded = tuple(item for item in (*producers, *consumers) if item.get("excluded_file"))
    missing_provenance = tuple(item for item in producers if not item.get("can_create_claim_without_inventing_facts"))
    clean_persistence = tuple(item for item in persistence if item.get("safe_for_claim_relations_without_source_change"))
    if excluded:
        primary = "excluded_path_required"
        status = STATUS_EXCLUDED_PATH_REQUIRED
        reason = "minimum trustworthy integration touches the actual conversation/live adapter boundary in excluded dirty files"
    elif missing_provenance:
        primary = "upstream_provenance_required"
        status = "COGNITIVE_TRANSFER_CYCLE_1C_UPSTREAM_PROVENANCE_REQUIRED"
        reason = "candidate producers cannot populate governed claims without inventing scope/provenance/authority facts"
    elif not clean_persistence:
        primary = "persistence_boundary_required"
        status = "COGNITIVE_TRANSFER_CYCLE_1C_PERSISTENCE_BOUNDARY_REQUIRED"
        reason = "no clean durable state bundle can preserve claim relation state"
    elif semantic_classifier_needed:
        primary = "semantic_classifier_required"
        status = "COGNITIVE_TRANSFER_CYCLE_1C_SEMANTIC_CLASSIFIER_REQUIRED"
        reason = "semantic relation cases require a bounded classifier contract before integration"
    else:
        primary = "locally_integrable"
        status = "COGNITIVE_TRANSFER_CYCLE_1C_LOCALLY_INTEGRABLE"
        reason = "all required boundaries are clean and bounded"
    return {"classification": primary, "status": status, "reason": reason}


def relation_classifier_audit() -> dict[str, Any]:
    return {
        "narrowest_clean_boundary": "review-only observation/proposal objects can compare text, but not before real conversation memory/currentness update",
        "narrowest_actual_boundary": "DELTA.py conversation dispatch/context assembly, excluded",
        "available_facts_clean": ("topic/source/claim strings", "proposal ids", "approval ids", "some artifact digests"),
        "missing_facts_clean": ("durable prior claim identity", "current lifecycle state", "structured scope", "structured temporal qualifier", "structured authority source for operator statements"),
        "deterministic_relation_types": deterministic_relation_types(),
        "semantic_relation_types": semantic_relation_types(),
        "model_called": False,
        "classifier_mode_needed_later": "hybrid",
    }


def required_information_matrix() -> tuple[dict[str, Any], ...]:
    rows = {
        "direct_contradiction": ("subject scope", "two claim identities", "overlapping temporal scope", "semantic predicate incompatibility"),
        "explicit_correction": ("correction marker", "same authorized source", "prior claim id", "scope unambiguous"),
        "preference_update": ("preference subject", "scope", "prior preference", "authority source"),
        "bounded_exception": ("original rule", "exception scope", "permitted action", "expiration/completion condition"),
        "uncertain_conflict": ("uncertainty marker", "evidence refs", "prior claim id"),
        "unrelated_topic": ("distinct subject identity",),
        "duplicate_restatement": ("scope-sensitive claim identity",),
        "authority_revocation": ("prior authorization", "revocation marker", "effective sequence", "affected pending work"),
        "temporal_transition": ("prior temporal scope", "new temporal scope", "transition marker/date"),
        "ambiguous_scope": ("ambiguous referent/scope marker", "affected claim ids", "affected work ids"),
        "restart_persistence": ("state bundle", "transition journal", "pending/resolved request state"),
        "operator_boundary_suspension": ("operator request id", "dependent work ids", "independent work ids"),
    }
    matrix = []
    for behavior, facts in rows.items():
        matrix.append({
            "behavior": behavior,
            "required_facts": facts,
            "current_source_of_facts": "partial across review-only and runtime state paths",
            "legally_available_at_producer": behavior in {"authority_revocation", "bounded_exception", "duplicate_restatement", "unrelated_topic"},
            "legally_available_at_classifier": "partial; actual boundary excluded",
            "legally_available_at_consumer": False,
            "persisted": False,
            "restart_visible": False,
            "authority_source": "partial for approvals, missing for general operator statements",
            "excluded_path_dependency": behavior in {"direct_contradiction", "explicit_correction", "preference_update", "ambiguous_scope", "operator_boundary_suspension"},
            "missing_fact": "structured claim lifecycle/currentness in production consumers",
            "minimum_integration_path": "excluded conversation boundary plus clean persistence/operator primitives",
        })
    return tuple(matrix)


def integration_path_graph() -> tuple[dict[str, Any], ...]:
    return (
        _edge("input producer", "claim construction", "existing but excluded for actual conversation", "DELTA.py"),
        _edge("claim construction", "prior-claim lookup", "missing", "new state lookup required"),
        _edge("prior-claim lookup", "relation classification", "missing", "hybrid classifier boundary required later"),
        _edge("relation classification", "relation transition", "existing inert only", "cognitive_claim_relations.py not production-integrated"),
        _edge("relation transition", "persistence", "partial", "persistent runtime can checkpoint; no production schema slot selected"),
        _edge("persistence", "current-state consumer", "missing/excluded", "conversation context in DELTA.py"),
        _edge("current-state consumer", "authority effect", "partial", "approval/operator primitives exist but no relation binding"),
        _edge("authority effect", "dependent-work transition", "partial", "LiveLongHorizonWorkItem supports selective blocking"),
        _edge("dependent-work transition", "operator request", "partial", "operator request primitives exist, not claim-bound"),
        _edge("operator request", "restart reconstruction", "partial", "several restart mechanisms preserve ids, not relation bundles"),
    )


def minimum_pilot_boundary() -> dict[str, Any]:
    return {
        "pilot": "one bounded conversation/review pilot for cross-turn operator claims",
        "must_support": ("explicit_correction", "direct_contradiction_or_unresolved_conflict", "duplicate_restatement", "temporal_transition", "restart_persistence", "one_operator_resolution_request", "linked_work_suspension_without_unrelated_work_blocking"),
        "minimum_paths": (
            "DELTA.py actual input/context boundary or an operator-approved clean adapter around it",
            "orchestration/runtime/cognitive_claim_relations.py inert transition contract",
            "orchestration/runtime/persistent_autonomous_development_runtime.py or equivalent clean checkpoint bundle",
            "orchestration/runtime/operator_ux.py and GSR/OAR operator question primitives",
            "LiveLongHorizonWorkItem-style selective work state",
        ),
        "not_all_baseline_cases_required": True,
        "materially_different_from_replay_validity": True,
        "blocked_reason": "actual input and consumer boundary is excluded dirty work",
    }


def amendment_consequence(classification: str) -> dict[str, Any]:
    mapping = {
        "excluded_path_required": "operator scope decision regarding excluded dirty files or an alternative clean adapter path",
        "semantic_classifier_required": "classifier contract and qualification gate",
        "upstream_provenance_required": "provenance-preservation contract gate",
        "persistence_boundary_required": "persistence boundary contract gate",
        "authority_binding_required": "authority-binding amendment gate",
    }
    return {
        "classification": classification,
        "next_authorized_gate": mapping.get(classification, "bounded integration authorization"),
        "execute_now": False,
        "amend_existing_transfer_amendment": False,
    }


def run_integration_audit_report(output_root: str | Path = OUTPUT_ROOT) -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    branch = _git_one("branch", "--show-current")
    head = _git_one("rev-parse", "HEAD")
    dirty_before = _git_lines("status", "--short", "--branch")
    evaluator_digest = _report_value(Path(".tmp/cognitive-transfer-cycle-1b/evaluator_digest.json"), "digest")
    amendment_digest = _report_value(Path(".tmp/cognitive-transfer-cycle-1b/proposal_amendment_digest.json"), "amendment_digest")
    final_1b = _read_json(Path(".tmp/cognitive-transfer-cycle-1b/final_status.json"))
    contract_digest = str(final_1b.get("contract_digest") or "")
    amendment_id = str(final_1b.get("amendment_id") or "")
    integrity_reasons = _integrity_reasons(head, evaluator_digest, amendment_id, amendment_digest, contract_digest)
    classification = classify_feasibility()
    if integrity_reasons:
        classification = {"classification": "integrity_stop", "status": STATUS_INTEGRITY_STOP, "reason": ";".join(integrity_reasons)}
    final = {
        "schema": SCHEMA_VERSION,
        "status": classification["status"],
        "primary_classification": classification["classification"],
        "reason": classification["reason"],
        "head": head,
        "branch": branch,
        "production_integration": False,
        "model_executed": False,
        "candidate_generated": False,
        "staged": False,
        "committed": False,
        "pushed": False,
    }
    reports: dict[str, Mapping[str, Any]] = {
        "baseline.json": {"accepted_status": "COGNITIVE_TRANSFER_CYCLE_1B_CONTRACT_PASSED", "accepted_gap": "durable_cross_turn_claim_relation_state_missing"},
        "branch_head.json": {"branch": branch, "head": head, "expected_head": FROZEN_HEAD},
        "dirty_tree_before.json": {"branch_status": dirty_before},
        "first_missing_transition.json": first_missing_transition(),
        "transfer_gap_identity.json": {"gap": "durable governed cross-turn claim-relation state missing", "materially_different_from_replay_validity": True},
        "evaluator_identity.json": {"path": str(EVALUATOR_PATH).replace("\\", "/"), "expected_digest": EXPECTED_EVALUATOR_DIGEST},
        "evaluator_digest_audit.json": {"digest": evaluator_digest, "expected": EXPECTED_EVALUATOR_DIGEST, "matches": evaluator_digest == EXPECTED_EVALUATOR_DIGEST},
        "contract_identity.json": {"path": str(CONTRACT_PATH).replace("\\", "/"), "test_path": str(CONTRACT_TEST_PATH).replace("\\", "/"), "exists": CONTRACT_PATH.exists()},
        "contract_digest.json": {"contract_digest": contract_digest, "expected": EXPECTED_CONTRACT_DIGEST, "matches": contract_digest == EXPECTED_CONTRACT_DIGEST},
        "amendment_identity.json": {"amendment_id": amendment_id, "expected": EXPECTED_AMENDMENT_ID, "matches": amendment_id == EXPECTED_AMENDMENT_ID},
        "amendment_digest_audit.json": {"amendment_digest": amendment_digest, "expected": EXPECTED_AMENDMENT_DIGEST, "matches": amendment_digest == EXPECTED_AMENDMENT_DIGEST},
        "producer_inventory.json": {"producers": producer_inventory()},
        "producer_feasibility.json": {"acceptable_without_inventing_facts": tuple(item for item in producer_inventory() if item["can_create_claim_without_inventing_facts"]), "actual_operator_statement_boundary_excluded": True},
        "relation_classifier_audit.json": relation_classifier_audit(),
        "deterministic_relation_types.json": {"relation_types": deterministic_relation_types()},
        "semantic_relation_types.json": {"relation_types": semantic_relation_types(), "model_call_authorized": False},
        "consumer_inventory.json": {"consumers": consumer_inventory()},
        "persistence_inventory.json": {"persistence": persistence_inventory()},
        "persistence_feasibility.json": {"clean_candidate_exists": True, "general_conversation_schema_slot_selected": False, "parallel_database_required": False},
        "authority_inventory.json": {"authority": authority_inventory()},
        "operator_request_inventory.json": {"operator_requests": operator_request_inventory()},
        "dependent_work_inventory.json": {"dependent_work": dependent_work_inventory()},
        "restart_inventory.json": {"restart": restart_inventory()},
        "integration_path_graph.json": {"edges": integration_path_graph()},
        "required_information_matrix.json": {"matrix": required_information_matrix()},
        "excluded_path_dependencies.json": {"excluded_paths": EXCLUDED_PATHS, "minimum_trustworthy_integration_requires": ("DELTA.py",), "live_adapter_dependency": "likely for live competence claim producer pilots"},
        "protected_path_dependencies.json": {"protected_paths": PROTECTED_PATHS, "required": False},
        "missing_facts.json": {"missing": ("production governed claim ledger", "prior-claim lookup", "production lifecycle consumer", "claim-bound operator request", "claim-bound authority effect", "structured scope/provenance for general operator statements")},
        "minimum_pilot_boundary.json": minimum_pilot_boundary(),
        "feasibility_classification.json": classification,
        "classification_evidence.json": {"excluded_producers_or_consumers": tuple(item for item in (*producer_inventory(), *consumer_inventory()) if item.get("excluded_file")), "semantic_classifier_later_needed": True, "primary_reason": classification["reason"]},
        "amendment_consequence.json": amendment_consequence(classification["classification"]),
        "next_gate_recommendation.json": {"recommended": amendment_consequence(classification["classification"])["next_authorized_gate"], "execute_now": False},
        "no_production_integration.json": {"memory_mutated": False, "discourse_mutated": False, "authority_mutated": False, "persistence_mutated": False, "operator_request_mutated": False, "conversation_behavior_mutated": False},
        "no_model_execution.json": {"model_executed": False},
        "no_candidate_generation.json": {"candidate_generated": False},
        "replay_checkpoint_regression.json": {"checkpoint": FROZEN_HEAD, "status": "pending_external_validation"},
        "test_results.json": {"status": "pending_external_validation"},
        "py_compile_result.json": {"status": "pending_external_validation"},
        "diff_check_result.json": {"status": "pending_external_validation"},
        "whitespace_result.json": {"status": "pending_external_validation"},
        "process_cleanup.json": {"long_running_processes_started": False},
        "dirty_tree_after.json": {"branch_status": _git_lines("status", "--short", "--branch")},
        "final_status.json": final,
    }
    for name in REQUIRED_REPORT_FILES:
        _write_json(root / name, reports[name])
    return final


def _consumer(path: str, symbol: str, state_consumed: str, current_behavior: str, excluded: bool) -> dict[str, Any]:
    return {
        "path": path,
        "symbol": symbol,
        "state_consumed": state_consumed,
        "current_behavior": current_behavior,
        "superseded_or_revoked_visible": "not governed by claim lifecycle",
        "historical_distinguished": False,
        "unresolved_contradiction_ignored": True,
        "operator_resolution_consulted": False,
        "integration_would_change_behavior": True,
        "excluded_or_protected": excluded,
        "excluded_file": excluded,
    }


def _edge(source: str, target: str, status: str, evidence: str) -> dict[str, str]:
    return {"from": source, "to": target, "status": status, "evidence": evidence}


def _integrity_reasons(head: str, evaluator_digest: str, amendment_id: str, amendment_digest: str, contract_digest: str) -> tuple[str, ...]:
    reasons: list[str] = []
    if evaluator_digest != EXPECTED_EVALUATOR_DIGEST:
        reasons.append("evaluator_digest_mismatch")
    if amendment_id != EXPECTED_AMENDMENT_ID:
        reasons.append("amendment_id_mismatch")
    if amendment_digest != EXPECTED_AMENDMENT_DIGEST:
        reasons.append("amendment_digest_mismatch")
    if contract_digest != EXPECTED_CONTRACT_DIGEST:
        reasons.append("contract_digest_mismatch")
    return tuple(reasons)


def _report_value(path: Path, key: str) -> str:
    data = _read_json(path)
    return str(data.get(key) or "")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")


def _git_lines(*args: str) -> tuple[str, ...]:
    completed = subprocess.run(("git", *args), check=False, capture_output=True, text=True)
    return tuple(line for line in completed.stdout.splitlines() if line.strip())


def _git_one(*args: str) -> str:
    lines = _git_lines(*args)
    return lines[0] if lines else ""


def artifact_digest_for_paths(paths: Sequence[str]) -> str:
    return bootstrap_digest({path: Path(path).read_text(encoding="utf-8") if Path(path).exists() else "" for path in paths})


__all__ = [
    "EXPECTED_AMENDMENT_DIGEST",
    "EXPECTED_AMENDMENT_ID",
    "EXPECTED_CONTRACT_DIGEST",
    "EXPECTED_EVALUATOR_DIGEST",
    "REQUIRED_REPORT_FILES",
    "STATUS_EXCLUDED_PATH_REQUIRED",
    "amendment_consequence",
    "artifact_digest_for_paths",
    "authority_inventory",
    "classify_feasibility",
    "consumer_inventory",
    "dependent_work_inventory",
    "deterministic_relation_types",
    "first_missing_transition",
    "integration_path_graph",
    "minimum_pilot_boundary",
    "operator_request_inventory",
    "persistence_inventory",
    "producer_inventory",
    "relation_classifier_audit",
    "required_information_matrix",
    "restart_inventory",
    "run_integration_audit_report",
    "semantic_relation_types",
]
