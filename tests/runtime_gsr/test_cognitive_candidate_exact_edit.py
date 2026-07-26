import subprocess

from orchestration.runtime.cognitive_candidate_exact_edit import (
    BLOCK_MARKER,
    RESULT_TYPE,
    attach_metadata,
    negative_controls,
    render_exact_diff,
    replacement_schema,
    select_source_block,
    source_identity,
    validate_replacement_artifact,
    validate_strategy_continuity,
)
from orchestration.runtime.cognitive_candidate_revision import RETAINED_CANDIDATE_DIGEST
from orchestration.runtime.cognitive_sandbox_execution import IMPLEMENTATION_PATH, PROPOSAL_ID
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


SOURCE = '''"""demo"""

def request_bounded_advice(output_root):
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


def artifact(block):
    return {
        "result_type": RESULT_TYPE,
        "proposal_id": PROPOSAL_ID,
        "revises_candidate_digest": RETAINED_CANDIDATE_DIGEST,
        "implementation_path": IMPLEMENTATION_PATH,
        "source_block_digest": block["source_block_digest"],
        "replacement_content": '''if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:
            return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP", "request": request, "advisory_output": existing, "grounding_audit": audit, "duplicate_suppressed": False, "reason": "stale_existing_advisory_not_reaccepted"}''',
        "change_summary": "Keep stale duplicate advisory replay from returning passed without fresh validation.",
        "expected_behavioral_change": "Existing stale advisory replay blocks rather than returning passed.",
        "limitations": ["Only covers the duplicate existing-advisory branch."],
        "uncertainty": {"score": 0.2, "reason": "Behavior is not executed in this exact-edit gate."},
        "authority_used": ["bounded_local_sandbox"],
    }


def test_exact_source_block_selection_is_unique_complete_unit():
    block = select_source_block(SOURCE)

    assert block["accepted"] is True
    assert block["syntactic_unit"] == "if_statement"
    assert block["occurrence_count"] == 1
    assert BLOCK_MARKER in block["source_block"]


def test_source_identity_binds_digest_encoding_and_newline():
    identity = source_identity(SOURCE)

    assert identity["digest"] == bootstrap_digest(SOURCE)
    assert identity["encoding"] == "utf-8"
    assert identity["newline_style"] == "lf"


def test_minimal_schema_and_metadata_are_deterministic():
    block = select_source_block(SOURCE)
    schema = replacement_schema(block["source_block_digest"])
    meta = attach_metadata(artifact(block), block=block, source_digest=bootstrap_digest(SOURCE), model_id="qwen")

    assert schema["result_type"] == RESULT_TYPE
    assert meta["original_candidate_digest"] == RETAINED_CANDIDATE_DIGEST
    assert meta["source_block_identity"]["digest"] == block["source_block_digest"]


def test_complete_replacement_validation_and_strategy_continuity_accept():
    block = select_source_block(SOURCE)
    candidate = artifact(block)

    validation = validate_replacement_artifact(candidate, source=SOURCE, block=block)
    strategy = validate_strategy_continuity(candidate, block=block)

    assert validation["accepted"] is True
    assert strategy["accepted"] is True


def test_negative_controls_reject_bad_replacements():
    block = select_source_block(SOURCE)
    controls = negative_controls(artifact(block), source=SOURCE, block=block)

    for name, result in controls.items():
        assert result.get("accepted") is False, name


def test_deterministic_exact_replacement_and_diff_render():
    block = select_source_block(SOURCE)
    rendered = render_exact_diff(SOURCE, block, artifact(block)["replacement_content"])

    assert rendered["accepted"] is True
    assert rendered["hunk_count"] == 1
    assert rendered["target_paths"] == (IMPLEMENTATION_PATH,)
    assert "stale_existing_advisory_not_reaccepted" in rendered["diff"]


def test_git_apply_check_succeeds_without_applying(tmp_path):
    block = select_source_block(SOURCE)
    rendered = render_exact_diff(SOURCE, block, artifact(block)["replacement_content"])
    target = tmp_path / IMPLEMENTATION_PATH
    target.parent.mkdir(parents=True)
    target.write_text(SOURCE, encoding="utf-8")
    patch = tmp_path / "exact.patch"
    patch.write_text(rendered["diff"], encoding="utf-8")
    before = target.read_text(encoding="utf-8")

    result = subprocess.run(["git", "apply", "--check", str(patch)], cwd=tmp_path, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == before
