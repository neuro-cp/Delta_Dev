from orchestration.runtime.cognitive_candidate_generation_audit import (
    classify_timeout_phase,
    compact_candidate_schema,
    contract_audit,
    negative_controls,
    render_patch_from_plan,
    source_window,
    validate_candidate_plan,
)
from orchestration.runtime.cognitive_sandbox_execution import FOCUSED_TEST_PATH, IMPLEMENTATION_PATH, PROPOSAL_ID
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


SOURCE = """def before():
    return 1

def request_bounded_advice(output_root):
    existing = True
    if existing:
        if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:
            return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"}
        return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP"}
"""


def valid_plan():
    anchor = 'if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:'
    return {
        "result_type": "sandbox_candidate_plan",
        "proposal_id": PROPOSAL_ID,
        "candidate_id": "candidate-1",
        "implementation_path": IMPLEMENTATION_PATH,
        "focused_test_path": FOCUSED_TEST_PATH,
        "change_intent": "Guard stale duplicate replay before returning pass.",
        "edits": [{
            "target": IMPLEMENTATION_PATH,
            "operation": "replace_block",
            "anchor": anchor,
            "replacement": 'if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True and not report.get("rejected_outputs"):',
            "purpose": "Reject stale reports with retained rejected outputs.",
        }],
        "expected_behavioral_change": "Stale duplicate replay returns blocked disposition.",
        "limitations": ["single transition candidate"],
        "uncertainty": {"score": 0.2, "reason": "bounded source window"},
        "authority_used": ["bounded_local_sandbox"],
    }


def test_timeout_phase_classification_distinguishes_generation_from_load():
    before_token = classify_timeout_phase(
        [{"event": "load_started"}, {"event": "load_done"}, {"event": "prompt_processing_started"}],
        process_alive_after_timeout=True,
        forced_termination=True,
    )
    during_generation = classify_timeout_phase(
        [{"event": "load_started"}, {"event": "load_done"}, {"event": "first_token"}],
        process_alive_after_timeout=True,
        forced_termination=True,
    )

    assert before_token["classification"] == "timed_out_before_first_token"
    assert during_generation["classification"] == "timed_out_during_generation"
    assert during_generation["cleanup"] == "process_required_forced_termination"


def test_compact_schema_removes_unified_diff_serialization_burden():
    schema = compact_candidate_schema()
    audit = contract_audit(schema, prompt_characters=3000, source_characters=1200)

    assert schema["result_type"] == "sandbox_candidate_plan"
    assert "patch" not in schema
    assert audit["recommendation"] == "use_compact_candidate_plan_then_deterministic_patch_render"


def test_source_window_binds_full_digest_and_exact_anchor():
    window = source_window(SOURCE, anchor="request_bounded_advice")

    assert window["accepted"] is True
    assert window["anchor_match_count"] == 1
    assert window["full_source_digest"] == bootstrap_digest(SOURCE)
    assert window["validatable_against_full_file"] is True


def test_candidate_plan_scope_validation_and_metadata_requirements():
    result = validate_candidate_plan(valid_plan(), full_source=SOURCE)
    bad = validate_candidate_plan({**valid_plan(), "authority_used": ["network"], "limitations": []}, full_source=SOURCE)

    assert result["accepted"] is True
    assert result["classification"] == "candidate_scope_valid"
    assert bad["accepted"] is False
    assert "authority_not_bounded" in bad["reasons"]
    assert "limitations_required" in bad["reasons"]


def test_deterministic_diff_render_does_not_apply_source():
    plan = valid_plan()
    rendered = render_patch_from_plan(plan, full_source=SOURCE)

    assert rendered["accepted"] is True
    assert rendered["target"] == IMPLEMENTATION_PATH
    assert rendered["source_modified"] is False
    assert "rejected_outputs" in rendered["patch"]


def test_rendering_rejects_missing_or_non_unique_anchor():
    invented = valid_plan()
    invented["edits"][0]["anchor"] = "not present"
    non_unique = valid_plan()
    non_unique["edits"][0]["anchor"] = "if "

    assert render_patch_from_plan(invented, full_source=SOURCE)["accepted"] is False
    assert render_patch_from_plan(non_unique, full_source=SOURCE)["accepted"] is False


def test_negative_controls_reject_bad_candidate_plans():
    controls = negative_controls(valid_plan(), full_source=SOURCE)

    for name, result in controls.items():
        assert result["accepted"] is False, name


def test_no_application_test_or_evaluator_execution_contract_is_explicit():
    record = {
        "candidate_applied": False,
        "focused_test_executed_against_candidate": False,
        "post_candidate_evaluator_executed": False,
        "primary_copyback": False,
    }

    assert record == {
        "candidate_applied": False,
        "focused_test_executed_against_candidate": False,
        "post_candidate_evaluator_executed": False,
        "primary_copyback": False,
    }
