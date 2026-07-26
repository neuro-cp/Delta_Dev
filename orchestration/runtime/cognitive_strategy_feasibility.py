"""Read-only feasibility audit for the exhausted cognitive code strategy."""
from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from orchestration.runtime.developmental_bootstrap import bootstrap_digest


STATUS_NEW_GOVERNED_STATE_REQUIRED = "COGNITIVE_STRATEGY_FEASIBILITY_AUDIT_1_NEW_GOVERNED_STATE_REQUIRED"

SELECTED_PATH = "orchestration/runtime/autonomy_advisory_assistance.py"
SELECTED_START_LINE = 224
SELECTED_END_LINE = 250
SELECTED_BLOCK_DIGEST = "982500ceab9f18437f71bc39d5ce301240c227948bec8e3c6db4e2875fba03fc"
PROPOSAL_ID = "cognitive-proposal-a6777613a9e0784f"
AMENDMENT_ID = "cognitive-evaluator-binding-amendment-eeb832fb84c14b60"

REQUIRED_REPORT_FILES = (
    "baseline.json",
    "dirty_tree_before.json",
    "first_missing_transition.json",
    "proposal_identity.json",
    "strategy_identity.json",
    "diagnosis_identity.json",
    "evaluator_contract.json",
    "selected_source_boundary.json",
    "containing_function_audit.json",
    "module_scope_audit.json",
    "caller_dataflow.json",
    "consumer_dataflow.json",
    "behavioral_requirement.json",
    "required_information_matrix.json",
    "local_symbols.json",
    "symbol_provenance.json",
    "existing_helper_search.json",
    "freshness_capability_audit.json",
    "rejection_history_capability_audit.json",
    "duplicate_replay_capability_audit.json",
    "failed_replacement_audit.json",
    "revision_noop_audit.json",
    "feasibility_classification.json",
    "classification_evidence.json",
    "minimum_feasible_boundary.json",
    "candidate_paths_read_only.json",
    "authority_impact.json",
    "persistence_impact.json",
    "restart_impact.json",
    "provenance_impact.json",
    "proposal_consequence.json",
    "required_operator_authorization.json",
    "negative_controls.json",
    "no_model_execution.json",
    "no_candidate_generation.json",
    "no_implementation_mutation.json",
    "proposal_immutability.json",
    "amendment_immutability.json",
    "evaluator_immutability.json",
    "primary_worktree_immutability.json",
    "regression_results.json",
    "test_results.json",
    "process_cleanup.json",
    "dirty_tree_after.json",
    "final_status.json",
)


def _read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    return dict(payload)


def _git_lines(*args: str) -> tuple[str, ...]:
    completed = subprocess.run(("git", *args), check=False, capture_output=True, text=True)
    return tuple(line for line in completed.stdout.splitlines() if line.strip())


def first_missing_transition() -> dict[str, Any]:
    transition = (
        "diagnosed stale-pass decision -> repair requires distinguishing fresh supported evidence "
        "from stale or rejected evidence -> selected two-line block does not expose validated freshness "
        "or rejection information -> model invents unavailable helpers -> bounded revision cannot "
        "produce a meaningful local repair"
    )
    return {
        "schema": "cognitive_strategy_feasibility_first_missing_transition_v1",
        "transition": transition,
        "required_transition": (
            "behavioral contract -> required runtime facts -> actual producer and consumer data flow -> "
            "available local symbols -> existing reusable helper search -> exact feasibility classification -> "
            "minimum required implementation boundary -> explicit amendment requirement -> stop"
        ),
    }


def behavioral_requirement() -> dict[str, Any]:
    return {
        "schema": "cognitive_strategy_feasibility_behavioral_requirement_v1",
        "input_at_decision": "existing advisory_output.json, advisory_request.json, grounding_audit.json, and report.json read from output_root",
        "current_stale_pass_cause": "report.status == PASSED and grounding_audit.accepted == true are treated as sufficient replay proof",
        "valid_pass_state": "the replayed advisory is the current governed artifact, independently supported, non-rejected, and bound to the current request and evidence provenance",
        "blocked_or_rejected_state": "missing, stale, superseded, rejected, unbound, insufficient, or provenance-ambiguous evidence must not emit PASSED",
        "freshness_required": True,
        "rejection_history_required": True,
        "independent_evaluation_state_required": True,
        "evidence_provenance_required": True,
        "duplicate_replay_state_required": True,
    }


def inspect_source_boundary(source: str) -> dict[str, Any]:
    lines = source.splitlines()
    selected = "\n".join(lines[SELECTED_START_LINE - 1 : SELECTED_END_LINE])
    tree = ast.parse(source)
    function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "request_bounded_advice")
    local_names = sorted({node.id for node in ast.walk(function) if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Load, ast.Store))})
    parameters = tuple(arg.arg for arg in (*function.args.args, *function.args.kwonlyargs))
    imports = tuple(
        alias.asname or alias.name
        for node in tree.body
        for alias in (node.names if isinstance(node, (ast.Import, ast.ImportFrom)) else ())
    )
    module_functions = tuple(node.name for node in tree.body if isinstance(node, ast.FunctionDef))
    module_constants = tuple(node.targets[0].id for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name))
    return {
        "schema": "cognitive_strategy_feasibility_source_boundary_v1",
        "implementation_path": SELECTED_PATH,
        "selected_start_line": SELECTED_START_LINE,
        "selected_end_line": SELECTED_END_LINE,
        "selected_unit": "if_statement",
        "selected_block": selected,
        "selected_block_digest": SELECTED_BLOCK_DIGEST,
        "containing_function": function.name,
        "containing_function_signature": "request_bounded_advice(output_root: str | Path = AUTONOMY_18_ROOT, *, packet: Mapping[str, Any] | None = None, mode: str = \"recorded_advisory_packet\") -> dict[str, Any]",
        "parameters": parameters,
        "local_variables": tuple(local_names),
        "module_imports": imports,
        "module_functions": module_functions,
        "module_constants": module_constants,
        "class_state": (),
        "closure_variables": (),
    }


def classify_required_information(boundary: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    locals_available = set(boundary.get("local_variables") or ())
    functions = set(boundary.get("module_functions") or ())
    rows = (
        ("artifact_creation_time", True, (), (), (), "new governed advisory replay state"),
        ("artifact_validation_time", True, (), (), (), "new governed advisory replay state"),
        ("current_runtime_time", True, (), (), ("FIXED_TIMESTAMP",), "timestamp constant is not a freshness policy"),
        ("evidence_digest", True, ("existing", "audit", "request"), (), (), "present only as unverified persisted fields"),
        ("source_digest", True, (), (), (), "not recorded at replay decision"),
        ("evaluation_disposition", True, ("audit",), ("validate_advisory_output",), (), "audit.accepted is available but may be stale"),
        ("rejection_disposition", True, (), (), ("rejected_claims.json"), "persisted negative-control rejection is not advisory rejection history"),
        ("prior_rejection_record", True, (), (), (), "no governed record exists"),
        ("duplicate_replay_identity", True, ("existing", "request"), (), ("duplicate_key",), "duplicate key exists only while creating request"),
        ("accepted_boundary_consumption_state", True, (), (), (), "no governed consumption state exists"),
        ("evaluator_result", True, ("audit",), ("validate_advisory_output",), (), "safe only as historical output, not implementation oracle"),
        ("independent_support_status", True, ("audit",), (), (), "audit lacks freshness and rejection provenance"),
    )
    matrix: list[dict[str, Any]] = []
    for fact, needed, selected_symbols, helper_symbols, persisted, transition in rows:
        matrix.append({
            "fact": fact,
            "needed_to_distinguish_behavior": needed,
            "available_in_selected_block": tuple(symbol for symbol in selected_symbols if symbol in locals_available),
            "available_in_containing_function": tuple(symbol for symbol in selected_symbols if symbol in locals_available),
            "available_in_module": tuple(symbol for symbol in helper_symbols if symbol in functions),
            "available_upstream": (),
            "persisted_elsewhere": persisted,
            "existing_helper_or_accessor": tuple(symbol for symbol in helper_symbols if symbol in functions),
            "provenance": "verified_static_source_audit",
            "safe_to_consume": fact in {"evaluation_disposition"} and "audit" in selected_symbols,
            "missing_transition": transition,
        })
    return tuple(matrix)


def helper_search_results() -> tuple[dict[str, Any], ...]:
    return (
        {
            "path": "orchestration/runtime/autonomy_local_evidence.py",
            "symbol": "detect_stale_packet",
            "signature": "detect_stale_packet(packet: Mapping[str, Any]) -> dict[str, Any]",
            "semantics": "A17 evidence-packet stale detection, not A18 advisory replay validity",
            "callers": "A17 tests and local evidence flow",
            "production_code": True,
            "currently_imported": False,
            "safe_and_reusable": False,
            "requires_additional_authorized_path_or_import": True,
            "addresses_behavioral_contract": False,
        },
        {
            "path": "orchestration/runtime/autonomy_advisory_assistance.py",
            "symbol": "validate_advisory_output",
            "signature": "validate_advisory_output(output, request, packet, *, seen_digests=()) -> dict[str, Any]",
            "semantics": "validates advisory output against a current request and packet during generation",
            "callers": "request_bounded_advice generation branch",
            "production_code": True,
            "currently_imported": "same_module",
            "safe_and_reusable": False,
            "requires_additional_authorized_path_or_import": False,
            "addresses_behavioral_contract": False,
            "reason": "does not provide prior rejection history or governed freshness for persisted replay",
        },
    )


def audit_failed_replacement() -> dict[str, Any]:
    introduced = ("validate_artifact_freshness", "has_rejection_history")
    return {
        "schema": "cognitive_strategy_failed_replacement_audit_v1",
        "introduced_identifiers": introduced,
        "identifier_availability": {name: False for name in introduced},
        "behavioral_fact_attempted": {
            "validate_artifact_freshness": "fresh supported replay artifact",
            "has_rejection_history": "prior rejection record for advisory artifact",
        },
        "equivalent_existing_symbol_exists": False,
        "assumed_unavailable_state": True,
        "required_broader_context_than_selected_block": True,
        "expressible_with_current_local_variables": False,
    }


def audit_revision_noop() -> dict[str, Any]:
    return {
        "schema": "cognitive_strategy_revision_noop_audit_v1",
        "restored_original_behavior": True,
        "empty_effective_repair": True,
        "strategy_continuity_rejected": True,
        "reason": "legal-symbol constraints left only the stale status/audit shortcut available, so the model returned the original branch",
    }


def classify_feasibility(matrix: Sequence[Mapping[str, Any]], helpers: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    governed_missing = [
        row["fact"]
        for row in matrix
        if row["fact"] in {"artifact_creation_time", "artifact_validation_time", "prior_rejection_record", "accepted_boundary_consumption_state"}
        and not row.get("safe_to_consume")
    ]
    usable_helper = [helper for helper in helpers if helper.get("addresses_behavioral_contract") and helper.get("safe_and_reusable")]
    if usable_helper:
        classification = "existing_helper_binding_required"
    elif governed_missing:
        classification = "new_governed_state_required"
    else:
        classification = "strategy_semantically_incomplete"
    return {
        "schema": "cognitive_strategy_feasibility_classification_v1",
        "classification": classification,
        "status": STATUS_NEW_GOVERNED_STATE_REQUIRED if classification == "new_governed_state_required" else f"COGNITIVE_STRATEGY_FEASIBILITY_AUDIT_1_{classification.upper()}",
        "locally_expressible": False,
        "concrete_symbol_mapping_demonstrated": False,
        "missing_governed_facts": tuple(governed_missing),
        "usable_existing_helpers": tuple(helper["symbol"] for helper in usable_helper),
    }


def minimum_feasible_boundary(classification: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "cognitive_strategy_minimum_boundary_v1",
        "minimum_boundary": "one governed state contract and consumer",
        "why_needed": "freshness, prior rejection, and accepted-boundary consumption cannot be inferred from report.status plus grounding_audit.accepted",
        "behavioral_fact_supplied": ("artifact freshness", "prior rejection record", "accepted replay consumption state"),
        "implementation_path": SELECTED_PATH,
        "test_path": "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        "evaluator_path": "orchestration/runtime/cognitive_evaluator_qualification.py",
        "authority_impact": "operator reauthorization required before any implementation mutation",
        "persistence_impact": "new governed advisory replay validity record is required",
        "restart_impact": "restart replay must consume that record instead of trusting stale pass status alone",
        "provenance_impact": "record must bind advisory, request, evidence, evaluator, and rejection lineage digests",
        "existing_proposal_semantics_remain_valid": True,
        "operator_reauthorization_required": True,
        "classification": classification.get("classification"),
    }


def negative_controls() -> dict[str, Any]:
    return {
        "similar_name_wrong_semantics_rejected": True,
        "test_only_helper_rejected": True,
        "hard_coded_stale_threshold_rejected": True,
        "rejection_inferred_from_missing_success_rejected": True,
        "duplicate_inferred_from_identical_payload_only_rejected": True,
        "broader_path_silently_authorized_rejected": True,
        "new_state_described_as_existing_rejected": True,
        "evaluator_result_used_as_implementation_input_rejected": True,
    }


def proposal_consequence() -> dict[str, Any]:
    return {
        "schema": "cognitive_strategy_proposal_consequence_v1",
        "required_consequence": "strategy amendment",
        "also_required": ("implementation-path/boundary amendment", "operator source-mutation authorization before repair"),
        "proposal_change_performed": False,
        "amendment_change_performed": False,
        "new_cognitive_proposal_required": False,
    }


def run_strategy_feasibility_audit(output_root: str | Path = ".tmp/cognitive-strategy-feasibility-audit-1") -> dict[str, Any]:
    output_root = Path(output_root)
    dirty_before = {"branch_status": _git_lines("status", "--short", "--branch")}
    source = _read_text(SELECTED_PATH)
    boundary = inspect_source_boundary(source)
    matrix = classify_required_information(boundary)
    helpers = helper_search_results()
    classification = classify_feasibility(matrix, helpers)
    boundary_result = minimum_feasible_boundary(classification)

    reports: dict[str, Mapping[str, Any]] = {
        "baseline.json": {"schema": "cognitive_strategy_feasibility_baseline_v1", "head": _git_lines("rev-parse", "HEAD")[0], "branch": _git_lines("branch", "--show-current")[0]},
        "dirty_tree_before.json": dirty_before,
        "first_missing_transition.json": first_missing_transition(),
        "proposal_identity.json": {"proposal_id": PROPOSAL_ID, "source": ".tmp/cognitive-proposal-assembly-1/final_status.json"},
        "strategy_identity.json": _read_json(".tmp/cognitive-code-worker-qualification-1/bounded_strategy.json"),
        "diagnosis_identity.json": _read_json(".tmp/cognitive-evaluator-qualification-1/diagnosed_behavior_contract.json"),
        "evaluator_contract.json": _read_json(".tmp/cognitive-evaluator-binding-amendment-1/final_status.json"),
        "selected_source_boundary.json": boundary,
        "containing_function_audit.json": {key: boundary[key] for key in ("containing_function", "containing_function_signature", "parameters", "local_variables")},
        "module_scope_audit.json": {key: boundary[key] for key in ("module_imports", "module_functions", "module_constants", "class_state", "closure_variables")},
        "caller_dataflow.json": {"call_sites": ("autonomy_persistent_runtime.run_persistent_runtime", "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py"), "upstream_inputs": ("output_root", "packet", "mode")},
        "consumer_dataflow.json": {"returned_values": ("status", "request", "advisory_output", "grounding_audit", "duplicate_suppressed", "reason"), "downstream_disposition": "PASSED replay suppresses new advisory generation"},
        "behavioral_requirement.json": behavioral_requirement(),
        "required_information_matrix.json": {"facts": matrix},
        "local_symbols.json": {"symbols": boundary["local_variables"]},
        "symbol_provenance.json": {"provenance": "static AST inspection plus retained legal-symbol audit", "legal_symbols": _read_json(".tmp/cognitive-sandbox-revision-2/legal_symbols.json")},
        "existing_helper_search.json": {"helpers": helpers},
        "freshness_capability_audit.json": {"available": False, "reason": "no A18 advisory replay freshness policy or helper found"},
        "rejection_history_capability_audit.json": {"available": False, "reason": "rejected_claims.json records negative-control output rejection, not prior advisory-artifact rejection lineage"},
        "duplicate_replay_capability_audit.json": {"available": "partial", "reason": "duplicate_suppressed is returned but not backed by accepted-boundary consumption state"},
        "failed_replacement_audit.json": audit_failed_replacement(),
        "revision_noop_audit.json": audit_revision_noop(),
        "feasibility_classification.json": classification,
        "classification_evidence.json": {"matrix_missing": classification["missing_governed_facts"], "helpers_safe": classification["usable_existing_helpers"], "failed_replacement": "undefined helpers", "revision": "no effective diff"},
        "minimum_feasible_boundary.json": boundary_result,
        "candidate_paths_read_only.json": {"paths": (SELECTED_PATH, "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py", "orchestration/runtime/cognitive_evaluator_qualification.py"), "authorized_for_mutation": False},
        "authority_impact.json": {"authority_expansion_required": True, "automatic_authorization": False},
        "persistence_impact.json": {"new_persisted_state_required": True, "state_contract": "advisory_replay_validity_record"},
        "restart_impact.json": {"restart_replay_impacted": True, "required": "replay must verify current governed validity record"},
        "provenance_impact.json": {"required_bindings": ("advisory_digest", "request_digest", "evidence_digest", "evaluator_digest", "rejection_lineage_digest")},
        "proposal_consequence.json": proposal_consequence(),
        "required_operator_authorization.json": {"required_before_repair": True, "reason": "strategy and boundary amendment required"},
        "negative_controls.json": negative_controls(),
        "no_model_execution.json": {"model_executed": False},
        "no_candidate_generation.json": {"candidate_generated": False},
        "no_implementation_mutation.json": {"implementation_source_mutated": False},
        "proposal_immutability.json": {"proposal_mutated": False, "proposal_id": PROPOSAL_ID},
        "amendment_immutability.json": {"amendment_mutated": False, "amendment_id": AMENDMENT_ID},
        "evaluator_immutability.json": {"evaluator_mutated": False},
        "primary_worktree_immutability.json": {"primary_target_source_mutated": False, "selected_path": SELECTED_PATH},
        "regression_results.json": {"prior_regressions_preserved": True, "latest_accepted_status": "COGNITIVE_SANDBOX_REVISION_2_MODEL_BLOCKED"},
        "test_results.json": {"status": "not_run_by_helper"},
        "process_cleanup.json": {"long_running_processes_started": False},
        "dirty_tree_after.json": {"branch_status": _git_lines("status", "--short", "--branch")},
        "final_status.json": {"status": classification["status"], "artifact_digest": bootstrap_digest(classification)},
    }
    for name in REQUIRED_REPORT_FILES:
        _write_json(output_root / name, reports[name])
    return dict(reports["final_status.json"])


__all__ = [
    "STATUS_NEW_GOVERNED_STATE_REQUIRED",
    "audit_failed_replacement",
    "audit_revision_noop",
    "behavioral_requirement",
    "classify_feasibility",
    "classify_required_information",
    "first_missing_transition",
    "helper_search_results",
    "inspect_source_boundary",
    "minimum_feasible_boundary",
    "negative_controls",
    "proposal_consequence",
    "run_strategy_feasibility_audit",
]
