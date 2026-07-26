"""Qualification helpers for a raw-code local model worker."""
from __future__ import annotations

import ast
import difflib
import json
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.cognitive_candidate_exact_edit import RESULT_TYPE
from orchestration.runtime.cognitive_candidate_revision import RETAINED_CANDIDATE_DIGEST
from orchestration.runtime.cognitive_sandbox_execution import IMPLEMENTATION_PATH, PROPOSAL_ID, path_prohibited
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


QWEN25_CODER_MODEL_ID = "qwen2-5-coder-7b-instruct-gguf-qwen2-5-coder-7b-instruct-q4-k-m"
QWEN25_CODER_EXPECTED_SHA256 = "7ec3d5cfd560c5eac34e6c377c0bbc2bda389b282dca2b28bc31e621d26929a7"
FIRST_MISSING_TRANSITION = (
    "validated cognitive proposal and exact source block -> Qwen3.5 cannot reliably serialize exact replacement artifacts -> "
    "no separately qualified code-emission worker exists -> applicable replacement content remains unproven"
)
REQUIRED_TRANSITION = (
    "exact frozen source block + validated bounded strategy -> native-template Qwen2.5-Coder request -> complete raw replacement source -> "
    "deterministic metadata binding -> replacement validation -> full-source syntax validation -> deterministic diff rendering -> "
    "git apply --check -> stop before application"
)
FORBIDDEN_RAW_MARKERS = (
    "```",
    "diff --git",
    "@@",
    "...",
    "todo",
    "http://",
    "https://",
    "pip install",
    "api_key",
    "credential",
    "token=",
    "deploy",
    "provider",
    "network",
    "DELTA-75",
    "reports/RC4_",
)
SUCCESS_CLAIMS = ("tests pass", "successfully fixed", "production ready", "verified success")
PATH_MARKERS = (".py", "orchestration/", "tests/", "\\")


def model_identity_from_spec(spec: Any, *, digest: str, backend_version: str = "") -> dict[str, Any]:
    path = Path(str(spec.path))
    return {
        "model_id": str(spec.name),
        "absolute_path": str(path),
        "file_digest": str(digest).lower(),
        "digest_matches_expected": str(digest).lower() == QWEN25_CODER_EXPECTED_SHA256,
        "architecture": str(getattr(spec, "family", "unknown")),
        "quantization": str(getattr(spec, "quantization", "unknown")),
        "context": int(getattr(spec, "context_length", 0) or 0),
        "size_bytes": int(getattr(spec, "size_bytes", 0) or 0),
        "backend_version": backend_version,
        "llama_cpp_compatible": True,
    }


def render_raw_code_request(
    *,
    implementation_path: str,
    diagnosed_transition: str,
    change_intent: str,
    expected_behavior: str,
    source_block: str,
) -> list[dict[str, str]]:
    system = (
        "You are a bounded code-editing worker.\n"
        "Return only the complete replacement source block.\n"
        "Do not return JSON.\n"
        "Do not use Markdown fences.\n"
        "Do not explain the answer.\n"
        "Do not include a diff.\n"
        "Do not modify another file.\n"
        "Do not claim the repair works or that tests pass."
    )
    user = "\n".join((
        "1. Language: Python",
        f"2. Exact implementation path: {implementation_path}",
        f"3. Diagnosed incorrect transition: {diagnosed_transition}",
        f"4. Bounded change intent: {change_intent}",
        f"5. Expected behavioral change: {expected_behavior}",
        "6. Prohibited changes: no other path, no evaluator change, no test change, no package/network/provider/credential/deployment code, no success claim",
        "7. Exact current source block:",
        source_block,
        "8. Return the complete replacement block only.",
    ))
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def raw_response_content(response: Mapping[str, Any]) -> str:
    choices = response.get("choices") or ()
    if not choices:
        return ""
    first = choices[0] if isinstance(choices[0], Mapping) else {}
    message = first.get("message") if isinstance(first, Mapping) else {}
    if isinstance(message, Mapping):
        return str(message.get("content") or "")
    return str(first.get("text") or "")


def _parse_single_if(raw: str) -> ast.If | None:
    try:
        parsed = ast.parse(raw)
    except SyntaxError:
        return None
    if len(parsed.body) == 1 and isinstance(parsed.body[0], ast.If):
        return parsed.body[0]
    return None


def _body_has_return_status(node: ast.If, status: str) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            text = ast.dump(child)
            if status in text:
                return True
    return False


def _test_mentions_runtime_evidence(node: ast.If) -> bool:
    text = ast.dump(node.test).lower()
    return "report" in text and "audit" in text and "accepted" in text


def _full_source_syntax(source: str, source_block: str, replacement: str) -> dict[str, Any]:
    if source.count(source_block) != 1:
        return {"accepted": False, "reason": "source_block_not_unique"}
    proposed = source.replace(source_block, replacement, 1)
    try:
        compile(proposed, IMPLEMENTATION_PATH, "exec")
    except SyntaxError as exc:
        return {"accepted": False, "reason": "syntax_error", "detail": str(exc)}
    return {"accepted": True, "proposed_source_digest": bootstrap_digest(proposed)}


def validate_raw_replacement(raw: str, *, source: str, source_block: str, source_block_digest: str) -> dict[str, Any]:
    reasons: list[str] = []
    content = str(raw or "")
    stripped = content.strip()
    if not stripped:
        reasons.append("empty_content")
    if content != stripped:
        reasons.append("leading_or_trailing_wrapper_rejected")
    lower = stripped.lower()
    if stripped.startswith("{") or stripped.startswith("["):
        reasons.append("json_envelope_rejected")
    if any(marker.lower() in lower for marker in FORBIDDEN_RAW_MARKERS):
        reasons.append("forbidden_marker_rejected")
    if any(claim in lower for claim in SUCCESS_CLAIMS):
        reasons.append("success_claim_rejected")
    if any(marker.lower() in lower for marker in PATH_MARKERS):
        reasons.append("additional_path_or_file_rejected")
    if "return the" in lower or "here is" in lower or "explanation" in lower:
        reasons.append("prose_wrapper_rejected")
    node = _parse_single_if(stripped)
    if node is None:
        reasons.append("not_complete_if_statement")
    else:
        if not _test_mentions_runtime_evidence(node):
            reasons.append("runtime_evidence_contract_bypassed")
        if _body_has_return_status(node, "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED") and not _body_has_return_status(node, "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP"):
            reasons.append("stale_pass_not_corrected")
        if '"accepted": true' in lower or "'accepted': true" in lower:
            reasons.append("hard_coded_evaluator_result_rejected")
    syntax = _full_source_syntax(source, source_block, stripped) if stripped else {"accepted": False, "reason": "empty_content"}
    if not syntax["accepted"]:
        reasons.append("full_source_syntax_invalid")
    if bootstrap_digest(source_block) != source_block_digest:
        reasons.append("source_block_digest_mismatch")
    return {
        "schema": "raw_code_replacement_validation_v1",
        "accepted": not reasons,
        "reasons": tuple(dict.fromkeys(reasons)),
        "syntax_validation": syntax,
        "raw_digest": bootstrap_digest(stripped) if stripped else "",
    }


def assemble_replacement_artifact(
    *,
    raw: str,
    original_candidate: Mapping[str, Any],
    source_block_digest: str,
    code_worker_model: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "result_type": RESULT_TYPE,
        "proposal_id": PROPOSAL_ID,
        "revises_candidate_digest": RETAINED_CANDIDATE_DIGEST,
        "implementation_path": IMPLEMENTATION_PATH,
        "source_block_digest": source_block_digest,
        "replacement_content": raw.strip(),
        "change_summary": original_candidate.get("change_intent"),
        "expected_behavioral_change": original_candidate.get("expected_behavioral_change"),
        "limitations": original_candidate.get("limitations"),
        "uncertainty": original_candidate.get("uncertainty"),
        "authority_used": ["bounded_local_sandbox"],
        "code_worker_model": dict(code_worker_model),
        "assembly_method": "deterministic_code_worker_binding_v1",
    }


def validate_strategy_continuity(raw: str) -> dict[str, Any]:
    reasons: list[str] = []
    stripped = str(raw or "").strip()
    node = _parse_single_if(stripped)
    text = stripped.lower()
    if node is None:
        reasons.append("not_complete_if_statement")
    else:
        if not _test_mentions_runtime_evidence(node):
            reasons.append("runtime_evidence_contract_bypassed")
        if not any(marker in text for marker in ("integrity_stop", "existing_advisory_not_grounded", "stale", "freshness", "rejection_history", "rejected_outputs", "advisory_remains_untrusted")):
            reasons.append("does_not_address_stale_pass_transition")
    if "import " in text or "def " in text or "class " in text:
        reasons.append("architecture_expansion")
    if "test_" in text or "evaluator" in text:
        reasons.append("evaluator_or_test_expansion")
    if "accepted\": true" in text or "'accepted': true" in text:
        reasons.append("hard_coded_evaluator_result")
    return {"schema": "code_worker_strategy_continuity_v1", "accepted": not reasons, "reasons": tuple(dict.fromkeys(reasons))}


def render_deterministic_diff(source: str, source_block: str, replacement: str) -> dict[str, Any]:
    if source.count(source_block) != 1:
        return {"schema": "code_worker_diff_v1", "accepted": False, "reason": "source_block_not_unique"}
    proposed = source.replace(source_block, replacement.strip(), 1)
    diff = "".join(difflib.unified_diff(
        source.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile=f"a/{IMPLEMENTATION_PATH}",
        tofile=f"b/{IMPLEMENTATION_PATH}",
    ))
    return {
        "schema": "code_worker_diff_v1",
        "accepted": bool(diff),
        "diff": diff,
        "raw_replacement_digest": bootstrap_digest(replacement.strip()),
        "proposed_source_digest": bootstrap_digest(proposed),
        "diff_digest": bootstrap_digest(diff),
        "hunk_count": sum(1 for line in diff.splitlines() if line.startswith("@@")),
        "changed_line_count": sum(1 for line in diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))),
        "target_path_count": 1,
    }


def negative_controls(valid_raw: str, *, source: str, source_block: str, source_block_digest: str) -> dict[str, Any]:
    cases = {
        "markdown_fenced": f"```python\n{valid_raw}\n```",
        "leading_trailing_explanation": f"Here is the block:\n{valid_raw}",
        "json_envelope": json.dumps({"replacement_content": valid_raw}),
        "partial_or_ellipsis": "if report.get(...):\n    ...",
        "additional_path": valid_raw + "\n# edit tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        "evaluator_hard_coding": "if report.get(\"status\") and audit.get(\"accepted\") is True:\n            return {\"grounding_audit\": {\"accepted\": True}}",
        "unconditional_bypass": "if True:\n            return {\"status\": \"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP\"}",
        "package_network_provider": "if report.get(\"status\"):\n            import requests\n            requests.get(\"https://example.com\")",
        "syntax_invalid": "if report.get(\"status\"):\nreturn {",
        "strategy_drift": "if report.get(\"status\"):\n            return {\"status\": \"rewrite architecture\"}",
        "source_block_digest_mismatch": valid_raw,
    }
    results: dict[str, Any] = {}
    for name, raw in cases.items():
        digest = "wrong" if name == "source_block_digest_mismatch" else source_block_digest
        validation = validate_raw_replacement(raw, source=source, source_block=source_block, source_block_digest=digest)
        strategy = validate_strategy_continuity(raw)
        results[name] = {"accepted": validation["accepted"] and strategy["accepted"], "validation": validation, "strategy": strategy}
    return results
