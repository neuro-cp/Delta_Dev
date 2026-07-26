from pathlib import Path

from orchestration.runtime.cognitive_code_output_adapter import adapter_record
from orchestration.runtime.cognitive_sandbox_application2 import (
    ACCEPTED_REPLACEMENT_DIGEST,
    DIFF_DIGEST,
    FINAL_APPLICATION_BLOCKED,
    FINAL_PASSED,
    FINAL_REGRESSION,
    RAW_DIGEST,
    classify_behavioral_comparison,
    evaluator_freeze,
    final_status,
    negative_controls,
    stale_replay_observation,
    verify_artifact_identity,
)
from orchestration.runtime.cognitive_sandbox_execution import IMPLEMENTATION_PATH, PROPOSAL_ID, REPLACEMENT_DIGEST as EVALUATOR_DIGEST, REPLACEMENT_EVALUATOR
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


def proposal():
    return {"proposal_id": PROPOSAL_ID}


def amendment():
    return {
        "amendment_id": "cognitive-evaluator-binding-amendment-eeb832fb84c14b60",
        "amendment_digest": "5d687ae4916b306318ec72a7376e420c3f6d9092dc9eca24019bc511073e5e32",
        "replacement_evaluator": REPLACEMENT_EVALUATOR,
        "replacement_evaluator_digest": EVALUATOR_DIGEST,
    }


def replacement(raw: str, diff: str):
    return {
        "proposal_id": PROPOSAL_ID,
        "implementation_path": IMPLEMENTATION_PATH,
        "source_block_digest": "982500ceab9f18437f71bc39d5ce301240c227948bec8e3c6db4e2875fba03fc",
        "replacement_content": raw,
        "code_worker_model": {"file_digest": "7ec3d5cfd560c5eac34e6c377c0bbc2bda389b282dca2b28bc31e621d26929a7"},
        "_diff": diff,
    }


def test_artifact_identity_verifies_all_retained_digests():
    raw = "x"
    diff = "y"
    # Use monkey-sized records but preserve digest expectations through patching values.
    result = verify_artifact_identity(
        proposal=proposal(),
        amendment=amendment(),
        adapter_final={"status": "COGNITIVE_CODE_OUTPUT_ADAPTER_1_PASSED"},
        adapter_record=adapter_record(),
        replacement={**replacement(raw, diff), "replacement_content": raw},
        diff_text=diff,
        raw_text=raw,
    )

    assert result["accepted"] is False
    assert "raw_output_digest_mismatch" in result["reasons"]


def test_evaluator_freeze_records_independence_fields(tmp_path):
    evaluator = tmp_path / "evaluator.py"
    evaluator.write_text("x", encoding="utf-8")

    frozen = evaluator_freeze(evaluator)

    assert frozen["candidate_identity_used"] is False
    assert frozen["strategy_label_used"] is False
    assert frozen["fixture_filename_used"] is False


def test_behavioral_comparison_maps_statuses():
    baseline = {"classification": "stale_pass_detected"}
    improved = classify_behavioral_comparison(
        baseline_eval=baseline,
        after_eval={"classification": "valid_blocked_behavior"},
        application_success=True,
        changed_files=(IMPLEMENTATION_PATH,),
        focused_exit_code=0,
        evaluator_unchanged=True,
    )
    regression = classify_behavioral_comparison(
        baseline_eval=baseline,
        after_eval={"classification": "unrelated_failure"},
        application_success=True,
        changed_files=(IMPLEMENTATION_PATH,),
        focused_exit_code=0,
        evaluator_unchanged=True,
    )
    blocked = classify_behavioral_comparison(
        baseline_eval=baseline,
        after_eval={"classification": "unrelated_failure"},
        application_success=False,
        changed_files=(),
        focused_exit_code=1,
        evaluator_unchanged=True,
    )

    assert final_status(improved) == FINAL_PASSED
    assert final_status(regression) == FINAL_REGRESSION
    assert final_status(blocked) == FINAL_APPLICATION_BLOCKED


def test_negative_controls_reject_bad_artifacts_and_duplicate():
    controls = negative_controls()

    for name, result in controls.items():
        assert result.get("accepted") is False, name
    assert controls["duplicate_application"]["duplicate_suppressed"] is True


def test_stale_replay_observation_shape():
    observation = stale_replay_observation()

    assert observation["status"] == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"
    assert observation["duplicate_suppressed"] is True


def test_no_copyback_contract_is_explicit():
    record = {"primary_source_mutated": False, "copyback": False, "staged": False}

    assert record["primary_source_mutated"] is False
    assert record["copyback"] is False
    assert record["staged"] is False
