import subprocess
from types import SimpleNamespace

from orchestration.runtime.cognitive_candidate_exact_edit import select_source_block
from orchestration.runtime.cognitive_candidate_revision import RETAINED_CANDIDATE_DIGEST
from orchestration.runtime.cognitive_code_worker_qualification import (
    QWEN25_CODER_EXPECTED_SHA256,
    assemble_replacement_artifact,
    model_identity_from_spec,
    negative_controls,
    raw_response_content,
    render_deterministic_diff,
    render_raw_code_request,
    validate_raw_replacement,
    validate_strategy_continuity,
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


def raw_replacement():
    return '''if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:
            if existing.get("advisory_output_id") in set(audit.get("rejected_output_ids") or ()):
                return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP", "request": request, "advisory_output": existing, "grounding_audit": audit, "duplicate_suppressed": False, "reason": "stale_rejected_advisory_artifact"}
            return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED", "request": request, "advisory_output": existing, "grounding_audit": audit, "duplicate_suppressed": True}'''


def original_candidate():
    return {
        "change_intent": "Introduce artifact freshness and rejection history validation before accepting grounding_audit.accepted.",
        "expected_behavioral_change": "Prevent stale rejected advisory artifacts from being treated as passed.",
        "limitations": ["bounded duplicate branch only"],
        "uncertainty": {"score": 0.0, "reason": "source-window bounded"},
    }


def test_model_identity_digest_binding():
    spec = SimpleNamespace(
        name="qwen2-5-coder-7b-instruct-gguf-qwen2-5-coder-7b-instruct-q4-k-m",
        path="G:/models/qwen.gguf",
        family="qwen",
        quantization="Q4_K_M",
        context_length=32768,
        size_bytes=123,
    )

    identity = model_identity_from_spec(spec, digest=QWEN25_CODER_EXPECTED_SHA256, backend_version="llama_cpp_python")

    assert identity["digest_matches_expected"] is True
    assert identity["quantization"] == "Q4_K_M"


def test_native_template_raw_code_request_has_no_json_contract():
    block = select_source_block(SOURCE)
    request = render_raw_code_request(
        implementation_path=IMPLEMENTATION_PATH,
        diagnosed_transition="stale pass",
        change_intent="bounded branch replacement",
        expected_behavior="block stale artifact",
        source_block=block["source_block"],
    )

    assert "Do not return JSON" in request[0]["content"]
    assert "required_output_schema" not in request[1]["content"]


def test_raw_response_content_extraction():
    response = {"choices": [{"message": {"content": raw_replacement()}}]}

    assert raw_response_content(response) == raw_replacement()


def test_raw_replacement_validation_and_strategy_accept():
    block = select_source_block(SOURCE)
    validation = validate_raw_replacement(raw_replacement(), source=SOURCE, source_block=block["source_block"], source_block_digest=block["source_block_digest"])
    strategy = validate_strategy_continuity(raw_replacement())

    assert validation["accepted"] is True
    assert strategy["accepted"] is True


def test_json_markdown_prose_partial_and_bad_controls_reject():
    block = select_source_block(SOURCE)
    controls = negative_controls(raw_replacement(), source=SOURCE, source_block=block["source_block"], source_block_digest=block["source_block_digest"])

    for name, result in controls.items():
        assert result["accepted"] is False, name


def test_deterministic_metadata_binding_does_not_invent_semantics():
    block = select_source_block(SOURCE)
    model = {"model_id": "qwen2.5-coder", "file_digest": QWEN25_CODER_EXPECTED_SHA256}

    artifact = assemble_replacement_artifact(raw=raw_replacement(), original_candidate=original_candidate(), source_block_digest=block["source_block_digest"], code_worker_model=model)

    assert artifact["proposal_id"] == PROPOSAL_ID
    assert artifact["revises_candidate_digest"] == RETAINED_CANDIDATE_DIGEST
    assert artifact["change_summary"] == original_candidate()["change_intent"]
    assert artifact["replacement_content"] == raw_replacement()


def test_deterministic_replacement_diff_and_apply_check(tmp_path):
    block = select_source_block(SOURCE)
    diff = render_deterministic_diff(SOURCE, block["source_block"], raw_replacement())
    target = tmp_path / IMPLEMENTATION_PATH
    patch = tmp_path / "worker.patch"
    target.parent.mkdir(parents=True)
    target.write_text(SOURCE, encoding="utf-8")
    patch.write_text(diff["diff"], encoding="utf-8")
    before = target.read_text(encoding="utf-8")

    result = subprocess.run(["git", "apply", "--check", str(patch)], cwd=tmp_path, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    assert diff["accepted"] is True
    assert diff["proposed_source_digest"] != bootstrap_digest(SOURCE)
    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == before
