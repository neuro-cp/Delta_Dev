"""Model-neutral code-output adapter for exact replacement blocks."""
from __future__ import annotations

import ast
import difflib
import json
import re
from typing import Any, Mapping

from orchestration.runtime.cognitive_candidate_exact_edit import RESULT_TYPE
from orchestration.runtime.cognitive_candidate_revision import RETAINED_CANDIDATE_DIGEST
from orchestration.runtime.cognitive_code_worker_qualification import QWEN25_CODER_EXPECTED_SHA256, validate_strategy_continuity
from orchestration.runtime.cognitive_sandbox_execution import IMPLEMENTATION_PATH, PROPOSAL_ID
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


ADAPTER_ID = "code-output-adapter-v1"
FIRST_INCORRECT_TRANSITION = (
    "single fenced replacement block -> strict plain-text contract rejects wrapper -> "
    "code semantics never reach indentation binding or full-source validation"
)


def adapter_record() -> dict[str, Any]:
    return {
        "adapter_id": ADAPTER_ID,
        "accepted_wrapper_types": ["plain_source", "single_python_fence"],
        "prohibited_wrapper_types": ["prose_plus_code", "multiple_code_blocks", "json_envelope", "unified_diff", "incomplete_fence"],
        "newline_policy": "match_frozen_source",
        "indentation_policy": "uniform_outer_offset_only",
        "semantic_repair": False,
    }


def _line_start(source: str, offset: int) -> int:
    return source.rfind("\n", 0, offset) + 1


def source_block_span(source: str, source_block: str) -> dict[str, Any]:
    if source.count(source_block) != 1:
        return {"accepted": False, "reason": "source_block_not_unique"}
    start = source.index(source_block)
    line_start = _line_start(source, start)
    base_indent = source[line_start:start]
    if base_indent.strip():
        return {"accepted": False, "reason": "non_whitespace_prefix"}
    extended_block = base_indent + source_block
    if source.count(extended_block) != 1:
        return {"accepted": False, "reason": "extended_block_not_unique"}
    return {
        "accepted": True,
        "source_block_digest": bootstrap_digest(source_block),
        "extended_block": extended_block,
        "extended_block_digest": bootstrap_digest(extended_block),
        "base_indentation": base_indent,
        "base_indentation_width": len(base_indent),
        "start_offset": line_start,
        "end_offset": line_start + len(extended_block),
    }


def classify_wrapper(raw: str) -> dict[str, Any]:
    text = str(raw or "")
    stripped = text.strip()
    fence_pattern = re.compile(r"```([A-Za-z0-9_-]*)\r?\n(.*?)\r?\n```", re.S)
    fences = list(fence_pattern.finditer(stripped))
    if not stripped:
        wrapper = "empty"
    elif stripped.startswith("{") or stripped.startswith("["):
        wrapper = "json_envelope"
    elif stripped.startswith("diff --git") or stripped.startswith("@@"):
        wrapper = "unified_diff"
    elif "```" in stripped and not fences:
        wrapper = "incomplete_fence"
    elif len(fences) == 1 and fences[0].span() == (0, len(stripped)):
        tag = fences[0].group(1).strip().lower()
        wrapper = "single_python_fence" if tag in {"", "python", "py"} else "unsupported_fence"
    elif len(fences) > 1:
        wrapper = "multiple_code_blocks"
    elif fences:
        wrapper = "prose_plus_code"
    else:
        wrapper = "plain_source"
    return {
        "wrapper_type": wrapper,
        "fence_count": len(fences),
        "language_tag": fences[0].group(1).strip().lower() if fences else "",
        "prose_before_or_after": bool(fences and (fences[0].span() != (0, len(stripped)))),
        "raw_digest": bootstrap_digest(text),
    }


def extract_payload(raw: str) -> dict[str, Any]:
    audit = classify_wrapper(raw)
    stripped = str(raw or "").strip()
    if audit["wrapper_type"] == "plain_source":
        return {"accepted": True, "payload": stripped, "wrapper_audit": audit}
    if audit["wrapper_type"] != "single_python_fence":
        return {"accepted": False, "payload": "", "wrapper_audit": audit, "reason": "wrapper_rejected"}
    match = re.fullmatch(r"```(?:python|py)?\r?\n(.*?)\r?\n```", stripped, re.S | re.I)
    if not match:
        return {"accepted": False, "payload": "", "wrapper_audit": audit, "reason": "fence_parse_failed"}
    return {"accepted": True, "payload": match.group(1), "wrapper_audit": audit}


def normalize_newlines(payload: str, *, newline_style: str) -> dict[str, Any]:
    before = str(payload)
    normalized = before.replace("\r\n", "\n").replace("\r", "\n")
    if newline_style == "crlf":
        normalized = normalized.replace("\n", "\r\n")
    return {
        "accepted": True,
        "original_digest": bootstrap_digest(before),
        "normalized_digest": bootstrap_digest(normalized),
        "newline_style": newline_style,
        "payload": normalized,
    }


def _nonblank_indents(lines: list[str]) -> list[str]:
    return [re.match(r"[ \t]*", line).group(0) for line in lines if line.strip()]


def relative_indentation_signature(payload: str) -> tuple[int, ...]:
    lines = str(payload).splitlines()
    indents = _nonblank_indents(lines)
    if not indents:
        return ()
    widths = [len(indent) for indent in indents]
    base = min(widths)
    return tuple(width - base for width in widths)


def bind_outer_indentation(payload: str, *, target_indent: str) -> dict[str, Any]:
    lines = str(payload).splitlines()
    indents = _nonblank_indents(lines)
    if not indents:
        return {"accepted": False, "reason": "empty_payload"}
    if any("\t" in indent for indent in indents) and any(" " in indent for indent in indents):
        return {"accepted": False, "reason": "mixed_indentation"}
    widths = [len(indent) for indent in indents]
    common = min(widths)
    before_sig = relative_indentation_signature(payload)
    rebound = []
    for line in lines:
        if not line.strip():
            rebound.append("")
        else:
            rebound.append(target_indent + line[common:])
    bound = "\n".join(rebound)
    after_sig = relative_indentation_signature(bound)
    return {
        "accepted": before_sig == after_sig,
        "input_base_indentation": " " * common,
        "target_indentation": target_indent,
        "applied_uniform_offset": len(target_indent) - common,
        "relative_indentation_before": before_sig,
        "relative_indentation_after": after_sig,
        "relative_indentation_preserved": before_sig == after_sig,
        "payload": bound,
    }


def syntactic_unit(payload: str) -> dict[str, Any]:
    try:
        parsed = ast.parse(str(payload).strip())
    except SyntaxError as exc:
        return {"complete": False, "unit": "syntax_error", "detail": str(exc)}
    if len(parsed.body) == 1 and isinstance(parsed.body[0], ast.If):
        return {"complete": True, "unit": "if_statement"}
    return {"complete": False, "unit": type(parsed.body[0]).__name__ if parsed.body else "empty"}


def validate_tiny_host(raw: str, *, source_block: str, newline_style: str = "lf") -> dict[str, Any]:
    extracted = extract_payload(raw)
    if not extracted["accepted"]:
        return {"accepted": False, "reason": "extraction_failed", "extraction": extracted}
    normalized = normalize_newlines(extracted["payload"], newline_style=newline_style)
    bound = bind_outer_indentation(normalized["payload"], target_indent="    ")
    host = "def sample(report, audit):\n" + bound.get("payload", "") + "\n    return {'status': 'fallback'}\n"
    try:
        compile(host, "tiny_host.py", "exec")
    except SyntaxError as exc:
        return {"accepted": False, "reason": "host_syntax_error", "detail": str(exc), "host": host}
    return {"accepted": True, "host": host, "extraction": extracted, "indentation_binding": bound}


def build_replacement_from_raw(raw: str, *, source: str, source_block: str, newline_style: str) -> dict[str, Any]:
    span = source_block_span(source, source_block)
    if not span["accepted"]:
        return {"accepted": False, "reason": "source_span_failed", "span": span}
    extracted = extract_payload(raw)
    if not extracted["accepted"]:
        return {"accepted": False, "reason": "extraction_failed", "extraction": extracted}
    normalized = normalize_newlines(extracted["payload"], newline_style=newline_style)
    bound = bind_outer_indentation(normalized["payload"], target_indent=str(span["base_indentation"]))
    if not bound["accepted"]:
        return {"accepted": False, "reason": "indentation_binding_failed", "indentation_binding": bound}
    unit = syntactic_unit(str(normalized["payload"]))
    if not unit["complete"] or unit["unit"] != "if_statement":
        return {"accepted": False, "reason": "syntactic_unit_invalid", "syntactic_unit": unit}
    proposed = source.replace(str(span["extended_block"]), str(bound["payload"]), 1)
    try:
        compile(proposed, IMPLEMENTATION_PATH, "exec")
    except SyntaxError as exc:
        return {"accepted": False, "reason": "full_source_syntax_invalid", "detail": str(exc), "proposed_source_digest": bootstrap_digest(proposed)}
    diff = "".join(difflib.unified_diff(
        source.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile=f"a/{IMPLEMENTATION_PATH}",
        tofile=f"b/{IMPLEMENTATION_PATH}",
    ))
    strategy = validate_strategy_continuity(str(normalized["payload"]))
    return {
        "accepted": strategy["accepted"] and bool(diff),
        "extraction": extracted,
        "newline_normalization": {key: value for key, value in normalized.items() if key != "payload"},
        "indentation_binding": {key: value for key, value in bound.items() if key != "payload"},
        "accepted_replacement": str(bound["payload"]),
        "accepted_replacement_digest": bootstrap_digest(str(bound["payload"])),
        "normalized_payload_digest": normalized["normalized_digest"],
        "relative_indentation_audit": {
            "before": bound["relative_indentation_before"],
            "after": bound["relative_indentation_after"],
            "preserved": bound["relative_indentation_preserved"],
        },
        "syntactic_unit": unit,
        "syntax_validation": {"accepted": True, "proposed_source_digest": bootstrap_digest(proposed)},
        "strategy_continuity": strategy,
        "proposed_source_digest": bootstrap_digest(proposed),
        "diff": diff,
        "diff_digest": bootstrap_digest(diff),
        "hunk_count": sum(1 for line in diff.splitlines() if line.startswith("@@")),
        "changed_line_count": sum(1 for line in diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))),
    }


def attach_metadata(*, replacement: str, original_candidate: Mapping[str, Any], source_block_digest: str, model_identity: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "result_type": RESULT_TYPE,
        "proposal_id": PROPOSAL_ID,
        "revises_candidate_digest": RETAINED_CANDIDATE_DIGEST,
        "implementation_path": IMPLEMENTATION_PATH,
        "source_block_digest": source_block_digest,
        "replacement_content": replacement,
        "change_summary": original_candidate.get("change_intent"),
        "expected_behavioral_change": original_candidate.get("expected_behavioral_change"),
        "limitations": original_candidate.get("limitations"),
        "uncertainty": original_candidate.get("uncertainty"),
        "authority_used": ["bounded_local_sandbox"],
        "code_worker_model": dict(model_identity),
        "assembly_method": "deterministic_code_output_adapter_binding_v1",
    }


def negative_controls(valid: str, *, source: str, source_block: str, newline_style: str) -> dict[str, Any]:
    cases = {
        "one_fenced_block": f"```python\n{valid}\n```",
        "prose_plus_fence": f"Here:\n```python\n{valid}\n```",
        "two_fenced_alternatives": f"```python\n{valid}\n```\n```python\n{valid}\n```",
        "json_envelope": json.dumps({"code": valid}),
        "unified_diff_fence": "```diff\n@@\n-old\n+new\n```",
        "incomplete_fence": f"```python\n{valid}",
        "inconsistent_indentation": "if report.get('status'):\n  if audit.get('accepted'):\n        return {'status': 'x'}",
        "missing_nested_body": "if report.get('status'):\n    if audit.get('accepted'):",
        "syntax_invalid": "if report.get('status'):\nreturn {",
        "evaluator_hard_coding": "if report.get('status') and audit.get('accepted') is True:\n    return {'grounding_audit': {'accepted': True}}",
        "unconditional_bypass": "if True:\n    return {'status': 'AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_FAILED'}",
    }
    results: dict[str, Any] = {}
    for name, raw in cases.items():
        built = build_replacement_from_raw(raw, source=source, source_block=source_block, newline_style=newline_style)
        if name == "one_fenced_block":
            results[name] = {"accepted": built["accepted"], "expected": "accepted_by_wrapper_then_normal_validation"}
        else:
            results[name] = {"accepted": built["accepted"], "reason": built.get("reason"), "strategy": built.get("strategy_continuity")}
    return results
