from orchestration.runtime.cognitive_candidate_revision import (
    RETAINED_CANDIDATE_DIGEST,
    classify_patch_failure,
    negative_controls,
    render_revised_patch,
    validate_revised_candidate,
)
from orchestration.runtime.cognitive_sandbox_execution import FOCUSED_TEST_PATH, IMPLEMENTATION_PATH, PROPOSAL_ID


SOURCE = """def request_bounded_advice(output_root):
    if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:
        return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"}
    return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP"}
"""


ANCHOR = """if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:
        return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"}"""


def revised():
    return {
        "result_type": "sandbox_candidate_plan",
        "proposal_id": PROPOSAL_ID,
        "revises_candidate_digest": RETAINED_CANDIDATE_DIGEST,
        "candidate_id": "revision-1",
        "implementation_path": IMPLEMENTATION_PATH,
        "focused_test_path": FOCUSED_TEST_PATH,
        "change_intent": "Replace the stale pass branch with a blocked return.",
        "edits": [{
            "target": IMPLEMENTATION_PATH,
            "operation": "replace_block",
            "anchor": ANCHOR,
            "expected_anchor_count": 1,
            "replacement": "if report.get(\"status\") == \"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED\" and audit.get(\"accepted\") is True:\n        return {\"status\": \"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP\"}",
            "purpose": "Keep stale replay from returning PASSED.",
        }],
        "expected_behavioral_change": "Stale replay blocks.",
        "limitations": ["single branch"],
        "uncertainty": {"score": 0.2, "reason": "bounded source"},
        "authority_used": ["bounded_local_sandbox"],
    }


def test_failure_classification_identifies_patch_context_mismatch():
    result = classify_patch_failure(stderr="error: patch does not apply", anchor_count=1, source_digest_matches=True)

    assert result["classification"] == "insufficient_patch_context"


def test_revised_candidate_validates_exact_anchor_and_prior_digest():
    result = validate_revised_candidate(revised(), full_source=SOURCE)

    assert result["accepted"] is True


def test_revised_candidate_rejects_approximate_and_wrong_prior_digest():
    bad = revised()
    bad["revises_candidate_digest"] = "wrong"
    bad["edits"][0]["anchor"] = "if ... accepted"

    result = validate_revised_candidate(bad, full_source=SOURCE)

    assert result["accepted"] is False
    assert "wrong_prior_candidate_digest" in result["reasons"]
    assert "approximate_anchor_rejected" in result["reasons"]


def test_render_revised_patch_is_in_memory_only():
    rendered = render_revised_patch(revised(), full_source=SOURCE)

    assert rendered["accepted"] is True
    assert rendered["source_modified"] is False
    assert rendered["hunk_count"] == 1
    assert "INTEGRITY_STOP" in rendered["patch"]


def test_negative_controls_reject_bad_revisions():
    controls = negative_controls(revised(), full_source=SOURCE)

    for name, result in controls.items():
        assert result.get("accepted") is False, name
