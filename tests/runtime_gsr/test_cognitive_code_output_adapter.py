import subprocess

from orchestration.runtime.cognitive_candidate_exact_edit import select_source_block
from orchestration.runtime.cognitive_code_output_adapter import (
    adapter_record,
    attach_metadata,
    bind_outer_indentation,
    build_replacement_from_raw,
    classify_wrapper,
    extract_payload,
    negative_controls,
    normalize_newlines,
    relative_indentation_signature,
    source_block_span,
    validate_tiny_host,
)
from orchestration.runtime.cognitive_sandbox_execution import IMPLEMENTATION_PATH, PROPOSAL_ID
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


SOURCE = '''def request_bounded_advice(output_root):
    existing = _read_json(output_root / "advisory_output.json")
    if existing:
        request = _read_json(output_root / "advisory_request.json") or {}
        audit = _read_json(output_root / "grounding_audit.json") or {}
        report = _read_json(output_root / "report.json") or {}
        if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:
            return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED", "request": request, "advisory_output": existing, "grounding_audit": audit, "duplicate_suppressed": True}
        return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP", "request": request, "advisory_output": existing, "grounding_audit": audit, "duplicate_suppressed": False, "reason": "existing_advisory_not_grounded"}
    return {"status": "new"}
'''


RAW = '''if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:
    if validate_artifact_freshness(audit) and not has_rejection_history(audit):
        return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED", "request": request, "advisory_output": existing, "grounding_audit": audit, "duplicate_suppressed": True}
    else:
        return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_FAILED", "request": request, "advisory_output": existing, "grounding_audit": audit, "duplicate_suppressed": False}'''


def test_wrapper_classification_and_plain_source_acceptance():
    assert classify_wrapper(RAW)["wrapper_type"] == "plain_source"
    assert extract_payload(RAW)["payload"] == RAW


def test_single_python_fence_extracts_without_prose():
    wrapped = f"```python\n{RAW}\n```"
    extracted = extract_payload(wrapped)

    assert classify_wrapper(wrapped)["wrapper_type"] == "single_python_fence"
    assert extracted["accepted"] is True
    assert extracted["payload"] == RAW


def test_rejects_prose_multiple_json_diff_and_incomplete_fence():
    bad = [
        f"Here:\n```python\n{RAW}\n```",
        f"```python\n{RAW}\n```\n```python\n{RAW}\n```",
        '{"code": "if x: pass"}',
        "```diff\n@@\n-a\n+b\n```",
        f"```python\n{RAW}",
    ]

    for item in bad:
        assert extract_payload(item)["accepted"] is False


def test_newline_normalization_and_uniform_indentation_binding_preserve_relative_shape():
    normalized = normalize_newlines(RAW.replace("\n", "\r\n"), newline_style="lf")
    bound = bind_outer_indentation(normalized["payload"], target_indent="        ")

    assert normalized["payload"] == RAW
    assert bound["accepted"] is True
    assert bound["relative_indentation_preserved"] is True
    assert relative_indentation_signature(RAW) == bound["relative_indentation_after"]


def test_tiny_host_context_validation_accepts_source_only_block():
    tiny = 'if report.get("status") == "PASSED" and audit.get("accepted") is True:\n    return {"status": "BLOCKED"}'

    result = validate_tiny_host(tiny, source_block=tiny)

    assert result["accepted"] is True


def test_full_source_replacement_strategy_diff_and_apply_check(tmp_path):
    block = select_source_block(SOURCE)
    built = build_replacement_from_raw(f"```python\n{RAW}\n```", source=SOURCE, source_block=block["source_block"], newline_style="lf")
    target = tmp_path / IMPLEMENTATION_PATH
    patch = tmp_path / "adapter.patch"
    target.parent.mkdir(parents=True)
    target.write_text(SOURCE, encoding="utf-8")
    patch.write_text(built["diff"], encoding="utf-8")
    before = target.read_text(encoding="utf-8")

    check = subprocess.run(["git", "apply", "--check", str(patch)], cwd=tmp_path, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    assert built["accepted"] is True
    assert built["syntax_validation"]["accepted"] is True
    assert built["strategy_continuity"]["accepted"] is True
    assert check.returncode == 0
    assert target.read_text(encoding="utf-8") == before


def test_metadata_attachment_does_not_invent_semantics():
    block = select_source_block(SOURCE)
    original = {"change_intent": "intent", "expected_behavioral_change": "expected", "limitations": ["limit"], "uncertainty": {"score": 0.1, "reason": "bounded"}}
    meta = {"model_id": "qwen2.5", "file_digest": "digest"}
    artifact = attach_metadata(replacement=RAW, original_candidate=original, source_block_digest=block["source_block_digest"], model_identity=meta)

    assert artifact["proposal_id"] == PROPOSAL_ID
    assert artifact["change_summary"] == "intent"
    assert artifact["replacement_content"] == RAW


def test_negative_controls_reject_materially_bad_cases():
    block = select_source_block(SOURCE)
    controls = negative_controls(RAW, source=SOURCE, source_block=block["source_block"], newline_style="lf")

    assert controls["one_fenced_block"]["accepted"] is True
    for name, result in controls.items():
        if name != "one_fenced_block":
            assert result["accepted"] is False, name


def test_source_block_span_preserves_frozen_digest():
    block = select_source_block(SOURCE)
    span = source_block_span(SOURCE, block["source_block"])

    assert span["accepted"] is True
    assert span["source_block_digest"] == bootstrap_digest(block["source_block"])
    assert span["base_indentation"] == "        "
