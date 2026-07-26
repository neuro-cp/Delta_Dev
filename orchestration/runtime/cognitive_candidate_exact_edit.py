"""Source-exact replacement helpers for non-applying cognitive edit checks."""
from __future__ import annotations

import ast
import difflib
import json
from typing import Any, Mapping

from orchestration.runtime.cognitive_candidate_revision import RETAINED_CANDIDATE_DIGEST
from orchestration.runtime.cognitive_sandbox_execution import IMPLEMENTATION_PATH, PROPOSAL_ID, path_prohibited
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


RESULT_TYPE = "sandbox_exact_block_replacement"
BLOCK_MARKER = 'if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:'
FIRST_MISSING_TRANSITION = (
    "scope-valid original candidate intent -> prior patch lacked sufficient exact source context -> "
    "broad candidate-revision request caused schema echo/incomplete output -> no source-exact replacement artifact exists -> "
    "exact applicability remains unproven"
)
REQUIRED_TRANSITION = (
    "verified original candidate intent -> deterministically identify exact authorized source block -> freeze source-block digest -> "
    "request replacement content only -> validate replacement artifact -> deterministically render exact diff -> "
    "git apply --check succeeds -> stop before application"
)
PROHIBITED_TEXT = (
    "delta-75",
    "reports/rc4_",
    "http://",
    "https://",
    "pip install",
    "package install",
    "api_key",
    "credential",
    "token=",
    "deploy",
    "provider",
    "network",
)
SUCCESS_CLAIMS = ("tests pass", "test passed", "successfully fixed", "production ready", "verified success")
EVALUATOR_REFERENCES = ("test_autonomy_18_advisory_assistance.py", "cognitive_evaluator", "evaluator_")
HARD_CODED_OUTCOMES = ("hidden_expected", "force accepted", "always accepted", "return true", '"accepted": true')


def source_identity(source: str) -> dict[str, Any]:
    return {
        "digest": bootstrap_digest(source),
        "encoding": "utf-8",
        "newline_style": "crlf" if "\r\n" in source else "lf",
    }


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    total = 0
    for line in source.splitlines(keepends=True):
        total += len(line)
        offsets.append(total)
    return offsets


def _node_text(source: str, node: ast.AST) -> str:
    offsets = _line_offsets(source)
    start = offsets[int(node.lineno) - 1] + int(node.col_offset)
    end = offsets[int(node.end_lineno) - 1] + int(node.end_col_offset)
    return source[start:end]


def select_source_block(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    candidates: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            text = _node_text(source, node)
            if BLOCK_MARKER in text:
                candidates.append(node)
    if not candidates:
        return {
            "accepted": False,
            "reason": "block_marker_not_unique",
            "marker_count": source.count(BLOCK_MARKER),
            "candidate_count": len(candidates),
        }
    node = min(candidates, key=lambda candidate: len(_node_text(source, candidate)))
    text = _node_text(source, node)
    count = source.count(text)
    return {
        "accepted": count == 1,
        "reason": "" if count == 1 else "source_block_not_unique",
        "implementation_path": IMPLEMENTATION_PATH,
        "start_line": int(node.lineno),
        "end_line": int(node.end_lineno),
        "syntactic_unit": "if_statement",
        "source_block": text,
        "source_block_digest": bootstrap_digest(text),
        "occurrence_count": count,
        "marker_count": source.count(BLOCK_MARKER),
        "relationship_to_original_candidate_intent": "contains the duplicate replay branch that returns PASSED when report status and grounding audit are accepted without validating stale rejected advisory artifacts",
    }


def replacement_schema(block_digest: str) -> dict[str, Any]:
    return {
        "result_type": RESULT_TYPE,
        "proposal_id": PROPOSAL_ID,
        "revises_candidate_digest": RETAINED_CANDIDATE_DIGEST,
        "implementation_path": IMPLEMENTATION_PATH,
        "source_block_digest": block_digest,
        "replacement_content": "complete replacement for the supplied block",
        "change_summary": "string",
        "expected_behavioral_change": "string",
        "limitations": ["string"],
        "uncertainty": {"score": 0.0, "reason": "string"},
        "authority_used": ["bounded_local_sandbox"],
    }


def _valid_uncertainty(value: Any) -> bool:
    if not isinstance(value, Mapping) or "score" not in value or not str(value.get("reason") or "").strip():
        return False
    try:
        score = float(value["score"])
    except (TypeError, ValueError):
        return False
    return 0.0 <= score <= 1.0


def _syntax_replacement_matches_block(replacement: str, *, expected_unit: str) -> bool:
    try:
        parsed = ast.parse(replacement)
    except SyntaxError:
        return False
    body = parsed.body
    return expected_unit == "if_statement" and len(body) == 1 and isinstance(body[0], ast.If)


def _full_source_syntax(source: str, source_block: str, replacement: str) -> dict[str, Any]:
    if source.count(source_block) != 1:
        return {"accepted": False, "reason": "source_block_not_unique"}
    proposed = source.replace(source_block, replacement, 1)
    try:
        compile(proposed, IMPLEMENTATION_PATH, "exec")
    except SyntaxError as exc:
        return {"accepted": False, "reason": "syntax_error", "detail": str(exc)}
    return {"accepted": True, "proposed_source_digest": bootstrap_digest(proposed)}


def validate_replacement_artifact(
    artifact: Mapping[str, Any] | None,
    *,
    source: str,
    block: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(artifact, Mapping):
        artifact = {}
        reasons.append("missing_object")
    if artifact.get("result_type") != RESULT_TYPE:
        reasons.append("wrong_result_type")
    if artifact.get("proposal_id") != PROPOSAL_ID:
        reasons.append("wrong_proposal_id")
    if artifact.get("revises_candidate_digest") != RETAINED_CANDIDATE_DIGEST:
        reasons.append("wrong_candidate_digest")
    if artifact.get("implementation_path") != IMPLEMENTATION_PATH or path_prohibited(str(artifact.get("implementation_path") or "")):
        reasons.append("implementation_path_mismatch")
    if artifact.get("source_block_digest") != block.get("source_block_digest"):
        reasons.append("source_block_digest_mismatch")
    if set(artifact.get("authority_used") or ()) != {"bounded_local_sandbox"}:
        reasons.append("authority_not_bounded")
    replacement = str(artifact.get("replacement_content") or "")
    if not replacement.strip():
        reasons.append("replacement_required")
    if "..." in replacement or "TODO" in replacement or "<" in replacement and ">" in replacement:
        reasons.append("placeholder_or_ellipsis_rejected")
    if "diff --git" in replacement or replacement.lstrip().startswith("@@"):
        reasons.append("model_diff_rejected")
    if not _syntax_replacement_matches_block(replacement, expected_unit=str(block.get("syntactic_unit") or "")):
        reasons.append("replacement_not_complete_syntactic_unit")
    full_syntax = _full_source_syntax(source, str(block.get("source_block") or ""), replacement) if replacement else {"accepted": False, "reason": "replacement_required"}
    if not full_syntax["accepted"]:
        reasons.append("full_source_syntax_invalid")
    if not isinstance(artifact.get("limitations"), list) or not artifact.get("limitations"):
        reasons.append("limitations_required")
    if not _valid_uncertainty(artifact.get("uncertainty")):
        reasons.append("uncertainty_required")
    text = json.dumps(dict(artifact), sort_keys=True, default=str).lower()
    if any(fragment in text for fragment in PROHIBITED_TEXT):
        reasons.append("prohibited_content")
    if any(fragment in text for fragment in SUCCESS_CLAIMS):
        reasons.append("success_claim_rejected")
    if any(fragment in text for fragment in EVALUATOR_REFERENCES):
        reasons.append("evaluator_or_test_mutation_rejected")
    if any(fragment in text for fragment in HARD_CODED_OUTCOMES):
        reasons.append("hard_coded_evaluator_outcome_rejected")
    if IMPLEMENTATION_PATH.replace("/", "\\") not in text and IMPLEMENTATION_PATH not in text:
        pass
    return {
        "schema": "exact_block_replacement_validation_v1",
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "syntax_validation": full_syntax,
    }


def validate_strategy_continuity(artifact: Mapping[str, Any] | None, *, block: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    artifact = artifact if isinstance(artifact, Mapping) else {}
    text = json.dumps(dict(artifact), sort_keys=True, default=str).lower()
    if artifact.get("implementation_path") != IMPLEMENTATION_PATH:
        reasons.append("path_expansion")
    if "evaluator" in text or "test_" in text:
        reasons.append("evaluator_or_test_expansion")
    if "new architecture" in text or "rewrite" in text or "refactor" in text:
        reasons.append("architecture_drift")
    if "hard-code" in text or "force accepted" in text or "always accepted" in text:
        reasons.append("governance_bypass")
    if "stale" not in text and "duplicate" not in text and "existing_advisory" not in text:
        reasons.append("does_not_address_diagnosed_transition")
    if str(block.get("relationship_to_original_candidate_intent") or "") and BLOCK_MARKER not in str(block.get("source_block") or ""):
        reasons.append("block_not_related_to_original_intent")
    return {
        "schema": "exact_block_strategy_continuity_v1",
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
    }


def attach_metadata(artifact: Mapping[str, Any], *, block: Mapping[str, Any], source_digest: str, model_id: str) -> dict[str, Any]:
    payload = dict(artifact)
    return {
        "replacement_artifact_id": "cognitive-exact-edit-" + bootstrap_digest(payload)[:16],
        "model_id": model_id,
        "inference_profile_id": "qwen35-native-template-exact-block-v1",
        "proposal_id": PROPOSAL_ID,
        "original_candidate_digest": RETAINED_CANDIDATE_DIGEST,
        "full_source_digest": source_digest,
        "source_block_identity": {
            "start_line": block.get("start_line"),
            "end_line": block.get("end_line"),
            "digest": block.get("source_block_digest"),
            "syntactic_unit": block.get("syntactic_unit"),
        },
        "artifact_digest": bootstrap_digest(payload),
    }


def render_exact_diff(source: str, block: Mapping[str, Any], replacement: str) -> dict[str, Any]:
    source_block = str(block.get("source_block") or "")
    if source.count(source_block) != 1:
        return {"schema": "exact_block_diff_v1", "accepted": False, "reason": "source_block_not_unique"}
    proposed = source.replace(source_block, replacement, 1)
    diff = "".join(difflib.unified_diff(
        source.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile=f"a/{IMPLEMENTATION_PATH}",
        tofile=f"b/{IMPLEMENTATION_PATH}",
    ))
    return {
        "schema": "exact_block_diff_v1",
        "accepted": bool(diff),
        "diff": diff,
        "proposed_source_digest": bootstrap_digest(proposed),
        "diff_digest": bootstrap_digest(diff),
        "changed_line_count": sum(1 for line in diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))),
        "hunk_count": sum(1 for line in diff.splitlines() if line.startswith("@@")),
        "target_paths": (IMPLEMENTATION_PATH,),
        "source_block_removal_count": diff.count(source_block.splitlines()[0]) if source_block else 0,
        "replacement_insertion_count": proposed.count(replacement),
    }


def negative_controls(valid: Mapping[str, Any], *, source: str, block: Mapping[str, Any]) -> dict[str, Any]:
    cases = {
        "wrong_source_block_digest": {**dict(valid), "source_block_digest": "wrong"},
        "wrong_candidate_digest": {**dict(valid), "revises_candidate_digest": "wrong"},
        "additional_implementation_path": {**dict(valid), "implementation_path": "orchestration/runtime/other.py"},
        "partial_snippet_or_ellipsis": {**dict(valid), "replacement_content": "if report.get(...):\n    ..."},
        "evaluator_mutation": {**dict(valid), "change_summary": "mutate tests/runtime_gsr/test_autonomy_18_advisory_assistance.py"},
        "success_claim": {**dict(valid), "change_summary": "tests pass and successfully fixed"},
        "network_package_provider": {**dict(valid), "change_summary": "pip install provider package and call network"},
        "source_block_not_unique": {"accepted": False, "reason": "source_block_not_unique"},
        "syntax_invalid_replacement": {**dict(valid), "replacement_content": "if report.get('status'):\nreturn {"},
        "strategy_drift": {**dict(valid), "change_summary": "rewrite the evaluator and broad refactor"},
        "hard_coded_evaluator_outcome": {**dict(valid), "replacement_content": "if report.get(\"status\"):\n        return {\"accepted\": True}"},
    }
    results: dict[str, Any] = {}
    for name, case in cases.items():
        if isinstance(case, Mapping) and "result_type" in case:
            validation = validate_replacement_artifact(case, source=source, block=block)
            strategy = validate_strategy_continuity(case, block=block)
            results[name] = {"accepted": validation["accepted"] and strategy["accepted"], "validation": validation, "strategy": strategy}
        else:
            results[name] = case
    return results
