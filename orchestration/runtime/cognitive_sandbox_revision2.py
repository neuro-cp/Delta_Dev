"""Bounded revision helpers after sandbox application regression."""
from __future__ import annotations

import ast
import builtins
from typing import Any, Mapping

from orchestration.runtime.cognitive_sandbox_execution import IMPLEMENTATION_PATH


SAFE_BUILTINS = {"bool", "dict", "len", "list", "set", "str", "tuple"}
PROHIBITED_IDENTIFIERS = {"validate_artifact_freshness", "has_rejection_history"}


def legal_symbols_for_request_bounded_advice(source: str, *, marker: str) -> dict[str, Any]:
    tree = ast.parse(source)
    function: ast.FunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "request_bounded_advice":
            function = node
            break
    if function is None:
        return {"accepted": False, "reason": "function_not_found"}
    local_names = {arg.arg for arg in function.args.args}
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            local_names.add(node.id)
    module_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            module_names.add(node.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                module_names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module_names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_names.add(target.id)
    return {
        "accepted": marker in source,
        "implementation_path": IMPLEMENTATION_PATH,
        "local_variables": tuple(sorted(local_names)),
        "module_symbols": tuple(sorted(module_names)),
        "safe_builtins": tuple(sorted(SAFE_BUILTINS)),
        "prohibited_identifiers": tuple(sorted(PROHIBITED_IDENTIFIERS)),
        "validate_artifact_freshness_available": "validate_artifact_freshness" in local_names | module_names,
        "has_rejection_history_available": "has_rejection_history" in local_names | module_names,
    }


def referenced_names(code: str) -> tuple[str, ...]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ()
    names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    return tuple(sorted(names))


def validate_identifier_scope(code: str, *, legal: Mapping[str, Any]) -> dict[str, Any]:
    names = set(referenced_names(code))
    allowed = set(legal.get("local_variables") or ()) | set(legal.get("module_symbols") or ()) | set(legal.get("safe_builtins") or ()) | set(dir(builtins))
    undefined = tuple(sorted(name for name in names if name not in allowed))
    prohibited = tuple(sorted(name for name in names if name in PROHIBITED_IDENTIFIERS))
    return {
        "schema": "sandbox_revision_2_identifier_scope_v1",
        "accepted": not undefined and not prohibited,
        "referenced_names": tuple(sorted(names)),
        "undefined_identifiers": undefined,
        "prohibited_identifiers_used": prohibited,
    }


def validate_revision_shape(code: str) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        parsed = ast.parse(code)
    except SyntaxError as exc:
        return {"accepted": False, "reasons": ("syntax_error",), "detail": str(exc)}
    if len(parsed.body) != 1 or not isinstance(parsed.body[0], ast.If):
        reasons.append("not_single_if_statement")
    text = code.lower()
    if "import " in text or "def " in text or "class " in text:
        reasons.append("new_import_or_helper_definition")
    if "tests/" in text or "orchestration/runtime/cognitive_evaluator" in text:
        reasons.append("additional_path_or_evaluator_reference")
    if "http://" in text or "https://" in text or "pip install" in text or "credential" in text or "token=" in text:
        reasons.append("external_authority_reference")
    return {"accepted": not reasons, "reasons": tuple(reasons)}


def classify_revision_behavior(
    *,
    baseline_classification: str,
    first_attempt_classification: str,
    revised_classification: str,
    focused_exit_code: int,
    prior_name_error_resolved: bool,
    evaluator_unchanged: bool,
) -> dict[str, Any]:
    if focused_exit_code != 0:
        classification = "focused_test_failure"
    elif not prior_name_error_resolved:
        classification = "regression"
    elif baseline_classification != "stale_pass_detected":
        classification = "evaluator_inconclusive"
    elif revised_classification == "valid_blocked_behavior" and evaluator_unchanged:
        classification = "measurable_improvement"
    elif revised_classification == "stale_pass_detected":
        classification = "no_material_change"
    elif revised_classification == "unrelated_failure":
        classification = "regression"
    else:
        classification = "evaluator_inconclusive"
    return {
        "schema": "sandbox_revision_2_behavioral_comparison_v1",
        "classification": classification,
        "baseline_classification": baseline_classification,
        "first_attempt_classification": first_attempt_classification,
        "revised_classification": revised_classification,
        "focused_exit_code": focused_exit_code,
        "prior_name_error_resolved": prior_name_error_resolved,
        "evaluator_unchanged": evaluator_unchanged,
    }


def negative_controls() -> dict[str, Any]:
    return {
        "undefined_helper_reference": {"accepted": False, "reason": "undefined_identifier"},
        "new_import_requirement": {"accepted": False, "reason": "new_import_rejected"},
        "additional_file_or_path": {"accepted": False, "reason": "additional_path_rejected"},
        "evaluator_hard_coding": {"accepted": False, "reason": "evaluator_hard_coding_rejected"},
        "unconditional_bypass": {"accepted": False, "reason": "evidence_bypass_rejected"},
        "wrong_source_block_digest": {"accepted": False, "reason": "source_block_digest_mismatch"},
        "strategy_drift": {"accepted": False, "reason": "strategy_drift"},
        "fuzzy_or_partial_patch": {"accepted": False, "reason": "fuzzy_or_partial_patch_rejected"},
        "external_authority": {"accepted": False, "reason": "external_authority_rejected"},
        "third_attempt_request": {"accepted": False, "reason": "third_attempt_rejected"},
    }
