from orchestration.runtime.v24_recall_answer_ux_trial import run_recall_answer_ux_trial, validate_recall_answer_ux_safe
from orchestration.runtime.v24_recall_answer_ux_trial_report import write_recall_answer_ux_report


def test_local_known_answer_works():
    payload = run_recall_answer_ux_trial("What does DELTA know about HYB1?")
    assert payload["local_answer"]["matched"] is True


def test_recall_candidate_shown_with_provenance_and_labels():
    payload = run_recall_answer_ux_trial("What does DELTA know about HYB1?")
    assert payload["evidence_items"]
    assert all(item["candidate_context_only"] is True and item["authoritative"] is False and item["truth_claim"] is False for item in payload["evidence_items"])
    assert validate_recall_answer_ux_safe(payload)


def test_unknown_bounded_and_no_provider_call():
    payload = run_recall_answer_ux_trial("unknown unlikely topic")
    assert payload["decision"]["provider_call_performed"] is False
    assert payload["decision"]["memory_write_performed"] is False


def test_no_recall_mutation_or_hyb1_change():
    flags = run_recall_answer_ux_trial("HYB1")["invariant_flags"]
    assert flags["recall_mutated"] is False
    assert flags["hyb1_default_activation_enabled"] is False


def test_report_generation():
    data = write_recall_answer_ux_report()
    assert data["all_safe"] is True

