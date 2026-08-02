"""Read-only reconciliation for excluded dirty production paths.

COGNITIVE-TRANSFER-CYCLE-1D determines whether the claim-relation pilot can be
authorized without absorbing unrelated dirty work. It does not modify excluded
files or integrate claim relations.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


STATUS_DELTA_ONLY = "COGNITIVE_TRANSFER_CYCLE_1D_DELTA_ONLY_AUTHORIZATION_REQUIRED"
SCHEMA_VERSION = "cognitive_transfer_cycle_1d_excluded_path_reconciliation_v1"
OUTPUT_ROOT = Path(".tmp/cognitive-transfer-cycle-1d-excluded-path-reconciliation")
FROZEN_HEAD = "c8386d4935d82981cc3b34543b384e4837b12e14"
EXPECTED_EVALUATOR_DIGEST = "6c849e6a92ff0ac6ae6246e9a84651d9eae8f1fafdc6721731351149a598a847"
EXPECTED_AMENDMENT_ID = "cognitive-claim-relation-amendment-fcd6210a00b71ee1"
EXPECTED_AMENDMENT_DIGEST = "38a6dc1dee1d7689ff4a2bcf3daaff94cc10ea90eaabe5b116eb508908631e58"
EXPECTED_CONTRACT_DIGEST = "cde1599b2ffb91a2fdf5e17c5ab2d05d15b23ade2f9c52357ec7a9dbf2b40b8a"
DELTA_PATH = Path("DELTA.py")
LIVE_ADAPTER_PATH = Path("orchestration/runtime/live_competence_adapter.py")
EXCLUDED_PATHS = (str(DELTA_PATH).replace("\\", "/"), str(LIVE_ADAPTER_PATH).replace("\\", "/"))

REQUIRED_REPORT_FILES = (
    "baseline.json",
    "branch_head.json",
    "dirty_tree_before.json",
    "first_missing_transition.json",
    "evaluator_identity.json",
    "contract_identity.json",
    "amendment_identity.json",
    "delta_head_digest.json",
    "delta_worktree_digest.json",
    "delta_complete_diff.json",
    "delta_hunk_inventory.json",
    "delta_hunk_classification.json",
    "delta_integration_seams.json",
    "live_adapter_head_digest.json",
    "live_adapter_worktree_digest.json",
    "live_adapter_complete_diff.json",
    "live_adapter_hunk_inventory.json",
    "live_adapter_hunk_classification.json",
    "live_adapter_dependency.json",
    "alternative_clean_seams.json",
    "rejected_alternatives.json",
    "semantic_classifier_placement.json",
    "deterministic_pilot_scope.json",
    "deferred_semantic_cases.json",
    "minimum_pilot.json",
    "scope_conflict_matrix.json",
    "dirty_hunk_ownership.json",
    "checkpoint_ownership.json",
    "primary_classification.json",
    "classification_evidence.json",
    "exact_authorization_boundary.json",
    "next_gate_recommendation.json",
    "no_excluded_file_mutation.json",
    "no_production_integration.json",
    "no_model_execution.json",
    "no_candidate_generation.json",
    "protected_path_audit.json",
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
        "schema": "cognitive_transfer_cycle_1d_excluded_path_reconciliation_first_missing_transition_v1",
        "first_missing_transition": (
            "claim-relation integration requires DELTA.py and possibly live_competence_adapter.py -> both files "
            "contain preserved pre-existing dirty work -> required integration hunks and existing dirty hunks have "
            "not been reconciled -> safe mutation scope and checkpoint ownership are unknown"
        ),
        "required_transition": (
            "exact excluded-file diff -> hunk provenance and purpose -> production call-graph role -> required "
            "integration seam -> overlap and conflict analysis -> alternative clean seam analysis -> minimum "
            "excluded-file set -> operator authorization recommendation -> stop before mutation"
        ),
    }


def delta_hunk_inventory() -> tuple[dict[str, Any], ...]:
    return (
        _hunk("DELTA.py", "177-199", "module imports", "imports autonomy A13/A14/A15/A16/A17/A18/A21 runtime helpers"),
        _hunk("DELTA.py", "1608-1621", "DeltaApp.__init__", "adds Tk status variables and button registries for A13/A14/A15/A16/A17/A18/A21"),
        _hunk("DELTA.py", "1846-1963", "DeltaApp UI construction", "adds visible control frames and buttons for task activation, composition, gap detection, mixed mission, local evidence, advisory proposal, and competence health"),
        _hunk("DELTA.py", "2088-2094", "_refresh_operator_ux_views", "refreshes new A13/A14/A15/A16/A17/A18/A21 controls"),
        _hunk("DELTA.py", "2286-2341", "_latest_autonomy_*", "reads latest A13/A14/A15/A16/A17/A18/A21 report artifacts"),
        _hunk("DELTA.py", "2384-2514", "_refresh_autonomy_*_controls", "updates enabled/disabled state and labels for new operator UX panels"),
        _hunk("DELTA.py", "2564-2829", "_run_autonomy_*_visible_control", "executes or explains A13/A14/A15/A16/A17/A18/A21 visible controls and appends operator-facing chat text"),
        _hunk("DELTA.py", "5351-5396", "conversation command dispatch", "routes local evidence and advisory-intent messages to A17/A18 controls"),
        _hunk("DELTA.py", "5431-5460", "conversation command dispatch", "routes composition and mixed-mission messages to A14/A16 controls"),
    )


def live_adapter_hunk_inventory() -> tuple[dict[str, Any], ...]:
    return (
        _hunk(
            "orchestration/runtime/live_competence_adapter.py",
            "282",
            "create_json_fixture",
            "ensures unsupported-schema directory exists before writing unsupported_schema_version schema",
        ),
    )


def classify_delta_hunks() -> tuple[dict[str, Any], ...]:
    classified: list[dict[str, Any]] = []
    for item in delta_hunk_inventory():
        symbol = item["symbol"]
        if symbol == "conversation command dispatch":
            classification = "production behavior change"
            overlap = "same broad message-dispatch function, but additive claim-relation hook can be placed before/after preserved intent blocks"
        else:
            classification = "active accepted development"
            overlap = "no direct overlap with claim-relation pilot seam"
        classified.append({
            **item,
            "classification": classification,
            "behavioral_effect": _delta_behavioral_effect(symbol),
            "supporting_evidence": "git diff, symbol search, and A13-A18/A21 runtime imports/control names",
            "likely_originating_gate": "autonomy A13-A18/A21 operator UX expansion; not part of claim-relation transfer cycle",
            "claim_relation_overlap": overlap,
            "must_remain_byte_for_byte_preserved": True,
            "operator_clarification_required": False,
            "ownership_known": True,
        })
    return tuple(classified)


def classify_live_adapter_hunks() -> tuple[dict[str, Any], ...]:
    return ({
        **live_adapter_hunk_inventory()[0],
        "classification": "compatibility repair",
        "behavioral_effect": "prevents missing parent directory failure for unsupported schema fixture creation",
        "supporting_evidence": "single-line diff inside create_json_fixture plus live_competence_adapter tests referencing unsupported_schema_version",
        "likely_originating_gate": "live competence adapter fixture robustness",
        "claim_relation_overlap": "none for operator-originated first pilot",
        "must_remain_byte_for_byte_preserved": True,
        "operator_clarification_required": False,
        "ownership_known": True,
    },)


def delta_integration_seams() -> tuple[dict[str, Any], ...]:
    return (
        _seam("DeltaApp conversation intake", "around _handle chat/message dispatch before route_message fallback", "raw operator message", "claim-relation pilot observation or no-op", "conversation state, last_report_inspection", "claim relation bundle state", "operator session", "raw turn and turn order", "overlaps broad dispatch function but not existing A17/A18/A14/A16 intent branches"),
        _seam("DeltaApp prior context reconstruction", "near current route_message/discourse_frame assembly", "current message plus prior pilot bundle", "prior GovernedClaimRecord candidates", "pilot persistence file", "none unless new claim", "operator session", "persisted claim provenance", "no direct dirty hunk overlap"),
        _seam("DeltaApp operator-facing rendering", "near _append_chat result path", "typed deterministic relation result", "concise operator-facing notice", "relation result", "chat display only", "operator session", "claim ids and relation ids", "same append surface used by dirty A13-A18 controls but additive"),
        _seam("DeltaApp restart persistence", "bounded pilot state path under governed runtime data or approved local state", "ClaimRelationStateBundle", "reconstructed bundle", "pilot state file", "pilot state file", "operator-authorized pilot only", "bundle transition journal", "requires DELTA.py call site but not live adapter"),
    )


def live_adapter_dependency() -> dict[str, Any]:
    return {
        "required_for_operator_turn_claim_production": False,
        "required_only_for_live_runtime_observations": True,
        "useful_but_not_necessary": True,
        "unrelated_to_first_pilot": True,
        "first_pilot_can_exclude_live_runtime_evidence": True,
        "classification": "deferred",
        "symbols": ("create_json_fixture", "run_live_competence_json_validation_mission", "declare_adapter_capability"),
    }


def alternative_clean_seams() -> tuple[dict[str, Any], ...]:
    return (
        {"alternative": "registered callback", "exists": False, "accepted": False, "reason": "no existing production callback around operator turns found"},
        {"alternative": "event listener/message bus", "exists": "v33 in-memory dispatcher only", "accepted": False, "reason": "would bypass actual DELTA.py conversation route/currentness consumer"},
        {"alternative": "state-bundle adapter", "exists": "persistent runtime checkpoints", "accepted": False, "reason": "can persist state but cannot receive real operator turns without DELTA.py"},
        {"alternative": "operator-request bridge", "exists": True, "accepted": False, "reason": "can render/request decisions but cannot create governed claims from production input"},
        {"alternative": "test-only harness", "exists": True, "accepted": False, "reason": "would fabricate end-to-end production integration"},
    )


def semantic_classifier_placement() -> dict[str, Any]:
    return {
        "model_called": False,
        "later_placement": "after deterministic claim construction and prior-claim lookup, before relation transition",
        "first_pilot_can_defer_semantic_classifier": True,
        "deterministic_first_pilot_relations": deterministic_pilot_cases(),
        "deferred_semantic_relations": deferred_semantic_cases(),
        "meaningful_without_model_inference": True,
    }


def deterministic_pilot_cases() -> tuple[str, ...]:
    return ("explicit_correction", "duplicate_restatement", "temporal_transition", "authority_revocation_or_bounded_exception", "restart_persistence", "no_duplicate_operator_request_needed")


def deferred_semantic_cases() -> tuple[str, ...]:
    return ("direct_contradiction", "uncertain_conflict", "ambiguous_scope", "scoped_preference_update_when_scope_is_implicit")


def minimum_pilot() -> dict[str, Any]:
    return {
        "sequence": (
            "operator turn A -> governed claim A persisted",
            "operator turn B contains explicit structural relation",
            "governed claim B created",
            "deterministic relation created",
            "prior claim preserved",
            "lifecycle state updated",
            "restart",
            "relation and lifecycle state reconstructed",
            "no silent overwrite",
        ),
        "required_cases": deterministic_pilot_cases(),
        "direct_semantic_contradiction_deferred": True,
        "uses_real_cross_turn_production_state": True,
        "requires_delta_py": True,
        "requires_live_competence_adapter": False,
    }


def scope_conflict_matrix() -> tuple[dict[str, Any], ...]:
    rows = [
        ("DELTA.py existing dirty hunks", "DELTA.py", "A13-A18/A21 UI, handlers, command dispatch", True, "same file, one broad dispatch overlap", True, True, "manageable with byte-for-byte preservation", False, "none", True, "commit existing dirty work separately preferred"),
        ("live_competence_adapter.py existing dirty hunk", str(LIVE_ADAPTER_PATH).replace("\\", "/"), "create_json_fixture", False, "none for first pilot", True, True, "none", False, "defer live-evidence pilot", False, "separate compatibility checkpoint"),
        ("claim producer insertion", "DELTA.py", "conversation intake", True, "near dispatch", True, True, "no conflict if additive and flag-guarded", False, "none trustworthy", True, "requires operator-scoped authorization"),
        ("relation classifier call", "DELTA.py plus new service", "deterministic classifier service call", True, "no existing hunk direct", True, True, "none for deterministic cases", False, "new service alone insufficient", True, "transfer pilot checkpoint after existing dirty ownership decision"),
        ("persistence binding", "DELTA.py plus clean persistence module", "pilot state load/write", True, "no existing hunk direct", True, True, "none if bounded", False, "state adapter cannot receive turns alone", True, "separate state schema evidence"),
        ("currentness consumer", "DELTA.py", "conversation context/current reply path", True, "same production file", True, True, "requires careful guard", False, "no clean production consumer", True, "operator authorization needed"),
        ("operator request", "operator_ux/GSR primitives", "compile_operator_request_card/create_live_operator_question", False, "none for deterministic pilot", True, True, "none", False, "existing primitive", False, "defer until semantic ambiguity pilot"),
        ("restart reconstruction", "DELTA.py plus clean persistence", "pilot bundle reconstruction", True, "no existing hunk direct", True, True, "none", False, "test-only reconstruction rejected", True, "required in next gate"),
        ("evaluator observation", "new focused tests", "contract/evaluator exposure", True, "none", True, True, "none", False, "existing evaluator compatibility", False, "no production mutation"),
    ]
    return tuple(_matrix_row(*row) for row in rows)


def checkpoint_ownership() -> dict[str, Any]:
    return {
        "delta_dirty_work": "commit_separately_before_claim_relation_integration_preferred",
        "live_adapter_dirty_work": "commit_separately_or_defer_outside_first_transfer_checkpoint",
        "claim_relation_pilot": "separate transfer checkpoint after explicit DELTA.py authorization",
        "include_existing_dirty_in_same_transfer_checkpoint": False,
        "preserve_outside_transfer_checkpoint_until_owner_decision": True,
        "impossible_to_separate_safely": False,
    }


def classify_reconciliation(
    *,
    delta_required: bool = True,
    live_required: bool = False,
    dirty_conflict: bool = False,
    unknown_ownership: bool = False,
    clean_adapter_available: bool = False,
    semantic_required_first: bool = False,
    broad_scope_blocked: bool = False,
) -> dict[str, str]:
    if dirty_conflict:
        return _classification("EXISTING_DIRTY_WORK_CONFLICT", "COGNITIVE_TRANSFER_CYCLE_1D_EXISTING_DIRTY_WORK_CONFLICT", "required integration overlaps dirty work in a way that cannot be separated")
    if unknown_ownership:
        return _classification("UNKNOWN_DIRTY_HUNK_OWNERSHIP", "COGNITIVE_TRANSFER_CYCLE_1D_UNKNOWN_DIRTY_HUNK_OWNERSHIP", "one or more required hunks have unknown ownership")
    if clean_adapter_available:
        return _classification("CLEAN_ADAPTER_PATH_AVAILABLE", "COGNITIVE_TRANSFER_CYCLE_1D_CLEAN_ADAPTER_AVAILABLE", "existing clean seam can support the real pilot")
    if semantic_required_first:
        return _classification("SEMANTIC_CLASSIFIER_GATE_REQUIRED_FIRST", "COGNITIVE_TRANSFER_CYCLE_1D_SEMANTIC_CLASSIFIER_REQUIRED", "no meaningful deterministic pilot remains")
    if broad_scope_blocked:
        return _classification("TRANSFER_SCOPE_BLOCKED", "COGNITIVE_TRANSFER_CYCLE_1D_SCOPE_BLOCKED", "bounded path requires broad conversation-runtime restructuring")
    if delta_required and live_required:
        return _classification("BOTH_EXCLUDED_FILES_AUTHORIZATION_REQUIRED", "COGNITIVE_TRANSFER_CYCLE_1D_BOTH_FILES_AUTHORIZATION_REQUIRED", "both excluded files are required for the minimum pilot")
    if delta_required and not live_required:
        return _classification("DELTA_ONLY_AUTHORIZATION_REQUIRED", STATUS_DELTA_ONLY, "DELTA.py is required; live_competence_adapter.py is deferred")
    return _classification("TRANSFER_SCOPE_BLOCKED", "COGNITIVE_TRANSFER_CYCLE_1D_SCOPE_BLOCKED", "no trustworthy production path identified")


def exact_authorization_boundary() -> dict[str, Any]:
    return {
        "classification": "DELTA_ONLY_AUTHORIZATION_REQUIRED",
        "allowed_delta_symbols": (
            "conversation message intake/dispatch around _handle_oar_language_development_mission and route_message fallback",
            "_append_chat rendering for concise pilot notice",
            "bounded pilot state load/write call sites",
        ),
        "allowed_additive_changes": (
            "import a new claim-relation pilot service",
            "create a flag-guarded deterministic structural claim-relation pilot hook",
            "persist/reconstruct only the pilot ClaimRelationStateBundle",
            "render concise operator-facing deterministic relation/lifecycle result",
            "focused tests and durable report evidence",
        ),
        "existing_dirty_hunks_to_preserve": tuple(item["line_range"] for item in delta_hunk_inventory()),
        "production_modules_allowed_to_add_or_change": (
            "new bounded pilot service module",
            "focused tests",
            "DELTA.py additive hook only after explicit operator authorization",
        ),
        "deterministic_pilot_cases": deterministic_pilot_cases(),
        "prohibited_semantic_cases": deferred_semantic_cases(),
        "test_and_restart_requirements": (
            "explicit correction preserves prior claim",
            "duplicate restatement suppressed",
            "temporal transition historical/current",
            "authority revocation or bounded exception",
            "restart reconstructs relation/lifecycle state",
            "no operator request duplicated where none is needed",
        ),
        "checkpoint_strategy": checkpoint_ownership(),
    }


def run_reconciliation_report(output_root: str | Path = OUTPUT_ROOT) -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    before = _git_lines("status", "--short", "--branch")
    delta_before = worktree_digest(DELTA_PATH)
    live_before = worktree_digest(LIVE_ADAPTER_PATH)
    classification = classify_reconciliation()
    final = {
        "schema": SCHEMA_VERSION,
        "status": classification["status"],
        "primary_classification": classification["classification"],
        "reason": classification["reason"],
        "branch": _git_one("branch", "--show-current"),
        "head": _git_one("rev-parse", "HEAD"),
        "production_integration": False,
        "model_executed": False,
        "candidate_generated": False,
        "staged": False,
        "committed": False,
        "pushed": False,
    }
    reports: dict[str, Mapping[str, Any]] = {
        "baseline.json": {"accepted_status": "COGNITIVE_TRANSFER_CYCLE_1C_EXCLUDED_PATH_REQUIRED", "frozen_head": FROZEN_HEAD},
        "branch_head.json": {"branch": final["branch"], "head": final["head"], "expected_head": FROZEN_HEAD},
        "dirty_tree_before.json": {"branch_status": before},
        "first_missing_transition.json": first_missing_transition(),
        "evaluator_identity.json": {"path": "orchestration/runtime/cognitive_contradiction_evaluation.py", "digest": EXPECTED_EVALUATOR_DIGEST},
        "contract_identity.json": {"path": "orchestration/runtime/cognitive_claim_relations.py", "contract_digest": EXPECTED_CONTRACT_DIGEST},
        "amendment_identity.json": {"amendment_id": EXPECTED_AMENDMENT_ID, "amendment_digest": EXPECTED_AMENDMENT_DIGEST},
        "delta_head_digest.json": {"path": "DELTA.py", "digest": head_digest(DELTA_PATH)},
        "delta_worktree_digest.json": {"path": "DELTA.py", "digest": delta_before},
        "delta_complete_diff.json": {"path": "DELTA.py", "diff": git_diff_for(DELTA_PATH)},
        "delta_hunk_inventory.json": {"hunks": delta_hunk_inventory()},
        "delta_hunk_classification.json": {"hunks": classify_delta_hunks()},
        "delta_integration_seams.json": {"seams": delta_integration_seams()},
        "live_adapter_head_digest.json": {"path": str(LIVE_ADAPTER_PATH).replace("\\", "/"), "digest": head_digest(LIVE_ADAPTER_PATH)},
        "live_adapter_worktree_digest.json": {"path": str(LIVE_ADAPTER_PATH).replace("\\", "/"), "digest": live_before},
        "live_adapter_complete_diff.json": {"path": str(LIVE_ADAPTER_PATH).replace("\\", "/"), "diff": git_diff_for(LIVE_ADAPTER_PATH)},
        "live_adapter_hunk_inventory.json": {"hunks": live_adapter_hunk_inventory()},
        "live_adapter_hunk_classification.json": {"hunks": classify_live_adapter_hunks()},
        "live_adapter_dependency.json": live_adapter_dependency(),
        "alternative_clean_seams.json": {"alternatives": alternative_clean_seams()},
        "rejected_alternatives.json": {"rejected": tuple(item for item in alternative_clean_seams() if not item["accepted"])},
        "semantic_classifier_placement.json": semantic_classifier_placement(),
        "deterministic_pilot_scope.json": {"cases": deterministic_pilot_cases()},
        "deferred_semantic_cases.json": {"cases": deferred_semantic_cases()},
        "minimum_pilot.json": minimum_pilot(),
        "scope_conflict_matrix.json": {"matrix": scope_conflict_matrix()},
        "dirty_hunk_ownership.json": {"delta": "known active accepted development outside transfer cycle", "live_adapter": "known compatibility repair outside first pilot", "unknown_ownership": False},
        "checkpoint_ownership.json": checkpoint_ownership(),
        "primary_classification.json": classification,
        "classification_evidence.json": {"delta_required": True, "live_adapter_required": False, "existing_dirty_preservable": True, "clean_adapter_available": False, "semantic_classifier_deferred": True},
        "exact_authorization_boundary.json": exact_authorization_boundary(),
        "next_gate_recommendation.json": {"recommended": "bounded DELTA.py authorization for deterministic claim-relation pilot", "execute_now": False},
        "no_excluded_file_mutation.json": {"delta_digest_before": delta_before, "delta_digest_after": worktree_digest(DELTA_PATH), "live_adapter_digest_before": live_before, "live_adapter_digest_after": worktree_digest(LIVE_ADAPTER_PATH), "mutated_by_gate": False},
        "no_production_integration.json": {"conversation_behavior_mutated": False, "memory_mutated": False, "authority_mutated": False, "persistence_mutated": False, "operator_request_mutated": False},
        "no_model_execution.json": {"model_executed": False},
        "no_candidate_generation.json": {"candidate_generated": False},
        "protected_path_audit.json": {"protected_paths": ("DELTA-75", "reports/RC4_*"), "required": False, "mutated": False},
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


def git_diff_for(path: Path) -> str:
    completed = subprocess.run(("git", "diff", "--", str(path)), check=False, capture_output=True, text=True)
    return completed.stdout


def worktree_digest(path: Path) -> str:
    return _sha256(path.read_bytes())


def head_digest(path: Path) -> str:
    completed = subprocess.run(("git", "show", f"HEAD:{str(path).replace(chr(92), '/')}"), check=False, capture_output=True)
    return _sha256(completed.stdout)


def _hunk(path: str, line_range: str, symbol: str, purpose: str) -> dict[str, Any]:
    return {
        "path": path,
        "line_range": line_range,
        "symbol": symbol,
        "purpose": purpose,
        "status": "modified",
        "production_active": path == "DELTA.py",
        "tests_depend_on_dirty_version": "unknown for DELTA.py UI; live adapter has focused tests around fixture creation" if path != "DELTA.py" else "not proven by this gate",
        "independently_checkpointable": True,
        "unknown_ownership": False,
    }


def _seam(symbol: str, line_range: str, inputs: str, outputs: str, state_read: str, state_written: str, authority: str, provenance: str, overlap: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "line_range": line_range,
        "inputs": inputs,
        "outputs": outputs,
        "state_read": state_read,
        "state_written": state_written,
        "authority_available": authority,
        "provenance_available": provenance,
        "existing_dirty_hunk_overlap": overlap,
        "clean_function_call_can_be_inserted": True,
        "bounded_pilot_flag_possible": True,
        "restart_exercisable_without_broad_refactor": True,
    }


def _delta_behavioral_effect(symbol: str) -> str:
    if symbol == "conversation command dispatch":
        return "new user utterances trigger A14/A16/A17/A18 visible controls instead of falling through to general discourse"
    if symbol.startswith("_run"):
        return "new button/command handlers can write bounded operator UX artifacts and append chat messages"
    if "UI" in symbol or "DeltaApp" in symbol:
        return "adds operator-visible panels and state only"
    return "supports new operator UX panels"


def _matrix_row(row: str, path: str, symbol: str, required: bool, overlap: str, ownership: bool, additive: bool, conflict: str, behavioral_conflict: bool, clean_alternative: str, auth: bool, checkpoint: str) -> dict[str, Any]:
    return {
        "row": row,
        "exact_path": path,
        "exact_symbol": symbol,
        "required_for_pilot": required,
        "existing_dirty_overlap": overlap,
        "ownership_known": ownership,
        "safe_additive_change": additive,
        "conflict_analysis": conflict,
        "behavioral_conflict": behavioral_conflict,
        "clean_alternative": clean_alternative,
        "operator_authorization_required": auth,
        "checkpoint_consequence": checkpoint,
    }


def _classification(classification: str, status: str, reason: str) -> dict[str, str]:
    return {"classification": classification, "status": status, "reason": reason}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")


def _git_lines(*args: str) -> tuple[str, ...]:
    completed = subprocess.run(("git", *args), check=False, capture_output=True, text=True)
    return tuple(line for line in completed.stdout.splitlines() if line.strip())


def _git_one(*args: str) -> str:
    lines = _git_lines(*args)
    return lines[0] if lines else ""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


__all__ = [
    "EXPECTED_AMENDMENT_DIGEST",
    "EXPECTED_AMENDMENT_ID",
    "EXPECTED_CONTRACT_DIGEST",
    "EXPECTED_EVALUATOR_DIGEST",
    "REQUIRED_REPORT_FILES",
    "STATUS_DELTA_ONLY",
    "alternative_clean_seams",
    "checkpoint_ownership",
    "classify_delta_hunks",
    "classify_live_adapter_hunks",
    "classify_reconciliation",
    "deferred_semantic_cases",
    "delta_hunk_inventory",
    "delta_integration_seams",
    "deterministic_pilot_cases",
    "exact_authorization_boundary",
    "first_missing_transition",
    "head_digest",
    "live_adapter_dependency",
    "live_adapter_hunk_inventory",
    "minimum_pilot",
    "run_reconciliation_report",
    "scope_conflict_matrix",
    "semantic_classifier_placement",
    "worktree_digest",
]
