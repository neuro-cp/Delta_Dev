from orchestration.runtime.v24_evaluator_consolidation_ux_trial import run_evaluator_consolidation_ux_trial, validate_evaluator_consolidation_ux_safe
from orchestration.runtime.v24_evaluator_consolidation_ux_trial_report import write_evaluator_consolidation_ux_report


def _candidate():
    return {"candidate_id": "candidate-demo", "candidate_text": "Model B remains default.", "provenance_reference_ids": ["p"]}


def test_evaluator_review_displayed_as_advisory():
    payload = run_evaluator_consolidation_ux_trial(_candidate())
    assert payload["ux"]["review_displayed_as_advisory"] is True
    assert payload["evaluator_review"]["recommendation"]["advisory_only"] is True
    assert validate_evaluator_consolidation_ux_safe(payload)


def test_evaluator_approval_not_user_approval_and_candidate_unwritten():
    payload = run_evaluator_consolidation_ux_trial(_candidate())
    assert payload["decision"]["evaluator_approval_accepted"] is False
    assert payload["decision"]["candidate_written"] is False


def test_risk_flags_displayed():
    payload = run_evaluator_consolidation_ux_trial({**_candidate(), "ambiguity_flag": True})
    assert "ambiguity" in payload["evaluator_review"]["risk_assessment"]["risks"]


def test_no_live_call_or_mutation_by_default():
    payload = run_evaluator_consolidation_ux_trial(_candidate())
    assert payload["decision"]["provider_call_performed"] is False
    assert payload["decision"]["evaluator_live_call_performed"] is False
    assert payload["decision"]["recall_mutated"] is False


def test_report_generation():
    data = write_evaluator_consolidation_ux_report()
    assert data["all_safe"] is True

